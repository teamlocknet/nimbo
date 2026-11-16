#!/usr/bin/env python3
"""Repositorio APT de candidato: aptly genera; release/ firma y verifica."""
import argparse
import datetime as dt
import email.utils
import gzip
import bz2
import hashlib
import importlib.util
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "release"))
import release as trust
import firmar
FINGERPRINT = "0C50B7391A9B8CFF8A36A627D3B9111FEC5748C6"
MODULES = ROOT / "iso/live-build/config/includes.chroot/usr/share/nimbo/modulos.list"
TTL = 30 * 86400
SIGNED = {"apt/dists/bookworm/InRelease", "apt/dists/bookworm/Release.gpg"}

def command(args, **kwargs):
    result = subprocess.run(args, capture_output=True, timeout=600, **kwargs)
    if result.returncode:
        raise ValueError(str(args[0])+": "+result.stderr.decode(errors="replace")[-1000:]+result.stdout.decode(errors="replace")[-1000:])
    return result.stdout

def modules():
    return [x.strip() for x in MODULES.read_text().splitlines() if x.strip() and not x.lstrip().startswith("#")]

def safe_file(root, name):
    p = PurePosixPath(name)
    if p.is_absolute() or not p.parts or any(x in ("..", ".", "") for x in name.split("/")) or "\\" in name:
        raise ValueError("ruta de repositorio no permitida")
    dest = root.joinpath(*p.parts)
    current = root
    for part in p.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("enlace no permitido")
    return trust.regular(dest)

def all_files(root):
    if root.is_symlink() or not root.is_dir():
        raise ValueError("directorio no valido")
    result = {}
    for p in root.rglob("*"):
        if p.is_symlink():
            raise ValueError("enlace no permitido")
        if p.is_file():
            name = p.relative_to(root).as_posix()
            result[name] = trust.digest(safe_file(root, name))
        elif not p.is_dir():
            raise ValueError("objeto no regular")
    return result

def bundle_digest(root):
    records = all_files(Path(root))
    return hashlib.sha256("".join(h+"  "+n+"\n" for n,h in sorted(records.items())).encode()).hexdigest()

def paragraphs(text):
    result=[]
    for paragraph in text.strip().split("\n\n"):
        fields={};last=None
        for line in paragraph.splitlines():
            if line.startswith((" ", "\t")):
                if last is None: raise ValueError("continuacion invalida")
                fields[last]+="\n"+line[1:]
            else:
                key, sep, value=line.partition(":")
                if not sep or key in fields:raise ValueError("campo invalido o duplicado")
                fields[key]=value.lstrip();last=key
        result.append(fields)
    return result

def entries(text):
    result={}
    for line in text.splitlines():
        if not line.strip():continue
        row=line.split()
        if len(row)!=3 or not re.fullmatch("[0-9a-f]{64}",row[0]) or not row[1].isdigit() or row[2] in result:
            raise ValueError("indice SHA256 invalido")
        result[row[2]]=(row[0],int(row[1]))
    return result

def check_hash(root, name, expected, size):
    path=safe_file(root,name)
    if path.stat().st_size!=size or trust.digest(path)!=expected:
        raise ValueError("bytes alterados: "+name)
    return path

