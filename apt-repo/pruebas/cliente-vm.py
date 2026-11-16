#!/usr/bin/env python3
"""Cliente APT real en VM desechable; fuente solo de prueba, firma efimera."""
from pathlib import Path
import functools,http.server,json,subprocess,sys,threading
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import aptrepo as apt
site,evidence=map(Path,sys.argv[1:])
primary=json.loads((evidence/"firma-laboratorio.json").read_text())["fingerprint"]
apt.verify_tree(site,signed=True,expected=primary)
class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(("127.0.0.1",0),functools.partial(Handler,directory=str(site)))
threading.Thread(target=server.serve_forever,daemon=True).start()
port=server.server_address[1]
key=Path("/usr/share/keyrings/nimbo-laboratorio.asc");key.write_bytes((site/"apt/release-key.asc").read_bytes())
source=Path("/etc/apt/sources.list.d/nimbo-laboratorio.list")
source.write_text("deb [arch=amd64 signed-by="+str(key)+"] http://127.0.0.1:"+str(port)+"/apt bookworm main\n")
info=apt.verify_tree(site,signed=True,expected=primary)
results=[]
def call(args,ok=True):
    p=subprocess.run(args,capture_output=True,text=True)
    results.append(dict(command=args,returncode=p.returncode,output=p.stdout,stderr=p.stderr))
    if ok and p.returncode:raise RuntimeError("APT fallo: "+str(args))
    return p
try:
    call(["apt-get","update","-o","APT::Update::Error-Mode=any"])
    specs=[p["name"]+"="+p["version"] for p in info["packages"]]
    download=evidence/"descargas";download.mkdir()
    p=subprocess.run(["apt-get","download",*specs],cwd=download,capture_output=True,text=True)
    results.append(dict(command=["apt-get","download",*specs],returncode=p.returncode,output=p.stdout,stderr=p.stderr))
    if p.returncode:raise RuntimeError("descarga fallo")
    for pkg in info["packages"]:
        matches=list(download.glob(pkg["name"]+"_*.deb"))
        if len(matches)!=1 or apt.trust.digest(matches[0])!=pkg["sha256"]:raise ValueError("descarga distinta")
    # Debian dependencies come from Debian sources; the five own modules only from this repo.
    call(["apt-get","install","-y","--no-install-recommends",*specs])
    call(["apt-cache","policy",*[p["name"] for p in info["packages"]]])
    # Wrong public key must fail a fresh APT update with only this source.
    empty=evidence/"listas-negativa";(empty/"partial").mkdir(parents=True)
    wrong=evidence/"clave-incorrecta.asc";wrong.write_bytes((apt.ROOT/"release/nimbo-release-publica.asc").read_bytes())
    negative=evidence/"fuente-negativa.list"
    negative.write_text(source.read_text().replace(str(key),str(wrong)))
    r=call(["apt-get","update","-o","Dir::Etc::sourcelist="+str(negative),
            "-o","Dir::Etc::sourceparts=-","-o","Dir::State::lists="+str(empty),
            "-o","APT::Update::Error-Mode=any"],ok=False)
    if r.returncode==0:raise ValueError("APT acepto otra identidad")
    (evidence/"cliente.json").write_text(json.dumps(dict(ok=True,results=results),indent=2))
finally:
    source.unlink(missing_ok=True);key.unlink(missing_ok=True);server.shutdown()
