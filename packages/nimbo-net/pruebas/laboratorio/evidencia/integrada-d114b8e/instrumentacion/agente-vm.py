#!/usr/bin/env python3
"""Agente SOLO de laboratorio en VM desechable; claves privadas nunca salen."""
import base64
import json
import os
import re
import signal
import subprocess
import sys
import termios
import tty
from pathlib import Path

BASE = Path("/run/nimbo-lab")
CAPTURAS = {}


def run(argv, check=True, timeout=60):
    p = subprocess.run(argv, check=False, capture_output=True, text=True, timeout=timeout)
    if check and p.returncode:
        raise RuntimeError("fallo " + argv[0] + ": " + (p.stderr[-1200:] or p.stdout[-1200:]))
    return p


def identidad():
    iface = Path("/run/nimbo-red/interfaz").read_text().strip()
    data = json.loads(run(["ip", "-j", "address", "show", "dev", iface]).stdout)
    ips = [a["local"] for d in data for a in d.get("addr_info", []) if a.get("family") == "inet"]
    return {"interfaz": iface, "ip": ips[0], "public_key": Path("/etc/nimbo-net/public.key").read_text().strip()}


def action(req):
    cmd = req["cmd"]
    if cmd == "ready":
        return {"kernel": os.uname().release, "pid1": Path("/proc/1/comm").read_text().strip()}
    if cmd == "prepare":
        Path("/usr/sbin/policy-rc.d").write_text("#!/bin/sh\nexit 101\n")
        Path("/usr/sbin/policy-rc.d").chmod(0o755)
        install = run(["dpkg", "-i", *map(str, sorted((BASE / "debs").glob("*.deb")))],timeout=180)
        # Se copia la unidad real para consultar Tor inactivo; no se inicia Tor.
        unit = BASE / "nimbo-modo-tor.service"
        if unit.exists():
            Path("/etc/systemd/system/nimbo-modo-tor.service").write_bytes(unit.read_bytes())
            run(["systemctl", "daemon-reload"])
        hardening = run(["sysctl", "-p", str(BASE / "hardening.conf")],check=False)
        cfg = Path("/etc/nimbo-net"); cfg.mkdir(mode=0o700,exist_ok=True);cfg.chmod(0o700)
        key = run(["wg", "genkey"]).stdout
        fd = os.open(cfg / "private.key", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd,"w") as f:f.write(key)
        pub = subprocess.run(["wg", "pubkey"],input=key,text=True,capture_output=True,check=True).stdout
        (cfg / "public.key").write_text(pub);key=None
        return {"install": install.stdout[-1200:], "hardening_rc": hardening.returncode,
                "hardening_stderr": hardening.stderr, "status":run(["nimbo-net","status"]).stdout,
                "wg_quick_enabled":run(["systemctl","is-enabled","wg-quick@wg-nimbo.service"],check=False).stdout.strip()}
    if cmd == "tor_prepare":
        import shutil
        shutil.copytree(BASE / "nimbo_nav", Path("/usr/lib/python3/dist-packages/nimbo_nav"), dirs_exist_ok=True)
        for name,module in [("nimbo-tor","tor_modo"),("nimbo-leakcheck","leakcheck")]:
            dest=Path("/usr/bin")/name
            dest.write_text("#!/usr/bin/python3\nfrom nimbo_nav."+module+" import main\nraise SystemExit(main())\n")
            dest.chmod(0o755)
        Path("/usr/share/nimbo-nav").mkdir(exist_ok=True)
        shutil.copy(BASE/"nimbo-tor.nft", "/usr/share/nimbo-nav/nimbo-tor.nft")
        for name in ["nimbo-modo-tor.service","nimbo-leakcheck.service"]:
            shutil.copy(BASE/name,Path("/etc/systemd/system")/name)
        run(["systemctl","disable","--now","tor.service","tor@default.service"],check=False)
        run(["systemctl","daemon-reload"])
        return {"preparado":True}
    if cmd in ["tor_on","tor_off"]:
        p=run(["nimbo-tor","on" if cmd=="tor_on" else "off"],check=False,timeout=120)
        return {"rc":p.returncode,"output":p.stdout,"error":p.stderr[-500:]}
    if cmd == "race":
        import concurrent.futures
        def call(argv):
            p=run(argv,check=False,timeout=420)
            return {"rc":p.returncode,"output":p.stdout,"error":p.stderr[-500:]}
        with concurrent.futures.ThreadPoolExecutor(2) as ex:
            a=ex.submit(call,["nimbo-net","join"])
            b=ex.submit(call,["nimbo-tor","on"])
            return {"join":a.result(),"tor":b.result()}
    if cmd == "coexistence":
        return {"tor":run(["systemctl","is-active","nimbo-modo-tor.service"],check=False).stdout.strip(),
                "links":json.loads(run(["ip","-j","link","show"]).stdout),
                "tables":json.loads(run(["nft","-j","list","tables"]).stdout)}
    if cmd == "alias_probe":
        name="wg-lab-probe"
        before=json.loads(run(["ip","-j","link","show"]).stdout)
        if any(d["ifname"]==name for d in before):raise RuntimeError("nombre de prueba ocupado")
        run(["ip","link","add","dev",name,"alias","nimbo-lab:probe","type","wireguard"])
        try:
            initial=json.loads(run(["ip","-j","link","show","dev",name]).stdout)[0]
            run(["ip","link","set","dev",name,"alias","nimbo-lab:probe"])
            final=json.loads(run(["ip","-j","link","show","dev",name]).stdout)[0]
            return {"alias_en_add":initial.get("ifalias"),"alias_en_set":final.get("ifalias"),"kernel":os.uname().release}
        finally:run(["ip","link","delete","dev",name])
    if cmd == "network_on":
        result=run(["nimbo-red","on"],timeout=90)
        return {"output":result.stdout,**identidad()}
    if cmd == "profile":
        data=req["perfil"]
        fd=os.open("/etc/nimbo-net/perfil.json",os.O_WRONLY | os.O_CREAT | os.O_TRUNC,0o600)
        with os.fdopen(fd,"w") as f:json.dump(data,f)
        return {"perfil_preparado":True}
    if cmd in ["join","leave","status"]:
        p=run(["nimbo-net",cmd],check=False,timeout=420)
        return {"rc":p.returncode,"output":p.stdout,"error":p.stderr[-500:]}
    if cmd == "report":
        iface=identidad()["interfaz"]
        filt={x:run(["sysctl","-n","net.ipv4.conf."+x+".rp_filter"]).stdout.strip()
              for x in ["all","default",iface,"wg-nimbo"]}
        link=json.loads(run(["ip","-details","-j","link","show","dev","wg-nimbo"]).stdout)
        raw=run(["wg","show","wg-nimbo","latest-handshakes"]).stdout
        return {"rp_filter":filt,"link":link,"handshakes":[int(x.split()[1]) for x in raw.splitlines()],
                "routes":json.loads(run(["ip","-j","route","show"]).stdout)}
    if cmd == "ping":
        target=json.loads(Path("/etc/nimbo-net/perfil.json").read_text())["peer_address"]
        p=run(["ping","-n","-c","3","-W","3","-I","wg-nimbo","-p","6e696d626f2d6c61622d31323334353637",target],check=False)
        return {"rc":p.returncode,"output":p.stdout}
    if cmd == "capture_start":
        iface=identidad()["interfaz"] if req["interface"]=="fisica" else "wg-nimbo"
        if iface in CAPTURAS:raise RuntimeError("captura ya activa")
        path=Path("/tmp/captura-"+iface+".pcap")
        CAPTURAS[iface]=(subprocess.Popen(["tcpdump","-U","-n","-i",iface,"-w",str(path)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL),path)
        return {"capturando":iface}
    if cmd == "capture_stop":
        result={}
        for iface,(proc,path) in list(CAPTURAS.items()):
            proc.send_signal(signal.SIGINT);proc.wait(timeout=15)
            result[iface]=base64.b64encode(path.read_bytes()).decode();del CAPTURAS[iface]
        return result
    if cmd == "network_off":
        p=run(["nimbo-red","off"],check=False)
        return {"rc":p.returncode,"output":p.stdout,"status":run(["nimbo-net","status"]).stdout}
    if cmd == "shutdown":
        subprocess.Popen(["systemctl","poweroff"]);return {"apagando":True}
    raise RuntimeError("accion no permitida")


def main():
    fd=os.open("/dev/ttyS1",os.O_RDWR | os.O_NOCTTY)
    tty.setraw(fd)
    attrs=termios.tcgetattr(fd);attrs[4]=termios.B115200;attrs[5]=termios.B115200;termios.tcsetattr(fd,termios.TCSANOW,attrs)
    pending=b""
    while True:
        pending+=os.read(fd,65536)
        if b"\n" not in pending:continue
        line,pending=pending.split(b"\n",1)
        try:
            req=json.loads(line);result={"ok":True,"result":action(req)}
        except Exception as e:
            result={"ok":False,"error":str(e)[:1800]}
        message=(json.dumps(result)+"\n").encode()
        while message:
            message=message[os.write(fd,message):]


if __name__=="__main__":main()
