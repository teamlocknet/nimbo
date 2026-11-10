"""Claves GPG EFÍMERAS de prueba: se generan en un directorio temporal y se borran al
terminar. Ninguna clave entra al repositorio (regla de credenciales)."""
import hashlib
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

GPG = shutil.which("gpg")
GPGV = shutil.which("gpgv")


def posix(ruta) -> str:
    """En Windows, el gpg de Git (MSYS) necesita rutas /c/...; en Linux no cambia nada."""
    ruta = str(ruta)
    if os.name == "nt" and len(ruta) > 2 and ruta[1] == ":":
        return "/" + ruta[0].lower() + ruta[2:].replace("\\", "/")
    return ruta


def _gpg(home: str, *args: str, entrada: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run([GPG, "--homedir", posix(home), "--batch", "--yes", *args],
                          input=entrada, check=True, capture_output=True)


class Firmante:
    def __init__(self, home: str, uid: str):
        self.home = home
        _gpg(home, "--passphrase", "", "--quick-gen-key", uid, "ed25519", "sign", "1d")
        self.uid = uid

    def exportar(self, destino: Path) -> Path:
        destino.write_bytes(_gpg(self.home, "--export", self.uid).stdout)
        return destino

    def firmar(self, fichero: Path) -> None:
        _gpg(self.home, "--local-user", self.uid, "--armor", "--detach-sign",
             "--output", posix(str(fichero) + ".asc"), posix(fichero))


@pytest.fixture(scope="session")
def claves():
    if not (GPG and GPGV):
        pytest.skip("gpg/gpgv no disponibles")
    base = tempfile.mkdtemp(prefix="nuo-")
    try:
        homes = {}
        for nombre in ("buena", "otra"):
            homes[nombre] = os.path.join(base, nombre)
            os.mkdir(homes[nombre])
        buena = Firmante(homes["buena"], "nimbo-actualizaciones-PRUEBA <prueba@invalid>")
        otra = Firmante(homes["otra"], "atacante-PRUEBA <atacante@invalid>")
        anillo = buena.exportar(Path(base) / "anillo.gpg")
        yield {"buena": buena, "otra": otra, "anillo": anillo}
    finally:
        subprocess.run(["gpgconf", "--homedir", posix(homes.get("buena", base)), "--kill", "gpg-agent"],
                       capture_output=True)
        subprocess.run(["gpgconf", "--homedir", posix(homes.get("otra", base)), "--kill", "gpg-agent"],
                       capture_output=True)
        shutil.rmtree(base, ignore_errors=True)


def escribir_manifiesto(directorio: Path, nombres: list[str]) -> Path:
    lineas = []
    for nombre in nombres:
        datos = (directorio / nombre).read_bytes() if (directorio / nombre).exists() else b""
        lineas.append(f"{hashlib.sha256(datos).hexdigest()}  {nombre}")
    manifiesto = directorio / "MANIFIESTO"
    manifiesto.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return manifiesto


@pytest.fixture
def lote(tmp_path, claves):
    """Un lote de actualización correcto: dos .deb (contenido de juguete) firmados."""
    d = tmp_path / "usb"
    d.mkdir()
    (d / "nimbo-audit_0.1.1-1_all.deb").write_bytes(b"deb de prueba A" * 100)
    (d / "nimbo-nav_0.1.1-1_all.deb").write_bytes(b"deb de prueba B" * 100)
    claves["buena"].firmar(escribir_manifiesto(d, sorted(p.name for p in d.glob("*.deb"))))
    return d
