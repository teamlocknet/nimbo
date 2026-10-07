#!/bin/sh
# verificar-instalado.sh — evidencia del sistema INSTALADO (Paso 3C.1, ADR-006).
#
# Se ejecuta DENTRO del sistema instalado, como root. NO va en la ISO: install-in-qemu.sh
# lo entrega al guest por un disco auxiliar de solo lectura. Imprime por pantalla y, si
# existe, también por la consola serie (/dev/ttyS0), que el arnés guarda en el host.
#
#   sudo mount -o ro /dev/vdb1 /mnt && sudo sh /mnt/verificar-instalado.sh
#   sudo mount -o ro /dev/vdb1 /mnt && sudo sh /mnt/verificar-instalado.sh --sin-cifrar
#
# --sin-cifrar: para la instalación hecha con el lanzador "avanzado". Salta SOLO los
# chequeos de LUKS (y comprueba que, en efecto, no hay cifrado); D14, hermetismo,
# limpieza del instalador, fuentes APT y paquetes se exigen igual.
#
# Cada comprobación imprime OK / FALLO; el resumen final da el veredicto.
set -u

SALIDA=/dev/null
[ -w /dev/ttyS0 ] && SALIDA=/dev/ttyS0
fallos=0
p()  { printf '%s\n' "$*"; printf '%s\r\n' "$*" > "$SALIDA" 2>/dev/null || true; }
ok() { p "  OK     $*"; }
ko() { p "  FALLO  $*"; fallos=$((fallos+1)); }
sec(){ p ""; p "== $* =="; }

[ "$(id -u)" = 0 ] || { echo "Ejecuta como root (sudo)."; exit 2; }
SIN_CIFRAR=0
[ "${1:-}" = "--sin-cifrar" ] && SIN_CIFRAR=1
p "NIMBO_VERIF_BEGIN"
[ "$SIN_CIFRAR" = 1 ] && p "MODO: instalación SIN cifrar (lanzador avanzado)" || p "MODO: instalación CIFRADA (lanzador recomendado)"

if [ "$SIN_CIFRAR" = 1 ]; then
sec "1. Sin cifrado (modo declarado): coherencia"
if grep -v '^[[:space:]]*#' /etc/crypttab 2>/dev/null | grep -q '[^[:space:]]'; then ko "/etc/crypttab tiene entradas en una instalación declarada sin cifrar"; else ok "/etc/crypttab sin entradas"; fi
if findmnt -no SOURCE / | grep -q '^/dev/mapper/'; then ko "/ está sobre un mapper: $(findmnt -no SOURCE /)"; else ok "/ directamente sobre $(findmnt -no SOURCE /) ($(findmnt -no FSTYPE /))"; fi
if blkid -t TYPE=crypto_LUKS -o device 2>/dev/null | grep -q .; then ko "hay volúmenes LUKS en el disco: $(blkid -t TYPE=crypto_LUKS -o device | tr '\n' ' ')"; else ok "ningún volumen LUKS en el disco"; fi
dpkg-query -W -f='${db:Status-Status}' cryptsetup-initramfs 2>/dev/null | grep -q '^installed$' && ko "cryptsetup-initramfs instalado sin haber LUKS" || ok "cryptsetup-initramfs no instalado (no hace falta)"
p "  INFO   /boot: $(findmnt -no SOURCE /boot 2>/dev/null) · firmware: $([ -d /sys/firmware/efi ] && echo UEFI || echo BIOS)"

sec "2. Initramfs"
for img in /boot/initrd.img-*; do
    [ -e "$img" ] || { ko "no hay initrd en /boot"; break; }
    lsinitramfs "$img" 2>/dev/null | grep -q 'scripts/live' && ko "$img aún contiene scripts de live-boot" || ok "$img sin scripts de live-boot"
done
else
sec "1. Cifrado: crypttab + LUKS2 argon2id"
linea=$(grep -v '^[[:space:]]*#' /etc/crypttab 2>/dev/null | grep -v '^[[:space:]]*$' | head -1)
if [ -z "$linea" ]; then
    ko "/etc/crypttab no tiene entradas (¿se instaló SIN cifrado?)"
