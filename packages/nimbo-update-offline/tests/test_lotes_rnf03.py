"""Lotes de la prueba RNF-03 / RF-UPD-01 (pruebas/preparar-lotes-rnf03.py).

Los mismos lotes que viajan a la VM sin red se comprueban aquí con `verificar()`: el lote de
control se acepta con el anillo de prueba y TODOS los inválidos se rechazan (criterio de
RF-UPD-01: el 100 %). Las claves son efímeras y no salen del directorio temporal.
"""
import importlib.util
import shutil
from pathlib import Path

import pytest

from nimbo_update_offline.verificar import verificar

RUTA = Path(__file__).resolve().parents[1] / "pruebas" / "preparar-lotes-rnf03.py"


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
