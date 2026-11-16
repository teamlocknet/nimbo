import importlib.util
import io
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import artifact
class Artifacts(unittest.TestCase):
    def test_roundtrip_and_wrong_digest(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp);site=r/"site";site.mkdir();(site/"index.html").write_bytes(b"public")
            digest=artifact.pack(site,r/"site.tar")
            with self.assertRaises(ValueError):artifact.receive(r/"site.tar","0"*64,r/"bad")
            artifact.receive(r/"site.tar",digest,r/"out")
            self.assertEqual((r/"out/index.html").read_bytes(),b"public")
    def test_links_traversal_duplicate(self):
        for mode in ["link","traversal","duplicate"]:
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as tmp:
                r=Path(tmp);archive=r/"a.tar"
                with tarfile.open(archive,"w") as t:
                    member=tarfile.TarInfo("../secret" if mode=="traversal" else "file")
                    if mode=="link":member.type=tarfile.SYMTYPE;member.linkname="/etc/passwd"
                    t.addfile(member,io.BytesIO())
                    if mode=="duplicate":t.addfile(member,io.BytesIO())
                with self.assertRaises(ValueError):artifact.receive(archive,artifact.aptrepo.trust.digest(archive),r/"out")
    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=Path(tmp);site=r/"site";site.mkdir();(site/"index.html").write_text("x");digest=artifact.pack(site,r/"a.tar")
            with self.assertRaises(FileExistsError):artifact.receive(r/"a.tar",digest,site)
