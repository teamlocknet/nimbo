#!/usr/bin/env bash
# build-in-container.sh — construye la ISO live mínima dentro de un contenedor
# Debian bookworm, aislando la toolchain de Debian del host.
#
# Motor de contenedor agnóstico (paridad dev/CI):
#   - Local (Fedora):   CONTAINER_ENGINE=podman (por defecto). DEBE correr rootful,
#                       porque debootstrap crea device nodes (mknod), imposible en
#                       podman rootless:
#                           sudo ./build-in-container.sh
#   - CI (ubuntu):      CONTAINER_ENGINE=docker ./build-in-container.sh
#                       (el runner permite --privileged sin sudo)
#
# La LÓGICA DE BUILD es idéntica en ambos: solo cambia el motor. No se reinventa
# la receta (misma imagen, mismo apt-get install live-build && lb config && lb build).
#
# Salida: live-image-amd64.hybrid.iso (en esta misma carpeta)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$HERE"

# --- Motor de contenedor -------------------------------------------------------
ENGINE="${CONTAINER_ENGINE:-podman}"
command -v "$ENGINE" >/dev/null || { echo "ERROR: no está instalado el motor '$ENGINE'"; exit 1; }

# :Z (relabel SELinux) solo aplica a podman en hosts con SELinux (Fedora); docker
# en Ubuntu no lo necesita.
VOL_OPT=""
[ "$ENGINE" = "podman" ] && VOL_OPT=":Z"

# -t (tty) solo si hay terminal interactiva (en CI no la hay).
TTY_OPT=()
[ -t 1 ] && TTY_OPT=(-t)

# --- Imagen base del contenedor ------------------------------------------------
# Anclada por DIGEST del índice multi-arch (reproducibilidad; docker y podman
# resuelven el amd64 desde el mismo índice). Forma solo-digest (canónica, aceptada
# por todos los motores). Este digest corresponde al tag debian:bookworm-slim.
# Sobreescribible con NIMBO_BASE_IMAGE=... ./build-in-container.sh
IMAGE="${NIMBO_BASE_IMAGE:-docker.io/library/debian@sha256:88200866dfff7ea7f5cbcb6ec7c8a701889efe6fe859fe64d6990e4b07ea4171}"

# --- Determinismo de tiempo ----------------------------------------------------
# SOURCE_DATE_EPOCH: se respeta si viene del entorno (CI lo pasa explícito); si no,
# se calcula desde el commit HEAD. -c safe.directory='*' evita el aviso de "dubious
# ownership" al correr con sudo sobre un repo de otro usuario.
SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-$(git -c safe.directory='*' -C "$HERE" log -1 --pretty=%ct 2>/dev/null || date +%s)}"
export SOURCE_DATE_EPOCH

echo ">> Motor             : $ENGINE"
echo ">> Imagen base       : $IMAGE"
echo ">> SOURCE_DATE_EPOCH  : $SOURCE_DATE_EPOCH ($(date -u -d "@$SOURCE_DATE_EPOCH" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo '?'))"
echo ">> Directorio montado : $HERE -> /build"
echo

# --- Build ---------------------------------------------------------------------
# --privileged : live-build usa debootstrap/chroot/mknod.
# --network=host: el contenedor debe alcanzar los mirrors de Debian (en Fedora el
#                 podman rootful no resuelve DNS con su backend propio; en CI iguala
#                 el comportamiento).
exec "$ENGINE" run --rm "${TTY_OPT[@]}" \
    --privileged \
    --network=host \
    -v "$HERE":/build"$VOL_OPT" \
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