def verify_tree(site, signed=False, public=None, expected=FINGERPRINT, now=None):
    site=Path(site);files=all_files(site)
    release=site/"apt/dists/bookworm/Release"
    if signed:
        with tempfile.TemporaryDirectory(prefix="nimbo-apt-verify-") as temp:
            home=Path(temp)
            ring=trust.keyring(home,site/"apt/release-key.asc",expected)
            if public is not None:ring=trust.keyring(home,Path(public),expected)
            for sig,source in [(site/"apt/dists/bookworm/Release.gpg",release),
                               (site/"apt/dists/bookworm/InRelease",None)]:
                args=["gpgv","--homedir",str(home),"--keyring",str(ring),"--status-fd","1"]
                if source is None:
                    plain=home/"plain";args+=["--output",str(plain),str(trust.regular(sig))]
                else:args += [str(trust.regular(sig)),str(release)]
                check=command(args);trust.signature_status(check,expected)
                if source is None and plain.read_bytes()!=release.read_bytes():
                    raise ValueError("InRelease y Release distintos")
    elif set(files)&SIGNED:
        raise ValueError("el artifact sin firma contiene firmas")
    records=paragraphs(trust.regular(release,2*1024*1024).read_text())
    if len(records)!=1:raise ValueError("Release debe tener un solo parrafo")
    fields=records[0]
    if (fields.get("Suite"),fields.get("Codename"),fields.get("Components"),fields.get("Origin"))!=("bookworm","bookworm","main","nimbo"):
        raise ValueError("identidad de Release incorrecta")
    if set(fields.get("Architectures","").split())!={"amd64","all"}:
        raise ValueError("arquitecturas incorrectas")
    date=email.utils.parsedate_to_datetime(fields["Date"])
    until=email.utils.parsedate_to_datetime(fields["Valid-Until"])
    if date.tzinfo is None or until.tzinfo is None or int((until-date).total_seconds())!=TTL:
        raise ValueError("Valid-Until debe ser 30 dias exactos")
    current=dt.datetime.now(dt.timezone.utc) if now is None else now
    if date>current+dt.timedelta(minutes=5) or until<=current:
        raise ValueError("Release futuro o caducado")
    indexed=entries(fields["SHA256"])
    provenance="PROCEDENCIA.json"
    if provenance not in indexed:raise ValueError("procedencia no cubierta por Release")
    allowed={"index.html",".nojekyll","apt/release-key.asc","apt/dists/bookworm/Release"}
    if signed:allowed |= SIGNED
    package_rows=[]
    for name,(digest,size) in indexed.items():
        path=check_hash(site/"apt/dists/bookworm",name,digest,size)
        allowed.add("apt/dists/bookworm/"+name)
        if name.endswith(("/Packages.gz", "/Packages.bz2")):
            raw_name=name.rsplit(".",1)[0]
            if raw_name not in indexed:raise ValueError("indice comprimido sin original")
            raw=trust.regular(safe_file(site/"apt/dists/bookworm",raw_name),2*1024*1024).read_bytes()
            opener=gzip.open if name.endswith(".gz") else bz2.open
            with opener(path,"rb") as stream:plain=stream.read(2*1024*1024+1)
            if plain!=raw:raise ValueError("indices comprimidos distintos")
        if name.endswith("/Packages"):
            package_rows += paragraphs(path.read_text()) if path.stat().st_size else []
    info=json.loads((release.parent/provenance).read_text(),object_pairs_hook=trust.unique)
    if not re.fullmatch("[0-9a-f]{40}",info["commit"]) or info["suite"]!="bookworm" or info["component"]!="main":
        raise ValueError("procedencia invalida")
    if type(info["candidate"]) is not bool or info.get("release_tag")!=(None if info["candidate"] else "v1.0.0"):
        raise ValueError("candidato y tag final incoherentes")
    names=modules()
    expected_packages={p["name"]:p for p in info["packages"]}
    if set(expected_packages)!=set(names) or len(info["packages"])!=len(names):
        raise ValueError("lista de modulos incompleta o duplicada")
    seen={}
    for row in package_rows:
        name=row["Package"]
        if name not in expected_packages or row["Architecture"]!="all":raise ValueError("paquete inesperado")
        p=expected_packages[name];filename=row["Filename"]
        path=check_hash(site/"apt",filename,row["SHA256"],int(row["Size"]))
        if (row["Version"],row["SHA256"])!=(p["version"],p["sha256"]):raise ValueError("paquete y procedencia distintos")
        if name in seen and seen[name]!=filename:raise ValueError("paquete ambiguo")
        seen[name]=filename;allowed.add("apt/"+filename)
        # dpkg-deb labels multiple fields, so inspect each individually.
        for field,value in [("Package",name),("Version",p["version"]),("Architecture","all")]:
            if command(["dpkg-deb","-f",str(path),field]).decode().strip()!=value:
                raise ValueError("cabecera deb no coincide")
    if set(seen)!=set(names):raise ValueError("faltan paquetes en Packages")
    if set(files)!=allowed:raise ValueError("sitio incompleto o contiene archivos no declarados")
    return info

