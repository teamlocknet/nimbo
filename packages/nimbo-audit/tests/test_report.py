"""Tests de `nimbo-audit report` (RF-04 / CU-03).

Rápidos y herméticos: usan tmp_path, nunca el home real. Cubren:
- Render determinista aislado de IO (mismo engagement -> mismo texto).
- Las tres secciones del reporte (datos, cronología de sesión, evidencia).
- Verificación de integridad recomputada DENTRO del reporte (opción a):
  intacta -> OK, modificada en disco -> MODIFICADO, borrada -> AUSENTE.
- Flujo engagement-sin-datos (CU-03 1a): [AVISO] + confirmación; declinar
  aborta sin escribir; --yes / confirmar generan un reporte parcial.
- Mensajes exactos [OK] / [AVISO] del CLI.
- Exportación PDF opcional con degradación graciosa de DOS niveles
  (pandoc ausente; pandoc presente pero sin motor PDF): nunca revienta ni
  deja el .md sin generar.
"""

from __future__ import annotations

import hashlib
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest
from typer.testing import CliRunner

from nimbo_audit.cli import app
from nimbo_audit.comandos.capture import ComandoCapture
from nimbo_audit.comandos.init import ComandoInit
from nimbo_audit.comandos.report import ComandoReport, EvidenciaVerificada
from nimbo_audit.errores import ExportacionPDFError
from nimbo_audit.modelos.engagement import Engagement
from nimbo_audit.modelos.evidencia import Evidencia
from nimbo_audit.repositorio.engagement_repo import RepositorioEngagementJSON
from nimbo_audit.repositorio.evidencia_repo import RepositorioEvidenciaJSON
from nimbo_audit.servicios import pdf as pdf_mod
from nimbo_audit.servicios.pdf import exportar_pdf
from nimbo_audit.servicios.reporte import renderizar_reporte

FECHA_FIJA = datetime(2026, 9, 9, 12, 0, 0, tzinfo=timezone.utc)


# --- helpers ----------------------------------------------------------------


def _engagement(base: Path, nombre: str = "acme") -> Path:
    return ComandoInit(
        nombre, RepositorioEngagementJSON(base), analista="tester", ahora=FECHA_FIJA
    ).ejecutar()


def _capturar(root: Path, tmp_path: Path, nombre: str, contenido: bytes) -> Evidencia:
    origen = tmp_path / nombre
    origen.write_bytes(contenido)
    return ComandoCapture(
        origen, RepositorioEvidenciaJSON(root), ahora=FECHA_FIJA
    ).ejecutar()


def _reportar(root: Path):
    return ComandoReport(
        root,
        RepositorioEngagementJSON(root.parent),
        RepositorioEvidenciaJSON(root),
    ).ejecutar()


# --- El repositorio ahora sabe LEER metadata (cargar) -----------------------


def test_repo_engagement_carga_metadata(tmp_path: Path) -> None:
    root = _engagement(tmp_path, "acme")
    repo = RepositorioEngagementJSON(tmp_path)
    eng = repo.cargar("acme")
    assert eng == Engagement(
        id="acme", fecha_inicio="2026-09-09T12:00:00+00:00", analista="tester"
    )


# --- Render puro y determinista (aislado de IO) -----------------------------


def _eng_demo() -> Engagement:
    return Engagement(
        id="acme", fecha_inicio="2026-09-09T12:00:00+00:00", analista="tester"
    )


def _ev(nombre: str, sha: str, estado: str) -> EvidenciaVerificada:
    return EvidenciaVerificada(
        Evidencia(nombre, f"evidencia/{nombre}", sha, "2026-09-09T12:00:00+00:00"),
        estado,
    )


def test_render_determinista(tmp_path: Path) -> None:
    eng = _eng_demo()
    evs = [_ev("a.pcap", "aa" * 32, "OK"), _ev("b.log", "bb" * 32, "MODIFICADO")]
    uno = renderizar_reporte(eng, evs, ["sesion.log"])
    dos = renderizar_reporte(eng, evs, ["sesion.log"])
    assert uno == dos
    assert uno.endswith("\n")


