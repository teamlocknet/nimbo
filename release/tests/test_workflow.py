import copy
import hashlib
import io
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
        promover.no_collision(API(False,False),'v1.0.0-rc1',promover.EXPECTED_SHA)
        for values in [(True,False),(False,True)]:
            with self.assertRaises(ValueError):promover.no_collision(API(*values),'v1.0.0-rc1',promover.EXPECTED_SHA)

    def test_artifact_digest_wrong(self):
        class API:
            def pages(self,*args):return [dict(name='iso',id=1,workflow_run=dict(id=2),expired=False,digest='sha256:'+'0'*64)]
            def download(self,endpoint,path):path.write_bytes(b'alterado')
        with tempfile.TemporaryDirectory() as tmp,self.assertRaises(ValueError):
            promover.artifact(API(),2,'iso',Path(tmp)/'out',{'data'},100)

    def same_name_artifacts(self, second_expired):
        content=io.BytesIO()
        with zipfile.ZipFile(content,'w') as z:z.writestr('data','bytes')
        data=content.getvalue()
        class API:
            downloaded=[]
            def pages(self,*args):
                return [dict(name='iso',id=10,workflow_run=dict(id=2),expired=second_expired,
                             digest='sha256:'+hashlib.sha256(data).hexdigest()),
                        dict(name='iso',id=20,workflow_run=dict(id=2),expired=False,
                             digest='sha256:'+hashlib.sha256(data).hexdigest())]
            def download(self,endpoint,path):
                self.downloaded.append(endpoint);path.write_bytes(data)
        return API()

    def test_artifact_expired_duplicate_selects_current(self):
        api=self.same_name_artifacts(second_expired=True)
        with tempfile.TemporaryDirectory() as tmp:
            out=promover.artifact(api,2,'iso',Path(tmp)/'out',{'data'},100)
            self.assertEqual((out/'data').read_text(),'bytes')
        self.assertEqual(api.downloaded,['actions/artifacts/20/zip'])

    def test_artifact_two_current_duplicates_rejected(self):
        api=self.same_name_artifacts(second_expired=False)
        with tempfile.TemporaryDirectory() as tmp,self.assertRaises(ValueError):
            promover.artifact(api,2,'iso',Path(tmp)/'out',{'data'},100)
        self.assertEqual(api.downloaded,[])

    def test_artifact_expired_or_wrong_run(self):
        class API:
            def __init__(self,expired,run):self.expired=expired;self.run=run
            def pages(self,*args):return [dict(name='iso',id=1,workflow_run=dict(id=self.run),expired=self.expired)]
        with tempfile.TemporaryDirectory() as tmp:
            for expired,run in [(True,2),(False,3)]:
                with self.assertRaises(ValueError):promover.artifact(API(expired,run),2,'iso',Path(tmp)/'out',{'data'},100)

    def tag_api(self,obj,rel=False):
        class API:
            posts=[]
            def api(self,endpoint,payload=None):
                if endpoint.startswith('git/matching'):
                    return [dict(ref='refs/tags/v1.0.0-rc10',object=dict(type='commit',sha='0'*40))]+(
                        [dict(ref='refs/tags/v1.0.0-rc1',object=obj)] if obj else [])
                API.posts.append(endpoint)
                return dict(id=1,html_url='https://example.invalid/draft')
            def pages(self,endpoint):return [{'tag_name':'v1.0.0-rc1'}] if rel else []
        return API()

    def test_preexisting_tag_on_candidate_accepted(self):
        # El GITHUB_TOKEN no puede crear un tag sobre un commit con otros workflows (run 43899924167).
        api=self.tag_api(dict(type='commit',sha=promover.EXPECTED_SHA))
        self.assertTrue(promover.no_collision(api,'v1.0.0-rc1',promover.EXPECTED_SHA))
        self.assertFalse(promover.no_collision(self.tag_api(None),'v1.0.0-rc1',promover.EXPECTED_SHA))

    def test_preexisting_tag_elsewhere_annotated_or_with_release_rejected(self):
        for obj,rel in [(dict(type='commit',sha='0'*40),False),
                        (dict(type='tag',sha=promover.EXPECTED_SHA),False),
                        (dict(type='commit',sha=promover.EXPECTED_SHA),True)]:
            with self.assertRaises(ValueError):
                promover.no_collision(self.tag_api(obj,rel),'v1.0.0-rc1',promover.EXPECTED_SHA)

    def test_validate_accepts_preexisting_tag_on_candidate(self):
        # Run 43904407697: validate() seguia llamando a no_collision sin el commit (TypeError).
        hasta_runs=ValueError('comprobacion de colision superada')
        for obj,esperado in [(dict(type='commit',sha=promover.EXPECTED_SHA),'comprobacion de colision superada'),
                             (dict(type='commit',sha='0'*40),'otro commit')]:
            with tempfile.TemporaryDirectory() as tmp,patch.object(promover,'validate_run',side_effect=hasta_runs):
                with self.assertRaisesRegex(ValueError,esperado):
                    promover.validate(self.tag_api(obj),promover.EXPECTED_TAG,promover.EXPECTED_SHA,1,2,Path(tmp)/'c')

    def test_draft_does_not_create_preexisting_tag(self):
        api=self.tag_api(dict(type='commit',sha=promover.EXPECTED_SHA))
        info=dict(tag=promover.EXPECTED_TAG,commit=promover.EXPECTED_SHA,iso_sha256=promover.EXPECTED_HASH)
        with tempfile.TemporaryDirectory() as tmp,patch.object(promover.verifier,'verify',return_value=info),patch.object(promover.subprocess,'run'):
            with self.assertRaises(ValueError):promover.draft(api,tmp,'A'*40)
        self.assertEqual(type(api).posts,['releases'])

    def test_draft_without_target_when_tag_preexists(self):
        # Run 43905814300: con el tag ya creado, POST releases devolvio 403; target_commitish no se usa si el tag existe.
        payloads=[]
        api=self.tag_api(dict(type='commit',sha=promover.EXPECTED_SHA))
        orig=type(api).api
        def api_espia(self,endpoint,payload=None):
            if payload is not None:payloads.append((endpoint,payload))
            return orig(self,endpoint,payload)
        type(api).api=api_espia
        info=dict(tag=promover.EXPECTED_TAG,commit=promover.EXPECTED_SHA,iso_sha256=promover.EXPECTED_HASH)
        with tempfile.TemporaryDirectory() as tmp,patch.object(promover.verifier,'verify',return_value=info),patch.object(promover.subprocess,'run'):
            with self.assertRaises(ValueError):promover.draft(api,tmp,'A'*40)
        self.assertEqual([e for e,_ in payloads],['releases'])
        self.assertNotIn('target_commitish',payloads[0][1])
        self.assertEqual(payloads[0][1]['tag_name'],promover.EXPECTED_TAG)

    def test_borrador_final_no_es_prerelease(self):
        # v1.0.0 final: el borrador de un tag final no sale como prerelease ni "candidato de pruebas".
        final=promover.datos_release('v1.0.0','a'*40,'b'*64)
        self.assertEqual((final['name'],final['draft'],final['prerelease']),('v1.0.0',True,False))
        self.assertNotIn('pruebas',final['body'])
        self.assertIn('a'*40,final['body']);self.assertIn('b'*64,final['body'])
        rc=promover.datos_release('v1.0.0-rc2','a'*40,'b'*64)
        self.assertEqual((rc['draft'],rc['prerelease']),(True,True))

    def test_valores_por_defecto_del_workflow_son_el_candidato(self):
        # El formulario de release.yml propone el mismo candidato que autoriza promover.py.
        ruta=ROOT.parent/'.github/workflows/release.yml'
        if not ruta.is_file():self.skipTest('sin el repositorio completo (CI monta solo release/)')
        yml=ruta.read_text()
        def defecto(campo):
            import re
            m=re.search(r'^      '+campo+r':\n(?:        .*\n)*?        default: \'?([^\'\n]+)\'?$',yml,re.M)
            return m and m.group(1)
        self.assertEqual(defecto('tag'),promover.EXPECTED_TAG)
        self.assertEqual(defecto('commit'),promover.EXPECTED_SHA)

    def test_github_error_names_method_and_endpoint(self):
        fallo=subprocess.CompletedProcess(['gh'],1,b'',b'gh: Resource not accessible by integration (HTTP 403)\n')
        with patch.object(promover.subprocess,'run',return_value=fallo):
            with self.assertRaisesRegex(ValueError,'POST releases'):
                promover.GitHub().api('releases',dict(tag_name='x'))
            with self.assertRaisesRegex(ValueError,'GET git/matching-refs/tags/x'):
                promover.GitHub().api('git/matching-refs/tags/x')

    def test_github_error_reports_cause(self):
        fallo=subprocess.CompletedProcess(['gh'],1,b'',b'gh: Resource not accessible by integration (HTTP 403)\n')
        with patch.object(promover.subprocess,'run',return_value=fallo):
            with self.assertRaisesRegex(ValueError,'Resource not accessible by integration'):
                promover.GitHub().api('git/refs',dict(ref='refs/tags/x',sha='0'*40))

    def test_main_prints_cause(self):
        argv=['promover.py','borrador','/no-existe','--huella','A'*40]
        out=io.StringIO()
        with patch.object(sys,'argv',argv),patch.object(promover,'draft',side_effect=ValueError('el tag ya existe en otro commit')),patch('sys.stdout',out):
            self.assertEqual(promover.main(),1)
        self.assertIn('el tag ya existe en otro commit',out.getvalue())

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
