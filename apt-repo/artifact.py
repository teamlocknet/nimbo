#!/usr/bin/env python3
"""Artifact local: empaqueta bytes verificados y exige su digest al recibirlos."""
import argparse
import hashlib
import io
from pathlib import Path
import tarfile
import tempfile
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"release"))
import promover
import aptrepo

LIMIT=64*1024*1024

def pack(site, output):
    site,output=Path(site),Path(output)
    files=aptrepo.all_files(site)
    if output.exists():raise FileExistsError("artifact existente")
    with output.open("xb") as stream,tarfile.open(fileobj=stream,mode="w",format=tarfile.USTAR_FORMAT) as tar:
        for name in sorted(files):
            raw=aptrepo.safe_file(site,name).read_bytes()
            member=tarfile.TarInfo(name);member.size=len(raw);member.mode=0o644
            member.mtime=0;member.uid=member.gid=0;member.uname=member.gname=""
            tar.addfile(member,io.BytesIO(raw))
    return aptrepo.trust.digest(output)

def receive(archive, digest, output):
    archive,output=Path(archive),Path(output)
    if aptrepo.trust.digest(archive)!=digest:raise ValueError("digest del artifact incorrecto")
    if archive.stat().st_size>LIMIT:raise ValueError("artifact demasiado grande")
    if output.exists():raise FileExistsError("salida existente")
    with tarfile.open(archive,"r:") as tar:
        members=tar.getmembers()
        if len(members)>512:raise ValueError("demasiados miembros")
        names=set();total=0
        for member in members:
            p=Path(member.name)
            if (not member.isfile() or member.name in names or p.is_absolute() or
                    any(x in ("","..",".") for x in member.name.split("/")) or "\\" in member.name):
                raise ValueError("miembro tar no permitido")
            names.add(member.name);total+=member.size
            if total>LIMIT:raise ValueError("artifact expandido demasiado grande")
        output.mkdir(parents=True)
        for member in members:
            target=output/member.name;target.parent.mkdir(parents=True,exist_ok=True)
            with tar.extractfile(member) as src,target.open("xb") as dst:
                while block:=src.read(1024*1024):dst.write(block)
    return aptrepo.bundle_digest(output)

def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest="cmd",required=True)
    x=s.add_parser("pack");x.add_argument("site",type=Path);x.add_argument("output",type=Path)
    x=s.add_parser("receive");x.add_argument("archive",type=Path);x.add_argument("output",type=Path);x.add_argument("--digest",required=True)
    x=s.add_parser("github-zip");x.add_argument("archive",type=Path);x.add_argument("output",type=Path);x.add_argument("--zip-digest",required=True);x.add_argument("--tar-digest",required=True)
    a=p.parse_args()
    if a.cmd=="pack":print(pack(a.site,a.output))
    elif a.cmd=="receive":print(receive(a.archive,a.digest,a.output))
    else:
        if aptrepo.trust.digest(a.archive)!=a.zip_digest:raise ValueError("digest ZIP no coincide con upload-artifact")
        with tempfile.TemporaryDirectory(prefix="nimbo-apt-input-") as tmp:
            promover.extract_archive(a.archive,Path(tmp)/"zip",{"site.tar"},LIMIT)
            print(receive(Path(tmp)/"zip/site.tar",a.tar_digest,a.output))
if __name__=="__main__":main()