def test_render_tiene_las_tres_secciones_y_datos(tmp_path: Path) -> None:
    md = renderizar_reporte(_eng_demo(), [_ev("a.pcap", "aa" * 32, "OK")], [])
    assert "# Reporte de auditoría — acme" in md
    # 1. datos del engagement
    assert "acme" in md and "tester" in md and "2026-09-09T12:00:00+00:00" in md
    # 2. cronología de la sesión (ausente, tolerada)
    assert "sesión" in md.lower()
    # 3. evidencia con su hash y estado
    assert "a.pcap" in md and "aa" * 32 in md and "OK" in md


def test_render_sin_sesion_lo_indica(tmp_path: Path) -> None:
    md = renderizar_reporte(_eng_demo(), [_ev("a.pcap", "aa" * 32, "OK")], [])
    assert "No hay registro de sesión" in md


# --- Integridad recomputada dentro del reporte (opción a) -------------------


def test_report_integridad_intacta_es_ok(tmp_path: Path) -> None:
    root = _engagement(tmp_path)
    _capturar(root, tmp_path, "captura.pcap", b"datos intactos")
    res = _reportar(root)
    md = res.ruta_md.read_text(encoding="utf-8")
    assert "captura.pcap" in md
    assert "OK" in md
    assert res.resumen == {"OK": 1, "MODIFICADO": 0, "AUSENTE": 0}


def test_report_detecta_modificacion(tmp_path: Path) -> None:
    root = _engagement(tmp_path)
    _capturar(root, tmp_path, "captura.pcap", b"original")
    # Alguien manipula la evidencia ya registrada.
    (root / "evidencia" / "captura.pcap").write_bytes(b"MANIPULADO")

    res = _reportar(root)
    md = res.ruta_md.read_text(encoding="utf-8")
    assert "MODIFICADO" in md
    assert res.resumen["MODIFICADO"] == 1
    assert res.resumen["OK"] == 0


def test_report_detecta_evidencia_ausente(tmp_path: Path) -> None:
    root = _engagement(tmp_path)
    _capturar(root, tmp_path, "captura.pcap", b"original")
    # El archivo referenciado en el índice desaparece del disco.
    (root / "evidencia" / "captura.pcap").unlink()

    res = _reportar(root)
    md = res.ruta_md.read_text(encoding="utf-8")
    assert "AUSENTE" in md
    assert res.resumen["AUSENTE"] == 1


def test_report_md_determinista_sobre_disco(tmp_path: Path) -> None:
    root = _engagement(tmp_path)
    _capturar(root, tmp_path, "a.pcap", b"AAA")
    _capturar(root, tmp_path, "b.pcap", b"BBB")
    primero = _reportar(root).ruta_md.read_text(encoding="utf-8")
    segundo = _reportar(root).ruta_md.read_text(encoding="utf-8")
    assert primero == segundo


# --- Cronología: consume logs/ si existe, tolera su ausencia -----------------


def test_report_lista_registros_de_sesion_si_existen(tmp_path: Path) -> None:
    root = _engagement(tmp_path)
    _capturar(root, tmp_path, "a.pcap", b"AAA")
    (root / "logs" / "sesion.cast").write_text("...", encoding="utf-8")
    md = _reportar(root).ruta_md.read_text(encoding="utf-8")
    assert "sesion.cast" in md


# --- CU-03 1a: engagement sin datos -----------------------------------------


def test_report_sin_datos_no_tiene_datos(tmp_path: Path) -> None:
    root = _engagement(tmp_path)
    comando = ComandoReport(
        root, RepositorioEngagementJSON(root.parent), RepositorioEvidenciaJSON(root)
    )
    assert comando.tiene_datos() is False


def test_cli_report_sin_datos_pide_confirmacion_y_declina(tmp_path: Path) -> None:
    root = _engagement(tmp_path)
    res = CliRunner().invoke(app, ["report", "--dir", str(root)], input="n\n")
    assert "[AVISO] El engagement no contiene evidencia ni registros de sesión." in res.stdout
    # Declinar: no se genera nada.
    assert not (root / "reportes" / "reporte-acme.md").exists()


