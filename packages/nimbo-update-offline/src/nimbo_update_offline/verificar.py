"""Verificación de un lote de actualización sin conexión (ADR-013, RF-UPD-01).

Un LOTE es un directorio (normalmente en una USB) con:
  * los paquetes `*.deb`;
  * `MANIFIESTO`: una línea "<sha256>  <nombre.deb>" por paquete;
  * `MANIFIESTO.asc`: firma GPG separada del MANIFIESTO, hecha con la clave de
    actualizaciones de nimbo (la custodia Juan José; nunca entra al repositorio).

Se acepta SOLO si todo esto se cumple; ante cualquier duda, se rechaza:
  1. Existen MANIFIESTO y MANIFIESTO.asc.
  2. `gpgv` valida la firma contra el anillo de confianza de nimbo (y solo ese).
  3. El manifiesto no está vacío, no repite nombres y cada nombre es un .deb sin rutas.
  4. Los .deb del directorio son exactamente los del manifiesto (ni más ni menos).
  5. El SHA-256 de cada .deb coincide con el del manifiesto.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

ANILLO = Path("/usr/share/nimbo/keyrings/nimbo-actualizaciones.gpg")
NOMBRE_VALIDO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.+_~-]*\.deb$")
LINEA = re.compile(r"^([0-9a-f]{64})  (\S+)$")


@dataclass
class Veredicto:
    aceptado: bool
    motivo: str
    paquetes: list[Path] = field(default_factory=list)


def _rechazo(motivo: str) -> Veredicto:
    return Veredicto(False, motivo, [])


def _sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def _ruta(p: Path) -> str:
    """Ruta absoluta para gpgv. En Debian no cambia nada; solo en Windows (pruebas con el
    gpgv de Git/MSYS) se escribe como /c/..."""
    s = str(Path(p).resolve())
    if os.name == "nt" and len(s) > 2 and s[1] == ":":
        return "/" + s[0].lower() + s[2:].replace("\\", "/")
    return s


def firma_valida(manifiesto: Path, firma: Path, anillo: Path) -> bool:
    gpgv = shutil.which("gpgv")
    if not gpgv or not anillo.is_file():
        return False
    r = subprocess.run([gpgv, "--status-fd", "1", "--keyring", _ruta(anillo),
                        _ruta(firma), _ruta(manifiesto)], capture_output=True, text=True)
    return r.returncode == 0 and "[GNUPG:] VALIDSIG" in r.stdout


def verificar(directorio: Path, anillo: Path = ANILLO) -> Veredicto:
    directorio = Path(directorio)
    manifiesto = directorio / "MANIFIESTO"
    firma = directorio / "MANIFIESTO.asc"

    if not manifiesto.is_file() or not firma.is_file():
        return _rechazo("lote sin firma: faltan MANIFIESTO o MANIFIESTO.asc")
    if not firma_valida(manifiesto, firma, Path(anillo)):
        return _rechazo("firma inválida: el MANIFIESTO no está firmado por la clave de "
                        "actualizaciones de nimbo, o fue modificado después de firmarse")

    esperados: dict[str, str] = {}
    for n, linea in enumerate(manifiesto.read_text(encoding="utf-8").splitlines(), 1):
        if not linea.strip():
            continue
        m = LINEA.match(linea)
        if not m:
            return _rechazo(f"manifiesto mal formado en la línea {n}")
        suma, nombre = m.groups()
        if not NOMBRE_VALIDO.match(nombre):
            return _rechazo(f"nombre no permitido en el manifiesto: {nombre!r}")
        if nombre in esperados:
            return _rechazo(f"nombre repetido en el manifiesto: {nombre}")
        esperados[nombre] = suma
    if not esperados:
        return _rechazo("manifiesto vacío: no hay paquetes que instalar")

    presentes = {p.name for p in directorio.glob("*.deb")}
    extra = sorted(presentes - set(esperados))
    if extra:
        return _rechazo(f"el paquete {extra[0]} no está firmado (no figura en el MANIFIESTO)")
    faltan = sorted(set(esperados) - presentes)
    if faltan:
        return _rechazo(f"falta el paquete {faltan[0]}, que figura en el MANIFIESTO")

    for nombre, suma in sorted(esperados.items()):
        if _sha256(directorio / nombre) != suma:
            return _rechazo(f"paquete alterado: el SHA-256 de {nombre} no coincide con el firmado")

    return Veredicto(True, f"{len(esperados)} paquetes con firma válida",
                     [directorio / n for n in sorted(esperados)])
