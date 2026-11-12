#!/usr/bin/env bash
# Construye el paquete sin tocar la red del host ni instalarlo en el host.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
LB="$REPO/iso/live-build"
ENGINE="${CONTAINER_ENGINE:-podman}"
command -v "$ENGINE" >/dev/null
IMAGE="$(sed -n 's/^IMAGE="\${NIMBO_BASE_IMAGE:-\(.*\)}"$/\1/p' "$LB/build-in-container.sh")"
IMAGE="${NIMBO_BASE_IMAGE:-$IMAGE}"
test -n "$IMAGE"
. "$LB/snapshot.env"
export NIMBO_SNAPSHOT NIMBO_ESPEJO="${NIMBO_ESPEJO:-}"
export SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-$(git -c safe.directory='*' -C "$REPO" log -1 --pretty=%ct)}"
SALIDA="$(mktemp -d /tmp/nimbo-net-deb.XXXXXX)"
echo "Artefactos: $SALIDA"
RO=":ro"; RW=""
if [ "$ENGINE" = podman ]; then RO=":ro,Z"; RW=":Z"; fi
"$ENGINE" run --rm --network=host \
    -v "$HERE:/src$RO" -v "$SALIDA:/out$RW" \
    -e NIMBO_SNAPSHOT -e NIMBO_ESPEJO -e SOURCE_DATE_EPOCH \
    -e HOST_UID="${SUDO_UID:-$(id -u)}" -e HOST_GID="${SUDO_GID:-$(id -g)}" \
    -e TZ=UTC -e LC_ALL=C.UTF-8 -e DEBIAN_FRONTEND=noninteractive \
    "$IMAGE" bash -euo pipefail -c '
        printf "deb %s/archive/debian/%s/ bookworm main\n" "${NIMBO_ESPEJO:-http://snapshot.debian.org}" "$NIMBO_SNAPSHOT" > /etc/apt/sources.list
        rm -f /etc/apt/sources.list.d/debian.sources
        printf "Acquire::Check-Valid-Until \"false\";\nAcquire::Retries \"5\";\n" > /etc/apt/apt.conf.d/99nimbo-snapshot
        apt-get update -qq
        apt-get install -y -qq --no-install-recommends \
            build-essential fakeroot debhelper dh-python pybuild-plugin-pyproject \
            python3-all python3-setuptools python3-pytest
        mkdir /trabajo
        cp -a /src /trabajo/nimbo-net
        cd /trabajo/nimbo-net
        dpkg-buildpackage -us -uc -b
        cp /trabajo/*.deb /trabajo/*.changes /trabajo/*.buildinfo /out/
        chown "$HOST_UID:$HOST_GID" /out /out/*
        set -- /out/*.deb
        [ "$#" -eq 1 ]
        [ "$(dpkg-deb -f "$1" Package)" = nimbo-net ]
        dpkg-deb -f "$1" Package Version Architecture Depends
        dpkg-deb -c "$1"
        sha256sum "$1"
    ' 2>&1 | tee "$SALIDA/build.log"
