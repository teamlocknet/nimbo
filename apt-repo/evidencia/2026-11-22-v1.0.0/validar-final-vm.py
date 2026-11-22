#!/usr/bin/env python3
"""Instrumentacion externa al checkout: validar Pages final en VM desechable."""
from pathlib import Path, PurePosixPath
import argparse, datetime as dt, email.utils, hashlib, json, os, shutil
import subprocess, sys, tempfile, urllib.request

COMMIT = '94f9b8fec60938baccae984f891cc3ac6960e109'
WORKFLOW_COMMIT = '23cd07974fad0037904ab71cdb75323a79957559'
FPR = '0C50B7391A9B8CFF8A36A627D3B9111FEC5748C6'
VERSIONS = {'nimbo-audit':'0.1.0-1','nimbo-nav':'0.1.5-1','nimbo-net':'0.1.0-1','nimbo-red':'0.1.1-1','nimbo-update-offline':'0.1.2-1'}
BASE = 'https://teamlocknet.github.io/nimbo/'
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('fase', choices=['verificar','instalar','negativas'])
p.add_argument('--checkout', type=Path, default=Path('/var/tmp/nimbo-v1.0.0'))
p.add_argument('--salida', type=Path, default=Path('/var/tmp/nimbo-apt-final-evidencia'))
a = p.parse_args(); root=a.checkout.resolve(); out=a.salida.resolve()
out.mkdir(parents=True, exist_ok=True)
os.environ.update(LC_ALL='C.UTF-8', DEBIAN_FRONTEND='noninteractive', PYTHONDONTWRITEBYTECODE='1')
sys.path.insert(0,str(root/'apt-repo'))
import aptrepo
import release as trust

def save(name,obj):
    (out/name).write_text(json.dumps(obj,sort_keys=True,indent=2)+'\n')
def command(name,args,cwd=None,env=None,ok=True):
    start=dt.datetime.now(dt.timezone.utc).isoformat()
    result=subprocess.run(args,cwd=cwd or root,env=env,capture_output=True,text=True)
    (out/(name+'.stdout.log')).write_text(result.stdout)
    (out/(name+'.stderr.log')).write_text(result.stderr)
    save(name+'.json',dict(argv=list(map(str,args)),cwd=str(cwd or root),inicio_utc=start,fin_utc=dt.datetime.now(dt.timezone.utc).isoformat(),exit_code=result.returncode))
    if ok and result.returncode:raise RuntimeError(name+' fallo: '+str(result.returncode))
    return result

def fetch(url,path):
    path.parent.mkdir(parents=True,exist_ok=True)
    request=urllib.request.Request(url,headers={'User-Agent':'nimbo-RF-DIST-01-validacion','Cache-Control':'no-cache'})
    with urllib.request.urlopen(request,timeout=90) as response:
        raw=response.read(16*1024*1024+1)
        assert len(raw)<=16*1024*1024
        path.write_bytes(raw)
        downloads.append(dict(url=url,url_final=response.url,archivo=str(path.relative_to(out)),sha256=hashlib.sha256(raw).hexdigest(),size=len(raw),fecha_utc=dt.datetime.now(dt.timezone.utc).isoformat(),etag=response.headers.get('ETag')))
    save('DESCARGAS.json',downloads)
    return path

def safename(name):
    assert not PurePosixPath(name).is_absolute() and all(part not in ('','.','..') for part in name.split('/')) and '\\' not in name
    return name

def check_tag():
    head=command('git-head',['git','rev-parse','HEAD']).stdout.strip()
    tag=command('git-tag',['git','rev-parse','refs/tags/v1.0.0^{commit}']).stdout.strip()
    assert head==tag==COMMIT
    for name,version in VERSIONS.items():
        assert (root/'packages'/name/'debian/changelog').read_text().splitlines()[0].startswith(name+' ('+version+')')
    assert not command('git-status',['git','status','--porcelain','--untracked-files=no']).stdout.strip()

