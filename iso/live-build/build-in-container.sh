#!/usr/bin/env bash
# build-in-container.sh — construye la ISO live mínima dentro de un contenedor
# Debian bookworm con podman. Aísla la toolchain de Debian del host (aquí Fedora).
#
# Uso:   ./build-in-container.sh
# Salida: live-image-amd64.hybrid.iso (en esta misma carpeta)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

# --- Imagen base del contenedor ------------------------------------------------
# Reproducibilidad: lo ideal es anclar por digest
#   docker.io/library/debian@sha256:<...>
# Para este PRIMER ladrillo usamos el tag bookworm-slim (Debian 12). Anclar por
# digest es el SIGUIENTE paso de reproducibilidad (ver README §Reproducibilidad).
# Se puede sobreescribir con NIMBO_BASE_IMAGE=... ./build-in-container.sh
IMAGE="${NIMBO_BASE_IMAGE:-docker.io/library/debian:bookworm-slim}"

# --- Determinismo de tiempo ----------------------------------------------------
# SOURCE_DATE_EPOCH = timestamp del commit HEAD (determinista y trazable).
SOURCE_DATE_EPOCH="$(git -C "$HERE" log -1 --pretty=%ct 2>/dev/null || date +%s)"
export SOURCE_DATE_EPOCH

echo ">> Imagen base       : $IMAGE"
echo ">> SOURCE_DATE_EPOCH  : $SOURCE_DATE_EPOCH ($(date -u -d "@$SOURCE_DATE_EPOCH" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo '?'))"
echo ">> Directorio montado : $HERE -> /build"
echo

# --- Build ---------------------------------------------------------------------
# --privileged: live-build usa debootstrap/chroot/mounts.
# Se intenta ROOTLESS primero. Si los mounts fallan, NO se usa sudo aquí: correr el
# MISMO comando anteponiendo 'sudo' (ver README §Privilegios).
exec podman run --rm -t \
    --privileged \
    -v "$HERE":/build:Z \
    -w /build \
    -e SOURCE_DATE_EPOCH \
    -e TZ=UTC \
    -e LC_ALL=C.UTF-8 \
    -e DEBIAN_FRONTEND=noninteractive \
    "$IMAGE" \
    bash -euo pipefail -c '
        apt-get update
        apt-get install -y --no-install-recommends live-build ca-certificates
        lb clean --purge || true
        lb config
        lb build
        echo
        echo ">> Build terminado. ISO:"
        ls -lh live-image-*.iso 2>/dev/null || echo "   (no se encontró la ISO — revisar binary.buildlog)"
    '
