#!/bin/sh
# probar-h002.sh — camino de PRUEBA de los mensajes honestos de H-002 (ADR-009). No va en la ISO.
#
# Instala en un sistema YA instalado los tres ficheros que la ISO lleva en
# config/includes.chroot/ (mismas rutas, mismos permisos) y regenera el initrd con
# initramfs-tools, igual que haría el instalador. Así se valida el cambio en QEMU sin
# reinstalar. install-in-qemu.sh lo entrega por el disco auxiliar de solo lectura.
#
# Dentro del sistema instalado (camino por defecto, initramfs-tools; NO tras nimbo-tpm-setup):
#   sudo mount -o ro /dev/vdb1 /mnt && sudo sh /mnt/probar-h002.sh
set -eu
[ "$(id -u)" = 0 ] || { echo "Ejecuta como root (sudo)."; exit 2; }
AQUI="$(cd "$(dirname "$0")" && pwd)"
command -v update-initramfs >/dev/null || { echo "Este sistema no usa initramfs-tools (¿pasó por nimbo-tpm-setup?)."; exit 1; }

install -D -m 0755 "$AQUI/h002-cryptsetup-envoltorio"   /usr/lib/nimbo/initramfs/cryptsetup-envoltorio
install -D -m 0755 "$AQUI/h002-nimbo-cryptsetup-honesto" /etc/initramfs-tools/hooks/nimbo-cryptsetup-honesto
install -D -m 0755 "$AQUI/h002-nimbo-aviso-ram"          /etc/initramfs-tools/scripts/local-top/nimbo-aviso-ram

update-initramfs -u -k "$(uname -r)"

IMG="/boot/initrd.img-$(uname -r)"
lista=$(lsinitramfs "$IMG")
fallos=0
for f in usr/sbin/cryptsetup.real scripts/local-top/nimbo-aviso-ram; do
    if printf '%s\n' "$lista" | grep -qE "(^|/)${f#usr/}\$"; then echo "   OK  el initrd contiene $f"; else echo "   FALTA en el initrd: $f"; fallos=1; fi
done
# El orden real de local-top: nimbo-aviso-ram debe ir ANTES de cryptroot.
d=$(mktemp -d); trap 'rm -rf "$d"' EXIT
(cd "$d" && unmkinitramfs "$IMG" . >/dev/null 2>&1) || true
orden=$(find "$d" -path '*scripts/local-top/ORDER' | head -1)
if [ -n "$orden" ]; then
    echo "   ORDER de local-top:"; grep -o 'local-top/[^ ]*' "$orden" | sed 's/^/      /'
    a=$(grep -n 'nimbo-aviso-ram' "$orden" | cut -d: -f1); c=$(grep -n 'local-top/cryptroot ' "$orden" | cut -d: -f1)
    if [ -n "$a" ] && [ -n "$c" ] && [ "$a" -lt "$c" ]; then echo "   OK  nimbo-aviso-ram corre antes que cryptroot"; else echo "   FALLO: orden incorrecto"; fallos=1; fi
fi
[ "$fallos" = 0 ] && echo ">> H-002 instalado. Apaga la VM (sin reiniciar) y avisa: las mediciones las corre el arnés." || { echo ">> Algo falló: no apagues, avisa con esta salida."; exit 1; }