check_tag()
if (out/(a.fase+'-OK.json')).exists():raise RuntimeError('fase ya completada; no se repite')
site=out/'pages'; dist=site/'apt/dists/bookworm'
downloads=json.loads((out/'DESCARGAS.json').read_text()) if (out/'DESCARGAS.json').exists() else []
if a.fase=='verificar':
    baseline={}
    for name in VERSIONS:
        r=subprocess.run(['dpkg-query','-W','-f=${db:Status-Abbrev} ${Version}',name],capture_output=True,text=True)
        baseline[name]=r.stdout.strip()
        assert not r.stdout.startswith('ii ')
    sourcefiles=[Path('/etc/apt/sources.list'),*Path('/etc/apt/sources.list.d').glob('*')]
    assert not any('teamlocknet.github.io/nimbo' in f.read_text(errors='replace') for f in sourcefiles if f.is_file())
    assert not Path('/usr/share/keyrings/nimbo-release.asc').exists()
    keyfiles=[Path('/etc/apt/trusted.gpg'),*Path('/etc/apt/trusted.gpg.d').glob('*'),*Path('/usr/share/keyrings').glob('*')]
    with tempfile.TemporaryDirectory(prefix='nimbo-baseline-key-') as tmp:
        for key in keyfiles:
            if key.is_file():
                r=subprocess.run(['gpg','--homedir',tmp,'--batch','--with-colons','--show-keys',str(key)],capture_output=True,text=True)
                assert FPR not in r.stdout
    save('BASELINE.json',dict(modulos=baseline,fuente_nimbo=False,clave_nimbo_en_llaveros_apt=False,os_release=Path('/etc/os-release').read_text(),kernel=command('uname',['uname','-a']).stdout.strip()))
    assert 'VERSION_CODENAME=bookworm' in Path('/etc/os-release').read_text()
    for name in ['apt','gnupg','python3','aptly','git','qemu-guest-agent']:
        command('version-'+name,['dpkg-query','-W','-f=${Package}\t${Version}\n',name])
    for name in ['apt/dists/bookworm/Release','apt/dists/bookworm/InRelease','apt/dists/bookworm/Release.gpg','apt/release-key.asc','index.html']:
        fetch(BASE+name,site/name)
    independent=fetch('https://raw.githubusercontent.com/teamlocknet/nimbo/'+WORKFLOW_COMMIT+'/release/nimbo-release-publica.asc',out/'clave-canal-independiente.asc')
    with tempfile.TemporaryDirectory(prefix='nimbo-verifica-final-') as tmp:
        home=Path(tmp); ring=trust.keyring(home,site/'apt/release-key.asc',FPR)
        ring=trust.keyring(home,independent,FPR)
        command('huella',['gpg','--homedir',str(home),'--batch','--no-default-keyring','--keyring',str(ring),'--with-colons','--fingerprint','--list-keys'])
        for label,args in [('firma-separada',[str(dist/'Release.gpg'),str(dist/'Release')]),('firma-inrelease',['--output',str(home/'plain'),str(dist/'InRelease')])]:
            r=command(label,['gpgv','--homedir',str(home),'--keyring',str(ring),'--status-fd','1',*args])
            trust.signature_status(r.stdout.encode(),FPR)
        assert (home/'plain').read_bytes()==(dist/'Release').read_bytes()
    fields=aptrepo.paragraphs((dist/'Release').read_text())[0]
    indexed=aptrepo.entries(fields['SHA256'])
    for name,(sha,size) in indexed.items():
        fetch(BASE+'apt/dists/bookworm/'+safename(name),dist/name)
        aptrepo.check_hash(dist,name,sha,size)
    # .nojekyll no se sirve como contenido en Pages. Solo marca local para verify_tree.
    (site/'.nojekyll').write_text('')
    rows=[]
    for name in indexed:
        if name.endswith('/Packages') and (dist/name).stat().st_size:
            rows+=aptrepo.paragraphs((dist/name).read_text())
    for row in rows:
        path=site/'apt'/safename(row['Filename'])
        if not path.exists():fetch(BASE+'apt/'+row['Filename'],path)
    info=aptrepo.verify_tree(site,signed=True,public=independent,expected=FPR)
    assert info['candidate'] is False and info['release_tag']=='v1.0.0' and info['commit']==COMMIT
    assert {x['name']:x['version'] for x in info['packages']}==VERSIONS
    save('PROCEDENCIA-verificada.json',info)
    date=email.utils.parsedate_to_datetime(fields['Date']); until=email.utils.parsedate_to_datetime(fields['Valid-Until'])
    assert (until-date).total_seconds()==30*86400
    save('verificar-OK.json',dict(commit=COMMIT,huella=FPR,candidate=False,release_tag='v1.0.0',date_utc=date.isoformat(),valid_until_utc=until.isoformat(),marcador_nojekyll='archivo vacio creado localmente; no descargado'))
