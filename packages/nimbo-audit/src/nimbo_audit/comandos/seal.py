"""Subcomando `seal` (ADR-021): cierra el caso con una firma GPG y un ancla externa.

Solo sella un caso íntegro y deja de admitir cambios: `capture`, `report` e
`init --force` se niegan después.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from nimbo_audit.comandos.base import Comando
from nimbo_audit.comandos.verify import ComandoVerify
from nimbo_audit.errores import CasoSelladoError, SelloError
from nimbo_audit.repositorio.evidencia_repo import RepositorioEvidenciaJSON
from nimbo_audit.servicios.registro import RegistroCustodia, caso_sellado
from nimbo_audit.servicios.sello import comprobar_clave, sellar


@dataclass(frozen=True)
class ResultadoSello:
    ancla: str
    firmante: str


class ComandoSeal(Comando):
    def __init__(
        self,
        raiz: Path,
        repo: RepositorioEvidenciaJSON,
        clave: str,
        analista: str,
        *,
        ahora: datetime | None = None,
    ) -> None:
        self._raiz = Path(raiz)
        self._repo = repo
        self._clave = clave
        self._analista = analista
        self._ahora = ahora

    def ejecutar(self) -> ResultadoSello:
        if caso_sellado(self._raiz):
            raise CasoSelladoError("El caso ya está sellado: no admite cambios.")
        huella = comprobar_clave(self._clave)
        verificacion = ComandoVerify(self._raiz, self._repo.listar_validado).ejecutar()
        if not verificacion.integro:
            raise SelloError("el caso no está íntegro; ejecuta verify. No se selló nada.")
        RegistroCustodia(self._raiz, ahora=self._ahora).adoptar_si_falta(
            self._repo.listar_validado(), self._analista
        )
        ancla = sellar(self._raiz, huella, self._analista, ahora=self._ahora)
        return ResultadoSello(ancla, huella)
