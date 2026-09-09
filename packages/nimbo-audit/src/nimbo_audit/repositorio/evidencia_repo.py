"""Repositorio de evidencia (`evidencia/index.json`).

Abstrae el acceso al FS detrás de una interfaz (patrón Repository), como el de
engagement en 2A. El comando `capture` nunca hace `open()` sobre el índice: todo
pasa por aquí, para poder migrar JSON -> SQLite sin reescribir el comando.

Reglas de integridad (Casos de Uso §4):
- Nada se sobrescribe en silencio: registrar dos veces el mismo nombre —o pisar
  un archivo ya presente en evidencia/— se rechaza con `EvidenciaDuplicadaError`.
- El índice se escribe de forma atómica (temporal + `os.replace`): nunca queda a
  medio escribir si algo revienta.
- Si la actualización del índice falla tras copiar el archivo, se revierte la
  copia (rollback): el engagement no queda con un archivo huérfano.
- JSON determinista (claves ordenadas + newline final) como en 2A: diffeable y
  coherente con el principio de reproducibilidad.
"""

from __future__ import annotations

import json
import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path

from nimbo_audit.errores import EvidenciaDuplicadaError
from nimbo_audit.modelos.evidencia import Evidencia

INDEX = "index.json"
EVIDENCIA = "evidencia"
VERSION_INDEX = 1


class RepositorioEvidencia(ABC):
    """Interfaz de persistencia de evidencia de un engagement."""

    @abstractmethod
    def existe(self, nombre: str) -> bool:
        """¿Ya hay una evidencia registrada con ese nombre?"""

    @abstractmethod
    def listar(self) -> list[Evidencia]:
        """Evidencias registradas, en orden cronológico de captura."""

    @abstractmethod
    def registrar(self, origen: Path, nombre: str, sha256: str, timestamp: str) -> Evidencia:
        """Copia `origen` a evidencia/<nombre> y añade su registro al índice.

        Operación con integridad: rechaza duplicados, escribe el índice de forma
        atómica y revierte la copia si el índice no se pudo actualizar.
        """


class RepositorioEvidenciaJSON(RepositorioEvidencia):
    """Implementación sobre el FS con el índice en JSON determinista."""

    def __init__(self, engagement_root: Path) -> None:
        self._root = Path(engagement_root)
        self._dir = self._root / EVIDENCIA
        self._index = self._dir / INDEX

    # --- lectura -------------------------------------------------------------

    def _cargar(self) -> list[Evidencia]:
        if not self._index.is_file():
            return []
        datos = json.loads(self._index.read_text(encoding="utf-8"))
        return [Evidencia(**e) for e in datos.get("evidencias", [])]

    def listar(self) -> list[Evidencia]:
        return self._cargar()

    def existe(self, nombre: str) -> bool:
        return any(e.nombre == nombre for e in self._cargar())

    # --- escritura -----------------------------------------------------------

    def registrar(self, origen: Path, nombre: str, sha256: str, timestamp: str) -> Evidencia:
        destino = self._dir / nombre
        # Integridad: ni un registro previo ni un archivo ya presente se pisan.
        if self.existe(nombre) or destino.exists():
            raise EvidenciaDuplicadaError(nombre)

        self._dir.mkdir(parents=True, exist_ok=True)
        evidencia = Evidencia(
            nombre=nombre,
            ruta=f"{EVIDENCIA}/{nombre}",
            sha256=sha256,
            timestamp=timestamp,
        )

        shutil.copy2(origen, destino)
        try:
            self._guardar(self._cargar() + [evidencia])
        except OSError:
            # Rollback: no dejar un archivo huérfano si el índice no se actualizó.
            destino.unlink(missing_ok=True)
            raise
        return evidencia

    def _guardar(self, evidencias: list[Evidencia]) -> None:
        datos = {
            "version": VERSION_INDEX,
            "evidencias": [
                {
                    "nombre": e.nombre,
                    "ruta": e.ruta,
                    "sha256": e.sha256,
                    "timestamp": e.timestamp,
                }
                for e in evidencias
            ],
        }
        texto = json.dumps(datos, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        # Escritura atómica: temporal en el mismo directorio + rename.
        tmp = self._index.with_suffix(".json.tmp")
        tmp.write_text(texto, encoding="utf-8")
        os.replace(tmp, self._index)
