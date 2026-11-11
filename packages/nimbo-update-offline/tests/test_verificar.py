"""RF-UPD-01 / HU-14: solo se aceptan paquetes con firma GPG válida.

CA-1: un lote con firma válida se acepta.
CA-2: un lote con firma inválida o sin firma se rechaza.
CA-3: se rechaza el 100 % del conjunto de lotes inválidos (N = 9 casos).
"""
import pytest

from conftest import escribir_manifiesto
from nimbo_update_offline.verificar import verificar


def test_lote_con_firma_valida_se_acepta(lote, claves):
    v = verificar(lote, claves["anillo"])
    assert v.aceptado, v.motivo
    assert sorted(p.name for p in v.paquetes) == ["nimbo-audit_0.1.1-1_all.deb",
                                                  "nimbo-nav_0.1.1-1_all.deb"]


# --- Conjunto de manipulaciones (CA-3). Cada una devuelve el texto esperado en el motivo.

def sin_firma(d, claves):
    (d / "MANIFIESTO.asc").unlink()
    return "sin firma"


def sin_manifiesto(d, claves):
    (d / "MANIFIESTO").unlink()
    return "sin firma"


def manifiesto_alterado_tras_firmar(d, claves):
    m = d / "MANIFIESTO"
    m.write_text(m.read_text(encoding="utf-8").replace("a", "b", 1), encoding="utf-8")
    return "firma inválida"


def firmado_por_otra_clave(d, claves):
    (d / "MANIFIESTO.asc").unlink()
    claves["otra"].firmar(d / "MANIFIESTO")
    return "firma inválida"


def firma_basura(d, claves):
    (d / "MANIFIESTO.asc").write_text("-----BEGIN PGP SIGNATURE-----\nxx\n-----END PGP SIGNATURE-----\n")
    return "firma inválida"


def byte_cambiado_en_un_deb(d, claves):
    p = d / "nimbo-nav_0.1.1-1_all.deb"
    datos = bytearray(p.read_bytes())
    datos[10] ^= 0x01
    p.write_bytes(bytes(datos))
    return "alterado"


def deb_extra_sin_firmar(d, claves):
    (d / "malicioso_1.0_all.deb").write_bytes(b"no estoy en el manifiesto")
    return "no está firmado"


def deb_listado_ausente(d, claves):
    (d / "nimbo-audit_0.1.1-1_all.deb").unlink()
    return "falta"


def ruta_con_directorios_firmada(d, claves):
    # Aunque esté firmado con la clave buena, un nombre con ruta se rechaza.
    (d / "MANIFIESTO.asc").unlink()
    m = d / "MANIFIESTO"
    m.write_text(m.read_text(encoding="utf-8") + f"{'0' * 64}  ../../etc/x.deb\n", encoding="utf-8")
    claves["buena"].firmar(m)
    return "nombre no permitido"


def manifiesto_vacio_firmado(d, claves):
    for p in d.glob("*.deb"):
        p.unlink()
    (d / "MANIFIESTO.asc").unlink()
    escribir_manifiesto(d, [])
    (d / "MANIFIESTO").write_text("", encoding="utf-8")
    claves["buena"].firmar(d / "MANIFIESTO")
    return "vacío"


MANIPULACIONES = [sin_firma, sin_manifiesto, manifiesto_alterado_tras_firmar,
                  firmado_por_otra_clave, firma_basura, byte_cambiado_en_un_deb,
                  deb_extra_sin_firmar, deb_listado_ausente, ruta_con_directorios_firmada,
                  manifiesto_vacio_firmado]


@pytest.mark.parametrize("manipular", MANIPULACIONES, ids=lambda f: f.__name__)
def test_lote_manipulado_se_rechaza(lote, claves, manipular):
    esperado = manipular(lote, claves)
    v = verificar(lote, claves["anillo"])
    assert not v.aceptado
    assert esperado in v.motivo, v.motivo
    assert v.paquetes == []


# --- Revisión de #49: errores que antes salían como traceback --------------------------

def manifiesto_no_utf8_firmado(d, claves):
    (d / "MANIFIESTO.asc").unlink()
    m = d / "MANIFIESTO"
    m.write_bytes(m.read_bytes() + b"\xff\xfe basura no utf-8\n")
    claves["buena"].firmar(m)
    return "no es UTF-8"


def directorio_que_se_llama_deb(d, claves):
    (d / "trampa.deb").mkdir()
    return "no es un fichero"


@pytest.mark.parametrize("manipular", [manifiesto_no_utf8_firmado, directorio_que_se_llama_deb],
                         ids=lambda f: f.__name__)
def test_errores_raros_se_rechazan_con_motivo(lote, claves, manipular):
    esperado = manipular(lote, claves)
    v = verificar(lote, claves["anillo"])  # no debe lanzar excepción
    assert not v.aceptado
    assert esperado in v.motivo, v.motivo
