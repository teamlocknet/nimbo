"""RF-AUD-04 / HU-13: comprobar un caso sin escribir en el."""
from __future__ import annotations

import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Callable

from nimbo_audit.comandos.base import Comando
from nimbo_audit.errores import CasoInvalidoError
from nimbo_audit.modelos.evidencia import Evidencia
from nimbo_audit.servicios.hashing import calcular_sha256
from nimbo_audit.servicios.verificacion import (
    MODIFICADO,
    EvidenciaVerificada,
    Hasher,
    resumir,
    ruta_interna,
    verificar_evidencia,
)


@dataclass(frozen=True)
class ResultadoVerificacion:
    evidencias: list[EvidenciaVerificada]
    resumen: dict[str, int]

    @property
    def integro(self) -> bool:
        return not (self.resumen["MODIFICADO"] or self.resumen["AUSENTE"])


class ComandoVerify(Comando):
    def __init__(
        self,
        raiz: Path,
        cargar_evidencias: Callable[[], list[Evidencia]],
        *,
        hasher: Hasher = calcular_sha256,
    ) -> None:
        self._raiz = raiz
        self._cargar = cargar_evidencias
        self._hasher = hasher

    def ejecutar(self) -> ResultadoVerificacion:
        ruta_interna(self._raiz, "metadata.json")
        verificadas = []
        for evidencia in self._cargar():
            ruta_interna(self._raiz, evidencia.ruta)
            if not re.fullmatch(r"[0-9a-fA-F]{64}", evidencia.sha256):
                verificadas.append(EvidenciaVerificada(
                    evidencia, MODIFICADO, "SHA-256 invalido en el indice"
                ))
                continue
            try:
                resultado = verificar_evidencia(
                    self._raiz,
                    replace(evidencia, sha256=evidencia.sha256.lower()),
                    hasher=self._hasher,
                )
            except OSError as exc:
                raise CasoInvalidoError(
                    f"No se pudo leer la evidencia {evidencia.nombre!r}."
                ) from exc
            verificadas.append(resultado)
        return ResultadoVerificacion(verificadas, resumir(verificadas))
