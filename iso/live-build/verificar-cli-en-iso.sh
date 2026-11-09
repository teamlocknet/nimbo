#!/usr/bin/env bash
# PR-B: extrae LA ISO y comprueba su squashfs en un contenedor desechable.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ISO="${1:-$HERE/live-image-amd64.hybrid.iso}"
[ -f "$ISO" ] || { echo "ERROR: no existe ISO: $ISO" >&2; exit 1; }
ISO="$(realpath "$ISO")"
ENGINE="${CONTAINER_ENGINE:-podman}"
IMAGE="$(sed -n 's/^IMAGE="\${NIMBO_BASE_IMAGE:-\(.*\)}"$/\1/p' "$HERE/build-in-container.sh")"
IMAGE="${NIMBO_BASE_IMAGE:-$IMAGE}"
[ -n "$IMAGE" ] || { echo "ERROR: imagen base no resuelta" >&2; exit 1; }
. "$HERE/snapshot.env"
export NIMBO_SNAPSHOT
export NIMBO_ESPEJO="${NIMBO_ESPEJO:-}"
RO=":ro"
[ "$ENGINE" = podman ] && RO=":ro,Z"
echo "P: [PR-B] verificando ISO $(sha256sum "$ISO")"
"$ENGINE" run --rm --network=host     -v "$ISO:/entrada.iso$RO"     -v "$HERE/verificar-cli-rootfs.sh:/verificar-cli-rootfs.sh$RO"     -e NIMBO_SNAPSHOT -e NIMBO_ESPEJO -e TZ=UTC -e LC_ALL=C.UTF-8     -e DEBIAN_FRONTEND=noninteractive "$IMAGE" bash -euo pipefail -c '
        printf "deb %s/archive/debian/%s/ bookworm main\n" "${NIMBO_ESPEJO:-http://snapshot.debian.org}" "$NIMBO_SNAPSHOT" > /etc/apt/sources.list
        rm -f /etc/apt/sources.list.d/debian.sources
        printf "Acquire::Check-Valid-Until \"false\";\nAcquire::Retries \"5\";\n" > /etc/apt/apt.conf.d/99nimbo-snapshot
        apt-get update -qq
        apt-get install -y -qq --no-install-recommends xorriso squashfs-tools >/tmp/herramientas.log 2>&1 || { cat /tmp/herramientas.log; exit 1; }
        xorriso -osirrox on -indev /entrada.iso -extract /live/filesystem.squashfs /tmp/filesystem.squashfs
        unsquashfs -no-progress -no-xattrs -d /tmp/rootfs /tmp/filesystem.squashfs >/tmp/extraccion.log 2>&1 || { cat /tmp/extraccion.log; exit 1; }
        bash /verificar-cli-rootfs.sh /tmp/rootfs
    '
