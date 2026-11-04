"""RF-AUD-04 / HU-13: verificacion independiente del caso."""
import builtins
import hashlib
import json
import os
from pathlib import Path

import pytest

from nimbo_audit.cli import app
from nimbo_audit.comandos.init import ComandoInit
from nimbo_audit.comandos.capture import ComandoCapture
from nimbo_audit.repositorio.engagement_repo import RepositorioEngagementJSON
from nimbo_audit.repositorio.evidencia_repo import RepositorioEvidenciaJSON


def test_verify_caso_integro(tmp_path: Path, cli_runner) -> None:
    raiz = ComandoInit("acme", RepositorioEngagementJSON(tmp_path)).ejecutar()
    origen = tmp_path / "captura.txt"
    origen.write_bytes(b"evidencia intacta")
    ComandoCapture(origen, RepositorioEvidenciaJSON(raiz)).ejecutar()

    resultado = cli_runner.invoke(app, ["verify", str(raiz)])

    assert resultado.exit_code == 0, resultado.output
    assert "captura.txt" in resultado.stdout
    assert "OK" in resultado.stdout


def _caso(tmp_path):
    raiz = ComandoInit("caso", RepositorioEngagementJSON(tmp_path)).ejecutar()
    for nombre, contenido in [("uno.bin", b"ABC"), ("dos.bin", b"DEF")]:
        origen = tmp_path / nombre
        origen.write_bytes(contenido)
        ComandoCapture(origen, RepositorioEvidenciaJSON(raiz)).ejecutar()
    (raiz / "notas" / "nota.txt").write_bytes(b"nota previa")
    (raiz / "logs" / "previo.log").write_bytes(b"log previo")
    (raiz / "reportes" / "previo.md").write_bytes(b"informe previo")
    return raiz


def _indice(raiz):
    return raiz / "evidencia" / "index.json"


def _editar_indice(raiz, modificar):
    archivo = _indice(raiz)
    datos = json.loads(archivo.read_text())
    modificar(datos)
    archivo.write_text(json.dumps(datos))


def _manifiesto(raiz):
    """Rutas, tipos, permisos, mtime y SHA de TODO el caso; excluye atime."""
    entradas = []
    for archivo in [raiz, *sorted(raiz.rglob("*"))]:
        meta = archivo.lstat()
        ruta = str(archivo.relative_to(raiz))
        contenido = (
            os.readlink(archivo) if archivo.is_symlink()
            else hashlib.sha256(archivo.read_bytes()).hexdigest()
            if archivo.is_file() else None
        )
        entradas.append((ruta, meta.st_mode, meta.st_mtime_ns, contenido))
    return entradas


@pytest.mark.parametrize("estado", ["intacto", "byte", "borrado", "hash"])
def test_verify_estados_y_no_modifica_caso(tmp_path, cli_runner, estado):
    raiz = _caso(tmp_path)
    if estado == "byte":
        # Misma longitud: exactamente un byte alterado.
        (raiz / "evidencia" / "uno.bin").write_bytes(b"AXC")
    elif estado == "borrado":
        (raiz / "evidencia" / "uno.bin").unlink()
    elif estado == "hash":
        _editar_indice(raiz, lambda d: d["evidencias"][0].update(sha256="no-es-sha"))
    antes = _manifiesto(raiz)

    resultado = cli_runner.invoke(app, ["verify", str(raiz)])

    assert resultado.exit_code == (0 if estado == "intacto" else 1)
    assert _manifiesto(raiz) == antes
    assert "OK: dos.bin" in resultado.stdout
    assert "Resumen:" in resultado.stdout
    if estado == "intacto":
        assert "Resumen: 2 OK, 0 MODIFICADO, 0 AUSENTE" in resultado.stdout
    elif estado == "borrado":
        assert "AUSENTE: uno.bin" in resultado.stdout
    else:
        assert "MODIFICADO: uno.bin" in resultado.stdout
    if estado == "hash":
        assert "SHA-256 invalido" in resultado.stdout


