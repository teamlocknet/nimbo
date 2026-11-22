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
from nimbo_audit.servicios.registro import ROTO, EstadoRegistro, RegistroCustodia
from nimbo_audit.servicios.sello import EstadoSello, comprobar_sello
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
    no_registrados: tuple[str, ...]
    registro: EstadoRegistro
    sello: EstadoSello

    @property
    def integro(self) -> bool:
        return not (
            self.resumen["MODIFICADO"]
            or self.resumen["AUSENTE"]
            or self.no_registrados
            or self.registro.estado == ROTO
            or self.sello.estado == ROTO
        )


class ComandoVerify(Comando):
    def __init__(
        self,
        raiz: Path,
        cargar_evidencias: Callable[[], list[Evidencia]],
        *,
        hasher: Hasher = calcular_sha256,
        ancla: str | None = None,
        huella: str | None = None,
    ) -> None:
        self._raiz = raiz
        self._cargar = cargar_evidencias
        self._hasher = hasher
        self._ancla = ancla
        self._huella = huella

    def _no_registrados(self, evidencias: list[Evidencia]) -> tuple[str, ...]:
        carpeta = self._raiz / "evidencia"
        conocidos = {e.nombre for e in evidencias} | {"index.json"}
        return tuple(sorted(p.name for p in carpeta.iterdir() if p.name not in conocidos))

    def ejecutar(self) -> ResultadoVerificacion:
        ruta_interna(self._raiz, "metadata.json")
        evidencias = self._cargar()
        verificadas = []
        for evidencia in evidencias:
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
        return ResultadoVerificacion(
            verificadas,
            resumir(verificadas),
            self._no_registrados(evidencias),
            RegistroCustodia(self._raiz).comprobar(evidencias),
            comprobar_sello(self._raiz, ancla=self._ancla, huella=self._huella),
        )
