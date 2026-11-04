#!/bin/sh
# probar-tpm.sh — envoltorio de PRUEBA para nimbo-tpm-setup (Paso 4). Solo camino de prueba.
#
# NO va en la ISO ni forma parte del producto: install-in-qemu.sh lo entrega al guest por
# el disco auxiliar de solo lectura, junto a nimbo-tpm-setup. Existe porque desde la
# ventana de QEMU no se puede copiar texto: esto saca la salida y la evidencia por la
# consola serie (/dev/ttyS0), que el arnés guarda en un fichero del anfitrión, y
# `install-in-qemu.sh ... evidencia` la extrae. El nimbo-tpm-setup que se entrega no
# escribe en la consola serie ni en discos auxiliares; quien lo hace es este envoltorio.
#
# Dentro del sistema instalado, como root:
#   sudo mount -o ro /dev/vdb1 /mnt
#   sudo sh /mnt/probar-tpm.sh [argumentos de nimbo-tpm-setup]   # ejecuta + evidencia
#   sudo sh /mnt/probar-tpm.sh --solo-evidencia                    # p. ej. tras reiniciar
#   sudo sh /mnt/probar-tpm.sh --manipular-initrd    # V5: altera el initrd (guarda el original)
#   sudo sh /mnt/probar-tpm.sh --restaurar-initrd    # V6: vuelve al original
#   sudo sh /mnt/probar-tpm.sh --regenerar-initrd    # V6: actualización legítima (dracut -f)
#
# Lo que se teclea (contraseñas, PIN) NO pasa por aquí: lo leen nimbo-tpm-setup y
# systemd-cryptenroll de la terminal. Lo que SÍ queda en la consola serie es lo que se
# imprime, incluida la clave de recuperación que genera la fase 2: es una credencial del
# volumen de PRUEBA, creada por la prueba.
#
# REGLA DEL PROYECTO: ninguna credencial entra al repo, ni de prueba. El log serie y la
# evidencia extraída están en .gitignore; `install-in-qemu.sh … evidencia` genera además
# una copia -redactada (clave de recuperación sustituida), que es la ÚNICA que se puede
# versionar o mostrar en la sustentación.
set -u

[ "$(id -u)" = 0 ] || { echo "Ejecuta como root (sudo)."; exit 2; }
AQUI="$(cd "$(dirname "$0")" && pwd)"
SERIE=/dev/null
[ -w /dev/ttyS0 ] && SERIE=/dev/ttyS0
s() { printf '%s\r\n' "$*" > "$SERIE" 2>/dev/null || true; }
# Copia un fichero o la salida de un comando a la serie, línea a línea.
s_cmd() { s "\$ $*"; sh -c "$*" 2>&1 | while IFS= read -r l; do s "$l"; done; }

N="$(date -u +%Y%m%dT%H%M%SZ)"
rc="-"
# --- Acciones de PRUEBA sobre el initrd (V5/V6). Solo existen aquí, nunca en el producto. ---
IMG="/boot/initrd.img-$(uname -r)"
RESP_PRUEBA=/var/lib/nimbo-tpm-prueba
case "${1:-}" in
    --manipular-initrd)
        # V5: simula una manipulación de /boot (evil maid): añade al initrd un archivo cpio
        # extra (el kernel acepta initrds concatenados, así que arranca igual) → cambia el
        # contenido que GRUB mide en el PCR 9.
        mkdir -p "$RESP_PRUEBA"; [ -f "$RESP_PRUEBA/initrd.orig" ] || cp -p "$IMG" "$RESP_PRUEBA/initrd.orig"
        d=$(mktemp -d); mkdir -p "$d/etc"; echo "manipulado por probar-tpm.sh $N" > "$d/etc/nimbo-manipulado"
        (cd "$d" && echo etc/nimbo-manipulado | cpio -o -H newc 2>/dev/null) >> "$IMG"; rm -rf "$d"
        s "NIMBO_TPM_ACCION $N initrd manipulado: $(sha256sum "$IMG" | cut -c1-16) (original guardado)"
        echo ">> initrd manipulado. Reinicia: el TPM NO debe desbloquear; debe pedir contraseña."
        set -- --solo-evidencia ;;
    --restaurar-initrd)
        [ -f "$RESP_PRUEBA/initrd.orig" ] || { echo "No hay initrd original guardado."; exit 1; }
        cp -p "$RESP_PRUEBA/initrd.orig" "$IMG"
        s "NIMBO_TPM_ACCION $N initrd restaurado: $(sha256sum "$IMG" | cut -c1-16)"
        echo ">> initrd original restaurado. Reinicia: el TPM debe volver a desbloquear solo."
        set -- --solo-evidencia ;;
    --regenerar-initrd)
        # V6: actualización LEGÍTIMA simulada (como tras un update del kernel).
        dracut --force "$IMG" "$(uname -r)" >/dev/null 2>&1
        rm -f "$RESP_PRUEBA/initrd.orig"
        s "NIMBO_TPM_ACCION $N initrd regenerado con dracut: $(sha256sum "$IMG" | cut -c1-16)"
        echo ">> initrd regenerado. Reinicia: pedirá contraseña; ya dentro, --reseal."
        set -- --solo-evidencia ;;
