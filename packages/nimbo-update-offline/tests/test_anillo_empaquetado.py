"""El anillo de actualizaciones viaja en el paquete (ADR-013) y es la clave de release.

Decisión de Juan José (16-nov, prueba RNF-03): los lotes los firma la clave de release
(ADR-015). Sin este fichero, `instalar` rechaza todo, también un lote bien firmado
(hallazgo 1 de repro/evidencia/2026-11-16-rnf03-sin-red.md).
"""
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
ANILLO = RAIZ / "debian" / "keyrings" / "nimbo-actualizaciones.gpg"
INSTALL = RAIZ / "debian" / "nimbo-update-offline.install"
HUELLA = "0C50B7391A9B8CFF8A36A627D3B9111FEC5748C6"  # README.md y release/README.md
# pybuild (dh_auto_test, al construir el .deb) copia solo tests/: ahí no hay debian/.
pytestmark = pytest.mark.skipif(not INSTALL.is_file(), reason="sin debian/ (build del .deb)")


def test_el_paquete_instala_el_anillo_en_la_ruta_que_usa_instalar():
    from nimbo_update_offline.verificar import ANILLO as RUTA
    lineas = INSTALL.read_text(encoding="utf-8").split("\n")
    assert f"debian/keyrings/nimbo-actualizaciones.gpg {str(RUTA.parent).lstrip('/')}/" in lineas


def test_el_anillo_es_binario_y_solo_la_clave_de_release():
    datos = ANILLO.read_bytes()
    assert not datos.startswith(b"-----BEGIN"), "gpgv --keyring necesita el anillo binario"
    assert b"PRIVATE" not in datos
    if not shutil.which("gpg"):
        pytest.skip("gpg no disponible")
    with tempfile.TemporaryDirectory() as home:
        salida = subprocess.run(["gpg", "--homedir", home, "--batch", "--with-colons",
                                 "--show-keys", str(ANILLO)],
                                check=True, capture_output=True, text=True).stdout
    filas = [l.split(":") for l in salida.splitlines()]
    assert [f[0] for f in filas].count("pub") == 1
    assert [f[0] for f in filas].count("sec") == 0
    assert filas[[f[0] for f in filas].index("fpr")][9] == HUELLA
