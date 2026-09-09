"""Repositorios (patrón Repository): abstraen el sistema de archivos.

Hoy la persistencia es JSON sobre el FS; mañana podría ser SQLite. Los comandos
dependen de la interfaz abstracta, no de la implementación, así que esa migración
no obliga a reescribir la lógica de los comandos.
"""

from nimbo_audit.repositorio.engagement_repo import (
    RepositorioEngagement,
    RepositorioEngagementJSON,
)

__all__ = ["RepositorioEngagement", "RepositorioEngagementJSON"]
