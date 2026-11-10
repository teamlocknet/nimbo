#!/usr/bin/env bash
# test-arnes-resolucion-fija.sh — con Secure Boot, la pantalla de la VM tiene resolución fija.
#
# Por qué existe (10-nov): con --secure-boot el arnés usaba `-vga virtio`. La tarjeta virtio
# adopta el tamaño de la ventana GTK de QEMU. En un gestor de ventanas en mosaico (Hyprland)
# la ventana nace pequeña y el escritorio de la VM arrancó a 941x484: Calamares no cabía
# y sus botones de abajo quedaban fuera de la pantalla. Maximizar solo escalaba la imagen.
# Arreglo: `bochs-display` (no sigue a la ventana) con resolución fija y `zoom-to-fit=on`.
#
# Cómo prueba: carga lib-qemu.sh y llama a nimbo_video_args. No arranca ninguna VM ni
# descarga el OVMF.
#
# Uso: ./iso/live-build/tests/test-arnes-resolucion-fija.sh   (sale con 0 solo si pasa)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$HERE/.."

fallos=0
ok()    { echo "  ok    $*"; }
falla() { echo "  FALLA $*"; fallos=$((fallos + 1)); }

# shellcheck source=../lib-qemu.sh
. "$SRC/lib-qemu.sh"

args() { (unset NIMBO_QEMU_VGA NIMBO_QEMU_RES; for kv in "${@:2}"; do export "${kv?}"; done
          nimbo_video_args "$1" 2>&1 | tr '\n' ' ') || true; }

echo "== nimbo_video_args"
if ! declare -F nimbo_video_args >/dev/null; then
    falla "lib-qemu.sh no define nimbo_video_args"
else
    a="$(args 1)"
    [[ "$a" == *"-vga none "* && "$a" == *"bochs-display,xres=1280,yres=800"* ]] \
        && ok "Secure Boot: bochs-display 1280x800 fijo" || falla "Secure Boot: '$a'"
    [[ "$a" != *virtio* ]] && ok "Secure Boot: sin virtio (sigue a la ventana)" || falla "Secure Boot sigue con virtio: '$a'"

    a="$(args 1 NIMBO_QEMU_RES=1920x1080)"
    [[ "$a" == *"xres=1920,yres=1080"* ]] && ok "NIMBO_QEMU_RES cambia la resolución" || falla "NIMBO_QEMU_RES: '$a'"

    a="$(args 1 NIMBO_QEMU_RES=grande)"
    [[ "$a" == *ERROR* ]] && ok "NIMBO_QEMU_RES mal formada → ERROR" || falla "acepta NIMBO_QEMU_RES=grande: '$a'"

    a="$(args 1 NIMBO_QEMU_VGA=virtio)"
    [[ "$a" == "-vga virtio " ]] && ok "NIMBO_QEMU_VGA sigue mandando" || falla "NIMBO_QEMU_VGA=virtio: '$a'"

    a="$(args 0)"
    [[ "$a" == "-vga std " ]] && ok "sin Secure Boot: -vga std (sin cambios)" || falla "sin Secure Boot: '$a'"
fi

echo "== install-in-qemu.sh"
grep -q 'nimbo_video_args' "$SRC/install-in-qemu.sh" \
    && ok "usa nimbo_video_args" || falla "no usa nimbo_video_args"
grep -q 'zoom-to-fit=on' "$SRC/install-in-qemu.sh" \
    && ok "ventana GTK con zoom-to-fit=on" || falla "falta zoom-to-fit=on en la ventana GTK"

echo
if [ "$fallos" -ne 0 ]; then echo "RESULTADO: $fallos comprobaciones fallaron"; exit 1; fi
echo "RESULTADO: OK"
