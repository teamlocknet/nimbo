#!/usr/bin/env bash
# build-twice.sh — arnés de reproducibilidad (Paso 1C.1): compila la ISO DOS VECES
# del MISMO commit con el MISMO SOURCE_DATE_EPOCH, reutilizando el build de 1A/1B
# (iso/live-build/build-in-container.sh) SIN modificarlo.
#
# Salidas en repro/out/:
#   iso-A/live-image-amd64.hybrid.iso  + .packages (manifiesto de paquetes)
#   iso-B/live-image-amd64.hybrid.iso  + .packages
#   sha256.txt        — SHA-256 de A y B + veredicto MATCH/DIFFER
#   packages.diff     — diff de los manifiestos (clase "versión de paquete")
#
# Necesita privilegios (podman rootful, como 1A/1B):
#     sudo ./build-twice.sh
# NO cierra ningún no-determinismo: solo MIDE.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LB="$REPO/iso/live-build"
OUT="$REPO/repro/out"
ENGINE="${CONTAINER_ENGINE:-podman}"

# Un único SOURCE_DATE_EPOCH (commit HEAD) compartido por AMBOS builds.
SOURCE_DATE_EPOCH="$(git -c safe.directory='*' -C "$REPO" log -1 --pretty=%ct)"
export SOURCE_DATE_EPOCH CONTAINER_ENGINE="$ENGINE"

echo ">> Repo              : $REPO"
echo ">> SOURCE_DATE_EPOCH  : $SOURCE_DATE_EPOCH ($(date -u -d "@$SOURCE_DATE_EPOCH" +%Y-%m-%dT%H:%M:%SZ))"
echo ">> Motor             : $ENGINE"
echo

rm -rf "$OUT"
mkdir -p "$OUT/iso-A" "$OUT/iso-B"

build_once() {
    local dest="$1" label="$2"
    echo "==================================================================="
    echo ">> BUILD $label -> $dest"
    echo "==================================================================="
    ( cd "$LB" && ./build-in-container.sh )
    cp "$LB/live-image-amd64.hybrid.iso" "$dest/"
    # Manifiesto de paquetes (para separar 'versión de paquete' de 'intrínseco').
    cp "$LB/live-image-amd64.packages" "$dest/" 2>/dev/null || \
        echo "   (aviso: no se encontró live-image-amd64.packages)"
}

build_once "$OUT/iso-A" "A"
build_once "$OUT/iso-B" "B"

# --- SHA-256 y veredicto -------------------------------------------------------
A_SHA="$(sha256sum "$OUT/iso-A/live-image-amd64.hybrid.iso" | awk '{print $1}')"
B_SHA="$(sha256sum "$OUT/iso-B/live-image-amd64.hybrid.iso" | awk '{print $1}')"
{
    echo "SOURCE_DATE_EPOCH=$SOURCE_DATE_EPOCH"
    echo "iso-A  $A_SHA"
    echo "iso-B  $B_SHA"
    if [ "$A_SHA" = "$B_SHA" ]; then echo "VEREDICTO: MATCH (bit-idéntico)"; else echo "VEREDICTO: DIFFER"; fi
} | tee "$OUT/sha256.txt"

# --- Diff de manifiestos de paquetes (clase 'versión de paquete') --------------
if [ -f "$OUT/iso-A/live-image-amd64.packages" ] && [ -f "$OUT/iso-B/live-image-amd64.packages" ]; then
    if diff -u "$OUT/iso-A/live-image-amd64.packages" "$OUT/iso-B/live-image-amd64.packages" > "$OUT/packages.diff"; then
        echo ">> Manifiestos de paquetes IDÉNTICOS → cualquier diff de las ISOs es INTRÍNSECO del pipeline."
    else
        echo ">> Los manifiestos DIFIEREN (ver packages.diff) → parte del diff es 'versión de paquete' (→ snapshot.debian.org)."
    fi
fi

# Devolver la propiedad de las salidas al usuario que invocó sudo.
if [ -n "${SUDO_USER:-}" ]; then chown -R "$SUDO_USER":"$(id -gn "$SUDO_USER")" "$OUT" || true; fi

echo
echo ">> Listo. Salidas en: $OUT"
echo ">> Siguiente: ./diff-isos.sh (rootless) para el reporte de diffoscope."
