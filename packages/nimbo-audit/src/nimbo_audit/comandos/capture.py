"""Subcomando `capture` (RF-03 / CU-02): registra evidencia con integridad.

Copia el archivo indicado a evidencia/ del engagement ACTIVO, calcula su
SHA-256 (por streaming, memoria acotada) y registra ruta + hash + marca de
tiempo en evidencia/index.json a través del repositorio.

Se construye SOBRE la arquitectura de 2A (Command + Repository): añade una clase
de comando nueva y depende de interfaces inyectadas (repositorio y función de
hash), no del FS directo.

Degradación graciosa (RNF-08 / CU-02 4a): si el cálculo del hash se interrumpe
por restricción de memoria, se traduce a `InterrupcionMemoriaError` (el CLI la
muestra como `[AVISO]`); nada se copia ni se escribe, porque el hash se calcula
ANTES de tocar el disco.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from nimbo_audit.comandos.base import Comando
from nimbo_audit.errores import (
    ArchivoNoAccesibleError,
    EngagementNoActivoError,
    InterrupcionMemoriaError,
)
from nimbo_audit.modelos.evidencia import Evidencia
from nimbo_audit.repositorio.engagement_repo import METADATA
from nimbo_audit.repositorio.evidencia_repo import RepositorioEvidencia
from nimbo_audit.servicios.hashing import calcular_sha256

Hasher = Callable[..., str]


def resolver_engagement_activo(inicio: Path, override: Path | None) -> Path:
    """Determina la raíz del engagement activo.

    - `override` (flag --dir): apunta directo a la raíz de un engagement; se
      exige que contenga su metadata.json.
    - Sin override: sube desde `inicio` (normalmente el cwd) hasta encontrar un
      directorio con metadata.json (el marcador del engagement).

    Lanza `EngagementNoActivoError` si no hay engagement por ninguna vía.
    """
    if override is not None:
        raiz = Path(override).resolve()
        if (raiz / METADATA).is_file():
            return raiz
        raise EngagementNoActivoError(
            f"El directorio indicado no es un engagement: {override}"
        )

    actual = Path(inicio).resolve()
    for candidato in (actual, *actual.parents):
        if (candidato / METADATA).is_file():
            return candidato
    raise EngagementNoActivoError(
        "No hay un engagement activo (ni en el directorio actual ni por --dir)."
    )


class ComandoCapture(Comando):
    """Registra un archivo de evidencia. Depende de interfaces, no del FS."""

    def __init__(
        self,
        archivo: Path,
        repo: RepositorioEvidencia,
        *,
        hasher: Hasher = calcular_sha256,
        ahora: datetime | None = None,
    ) -> None:
        self._archivo = Path(archivo)
        self._repo = repo
        self._hasher = hasher
        self._ahora = ahora

    def ejecutar(self) -> Evidencia:
        # CU-02 3a: si el archivo no existe/no accesible, abortar sin tocar nada.
        if not self._archivo.is_file():
            raise ArchivoNoAccesibleError(str(self._archivo))

        # El hash se calcula ANTES de copiar: si la memoria se agota aquí, el
        # engagement queda intacto (RNF-08).
        try:
            sha256 = self._hasher(self._archivo)
        except MemoryError as exc:
            raise InterrupcionMemoriaError(str(self._archivo)) from exc

        return self._repo.registrar(
            self._archivo, self._archivo.name, sha256, self._marca_temporal()
        )

    def _marca_temporal(self) -> str:
        momento = self._ahora or datetime.now(timezone.utc)
        return momento.isoformat(timespec="seconds")
