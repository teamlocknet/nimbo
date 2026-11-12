#!/usr/bin/env bash
# Instalacion en contenedor desechable; nunca activa una VPN real.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
SALIDA="$(realpath "${1:?Uso: test-deb.sh <directorio-artefactos>}")"
NET="$SALIDA/nimbo-net_0.1.0-1_all.deb"
test -s "$NET"
ENGINE="${CONTAINER_ENGINE:-podman}"
command -v "$ENGINE" >/dev/null
IMAGE="$(sed -n 's/^IMAGE="\${NIMBO_BASE_IMAGE:-\(.*\)}"$/\1/p' "$REPO/iso/live-build/build-in-container.sh")"
IMAGE="${NIMBO_BASE_IMAGE:-$IMAGE}"; test -n "$IMAGE"
. "$REPO/iso/live-build/snapshot.env"
export NIMBO_SNAPSHOT NIMBO_ESPEJO="${NIMBO_ESPEJO:-}"
RO=":ro"; [ "$ENGINE" != podman ] || RO=":ro,Z"
"$ENGINE" run --rm --network=host \
    -v "$SALIDA:/paquetes$RO" -v "$REPO/packages/nimbo-red:/src-red$RO" \
    -e NIMBO_SNAPSHOT -e NIMBO_ESPEJO -e TZ=UTC -e LC_ALL=C.UTF-8 \
    -e DEBIAN_FRONTEND=noninteractive "$IMAGE" bash -euo pipefail -c '
        printf "deb %s/archive/debian/%s/ bookworm main\n" "${NIMBO_ESPEJO:-http://snapshot.debian.org}" "$NIMBO_SNAPSHOT" > /etc/apt/sources.list
        rm -f /etc/apt/sources.list.d/debian.sources
        printf "Acquire::Check-Valid-Until \"false\";\nAcquire::Retries \"5\";\n" > /etc/apt/apt.conf.d/99nimbo-snapshot
        apt-get update -qq
        apt-get install -y -qq --no-install-recommends \
            build-essential fakeroot debhelper dh-python pybuild-plugin-pyproject \
            python3-all python3-setuptools python3-pytest
        # nimbo-red aun no esta publicado en APT. Construir su paquete sin tocar
        # su fuente ni sustituirlo por una instalacion Python que omita Depends.
        mkdir /trabajo
        cp -a /src-red /trabajo/nimbo-red
        cd /trabajo/nimbo-red
        dpkg-buildpackage -us -uc -b
        # El slim excluye manuales; excepcion solo en este contenedor de prueba.
        printf "%s\n" "path-include /usr/share/man/" "path-include /usr/share/man/man1/" "path-include /usr/share/man/man1/nimbo-net.1.gz" > /etc/dpkg/dpkg.cfg.d/zz-nimbo-net-test-manual
        apt-get install -y --no-install-recommends \
            /trabajo/nimbo-red_0.1.0-1_all.deb /paquetes/nimbo-net_0.1.0-1_all.deb
        cd /tmp
        unset PYTHONPATH
        test ! -e /etc/nimbo-net
        test ! -e /sys/class/net/wg-nimbo
        ip -j link show > /tmp/enlaces-antes.json
        command -v nimbo-net
        nimbo-net --help
        test -s /usr/share/man/man1/nimbo-net.1.gz
        gzip -t /usr/share/man/man1/nimbo-net.1.gz
        echo "OK: manual instalado e integro"
        nimbo-net status
        rc=0
        nimbo-net join || rc=$?
        test "$rc" -eq 1
        ip -j link show > /tmp/enlaces-despues.json
        cmp /tmp/enlaces-antes.json /tmp/enlaces-despues.json
        test ! -e /sys/class/net/wg-nimbo
        dpkg-query -W nimbo-net nimbo-red wireguard-tools iproute2 iputils-ping nftables systemd
        sha256sum /paquetes/nimbo-net_0.1.0-1_all.deb
        echo "OK: instalacion, ayuda y status; join sin perfil falla sin crear interfaz"
    ' 2>&1 | tee "$SALIDA/test.log"
