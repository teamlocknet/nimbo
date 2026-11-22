"""ADR-021: registro encadenado de acciones y copias de evidencia en solo lectura."""
import hashlib
import json
import stat
from pathlib import Path

import pytest

from nimbo_audit.cli import app
from nimbo_audit.comandos.capture import ComandoCapture
from nimbo_audit.comandos.init import ComandoInit
from nimbo_audit.errores import RegistroError
from nimbo_audit.repositorio.engagement_repo import RepositorioEngagementJSON
from nimbo_audit.repositorio.evidencia_repo import RepositorioEvidenciaJSON
from nimbo_audit.servicios.registro import GENESIS, RUTA_REGISTRO, RegistroCustodia


def _caso(tmp_path, cli_runner, nombre="caso"):
    base = tmp_path / "audits"
    res = cli_runner.invoke(app, ["init", nombre, "--dir", str(base), "--analista", "Ana"])
    assert res.exit_code == 0, res.output
    raiz = base / nombre
    origen = tmp_path / "captura.txt"
    origen.write_bytes(b"evidencia original")
    res = cli_runner.invoke(app, [
        "capture", str(origen), "--dir", str(raiz),
        "--analista", "Bea", "--origen", "servidor web del cliente",
    ])
    assert res.exit_code == 0, res.output
    return raiz


def _entradas(raiz):
    texto = (raiz / RUTA_REGISTRO).read_text(encoding="utf-8")
    return [json.loads(linea) for linea in texto.splitlines()]


def _escribir_entradas(raiz, entradas):
    (raiz / RUTA_REGISTRO).write_text(
        "".join(json.dumps(e, ensure_ascii=False, sort_keys=True) + "\n" for e in entradas),
        encoding="utf-8",
    )


def _alterar_evidencia(raiz, nombre, contenido):
    archivo = raiz / "evidencia" / nombre
    archivo.chmod(0o640)
    archivo.write_bytes(contenido)
    indice = raiz / "evidencia" / "index.json"
    datos = json.loads(indice.read_text())
    for evidencia in datos["evidencias"]:
        if evidencia["nombre"] == nombre:
            evidencia["sha256"] = hashlib.sha256(contenido).hexdigest()
    indice.write_text(json.dumps(datos))


def test_registro_guarda_quien_que_y_origen(tmp_path, cli_runner):
    raiz = _caso(tmp_path, cli_runner)

    inicio, captura = _entradas(raiz)

    assert (inicio["accion"], inicio["analista"], inicio["previo"]) == ("init", "Ana", GENESIS)
    assert captura["accion"] == "capture"
    assert captura["analista"] == "Bea"
    assert captura["nombre"] == "captura.txt"
    assert captura["sha256"] == hashlib.sha256(b"evidencia original").hexdigest()
    assert captura["origen"] == "servidor web del cliente"
    assert captura["ruta_origen"] == str((tmp_path / "captura.txt").resolve())
    assert captura["previo"] == inicio["hash"]


def test_analista_por_defecto_es_el_del_caso(tmp_path, cli_runner):
    raiz = _caso(tmp_path, cli_runner)
    origen = tmp_path / "otra.txt"
    origen.write_bytes(b"x")

    res = cli_runner.invoke(app, ["capture", str(origen), "--dir", str(raiz)])

    assert res.exit_code == 0, res.output
    assert _entradas(raiz)[-1]["analista"] == "Ana"


def test_analista_desde_variable_de_entorno(tmp_path, cli_runner, monkeypatch):
    raiz = _caso(tmp_path, cli_runner)
    origen = tmp_path / "otra.txt"
    origen.write_bytes(b"x")
    monkeypatch.setenv("NIMBO_ANALISTA", "Carla")

    res = cli_runner.invoke(app, ["capture", str(origen), "--dir", str(raiz)])

    assert res.exit_code == 0, res.output
    assert _entradas(raiz)[-1]["analista"] == "Carla"


def test_report_queda_en_el_registro(tmp_path, cli_runner):
    raiz = _caso(tmp_path, cli_runner)

    res = cli_runner.invoke(app, ["report", "--dir", str(raiz), "--analista", "Bea"])

    assert res.exit_code == 0, res.output
    ultima = _entradas(raiz)[-1]
    assert (ultima["accion"], ultima["analista"]) == ("report", "Bea")
    reporte = raiz / "reportes" / "reporte-caso.md"
    assert ultima["sha256"] == hashlib.sha256(reporte.read_bytes()).hexdigest()


def test_verify_caso_con_registro_integro(tmp_path, cli_runner):
    raiz = _caso(tmp_path, cli_runner)

    res = cli_runner.invoke(app, ["verify", str(raiz)])

    assert res.exit_code == 0, res.output
    assert "Registro: VALIDO (2 entradas)" in res.stdout
    assert "Sello: SIN SELLAR" in res.stdout


@pytest.mark.parametrize("ataque", ["editar", "borrar", "reordenar", "linea-rota"])
def test_verify_detecta_registro_manipulado(tmp_path, cli_runner, ataque):
    raiz = _caso(tmp_path, cli_runner)
    entradas = _entradas(raiz)
    if ataque == "editar":
        entradas[1]["analista"] = "Mallory"
        _escribir_entradas(raiz, entradas)
    elif ataque == "borrar":
        _escribir_entradas(raiz, entradas[1:])
    elif ataque == "reordenar":
        _escribir_entradas(raiz, list(reversed(entradas)))
    else:
        with (raiz / RUTA_REGISTRO).open("a", encoding="utf-8") as fh:
            fh.write("esto no es json\n")

    res = cli_runner.invoke(app, ["verify", str(raiz)])

    assert res.exit_code == 1
    assert "Registro: ROTO" in res.stdout


