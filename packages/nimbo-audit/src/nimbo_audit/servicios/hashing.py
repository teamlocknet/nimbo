"""Servicio de hashing SHA-256 por streaming.

Lee el archivo por bloques (chunks) en lugar de cargarlo entero en RAM: el
consumo de memoria queda acotado por diseño, coherente con el target de hardware
limitado. El comando `capture` inyecta esta función (como `init` inyecta el
repositorio), lo que permite simular fallos de memoria en los tests.

Si el sistema no puede sostener ni un bloque en memoria (OOM Killer /
`MemoryError`), la excepción se propaga tal cual: es `capture` quien la traduce
a una degradación graciosa (`[AVISO]`, RNF-08), no este servicio.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

# 64 KiB: equilibrio entre número de lecturas y memoria residente por chunk.
CHUNK_POR_DEFECTO = 64 * 1024


def calcular_sha256(ruta: Path, *, chunk_size: int = CHUNK_POR_DEFECTO) -> str:
    """SHA-256 hexadecimal del archivo, leído en bloques de `chunk_size` bytes."""
    digest = hashlib.sha256()
    with open(ruta, "rb") as fh:
        for bloque in iter(lambda: fh.read(chunk_size), b""):
            digest.update(bloque)
    return digest.hexdigest()
