"""Exportación opcional del reporte a PDF (RF-04).

El `.md` es el entregable PRIMARIO; el PDF es un extra opt-in (`--pdf`). Se hace
por shell-out a `pandoc` (FOSS, auditable) SIN añadir dependencia Python: pandoc
—y su motor PDF (LaTeX/wkhtmltopdf)— son del entorno del usuario si los quiere.

Degradación graciosa de DOS niveles (nunca revienta ni deja el `.md` sin
generar; el CLI traduce el fallo a un `[AVISO]` con exit 0):
  (a) pandoc no está en PATH -> ExportacionPDFError explicando que falta pandoc;
  (b) pandoc está pero falla (típicamente sin motor PDF instalado) ->
      ExportacionPDFError explicando que falta el motor.

`which`/`runner` se inyectan (por defecto `shutil.which` / `subprocess.run`) para
poder simular ambos niveles en los tests sin depender del entorno.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Callable, Optional

from nimbo_audit.errores import ExportacionPDFError

Which = Callable[[str], Optional[str]]
Runner = Callable[..., "subprocess.CompletedProcess"]


def exportar_pdf(
    md_path: Path,
    pdf_path: Path,
    *,
    which: Which = shutil.which,
    runner: Runner = subprocess.run,
) -> Path:
    """Convierte `md_path` a `pdf_path` con pandoc. Devuelve la ruta del PDF.

    Lanza `ExportacionPDFError` (traducible a `[AVISO]`) si pandoc no está o si
    no puede generar el PDF; en ningún caso propaga un error crudo.
    """
    if which("pandoc") is None:
        raise ExportacionPDFError(
            "pandoc no está instalado en el sistema; se generó solo el .md. "
            "Instala pandoc si quieres exportar a PDF."
        )

    try:
        proc = runner(
            ["pandoc", str(md_path), "-o", str(pdf_path)],
            capture_output=True,
            text=True,
        )
    except OSError as exc:  # p. ej. binario ilegible pese a estar en PATH
        raise ExportacionPDFError(
            f"no se pudo ejecutar pandoc: {exc}; se generó solo el .md."
        ) from exc

    if proc.returncode != 0:
        raise ExportacionPDFError(
            "pandoc no pudo generar el PDF; probablemente falta un motor PDF "
            "(LaTeX o wkhtmltopdf) en el sistema. Se generó solo el .md."
        )
    return pdf_path
