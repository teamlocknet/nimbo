"""Repositorio de engagements (metadata.json).

Abstrae el acceso al FS detrás de una interfaz. `init` escribe metadata.json
SOLO a través de este repositorio (nunca con open() directo desde el comando),
para permitir migrar JSON -> SQLite sin reescribir la lógica.

Seguridad (evidencia de auditoría): toda ruta de un engagement se RESUELVE y se
valida que quede ESTRICTAMENTE DENTRO del base_dir esperado antes de crear o —
sobre todo— de borrar nada. El borrado de --force nunca se construye con el
nombre crudo: opera sobre el Path ya resuelto y confirmado dentro de base_dir.
"""

from __future__ import annotations

import json
import shutil
from abc import ABC, abstractmethod
from pathlib import Path

from nimbo_audit.errores import NombreInvalidoError
from nimbo_audit.modelos.engagement import Engagement

# Subdirectorios estándar del engagement (§4.3). `evidencia/index.json` lo
# llena `capture` (2B); `init` solo deja la carpeta creada.
SUBDIRS = ("evidencia", "logs", "reportes", "notas")
METADATA = "metadata.json"


class RepositorioEngagement(ABC):
    """Interfaz de persistencia de engagements (patrón Repository)."""

    @abstractmethod
    def existe(self, engagement_id: str) -> bool: ...

    @abstractmethod
    def crear_estructura(self, engagement: Engagement) -> Path:
        """Crea el árbol del engagement y persiste su metadata. Devuelve la ruta raíz."""

    @abstractmethod
    def eliminar(self, engagement_id: str) -> None:
        """Borra un engagement existente (uso destructivo de --force)."""

    @abstractmethod
    def ruta(self, engagement_id: str) -> Path:
        """Ruta raíz (resuelta y validada dentro de base_dir) de un engagement."""


class RepositorioEngagementJSON(RepositorioEngagement):
    """Implementación sobre el FS con metadata en JSON determinista."""

    def __init__(self, base_dir: Path) -> None:
        self._base = Path(base_dir)

    def _base_resuelto(self) -> Path:
        return self._base.resolve()

    def _resolver_dentro(self, engagement_id: str) -> Path:
        """Resuelve la ruta del engagement y confirma que cuelga DIRECTAMENTE de base_dir.

        Cinturón y tirantes frente a path traversal: aunque el nombre ya se valide
        en el comando, aquí se exige que el padre de la ruta resuelta sea exactamente
        base_dir. Un `..` o un separador desplazarían el padre y se rechazan.
        """
        base = self._base_resuelto()
        candidato = (self._base / engagement_id).resolve()
        if candidato == base or candidato.parent != base:
            raise NombreInvalidoError(
                f"Ruta de engagement fuera del directorio base: {engagement_id!r}"
            )
        return candidato

    def ruta(self, engagement_id: str) -> Path:
        return self._resolver_dentro(engagement_id)

    def existe(self, engagement_id: str) -> bool:
        return self._resolver_dentro(engagement_id).is_dir()

    def crear_estructura(self, engagement: Engagement) -> Path:
        raiz = self._resolver_dentro(engagement.id)
        for sub in SUBDIRS:
            (raiz / sub).mkdir(parents=True, exist_ok=True)
        self._guardar_metadata(raiz, engagement)
        return raiz

    def eliminar(self, engagement_id: str) -> None:
        # Borrado quirúrgico: sobre el Path YA resuelto y confirmado dentro de
        # base_dir, nunca sobre el nombre crudo.
        objetivo = self._resolver_dentro(engagement_id)
        if objetivo.is_dir():
            shutil.rmtree(objetivo)

    def _guardar_metadata(self, raiz: Path, engagement: Engagement) -> None:
        datos = {
            "id": engagement.id,
            "fecha_inicio": engagement.fecha_inicio,
            "analista": engagement.analista,
        }
        # JSON determinista (claves ordenadas, indentado, newline final): coherente
        # con el principio de reproducibilidad y fácil de diffear.
        texto = json.dumps(datos, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        (raiz / METADATA).write_text(texto, encoding="utf-8")
