"""Interfaz común de los comandos (patrón Command).

Cada subcomando es una clase que encapsula su lógica y expone `ejecutar()`.
`cli.py` solo instancia el comando y llama a `ejecutar()`; así, añadir capture
o report no obliga a tocar el núcleo del CLI.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Comando(ABC):
    """Contrato de un subcomando ejecutable."""

    @abstractmethod
    def ejecutar(self) -> Any:
        """Realiza la acción del subcomando. Lanza NimboAuditError en fallos esperados."""
