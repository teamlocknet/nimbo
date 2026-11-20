#!/usr/bin/env python3
"""preparar-lotes-rnf03.py — lotes de nimbo-update-offline para la prueba sin red (RNF-03).

Genera, en el HOST, un lote de control bien firmado y lotes inválidos (uno por forma de
romper la firma o el contenido), más el anillo PÚBLICO de prueba y el fichero ESPERADO que
lee iso/live-build/rnf03-en-vm.sh dentro de la VM:

    python3 -I packages/nimbo-update-offline/pruebas/preparar-lotes-rnf03.py <destino> [--para-firmar]
    NIMBO_SIN_RED=1 NIMBO_LOTES=<destino> iso/live-build/install-in-qemu.sh arrancar

Claves: EFÍMERAS, sin frase, en un GNUPGHOME temporal que se borra al terminar. Al destino
solo llegan claves públicas (anillo-prueba.gpg) y firmas. Ninguna clave entra al repo.

La clave de prueba NO es la de nimbo: con el anillo de la ISO, el lote de control se tiene
que rechazar (y `instalar` no puede instalarlo). Con anillo-prueba.gpg (solo para
`verificar --anillo`) el control se acepta y todos los inválidos se rechazan (RF-UPD-01).

Con --para-firmar añade 20-firmado-release, SIN firma: lo firma Juan José con la clave de
release (ADR-013) y, con el anillo de la ISO, se tiene que aceptar e instalar sin red.

Solo usa la biblioteca estándar y gpg (el .deb de juguete se arma a mano: formato ar).
"""
from __future__ import annotations

import gzip
import hashlib
import io
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

PAQUETE = "nimbo-rnf03-prueba"
DEB = f"{PAQUETE}_1.0_all.deb"
EPOCA = 1794326512  # fija: el .deb de juguete sale igual en cada ejecución


def _tar_gz(miembros: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    # gzip aparte, con mtime fijo: "w:gz" escribiría la hora actual en la cabecera.
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=EPOCA) as gz, \
            tarfile.open(fileobj=gz, mode="w", format=tarfile.GNU_FORMAT) as t:
        # dpkg no crea los directorios padre: cada uno va como entrada propia (VM, 16-nov).
        dirs = sorted({"/".join(n.split("/")[:i]) for n in miembros for i in range(1, n.count("/") + 1)})
        for d in dirs:
            info = tarfile.TarInfo(d + "/")
            info.type, info.mtime, info.mode = tarfile.DIRTYPE, EPOCA, 0o755
            info.uname = info.gname = "root"
            t.addfile(info)
        for nombre, datos in miembros.items():
            info = tarfile.TarInfo(nombre)
            info.size, info.mtime, info.mode = len(datos), EPOCA, 0o644
            info.uname = info.gname = "root"
            t.addfile(info, io.BytesIO(datos))
    return buf.getvalue()


def _ar(miembros: list[tuple[str, bytes]]) -> bytes:
    out = bytearray(b"!<arch>\n")
    for nombre, datos in miembros:
        out += f"{nombre:<16}{EPOCA:<12}{0:<6}{0:<6}{'100644':<8}{len(datos):<10}`\n".encode()
        out += datos + (b"\n" if len(datos) % 2 else b"")
    return bytes(out)


def deb_de_juguete(version: str = "1.0") -> bytes:
    control = (f"Package: {PAQUETE}\nVersion: {version}\nArchitecture: all\n"
               "Maintainer: nimbo <prueba@invalid>\n"
               "Description: paquete de juguete de la prueba RNF-03 (no hace nada)\n").encode()
    leeme = f"Paquete de juguete de la prueba sin red RNF-03, versión {version}.\n".encode()
    return _ar([("debian-binary", b"2.0\n"),
                ("control.tar.gz", _tar_gz({"./control": control})),
                ("data.tar.gz", _tar_gz({f"./usr/share/doc/{PAQUETE}/LEEME": leeme}))])


class Gpg:
    def __init__(self, home: Path):
        self.home = home

    def __call__(self, *args: str, hora: str | None = None) -> bytes:
        extra = ["--faked-system-time", hora] if hora else []
        return subprocess.run(["gpg", "--homedir", str(self.home), "--batch", "--yes",
                               "--pinentry-mode", "loopback", "--passphrase", "", *extra, *args],
                              check=True, capture_output=True).stdout

    def clave(self, uid: str, caduca: str = "1d", hora: str | None = None) -> str:
        self("--quick-gen-key", uid, "ed25519", "sign", caduca, hora=hora)
        for linea in self("--with-colons", "--list-keys", uid).decode().splitlines():
            if linea.startswith("fpr:"):
                return linea.split(":")[9]
        raise RuntimeError("no encuentro la huella de " + uid)

    def firmar(self, fpr: str, fichero: Path, salida: Path, hora: str | None = None) -> None:
        self("--local-user", fpr, "--armor", "--detach-sign", "--output", str(salida), str(fichero),
             hora=hora)

    def revocar(self, fpr: str) -> None:
        cert = (self.home / "openpgp-revocs.d" / f"{fpr}.rev").read_text(encoding="utf-8")
        # gpg deja el certificado "desactivado" con ':' delante de la cabecera.
        self.importar(cert.replace(":-----BEGIN", "-----BEGIN"))

    def importar(self, texto: str) -> None:
        subprocess.run(["gpg", "--homedir", str(self.home), "--batch", "--yes", "--import"],
                       input=texto.encode(), check=True, capture_output=True)


