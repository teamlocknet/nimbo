#!/usr/bin/env bash
# test-arnes-sin-red.sh — con NIMBO_SIN_RED=1 la VM del arnés no tiene tarjeta de red.
#
# Por qué existe (16-nov): RNF-03 pide que "la instalación completa y el uso de cada módulo
# funcionen en una máquina virtual sin red". La prueba de hermetismo deja una tarjeta con
# red disponible (para ver que no se usa); esta prueba quita la tarjeta (`-nic none`), así
# que nada puede depender de la red ni por error. Además, `arrancar` lleva al disco de
# herramientas el script de la prueba (rnf03-en-vm.sh) y, con NIMBO_LOTES=<dir>, los lotes de
# nimbo-update-offline.
#
# Cómo prueba: carga lib-qemu.sh y llama a nimbo_red_args. No arranca ninguna VM.
#
# Uso: ./iso/live-build/tests/test-arnes-sin-red.sh   (sale con 0 solo si pasa)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$HERE/.."

fallos=0
ok()    { echo "  ok    $*"; }
falla() { echo "  FALLA $*"; fallos=$((fallos + 1)); }

# shellcheck source=../lib-qemu.sh
. "$SRC/lib-qemu.sh"

args() { (unset NIMBO_SIN_RED NIMBO_PCAP; for kv in "$@"; do export "${kv?}"; done
          nimbo_red_args 2>&1 | tr '\n' ' ') || true; }

echo "== nimbo_red_args"
if ! declare -F nimbo_red_args >/dev/null; then
    falla "lib-qemu.sh no define nimbo_red_args"
else
    a="$(args)"
    [[ "$a" == "-nic user,model=virtio-net-pci " ]] && ok "por defecto: red user-mode (sin cambios)" || falla "por defecto: '$a'"

    a="$(args NIMBO_SIN_RED=1)"
    [[ "$a" == "-nic none " ]] && ok "NIMBO_SIN_RED=1: -nic none (sin tarjeta)" || falla "NIMBO_SIN_RED=1: '$a'"

    a="$(args NIMBO_PCAP=/tmp/x.pcap)"
    [[ "$a" == *"filter-dump"*"file=/tmp/x.pcap"* ]] && ok "NIMBO_PCAP: captura (sin cambios)" || falla "NIMBO_PCAP: '$a'"

    a="$(args NIMBO_SIN_RED=1 NIMBO_PCAP=/tmp/x.pcap)"
    [[ "$a" == *ERROR* ]] && ok "NIMBO_SIN_RED con NIMBO_PCAP → ERROR (no hay tráfico que capturar)" \
        || falla "acepta NIMBO_SIN_RED con NIMBO_PCAP: '$a'"

    a="$(args NIMBO_SIN_RED=si)"
    [[ "$a" == *ERROR* ]] && ok "NIMBO_SIN_RED distinto de 1 → ERROR" || falla "acepta NIMBO_SIN_RED=si: '$a'"
fi

echo "== install-in-qemu.sh"
grep -q 'nimbo_red_args' "$SRC/install-in-qemu.sh" \
    && ok "usa nimbo_red_args" || falla "no usa nimbo_red_args"
! grep -q 'RED_ARGS=(-nic user' "$SRC/install-in-qemu.sh" \
    && ok "sin la red fijada a mano" || falla "install-in-qemu.sh sigue fijando la red a mano"
grep -q 'rnf03-en-vm.sh' "$SRC/install-in-qemu.sh" \
    && ok "arrancar lleva rnf03-en-vm.sh al disco de herramientas" || falla "no lleva rnf03-en-vm.sh"
grep -q 'NIMBO_LOTES' "$SRC/install-in-qemu.sh" \
    && ok "arrancar admite NIMBO_LOTES" || falla "no admite NIMBO_LOTES"
[ -f "$SRC/rnf03-en-vm.sh" ] && sh -n "$SRC/rnf03-en-vm.sh" \
    && ok "rnf03-en-vm.sh existe y es sh válido" || falla "falta rnf03-en-vm.sh o no es sh válido"

echo
if [ "$fallos" -ne 0 ]; then echo "RESULTADO: $fallos comprobaciones fallaron"; exit 1; fi
echo "RESULTADO: OK"
