"""Fixtures compartidas de los tests de nimbo-audit."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner() -> CliRunner:
    """CliRunner con stderr separado de stdout, en click 8.1 y en click 8.2+.

    - click 8.1 (bookworm, ADR-005 — el entorno del producto) mezcla stderr en
      stdout salvo que se pida `mix_stderr=False`; sin eso, `res.stderr` lanza
      "ValueError: stderr not separately captured".
    - click 8.2 quitó ese argumento (stderr ya va siempre aparte) y pasarlo da
      TypeError — es lo que pasa en el venv local con Python/Typer recientes.
    """
    try:
        return CliRunner(mix_stderr=False)
    except TypeError:
        return CliRunner()
