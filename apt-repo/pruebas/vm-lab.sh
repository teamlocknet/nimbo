#!/usr/bin/env bash
# Solo VM Bookworm desechable. No usar en el host ni en una ISO de producto.
set -euo pipefail
[ "$(id -u)" -eq 0 ]
[ -f /run/nimbo-apt-lab-autorizado ] || { echo "Solo en VM preparada por el laboratorio"; exit 1; }
WORK=/var/tmp/nimbo-apt-lab
mkdir -p "$WORK/evidencia"
exec > >(tee "$WORK/evidencia/ejecucion.log") 2>&1
finish() {
  code=$?
  echo "$code" > "$WORK/evidencia/exit-code"
  python3 - "$WORK" <<'PY'
import base64,io,tarfile,sys
from pathlib import Path
root=Path(sys.argv[1])
with io.BytesIO() as buf:
    with tarfile.open(fileobj=buf,mode="w:gz") as tar:
        tar.add(root/"evidencia",arcname="evidencia")
        for name in ["build-A","build-B","site"]:
            if (root/name).exists():tar.add(root/name,arcname=name)
    with open("/dev/ttyS1","wb",buffering=0) as serial:
        serial.write(b"NIMBO_APT_EVIDENCIA_BEGIN\n")
        serial.write(base64.b64encode(buf.getvalue())+b"\nNIMBO_APT_EVIDENCIA_END\n")
PY
  systemctl poweroff
}
trap finish EXIT
date -u
cat /etc/os-release
uname -r
if dpkg-query -W nimbo-audit nimbo-red nimbo-net nimbo-nav nimbo-update-offline 2>/dev/null; then
  echo "ERROR: la VM no es limpia de modulos"; exit 1
fi
echo "BASELINE: ninguno de los cinco modulos instalado"
apt-get update
apt-get install -y --no-install-recommends docker.io aptly gnupg git python3-pytest bzip2 ca-certificates
systemctl start docker
mkdir -p "$WORK/repo"
cd "$WORK/repo"
git init
git fetch /media/nimbo/source.bundle refs/remotes/origin/main
git checkout --detach FETCH_HEAD
cp -a /media/nimbo/apt-repo .
cp /media/nimbo/release/firmar.py release/firmar.py
cp /media/nimbo/release/release.py release/release.py
bash apt-repo/test-local.sh
COMMIT="$(git rev-parse HEAD)"
CONTAINER_ENGINE=docker ./apt-repo/build-packages.sh "$WORK/build-A" "$COMMIT"
CONTAINER_ENGINE=docker ./apt-repo/build-packages.sh "$WORK/build-B" "$COMMIT"
cmp "$WORK/build-A/BUILD.json" "$WORK/build-B/BUILD.json"
echo "MATCH: los cinco deb identicos en dos builds del mismo commit/epoch"
python3 - "$WORK" <<'PY'
import sys,json
from pathlib import Path
root=Path(sys.argv[1]);sys.path.insert(0,str(root/"repo/apt-repo"));import aptrepo
b=json.loads((root/"build-A/BUILD.json").read_text())
aptrepo.prepare(root/"build-A",root/"unsigned",b["commit"],b["source_date_epoch"],b["snapshot"],b["base_image_digest"])
PY
python3 apt-repo/pruebas/firmar-efimero.py "$WORK/unsigned" "$WORK/site" "$WORK/evidencia"
python3 apt-repo/pruebas/cliente-vm.py "$WORK/site" "$WORK/evidencia"
dpkg-query -W -f='${Package} ${Version}\n' nimbo-audit nimbo-red nimbo-update-offline nimbo-nav nimbo-net > "$WORK/evidencia/instalados.txt"
for cmd in nimbo-audit nimbo-red nimbo-update-offline nimbo-tor nimbo-net; do "$cmd" --help >/dev/null; done
echo "OK: actualizacion, descarga, firma, instalacion exacta y ayudas"
