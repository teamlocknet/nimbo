#!/usr/bin/env bash
# Misma receta de modulos que build-in-container.sh; no construye ni modifica ISO.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
OUT="${1:?Uso: build-packages.sh directorio-nuevo [commit]}"
COMMIT="$(git -C "$REPO" rev-parse "${2:-HEAD}^{commit}")"
[ ! -e "$OUT" ] || { echo "ERROR: la salida ya existe" >&2; exit 1; }
ENGINE="${CONTAINER_ENGINE:-docker}"
command -v "$ENGINE" >/dev/null
WORK="$(mktemp -d)"
trap 'rm -rf -- "$WORK"' EXIT
git -C "$REPO" archive "$COMMIT" | tar -x -C "$WORK"
LB="$WORK/iso/live-build"
IMAGE="$(sed -n 's/^IMAGE="\${NIMBO_BASE_IMAGE:-\(.*\)}"$/\1/p' "$LB/build-in-container.sh")"
[ -n "$IMAGE" ]
. "$LB/snapshot.env"
EPOCH="$(git -C "$REPO" show -s --format=%ct "$COMMIT")"
mkdir -p "$OUT";OUT="$(cd "$OUT" && pwd)"
# Build input is only git archive of the selected commit, never untracked files.
"$ENGINE" run --rm --network=host \
  -v "$WORK:/src:ro" -v "$OUT:/out" \
  -e SOURCE_DATE_EPOCH="$EPOCH" -e NIMBO_SNAPSHOT="$NIMBO_SNAPSHOT" \
  -e NIMBO_ESPEJO="${NIMBO_ESPEJO:-}" -e TZ=UTC -e LC_ALL=C.UTF-8 \
  -e DEBIAN_FRONTEND=noninteractive "$IMAGE" bash -euo pipefail -c '
    printf "deb %s/archive/debian/%s/ bookworm main\n" "${NIMBO_ESPEJO:-http://snapshot.debian.org}" "$NIMBO_SNAPSHOT" > /etc/apt/sources.list
    rm -f /etc/apt/sources.list.d/debian.sources
    printf "Acquire::Check-Valid-Until \"false\";\nAcquire::Retries \"5\";\n" > /etc/apt/apt.conf.d/99nimbo-snapshot
    apt-get update
    apt-get install -y --no-install-recommends live-build ca-certificates \
      build-essential fakeroot debhelper dh-python pybuild-plugin-pyproject \
      python3-all python3-setuptools python3-pytest python3-typer
    mkdir -p /tmp/nimbo-package
    MODULES="$(grep -v "^[[:space:]]*#" /src/iso/live-build/config/includes.chroot/usr/share/nimbo/modulos.list | grep -v "^[[:space:]]*$")"
    for m in $MODULES; do
      cp -a "/src/packages/$m" "/tmp/nimbo-package/$m"
      apt-get build-dep -y "/tmp/nimbo-package/$m"
      (cd "/tmp/nimbo-package/$m" && dpkg-buildpackage -us -uc -b)
    done
    for m in $MODULES; do
      set -- /tmp/nimbo-package/"$m"_*.deb
      [ "$#" -eq 1 ] && [ -f "$1" ]
      [ "$(dpkg-deb -f "$1" Package)" = "$m" ]
      [ "$(dpkg-deb -f "$1" Architecture)" = all ]
      cp "$1" /out/
      dpkg-deb -f "$1" Package Version Architecture
      sha256sum "$1"
    done
    [ "$(find /tmp/nimbo-package -maxdepth 1 -name "*.deb" | wc -l)" -eq "$(printf "%s\n" $MODULES | wc -l)" ]
  '
python3 - "$OUT" "$COMMIT" "$EPOCH" "$NIMBO_SNAPSHOT" "$IMAGE" <<'PY'
import hashlib,json,sys
from pathlib import Path
out=Path(sys.argv[1])
data=dict(commit=sys.argv[2],source_date_epoch=int(sys.argv[3]),snapshot=sys.argv[4],
          base_image_digest=sys.argv[5].split("@")[1],
          packages={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob("*.deb"))})
(out/"BUILD.json").write_text(json.dumps(data,sort_keys=True,indent=2)+"\n")
print("OK: cinco modulos, procedencia en BUILD.json")
PY
