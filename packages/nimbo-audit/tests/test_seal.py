"""ADR-021: sello GPG del caso y ancla externa. Claves efimeras, sin frase, solo de prueba."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile

import pytest

from nimbo_audit.cli import app
from nimbo_audit.servicios.registro import RUTA_REGISTRO
from nimbo_audit.servicios.sello import (
    HUELLA_RELEASE,
    RUTA_CLAVE,
    RUTA_FIRMA,
    RUTA_SELLO,
    interpretar_estado,
)


def _gpg(home, *args):
    return subprocess.run(
        ["gpg", "--homedir", home, "--batch", *args],
        check=True, capture_output=True, text=True,
    )


def _crear_clave(home, uid):
    _gpg(home, "--passphrase", "", "--quick-generate-key", uid, "ed25519", "sign", "never")
    salida = _gpg(home, "--with-colons", "--fingerprint", "--list-secret-keys", uid).stdout
    return next(l.split(":")[9] for l in salida.splitlines() if l.startswith("fpr:"))


@pytest.fixture(scope="module")
def anillo():
    # Ruta corta: el socket de gpg-agent no admite mas de 108 bytes.
    home = tempfile.mkdtemp(prefix="nag", dir="/tmp")
    os.chmod(home, 0o700)
    try:
        yield {
            "home": home,
            "analista": _crear_clave(home, "Analista Prueba <analista@prueba.invalid>"),
            "atacante": _crear_clave(home, "Atacante Prueba <atacante@prueba.invalid>"),
        }
    finally:
        subprocess.run(["gpgconf", "--homedir", home, "--kill", "gpg-agent"], check=False)
        shutil.rmtree(home, ignore_errors=True)


@pytest.fixture
def claves(anillo, monkeypatch):
    monkeypatch.setenv("GNUPGHOME", anillo["home"])
    return anillo


def _ancla(salida):
    return re.search(r"Ancla: ([0-9a-f]{64})", salida).group(1)


def _sellar(cli_runner, raiz, huella):
    return cli_runner.invoke(app, ["seal", "--dir", str(raiz), "--clave", huella])


def _caso_sin_sellar(tmp_path, cli_runner):
    base = tmp_path / "audits"
    assert cli_runner.invoke(
        app, ["init", "caso", "--dir", str(base), "--analista", "Ana"]
    ).exit_code == 0
    raiz = base / "caso"
    origen = tmp_path / "captura.txt"
    origen.write_bytes(b"evidencia original")
    assert cli_runner.invoke(app, ["capture", str(origen), "--dir", str(raiz)]).exit_code == 0
    assert cli_runner.invoke(app, ["report", "--dir", str(raiz)]).exit_code == 0
    (raiz / "notas" / "nota.txt").write_bytes(b"nota")
    return raiz


def _caso_sellado(tmp_path, cli_runner, claves):
    raiz = _caso_sin_sellar(tmp_path, cli_runner)
    res = _sellar(cli_runner, raiz, claves["analista"])
    assert res.exit_code == 0, res.output
    return raiz, _ancla(res.stdout)


def _falsificar_contenido(raiz):
    """Reescribe evidencia, indice y registro de forma coherente entre si."""
    falso = b"evidencia falsificada"
    sha = hashlib.sha256(falso).hexdigest()
    archivo = raiz / "evidencia" / "captura.txt"
    archivo.chmod(0o640)
    archivo.write_bytes(falso)
    indice = raiz / "evidencia" / "index.json"
    datos = json.loads(indice.read_text())
    datos["evidencias"][0]["sha256"] = sha
    indice.write_text(json.dumps(datos))

    registro = raiz / RUTA_REGISTRO
    previo = "0" * 64
    lineas = []
    for linea in registro.read_text().splitlines():
        entrada = json.loads(linea)
        if entrada["accion"] == "capture":
            entrada["sha256"] = sha
        entrada["previo"] = previo
        entrada.pop("hash")
        canonico = json.dumps(entrada, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        entrada["hash"] = hashlib.sha256(canonico.encode()).hexdigest()
        previo = entrada["hash"]
        lineas.append(json.dumps(entrada, ensure_ascii=False, sort_keys=True))
    registro.write_text("\n".join(lineas) + "\n")


def _quitar_sello(raiz):
    for ruta in (RUTA_SELLO, RUTA_FIRMA, RUTA_CLAVE):
        (raiz / ruta).unlink()


def _foto(raiz):
    return sorted(
        (str(p.relative_to(raiz)), p.stat().st_mode, p.stat().st_mtime_ns, p.read_bytes())
        for p in raiz.rglob("*") if p.is_file()
    )


def test_seal_y_verify_correcto(tmp_path, cli_runner, claves):
    raiz, ancla = _caso_sellado(tmp_path, cli_runner, claves)

    res = cli_runner.invoke(app, [
        "verify", str(raiz), "--ancla", ancla, "--huella", claves["analista"],
    ])

    assert res.exit_code == 0, res.output
    assert "Sello: VALIDO" in res.stdout
    assert claves["analista"] in res.stdout
    assert ancla == hashlib.sha256((raiz / RUTA_SELLO).read_bytes()).hexdigest()


def test_verify_sin_ancla_avisa_que_no_prueba_el_origen(tmp_path, cli_runner, claves):
    raiz, ancla = _caso_sellado(tmp_path, cli_runner, claves)

    res = cli_runner.invoke(app, ["verify", str(raiz)])

    assert res.exit_code == 0, res.output
    assert f"Ancla: {ancla}" in res.stdout
    assert "[AVISO]" in res.stdout


def test_ataque_reescribir_evidencia_indice_y_registro(tmp_path, cli_runner, claves):
    """El ataque que motiva ADR-021: todo coherente menos el sello."""
    raiz, _ = _caso_sellado(tmp_path, cli_runner, claves)
    _falsificar_contenido(raiz)

    res = cli_runner.invoke(app, ["verify", str(raiz)])

    assert res.exit_code == 1
    assert "OK: captura.txt" in res.stdout
    assert "Registro: VALIDO" in res.stdout
    assert "Sello: ROTO" in res.stdout
    assert "evidencia/captura.txt" in res.stdout


def test_ataque_resellar_con_otra_clave_lo_detecta_el_ancla(tmp_path, cli_runner, claves):
    raiz, ancla = _caso_sellado(tmp_path, cli_runner, claves)
    _falsificar_contenido(raiz)
    _quitar_sello(raiz)
    assert _sellar(cli_runner, raiz, claves["atacante"]).exit_code == 0

    con_ancla = cli_runner.invoke(app, ["verify", str(raiz), "--ancla", ancla])
    con_huella = cli_runner.invoke(app, ["verify", str(raiz), "--huella", claves["analista"]])

    assert con_ancla.exit_code == 1
    assert "Sello: ROTO" in con_ancla.stdout
    assert con_huella.exit_code == 1
    assert "Sello: ROTO" in con_huella.stdout


def test_ataque_borrar_la_custodia_lo_detecta_el_ancla(tmp_path, cli_runner, claves):
    raiz, ancla = _caso_sellado(tmp_path, cli_runner, claves)
    shutil.rmtree(raiz / "custodia")

    sin_ancla = cli_runner.invoke(app, ["verify", str(raiz)])
    con_ancla = cli_runner.invoke(app, ["verify", str(raiz), "--ancla", ancla])

    assert "Sello: SIN SELLAR" in sin_ancla.stdout
    assert con_ancla.exit_code == 1
    assert "Sello: ROTO" in con_ancla.stdout


@pytest.mark.parametrize("cambio", ["nota", "extra", "borrado", "metadata", "reporte"])
def test_sello_cubre_todo_el_caso(tmp_path, cli_runner, claves, cambio):
    raiz, _ = _caso_sellado(tmp_path, cli_runner, claves)
    if cambio == "nota":
        (raiz / "notas" / "nota.txt").write_bytes(b"cambiada")
    elif cambio == "extra":
        (raiz / "logs" / "colado.log").write_bytes(b"colado")
    elif cambio == "borrado":
        (raiz / "notas" / "nota.txt").unlink()
    elif cambio == "metadata":
        (raiz / "metadata.json").write_text('{"id":"caso","fecha_inicio":"x","analista":"M"}')
    else:
        (raiz / "reportes" / "reporte-caso.md").write_text("reporte falso")

    res = cli_runner.invoke(app, ["verify", str(raiz)])

    assert res.exit_code == 1
    assert "Sello: ROTO" in res.stdout


@pytest.mark.parametrize("pieza", [RUTA_SELLO, RUTA_FIRMA, RUTA_CLAVE])
def test_sello_alterado(tmp_path, cli_runner, claves, pieza):
    raiz, _ = _caso_sellado(tmp_path, cli_runner, claves)
    archivo = raiz / pieza
    archivo.chmod(0o640)
    archivo.write_bytes(archivo.read_bytes().replace(b"a", b"b", 1) + b"\n")

    res = cli_runner.invoke(app, ["verify", str(raiz)])

    assert res.exit_code == 1
    assert "Sello: ROTO" in res.stdout


@pytest.mark.parametrize("pieza", [RUTA_FIRMA, RUTA_CLAVE])
def test_sello_incompleto(tmp_path, cli_runner, claves, pieza):
    raiz, _ = _caso_sellado(tmp_path, cli_runner, claves)
    (raiz / pieza).unlink()

    res = cli_runner.invoke(app, ["verify", str(raiz)])

    assert res.exit_code == 1
    assert "Sello: ROTO" in res.stdout


def test_firma_y_sello_sueltos_sin_sello_json_no_pasan_por_sin_sellar(
    tmp_path, cli_runner, claves
):
    raiz, _ = _caso_sellado(tmp_path, cli_runner, claves)
    (raiz / RUTA_SELLO).unlink()

    res = cli_runner.invoke(app, ["verify", str(raiz)])

    assert res.exit_code == 1
    assert "Sello: ROTO" in res.stdout


def test_enlace_simbolico_rompe_el_sello(tmp_path, cli_runner, claves):
    raiz, _ = _caso_sellado(tmp_path, cli_runner, claves)
    (raiz / "notas" / "enlace").symlink_to("/etc/hostname")

    res = cli_runner.invoke(app, ["verify", str(raiz)])

    assert res.exit_code == 1
    assert "Sello: ROTO" in res.stdout


def test_verify_de_caso_sellado_no_escribe(tmp_path, cli_runner, claves):
    raiz, ancla = _caso_sellado(tmp_path, cli_runner, claves)
    antes = _foto(raiz)

    assert cli_runner.invoke(app, ["verify", str(raiz), "--ancla", ancla]).exit_code == 0

    assert _foto(raiz) == antes


def test_caso_sellado_no_admite_cambios(tmp_path, cli_runner, claves):
    raiz, ancla = _caso_sellado(tmp_path, cli_runner, claves)
    otro = tmp_path / "otro.txt"
    otro.write_bytes(b"otro")

    capture = cli_runner.invoke(app, ["capture", str(otro), "--dir", str(raiz)])
    report = cli_runner.invoke(app, ["report", "--dir", str(raiz), "--yes"])
    reinicio = cli_runner.invoke(app, ["init", "caso", "--dir", str(raiz.parent), "--force"])
    resello = _sellar(cli_runner, raiz, claves["analista"])

    for resultado in (capture, report, reinicio, resello):
        assert resultado.exit_code == 1
        assert "sellado" in resultado.stderr
    assert cli_runner.invoke(app, ["verify", str(raiz), "--ancla", ancla]).exit_code == 0


def test_no_sella_un_caso_alterado(tmp_path, cli_runner, claves):
    raiz = _caso_sin_sellar(tmp_path, cli_runner)
    archivo = raiz / "evidencia" / "captura.txt"
    archivo.chmod(0o640)
    archivo.write_bytes(b"alterado")

    res = _sellar(cli_runner, raiz, claves["analista"])

    assert res.exit_code == 1
    assert not (raiz / RUTA_SELLO).exists()


def test_no_sella_con_registro_roto(tmp_path, cli_runner, claves):
    raiz = _caso_sin_sellar(tmp_path, cli_runner)
    with (raiz / RUTA_REGISTRO).open("a", encoding="utf-8") as fh:
        fh.write("roto\n")

    res = _sellar(cli_runner, raiz, claves["analista"])

    assert res.exit_code == 1
    assert not (raiz / RUTA_SELLO).exists()


def test_rechaza_la_clave_de_release(tmp_path, cli_runner, claves):
    raiz = _caso_sin_sellar(tmp_path, cli_runner)

    res = _sellar(cli_runner, raiz, HUELLA_RELEASE)

    assert res.exit_code == 1
    assert "release" in res.stderr
    assert not (raiz / RUTA_SELLO).exists()


@pytest.mark.parametrize("clave", ["analista@prueba.invalid", "ABCD1234", "0" * 40])
def test_exige_huella_completa_de_una_clave_disponible(tmp_path, cli_runner, claves, clave):
    raiz = _caso_sin_sellar(tmp_path, cli_runner)
    antes = _foto(raiz)

    res = _sellar(cli_runner, raiz, clave)

    assert res.exit_code == 1
    assert _foto(raiz) == antes


def test_caso_antiguo_se_puede_sellar(tmp_path, cli_runner, claves):
    from nimbo_audit.comandos.capture import ComandoCapture
    from nimbo_audit.comandos.init import ComandoInit
    from nimbo_audit.repositorio.engagement_repo import RepositorioEngagementJSON
    from nimbo_audit.repositorio.evidencia_repo import RepositorioEvidenciaJSON

    raiz = ComandoInit("antiguo", RepositorioEngagementJSON(tmp_path)).ejecutar()
    origen = tmp_path / "a.txt"
    origen.write_bytes(b"a")
    ComandoCapture(origen, RepositorioEvidenciaJSON(raiz)).ejecutar()

    res = _sellar(cli_runner, raiz, claves["analista"])

    assert res.exit_code == 0, res.output
    verificado = cli_runner.invoke(app, ["verify", str(raiz), "--ancla", _ancla(res.stdout)])
    assert verificado.exit_code == 0, verificado.output
    assert "Registro: VALIDO (1 entradas)" in verificado.stdout


P = "A" * 40
S = "B" * 40


@pytest.mark.parametrize("salida, valida, caducada, primaria", [
    (f"[GNUPG:] GOODSIG X U\n[GNUPG:] VALIDSIG {S} d t e 4 0 22 8 00 {P}\n", True, False, P),
    (f"[GNUPG:] EXPKEYSIG X U\n[GNUPG:] VALIDSIG {S} d t e 4 0 22 8 00 {P}\n", True, True, P),
    (f"[GNUPG:] REVKEYSIG X U\n[GNUPG:] VALIDSIG {S} d t e 4 0 22 8 00 {P}\n", False, False, ""),
    (f"[GNUPG:] EXPSIG X U\n[GNUPG:] VALIDSIG {S} d t e 4 0 22 8 00 {P}\n", False, False, ""),
    ("[GNUPG:] BADSIG X U\n", False, False, ""),
    ("[GNUPG:] ERRSIG X\n", False, False, ""),
    ("[GNUPG:] NO_PUBKEY X\n", False, False, ""),
    ("", False, False, ""),
    (f"[GNUPG:] GOODSIG X U\n[GNUPG:] GOODSIG Y U\n[GNUPG:] VALIDSIG {S} d t e 4 0 22 8 00 {P}\n",
     False, False, ""),
])
def test_interpretar_estado_de_gpg(salida, valida, caducada, primaria):
    estado = interpretar_estado(salida)

    assert (estado.valida, estado.caducada, estado.primaria) == (valida, caducada, primaria)
