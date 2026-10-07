#!/usr/bin/env bash
# install-in-qemu.sh — arnés HOST-SIDE de instalación (Paso 3C.1, ADR-006).
#
# NO se hornea en la ISO. Levanta una VM UEFI (OVMF) con un disco qcow2 vacío para que
# la instalación se haga CON LOS OJOS, y después arranca el disco instalado.
#
#   ./install-in-qemu.sh instalar [ISO]   # arranca la ISO live con el disco destino vacío
#   ./install-in-qemu.sh arrancar         # arranca el disco YA instalado (pide la clave LUKS)
#   ./install-in-qemu.sh informe          # extrae del log serie el informe de verificación
#   ./install-in-qemu.sh limpiar          # borra disco, NVRAM y logs del arnés
#
# QUÉ DEJA (todo regenerable, ignorado por git):
#   nimbo-install.qcow2        disco destino (20 GiB, crece bajo demanda)
#   nimbo-install-vars.fd      NVRAM de OVMF del guest (guarda la entrada de arranque UEFI)
#   install-serial.log         consola serie de la sesión live durante la instalación
#   installed-serial.log       consola serie del sistema instalado (aquí cae el informe)
#   installed-informe.txt      informe de verificar-instalado.sh, extraído del serie
#   installed-paquetes.txt     lista de paquetes del sistema instalado
#
# VERIFICACIÓN DEL INSTALADO: `arrancar` conecta un segundo disco de SOLO LECTURA con
# verificar-instalado.sh. Dentro del sistema instalado, en una terminal:
#       sudo mount -o ro /dev/vdb1 /mnt && sudo sh /mnt/verificar-instalado.sh
# El script escribe también por la consola serie; `informe` lo recoge en el host.
#
# Requisitos del host: qemu-system-x86_64, firmware OVMF (edk2-ovmf / ovmf) y KVM.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DISK="$HERE/nimbo-install.qcow2"
VARS="$HERE/nimbo-install-vars.fd"
LOG_LIVE="$HERE/install-serial.log"
LOG_INST="$HERE/installed-serial.log"
INFORME="$HERE/installed-informe.txt"
PAQUETES="$HERE/installed-paquetes.txt"
BASE="$HERE/paquetes-linea-base-3b1.txt"

DISK_GB="${NIMBO_DISK_GB:-20}"
VM_MB="${NIMBO_VM_MB:-4096}"
# RAM del sistema instalado: 2048 MiB, igual que measure-ram-in-qemu.sh, para que la
# cifra de RAM idle sea comparable con la de la sesión live.
VM_MB_INST="${NIMBO_VM_MB_INST:-2048}"
DISPLAY_OPT="${NIMBO_QEMU_DISPLAY:-gtk}"

# --- Firmware OVMF (rutas de Fedora y de Debian/Ubuntu) ----------------------------------
find_first() { for f in "$@"; do [ -r "$f" ] && { printf '%s\n' "$f"; return 0; }; done; return 1; }
OVMF_CODE="${OVMF_CODE:-$(find_first /usr/share/edk2/ovmf/OVMF_CODE.fd /usr/share/OVMF/OVMF_CODE_4M.fd /usr/share/OVMF/OVMF_CODE.fd || true)}"
OVMF_VARS_TPL="${OVMF_VARS:-$(find_first /usr/share/edk2/ovmf/OVMF_VARS.fd /usr/share/OVMF/OVMF_VARS_4M.fd /usr/share/OVMF/OVMF_VARS.fd || true)}"

need() { command -v "$1" >/dev/null || { echo "ERROR: falta '$1' en el host"; exit 1; }; }

qemu_base() {
    # $1 = RAM en MiB, $2 = fichero de log serie; el resto, argumentos extra de QEMU.
    local mem="$1" log="$2"; shift 2
    local kvm=()
    if [ -w /dev/kvm ]; then kvm=(-enable-kvm -cpu host); else echo ">> AVISO: sin KVM, irá muy lento"; fi
    : > "$log"
    qemu-system-x86_64 \
        "${kvm[@]}" \
        -machine q35 -m "$mem" -smp 2 \
        -drive if=pflash,format=raw,readonly=on,file="$OVMF_CODE" \
        -drive if=pflash,format=raw,file="$VARS" \
        -drive file="$DISK",if=virtio,format=qcow2 \
        -vga std -display "$DISPLAY_OPT" \
        -serial file:"$log" \
        -nic user,model=virtio-net-pci \
        "$@"
}