def test_verify_caso_activo_desde_subdirectorio(tmp_path, cli_runner, monkeypatch):
    raiz = _caso(tmp_path)
    monkeypatch.chdir(raiz / "notas")
    resultado = cli_runner.invoke(app, ["verify"])
    assert resultado.exit_code == 0
    assert "2 OK" in resultado.stdout


def test_verify_ruta_explicita_prevalece_sobre_caso_activo(tmp_path, cli_runner, monkeypatch):
    raiz = _caso(tmp_path)
    otro = ComandoInit("otro", RepositorioEngagementJSON(tmp_path)).ejecutar()
    monkeypatch.chdir(otro)
    resultado = cli_runner.invoke(app, ["verify", str(raiz)])
    assert resultado.exit_code == 0
    assert "2 OK" in resultado.stdout


def test_verify_ruta_relativa(tmp_path, cli_runner, monkeypatch):
    raiz = _caso(tmp_path)
    monkeypatch.chdir(tmp_path)
    resultado = cli_runner.invoke(app, ["verify", raiz.name])
    assert resultado.exit_code == 0


def test_verify_caso_copiado_con_otro_nombre(tmp_path, cli_runner):
    raiz = _caso(tmp_path)
    nuevo = raiz.rename(tmp_path / "copia-del-cliente")
    resultado = cli_runner.invoke(app, ["verify", str(nuevo)])
    assert resultado.exit_code == 0


def test_verify_sin_caso(tmp_path, cli_runner, monkeypatch):
    monkeypatch.chdir(tmp_path)
    resultado = cli_runner.invoke(app, ["verify"])
    assert resultado.exit_code == 1
    assert "[ERROR]" in resultado.stderr


@pytest.mark.parametrize("tipo", ["sin-metadata", "ruta-inexistente", "archivo"])
def test_verify_ruta_no_es_caso(tmp_path, cli_runner, tipo):
    destino = tmp_path / "destino"
    if tipo == "sin-metadata":
        destino.mkdir()
    elif tipo == "archivo":
        destino.write_bytes(b"no es caso")
    resultado = cli_runner.invoke(app, ["verify", str(destino)])
    assert resultado.exit_code == 1
    assert "[ERROR]" in resultado.stderr


@pytest.mark.parametrize("texto", [
    "{", "[]", "null", "{}", '{"version":1}',
    '{"version":2,"evidencias":[]}',
    '{"version":true,"evidencias":[]}',
    '{"version":1,"evidencias":{}}',
    '{"version":1,"evidencias":[{}]}',
    '{"version":1,"evidencias":[null]}',
])
def test_verify_indice_invalido_falla_sin_cambios(tmp_path, cli_runner, texto):
    raiz = _caso(tmp_path)
    _indice(raiz).write_text(texto)
    antes = _manifiesto(raiz)
    resultado = cli_runner.invoke(app, ["verify", str(raiz)])
    assert resultado.exit_code == 1
    assert "[ERROR]" in resultado.stderr
    assert "Traceback" not in resultado.output + resultado.stderr
    assert _manifiesto(raiz) == antes


def test_verify_indice_ausente_no_es_caso_integro(tmp_path, cli_runner):
    raiz = _caso(tmp_path)
    _indice(raiz).unlink()
    antes = _manifiesto(raiz)
    resultado = cli_runner.invoke(app, ["verify", str(raiz)])
    assert resultado.exit_code == 1
    assert "index.json" in resultado.stderr
    assert _manifiesto(raiz) == antes


def test_verify_indice_vacio_valido(tmp_path, cli_runner):
    raiz = _caso(tmp_path)
    _editar_indice(raiz, lambda d: d.update(evidencias=[]))
    resultado = cli_runner.invoke(app, ["verify", str(raiz)])
    assert resultado.exit_code == 0
    assert "Resumen: 0 OK, 0 MODIFICADO, 0 AUSENTE" in resultado.stdout


