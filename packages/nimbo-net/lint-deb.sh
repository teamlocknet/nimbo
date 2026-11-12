#!/usr/bin/env bash
# Lintian en bookworm, sin instalar paquetes en el anfitrion.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
SALIDA="$(realpath "${1:?Uso: lint-deb.sh <directorio-artefactos>}")"
test -s "$SALIDA/nimbo-net_0.1.0-1_all.deb"
ENGINE="${CONTAINER_ENGINE:-podman}"
command -v "$ENGINE" >/dev/null
IMAGE="$(sed -n 's/^IMAGE="\${NIMBO_BASE_IMAGE:-\(.*\)}"$/\1/p' "$REPO/iso/live-build/build-in-container.sh")"
IMAGE="${NIMBO_BASE_IMAGE:-$IMAGE}"; test -n "$IMAGE"
. "$REPO/iso/live-build/snapshot.env"
export NIMBO_SNAPSHOT NIMBO_ESPEJO="${NIMBO_ESPEJO:-}"
RO=":ro"; [ "$ENGINE" != podman ] || RO=":ro,Z"
"$ENGINE" run --rm --network=host -v "$SALIDA:/paquetes$RO" \
    -e NIMBO_SNAPSHOT -e NIMBO_ESPEJO -e LC_ALL=C.UTF-8 -e TZ=UTC \
    -e DEBIAN_FRONTEND=noninteractive "$IMAGE" bash -euo pipefail -c '
        printf "deb %s/archive/debian/%s/ bookworm main\n" "${NIMBO_ESPEJO:-http://snapshot.debian.org}" "$NIMBO_SNAPSHOT" > /etc/apt/sources.list
        rm -f /etc/apt/sources.list.d/debian.sources
        printf "Acquire::Check-Valid-Until \"false\";\nAcquire::Retries \"5\";\n" > /etc/apt/apt.conf.d/99nimbo-snapshot
        apt-get update -qq
        apt-get install -y -qq --no-install-recommends lintian > /tmp/lintian-install.log 2>&1 || { cat /tmp/lintian-install.log; exit 1; }
        lintian --version
        lintian /paquetes/nimbo-net_0.1.0-1_all.deb
    ' 2>&1 | tee "$SALIDA/lintian.log"
