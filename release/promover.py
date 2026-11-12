#!/usr/bin/env python3
"""Compuertas de procedencia y creacion de borrador; no publica releases."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import zipfile

import release as verifier

REPO = "teamlocknet/nimbo"
EVIDENCE = "repro/evidencia/2026-11-10-qemu-instalado-03ff84c.md"
EXPECTED_SHA = "03ff84cd1804908cbd1fd7cdb90c0e8c1734a5fa"
EXPECTED_HASH = "28760694ba8e20d13b98d04435d97937ae4e33ece521d62324c0ed33c484ae90"
EXPECTED_TAG = "v1.0.0-rc1"


class GitHub:
    def api(self, endpoint, payload=None):
        args = ["gh", "api", "repos/"+REPO+"/"+endpoint]
        data = None
        if payload is not None:
            args += ["--method", "POST", "--input", "-"]
            data = json.dumps(payload).encode()
        p = subprocess.run(args, input=data, capture_output=True, timeout=120)
        if p.returncode:
            raise ValueError("consulta/mutacion de GitHub rechazada")
        return json.loads(p.stdout)

    def pages(self, endpoint, key=None):
        out = []
        for page in range(1, 1001):
            join = "&" if "?" in endpoint else "?"
            data = self.api(endpoint+join+"per_page=100&page="+str(page))
            items = data[key] if key else data
            out.extend(items)
            if len(items) < 100:
                return out
        raise ValueError("paginacion excedida")

    def download(self, endpoint, path):
        with path.open("xb") as stream:
            p = subprocess.run(["gh", "api", "repos/"+REPO+"/"+endpoint],
                               stdout=stream, stderr=subprocess.PIPE, timeout=900)
        if p.returncode:
            raise ValueError("descarga de GitHub rechazada")


def no_collision(api, tag):
    refs = api.api("git/matching-refs/tags/"+tag)
    if any(x["ref"] == "refs/tags/"+tag for x in refs):
        raise ValueError("el tag ya existe")
    if any(x["tag_name"] == tag for x in api.pages("releases")):
        raise ValueError("el release ya existe")


def validate_run(run, workflow, commit):
    if (run.get("path") != ".github/workflows/"+workflow or
            run.get("event") != "push" or run.get("head_branch") != "main" or
            run.get("head_sha") != commit or run.get("status") != "completed" or
            run.get("conclusion") != "success" or
            run.get("repository", {}).get("full_name") != REPO or
            run.get("head_repository", {}).get("full_name") != REPO):
        raise ValueError("run no autorizado o sin exito")


def extract_archive(archive, target, allowed, max_total):
    if target.exists():
        raise FileExistsError("destino existente")
    with zipfile.ZipFile(archive) as z:
        members = z.infolist()
        if {x.filename for x in members} != set(allowed) or len(members) != len(allowed):
            raise ValueError("contenido inesperado del artifact")
        if sum(x.file_size for x in members) > max_total:
            raise ValueError("artifact demasiado grande")
        for item in members:
            mode = item.external_attr >> 16
            if item.is_dir() or stat.S_ISLNK(mode) or (stat.S_IFMT(mode) not in [0, stat.S_IFREG]):
                raise ValueError("artifact contiene enlaces o archivos especiales")
        target.mkdir()
        for item in members:
            # allowed es una lista fija de basenames, nunca entrada del artifact.
            with z.open(item) as src, (target/item.filename).open("xb") as dst:
                while block := src.read(1024*1024):
                    dst.write(block)


def artifact(api, run_id, name, target, allowed, max_total):
    matches = [a for a in api.pages("actions/runs/"+str(run_id)+"/artifacts", "artifacts")
               if a["name"] == name]
    if len(matches) != 1:
        raise ValueError("artifact ausente o ambiguo")
    a = matches[0]
    if a.get("expired") or a.get("workflow_run", {}).get("id") != run_id:
        raise ValueError("artifact caducado o de otro run")
    value = a.get("digest", "")
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
        raise ValueError("digest de artifact ausente")
    archive = target.with_suffix(".zip")
    api.download("actions/artifacts/"+str(a["id"])+"/zip", archive)
    if verifier.digest(archive) != value.split(":")[1]:
        raise ValueError("digest del archivo descargado incorrecto")
    extract_archive(archive, target, allowed, max_total)
    return target


def leg(path, expected):
    rows = path.read_text().splitlines()
    pairs = [x.split("=", 1) for x in rows]
    if any(len(x) != 2 for x in pairs):
        raise ValueError("pierna mal formada")
    values = verifier.unique(pairs)
    if values.get("leg") != expected or not verifier.HEX.fullmatch(values.get("sha256", "")):
        raise ValueError("pierna incorrecta")
    if not re.fullmatch(r"[0-9a-f-]{36}", values.get("boot_id", "")):
        raise ValueError("boot_id ausente")
    return values


def qemu(text, commit, digest):
    blocks = re.findall(r"(?m)^NIMBO_APROBACION_QEMU\n(.*?)^NIMBO_APROBACION_QEMU_FIN$", text, re.S)
    if len(blocks) != 1:
        raise ValueError("aprobacion QEMU ausente o ambigua")
    values = verifier.unique([line.split(": ", 1) for line in blocks[0].strip().splitlines()])
    required = {"iso_sha256": digest, "commit": commit,
                "verificar_instalado": "OK \u2014 0 fallos", "secure_boot": "exigido",
                "aprobado_por": "Juan Jos\u00e9 (@Duque-Londono)"}
    if any(values.get(k) != v for k, v in required.items()):
        raise ValueError("aprobacion QEMU no corresponde al candidato")
    return values


def contents(api, path, ref):
    obj = api.api("contents/"+path+"?ref="+ref)
    if obj.get("type") != "file" or obj.get("encoding") != "base64":
        raise ValueError("contenido GitHub inesperado")
    return base64.b64decode(obj["content"]).decode()


def validate(api, tag, commit, build, repro, output):
    # Alcance v1: evita usar la evidencia especifica de rc1 para otro producto.
    if (tag, commit) != (EXPECTED_TAG, EXPECTED_SHA):
        raise ValueError("este workflow solo promueve el candidato rc1 aprobado")
    if type(build) is not int or type(repro) is not int or min(build, repro) <= 0:
        raise ValueError("runs invalidos")
    no_collision(api, tag)
    for run_id, workflow in [(build,"build-iso.yml"),(repro,"repro-verify.yml")]:
        validate_run(api.api("actions/runs/"+str(run_id)),workflow,commit)
    main_sha = api.api("git/ref/heads/main")["object"]["sha"]
    if not re.fullmatch(r"[0-9a-f]{40}", main_sha):
        raise ValueError("main invalido")
    qemu(contents(api,EVIDENCE,main_sha),commit,EXPECTED_HASH)
    snapshot = contents(api,"iso/live-build/snapshot.env",commit)
    match = re.search(r'^NIMBO_SNAPSHOT=["\']?([0-9]{8}T[0-9]{6}Z)',snapshot,re.M)
    image = contents(api,"iso/live-build/build-in-container.sh",commit)
    base = re.search(r'debian@(sha256:[0-9a-f]{64})',image)
    if not match or not base:
        raise ValueError("anclaje de toolchain ausente")
    epoch = api.api("commits/"+commit)["commit"]["committer"]["date"]
    from datetime import datetime
    epoch = int(datetime.fromisoformat(epoch.replace("Z","+00:00")).timestamp())
    with tempfile.TemporaryDirectory(prefix="nimbo-provenance-") as tmp:
        work = Path(tmp)
        iso = artifact(api,build,"nimbo-iso-"+commit[:7],work/"iso",
                       {"live-image-amd64.hybrid.iso","live-image-amd64.hybrid.iso.sha256"},3*1024**3)
        vals=[]
        for name in ["A","B"]:
            dest=artifact(api,repro,"iso-sha-"+name,work/("leg-"+name),{"leg-"+name+".txt"},16384)
            vals.append(leg(dest/("leg-"+name+".txt"),name))
        digest=verifier.digest(iso/"live-image-amd64.hybrid.iso")
        expected_line=digest+"  live-image-amd64.hybrid.iso"
        if (iso/"live-image-amd64.hybrid.iso.sha256").read_text().strip()!=expected_line:
            raise ValueError("hash adjunto incorrecto")
        if digest != EXPECTED_HASH or any(x["sha256"]!=digest for x in vals):
            raise ValueError("no hay MATCH entre candidato y ambas piernas")
        if vals[0]["boot_id"] == vals[1]["boot_id"]:
            raise ValueError("runners independientes no demostrados")
        info=dict(tag=tag,commit=commit,build_run=build,repro_run=repro,iso_sha256=digest,
                  leg_a_sha256=digest,leg_b_sha256=digest,qemu_iso_sha256=digest,
                  qemu_evidence_url="https://github.com/"+REPO+"/blob/"+main_sha+"/"+EVIDENCE,
                  snapshot=match[1],source_date_epoch=epoch,base_image_digest=base[1])
        output=Path(output);output.mkdir()
        import shutil
        shutil.copyfile(iso/"live-image-amd64.hybrid.iso",output/"candidate.iso")
        (output/"candidate.json").write_text(json.dumps(info,indent=2)+"\n")
        verifier.metadata(output/"candidate.json")
        return info


def public_identity(public, expected_hash):
    if not verifier.HEX.fullmatch(expected_hash):
        raise ValueError("compromiso de identidad invalido")
    with tempfile.TemporaryDirectory(prefix="nimbo-public-identity-") as tmp:
        rows=verifier.gpg(Path(tmp),"--with-colons","--show-keys",str(public)).stdout.decode().splitlines()
    values=[];pending=False
    for line in rows:
        f=line.split(":")
        if f[0]=="pub":pending=True
        elif f[0]=="fpr" and pending:
            values.append(f[9]);pending=False
    if len(values)!=1 or hashlib.sha256(values[0].encode()).hexdigest()!=expected_hash:
        raise ValueError("identidad publica no coincide con la aprobada para firma")
    return verifier.fingerprint(values[0])


def draft(api, directory, expected):
    info=verifier.verify(directory,expected)
    if (info["tag"],info["commit"],info["iso_sha256"])!=(EXPECTED_TAG,EXPECTED_SHA,EXPECTED_HASH):
        raise ValueError("distribucion no autorizada")
    no_collision(api,info["tag"])
    api.api("git/refs",dict(ref="refs/tags/"+info["tag"],sha=info["commit"]))
    release=api.api("releases",dict(tag_name=info["tag"],target_commitish=info["commit"],
        name=info["tag"],draft=True,prerelease=True,
        body="Candidato de pruebas. Commit "+info["commit"]+". ISO SHA-256 "+info["iso_sha256"]+
             ". Procedencia y verificacion en los assets. Pendiente comprobacion de descarga."))
    # gh no usa --clobber: una colision de asset falla.
    files=sorted(str(x) for x in Path(directory).iterdir())
    subprocess.run(["gh","release","upload",info["tag"],*files,"--repo",REPO],check=True,timeout=900)
    with tempfile.TemporaryDirectory(prefix="nimbo-draft-check-") as tmp:
        root=Path(tmp)
        assets=api.pages("releases/"+str(release["id"])+"/assets")
        names={Path(x).name for x in files}
        if len(assets)!=5 or {x["name"] for x in assets}!=names:
            raise ValueError("publicacion incompleta")
        for asset in assets:
            # endpoint fijo; no ejecutar ni seguir URLs elegidas por el artifact.
            with (root/asset["name"]).open("xb") as stream:
                subprocess.run(["gh","api","-H","Accept: application/octet-stream",
                    "repos/"+REPO+"/releases/assets/"+str(asset["id"])],
                    stdout=stream,stderr=subprocess.PIPE,check=True,timeout=900)
        verifier.verify(root,expected)
    return release["html_url"]


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest="action",required=True)
    a=sub.add_parser("validar")
    for k in ["tag","commit","build","repro","salida"]:a.add_argument("--"+k,required=True)
    a=sub.add_parser("borrador");a.add_argument("directorio")
    identity=a.add_mutually_exclusive_group(required=True)
    identity.add_argument("--huella");identity.add_argument("--huella-sha256")
    args=p.parse_args()
    try:
        api=GitHub()
        if args.action=="validar":
            validate(api,args.tag,args.commit,int(args.build),int(args.repro),Path(args.salida))
            print("OK: procedencia, MATCH y evidencia QEMU comprobados")
        else:
            expected=args.huella or public_identity(Path(args.directorio)/"release-key.asc",args.huella_sha256)
            print("BORRADOR VERIFICADO, publicar manualmente: "+draft(api,args.directorio,expected))
        return 0
    except (ValueError,KeyError,OSError,subprocess.SubprocessError,zipfile.BadZipFile):
        print("ERROR: promocion rechazada; no publicar el borrador")
        return 1

if __name__=="__main__":raise SystemExit(main())
