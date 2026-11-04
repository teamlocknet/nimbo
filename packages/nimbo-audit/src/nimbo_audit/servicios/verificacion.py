"""Clasificacion de integridad compartida por report y verify (RF-AUD-03/04)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

from nimbo_audit.errores import CasoInvalidoError
from nimbo_audit.modelos.evidencia import Evidencia
from nimbo_audit.servicios.hashing import calcular_sha256

OK = "OK"
MODIFICADO = "MODIFICADO"
AUSENTE = "AUSENTE"
Hasher = Callable[..., str]


@dataclass(frozen=True)
class EvidenciaVerificada:
    evidencia: Evidencia
    estado: str
    detalle: str = ""


def verificar_evidencia(
    raiz: Path, evidencia: Evidencia, *, hasher: Hasher = calcular_sha256
) -> EvidenciaVerificada:
    """Conserva la comparacion y estados existentes de report."""
    archivo = raiz / evidencia.ruta
    if not archivo.is_file():
        return EvidenciaVerificada(evidencia, AUSENTE)
    actual = hasher(archivo)
    return EvidenciaVerificada(
        evidencia, OK if actual == evidencia.sha256 else MODIFICADO
    )


def resumir(verificadas: Sequence[EvidenciaVerificada]) -> dict[str, int]:
    resumen = {OK: 0, MODIFICADO: 0, AUSENTE: 0}
    for verificada in verificadas:
        resumen[verificada.estado] += 1
    return resumen


def ruta_interna(raiz: Path, ruta: str) -> Path:
    """Validacion adicional de verify; no cambia la politica de report."""
    relativa = Path(ruta)
    if relativa.is_absolute() or ".." in relativa.parts:
        raise CasoInvalidoError(f"Ruta fuera del caso: {ruta!r}")
    try:
        destino = (raiz / relativa).resolve()
        if not destino.is_relative_to(raiz.resolve()):
            raise CasoInvalidoError(f"Ruta fuera del caso: {ruta!r}")
    except (OSError, RuntimeError, ValueError) as exc:
        raise CasoInvalidoError(f"No se puede resolver la ruta: {ruta!r}") from exc
    return destino
