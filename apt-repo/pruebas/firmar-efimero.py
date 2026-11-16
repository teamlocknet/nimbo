#!/usr/bin/env python3
"""Solo laboratorio: clave efimera, nunca usa ni configura la clave real."""
from pathlib import Path
import json,os,subprocess,sys,tempfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import aptrepo as apt
site,out,evidence=map(Path,sys.argv[1:])
with tempfile.TemporaryDirectory(prefix="nimbo-apt-fixture-") as tmp:
    home=Path(tmp);env=dict(os.environ,GNUPGHOME=str(home))
    def g(*args):return subprocess.run(["gpg",*args],env=env,capture_output=True,check=True).stdout
    try:
        g("--batch","--pinentry-mode","loopback","--passphrase","","--quick-generate-key","NIMBO APT LAB NO PUBLICAR","ed25519","cert","1d")
        primary=next(x.split(":")[9] for x in g("--with-colons","--list-keys").decode().splitlines() if x.startswith("fpr:"))
        g("--batch","--pinentry-mode","loopback","--passphrase","","--quick-add-key",primary,"ed25519","sign","1d")
        public=g("--armor","--export",primary);(site/"apt/release-key.asc").write_bytes(public)
        secret=g("--batch","--pinentry-mode","loopback","--passphrase","","--armor","--export-secret-subkeys",primary)
        adr=home/"ADR";adr.write_text("**Estado:** Aceptado.")
        signer=apt.sign(site,out,apt.bundle_digest(site),primary,secret,b"",adr)
        (evidence/"firma-laboratorio.json").write_text(json.dumps(dict(fingerprint=primary,subkey=signer,solo_laboratorio=True),indent=2))
        (evidence/"clave-laboratorio.asc").write_bytes(public)
    finally:subprocess.run(["gpgconf","--kill","gpg-agent"],env=env,capture_output=True)
