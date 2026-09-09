"""Tests de `nimbo-audit init` (RF-01 / CU-01).

Rápidos y herméticos: usan tmp_path como directorio base, nunca el home real.
Incluyen los flujos OK y duplicado, la validación anti path-traversal y — punto
crítico — que --force jamás borre nada fuera del directorio base.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from typer.testing import CliRunner

from nimbo_audit.cli import app
from nimbo_audit.comandos.init import ComandoInit
from nimbo_audit.errores import EngagementExistenteError, NombreInvalidoError
from nimbo_audit.repositorio.engagement_repo import (
    SUBDIRS,
    RepositorioEngagementJSON,
)

FECHA_FIJA = datetime(2026, 9, 8, 12, 0, 0, tzinfo=timezone.utc)


def _repo(base: Path) -> RepositorioEngagementJSON:
    return RepositorioEngagementJSON(base)


# --- Flujo de éxito (CU-01 flujo principal) ---------------------------------


def test_init_ok_crea_estructura_y_metadata(tmp_path: Path) -> None:
    ruta = ComandoInit(
        "acme", _repo(tmp_path), analista="tester", ahora=FECHA_FIJA
    ).ejecutar()

    assert ruta == tmp_path / "acme"
    for sub in SUBDIRS:
        assert (ruta / sub).is_dir(), f"falta el subdirectorio {sub}"

    metadata = json.loads((ruta / "metadata.json").read_text(encoding="utf-8"))
    assert metadata == {
        "id": "acme",
        "fecha_inicio": "2026-09-08T12:00:00+00:00",
        "analista": "tester",
    }


# --- Flujo alternativo: duplicado (CU-01 2a) --------------------------------


def test_init_duplicado_no_sobrescribe(tmp_path: Path) -> None:
    ComandoInit("acme", _repo(tmp_path), analista="a", ahora=FECHA_FIJA).ejecutar()
    marcador = tmp_path / "acme" / "notas" / "previo.txt"
    marcador.write_text("evidencia previa", encoding="utf-8")

    with pytest.raises(EngagementExistenteError):
        ComandoInit("acme", _repo(tmp_path), analista="b").ejecutar()

    # No se tocó nada de lo existente.
    assert marcador.read_text(encoding="utf-8") == "evidencia previa"


def test_force_reinicializa(tmp_path: Path) -> None:
    ComandoInit("acme", _repo(tmp_path), analista="a", ahora=FECHA_FIJA).ejecutar()
    marcador = tmp_path / "acme" / "notas" / "previo.txt"
    marcador.write_text("se irá con --force", encoding="utf-8")

    ruta = ComandoInit(
        "acme", _repo(tmp_path), force=True, analista="b", ahora=FECHA_FIJA
    ).ejecutar()

    assert not marcador.exists()  # el árbol se recreó limpio
    assert (ruta / "metadata.json").is_file()


# --- Validación de nombre (anti path-traversal) -----------------------------


@pytest.mark.parametrize(
    "nombre", ["../evil", "a/b", "..", ".", "", "con espacio", "na;me", "x\\y"]
)
def test_nombre_invalido(tmp_path: Path, nombre: str) -> None:
    with pytest.raises(NombreInvalidoError):
        ComandoInit(nombre, _repo(tmp_path)).ejecutar()


# --- Seguridad: --force nunca borra fuera del directorio base ----------------


def test_force_traversal_no_borra_fuera_del_base(tmp_path: Path) -> None:
    base = tmp_path / "base"
    base.mkdir()
    externo = tmp_path / "externo"
    externo.mkdir()
    intocable = externo / "evidencia_previa.txt"
    intocable.write_text("NO TOCAR", encoding="utf-8")

    # El comando valida el nombre antes de cualquier borrado -> traversal rechazado.
    with pytest.raises(NombreInvalidoError):
        ComandoInit("../externo", _repo(base), force=True).ejecutar()

    assert externo.is_dir()
    assert intocable.read_text(encoding="utf-8") == "NO TOCAR"


@pytest.mark.parametrize("nombre", ["../externo", "..", "a/b", "sub/../../externo"])
def test_repo_eliminar_rechaza_rutas_fuera_del_base(tmp_path: Path, nombre: str) -> None:
    # Cinturón y tirantes en la capa de repositorio (independiente del comando):
    # eliminar() nunca opera sobre un nombre crudo que escape del base_dir.
    base = tmp_path / "base"
    base.mkdir()
    externo = tmp_path / "externo"
    externo.mkdir()
    intocable = externo / "evidencia_previa.txt"
    intocable.write_text("NO TOCAR", encoding="utf-8")

    with pytest.raises(NombreInvalidoError):
        _repo(base).eliminar(nombre)

    assert externo.is_dir()
    assert intocable.read_text(encoding="utf-8") == "NO TOCAR"


# --- CLI: mensajes exactos [OK] / [ERROR] -----------------------------------


def test_cli_ok(tmp_path: Path) -> None:
    res = CliRunner().invoke(app, ["init", "acme", "--dir", str(tmp_path)])
    assert res.exit_code == 0
    assert "[OK] Engagement 'acme' inicializado en" in res.stdout
    assert (tmp_path / "acme" / "metadata.json").is_file()


def test_cli_duplicado(tmp_path: Path) -> None:
    runner = CliRunner()
    runner.invoke(app, ["init", "acme", "--dir", str(tmp_path)])
    res = runner.invoke(app, ["init", "acme", "--dir", str(tmp_path)])
    assert res.exit_code == 1
    assert "[ERROR] Ya existe un engagement con este nombre" in res.stderr


def test_cli_nombre_invalido(tmp_path: Path) -> None:
    res = CliRunner().invoke(app, ["init", "a/b", "--dir", str(tmp_path)])
    assert res.exit_code == 1
    assert "[ERROR] Nombre no válido" in res.stderr
