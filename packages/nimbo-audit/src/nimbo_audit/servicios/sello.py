"""Sello GPG del caso (ADR-021).

`custodia/sello.json` lista el SHA-256 de TODOS los archivos del caso y se firma
con la clave del analista. El SHA-256 de ese fichero es el **ancla**: se entrega
al cliente por otro canal. Sin ancla o huella, un sello válido solo dice que el
caso es coherente; quien controle el equipo podría haberlo resellado con otra clave.

Solo se usa GPG local: ninguna orden contacta con servidores de claves (RNF-01).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from nimbo_audit.errores import SelloError
from nimbo_audit.servicios.hashing import calcular_sha256
from nimbo_audit.servicios.registro import (
    ROTO,
    RUTA_CLAVE,
    RUTA_FIRMA,
    RUTA_SELLO,
    RUTAS_SELLO,
    VALIDO,
)

__all__ = [
    "HUELLA_RELEASE", "RUTA_CLAVE", "RUTA_FIRMA", "RUTA_SELLO", "SIN_SELLAR",
    "EstadoFirma", "EstadoSello", "comprobar_clave", "comprobar_sello",
    "interpretar_estado", "sellar",
]

# La clave de release firma el producto; nunca la evidencia de un cliente.
HUELLA_RELEASE = "0C50B7391A9B8CFF8A36A627D3B9111FEC5748C6"
SIN_SELLAR = "SIN SELLAR"
VERSION_SELLO = 1
_HUELLA = re.compile(r"[0-9A-F]{40}")
_SHA256 = re.compile(r"[0-9a-f]{64}")
# gpgv da código 0 y VALIDSIG también con claves revocadas: mismo criterio que #74.
_PROHIBIDOS = frozenset({"REVKEYSIG", "EXPSIG", "BADSIG", "ERRSIG", "NO_PUBKEY"})


@dataclass(frozen=True)
class EstadoFirma:
    valida: bool
    caducada: bool = False
    primaria: str = ""


@dataclass(frozen=True)
class EstadoSello:
    estado: str
    ancla: str = ""
    firmante: str = ""
    problemas: tuple[str, ...] = ()
    anclado: bool = False


def interpretar_estado(salida: str) -> EstadoFirma:
    """Exige una sola firma buena y su huella primaria en la salida de --status-fd."""
    filas = [l.split() for l in salida.splitlines() if l.startswith("[GNUPG:] ")]
    estados = [f[1] for f in filas if len(f) > 1]
    if _PROHIBIDOS.intersection(estados):
        return EstadoFirma(False)
    buenas, caducadas = estados.count("GOODSIG"), estados.count("EXPKEYSIG")
    validas = [f for f in filas if len(f) > 1 and f[1] == "VALIDSIG"]
    if buenas + caducadas != 1 or len(validas) != 1 or len(validas[0]) < 12:
        return EstadoFirma(False)
    primaria = validas[0][11]
    if not _HUELLA.fullmatch(primaria):
        return EstadoFirma(False)
    return EstadoFirma(True, caducadas == 1, primaria)


def _ejecutar(orden: list[str]) -> subprocess.CompletedProcess:
    entorno = dict(os.environ)
    try:
        entorno.setdefault("GPG_TTY", os.ttyname(0))  # pinentry pide aquí la frase
    except OSError:
        pass
    try:
        return subprocess.run(
            orden, stdin=subprocess.DEVNULL, capture_output=True, env=entorno, check=False
        )
    except OSError as exc:
        raise SelloError(f"no se pudo ejecutar {orden[0]}: {exc}") from exc


def comprobar_clave(clave: str) -> str:
    """Valida la huella antes de tocar el caso y la devuelve normalizada."""
    huella = clave.replace(" ", "").upper()
    if not _HUELLA.fullmatch(huella):
        raise SelloError("indica la huella COMPLETA de la clave (40 caracteres).")
    if huella == HUELLA_RELEASE:
        raise SelloError("la clave de release no firma evidencia: usa la clave del analista.")
    r = _ejecutar(["gpg", "--batch", "--with-colons", "--fingerprint",
                   "--list-secret-keys", huella])
    if r.returncode != 0:
        raise SelloError("no tienes la clave privada de esa huella en este equipo.")
    primarias = []
    validez = ""
    esperando = False
    for linea in r.stdout.decode("utf-8", "replace").splitlines():
        campos = linea.split(":")
        if campos[0] == "sec":
            validez, esperando = campos[1], True
        elif campos[0] == "fpr" and esperando:
            primarias.append(campos[9])
            esperando = False
    if primarias != [huella]:
        raise SelloError("usa la huella de la clave primaria.")
    if validez in ("r", "e", "d"):
        raise SelloError("esa clave está revocada o caducada.")
    return huella


def _inventario(raiz: Path) -> tuple[dict[str, str], list[str]]:
    """SHA-256 de cada archivo salvo el propio sello, y lo que no es archivo regular."""
    archivos: dict[str, str] = {}
    raros: list[str] = []
    for carpeta, dirs, nombres in os.walk(raiz):
        for nombre in [*dirs, *nombres]:
            ruta = Path(carpeta) / nombre
            relativa = ruta.relative_to(raiz).as_posix()
            if relativa in RUTAS_SELLO:
                continue
            modo = ruta.lstat().st_mode
            if stat.S_ISREG(modo):
                archivos[relativa] = calcular_sha256(ruta)
            elif not stat.S_ISDIR(modo):
                raros.append(relativa)
    return archivos, sorted(raros)


def _comprobar_firma(clave: Path, sello: Path, firma: Path) -> EstadoFirma:
    with tempfile.TemporaryDirectory(prefix="nimbo-sello-") as temporal:
        anillo = Path(temporal) / "anillo.gpg"
        r = _ejecutar(["gpg", "--homedir", temporal, "--batch", "--dearmor",
                       "--output", str(anillo), str(clave)])
        if r.returncode != 0:
            return EstadoFirma(False)
        r = _ejecutar(["gpgv", "--homedir", temporal, "--status-fd", "1",
                       "--keyring", str(anillo), str(firma), str(sello)])
    if r.returncode != 0 and b"EXPKEYSIG" not in r.stdout:
        return EstadoFirma(False)
    return interpretar_estado(r.stdout.decode("utf-8", "replace"))


def sellar(raiz: Path, huella: str, analista: str, *, ahora: datetime | None = None) -> str:
    """Firma el inventario del caso y devuelve el ancla. El sello aparece el último."""
    raiz = Path(raiz)
    archivos, raros = _inventario(raiz)
    if raros:
        raise SelloError(f"el caso contiene algo que no es un archivo: {raros[0]}")
    r = _ejecutar(["gpg", "--batch", "--armor", "--export-options", "export-minimal",
                   "--export", huella])
    if r.returncode != 0 or not r.stdout:
        raise SelloError("no se pudo exportar la clave pública.")
    clave_publica = r.stdout
    momento = ahora or datetime.now(timezone.utc)
    documento = {
        "version": VERSION_SELLO,
        "caso": raiz.name,
        "analista": analista,
        "fecha": momento.isoformat(timespec="seconds"),
        "firmante": huella,
        "clave_publica_sha256": hashlib.sha256(clave_publica).hexdigest(),
        "archivos": archivos,
    }
    texto = json.dumps(documento, ensure_ascii=False, indent=2, sort_keys=True) + "\n"

    with tempfile.TemporaryDirectory(prefix=".nimbo-sello-", dir=raiz.parent) as temporal:
        tmp = Path(temporal)
        (tmp / "clave").write_bytes(clave_publica)
        (tmp / "sello").write_text(texto, encoding="utf-8")
        r = _ejecutar(["gpg", "--batch", "--yes", "--armor", "--local-user", huella,
                       "--output", str(tmp / "firma"), "--detach-sign", str(tmp / "sello")])
        if r.returncode != 0:
            raise SelloError("GPG no pudo firmar el caso; no se selló nada.")
        firma = _comprobar_firma(tmp / "clave", tmp / "sello", tmp / "firma")
        if not firma.valida or firma.caducada or firma.primaria != huella:
            raise SelloError("la firma recién creada no se pudo comprobar; no se selló nada.")
        for origen in ("clave", "firma", "sello"):
            (tmp / origen).chmod(0o440)
        os.replace(tmp / "clave", raiz / RUTA_CLAVE)
        os.replace(tmp / "firma", raiz / RUTA_FIRMA)
        os.replace(tmp / "sello", raiz / RUTA_SELLO)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def _documento_valido(documento: object) -> bool:
    return (
        isinstance(documento, dict)
        and documento.get("version") == VERSION_SELLO
        and isinstance(documento.get("firmante"), str)
        and isinstance(documento.get("clave_publica_sha256"), str)
        and isinstance(documento.get("archivos"), dict)
    )


def comprobar_sello(
    raiz: Path, *, ancla: str | None = None, huella: str | None = None
) -> EstadoSello:
    """Comprueba el sello sin escribir nada en el caso."""
    raiz = Path(raiz)
    presentes = [r for r in RUTAS_SELLO if os.path.lexists(raiz / r)]
    if not presentes:
        if ancla or huella:
            return EstadoSello(ROTO, problemas=("el caso no tiene sello",))
        return EstadoSello(SIN_SELLAR)
    faltan = [r for r in RUTAS_SELLO if r not in presentes]
    if faltan:
        return EstadoSello(ROTO, problemas=tuple(f"AUSENTE: {r}" for r in faltan))
    if any((raiz / r).is_symlink() or not (raiz / r).is_file() for r in RUTAS_SELLO):
        return EstadoSello(ROTO, problemas=("una pieza del sello no es un archivo",))

    bytes_sello = (raiz / RUTA_SELLO).read_bytes()
    actual = hashlib.sha256(bytes_sello).hexdigest()
    problemas: list[str] = []
    anclado = False
    if ancla:
        anclado = ancla.strip().lower() == actual
        if not anclado:
            problemas.append("el ancla no coincide: este no es el sello original")
    try:
        documento = json.loads(bytes_sello.decode("utf-8"))
    except ValueError:
        documento = None
    if not _documento_valido(documento):
        return EstadoSello(ROTO, actual, problemas=(*problemas, "sello.json no es válido"))

    firmante = documento["firmante"]
    if huella:
        esperada = huella.replace(" ", "").upper()
        if esperada != firmante:
            problemas.append("la clave que firmó no es la esperada")
        else:
            anclado = anclado or not ancla
    clave = raiz / RUTA_CLAVE
    if calcular_sha256(clave) != documento["clave_publica_sha256"]:
        problemas.append("la clave pública del caso fue cambiada")
    firma = _comprobar_firma(clave, raiz / RUTA_SELLO, raiz / RUTA_FIRMA)
    if not firma.valida or firma.primaria != firmante:
        problemas.append("la firma no es válida")
    elif firma.caducada and not (ancla and anclado):
        # Una clave caducada no impide comprobar casos viejos, pero exige el ancla.
        problemas.append("la clave caducó: comprueba el caso con --ancla")

    archivos, raros = _inventario(raiz)
    registrados = documento["archivos"]
    for ruta in sorted(set(registrados) | set(archivos)):
        if ruta not in archivos:
            problemas.append(f"AUSENTE: {ruta}")
        elif ruta not in registrados:
            problemas.append(f"NO REGISTRADO: {ruta}")
        elif archivos[ruta] != registrados[ruta]:
            problemas.append(f"MODIFICADO: {ruta}")
    problemas.extend(f"NO ES UN ARCHIVO: {ruta}" for ruta in raros)

    if problemas:
        return EstadoSello(ROTO, actual, firmante, tuple(problemas))
    return EstadoSello(VALIDO, actual, firmante, anclado=anclado)
