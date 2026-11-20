"""Lotes de la prueba RNF-03 / RF-UPD-01 (pruebas/preparar-lotes-rnf03.py).

Los mismos lotes que viajan a la VM sin red se comprueban aquí con `verificar()`: el lote de
control se acepta con el anillo de prueba y TODOS los inválidos se rechazan (criterio de
RF-UPD-01: el 100 %). Las claves son efímeras y no salen del directorio temporal.
"""
import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest

from nimbo_update_offline.verificar import verificar

RUTA = Path(__file__).resolve().parents[1] / "pruebas" / "preparar-lotes-rnf03.py"
# pybuild (dh_auto_test, al construir el .deb) copia solo tests/: ahí no hay pruebas/.
pytestmark = pytest.mark.skipif(not RUTA.is_file(), reason="sin pruebas/ (build del .deb)")


def _modulo():
    spec = importlib.util.spec_from_file_location("preparar_lotes_rnf03", RUTA)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def lotes(tmp_path_factory):
    if not (shutil.which("gpg") and shutil.which("gpgv")):
        pytest.skip("gpg/gpgv no disponibles")
    destino = tmp_path_factory.mktemp("rnf03") / "lotes"
    _modulo().preparar(destino)
    return destino


def _esperado(lotes):
    filas = []
    for linea in (lotes / "ESPERADO").read_text(encoding="utf-8").splitlines():
        if linea.strip() and not linea.startswith("#"):
            filas.append(tuple(linea.split()))
    return filas


def test_cada_lote_da_lo_esperado_con_el_anillo_de_prueba(lotes):
    filas = [f for f in _esperado(lotes) if f[1] == "prueba"]
    assert ("00-control", "prueba", "ACEPTADO") in filas
    for lote, _, esperado in filas:
        v = verificar(lotes / lote, lotes / "anillo-prueba.gpg")
        assert ("ACEPTADO" if v.aceptado else "RECHAZADO") == esperado, (lote, v.motivo)


def test_cubre_los_casos_de_firma_invalida(lotes):
    invalidos = {f[0] for f in _esperado(lotes) if f[1] == "prueba" and f[2] == "RECHAZADO"}
    for caso in ("sin-firma", "otra-clave", "manifiesto-alterado", "deb-alterado", "deb-extra",
                 "clave-revocada", "clave-caducada", "firma-basura"):
        assert any(caso in x for x in invalidos), caso
    assert len(invalidos) >= 13


def test_la_clave_de_prueba_no_vale_para_el_anillo_de_nimbo(lotes, tmp_path):
    filas = [f for f in _esperado(lotes) if f[1] in ("nimbo", "instalar")]
    assert ("00-control", "nimbo", "RECHAZADO") in filas
    assert ("00-control", "instalar", "RECHAZADO") in filas
    assert not verificar(lotes / "00-control", tmp_path / "no-existe.gpg").aceptado


def test_ninguna_clave_privada_sale_del_temporal(lotes):
    for f in lotes.rglob("*"):
        if f.is_file():
            datos = f.read_bytes()
            assert b"PRIVATE KEY" not in datos, f
    assert sorted(p.name for p in lotes.rglob("*.gpg")) == ["anillo-prueba.gpg"]


def test_el_deb_de_control_es_un_ar_de_debian(lotes):
    debs = list((lotes / "00-control").glob("*.deb"))
    assert len(debs) == 1
    datos = debs[0].read_bytes()
    assert datos.startswith(b"!<arch>\ndebian-binary   ")
    assert b"control.tar.gz" in datos and b"data.tar.gz" in datos


def test_lote_para_firmar_con_la_clave_de_release(tmp_path):
    # Parte 2 (16-nov): un lote SIN firma que Juan José firma con la clave de release;
    # en la VM, con el anillo de la ISO, tiene que aceptarse e instalarse sin red.
    if not (shutil.which("gpg") and shutil.which("gpgv")):
        pytest.skip("gpg/gpgv no disponibles")
    destino = tmp_path / "lotes"
    filas = _modulo().preparar(destino, para_firmar=True)
    lote = destino / "20-firmado-release"
    assert sorted(p.name for p in lote.iterdir()) == ["MANIFIESTO", "nimbo-rnf03-prueba_1.0_all.deb"]
    assert ("20-firmado-release", "nimbo", "ACEPTADO") in filas
    assert ("20-firmado-release", "instalar", "INSTALADO") in filas
    texto = (destino / "ESPERADO").read_text(encoding="utf-8")
    assert "20-firmado-release instalar INSTALADO" in texto
    # sin firmar todavía: se rechaza con cualquier anillo
    assert not verificar(lote, destino / "anillo-prueba.gpg").aceptado


def test_el_deb_de_juguete_trae_sus_directorios(tmp_path):
    # VM, 16-nov: dpkg no crea los directorios padre ("unable to create
    # /usr/share/doc/nimbo-rnf03-prueba/LEEME.dpkg-new: No such file or directory").
    import io
    import tarfile
    datos = _modulo().deb_de_juguete()
    inicio = datos.index(b"data.tar.gz")
    tam = int(datos[inicio + 48:inicio + 58].decode().strip())
    tar = tarfile.open(fileobj=io.BytesIO(datos[inicio + 60:inicio + 60 + tam]), mode="r:gz")
    nombres = {m.name.rstrip("/") for m in tar.getmembers()}
    for m in tar.getmembers():
        if m.isfile():
            partes = m.name.split("/")
            for i in range(1, len(partes)):
                assert "/".join(partes[:i]) in nombres, ("falta el directorio", "/".join(partes[:i]))
    if shutil.which("dpkg"):
        deb = tmp_path / "x.deb"
        deb.write_bytes(datos)
        raiz = tmp_path / "raiz"
        (raiz / "var/lib/dpkg/updates").mkdir(parents=True)
        (raiz / "var/lib/dpkg/info").mkdir()
        (raiz / "var/lib/dpkg/status").write_text("")
        r = subprocess.run(["dpkg", "--root", str(raiz), "--force-not-root", "--force-script-chrootless",
                            "--log=/dev/null", "-i", str(deb)], capture_output=True, text=True)
        assert r.returncode == 0, r.stderr


def test_el_deb_de_juguete_no_depende_de_la_hora(monkeypatch):
    # "w:gz" de tarfile guarda en la cabecera gzip la hora actual: el .deb cambiaba en cada
    # ejecución aunque los tars usen EPOCA (hallazgo 4 del ensayo de la demo, 17-nov).
    import time
    m = _modulo()
    monkeypatch.setattr(time, "time", lambda: 1_000_000_000.0)
    uno = m.deb_de_juguete()
    monkeypatch.setattr(time, "time", lambda: 2_000_000_000.0)
    assert m.deb_de_juguete() == uno
