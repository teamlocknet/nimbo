#!/usr/bin/env python3
"""Arranca dos VMs live desechables con la ISO integrada de solo lectura."""
import argparse
import hashlib
import gzip
import json
from pathlib import Path
import shutil
import socket
import subprocess


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iso",type=Path,required=True)
    parser.add_argument("--lab",type=Path,required=True)
    parser.add_argument("--procedencia",type=Path,required=True)
    args=parser.parse_args()
    iso=args.iso.resolve(strict=True);lab=args.lab.absolute();src=Path(__file__).parent
    lab.mkdir(mode=0o700)
    manifest=json.loads(args.procedencia.read_text())
    sha=hashlib.sha256()
    with iso.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):sha.update(block)
    if sha.hexdigest()!=manifest["iso_sha256"]:raise ValueError("ISO distinta a la procedencia")
    with (lab/"extraccion.log").open("w") as log:
        subprocess.run(["xorriso","-osirrox","on","-indev",str(iso),
            "-extract","/live/vmlinuz",str(lab/"vmlinuz"),
            "-extract","/live/initrd.img",str(lab/"initrd.original")],stdout=log,stderr=log,check=True)
    payload=lab/"payload";payload.mkdir()
    for name in ["agente-vm.py","agente-integrado.py"]:shutil.copyfile(src/name,payload/name)
    extra=lab/"initrd-extra";hooks=extra/"scripts/live-bottom";hooks.mkdir(parents=True)
    hook=(src/"evidencia/instrumentacion/99-nimbo-lab").read_text()
    hook=hook.replace('/run/nimbo-lab/agent.py','/run/nimbo-lab/agente-integrado.py')
    (hooks/"99-nimbo-lab").write_text(hook);(hooks/"99-nimbo-lab").chmod(0o755)
    (hooks/"ORDER").write_text('/scripts/live-bottom/99-nimbo-lab\n')
    with (lab/"extra.cpio").open("wb") as output:
        subprocess.run(["cpio","--create","--format=newc"],cwd=extra,
            input=b"scripts\nscripts/live-bottom\nscripts/live-bottom/99-nimbo-lab\nscripts/live-bottom/ORDER\n",
            stdout=output,stderr=subprocess.PIPE,check=True)
    with (lab/"initrd.lab").open("wb") as output:
        with (lab/"initrd.original").open("rb") as stream:shutil.copyfileobj(stream,output)
        output.write(gzip.compress((lab/"extra.cpio").read_bytes(),mtime=0))
    subprocess.run(["xorriso","-as","mkisofs","-quiet","-V","NIMBO_NET_LAB","-o",str(lab/"carga.iso"),str(payload)],check=True)
    with socket.socket() as probe:
        probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
    manifest.update(iso=str(iso),tipo="ISO CI integrada de solo lectura, initrd de laboratorio concatenado",
                    console="ttyS0",control="ttyS1",accel="tcg",ram_mib_por_vm=1536,port=port,
                    paquetes_reinstalados=False,sysctl_aplicado_por_agente=False)
    manifest["instrumentacion_sha256"]={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in payload.glob("*.py")}
    (lab/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
    started=[]
    try:
        for n in ['A','B']:
            cmd=['qemu-system-x86_64','-name','nimbo-net-integrado-'+n,'-machine','pc,accel=tcg',
                '-m','1536','-smp','2','-display','none','-monitor','none','-no-reboot','-daemonize',
                '-pidfile',str(lab/(n+'.pid')),'-kernel',str(lab/'vmlinuz'),'-initrd',str(lab/'initrd.lab'),
                '-append','boot=live components hostname=nimbo-lab-'+n.lower()+' username=nimbo console=ttyS0,115200 systemd.unit=multi-user.target live-config.timezone=Etc/UTC',
                '-drive','file='+str(iso)+',format=raw,media=cdrom,readonly=on',
                '-drive','file='+str(lab/'carga.iso')+',format=raw,media=cdrom,readonly=on',
                '-serial','file:'+str(lab/(n+'.boot.log')),
                '-chardev','socket,id=control,path='+str(lab/(n+'.serial.sock'))+',server=on,wait=off',
                '-serial','chardev:control']
            if n=='A':
                cmd+=['-netdev','user,id=dhcp,restrict=on,ipv6=off','-netdev','hubport,id=up,hubid=0,netdev=dhcp',
                      '-netdev','socket,id=wire,listen=127.0.0.1:'+str(port),
                      '-netdev','hubport,id=cable,hubid=0,netdev=wire','-netdev','hubport,id=nic,hubid=0',
                      '-device','virtio-net-pci,netdev=nic,mac=52:54:00:11:00:01']
            else:cmd+=['-netdev','socket,id=wire,connect=127.0.0.1:'+str(port),
                       '-device','virtio-net-pci,netdev=wire,mac=52:54:00:11:00:02']
            (lab/(n+'.command.json')).write_text(json.dumps(cmd))
            subprocess.run(cmd,check=True);started.append(n)
    except BaseException:
        import os,signal
        for n in started:
            pid=int((lab/(n+'.pid')).read_text())
            proc=Path('/proc')/str(pid)/'cmdline'
            if proc.exists() and str(lab).encode() in proc.read_bytes():os.kill(pid,signal.SIGTERM)
        raise
    print('VMs iniciadas; laboratorio:',lab)

if __name__=='__main__':main()
