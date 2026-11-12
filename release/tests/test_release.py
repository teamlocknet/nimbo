import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]

class ReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("release_tool", ROOT / "release.py")
        cls.tool = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.tool)
        cls.tmp = tempfile.TemporaryDirectory(prefix="nimbo-release-test-")
        cls.home = Path(cls.tmp.name) / "keys"
        cls.home.mkdir(mode=0o700)
        cls.env = dict(os.environ, GNUPGHOME=str(cls.home))
        cls.fingerprints = []
        for uid in ["Release test A", "Release test B"]:
            cls.gpg("--batch", "--pinentry-mode", "loopback", "--passphrase", "",
                    "--quick-generate-key", uid, "ed25519", "sign", "1d")
        rows = cls.gpg("--with-colons", "--list-keys").stdout.decode().splitlines()
        cls.fingerprints = [x.split(":")[9] for x in rows if x.startswith("fpr:")]

    @classmethod
    def gpg(cls, *args):
        return subprocess.run(["gpg", *args], env=cls.env, capture_output=True, check=True)

    @classmethod
    def tearDownClass(cls):
        subprocess.run(["gpgconf", "--kill", "gpg-agent"], env=cls.env, capture_output=True)
        cls.tmp.cleanup()

    def setUp(self):
        self.tmpcase = tempfile.TemporaryDirectory(dir=self.tmp.name)
        self.base = Path(self.tmpcase.name)
        self.iso = self.base / "input.iso"
        self.iso.write_bytes(b"ISO DE PRUEBA; NO PUBLICAR\n")
        digest = hashlib.sha256(self.iso.read_bytes()).hexdigest()
        self.provenance = dict(tag="v1.0.0-rc1", commit="a"*40, build_run=42850483095,
            repro_run=42850482997, iso_sha256=digest, leg_a_sha256=digest,
            leg_b_sha256=digest, qemu_iso_sha256=digest,
            qemu_evidence_url="https://github.com/teamlocknet/nimbo/blob/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/repro/evidencia/prueba-qemu.md",
            snapshot="20260901T000000Z", source_date_epoch=1794186923,
            base_image_digest="sha256:"+"b"*64)
        self.metadata = self.base / "candidate.json"
        self.metadata.write_text(json.dumps(self.provenance))
        self.key = self.base / "public.asc"
        self.key.write_bytes(self.gpg("--armor", "--export", self.fingerprints[0]).stdout)
        self.out = self.base / "dist"

    def tearDown(self):
        self.tmpcase.cleanup()

    def prepare(self):
        self.tool.prepare(self.iso, self.metadata, self.key, self.out, self.fingerprints[0])

    def sign(self, fingerprint=None):
        sig = self.gpg("--batch", "--armor", "--local-user", fingerprint or self.fingerprints[0],
            "--detach-sign", "--output", "-", str(self.out / "SHA256SUMS")).stdout
        (self.out / "SHA256SUMS.asc").write_bytes(sig)

    def ready(self):
        self.prepare()
        self.sign()

    def verify(self):
        return self.tool.verify(self.out, self.fingerprints[0])

    def bad(self):
        with self.assertRaises((ValueError, OSError, subprocess.SubprocessError)):
            self.verify()

    def test_R01_integral(self):
        self.ready(); self.verify()

    def test_R02_iso_alterada(self):
        self.ready(); next(self.out.glob("*.iso")).write_bytes(b"alterada"); self.bad()

    def test_R03_manifiesto_alterado(self):
        self.ready(); p=self.out/"SHA256SUMS"; p.write_bytes(p.read_bytes()+b"x"); self.bad()

    def test_R04_firma_truncada(self):
        self.ready(); (self.out/"SHA256SUMS.asc").write_bytes(b"truncada"); self.bad()

    def test_R05_firma_ausente(self):
        self.ready(); (self.out/"SHA256SUMS.asc").unlink(); self.bad()

    def test_R06_otra_identidad(self):
        self.prepare(); self.sign(self.fingerprints[1]); self.bad()

    def test_R07_iso_ausente(self):
        self.ready(); next(self.out.glob("*.iso")).unlink(); self.bad()

    def test_R08_archivo_no_listado(self):
        self.ready(); (self.out/"otra.iso").write_bytes(b"extra"); self.bad()

    def test_R09_rutas(self):
        for name in ["/tmp/externa.iso", "../externa.iso"]:
            with self.subTest(name=name):
                if self.out.exists(): shutil.rmtree(self.out)
                self.prepare(); p=self.out/"SHA256SUMS"
                p.write_text("a"*64+"  "+name+"\n"); self.sign(); self.bad()

    def test_R10_duplicado(self):
        self.prepare(); p=self.out/"SHA256SUMS"; p.write_bytes(p.read_bytes()*2)
        self.sign(); self.bad()

    def test_candidato_sin_match_o_qemu(self):
        for field in ["leg_a_sha256", "leg_b_sha256", "qemu_iso_sha256"]:
            with self.subTest(field=field):
                value=dict(self.provenance, **{field:"c"*64}); self.metadata.write_text(json.dumps(value))
                with self.assertRaises(ValueError): self.prepare()
                self.assertFalse(self.out.exists())

    def test_no_sobrescribe(self):
        self.ready()
        with self.assertRaises(FileExistsError): self.prepare()
        self.verify()

    def test_enlace_simbolico(self):
        self.ready(); iso=next(self.out.glob("*.iso")); iso.unlink(); iso.symlink_to(self.iso); self.bad()

    def test_subclave_vinculada(self):
        self.gpg("--batch", "--pinentry-mode", "loopback", "--passphrase", "",
                 "--quick-generate-key", "Release subkey test", "ed25519", "cert", "1d")
        rows=self.gpg("--with-colons", "--list-keys", "Release subkey test").stdout.decode().splitlines()
        primary=next(x.split(":")[9] for x in rows if x.startswith("fpr:"))
        self.gpg("--batch", "--pinentry-mode", "loopback", "--passphrase", "",
                 "--quick-add-key", primary, "ed25519", "sign", "1d")
        self.key.write_bytes(self.gpg("--armor", "--export", primary).stdout)
        self.tool.prepare(self.iso, self.metadata, self.key, self.out, primary)
        self.sign(primary)
        self.tool.verify(self.out, primary)

    def subkey_identity(self, expired=False):
        created = int(time.time()) - (3*86400 if expired else 0)
        clock = ["--faked-system-time", str(created)] if expired else []
        uid = ("Expired signing test " if expired else "Revoked signing test ") + self.base.name
        self.gpg(*clock, "--batch", "--pinentry-mode", "loopback", "--passphrase", "",
                 "--quick-generate-key", uid, "ed25519", "cert", "30d")
        rows=self.gpg("--with-colons", "--list-keys", uid).stdout.decode().splitlines()
        primary=next(x.split(":")[9] for x in rows if x.startswith("fpr:"))
        self.gpg(*clock, "--batch", "--pinentry-mode", "loopback", "--passphrase", "",
                 "--quick-add-key", primary, "ed25519", "sign", "1d")
        return primary, created

    def publish_subkey_case(self, expired=False, external=False):
        primary, created = self.subkey_identity(expired)
        old = self.gpg("--armor", "--export", primary).stdout
        updated = old
        if not expired:
            copy = self.base / "revoked-home"
            shutil.copytree(self.home, copy, ignore=shutil.ignore_patterns("S.gpg-agent*", "*.lock"))
            env=dict(self.env, GNUPGHOME=str(copy))
            try:
                subprocess.run(["gpg", "--batch", "--yes", "--command-fd", "0",
                    "--status-fd", "1", "--edit-key", primary], input=b"key 1\nrevkey\ny\n0\n\ny\nsave\n",
                    env=env, capture_output=True, check=True)
                rows=subprocess.run(["gpg", "--with-colons", "--list-keys", primary],
                    env=env, capture_output=True, check=True).stdout.decode().splitlines()
                self.assertTrue(any(x.startswith("sub:r:") for x in rows), "fixture no revocada")
                updated=subprocess.run(["gpg", "--armor", "--export", primary], env=env,
                    capture_output=True, check=True).stdout
            finally:
                subprocess.run(["gpgconf", "--kill", "gpg-agent"], env=env, capture_output=True)
        self.key.write_bytes(old if external else updated)
        self.tool.prepare(self.iso, self.metadata, self.key, self.out, primary)
        clock=["--faked-system-time",str(created+3600)] if expired else []
        sig=self.gpg(*clock,"--batch","--armor","--local-user",primary,"--detach-sign",
            "--output","-",str(self.out/"SHA256SUMS")).stdout
        (self.out/"SHA256SUMS.asc").write_bytes(sig)
        return primary, updated

    def test_subclave_revocada(self):
        primary,_=self.publish_subkey_case()
        with self.assertRaises((ValueError, subprocess.SubprocessError)):
            self.tool.verify(self.out,primary)

    def test_subclave_caducada_despues_de_firmar(self):
        primary,_=self.publish_subkey_case(expired=True)
        with self.assertRaises((ValueError, subprocess.SubprocessError)):
            self.tool.verify(self.out,primary)

    def test_certificado_externo_actualizado(self):
        primary,updated=self.publish_subkey_case(external=True)
        self.tool.verify(self.out,primary)  # certificado antiguo incluido aun no conoce revocacion
        fresh=self.base/"updated.asc";fresh.write_bytes(updated)
        with self.assertRaises((ValueError, subprocess.SubprocessError)):
            self.tool.verify(self.out,primary,public=fresh)

    def test_certificado_externo_antiguo_no_borra_revocacion(self):
        primary,_=self.publish_subkey_case()
        old=self.base/"old.asc";old.write_bytes(self.gpg("--armor","--export",primary).stdout)
        with self.assertRaises((ValueError,subprocess.SubprocessError)):
            self.tool.verify(self.out,primary,public=old)

    def test_uid_adicional(self):
        self.gpg("--batch", "--pinentry-mode", "loopback", "--passphrase", "",
                 "--quick-add-uid", self.fingerprints[1], "Otra identidad de prueba")
        self.key.write_bytes(self.gpg("--armor", "--export", self.fingerprints[1]).stdout)
        with self.assertRaises(ValueError):
            self.tool.prepare(self.iso,self.metadata,self.key,self.out,self.fingerprints[1])

    def test_evidencia_blob_fijada(self):
        self.prepare()  # acepta blob del commit completo
        for url in ["https://github.com/teamlocknet/nimbo/blob/main/repro/evidencia/qemu.md",
                    "https://github.com/teamlocknet/nimbo/pull/73"]:
            self.metadata.write_text(json.dumps(dict(self.provenance,qemu_evidence_url=url)))
            with self.assertRaises(ValueError): self.tool.metadata(self.metadata)

    def test_clave_publica_distinta(self):
        self.key.write_bytes(self.gpg("--armor", "--export", self.fingerprints[1]).stdout)
        with self.assertRaises(ValueError): self.prepare()

if __name__ == "__main__":
    unittest.main()