def prepare(debs, site, commit, epoch, snapshot, image, published=None, candidate=True):
    debs=Path(debs);site=Path(site)
    if site.exists():raise FileExistsError("salida existente")
    if not re.fullmatch("[0-9a-f]{40}",commit):raise ValueError("commit completo requerido")
    if not re.fullmatch("[0-9]{8}T[0-9]{6}Z",snapshot) or not re.fullmatch("sha256:[0-9a-f]{64}",image):
        raise ValueError("anclaje invalido")
    if epoch<=0:raise ValueError("epoch invalido")
    if not candidate:
        tag_commit=command(["git","-C",str(ROOT),"rev-parse","refs/tags/v1.0.0^{commit}"]).decode().strip()
        if tag_commit!=commit:raise ValueError("v1.0.0 no apunta al commit seleccionado")
    build=json.loads(trust.regular(debs/"BUILD.json",65536).read_text(),object_pairs_hook=trust.unique)
    if (build["commit"],build["source_date_epoch"],build["snapshot"],build["base_image_digest"])!=(commit,epoch,snapshot,image):
        raise ValueError("anclaje y BUILD.json distintos")
    actual={p.name:trust.digest(p) for p in debs.glob("*.deb")}
    if actual!=build["packages"] or set(all_files(debs))!=set(actual)|{"BUILD.json"}:
        raise ValueError("BUILD.json o conjunto de paquetes alterado")
    date=dt.datetime.now(dt.timezone.utc).replace(microsecond=0) if published is None else published
    records=[];packages=sorted(debs.glob("*.deb"))
    for path in packages:
        trust.regular(path)
        values=[command(["dpkg-deb","-f",str(path),f]).decode().strip() for f in ["Package","Version","Architecture"]]
        if values[0] not in modules() or values[2]!="all":raise ValueError("deb inesperado")
        records.append(dict(name=values[0],version=values[1],sha256=trust.digest(path)))
    if sorted(x["name"] for x in records)!=sorted(modules()):raise ValueError("se requieren exactamente los cinco modulos")
    with tempfile.TemporaryDirectory(prefix="nimbo-aptly-") as temp:
        work=Path(temp);config=work/"aptly.json";aptroot=work/"aptly"
        config.write_text(json.dumps(dict(rootDir=str(aptroot),architectures=["amd64","all"])))
        def aptly(*args):return command(["aptly","-config="+str(config),*args])
        aptly("repo","create","-distribution=bookworm","-component=main","nimbo")
        aptly("repo","add","nimbo",str(debs.resolve()))
        aptly("snapshot","create","candidate","from","repo","nimbo")
        aptly("publish","snapshot","-skip-signing","-skip-contents","-architectures=amd64,all",
              "-distribution=bookworm","-component=main","-origin=nimbo","-label=nimbo","candidate")
        site.mkdir(parents=True);shutil.copytree(aptroot/"public",site/"apt")
    with tempfile.TemporaryDirectory(prefix="nimbo-apt-public-") as tmp:
        trust.keyring(Path(tmp),ROOT/"release/nimbo-release-publica.asc",FINGERPRINT)
    shutil.copyfile(ROOT/"release/nimbo-release-publica.asc",site/"apt/release-key.asc")
    (site/".nojekyll").write_text("")
    (site/"index.html").write_text("<!doctype html><html lang=\"es\"><meta charset=\"utf-8\"><title>nimbo APT</title><h1>Repositorio APT nimbo</h1><p>"+("Candidato de main; no es v1.0.0 final." if candidate else "Paquetes del tag v1.0.0.")+"</p><p>Configuracion y huella: <a href=\"https://github.com/teamlocknet/nimbo/tree/main/apt-repo\">instrucciones</a>.</p></html>\n")
    release=site/"apt/dists/bookworm/Release"
    info=dict(format=1,commit=commit,candidate=candidate,source_date_epoch=epoch,snapshot=snapshot,
              base_image_digest=image,suite="bookworm",component="main",release_tag=None if candidate else "v1.0.0",packages=sorted(records,key=lambda x:x["name"]))
    prov=release.parent/"PROCEDENCIA.json";prov.write_text(json.dumps(info,sort_keys=True,indent=2)+"\n")
    # aptly's local publisher has no Valid-Until option in Bookworm. Add dates
    # before verification/signing; all other fields and indices remain its output.
    fields=paragraphs(release.read_text())[0]
    fields["Date"]=email.utils.format_datetime(date,usegmt=True)
    fields["Valid-Until"]=email.utils.format_datetime(date+dt.timedelta(seconds=TTL),usegmt=True)
    fields["SHA256"]+="\n "+trust.digest(prov)+" "+str(prov.stat().st_size)+" PROCEDENCIA.json"
    lines=[]
    for k,v in fields.items():
        if k in ["MD5Sum","SHA1","SHA256","SHA512"]:
            lines.append(k+":\n"+"".join(" "+row.strip()+"\n" for row in v.splitlines() if row.strip()))
        else:lines.append(k+": "+v+"\n")
    release.write_text("".join(lines))
    verify_tree(site,now=date)
    return info

