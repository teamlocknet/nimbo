#!/usr/bin/env bash
# diff-isos.sh — compara las dos ISOs de build-twice.sh con diffoscope y genera un
# reporte legible (HTML + texto). diffoscope corre en un contenedor Debian con las
# herramientas de descenso (xorriso, squashfs-tools, binutils) — 100% FOSS, no
# ensucia el host. ROOTLESS: solo lee las ISOs y hace unsquashfs en userspace.
#
# Uso:   ./diff-isos.sh            (tras haber corrido build-twice.sh)
# Salida: repro/out/reporte-diffoscope.html  y  .txt
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$REPO/repro/out"
ENGINE="${CONTAINER_ENGINE:-podman}"

# Misma imagen base anclada por digest que el build (parity + reproducibilidad).
IMAGE="${NIMBO_DIFF_IMAGE:-docker.io/library/debian@sha256:88200866dfff7ea7f5cbcb6ec7c8a701889efe6fe859fe64d6990e4b07ea4171}"

A="$OUT/iso-A/live-image-amd64.hybrid.iso"
B="$OUT/iso-B/live-image-amd64.hybrid.iso"
[ -f "$A" ] && [ -f "$B" ] || { echo "ERROR: faltan las ISOs. Corre primero build-twice.sh"; exit 1; }

echo ">> Motor  : $ENGINE"
echo ">> Imagen : $IMAGE"
echo ">> A: $A"
echo ">> B: $B"
echo ">> Ejecutando diffoscope en contenedor (instala diffoscope + herramientas)..."

VOL_OPT=""; [ "$ENGINE" = "podman" ] && VOL_OPT=":Z"

"$ENGINE" run --rm \
    --network=host \
    -v "$OUT":/work"$VOL_OPT" \
    -w /work \
    -e DEBIAN_FRONTEND=noninteractive \
    "$IMAGE" \
    bash -euo pipefail -c '
        apt-get update
        # Herramientas de descenso para que diffoscope entre en cada capa:
        #  genisoimage(isoinfo)=ISO9660, squashfs-tools(unsquashfs)=filesystem.squashfs,
        #  cpio+gzip+xz-utils=initrd, mtools=efi.img(FAT), binutils/xxd/file=binarios.
        apt-get install -y --no-install-recommends \
            diffoscope genisoimage xorriso squashfs-tools \
            binutils file xxd cpio mtools gzip xz-utils
        echo ">> diffoscope $(diffoscope --version 2>/dev/null | head -1)"
        # diffoscope devuelve 1 cuando hay diferencias: no debe abortar el script.
        diffoscope \
            --html /work/reporte-diffoscope.html \
            --text /work/reporte-diffoscope.txt \
            --max-report-size 80000000 \
            /work/iso-A/live-image-amd64.hybrid.iso \
            /work/iso-B/live-image-amd64.hybrid.iso \
            && echo ">> diffoscope: SIN diferencias (ISOs idénticas)." \
            || echo ">> diffoscope: encontró diferencias (ver reporte-diffoscope.html/.txt)."

        # --- Análisis del squashfs SIN privilegios --------------------------------
        # unsquashfs no puede crear device nodes en rootless, pero -s (superbloque) y
        # -lls (listado con permisos/mtimes/orden) NO extraen nada: sirven para
        # clasificar el no-determinismo (timestamps vs orden vs compresión).
        echo ">> Extrayendo y analizando live/filesystem.squashfs de cada ISO..."
        for x in A B; do
            osirrox_iso="/work/iso-$x/live-image-amd64.hybrid.iso"
            xorriso -osirrox on -indev "$osirrox_iso" \
                    -extract /live/filesystem.squashfs "/work/sq-$x.squashfs" 2>/dev/null
            unsquashfs -s "/work/sq-$x.squashfs" > "/work/sq-$x.superblock.txt" 2>&1 || true
            unsquashfs -lls "/work/sq-$x.squashfs" > "/work/sq-$x.listado.txt" 2>&1 || true
        done
        echo "== Superbloque (A vs B) =="
        diff -u /work/sq-A.superblock.txt /work/sq-B.superblock.txt \
            && echo "   superbloques IDÉNTICOS" || echo "   (superbloques difieren, ver arriba)"
        echo "== Listado de archivos (A vs B): nº de líneas que difieren =="
        diff /work/sq-A.listado.txt /work/sq-B.listado.txt > /work/sq.listado.diff || true
        wc -l < /work/sq.listado.diff | sed "s/^/   lineas de diff en el listado: /"
        rm -f /work/sq-A.squashfs /work/sq-B.squashfs
    '