cmd_instalar() {
    local iso="${1:-$HERE/live-image-amd64.hybrid.iso}"
    need qemu-system-x86_64; need qemu-img
    [ -f "$iso" ] || { echo "ERROR: no existe la ISO: $iso"; exit 1; }
    [ -n "$OVMF_CODE" ] && [ -n "$OVMF_VARS_TPL" ] || { echo "ERROR: no encuentro OVMF (instala edk2-ovmf / ovmf, o exporta OVMF_CODE y OVMF_VARS)"; exit 1; }

    if [ -e "$DISK" ]; then
        echo "ERROR: ya existe $DISK (¿una instalación previa?)."
        echo "       Usa '$0 arrancar' para arrancarla, o '$0 limpiar' para empezar de cero."
        exit 1
    fi
    qemu-img create -f qcow2 "$DISK" "${DISK_GB}G" >/dev/null
    cp "$OVMF_VARS_TPL" "$VARS"

    echo ">> ISO    : $iso ($(du -h "$iso" | cut -f1)) sha256=$(sha256sum "$iso" | cut -c1-16)…"
    echo ">> Disco  : $DISK (${DISK_GB} GiB, vacío)"
    echo ">> OVMF   : $OVMF_CODE"
    echo ">> Serie  : $LOG_LIVE"
    echo
    echo "   EN LA VM: escritorio live -> icono 'Instalar nimbo' (o menú Aplicaciones > Sistema)."
    echo "   Deja MARCADA la casilla de cifrado y pon una contraseña que recuerdes."
    echo "   Al terminar, apaga la VM y ejecuta:  $0 arrancar"
    echo
    qemu_base "$VM_MB" "$LOG_LIVE" -cdrom "$iso" -boot menu=on
}

cmd_arrancar() {
    need qemu-system-x86_64
    [ -f "$DISK" ] && [ -f "$VARS" ] || { echo "ERROR: no hay instalación ($DISK). Ejecuta primero '$0 instalar'."; exit 1; }
    [ -n "$OVMF_CODE" ] || { echo "ERROR: no encuentro OVMF"; exit 1; }

    # Disco auxiliar de solo lectura con el verificador (vvfat: un directorio del host
    # servido como FAT). No toca ni la ISO ni el disco instalado.
    local tools; tools="$(mktemp -d "${TMPDIR:-/tmp}/nimbo-verif.XXXXXX")"
    trap 'rm -rf "$tools"' EXIT
    cp "$HERE/verificar-instalado.sh" "$tools/"
    [ -f "$BASE" ] && cp "$BASE" "$tools/"

    echo ">> Disco  : $DISK (sin ISO: arranca lo instalado)"
    echo ">> Serie  : $LOG_INST"
    echo
    echo "   CON LOS OJOS: debe pedir la CONTRASEÑA LUKS antes de arrancar, y llegar al"
    echo "   greeter de lightdm SIN entrar solo (D14). Luego, en una terminal del guest:"
    echo "       sudo mount -o ro /dev/vdb1 /mnt && sudo sh /mnt/verificar-instalado.sh"
    echo "   (para la RAM idle, espera ~90 s tras iniciar sesión antes de lanzarlo)."
    echo "   Al terminar, apaga la VM y ejecuta:  $0 informe"
    echo
    qemu_base "$VM_MB_INST" "$LOG_INST" \
        -drive file=fat:ro:"$tools",if=virtio,format=raw,readonly=on
}

cmd_informe() {
    [ -s "$LOG_INST" ] || { echo "ERROR: no hay log serie del instalado ($LOG_INST)."; exit 1; }
    tr -d '\r' < "$LOG_INST" | awk '/NIMBO_VERIF_BEGIN/{f=1} f{print} /NIMBO_VERIF_END/{f=0}' > "$INFORME"
    [ -s "$INFORME" ] || { echo "ERROR: el log serie no contiene el informe. ¿Se ejecutó verificar-instalado.sh como root?"; exit 1; }
    awk '/NIMBO_PKGS_BEGIN/{f=1;next} /NIMBO_PKGS_END/{f=0} f' "$INFORME" > "$PAQUETES"

    sed '/^== 7\./,$d' "$INFORME" | grep -v '^NIMBO_'
    echo
    echo "== Paquetes: instalado vs línea base 3B.1 =="
    echo "   instalado : $(wc -l < "$PAQUETES") paquetes"
    if [ -f "$BASE" ]; then
        # Nombres sin sufijo de arquitectura (":amd64") y orden de bytes en AMBAS listas.
        local b i; b="$(mktemp)"; i="$(mktemp)"
        grep -v '^#' "$BASE" | cut -f1 | sed 's/:.*//' | LC_ALL=C sort -u > "$b"
        cut -f1 "$PAQUETES" | sed 's/:.*//' | LC_ALL=C sort -u > "$i"
        echo "   base 3B.1 : $(wc -l < "$b") paquetes"
        echo "   -- en el instalado y NO en la base (deberían ser solo arranque/cifrado):"
        LC_ALL=C comm -23 "$i" "$b" | sed 's/^/      + /'
        echo "   -- en la base y NO en el instalado (deberían ser solo paquetes live):"
        LC_ALL=C comm -13 "$i" "$b" | sed 's/^/      - /'
        rm -f "$b" "$i"
    fi
    echo
    grep '^VEREDICTO' "$INFORME" || true
    echo ">> Informe completo: $INFORME"
    echo ">> Lista de paquetes: $PAQUETES"
}

cmd_limpiar() {
    rm -f "$DISK" "$VARS" "$LOG_LIVE" "$LOG_INST" "$INFORME" "$PAQUETES"
    echo ">> Arnés limpio."
}

case "${1:-}" in
    instalar) shift; cmd_instalar "$@" ;;
    arrancar) cmd_arrancar ;;
    informe)  cmd_informe ;;
    limpiar)  cmd_limpiar ;;
    *) sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 1 ;;
esac