def sign(site, output, digest, expected, secret, passphrase, adr):
    site=Path(site);output=Path(output)
    if bundle_digest(site)!=digest:raise ValueError("artifact no coincide con digest verificado")
    if not re.search(r"^\*\*Estado:\*\* Aceptado(?:[. ;]|$)",Path(adr).read_text(),re.M):
        raise ValueError("ADR-015 no aceptado")
    verify_tree(site)
    if output.exists():raise FileExistsError("no se sobrescribe la salida")
    with firmar.signing_key(expected,secret) as (home,call,signer,public):
        # The publication certificate must be the independently published identity.
        trust.keyring(home,site/"apt/release-key.asc",expected)
        shutil.copytree(site,output)
        release=output/"apt/dists/bookworm/Release"
        firmar.sign_document(call,signer,release,release.with_name("Release.gpg"),passphrase)
        firmar.sign_document(call,signer,release,release.with_name("InRelease"),passphrase,clearsign=True)
        verify_tree(output,signed=True,public=public,expected=expected)
    return signer

def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest="action",required=True)
    v=sub.add_parser("verificar");v.add_argument("site",type=Path);v.add_argument("--sin-firma",action="store_true");v.add_argument("--clave",type=Path);v.add_argument("--huella",default=FINGERPRINT)
    d=sub.add_parser("digest");d.add_argument("site",type=Path)
    prep=sub.add_parser("preparar")
    for name in ["debs","salida","commit","epoch","snapshot","image"]:prep.add_argument("--"+name,required=True)
    prep.add_argument("--final",action="store_true",help="exige tag local v1.0.0 en el commit indicado")
    sig=sub.add_parser("firmar");sig.add_argument("site",type=Path);sig.add_argument("output",type=Path);sig.add_argument("--digest",required=True);sig.add_argument("--adr",required=True)
    args=p.parse_args()
    try:
        if args.action=="digest":print(bundle_digest(args.site))
        elif args.action=="verificar":
            info=verify_tree(args.site,signed=not args.sin_firma,public=args.clave,expected=args.huella);print("OK: firma/indices/paquetes/procedencia",info["commit"])
        elif args.action=="preparar":
            prepare(args.debs,args.salida,args.commit,int(args.epoch),args.snapshot,args.image,candidate=not args.final);print("Preparado SIN FIRMA; no desplegar")
        else:
            secret=os.environ.pop("RELEASE_GPG_SUBKEY","").encode();phrase=os.environ.pop("RELEASE_GPG_PASSPHRASE","").encode();expected=os.environ.pop("RELEASE_GPG_FINGERPRINT","")
            if expected!=FINGERPRINT or not secret:raise ValueError("identidad o subclave no configurada")
            print("OK: firmado con subclave",sign(args.site,args.output,args.digest,expected,secret,phrase,args.adr))
        return 0
    except (ValueError,KeyError,OSError,subprocess.SubprocessError) as e:
        print("RECHAZADO:",type(e).__name__,str(e)[:180],file=sys.stderr);return 1
if __name__=="__main__":raise SystemExit(main())
