#!/usr/bin/env bash
# test-in-bookworm.sh — corre los tests de nimbo-audit con el Python 3.11 de bookworm y
# las dependencias instaladas DESDE APT (no pip), en el mismo contenedor anclado que
# construye la ISO.
#
# Por qué APT y no pip: la ISO es offline y el CLI va a correr con las versiones que
# trae bookworm (ADR-005): python3 3.11, python3-typer 0.7, python3-click 8.1,
# python3-pytest 7.2. Un test verde en el venv local (Python/Typer recientes) no prueba
# que el CLI funcione en el producto.
#
# Motor de contenedor agnóstico (paridad dev/CI, igual que iso/live-build):
#   - Local: CONTAINER_ENGINE=podman (por defecto) o docker. No necesita --privileged.
#   - CI   : CONTAINER_ENGINE=docker ./packages/nimbo-audit/test-in-bookworm.sh
#
# Anclaje (ADR-004): misma imagen por digest y mismo snapshot que el build de la ISO
# (iso/live-build/snapshot.env). Una GUARDA falla si el digest de este script deja de
# coincidir con el de iso/live-build/build-in-container.sh.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
LB="$REPO/iso/live-build"

# --- Motor de contenedor -------------------------------------------------------
ENGINE="${CONTAINER_ENGINE:-podman}"
command -v "$ENGINE" >/dev/null || { echo "ERROR: no está instalado el motor '$ENGINE'"; exit 1; }
VOL_OPT=""
[ "$ENGINE" = "podman" ] && VOL_OPT=":Z"

# --- Imagen base: el MISMO digest que el build de la ISO ------------------------
DIGEST_DEFAULT="docker.io/library/debian@sha256:88200866dfff7ea7f5cbcb6ec7c8a701889efe6fe859fe64d6990e4b07ea4171"
IMAGE="${NIMBO_BASE_IMAGE:-$DIGEST_DEFAULT}"

# GUARDA: el digest vive duplicado (build-in-container.sh, repro/diff-isos.sh y aquí).
# Si alguien lo mueve en la receta y olvida este script, los tests correrían sobre otro
# entorno sin avisar. Se compara el valor POR DEFECTO de ambos scripts.
DIGEST_RECETA="$(sed -n 's/^IMAGE="\${NIMBO_BASE_IMAGE:-\(.*\)}"$/\1/p' "$LB/build-in-container.sh")"
if [ -z "$DIGEST_RECETA" ]; then
    echo "ERROR: no pude leer el digest por defecto de $LB/build-in-container.sh"; exit 1
fi
if [ "$DIGEST_RECETA" != "$DIGEST_DEFAULT" ]; then
    echo "ERROR: el digest de este script no coincide con el de la receta de la ISO:"
    echo "   receta : $DIGEST_RECETA"
    echo "   tests  : $DIGEST_DEFAULT"
    exit 1
fi

# --- Snapshot: fuente única del anclaje temporal --------------------------------
# shellcheck source=../../iso/live-build/snapshot.env
. "$LB/snapshot.env"
[ -n "${NIMBO_SNAPSHOT:-}" ] || { echo "ERROR: NIMBO_SNAPSHOT vacío en $LB/snapshot.env"; exit 1; }
export NIMBO_SNAPSHOT   # snapshot.env solo asigna; -e NIMBO_SNAPSHOT necesita que esté exportada

echo ">> Motor     : $ENGINE"
echo ">> Imagen    : $IMAGE"
echo ">> Snapshot  : $NIMBO_SNAPSHOT"
echo ">> Paquete   : $HERE (montado de solo lectura)"
echo

# El código se monta de solo lectura y se copia dentro: el contenedor no escribe
# cachés ni egg-info en el árbol del host.
exec "$ENGINE" run --rm \
    --network=host \
    -v "$HERE":/src:ro"$VOL_OPT" \
    -e NIMBO_SNAPSHOT \
    -e TZ=UTC \
    -e LC_ALL=C.UTF-8 \
    -e DEBIAN_FRONTEND=noninteractive \
    "$IMAGE" \
    bash -euo pipefail -c '
        printf "deb http://snapshot.debian.org/archive/debian/%s/ bookworm main\n" "$NIMBO_SNAPSHOT" > /etc/apt/sources.list
        rm -f /etc/apt/sources.list.d/debian.sources
        printf "Acquire::Check-Valid-Until \"false\";\nAcquire::Retries \"5\";\n" > /etc/apt/apt.conf.d/99nimbo-snapshot
        apt-get update -qq
        apt-get install -y -qq --no-install-recommends python3-typer python3-pytest >/dev/null
        echo ">> Versiones de bookworm (APT):"
        dpkg-query -W -f="   \${Package} \${Version}\n" python3 python3-typer python3-click python3-pytest
        echo
        cp -r /src /w
        cd /w
        rm -rf .venv src/*.egg-info
        PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider
    '