@pytest.mark.parametrize("accion, campos", [
    ("capture", {"nombre": ["no", "es", "texto"], "sha256": "x"}),
    ("adopcion", {"evidencias": ["no", "es", "un", "dict"]}),
    ("adopcion", {"evidencias": 7}),
])
def test_verify_registro_con_tipos_invalidos_no_revienta(
    tmp_path, cli_runner, accion, campos
):
    """Cadena bien recalculada, pero con campos de un tipo inesperado."""
    raiz = _caso(tmp_path, cli_runner)
    entradas = _entradas(raiz)
    falsa = {
        **campos, "seq": 3, "previo": entradas[-1]["hash"], "accion": accion,
        "analista": "M", "timestamp": "t",
    }
    canonico = json.dumps(falsa, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    falsa["hash"] = hashlib.sha256(canonico.encode()).hexdigest()
    _escribir_entradas(raiz, [*entradas, falsa])

    res = cli_runner.invoke(app, ["verify", str(raiz)])

    assert res.exit_code == 1
    assert res.exception is None or isinstance(res.exception, SystemExit)
    assert "Registro: ROTO" in res.stdout


def test_verify_detecta_evidencia_e_indice_reescritos(tmp_path, cli_runner):
    """El hueco de 0.1.0: cambiar a la vez la evidencia y su hash en el indice."""
    raiz = _caso(tmp_path, cli_runner)
    _alterar_evidencia(raiz, "captura.txt", b"evidencia falsificada")

    res = cli_runner.invoke(app, ["verify", str(raiz)])

    assert res.exit_code == 1
    assert "OK: captura.txt" in res.stdout  # el indice por si solo no lo ve
    assert "Registro: ROTO" in res.stdout


def test_verify_senala_archivo_no_registrado(tmp_path, cli_runner):
    raiz = _caso(tmp_path, cli_runner)
    (raiz / "evidencia" / "colado.txt").write_bytes(b"metido a mano")

    res = cli_runner.invoke(app, ["verify", str(raiz)])

    assert res.exit_code == 1
    assert "NO REGISTRADO: colado.txt" in res.stdout


def test_capture_deja_la_copia_en_solo_lectura(tmp_path, cli_runner):
    raiz = _caso(tmp_path, cli_runner)

    modo = stat.S_IMODE((raiz / "evidencia" / "captura.txt").stat().st_mode)

    assert modo == 0o440


def test_capture_no_cambia_permisos_del_original(tmp_path, cli_runner):
    _caso(tmp_path, cli_runner)
    assert stat.S_IMODE((tmp_path / "captura.txt").stat().st_mode) & stat.S_IWUSR


def test_caso_antiguo_se_verifica_sin_registro(tmp_path, cli_runner):
    raiz = ComandoInit("antiguo", RepositorioEngagementJSON(tmp_path)).ejecutar()
    origen = tmp_path / "a.txt"
    origen.write_bytes(b"a")
    ComandoCapture(origen, RepositorioEvidenciaJSON(raiz)).ejecutar()

    res = cli_runner.invoke(app, ["verify", str(raiz)])

    assert res.exit_code == 0, res.output
    assert "Registro: SIN REGISTRO" in res.stdout
    assert "Sello: SIN SELLAR" in res.stdout


def test_caso_antiguo_adopta_el_registro_al_capturar(tmp_path, cli_runner):
    raiz = ComandoInit("antiguo", RepositorioEngagementJSON(tmp_path)).ejecutar()
    previa = tmp_path / "previa.txt"
    previa.write_bytes(b"previa")
    ComandoCapture(previa, RepositorioEvidenciaJSON(raiz)).ejecutar()
    nueva = tmp_path / "nueva.txt"
    nueva.write_bytes(b"nueva")

    res = cli_runner.invoke(app, ["capture", str(nueva), "--dir", str(raiz)])

    assert res.exit_code == 0, res.output
    adopcion, captura = _entradas(raiz)
    assert adopcion["accion"] == "adopcion"
    assert adopcion["evidencias"] == {
        "previa.txt": hashlib.sha256(b"previa").hexdigest()
    }
    assert captura["nombre"] == "nueva.txt"
    assert cli_runner.invoke(app, ["verify", str(raiz)]).exit_code == 0


def test_capture_revierte_si_el_registro_falla(tmp_path, monkeypatch):
    raiz = ComandoInit("caso", RepositorioEngagementJSON(tmp_path)).ejecutar()
    origen = tmp_path / "a.txt"
    origen.write_bytes(b"a")
    registro = RegistroCustodia(raiz)

    def falla(*_args, **_kwargs):
        raise RegistroError("disco lleno")

    monkeypatch.setattr(registro, "anadir", falla)
    repo = RepositorioEvidenciaJSON(raiz)

    with pytest.raises(RegistroError):
        ComandoCapture(origen, repo, registro=registro, analista="Ana").ejecutar()

    assert not (raiz / "evidencia" / "a.txt").exists()
    assert repo.listar() == []


def test_registro_no_escribe_al_verificar(tmp_path, cli_runner):
    raiz = _caso(tmp_path, cli_runner)
    antes = (raiz / RUTA_REGISTRO).read_bytes()

    assert cli_runner.invoke(app, ["verify", str(raiz)]).exit_code == 0

    assert (raiz / RUTA_REGISTRO).read_bytes() == antes
    assert isinstance(raiz / RUTA_REGISTRO, Path)
