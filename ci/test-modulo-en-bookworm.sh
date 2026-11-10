#!/usr/bin/env bash
# test-modulo-en-bookworm.sh — corre los tests (pytest) de un módulo Python de nimbo con el
# Python 3.11 de bookworm y sus dependencias DESDE APT, en el mismo contenedor anclado que
# construye la ISO. Es la versión genérica de packages/nimbo-audit/test-in-bookworm.sh.
#
# Uso: ci/test-modulo-en-bookworm.sh <carpeta-del-paquete> [paquetes-apt-extra...]
#   ci/test-modulo-en-bookworm.sh packages/nimbo-nav
#   ci/test-modulo-en-bookworm.sh packages/nimbo-update-offline gnupg
#
# Motor: CONTAINER_ENGINE=podman (por defecto) o docker (CI).
#
# Anclaje (ADR-004): la imagen se lee DIRECTAMENTE de iso/live-build/build-in-container.sh
# y el snapshot de iso/live-build/snapshot.env. Así este script no añade otra copia del
# digest.
set -euo pipefail

[ $# -ge 1 ] || { sed -n '6,9p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LB="$REPO/iso/live-build"
PKG="$(cd "$1" && pwd)"; shift
[ -d "$PKG/tests" ] || { echo "ERROR: $PKG no tiene carpeta tests/"; exit 1; }

ENGINE="${CONTAINER_ENGINE:-podman}"
command -v "$ENGINE" >/dev/null || { echo "ERROR: no está instalado el motor '$ENGINE'"; exit 1; }
VOL_OPT=""
[ "$ENGINE" = "podman" ] && VOL_OPT=":Z"

IMAGE="$(sed -n 's/^IMAGE="\${NIMBO_BASE_IMAGE:-\(.*\)}"$/\1/p' "$LB/build-in-container.sh")"
[ -n "$IMAGE" ] || { echo "ERROR: no pude leer la imagen de $LB/build-in-container.sh"; exit 1; }

# shellcheck source=../iso/live-build/snapshot.env
. "$LB/snapshot.env"
[ -n "${NIMBO_SNAPSHOT:-}" ] || { echo "ERROR: NIMBO_SNAPSHOT vacío en $LB/snapshot.env"; exit 1; }
export NIMBO_SNAPSHOT
export NIMBO_APT_EXTRA="$*"

echo ">> Motor     : $ENGINE"
echo ">> Imagen    : $IMAGE"
echo ">> Snapshot  : $NIMBO_SNAPSHOT"
echo ">> Paquete   : $PKG (montado de solo lectura)"
echo ">> APT extra : ${NIMBO_APT_EXTRA:-(ninguno)}"
echo

# El código se monta de solo lectura y se copia dentro: el contenedor no escribe en el
# árbol del host.
exec "$ENGINE" run --rm \
    --network=host \
    -v "$PKG":/src:ro"$VOL_OPT" \
    -e NIMBO_SNAPSHOT -e NIMBO_APT_EXTRA \
    -e TZ=UTC \
    -e LC_ALL=C.UTF-8 \
    -e DEBIAN_FRONTEND=noninteractive \
    "$IMAGE" \
    bash -euo pipefail -c '
        printf "deb http://snapshot.debian.org/archive/debian/%s/ bookworm main\n" "$NIMBO_SNAPSHOT" > /etc/apt/sources.list
        rm -f /etc/apt/sources.list.d/debian.sources
        printf "Acquire::Check-Valid-Until \"false\";\nAcquire::Retries \"5\";\n" > /etc/apt/apt.conf.d/99nimbo-snapshot
        apt-get update -qq
        # shellcheck disable=SC2086
        apt-get install -y -qq --no-install-recommends python3 python3-pytest $NIMBO_APT_EXTRA >/dev/null
        echo ">> Versiones de bookworm (APT):"
        dpkg-query -W -f="   \${Package} \${Version}\n" python3 python3-pytest $NIMBO_APT_EXTRA
        echo
        cp -r /src /w
        cd /w
        rm -rf .venv src/*.egg-info
        PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider
    '