def _manifiesto(lote: Path, nombres: list[str]) -> Path:
    lineas = [f"{hashlib.sha256((lote / n).read_bytes() if (lote / n).exists() else b'').hexdigest()}  {n}"
              for n in nombres]
    m = lote / "MANIFIESTO"
    m.write_text("".join(x + "\n" for x in lineas), encoding="utf-8")
    return m


def preparar(destino: Path, para_firmar: bool = False) -> list[tuple[str, str, str]]:
    destino = Path(destino)
    if destino.exists():
        raise FileExistsError(f"{destino} ya existe: no se sobrescribe nada")
    deb = deb_de_juguete()
    esperado: list[tuple[str, str, str]] = []
    home = Path(tempfile.mkdtemp(prefix="nimbo-rnf03-gpg-"))
    try:
        home.chmod(0o700)
        g = Gpg(home)
        buena = g.clave("nimbo-rnf03-PRUEBA <prueba@invalid>")
        otra = g.clave("atacante-rnf03-PRUEBA <atacante@invalid>")
        revocada = g.clave("revocada-rnf03-PRUEBA <revocada@invalid>")
        # Caducó en 2020: la firma se hace "en 2020", cuando aún valía; hoy la clave está caducada.
        caducada = g.clave("caducada-rnf03-PRUEBA <caducada@invalid>", "1d", hora="20200101T000000")
        destino.mkdir(parents=True)

        def lote(nombre: str, firma: str | None = buena, debs: dict[str, bytes] | None = None,
                 lista: list[str] | None = None, hora: str | None = None) -> Path:
            d = destino / nombre
            d.mkdir()
            debs = {DEB: deb} if debs is None else debs
            for n, datos in debs.items():
                (d / n).write_bytes(datos)
            m = _manifiesto(d, list(debs) if lista is None else lista)
            if firma:
                g.firmar(firma, m, d / "MANIFIESTO.asc", hora=hora)
            esperado.append((nombre, "prueba", "ACEPTADO" if nombre.startswith("00-") else "RECHAZADO"))
            return d

        d = lote("00-control")
        esperado += [("00-control", "nimbo", "RECHAZADO"), ("00-control", "instalar", "RECHAZADO")]
        lote("01-sin-firma", firma=None)
        d = lote("02-sin-manifiesto"); (d / "MANIFIESTO").unlink()
        lote("03-otra-clave", firma=otra)
        d = lote("04-manifiesto-alterado")
        with (d / "MANIFIESTO").open("a", encoding="utf-8") as f:
            f.write(f"{'0' * 64}  colado_1.0_all.deb\n")
        d = lote("05-deb-alterado")
        datos = bytearray((d / DEB).read_bytes()); datos[-2] ^= 0xFF; (d / DEB).write_bytes(bytes(datos))
        d = lote("06-deb-extra"); (d / "colado_1.0_all.deb").write_bytes(deb_de_juguete("6.6"))
        lote("07-deb-faltante", debs={}, lista=[DEB])
        d = lote("08-firma-de-otro-fichero")
        otro = d / "otro.txt"; otro.write_text("otro fichero\n", encoding="utf-8")
        g.firmar(buena, otro, d / "MANIFIESTO.asc"); otro.unlink()
        d = lote("09-firma-basura")
        (d / "MANIFIESTO.asc").write_text("-----BEGIN PGP SIGNATURE-----\n\nbasura\n"
                                          "-----END PGP SIGNATURE-----\n", encoding="utf-8")
        lote("10-nombre-con-ruta", debs={}, lista=["../" + DEB])
        lote("11-manifiesto-vacio", debs={}, lista=[])
        lote("12-clave-revocada", firma=revocada)
        lote("13-clave-caducada", firma=caducada, hora="20200101T120000")

        if para_firmar:
            # Parte 2: SIN firma. Lo firma Juan José con la clave de release (ADR-013); con el
            # anillo de la ISO se tiene que aceptar e instalar sin red.
            d = destino / "20-firmado-release"
            d.mkdir()
            (d / DEB).write_bytes(deb)
            _manifiesto(d, [DEB])
            esperado += [("20-firmado-release", "nimbo", "ACEPTADO"),
                         ("20-firmado-release", "instalar", "INSTALADO")]

        g.revocar(revocada)
        # Anillo PÚBLICO: la buena, la revocada (con su revocación) y la caducada. La "otra" no.
        (destino / "anillo-prueba.gpg").write_bytes(g("--export", buena, revocada, caducada))
        (destino / "ESPERADO").write_text(
            "# <lote> <prueba|nimbo|instalar> <resultado> — lo lee iso/live-build/rnf03-en-vm.sh\n"
            + "".join(f"{a} {b} {c}\n" for a, b, c in esperado), encoding="utf-8")
    finally:
        subprocess.run(["gpgconf", "--homedir", str(home), "--kill", "gpg-agent"], capture_output=True)
        shutil.rmtree(home, ignore_errors=True)
    return esperado


def main(argv: list[str]) -> int:
    para_firmar = "--para-firmar" in argv
    args = [a for a in argv[1:] if a != "--para-firmar"]
    if len(args) != 1:
        print(__doc__.split("\n\n")[1])
        return 2
    filas = preparar(Path(args[0]), para_firmar)
    inv = sum(1 for _, m, r in filas if m == "prueba" and r == "RECHAZADO")
    print(f"Lotes en {args[0]}: 1 de control y {inv} inválidos. Claves privadas borradas.")
    if para_firmar:
        print(f"Falta firmar con la clave de release: {args[0]}/20-firmado-release/MANIFIESTO")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
