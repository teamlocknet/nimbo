#!/usr/bin/env bash
# generar-branding.sh — genera los PNG de branding de Calamares desde los SVG propios.
#
# Fuente de verdad: iso/branding/*.svg (escritos a mano en el repo, solo geometría, sin
# texto ni tipografías; autoría y licencia en CREDITOS.md). Los PNG que consume el
# instalador se versionan en config/includes.chroot/etc/calamares/branding/nimbo/ para que
# el build de la ISO no dependa de esta herramienta; este script es cómo se regeneran.
#
# Determinista: mismo contenedor por digest y mismo snapshot que la ISO (ADR-004),
# rsvg-convert de bookworm. Dos ejecuciones dan los mismos bytes (lo comprueba al final).
#
#   CONTAINER_ENGINE=docker ./iso/branding/generar-branding.sh    # o podman (por defecto)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LB="$(cd "$HERE/../live-build" && pwd)"
DEST="$LB/config/includes.chroot/etc/calamares/branding/nimbo"

ENGINE="${CONTAINER_ENGINE:-podman}"
command -v "$ENGINE" >/dev/null || { echo "ERROR: no está instalado el motor '$ENGINE'"; exit 1; }
VOL_OPT=""
[ "$ENGINE" = "podman" ] && VOL_OPT=":Z"

# Mismo digest que la receta de la ISO; la guarda falla si dejan de coincidir.
DIGEST_DEFAULT="docker.io/library/debian@sha256:88200866dfff7ea7f5cbcb6ec7c8a701889efe6fe859fe64d6990e4b07ea4171"
IMAGE="${NIMBO_BASE_IMAGE:-$DIGEST_DEFAULT}"
DIGEST_RECETA="$(sed -n 's/^IMAGE="\${NIMBO_BASE_IMAGE:-\(.*\)}"$/\1/p' "$LB/build-in-container.sh")"
if [ "$DIGEST_RECETA" != "$DIGEST_DEFAULT" ]; then
    echo "ERROR: el digest de este script no coincide con el de la receta de la ISO:"
    echo "   receta   : ${DIGEST_RECETA:-?}"
    echo "   branding : $DIGEST_DEFAULT"
    exit 1
fi

# shellcheck source=../live-build/snapshot.env
. "$LB/snapshot.env"
export NIMBO_SNAPSHOT

echo ">> Motor    : $ENGINE"
echo ">> Imagen   : $IMAGE"
echo ">> Snapshot : $NIMBO_SNAPSHOT"
echo ">> Destino  : $DEST"

"$ENGINE" run --rm \
    --network=host \
    -v "$HERE":/src:ro"$VOL_OPT" \
    -v "$DEST":/out"$VOL_OPT" \
    -e NIMBO_SNAPSHOT \
    -e TZ=UTC \
    -e LC_ALL=C.UTF-8 \
    -e DEBIAN_FRONTEND=noninteractive \
    -e HOST_UID="$(id -u)" -e HOST_GID="$(id -g)" \
    "$IMAGE" \
    bash -euo pipefail -c '
        printf "deb http://snapshot.debian.org/archive/debian/%s/ bookworm main\n" "$NIMBO_SNAPSHOT" > /etc/apt/sources.list
        rm -f /etc/apt/sources.list.d/debian.sources
        printf "Acquire::Check-Valid-Until \"false\";\nAcquire::Retries \"5\";\n" > /etc/apt/apt.conf.d/99nimbo-snapshot
        apt-get update -qq
        apt-get install -y -qq --no-install-recommends librsvg2-bin >/dev/null
        echo ">> $(dpkg-query -W -f="\${Package} \${Version}" librsvg2-bin)"
        render() {  # $1 = nombre base; renderiza dos veces y exige bytes idénticos
            rsvg-convert --format=png -o "/tmp/$1.a.png" "/src/$1.svg"
            rsvg-convert --format=png -o "/tmp/$1.b.png" "/src/$1.svg"
            cmp -s "/tmp/$1.a.png" "/tmp/$1.b.png" || { echo "ERROR: $1.png no es determinista"; exit 1; }
            install -m 0644 -o "$HOST_UID" -g "$HOST_GID" "/tmp/$1.a.png" "/out/$1.png"
            echo ">> $1.png  $(sha256sum "/out/$1.png" | cut -c1-16)…  (2 renders idénticos)"
        }
        render nimbo
        render nimbo-bienvenida
    '
