"""APT real sin instalar ni modificar fuentes del host: todo el estado es temporal."""
import functools
import http.server
import os
import pwd
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
import unittest
import test_aptrepo as fixtures

class AptTransport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.AptTests.setUpClass()
    @classmethod
    def tearDownClass(cls):
        fixtures.AptTests.tearDownClass()
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="nimbo-apt-client-");self.root=Path(self.tmp.name)
        self.site=self.root/"site";shutil.copytree(fixtures.AptTests.signed,self.site)
        class Handler(http.server.SimpleHTTPRequestHandler):
            def log_message(self,*args):pass
        self.server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(Handler,directory=str(self.site)))
        threading.Thread(target=self.server.serve_forever,daemon=True).start()
        self.key=self.root/"key.asc";self.key.write_bytes(fixtures.AptTests.public)
        self.source=self.root/"sources.list";self.source.write_text("deb [arch=amd64 signed-by="+str(self.key)+"] http://127.0.0.1:"+str(self.server.server_port)+"/apt bookworm main\n")
        for d in ["lists/partial","cache/archives/partial","download"]:(self.root/d).mkdir(parents=True)
        self.options=["-o","Dir::Etc::sourcelist="+str(self.source),"-o","Dir::Etc::sourceparts=-",
            "-o","Dir::State::lists="+str(self.root/"lists"),"-o","Dir::Cache="+str(self.root/"cache"),
            "-o","APT::Update::Error-Mode=any","-o","APT::Sandbox::User="+pwd.getpwuid(os.getuid()).pw_name]
    def tearDown(self):
        self.server.shutdown();self.server.server_close();self.tmp.cleanup()
    def call(self,*args):
        return subprocess.run(["apt-get",*self.options,*args],cwd=self.root/"download",capture_output=True,text=True)
    def test_real_apt_update_and_download(self):
        p=self.call("update");self.assertEqual(p.returncode,0,p.stderr)
        p=self.call("download","nimbo-net=0.1.0-1");self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(len(list((self.root/"download").glob("nimbo-net*.deb"))),1)
    def test_real_apt_rejects_metadata_tampering(self):
        path=self.site/"apt/dists/bookworm/InRelease";path.write_bytes(path.read_bytes().replace(b"Origin: nimbo",b"Origin: other",1))
        self.assertNotEqual(self.call("update").returncode,0)
    def test_real_apt_rejects_wrong_identity(self):
        self.key.write_bytes((fixtures.ROOT/"release/nimbo-release-publica.asc").read_bytes())
        self.assertNotEqual(self.call("update").returncode,0)
    def test_real_apt_rejects_deb_tampering(self):
        p=self.call("update");self.assertEqual(p.returncode,0,p.stderr)
        path=next((self.site/"apt/pool").rglob("nimbo-net*.deb"));path.write_bytes(path.read_bytes()+b"alterado")
        self.assertNotEqual(self.call("download","nimbo-net=0.1.0-1").returncode,0)
