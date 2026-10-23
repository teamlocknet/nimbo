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
# DOS VARIANTES (ADR-006), cada una con su propio disco y sus logs, para tener las dos
# instalaciones a la vez. Antepón --sin-cifrar a cualquier orden para la segunda:
#   ./install-in-qemu.sh instalar              -> lanzador "Instalar nimbo (cifrado, recomendado)"
#   ./install-in-qemu.sh --sin-cifrar instalar -> lanzador "Instalar nimbo sin cifrar (avanzado)"
# Con --sin-cifrar los ficheros llevan el sufijo -sincifrar y el verificador se lanza con
# `--sin-cifrar` (salta solo los chequeos de LUKS).
#
# SECURE BOOT: antepón --secure-boot (combinable con --sin-cifrar, en cualquier orden):
#   ./install-in-qemu.sh --secure-boot instalar
# Arranca con OVMF Secure Boot + llaves de Microsoft (shim se valide de verdad) y SMM. El
# firmware es el de Debian bookworm, del snapshot anclado (ver lib-qemu.sh): HOST-SIDE,
# NO entra en la ISO ni es dependencia del producto. Ficheros con sufijo -sb, y el
# verificador se lanza con `--secure-boot` (exige SecureBoot=1 y SetupMode=0).
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
# Requisitos del host: qemu-system-x86_64 + qemu-img, firmware OVMF y KVM.
#   Arch/Omarchy : pacman -S qemu-desktop edk2-ovmf
#   Fedora       : dnf install qemu-kvm edk2-ovmf
#   Debian/Ubuntu: apt install qemu-system-x86 qemu-utils ovmf
# Con --secure-boot además: curl y bsdtar (libarchive) para traer el OVMF de Debian.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib-qemu.sh
. "$HERE/lib-qemu.sh"

SUF=""; VERIF_ARG=""; LANZADOR="Instalar nimbo (cifrado, recomendado)"; SB=0
while [ $# -gt 0 ]; do
    case "$1" in
        --sin-cifrar)
            SUF="$SUF-sincifrar"; VERIF_ARG="$VERIF_ARG --sin-cifrar"
            LANZADOR="Instalar nimbo sin cifrar (avanzado)"; shift ;;
        --secure-boot)
            SB=1; SUF="$SUF-sb"; VERIF_ARG="$VERIF_ARG --secure-boot"; shift ;;
        *) break ;;
    esac
done
DISK="$HERE/nimbo-install$SUF.qcow2"
VARS="$HERE/nimbo-install$SUF-vars.fd"
LOG_LIVE="$HERE/install$SUF-serial.log"
LOG_INST="$HERE/installed$SUF-serial.log"
INFORME="$HERE/installed$SUF-informe.txt"
PAQUETES="$HERE/installed$SUF-paquetes.txt"
YO="$0"
case "$SUF" in *-sincifrar*) YO="$YO --sin-cifrar" ;; esac
if [ "$SB" = 1 ]; then YO="$YO --secure-boot"; fi
BASE="$HERE/paquetes-linea-base-3b1.txt"

DISK_GB="${NIMBO_DISK_GB:-20}"
VM_MB="${NIMBO_VM_MB:-4096}"
# RAM del sistema instalado: 2048 MiB, igual que measure-ram-in-qemu.sh, para que la
# cifra de RAM idle sea comparable con la de la sesión live.
VM_MB_INST="${NIMBO_VM_MB_INST:-2048}"
DISPLAY_OPT="${NIMBO_QEMU_DISPLAY:-gtk}"

# --- Firmware OVMF (lib-qemu.sh: resuelto, nunca con ruta fija) ---------------------------
# Sin Secure Boot: el OVMF del host (descriptores de QEMU). Con Secure Boot: el par de
# Debian bookworm del snapshot, con SHA-256 fijado. La máquina con Secure Boot necesita
# SMM y la flash de variables marcada como segura, o el firmware se niega a arrancar.
OVMF_CODE_ENV="${OVMF_CODE:-}"; OVMF_CODE=""; OVMF_VARS_TPL=""; OVMF_ORIGEN=""
MACHINE=(-machine q35)
ovmf_preparar() {
    if [ "$SB" = 1 ]; then
        nimbo_ovmf_secboot || exit 1
        MACHINE=(-machine q35,smm=on -global driver=cfi.pflash01,property=secure,value=on)
    else
        OVMF_CODE="$OVMF_CODE_ENV"
        nimbo_ovmf_resolver || { echo "ERROR: no encuentro OVMF (instala edk2-ovmf / ovmf, o exporta OVMF_CODE y OVMF_VARS)"; exit 1; }
    fi
}

