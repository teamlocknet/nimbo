"""Subcomando `report` (RF-04 / CU-03): reporte consolidado del engagement.

Cierra el ciclo del CLI (init -> capture -> report). Se construye SOBRE la
arquitectura de 2A/2B: una clase de comando nueva que orquesta interfaces ya
existentes (repos de engagement y evidencia + el hashing por streaming de 2B),
sin acoplarse al formato de almacenamiento.

Valor probatorio (opción a): al consolidar, `report` RECOMPUTA el SHA-256 de
cada archivo de evidencia y lo compara con el hash ancla del índice, marcando en
el reporte el estado de integridad:
  - OK          : el hash recomputado coincide con el del índice.
  - MODIFICADO  : el archivo existe pero su hash cambió (evidencia alterada).
  - AUSENTE     : el archivo del índice ya no está en disco.

El `.md` resultante es determinista (el render no usa reloj de pared): mismo
engagement -> mismo texto.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from nimbo_audit.comandos.base import Comando
from nimbo_audit.modelos.evidencia import Evidencia
from nimbo_audit.repositorio.engagement_repo import RepositorioEngagement
from nimbo_audit.repositorio.evidencia_repo import RepositorioEvidencia
from nimbo_audit.servicios.hashing import calcular_sha256
from nimbo_audit.servicios.reporte import renderizar_reporte

# Reexportados para conservar los imports de los consumidores existentes.
from nimbo_audit.servicios.verificacion import (
    AUSENTE,
    MODIFICADO,
    OK,
    EvidenciaVerificada,
    Hasher,
    resumir,
    verificar_evidencia,
)

REPORTES = "reportes"
LOGS = "logs"


@dataclass(frozen=True)
class ResultadoReporte:
    """Resultado de generar el reporte: ruta del `.md` y resumen de integridad."""

    ruta_md: Path
    nombre: str
    resumen: dict[str, int]


class ComandoReport(Comando):
    """Genera el reporte consolidado. Depende de interfaces, no del FS directo."""

    def __init__(
        self,
        raiz: Path,
        engagement_repo: RepositorioEngagement,
        evidencia_repo: RepositorioEvidencia,
        *,
        hasher: Hasher = calcular_sha256,
    ) -> None:
        self._raiz = Path(raiz)
        self._engagement_repo = engagement_repo
        self._evidencia_repo = evidencia_repo
        self._hasher = hasher
        self._id = self._raiz.name

    # --- recopilación --------------------------------------------------------

    def tiene_datos(self) -> bool:
        """¿El engagement tiene evidencia o algún registro de sesión? (CU-03 1a)."""
        return bool(self._evidencia_repo.listar()) or bool(self._registros_sesion())

    def _registros_sesion(self) -> list[str]:
        """Nombres de los registros de sesión en logs/ (tolera su ausencia).

        RF-02 (registro de sesión) aún no existe; `report` solo CONSUME el log si
        está presente. No hay repositorio de sesión todavía, así que se lista el
        directorio directamente, ordenado para un reporte determinista.
        """
        logs = self._raiz / LOGS
        if not logs.is_dir():
            return []
        return sorted(p.name for p in logs.iterdir() if p.is_file())

    def _verificar(self, evidencia: Evidencia) -> EvidenciaVerificada:
        return verificar_evidencia(self._raiz, evidencia, hasher=self._hasher)

    # --- ejecución -----------------------------------------------------------

    def ejecutar(self) -> ResultadoReporte:
        engagement = self._engagement_repo.cargar(self._id)
        verificadas = [self._verificar(e) for e in self._evidencia_repo.listar()]
        sesion = self._registros_sesion()

        contenido = renderizar_reporte(engagement, verificadas, sesion)

        nombre = f"reporte-{self._id}.md"
        destino = self._raiz / REPORTES / nombre
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(contenido, encoding="utf-8")

        return ResultadoReporte(
            ruta_md=destino,
            nombre=nombre,
            resumen=self._resumen(verificadas),
        )

    @staticmethod
    def _resumen(verificadas: list[EvidenciaVerificada]) -> dict[str, int]:
        return resumir(verificadas)
