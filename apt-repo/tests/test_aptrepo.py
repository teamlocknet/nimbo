import datetime as dt
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"apt-repo"))
import aptrepo as apt

class AptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix="nimbo-apt-tests-")
        cls.root=Path(cls.tmp.name);cls.home=cls.root/"keys";cls.home.mkdir(mode=0o700)
        cls.env=dict(os.environ,GNUPGHOME=str(cls.home))
        cls.gpg("--batch","--pinentry-mode","loopback","--passphrase","",
                "--quick-generate-key","APT test","ed25519","cert","1y")
        rows=cls.gpg("--with-colons","--list-keys").stdout.decode()
        cls.primary=next(x.split(":")[9] for x in rows.splitlines() if x.startswith("fpr:"))
        cls.gpg("--batch","--pinentry-mode","loopback","--passphrase","",
                "--quick-add-key",cls.primary,"ed25519","sign","1y")
        cls.public=cls.gpg("--armor","--export",cls.primary).stdout
        cls.secret=cls.gpg("--batch","--pinentry-mode","loopback","--passphrase","",
                           "--armor","--export-secret-subkeys",cls.primary).stdout
        cls.debs=cls.root/"debs";cls.debs.mkdir()
        for name in apt.modules():
            pkg=cls.root/name;(pkg/"DEBIAN").mkdir(parents=True)
            (pkg/"DEBIAN/control").write_text("Package: "+name+"\nVersion: 0.1.0-1\nArchitecture: all\nMaintainer: Test <test@example.invalid>\nDescription: fixture; no publicar\n")
            apt.command(["dpkg-deb","--build","--root-owner-group",str(pkg),str(cls.debs/(name+"_0.1.0-1_all.deb"))])
        (cls.debs/"BUILD.json").write_text(json.dumps(dict(commit="a"*40,source_date_epoch=1794500000,
            snapshot="20260901T000000Z",base_image_digest="sha256:"+"a"*64,
            packages={p.name:apt.trust.digest(p) for p in cls.debs.glob("*.deb")})))
        cls.unsigned=cls.root/"unsigned"
        apt.prepare(cls.debs,cls.unsigned,"a"*40,1794500000,"20260901T000000Z","sha256:"+"a"*64)
        (cls.unsigned/"apt/release-key.asc").write_bytes(cls.public)
        cls.adr=cls.root/"ADR";cls.adr.write_text("**Estado:** Aceptado.")
        cls.signed=cls.root/"signed"
        apt.sign(cls.unsigned,cls.signed,apt.bundle_digest(cls.unsigned),cls.primary,cls.secret,b"",cls.adr)

    @classmethod
    def gpg(cls,*args):
        return subprocess.run(["gpg",*args],env=cls.env,capture_output=True,check=True)
    @classmethod
    def tearDownClass(cls):
        subprocess.run(["gpgconf","--kill","gpg-agent"],env=cls.env,capture_output=True)
        cls.tmp.cleanup()
    def setUp(self):
        self.case=tempfile.TemporaryDirectory(dir=self.root);self.base=Path(self.case.name)
    def tearDown(self):self.case.cleanup()
    def copy(self,signed=True):
        out=self.base/"site";shutil.copytree(self.signed if signed else self.unsigned,out);return out
    def verify(self,site,**kw):return apt.verify_tree(site,signed=True,expected=self.primary,**kw)

    def test_real_aptly_and_two_real_signatures(self):
        info=self.verify(self.signed);self.assertEqual(len(info["packages"]),5)
    def test_exact_30_days(self):
        f=apt.paragraphs((self.signed/"apt/dists/bookworm/Release").read_text())[0]
        self.assertEqual((apt.email.utils.parsedate_to_datetime(f["Valid-Until"])-apt.email.utils.parsedate_to_datetime(f["Date"])).total_seconds(),30*86400)
    def test_expired_release(self):
        with self.assertRaises(ValueError):self.verify(self.signed,now=dt.datetime.now(dt.timezone.utc)+dt.timedelta(days=31))
    def test_wrong_identity(self):
        with self.assertRaises(ValueError):apt.verify_tree(self.signed,signed=True,expected="B"*40)
    def test_tampered_release(self):
        s=self.copy();p=s/"apt/dists/bookworm/Release";p.write_bytes(p.read_bytes()+b"X")
        with self.assertRaises((ValueError,subprocess.SubprocessError)):self.verify(s)
    def test_tampered_inrelease(self):
        s=self.copy();p=s/"apt/dists/bookworm/InRelease";p.write_bytes(p.read_bytes().replace(b"bookworm",b"alterado",1))
        with self.assertRaises((ValueError,subprocess.SubprocessError)):self.verify(s)
    def test_tampered_index(self):
        s=self.copy();p=next((s/"apt/dists").rglob("Packages"));p.write_bytes(p.read_bytes()+b"X")
        with self.assertRaises(ValueError):self.verify(s)
    def test_tampered_deb(self):
        s=self.copy();p=next((s/"apt/pool").rglob("*.deb"));p.write_bytes(p.read_bytes()+b"X")
        with self.assertRaises(ValueError):self.verify(s)
    def test_missing_package(self):
        s=self.copy();next((s/"apt/pool").rglob("*.deb")).unlink()
        with self.assertRaises(OSError):self.verify(s)
    def test_extra_file(self):
        s=self.copy();(s/"secret.key").write_text("extra")
        with self.assertRaises(ValueError):self.verify(s)
    def test_symlink(self):
        s=self.copy();p=next((s/"apt/pool").rglob("*.deb"));p.unlink();p.symlink_to("/etc/passwd")
        with self.assertRaises(ValueError):self.verify(s)
    def test_wrong_artifact_digest(self):
        with self.assertRaises(ValueError):apt.sign(self.unsigned,self.base/"out","0"*64,self.primary,self.secret,b"",self.adr)
        self.assertFalse((self.base/"out").exists())
    def test_no_overwrite(self):
        with self.assertRaises(FileExistsError):apt.sign(self.unsigned,self.signed,apt.bundle_digest(self.unsigned),self.primary,self.secret,b"",self.adr)
    def test_primary_secret_rejected(self):
        secret=self.gpg("--batch","--pinentry-mode","loopback","--passphrase","","--armor","--export-secret-keys",self.primary).stdout
        with self.assertRaises(ValueError):apt.sign(self.unsigned,self.base/"out",apt.bundle_digest(self.unsigned),self.primary,secret,b"",self.adr)
    def test_no_sign_before_adr(self):
        self.adr_copy=self.base/"ADR";self.adr_copy.write_text("**Estado:** Propuesto.")
        with self.assertRaises(ValueError):apt.sign(self.unsigned,self.base/"out",apt.bundle_digest(self.unsigned),self.primary,self.secret,b"",self.adr_copy)

    def test_final_requires_exact_tag_commit(self):
        from unittest.mock import patch
        original=apt.command
        def command(args,**kwargs):
            if args[:2]==["git","-C"]:return ("b"*40+"\n").encode()
            return original(args,**kwargs)
        with patch.object(apt,"command",side_effect=command),self.assertRaises(ValueError):
            apt.prepare(self.debs,self.base/"out","a"*40,1794500000,"20260901T000000Z","sha256:"+"a"*64,candidate=False)
        self.assertFalse((self.base/"out").exists())

    def exceptional_key(self,expired=False):
        home=self.base/"exception";home.mkdir(mode=0o700);env=dict(os.environ,GNUPGHOME=str(home))
        def g(*args,input=None):
            return subprocess.run(["gpg",*args],env=env,input=input,capture_output=True,check=True).stdout
        clock=int(time.time())-3*86400 if expired else int(time.time())
        fake=["--faked-system-time",str(clock)]
        try:
            g(*fake,"--batch","--pinentry-mode","loopback","--passphrase","","--quick-generate-key","APT negative","ed25519","cert","1y")
            primary=next(x.split(":")[9] for x in g("--with-colons","--list-keys").decode().splitlines() if x.startswith("fpr:"))
            g(*fake,"--batch","--pinentry-mode","loopback","--passphrase","","--quick-add-key",primary,"ed25519","sign","1d" if expired else "1y")
            site=self.copy();release=site/"apt/dists/bookworm/Release"
            for target,mode in [("InRelease","--clearsign"),("Release.gpg","--detach-sign")]:
                (release.parent/target).unlink()
                g(*fake,"--batch","--yes","--pinentry-mode","loopback","--passphrase","","--armor","--local-user",primary,mode,"--output",str(release.parent/target),str(release))
            if not expired:
                g("--batch","--yes","--command-fd","0","--status-fd","1","--edit-key",primary,
                  input=b"key 1\nrevkey\ny\n0\n\ny\nsave\n")
                rows=g("--with-colons","--list-keys",primary).decode();self.assertIn("sub:r:",rows)
            (site/"apt/release-key.asc").write_bytes(g("--armor","--export",primary))
            return site,primary
        finally:subprocess.run(["gpgconf","--homedir",str(home),"--kill","gpg-agent"],capture_output=True)

    def test_revoked_subkey_real_signature_rejected(self):
        site,primary=self.exceptional_key()
        with self.assertRaises((ValueError,subprocess.SubprocessError)):apt.verify_tree(site,signed=True,expected=primary)
    def test_expired_subkey_real_signature_rejected(self):
        site,primary=self.exceptional_key(expired=True)
        with self.assertRaises((ValueError,subprocess.SubprocessError)):apt.verify_tree(site,signed=True,expected=primary)
    def test_good_and_valid_required(self):
        for status in [b"[GNUPG:] VALIDSIG "+" ".join(["A"]*9+[self.primary]).encode(),
                       b"[GNUPG:] GOODSIG abc Test\n"]:
            with self.assertRaises(ValueError):apt.trust.signature_status(status,self.primary)
    def test_all_error_statuses_rejected(self):
        for status in ["REVKEYSIG","EXPKEYSIG","EXPSIG","BADSIG","ERRSIG","NO_PUBKEY"]:
            with self.assertRaises(ValueError):
                apt.trust.signature_status(("[GNUPG:] "+status+" test\n").encode(),self.primary)
    def test_traversal(self):
        for name in ["../etc/passwd","/etc/passwd","pool/../secret","pool//x"]:
            with self.assertRaises(ValueError):apt.safe_file(self.signed,name)

if __name__=="__main__":unittest.main()