esac
if [ "${1:-}" != "--solo-evidencia" ]; then
    s "NIMBO_TPM_RUN_BEGIN $N args: $*"
    # `script` (util-linux) da una terminal real: los prompts interactivos (contraseña,
    # confirmación de la clave de recuperación) funcionan igual que sin envoltorio, y la
    # sesión queda grabada para mandarla a la serie al terminar. -e conserva el código.
    TS=/tmp/nimbo-tpm-sesion.txt
    args=""; for a in "$@"; do args="$args '$a'"; done
    script -q -e -c "sh '$AQUI/nimbo-tpm-setup'$args" "$TS"
    rc=$?
    tr -d '\r' < "$TS" | while IFS= read -r l; do s "$l"; done
    s "NIMBO_TPM_RUN_END rc=$rc"
fi

echo
echo ">> Volcando evidencia a la consola serie…"
s "NIMBO_TPM_EVID_BEGIN $N rc=$rc"
s "== sistema"
s_cmd "uname -r; cat /proc/cmdline"
s_cmd 'f=/sys/firmware/efi/efivars; for v in SecureBoot SetupMode; do printf "%s=" $v; od -An -t u1 -j4 -N1 $f/$v-8be4df61-93ca-11d2-aa0d-00e098032b8c | tr -d " "; done'
s_cmd "cat /sys/class/tpm/tpm0/tpm_version_major 2>&1; ls -l /dev/tpm* 2>&1"
s "== nimbo-tpm-setup --estado"
s_cmd "sh '$AQUI/nimbo-tpm-setup' --estado"
s "== estado y log del script"
s_cmd "cat /var/lib/nimbo-tpm/estado 2>&1"
s_cmd "cat /var/lib/nimbo-tpm/nimbo-tpm-setup.log 2>&1"
s "== crypttab y dracut"
s_cmd "cat /etc/crypttab; cat /etc/dracut.conf.d/90-nimbo-tpm.conf 2>&1"
s "== LUKS (tokens y keyslots)"
s_cmd 'dev=$(blkid -t TYPE=crypto_LUKS -o device | head -1); echo "$dev"; cryptsetup luksDump "$dev" | grep -E "^(Version|Keyslots|Tokens)|^  [0-9]+: |tpm2-pcrs|tpm2-pin|systemd-tpm2|systemd-recovery|Keyslot:"'
s "== initrd del kernel en uso"
s_cmd 'img=/boot/initrd.img-$(uname -r); ls -l "$img"; sha256sum "$img"; if command -v lsinitrd >/dev/null; then lsinitrd "$img" | grep -E "systemd-cryptsetup$|token-systemd-tpm2|libtss2-esys|udev/console-setup$|etc/crypttab$|console-setup/|scripts/local-top/cryptroot" ; lsinitrd -f etc/crypttab "$img"; else lsinitramfs "$img" | grep -E "cryptroot|cryptsetup$|console-setup"; fi'
s "== paquetes de arranque"
s_cmd "dpkg-query -W -f='\${db:Status-Status} \${Package} \${Version}\n' dracut dracut-core initramfs-tools initramfs-tools-core cryptsetup-initramfs tpm2-tools 2>&1"
s "== este arranque: journal del INITRD completo (hasta el cambio de raíz)"
# Completo y sin filtrar: el orden entre console-setup (teclado) y el prompt de
# systemd-cryptsetup solo se ve con todas las líneas.
s_cmd "journalctl -b -o short-monotonic --no-pager 2>/dev/null | sed '/Switching root/q' | head -400"
s "== este arranque: cryptsetup / TPM después del cambio de raíz"
s_cmd "journalctl -b -o short-monotonic --no-pager 2>/dev/null | sed '1,/Switching root/d' | grep -iE 'cryptsetup|tpm2|tpm:|crypt|unlock|console-setup|setupcon' | head -60"
s "NIMBO_TPM_EVID_END $N"
echo ">> Hecho (rc del script: $rc). Apaga la VM y, en el anfitrión:"
echo "   ./install-in-qemu.sh --secure-boot --tpm evidencia"
