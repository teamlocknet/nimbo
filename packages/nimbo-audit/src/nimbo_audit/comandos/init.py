"""Subcomando `init` (RF-01 / CU-01): inicializa un engagement de auditoría.

Crea la estructura estandarizada (§4.3) y su metadata.json a través del
repositorio inyectado. No sobrescribe un engagement existente salvo --force.
"""

from __future__ import annotations

import getpass
import re
from datetime import datetime, timezone
from pathlib import Path

from nimbo_audit.comandos.base import Comando
from nimbo_audit.errores import EngagementExistenteError, NombreInvalidoError
from nimbo_audit.modelos.engagement import Engagement
from nimbo_audit.repositorio.engagement_repo import RepositorioEngagement

# Caracteres permitidos en el identificador del engagement: letras, dígitos,
# punto, guion y guion bajo. Rechaza separadores de ruta, espacios y control.
_NOMBRE_VALIDO = re.compile(r"^[A-Za-z0-9._-]+$")


class ComandoInit(Comando):
    """Crea un engagement nuevo. Depende de la interfaz de repositorio, no del FS."""

    def __init__(
        self,
        cliente: str,
        repo: RepositorioEngagement,
        *,
        force: bool = False,
        analista: str | None = None,
        ahora: datetime | None = None,
    ) -> None:
        self._cliente = cliente
        self._repo = repo
        self._force = force
        self._analista = analista
        self._ahora = ahora

    def ejecutar(self) -> Path:
        self._validar_nombre(self._cliente)

        if self._repo.existe(self._cliente):
            if not self._force:
                raise EngagementExistenteError(self._cliente)
            # --force: el borrado es responsabilidad del repo, que opera sobre el
            # Path ya resuelto y validado dentro de base_dir (no sobre el nombre crudo).
            self._repo.eliminar(self._cliente)

        engagement = Engagement(
            id=self._cliente,
            fecha_inicio=self._marca_temporal(),
            analista=self._analista or getpass.getuser(),
        )
        return self._repo.crear_estructura(engagement)

    @staticmethod
    def _validar_nombre(cliente: str) -> None:
        if cliente in (".", "..") or not _NOMBRE_VALIDO.match(cliente):
            raise NombreInvalidoError(cliente)

    def _marca_temporal(self) -> str:
        momento = self._ahora or datetime.now(timezone.utc)
        return momento.isoformat(timespec="seconds")
