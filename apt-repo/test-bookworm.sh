#!/usr/bin/env bash
# Test de las funciones compartidas y APT en la imagen/snapshot de la ISO.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LB="$REPO/iso/live-build"
ENGINE="${CONTAINER_ENGINE:-docker}"
IMAGE="$(sed -n 's/^IMAGE="\${NIMBO_BASE_IMAGE:-\(.*\)}"$/\1/p' "$LB/build-in-container.sh")"
[ -n "$IMAGE" ];. "$LB/snapshot.env"
exec "$ENGINE" run --rm --network=host -v "$REPO:/src:ro" \
  -e NIMBO_SNAPSHOT="$NIMBO_SNAPSHOT" -e DEBIAN_FRONTEND=noninteractive \
  -e TZ=UTC -e LC_ALL=C.UTF-8 "$IMAGE" bash -euo pipefail -c '
  printf "deb http://snapshot.debian.org/archive/debian/%s/ bookworm main\n" "$NIMBO_SNAPSHOT" > /etc/apt/sources.list
  rm -f /etc/apt/sources.list.d/debian.sources
  printf "Acquire::Check-Valid-Until \"false\";\nAcquire::Retries \"5\";\n" > /etc/apt/apt.conf.d/99nimbo-snapshot
  apt-get update -qq
  apt-get install -y -qq --no-install-recommends python3 python3-pytest gnupg aptly bzip2 ca-certificates >/dev/null
  mkdir -p /w/iso/live-build/config/includes.chroot/usr/share/nimbo /w/docs/sustentacion
  cp -a /src/apt-repo /src/release /w/
  cp /src/README.md /w/README.md
  cp /src/docs/sustentacion/README.md /w/docs/sustentacion/README.md
  cp /src/iso/live-build/config/includes.chroot/usr/share/nimbo/modulos.list /w/iso/live-build/config/includes.chroot/usr/share/nimbo/modulos.list
  cd /w
  PYTHONDONTWRITEBYTECODE=1 bash apt-repo/test-local.sh
'
