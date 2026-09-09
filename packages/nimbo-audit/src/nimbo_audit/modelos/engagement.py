"""Modelo del engagement (ERS RF-01, §4.3 del maestro).

Dataclass pura: representa los datos, no sabe nada de rutas ni de archivos.
La serialización a metadata.json vive en el repositorio (patrón Repository),
no aquí, para poder migrar JSON -> SQLite sin tocar el modelo ni los comandos.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Engagement:
    """Un engagement de auditoría recién iniciado.

    Campos de metadata.json según §4.3: identificador, fecha/hora de inicio y
    analista (usuario del sistema).
    """

    id: str
    fecha_inicio: str  # ISO-8601 (UTC), p. ej. "2026-09-08T14:30:00+00:00"
    analista: str
