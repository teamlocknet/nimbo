#!/usr/bin/env bash
# Solo cliente Bookworm desechable de RF-DIST-01. No instala nimbo ni su clave.
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
mkdir -p /var/tmp/nimbo-apt-final-ready
exec > >(tee /var/tmp/nimbo-apt-final-ready/preparacion.log) 2>&1
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl git gnupg aptly bzip2 python3 python3-pytest qemu-guest-agent
systemctl start qemu-guest-agent
python3 - <<'PY'
from pathlib import Path
import datetime,json,os,subprocess,tempfile,termios,tty
expected="0C50B7391A9B8CFF8A36A627D3B9111FEC5748C6"
modules=["nimbo-audit","nimbo-red","nimbo-update-offline","nimbo-nav","nimbo-net"]
osinfo=dict(line.split("=",1) for line in Path("/etc/os-release").read_text().splitlines() if "=" in line)
assert osinfo.get("VERSION_CODENAME","").strip('"')=="bookworm"
states={}
for name in modules:
    p=subprocess.run(["dpkg-query","-W","-f=${db:Status-Status}",name],capture_output=True,text=True)
    states[name]=p.stdout.strip() if p.returncode==0 else "ausente"
assert not any(x=="installed" for x in states.values()),states
sources=[Path("/etc/apt/sources.list"),*Path("/etc/apt/sources.list.d").glob("*")]
assert not any("teamlocknet.github.io/nimbo" in p.read_text(errors="replace") for p in sources if p.is_file())
rings=[Path("/etc/apt/trusted.gpg"),*Path("/etc/apt/trusted.gpg.d").glob("*"),*Path("/usr/share/keyrings").glob("*")]
checked=[]
with tempfile.TemporaryDirectory(prefix="nimbo-ready-public-") as temp:
    for key in rings:
        if not key.is_file():continue
        p=subprocess.run(["gpg","--no-options","--homedir",temp,"--batch","--with-colons","--show-keys",str(key)],capture_output=True,text=True)
        assert expected not in p.stdout,"La clave nimbo ya esta instalada"
        checked.append(str(key))
versions=subprocess.run(["dpkg-query","-W","-f=${Package} ${Version}\n","apt","aptly","gnupg","python3","git","qemu-guest-agent"],capture_output=True,text=True,check=True).stdout
agent=subprocess.run(["systemctl","is-active","qemu-guest-agent"],capture_output=True,text=True)
assert agent.stdout.strip()=="active",agent.stderr
report=dict(estado="PREPARADA_SIN_VALIDACION_FINAL",fecha_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    sistema=osinfo,kernel=os.uname().release,modulos=states,fuente_nimbo_instalada=False,
    clave_nimbo_instalada=False,huella_buscada=expected,llaveros_publicos_revisados=checked,
    herramientas=versions,agente_local="qemu-guest-agent activo; socket solo del host de laboratorio",
    validacion_tag_realizada=False,pruebas_negativas_finales_realizadas=False)
path=Path("/var/tmp/nimbo-apt-final-ready/estado.json");path.write_text(json.dumps(report,indent=2)+"\n")
fd=os.open("/dev/ttyS1",os.O_WRONLY|os.O_NOCTTY);tty.setraw(fd)
attrs=termios.tcgetattr(fd);attrs[4]=termios.B115200;attrs[5]=termios.B115200;termios.tcsetattr(fd,termios.TCSANOW,attrs)
payload=b"NIMBO_APT_FINAL_READY_BEGIN\n"+path.read_bytes()+b"NIMBO_APT_FINAL_READY_END\n"
while payload:payload=payload[os.write(fd,payload):]
os.close(fd)
PY
# La plantilla ya esta aprovisionada: no repetir NoCloud al arrancar para validar.
touch /etc/cloud/cloud-init.disabled
sync
systemctl poweroff
