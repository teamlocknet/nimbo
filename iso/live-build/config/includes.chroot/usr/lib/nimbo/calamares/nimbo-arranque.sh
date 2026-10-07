#!/bin/sh
# nimbo-arranque.sh — Paso 3C.1 (ADR-006). Lo ejecuta Calamares (shellprocess) DENTRO del
# sistema destino, después de `fstab` y antes de `grubcfg`/`bootloader`.
#
# Instala SIN RED, desde el pool local /usr/share/nimbo/pool (viaja en el squashfs):
#   - GRUB + shim (UEFI) o grub-pc (BIOS legacy), según el firmware con que arrancó el live;
#   - cryptsetup-initramfs, solo si el instalador creó volúmenes LUKS (/etc/crypttab).
# De paso deja el sources.list DEFINITIVO del sistema instalado: solo el pool local.
set -eu

POOL=/usr/share/nimbo/pool
export DEBIAN_FRONTEND=noninteractive

[ -f "$POOL/Packages" ] || { echo "nimbo-arranque: falta $POOL/Packages" >&2; exit 1; }

# --- sources.list del sistema instalado: producto OFFLINE --------------------------------
# Sin mirrors remotos y sin backports. [trusted=yes]: fuente local sin red; su integridad
# la da el hash de la ISO de la que salió (ADR-006). Lo reemplazará el repo APT firmado.
cat > /etc/apt/sources.list <<'SOURCES'
# nimbo — sistema OFFLINE: sin mirrors remotos.
# Única fuente: el pool local que viaja con el sistema (GRUB, cryptsetup-initramfs y lo
# que necesita nimbo-tpm-setup). Las actualizaciones llegan con nimbo-update-offline,
# verificadas por GPG (RF-CORE-06).
deb [trusted=yes] file:/usr/share/nimbo/pool ./
SOURCES
rm -f /etc/apt/sources.list.d/*.list /etc/apt/sources.list.d/*.sources
rm -rf /var/lib/apt/lists/*
apt-get update

APT="apt-get --yes --no-install-recommends"

# --- initramfs capaz de pedir la contraseña LUKS ------------------------------------------
if grep -qs '^[^#[:space:]]' /etc/crypttab; then
    echo "nimbo-arranque: hay volúmenes LUKS -> instalando cryptsetup-initramfs"
    $APT install cryptsetup-initramfs
else
    echo "nimbo-arranque: instalación sin cifrado (crypttab vacío)"
fi

# --- gestor de arranque --------------------------------------------------------------------
if [ -d /sys/firmware/efi ]; then
    echo "nimbo-arranque: firmware UEFI -> grub-efi-amd64 + shim"
    $APT install grub-efi-amd64 grub-efi-amd64-signed shim-signed efibootmgr
else
    echo "nimbo-arranque: firmware BIOS -> grub-pc"
    $APT install grub-pc
fi
