#!/usr/bin/env python3
"""Preparacion y verificacion local de una distribucion firmada; nunca publica."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile

META = {"tag", "commit", "build_run", "repro_run", "iso_sha256", "leg_a_sha256",
        "leg_b_sha256", "qemu_iso_sha256", "qemu_evidence_url", "snapshot",
        "source_date_epoch", "base_image_digest"}
HEX = re.compile(r"[0-9a-f]{64}")
TAG = re.compile(r"v[0-9]+\.[0-9]+\.[0-9]+-rc[1-9][0-9]*")


def regular(path, limit=None):
    st = path.lstat()
    if not stat.S_ISREG(st.st_mode):
        raise ValueError("se requiere un archivo regular sin enlaces simbolicos")
    if limit is not None and st.st_size > limit:
        raise ValueError("archivo de metadatos demasiado grande")
    return path


def digest(path):
    h = hashlib.sha256()
    with regular(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def unique(pairs):
    obj = {}
    for k, v in pairs:
        if k in obj:
            raise ValueError("campo duplicado")
        obj[k] = v
    return obj


def metadata(path):
    obj = json.loads(regular(path, 16384).read_text(), object_pairs_hook=unique)
    if not isinstance(obj, dict) or set(obj) != META:
        raise ValueError("campos de procedencia desconocidos o ausentes")
    if not isinstance(obj["tag"], str) or not TAG.fullmatch(obj["tag"]):
        raise ValueError("tag prerelease invalido")
    if not isinstance(obj["commit"], str) or not re.fullmatch(r"[0-9a-f]{40}", obj["commit"]):
        raise ValueError("commit completo requerido")
    for field in ["build_run", "repro_run", "source_date_epoch"]:
        if type(obj[field]) is not int or obj[field] <= 0:
            raise ValueError("identificador/epoch invalido")
    for field in ["iso_sha256", "leg_a_sha256", "leg_b_sha256", "qemu_iso_sha256"]:
        if not isinstance(obj[field], str) or not HEX.fullmatch(obj[field]):
            raise ValueError("SHA-256 completo requerido")
        if obj[field] != obj["iso_sha256"]:
            raise ValueError("ISO, MATCH y QEMU deben corresponder a los mismos bytes")
    if not isinstance(obj["snapshot"], str) or not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z", obj["snapshot"]):
        raise ValueError("snapshot invalido")
    if not isinstance(obj["base_image_digest"], str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", obj["base_image_digest"]):
        raise ValueError("digest de imagen invalido")
    if not isinstance(obj["qemu_evidence_url"], str) or not re.fullmatch(
            r"https://github\.com/teamlocknet/nimbo/blob/[0-9a-f]{40}/repro/evidencia/[A-Za-z0-9_-][A-Za-z0-9._-]*\.md", obj["qemu_evidence_url"]):
        raise ValueError("evidencia QEMU requiere enlace blob fijado a un commit completo")
    return obj


def fingerprint(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9A-F]{40}", value):
        raise ValueError("huella primaria OpenPGP v4 completa en mayusculas requerida")
    return value


def gpg(home, *args):
    return subprocess.run(["gpg", "--no-options", "--homedir", str(home), "--batch",
        "--no-auto-key-retrieve", "--auto-key-locate", "clear", *args],
        capture_output=True, check=True, timeout=30)


def keyring(home, public, expected):
    regular(public, 1024 * 1024)
    # El llavero aislado no hereda identidades ni confianza del equipo del usuario.
    rows = gpg(home, "--with-colons", "--show-keys", str(public)).stdout.decode().splitlines()
    primary = []
    uid_count = 0
    pending = False
    for row in rows:
        fields = row.split(":")
        if fields[0] == "uid":
            uid_count += 1
        if fields[0] in ["sec", "ssb"]:
            raise ValueError("solo se permite material publico")
        if fields[0] == "pub":
            pending = True
        elif fields[0] == "fpr" and pending:
            primary.append(fields[9]); pending = False
    if uid_count != 1:
        raise ValueError("se requiere exactamente una identidad UID")
    if primary != [fingerprint(expected)]:
        raise ValueError("la clave publica no corresponde a la identidad autorizada")
    gpg(home, "--import", str(public))
    ring = home / "trusted.gpg"
    ring.write_bytes(gpg(home, "--export", expected).stdout)
    return ring


def prepare(iso, candidate, public, output, expected):
    iso, candidate, public, output = map(Path, [iso, candidate, public, output])
    if output.exists() or output.is_symlink():
        raise FileExistsError("no se sobrescribe una distribucion existente")
    info = metadata(candidate)
    if digest(iso) != info["iso_sha256"]:
        raise ValueError("la ISO no corresponde al candidato")
    with tempfile.TemporaryDirectory(prefix="nimbo-public-key-") as temp:
        keyring(Path(temp), public, expected)
    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".nimbo-release-", dir=output.parent))
    try:
        iso_name = "nimbo-" + info["tag"] + "-amd64.iso"
        shutil.copyfile(iso, staging / iso_name)
        shutil.copyfile(public, staging / "release-key.asc")
        (staging / "PROCEDENCIA.json").write_text(json.dumps(info, indent=2, sort_keys=True)+"\n")
        names = sorted([iso_name, "release-key.asc", "PROCEDENCIA.json"])
        (staging / "SHA256SUMS").write_text("".join(digest(staging/n)+"  "+n+"\n" for n in names))
        # rename no pisa directorios existentes no vacios; impedir tambien el vacio.
        output.mkdir()
        try:
            for item in staging.iterdir():
                os.rename(item, output / item.name)
        except BaseException:
            # Una salida incompleta se conserva para inspeccion y no se reutiliza.
            raise
    finally:
        shutil.rmtree(staging)


def verify(directory, expected, public=None):
    directory = Path(directory)
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("directorio de distribucion invalido")
    manifest = regular(directory / "SHA256SUMS", 8192)
    signature = regular(directory / "SHA256SUMS.asc", 1024 * 1024)
    with tempfile.TemporaryDirectory(prefix="nimbo-verify-") as temp:
        home = Path(temp)
        # El certificado externo actualizado aporta revocaciones que el adjunto
        # antiguo podria omitir; su identidad se contrasta con la misma huella.
        ring = keyring(home, directory / "release-key.asc", expected)
        if public is not None:
            # Importar ambos conserva cualquier revocacion conocida en uno de ellos.
            ring = keyring(home, Path(public), expected)
        check = subprocess.run(["gpgv", "--homedir", str(home), "--keyring", str(ring),
            "--status-fd", "1", str(signature), str(manifest)],
            capture_output=True, check=True, timeout=30)
        statuses = [line.split()[1:] for line in check.stdout.decode().splitlines()
                    if line.startswith("[GNUPG:] ")]
        forbidden = {"REVKEYSIG", "EXPKEYSIG", "EXPSIG", "BADSIG", "ERRSIG",
                     "NO_PUBKEY", "KEYEXPIRED", "SIGEXPIRED", "KEYREVOKED"}
        if any(row and row[0] in forbidden for row in statuses):
            raise ValueError("firma revocada, caducada o no valida")
        good = [row for row in statuses if row and row[0] == "GOODSIG"]
        valid = [row for row in statuses if row and row[0] == "VALIDSIG"]
        if len(good) != 1 or len(valid) != 1 or valid[0][-1] != fingerprint(expected):
            raise ValueError("firma de identidad no autorizada o ambigua")
    entries = {}
    for line in manifest.read_text(encoding="ascii").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9][A-Za-z0-9._-]*)", line)
        if not match or match[2] in entries:
            raise ValueError("entrada de manifiesto invalida o duplicada")
        entries[match[2]] = match[1]
    # Verificar bytes antes de interpretar la procedencia firmada.
    if set(entries) != {x.name for x in directory.iterdir()} - {"SHA256SUMS", "SHA256SUMS.asc"}:
        raise ValueError("distribucion incompleta o con archivos adicionales")
    for name, expected_hash in entries.items():
        if digest(directory/name) != expected_hash:
            raise ValueError("hash incorrecto: " + name)
    info = metadata(directory / "PROCEDENCIA.json")
    iso_name = "nimbo-" + info["tag"] + "-amd64.iso"
    if set(entries) != {iso_name, "PROCEDENCIA.json", "release-key.asc"}:
        raise ValueError("contenido inesperado")
    if entries[iso_name] != info["iso_sha256"]:
        raise ValueError("procedencia e ISO no coinciden")
    return info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    prep = sub.add_parser("preparar")
    for name in ["iso", "candidato", "clave-publica", "salida", "huella"]:
        prep.add_argument("--"+name, required=True)
    ver = sub.add_parser("verificar")
    ver.add_argument("directorio", type=Path)
    ver.add_argument("--huella", required=True)
    ver.add_argument("--clave", type=Path, help="certificado publico actualizado obtenido por canal independiente")
    args = parser.parse_args()
    try:
        if args.action == "preparar":
            prepare(args.iso, args.candidato, args.clave_publica, args.salida, args.huella)
            print("Preparado sin firma; no publicar todavia")
        else:
            info = verify(args.directorio, args.huella, public=args.clave)
            print("OK: firma, identidad y hashes de " + info["tag"])
        return 0
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        print("ERROR: distribucion rechazada (" + type(error).__name__ + ")")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