elif a.fase=='instalar':
    assert (out/'verificar-OK.json').is_file()
    independent=out/'clave-canal-independiente.asc'
    info=aptrepo.verify_tree(site,signed=True,public=independent,expected=FPR)
    assert info['commit']==COMMIT and info['candidate'] is False
    key=Path('/usr/share/keyrings/nimbo-release.asc'); assert not key.exists()
    shutil.copyfile(independent,key);key.chmod(0o644)
    source=Path('/etc/apt/sources.list.d/nimbo-final-validacion.list');assert not source.exists()
    source.write_text('deb [arch=amd64 signed-by=/usr/share/keyrings/nimbo-release.asc] '+BASE+'apt/ bookworm main\n')
    shutil.copyfile(source,out/'nimbo-final-validacion.list')
    specs=[name+'='+version for name,version in sorted(VERSIONS.items())]
    command('apt-update',['apt-get','-o','APT::Update::Error-Mode=any','update'])
    command('apt-policy',['apt-cache','policy',*sorted(VERSIONS)])
    download=out/'descargas-apt';download.mkdir();download.chmod(0o755)
    command('apt-download',['apt-get','download',*specs],cwd=download)
    expected={x['name']:x for x in info['packages']}; hashes={}
    for deb in download.glob('*.deb'):
        name=subprocess.check_output(['dpkg-deb','-f',str(deb),'Package'],text=True).strip()
        sha=hashlib.sha256(deb.read_bytes()).hexdigest();assert sha==expected[name]['sha256']
        hashes[deb.name]=sha
    assert len(hashes)==5
    save('HASHES-descargas-apt.json',hashes)
    command('apt-install',['apt-get','install','-y','--no-install-recommends',*specs])
    r=command('dpkg-instalados',['dpkg-query','-W','-f=${Package}\t${Version}\t${db:Status-Abbrev}\n',*sorted(VERSIONS)])
    installed={row.split('\t')[0]:row.split('\t')[1] for row in r.stdout.splitlines() if row.split('\t')[2].startswith('ii ')}
    assert installed==VERSIONS
    save('instalar-OK.json',dict(versiones=installed,paquetes=hashes))
else:
    assert (out/'instalar-OK.json').is_file()
    instrument=out/'instrumentacion';instrument.mkdir(exist_ok=True)
    (instrument/'sitecustomize.py').write_text("""import os,subprocess,json,pathlib,datetime,inspect
_original=subprocess.run
def _run(*args,**kwargs):
    r=_original(*args,**kwargs)
    cmd=args[0] if args else kwargs.get('args',[])
    if isinstance(cmd,(list,tuple)) and cmd and pathlib.Path(str(cmd[0])).name=='apt-get':
        def text(x):return x.decode(errors='replace') if isinstance(x,bytes) else x
        row=dict(test=next((f.function for f in inspect.stack() if f.function.startswith('test_real_apt_')),None),argv=list(map(str,cmd)),exit_code=r.returncode,stdout=text(r.stdout),stderr=text(r.stderr),utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
        with open(os.environ['NIMBO_APT_OBSERVACION'],'a') as f:f.write(json.dumps(row)+'\\n')
    return r
subprocess.run=_run
""")
    env=os.environ.copy();env['PYTHONPATH']=str(instrument);env['NIMBO_APT_OBSERVACION']=str(out/'apt-negativas-subprocesos.jsonl')
    command('test-apt-transport',['python3','-m','unittest','discover','-s','apt-repo/tests','-p','test_apt_transport.py','-v'],env=env)
    records=[json.loads(line) for line in (out/'apt-negativas-subprocesos.jsonl').read_text().splitlines()]
    assert len(records)==6 and sum(x['exit_code']!=0 for x in records)==3
    check_tag()
    save('negativas-OK.json',dict(tests=4,exit_code=0,subprocesos_apt=len(records),rechazos_apt=sum(x['exit_code']!=0 for x in records),checkout_sin_cambios=True))
print('OK:',a.fase,flush=True)
