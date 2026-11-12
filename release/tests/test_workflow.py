import copy
import importlib.util
import json
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import promover
import firmar


class Gates(unittest.TestCase):
    def run_fixture(self):
        return dict(path=".github/workflows/build-iso.yml",event="push",head_branch="main",
            head_sha=promover.EXPECTED_SHA,status="completed",conclusion="success",
            repository=dict(full_name=promover.REPO),head_repository=dict(full_name=promover.REPO))

    def test_run_control(self):
        promover.validate_run(self.run_fixture(),"build-iso.yml",promover.EXPECTED_SHA)

    def test_run_wrong_provenance(self):
        for field,value in [('path','.github/workflows/otro.yml'),('event','pull_request'),
                            ('head_branch','otra'),('head_sha','0'*40),('status','in_progress'),
                            ('conclusion','failure'),('head_repository',dict(full_name='ajeno/repo'))]:
            with self.subTest(field=field),self.assertRaises(ValueError):
                promover.validate_run(dict(self.run_fixture(),**{field:value}),"build-iso.yml",promover.EXPECTED_SHA)

    def qemu(self):
        return ("NIMBO_APROBACION_QEMU\niso_sha256: "+promover.EXPECTED_HASH+
            "\ncommit: "+promover.EXPECTED_SHA+"\nverificar_instalado: OK \u2014 0 fallos\n"
            "secure_boot: exigido\naprobado_por: Juan Jos\u00e9 (@Duque-Londono)\nNIMBO_APROBACION_QEMU_FIN")

    def test_qemu_control(self):
        promover.qemu(self.qemu(),promover.EXPECTED_SHA,promover.EXPECTED_HASH)

    def test_qemu_absent_duplicate_or_wrong_hash(self):
        for text in ['',self.qemu()+"\n"+self.qemu(),self.qemu().replace(promover.EXPECTED_HASH,'0'*64)]:
            with self.subTest(text=text[:20]),self.assertRaises(ValueError):
                promover.qemu(text,promover.EXPECTED_SHA,promover.EXPECTED_HASH)

    def test_zip_traversal_link_duplicate_extra(self):
        cases=[['../data'],['data','data'],['data','extra'],['symlink']]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for i,names in enumerate(cases):
                zpath=root/(str(i)+'.zip')
                with zipfile.ZipFile(zpath,'w') as z:
                    for name in names:
                        if name=='symlink':
                            member=zipfile.ZipInfo('data');member.external_attr=(stat.S_IFLNK|0o777)<<16
                            z.writestr(member,'/tmp/externo')
                        else:z.writestr(name,'bytes')
                with self.assertRaises(ValueError):promover.extract_archive(zpath,root/str(i),{'data'},100)

    def test_zip_control_and_size(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);zpath=root/'a.zip'
            with zipfile.ZipFile(zpath,'w') as z:z.writestr('data','bytes')
            promover.extract_archive(zpath,root/'ok',{'data'},100)
            self.assertEqual((root/'ok/data').read_text(),'bytes')
            with self.assertRaises(ValueError):promover.extract_archive(zpath,root/'bad',{'data'},1)

    def test_collision_tag_or_release(self):
        class API:
            def __init__(self,tag,rel):self.tag=tag;self.rel=rel
            def api(self,endpoint):return [{'ref':'refs/tags/v1.0.0-rc1'}] if self.tag else []
            def pages(self,endpoint):return [{'tag_name':'v1.0.0-rc1'}] if self.rel else []
        promover.no_collision(API(False,False),'v1.0.0-rc1')
        for values in [(True,False),(False,True)]:
            with self.assertRaises(ValueError):promover.no_collision(API(*values),'v1.0.0-rc1')

    def test_artifact_digest_wrong(self):
        class API:
            def pages(self,*args):return [dict(name='iso',id=1,workflow_run=dict(id=2),expired=False,digest='sha256:'+'0'*64)]
            def download(self,endpoint,path):path.write_bytes(b'alterado')
        with tempfile.TemporaryDirectory() as tmp,self.assertRaises(ValueError):
            promover.artifact(API(),2,'iso',Path(tmp)/'out',{'data'},100)

    def test_artifact_expired_or_wrong_run(self):
        class API:
            def __init__(self,expired,run):self.expired=expired;self.run=run
            def pages(self,*args):return [dict(name='iso',id=1,workflow_run=dict(id=self.run),expired=self.expired)]
        with tempfile.TemporaryDirectory() as tmp:
            for expired,run in [(True,2),(False,3)]:
                with self.assertRaises(ValueError):promover.artifact(API(expired,run),2,'iso',Path(tmp)/'out',{'data'},100)

    def test_upload_failure_never_reports_verified(self):
        class API:
            def api(self,endpoint,payload=None):
                if endpoint.startswith('git/matching'):return []
                return dict(id=1,html_url='https://example.invalid/draft')
            def pages(self,*args):return []
        info=dict(tag=promover.EXPECTED_TAG,commit=promover.EXPECTED_SHA,iso_sha256=promover.EXPECTED_HASH)
        with tempfile.TemporaryDirectory() as tmp,patch.object(promover.verifier,'verify',return_value=info),patch.object(promover.subprocess,'run',side_effect=subprocess.CalledProcessError(1,['gh'])):
            with self.assertRaises(subprocess.CalledProcessError):promover.draft(API(),tmp,'A'*40)

    def test_incomplete_release(self):
        class API:
            def api(self,endpoint,payload=None):
                if endpoint.startswith('git/matching'):return []
                return dict(id=1,html_url='https://example.invalid/draft')
            def pages(self,endpoint):return []
        info=dict(tag=promover.EXPECTED_TAG,commit=promover.EXPECTED_SHA,iso_sha256=promover.EXPECTED_HASH)
        with tempfile.TemporaryDirectory() as tmp,patch.object(promover.verifier,'verify',return_value=info),patch.object(promover.subprocess,'run'):
            with self.assertRaises(ValueError):promover.draft(API(),tmp,'A'*40)

    def secret_rows(self,primary='#',expiry='200',validity='-'):
        def row(kind,token,caps,exp):
            f=['']*18;f[0]=kind;f[1]=validity;f[6]=exp;f[11]=caps;f[14]=token;return ':'.join(f)
        return row('sec',primary,'c','')+'\nfpr:::::::::'+'A'*40+':\n'+row('ssb','+','s',expiry)+'\nfpr:::::::::'+'B'*40+':'

    def test_only_expiring_subkey(self):
        self.assertEqual(firmar.select_subkey(self.secret_rows(),'A'*40,100),'B'*40)
        for kwargs in [dict(primary='+'),dict(expiry=''),dict(expiry='50'),dict(validity='r')]:
            with self.subTest(kwargs=kwargs),self.assertRaises(ValueError):
                firmar.select_subkey(self.secret_rows(**kwargs),'A'*40,100)

    def test_no_sign_before_adr_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            adr=Path(tmp)/'ADR.md';adr.write_text('**Estado:** Propuesto.')
            with self.assertRaises(ValueError):firmar.sign(Path(tmp)/'bundle',Path(tmp)/'out','A'*40,b'',b'',adr)

if __name__=='__main__':unittest.main()