else
    p "  crypttab: $linea"
    uuid=$(printf '%s\n' "$linea" | awk '{print $2}' | sed 's/^UUID=//')
    dev=$(blkid -U "$uuid" 2>/dev/null || true)
    if [ -z "$dev" ]; then ko "el UUID de crypttab ($uuid) no corresponde a ningún dispositivo"
    else
        ok "crypttab apunta a $dev (UUID $uuid)"
        dump=$(cryptsetup luksDump "$dev" 2>&1)
        ver=$(printf '%s\n' "$dump" | awk '/^Version:/{print $2; exit}')
        [ "$ver" = 2 ] && ok "cryptsetup luksDump: Version 2 (LUKS2)" || ko "LUKS versión '$ver' (se esperaba 2)"
        pb=$(printf '%s\n' "$dump" | awk '/PBKDF:/{print $2}' | sort -u | tr '\n' ' ')
        case "$pb" in *argon2id*) ok "PBKDF de los keyslots: $pb" ;; *) ko "PBKDF: '$pb' (se esperaba argon2id)" ;; esac
        printf '%s\n' "$dump" | grep -E '^(Version|UUID|Keyslots|Tokens)|PBKDF|Cipher:' | sed 's/^/    /' | while read -r l; do p "    $l"; done
    fi
    clave=$(printf '%s\n' "$linea" | awk '{print $3}')
    [ "$clave" = none ] && ok "crypttab sin keyfile (clave: none -> pide contraseña)" || ko "crypttab usa keyfile: $clave"
