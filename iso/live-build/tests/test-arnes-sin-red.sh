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

args() { (unset NIMBO_SIN_RED NIMBO_PCAP NIMBO_RED_ENLACE; for kv in "$@"; do export "${kv?}"; done
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

    # 24-nov: dos VMs en la misma red (nimbo-net entre A y B), con la topología del
    # laboratorio de #84: A lleva la red user-mode y un concentrador que escucha en
    # 127.0.0.1; B se conecta a él. Cada una con su MAC, o el DHCP las confunde.
    # 24-nov, primer ensayo: sin restrict=on, la red user-mode recibe copia del tráfico
    # entre A y B (el concentrador repite a todos), lo trata como salida a internet y
    # corta las conexiones TCP con un RST. Con restrict=on lo descarta (como en #84).
    a="$(args NIMBO_RED_ENLACE=escuchar:47000)"
    [[ "$a" == *"-netdev user,id=n0,restrict=on"* && "$a" == *"socket,id=cable,listen=127.0.0.1:47000"* \
       && "$a" == *"hubport,id=nic,hubid=0"* && "$a" == *"mac=52:54:00:11:00:01"* ]] \
        && ok "NIMBO_RED_ENLACE=escuchar: red user-mode aislada (restrict=on) + concentrador en 127.0.0.1" \
        || falla "NIMBO_RED_ENLACE=escuchar: '$a'"

    a="$(args NIMBO_RED_ENLACE=conectar:47000)"
    [[ "$a" == *"socket,id=cable,connect=127.0.0.1:47000"* && "$a" == *"mac=52:54:00:11:00:02"* \
       && "$a" != *"user"* ]] \
        && ok "NIMBO_RED_ENLACE=conectar: solo el cable hacia A, sin red propia" \
        || falla "NIMBO_RED_ENLACE=conectar: '$a'"

    for malo in escuchar conectar:80 conectar:99999 escuchar:abc otro:47000; do
        a="$(args NIMBO_RED_ENLACE=$malo)"
        [[ "$a" == *ERROR* ]] && ok "NIMBO_RED_ENLACE=$malo → ERROR" || falla "acepta NIMBO_RED_ENLACE=$malo: '$a'"
    done

    a="$(args NIMBO_RED_ENLACE=escuchar:47000 NIMBO_SIN_RED=1)"
    [[ "$a" == *ERROR* ]] && ok "NIMBO_RED_ENLACE con NIMBO_SIN_RED → ERROR" \
        || falla "acepta NIMBO_RED_ENLACE con NIMBO_SIN_RED: '$a'"

    a="$(args NIMBO_RED_ENLACE=escuchar:47000 NIMBO_PCAP=/tmp/x.pcap)"
    [[ "$a" == *ERROR* ]] && ok "NIMBO_RED_ENLACE con NIMBO_PCAP → ERROR" \
        || falla "acepta NIMBO_RED_ENLACE con NIMBO_PCAP: '$a'"
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
# 16-nov, primera pasada en la VM: `timeout` no puede ejecutar una FUNCIÓN de shell
# ("fallo al ejecutar la orden «como_usuario»") y nimbo-audit y Firefox no llegaron a probarse.
! grep -qE '^[^#]*corre [0-9]+ [^ ]+ como_usuario' "$SRC/rnf03-en-vm.sh" \
    && ok "rnf03-en-vm.sh no pasa funciones de shell a timeout" \
    || falla "rnf03-en-vm.sh pasa la función como_usuario a timeout (no se puede ejecutar)"
# 16-nov, Parte 2: en sh las variables de una función son globales; corre() hacía f="$2" y
# pisaba la f del llamador, así que la salida de nimbo-audit verify se buscaba en un fichero
# que no existía y salía vacía. Prueba de comportamiento: corre() no cambia f ni t.
if (
    corre=$(grep '^corre() {' "$SRC/rnf03-en-vm.sh")
    eval "$corre"
    f=llamador; t=llamador
    corre 5 /dev/null true
    [ "$f" = llamador ] && [ "$t" = llamador ]
); then ok "corre() no pisa las variables f y t del llamador"
else falla "corre() pisa f o t del llamador (la salida de verify salía vacía)"; fi

echo
if [ "$fallos" -ne 0 ]; then echo "RESULTADO: $fallos comprobaciones fallaron"; exit 1; fi
echo "RESULTADO: OK"
