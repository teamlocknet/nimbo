#!/usr/bin/env python3
"""Agente temporal para la ISO integrada: no instala modulos ni aplica sysctl."""
import hashlib
import base64
import socket
import struct
import threading
import time
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

spec=importlib.util.spec_from_file_location("lab_base",Path(__file__).with_name("agente-vm.py"))
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
original=base.action
CAPTURES={}
ALLOWED={"ready","alias_probe","network_on","network_off","profile","join","leave","status",
         "report","ping","tor_on","tor_off","race","coexistence","capture_start","capture_stop","shutdown"}


def leaks():
    p=base.run(["nft","-j","list","counter","inet","nimbo_tor","fugas"],check=False)
    counter=json.loads(p.stdout) if p.returncode==0 else None
    state=Path("/run/nimbo-nav/leakcheck.json")
    values=json.loads(state.read_text()) if state.exists() else None
    if values is not None:
        values={k:values.get(k) for k in ["modo_tor","vigilante","limpio","paquetes_descartados","actualizado"]}
    return {"counter":counter,"leakcheck":values}


def action(req):
    cmd=req["cmd"]
    if cmd=="capture_start":
        iface=base.identidad()["interfaz"] if req["interface"]=="fisica" else "wg-nimbo"
        if iface in CAPTURES:raise ValueError("captura ya activa")
        sock=socket.socket(socket.AF_PACKET,socket.SOCK_RAW,socket.htons(3))
        sock.bind((iface,0));sock.settimeout(0.5)
        stop=threading.Event();path=Path("/tmp/captura-"+iface+".pcap")
        def collect():
            with path.open("wb") as output:
                output.write(struct.pack("<IHHIIII",0xa1b2c3d4,2,4,0,0,65535,1 if iface!="wg-nimbo" else 101))
                while not stop.is_set():
                    try:data=sock.recv(65535)
                    except socket.timeout:continue
                    now=time.time();seconds=int(now);micro=int((now-seconds)*1000000)
                    output.write(struct.pack("<IIII",seconds,micro,len(data),len(data)));output.write(data)
                output.flush()
        thread=threading.Thread(target=collect,daemon=True);thread.start()
        CAPTURES[iface]=(sock,stop,thread,path)
        return {"capturando":iface,"instrumento":"AF_PACKET pasivo de Python; sin instalar tcpdump"}
    if cmd=="capture_stop":
        result={}
        for iface,(sock,stop,thread,path) in list(CAPTURES.items()):
            stop.set();thread.join(timeout=3)
            if thread.is_alive():raise ValueError("captura no detenida")
            sock.close();result[iface]=base64.b64encode(path.read_bytes()).decode();del CAPTURES[iface]
        return result
    if cmd=="leak_log":
        return {"kernel_log":base.run(["journalctl","-k","-b","-g","nimbo-fuga","--no-pager","-n","30"],check=False).stdout}
    if cmd=="baseline":
        versions=base.run(["dpkg-query","-W","-f=${Package} ${Version}\n","nimbo-audit","nimbo-red",
            "nimbo-net","nimbo-nav","nimbo-update-offline","wireguard-tools","tor","firefox-esr"]).stdout
        units={name:base.run(["systemctl","show",name,"--property=LoadState","--property=ActiveState",
            "--property=UnitFileState"],check=False).stdout for name in ["tor.service","tor@default.service",
            "nimbo-modo-tor.service","nimbo-leakcheck.service","wg-quick@wg-nimbo.service"]}
        files={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in Path("/etc/sysctl.d").glob("*nimbo*") if f.is_file()}
        hardening=base.run(["/usr/lib/nimbo/verify-hardening"],check=False)
        return {"versions":versions,"units":units,"sysctl_files":files,
                "hardening_rc":hardening.returncode,"hardening_output":hardening.stdout,
                "red_estado":base.run(["nimbo-red","estado"],check=False).stdout,
                "wg_present":Path("/sys/class/net/wg-nimbo").exists(),
                "wg_config_exists":Path("/etc/wireguard/wg-nimbo.conf").exists(),
                "kernel":os.uname().release,
                "secure_boot":any(f.read_bytes()[4:5]==b"\x01" for f in Path("/sys/firmware/efi/efivars").glob("SecureBoot-*")),
                "luks2_mapping_active":any(f.read_text().startswith("CRYPT-LUKS2-") for f in Path("/sys/class/block").glob("dm-*/dm/uuid")),
                "root_fstype":base.run(["findmnt","-n","-o","FSTYPE","/"]).stdout.strip(),
                "live_medium_present":Path("/run/live/medium/live/filesystem.squashfs").exists(),
                "physical_global_ipv4":[a["local"] for d in json.loads(base.run(["ip","-j","address","show"]).stdout)
                    if d["ifname"].startswith(("en","eth")) for a in d.get("addr_info",[])
                    if a.get("family")=="inet" and a.get("scope")=="global"]}
    if cmd=="prepare_integrated":
        # Solo perfiles propios en RAM. No cambia paquetes, unidades ni hardening.
        cfg=Path("/etc/nimbo-net");cfg.mkdir(mode=0o700,exist_ok=True);cfg.chmod(0o700)
        key=base.run(["wg","genkey"]).stdout
        fd=os.open(cfg/"private.key",os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        with os.fdopen(fd,"w") as f:f.write(key)
        pub=subprocess.run(["wg","pubkey"],input=key,text=True,capture_output=True,check=True).stdout
        (cfg/"public.key").write_text(pub)
        return {"prepared":True,"private_key_exported":False}
    if cmd=="network_snapshot":
        resolver=Path("/etc/resolv.conf")
        return {"routes":json.loads(base.run(["ip","-j","route","show","table","all"]).stdout),
                "resolv_sha256":hashlib.sha256(resolver.read_bytes()).hexdigest(),
                "links":json.loads(base.run(["ip","-j","link","show"]).stdout),
                "dhclient":base.run(["pgrep","-af","dhclient"],check=False).stdout,
                "leaks":leaks(),"red_estado":base.run(["nimbo-red","estado"],check=False).stdout}
    if cmd=="leaks":return leaks()
    if cmd not in ALLOWED:raise ValueError("accion no permitida en la ISO integrada")
    return original(req)

base.action=action
if __name__=="__main__":base.main()