fi
if findmnt -no SOURCE / | grep -q '^/dev/mapper/'; then ok "/ está sobre $(findmnt -no SOURCE /)"; else ko "/ NO está sobre un mapper: $(findmnt -no SOURCE /)"; fi
bootsrc=$(findmnt -no SOURCE /boot 2>/dev/null || true)
case "$bootsrc" in ""|/dev/mapper/*) ko "/boot no es una partición en claro separada: '$bootsrc'" ;; *) ok "/boot en claro, separado: $bootsrc ($(findmnt -no FSTYPE /boot))" ;; esac
[ -d /sys/firmware/efi ] && ok "arrancado por UEFI; ESP: $(findmnt -no SOURCE /boot/efi 2>/dev/null)" || p "  INFO   arrancado por BIOS legacy"

sec "2. Initramfs: cryptsetup + cryptroot"
for img in /boot/initrd.img-*; do
    [ -e "$img" ] || { ko "no hay initrd en /boot"; break; }
    cont=$(lsinitramfs "$img" 2>/dev/null)
    printf '%s\n' "$cont" | grep -q 'sbin/cryptsetup$' && ok "$img contiene sbin/cryptsetup" || ko "$img SIN cryptsetup"
    printf '%s\n' "$cont" | grep -q 'scripts/local-top/cryptroot$' && ok "$img contiene scripts/local-top/cryptroot" || ko "$img SIN cryptroot"
    printf '%s\n' "$cont" | grep -q -E 'etc/console-setup/(cached_.*\.kmap|tmpkbd\.)|etc/boottime\.kmap' && ok "$img lleva el teclado de consola (keymap de console-setup)" || ko "$img SIN keymap: la contraseña LUKS se teclearía en distribución US"
    printf '%s\n' "$cont" | grep -q 'scripts/live' && ko "$img aún contiene scripts de live-boot" || ok "$img sin scripts de live-boot"
done

fi
p "  teclado configurado: $(grep -E '^XKB(LAYOUT|VARIANT)=' /etc/default/keyboard 2>/dev/null | tr '\n' ' ')"

sec "3. D14: sin autologin"
if grep -rqs '^[[:space:]]*autologin-user' /etc/lightdm; then ko "lightdm tiene autologin: $(grep -rs '^[[:space:]]*autologin-user' /etc/lightdm | head -2)"; else ok "ningún autologin-user en /etc/lightdm"; fi
getent group autologin >/dev/null && ko "existe el grupo autologin" || ok "no existe el grupo autologin"

sec "4. Hermetismo 3B.1"
for u in apt-daily.timer apt-daily-upgrade.timer apt-daily.service apt-daily-upgrade.service; do
    [ "$(systemctl is-enabled "$u" 2>/dev/null)" = masked ] && ok "$u masked" || ko "$u NO masked ($(systemctl is-enabled "$u" 2>&1))"
done
[ -f /etc/apt/apt.conf.d/99nimbo-no-telemetry ] && ok "99nimbo-no-telemetry presente" || ko "falta 99nimbo-no-telemetry"
esc=$(ss -Htuln 2>/dev/null | awk '{print $1, $5}' | grep -v -E ' (127\.|\[::1\]|%lo)' || true)
[ -z "$esc" ] && ok "ningún listener TCP/UDP fuera de loopback" || p "  INFO   listeners no-loopback (revisar; DHCP cliente udp/68 es local): $(echo "$esc" | tr '\n' ';')"

sec "5. Sin instalador, sin live, sin backports"
bpo=$(dpkg-query -W -f='${Package} ${Version}\n' | grep '~bpo' || true)
[ -z "$bpo" ] && ok "ningún paquete ~bpo instalado" || ko "paquetes de backports: $bpo"
for pk in calamares polkitd rsync squashfs-tools live-boot live-boot-initramfs-tools live-config live-config-systemd user-setup; do
    dpkg-query -W -f='${db:Status-Status}' "$pk" 2>/dev/null | grep -q '^installed$' && ko "sigue instalado: $pk" || ok "no instalado: $pk"
done
for f in /etc/calamares /etc/calamares-sincifrar /usr/lib/nimbo/calamares /usr/bin/nimbo-instalar /usr/share/applications/nimbo-instalar.desktop /usr/share/applications/nimbo-instalar-sincifrar.desktop /lib/live/config /usr/lib/x86_64-linux-gnu/calamares /usr/share/calamares; do
    [ -e "$f" ] && ko "queda en disco: $f" || ok "no existe: $f"
done
ls /home/*/Desktop/nimbo-instalar*.desktop >/dev/null 2>&1 && ko "hay lanzador del instalador en un escritorio" || ok "ningún lanzador del instalador en /home"
p "  sources APT activas:"
grep -rhs '^[[:space:]]*deb' /etc/apt/sources.list /etc/apt/sources.list.d 2>/dev/null | while read -r l; do p "    $l"; done
if grep -rhs '^[[:space:]]*deb' /etc/apt/sources.list /etc/apt/sources.list.d 2>/dev/null | grep -v '^deb \[trusted=yes\] file:/usr/share/nimbo/pool \./$' | grep -q .; then ko "hay fuentes APT distintas del pool local"; else ok "única fuente APT: el pool local"; fi
grep -rqs backports /etc/apt && ko "referencia a backports en /etc/apt" || ok "ninguna referencia a backports en /etc/apt"
if apt-get --simulate --no-install-recommends install dracut tpm2-tools libtss2-esys-3.0.2-0 libtss2-mu0 libtss2-rc0 libtss2-tcti-device0 libtss2-tctildr0 >/dev/null 2>&1; then ok "dracut + tpm2-tools + libtss2 instalables SIN RED desde el pool (simulado)"; else ko "dracut/tpm2-tools NO instalables desde el pool"; fi

sec "6. RAM idle del sistema instalado"
p "  (used = MemTotal - MemAvailable, la misma fórmula que measure-ram-in-qemu.sh)"
p "  uptime: $(cut -d' ' -f1 /proc/uptime) s — para una cifra comparable, medir con >= 90 s de reposo"
mt=$(awk '/^MemTotal:/{print $2}' /proc/meminfo); ma=$(awk '/^MemAvailable:/{print $2}' /proc/meminfo)
p "  MemTotal ${mt} kB · MemAvailable ${ma} kB · USED (idle) $(( (mt-ma)/1024 )) MiB"

sec "7. Lista de paquetes del sistema instalado"
p "NIMBO_PKGS_BEGIN"
dpkg-query -W -f='${Package}\t${Version}\n' | LC_ALL=C sort | while read -r l; do p "$l"; done
p "NIMBO_PKGS_END"

p ""
if [ "$fallos" = 0 ]; then p "VEREDICTO: OK — 0 fallos"; else p "VEREDICTO: $fallos FALLO(S)"; fi
p "NIMBO_VERIF_END"
[ "$fallos" = 0 ]
