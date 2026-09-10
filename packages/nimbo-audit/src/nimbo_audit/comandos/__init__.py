"""Comandos del CLI (patrón Command): una clase modular por subcomando.

`init` (2A), `capture` (2B) y `report` (2C) son clases que implementan `Comando`,
añadidas sin tocar el núcleo (cli.py) más allá del cableado.
"""

from nimbo_audit.comandos.base import Comando
from nimbo_audit.comandos.capture import ComandoCapture
from nimbo_audit.comandos.init import ComandoInit
from nimbo_audit.comandos.report import ComandoReport

__all__ = ["Comando", "ComandoInit", "ComandoCapture", "ComandoReport"]
