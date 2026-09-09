"""Comandos del CLI (patrón Command): una clase modular por subcomando.

Hoy solo existe `init` (2A). `capture` (2B) y `report` (2C) se añadirán como
clases nuevas que implementan `Comando`, sin tocar el núcleo (cli.py).
"""

from nimbo_audit.comandos.base import Comando
from nimbo_audit.comandos.init import ComandoInit

__all__ = ["Comando", "ComandoInit"]
