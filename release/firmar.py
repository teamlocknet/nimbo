#!/usr/bin/env python3
"""Firma en environment aprobado con subclave; nunca crea tags ni releases."""
from contextlib import contextmanager
import argparse
import hashlib
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time

import release as verifier


def select_subkey(rows, expected, now):
    primary=[];subs=[];current=None
    for line in rows.splitlines():
        f=line.split(":")
        if f[0] in ["sec","ssb"]:
            if len(f)<15:
                raise ValueError("registro de clave incompleto")
            current=dict(kind=f[0],validity=f[1],expiry=f[6],caps=f[11],secret=f[14])
            (primary if f[0]=="sec" else subs).append(current)
        elif f[0]=="fpr" and current is not None:
            current["fingerprint"]=f[9];current=None
    if len(primary)!=1 or primary[0].get("fingerprint")!=verifier.fingerprint(expected):
        raise ValueError("identidad primaria no autorizada")
    if primary[0]["secret"]!="#":
        raise ValueError("la clave primaria secreta no puede estar en CI")
    if primary[0]["validity"] in ["r","e","d","i"]:
        raise ValueError("primaria no vigente")
    if primary[0]["expiry"] and int(primary[0]["expiry"])<=now:
        raise ValueError("primaria caducada")
    signing=[]
    for s in subs:
        if "s" not in s["caps"]:
            continue
        if (s["secret"]!="+" or s["validity"] in ["r","e","d","i"] or
                not s["expiry"] or int(s["expiry"])<=now or "D" in s["caps"]):
            raise ValueError("subclave de firma no disponible, revocada o sin caducidad vigente")
        verifier.fingerprint(s.get("fingerprint"))
        signing.append(s["fingerprint"])
    if len(signing)!=1:
        raise ValueError("se requiere una sola subclave de firma utilizable")
    return signing[0]


@contextmanager
def signing_key(expected, secret):
    """Llavero efimero compartido: solo una subclave vigente, primaria offline."""
    with tempfile.TemporaryDirectory(prefix="nimbo-signing-") as tmp:
        home = Path(tmp)
        def call(*args, input=None):
            p = subprocess.run(["gpg", "--no-options", "--homedir", str(home), "--batch",
                "--no-auto-key-retrieve", "--auto-key-locate", "clear", *args],
                input=input, capture_output=True, timeout=120)
            if p.returncode:
                raise ValueError("operacion GPG de firma rechazada")
            return p.stdout
        try:
            call("--import", input=secret)
            signer = select_subkey(call("--with-colons", "--list-secret-keys").decode(), expected, int(time.time()))
            public = home / "public.asc"
            public.write_bytes(call("--armor", "--export", expected))
            verifier.keyring(home, public, expected)
            yield home, call, signer, public
        finally:
            subprocess.run(["gpgconf", "--homedir", str(home), "--kill", "gpg-agent"], capture_output=True)


def sign_document(call, signer, source, output, passphrase, clearsign=False):
    """Firma un fichero existente y confirma la subclave realmente utilizada."""
    if Path(output).exists():
        raise FileExistsError("no se sobrescribe una firma")
    status = call("--pinentry-mode", "loopback", "--passphrase-fd", "0",
        "--local-user", signer+"!", "--armor", "--digest-algo", "SHA256", "--status-fd", "1",
        "--clearsign" if clearsign else "--detach-sign", "--output", str(output), str(source),
        input=passphrase+b"\n").decode()
    created = [line.split() for line in status.splitlines() if line.startswith("[GNUPG:] SIG_CREATED ")]
    if len(created) != 1 or created[0][-1] != signer:
        raise ValueError("firmante efectivo incorrecto")


def sign(bundle, output, expected, secret, passphrase, adr):
    # La firma requiere la decision versionada de Juan Jose en ADR-015.
    if not re.search(r"^\*\*Estado:\*\* Aceptado(?:[. ;]|$)", Path(adr).read_text(),re.M):
        raise ValueError("ADR-015 aun no esta Aceptado")
    bundle=Path(bundle);info=verifier.metadata(bundle/"candidate.json")
    if verifier.digest(bundle/"candidate.iso")!=info["iso_sha256"]:
        raise ValueError("candidato alterado")
    with signing_key(expected, secret) as (home, call, signer, public):
        verifier.prepare(bundle/"candidate.iso", bundle/"candidate.json", public, output, expected)
        sign_document(call, signer, Path(output)/"SHA256SUMS", Path(output)/"SHA256SUMS.asc", passphrase)
        verifier.verify(output, expected)
        return signer


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("bundle");p.add_argument("salida");p.add_argument("--adr",required=True)
    args=p.parse_args()
    # No heredar material privado en subprocesos ni pasarlo como argumentos.
    secret=os.environ.pop("RELEASE_GPG_SUBKEY","").encode()
    passphrase=os.environ.pop("RELEASE_GPG_PASSPHRASE","").encode()
    expected=os.environ.pop("RELEASE_GPG_FINGERPRINT","")
    try:
        if not secret:raise ValueError("subclave no configurada")
        signer=sign(args.bundle,args.salida,expected,secret,passphrase,args.adr)
        output=os.environ.get("GITHUB_OUTPUT")
        if output:
            with open(output,"a") as stream:stream.write("fingerprint_sha256="+hashlib.sha256(expected.encode()).hexdigest()+"\n")
        print("OK: firma verificada; subclave publica "+signer)
        return 0
    except (ValueError,KeyError,OSError,subprocess.SubprocessError):
        print("ERROR: firma rechazada; no publicar")
        return 1

if __name__=="__main__":raise SystemExit(main())
