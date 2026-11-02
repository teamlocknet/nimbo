#!/usr/bin/env bash
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
cd "$REPO"
imagen=$(sed -n 's/^DIGEST_DEFAULT="\(.*\)"$/\1/p' \
  packages/nimbo-audit/test-in-bookworm.sh)
test -n "$imagen"
. iso/live-build/snapshot.env

if [ "$#" -ne 1 ]; then
  echo "Uso: $0 <directorio-de-artefactos>" >&2
  exit 2
fi
artefactos=$(cd "$1" && pwd)

test -f "$artefactos/nimbo-audit_0.1.0-1_all.deb"

docker run --rm \
  -v "$artefactos:/paquetes:ro" \
  -e NIMBO_SNAPSHOT="$NIMBO_SNAPSHOT" \
  -e DEBIAN_FRONTEND=noninteractive \
  -e LC_ALL=C.UTF-8 \
  "$imagen" bash -euo pipefail -c '
    printf "deb http://snapshot.debian.org/archive/debian/%s/ bookworm main\n" \
      "$NIMBO_SNAPSHOT" > /etc/apt/sources.list
    rm -f /etc/apt/sources.list.d/debian.sources
    printf "Acquire::Check-Valid-Until \"false\";\nAcquire::Retries \"5\";\n" \
      > /etc/apt/apt.conf.d/99nimbo-snapshot
    apt-get update -qq
    apt-get install -y -qq --no-install-recommends lintian \
      > /tmp/apt-install.log 2>&1 \
      || { cat /tmp/apt-install.log; exit 1; }
    lintian --version
    lintian --allow-root /paquetes/nimbo-audit_0.1.0-1_all.deb
  ' 2>&1 | tee "$artefactos/lintian.log"