need() { command -v "$1" >/dev/null || { echo "ERROR: falta '$1' en el host (ver Requisitos en la cabecera)"; exit 1; }; }

qemu_base() {
    # $1 = RAM en MiB, $2 = fichero de log serie; el resto, argumentos extra de QEMU.
    local mem="$1" log="$2"; shift 2
    local kvm=()
    if [ -w /dev/kvm ]; then kvm=(-enable-kvm -cpu host); else echo ">> AVISO: sin KVM, irá muy lento"; fi
    : > "$log"
    qemu-system-x86_64 \
        "${kvm[@]}" \
        "${MACHINE[@]}" -m "$mem" -smp 2 \
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
    ovmf_preparar

    if [ -e "$DISK" ]; then
        echo "ERROR: ya existe $DISK (¿una instalación previa?)."
        echo "       Usa '$YO arrancar' para arrancarla, o '$YO limpiar' para empezar de cero."
        exit 1
    fi
    qemu-img create -f qcow2 "$DISK" "${DISK_GB}G" >/dev/null
    cp "$OVMF_VARS_TPL" "$VARS"

    echo ">> ISO    : $iso ($(du -h "$iso" | cut -f1)) sha256=$(sha256sum "$iso" | cut -c1-16)…"
    echo ">> Disco  : $DISK (${DISK_GB} GiB, vacío)"
    echo ">> OVMF   : $OVMF_CODE"
    echo ">> Origen : $OVMF_ORIGEN"
    echo ">> Secure Boot: $([ "$SB" = 1 ] && echo 'ACTIVO (llaves MS inscritas, SMM)' || echo 'apagado')"
    echo ">> Serie  : $LOG_LIVE"
    echo
    echo "   EN LA VM: escritorio live -> icono '$LANZADOR'"
    echo "   (o menú Aplicaciones > Sistema)."
    if [ -z "$SUF" ]; then
        echo "   El cifrado es obligatorio en este lanzador: pon una contraseña LUKS que recuerdes."
    else
        echo "   En este lanzador NO debe aparecer la casilla de cifrado."
    fi
    echo "   Al terminar, apaga la VM y ejecuta:  $YO arrancar"
    echo
    qemu_base "$VM_MB" "$LOG_LIVE" -cdrom "$iso" -boot menu=on
}

cmd_arrancar() {
    need qemu-system-x86_64
    [ -f "$DISK" ] && [ -f "$VARS" ] || { echo "ERROR: no hay instalación ($DISK). Ejecuta primero '$YO instalar'."; exit 1; }
    ovmf_preparar

    # Disco auxiliar de solo lectura con el verificador (vvfat: un directorio del host
    # servido como FAT). No toca ni la ISO ni el disco instalado.
    local tools; tools="$(mktemp -d "${TMPDIR:-/tmp}/nimbo-verif.XXXXXX")"
    trap 'rm -rf "$tools"' EXIT
    cp "$HERE/verificar-instalado.sh" "$tools/"
    [ -f "$BASE" ] && cp "$BASE" "$tools/"

    echo ">> Disco  : $DISK (sin ISO: arranca lo instalado)"
    echo ">> Secure Boot: $([ "$SB" = 1 ] && echo 'ACTIVO' || echo 'apagado')  ·  OVMF: $OVMF_ORIGEN"
    echo ">> Serie  : $LOG_INST"
    echo
    if [ -z "$SUF" ]; then
        echo "   CON LOS OJOS: debe pedir la CONTRASEÑA LUKS antes de arrancar, y llegar al"
    else
        echo "   CON LOS OJOS: NO debe pedir contraseña de disco, y debe llegar al"
    fi
    echo "   greeter de lightdm SIN entrar solo (D14). Luego, en una terminal del guest:"
    echo "       sudo mount -o ro /dev/vdb1 /mnt && sudo sh /mnt/verificar-instalado.sh$VERIF_ARG"
    echo "   (para la RAM idle, espera ~90 s tras iniciar sesión antes de lanzarlo)."
    echo "   Al terminar, apaga la VM y ejecuta:  $YO informe"
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
        echo "   -- en el instalado y NO en la base (deberían ser solo arranque/cifrado/teclado):"
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
    *) sed -n '2,26p' "$0" | sed 's/^# \{0,1\}//'; exit 1 ;;
esac