@pytest.mark.parametrize("hash_invalido", ["", "a"*63, "a"*65, "z"*64, "a"*63+"\n"])
def test_verify_hash_mal_formado_nombra_evidencia(tmp_path, cli_runner, hash_invalido):
    raiz = _caso(tmp_path)
    _editar_indice(raiz, lambda d: d["evidencias"][0].update(sha256=hash_invalido))
    resultado = cli_runner.invoke(app, ["verify", str(raiz)])
    assert resultado.exit_code == 1
    assert "MODIFICADO: uno.bin" in resultado.stdout


def test_verify_hash_hexadecimal_mayusculas_valido(tmp_path, cli_runner):
    raiz = _caso(tmp_path)
    _editar_indice(raiz, lambda d: d["evidencias"][0].update(
        sha256=d["evidencias"][0]["sha256"].upper()
    ))
    resultado = cli_runner.invoke(app, ["verify", str(raiz)])
    assert resultado.exit_code == 0


@pytest.mark.parametrize("cambio", [
    {"ruta": "../fuera"}, {"ruta": "/etc/passwd"},
    {"ruta": "notas/nota.txt"}, {"nombre": "../uno.bin"},
    {"sha256": None}, {"timestamp": 42}, {"nombre": "malo\n"},
])
def test_verify_registro_invalido_no_se_lee(tmp_path, cli_runner, cambio):
    raiz = _caso(tmp_path)
    _editar_indice(raiz, lambda d: d["evidencias"][0].update(cambio))
    resultado = cli_runner.invoke(app, ["verify", str(raiz)])
    assert resultado.exit_code == 1
    assert "[ERROR]" in resultado.stderr


def test_verify_indice_duplicado(tmp_path, cli_runner):
    raiz = _caso(tmp_path)
    _editar_indice(raiz, lambda d: d["evidencias"].append(d["evidencias"][0].copy()))
    resultado = cli_runner.invoke(app, ["verify", str(raiz)])
    assert resultado.exit_code == 1
    assert "duplicada" in resultado.stderr


@pytest.mark.parametrize("ruta", ["evidencia/uno.bin", "evidencia/index.json", "metadata.json"])
def test_verify_rechaza_enlace_fuera_del_caso(tmp_path, cli_runner, ruta):
    raiz = _caso(tmp_path)
    archivo = raiz / ruta
    fuera = tmp_path / "fuera"
    fuera.write_bytes(archivo.read_bytes())
    archivo.unlink()
    archivo.symlink_to(fuera)
    resultado = cli_runner.invoke(app, ["verify", str(raiz)])
    assert resultado.exit_code == 1
    assert "fuera del caso" in resultado.stderr


def test_verify_error_lectura_limpio(tmp_path, cli_runner, monkeypatch):
    raiz = _caso(tmp_path)
    original = builtins.open

    def abrir(archivo, *args, **kwargs):
        if Path(archivo) == raiz / "evidencia" / "uno.bin":
            raise PermissionError("sin permiso")
        return original(archivo, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", abrir)
    resultado = cli_runner.invoke(app, ["verify", str(raiz)])
    assert resultado.exit_code == 1
    assert "uno.bin" in resultado.stderr
    assert "Traceback" not in resultado.stderr


def test_verify_ayuda(tmp_path, cli_runner):
    resultado = cli_runner.invoke(app, ["verify", "--help"])
    assert resultado.exit_code == 0
    assert "RUTA_DEL_CASO" in resultado.stdout


def test_verify_no_cambia_report(tmp_path, cli_runner):
    raiz = _caso(tmp_path)
    (raiz / "evidencia" / "uno.bin").write_bytes(b"AXC")
    report_args = ["report", "--dir", str(raiz)]
    assert cli_runner.invoke(app, report_args).exit_code == 0
    archivo = raiz / "reportes" / "reporte-caso.md"
    antes = archivo.read_bytes()
    assert cli_runner.invoke(app, ["verify", str(raiz)]).exit_code == 1
    assert cli_runner.invoke(app, report_args).exit_code == 0
    assert archivo.read_bytes() == antes
    assert b"MODIFICADO" in antes and b"OK" in antes