def test_cli_report_sin_datos_con_yes_genera_parcial(tmp_path: Path) -> None:
    root = _engagement(tmp_path)
    res = CliRunner().invoke(app, ["report", "--dir", str(root), "--yes"])
    assert res.exit_code == 0
    assert "[OK] Reporte generado en reportes/reporte-acme.md" in res.stdout
    assert (root / "reportes" / "reporte-acme.md").is_file()


# --- CLI: mensaje de éxito exacto -------------------------------------------


def test_cli_report_ok(tmp_path: Path) -> None:
    root = _engagement(tmp_path)
    origen = tmp_path / "captura.pcap"
    origen.write_bytes(b"datos")
    CliRunner().invoke(app, ["capture", str(origen), "--dir", str(root)])

    res = CliRunner().invoke(app, ["report", "--dir", str(root)])
    assert res.exit_code == 0
    assert "[OK] Reporte generado en reportes/reporte-acme.md" in res.stdout
    md = (root / "reportes" / "reporte-acme.md").read_text(encoding="utf-8")
    assert hashlib.sha256(b"datos").hexdigest() in md


def test_cli_report_sin_engagement_activo(tmp_path: Path) -> None:
    vacio = tmp_path / "vacio"
    vacio.mkdir()
    res = CliRunner().invoke(app, ["report", "--dir", str(vacio)])
    assert res.exit_code == 1
    assert "[ERROR]" in res.stderr


# --- Exportación PDF: degradación graciosa de DOS niveles -------------------


def test_pdf_pandoc_ausente_avisa(tmp_path: Path) -> None:
    md = tmp_path / "r.md"
    md.write_text("# hola\n", encoding="utf-8")
    with pytest.raises(ExportacionPDFError) as exc:
        exportar_pdf(md, tmp_path / "r.pdf", which=lambda _: None)
    assert "pandoc" in str(exc.value).lower()


def test_pdf_pandoc_sin_motor_avisa(tmp_path: Path) -> None:
    md = tmp_path / "r.md"
    md.write_text("# hola\n", encoding="utf-8")

    def _runner_falla(*args, **kwargs):
        return subprocess.CompletedProcess(args, returncode=1, stdout="", stderr="no pdf engine")

    with pytest.raises(ExportacionPDFError) as exc:
        exportar_pdf(
            md,
            tmp_path / "r.pdf",
            which=lambda _: "/usr/bin/pandoc",
            runner=_runner_falla,
        )
    assert "motor" in str(exc.value).lower()


def test_pdf_ok_invoca_pandoc(tmp_path: Path) -> None:
    md = tmp_path / "r.md"
    md.write_text("# hola\n", encoding="utf-8")
    pdf = tmp_path / "r.pdf"

    llamado = {}

    def _runner_ok(args, **kwargs):
        llamado["args"] = args
        pdf.write_bytes(b"%PDF-1.4 fake")
        return subprocess.CompletedProcess(args, returncode=0, stdout="", stderr="")

    exportar_pdf(md, pdf, which=lambda _: "/usr/bin/pandoc", runner=_runner_ok)
    assert pdf.is_file()
    assert "pandoc" in llamado["args"][0]


def test_cli_report_pdf_sin_pandoc_genera_md_y_avisa(
    tmp_path: Path, monkeypatch
) -> None:
    """--pdf nunca debe reventar ni dejar el .md sin generar (nivel a)."""
    monkeypatch.setattr(pdf_mod.shutil, "which", lambda _: None)
    root = _engagement(tmp_path)
    origen = tmp_path / "captura.pcap"
    origen.write_bytes(b"datos")
    CliRunner().invoke(app, ["capture", str(origen), "--dir", str(root)])

    res = CliRunner().invoke(app, ["report", "--dir", str(root), "--pdf"])
    assert res.exit_code == 0
    assert (root / "reportes" / "reporte-acme.md").is_file()
    assert "[AVISO]" in res.stdout
    assert not (root / "reportes" / "reporte-acme.pdf").exists()
