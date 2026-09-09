"""Modelo de una evidencia registrada (ERS RF-03, §4.3 del maestro).

Dataclass pura: representa el registro de un archivo de evidencia, no sabe nada
de FS ni de JSON. La serialización a `evidencia/index.json` vive en el
repositorio (patrón Repository), para poder migrar JSON -> SQLite sin tocar el
modelo ni el comando.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Evidencia:
    """Un archivo de evidencia copiado al engagement y anclado por su hash.

    `sha256` es el ancla de integridad: cualquier modificación posterior del
    archivo se detecta recomputando el hash y comparándolo con este valor.
    """

    nombre: str  # nombre del archivo dentro de evidencia/
    ruta: str  # ruta relativa a la raíz del engagement, p. ej. "evidencia/x.pcap"
    sha256: str  # digest hexadecimal (64 caracteres)
    timestamp: str  # ISO-8601 (UTC) del momento del registro
