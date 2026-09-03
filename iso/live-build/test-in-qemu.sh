#!/usr/bin/env bash
# test-in-qemu.sh — arranca la ISO en QEMU headless y captura evidencia de que
# llega a login (prompt por consola serial).
#
# Uso:   ./test-in-qemu.sh [ruta-al-iso]
# Salida: boot-serial.log (log de la consola serial, evidencia del arranque)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ISO="${1:-$HERE/live-image-amd64.hybrid.iso}"
LOG="$HERE/boot-serial.log"
MAX_SEG=240

[ -f "$ISO" ] || { echo "ERROR: no existe la ISO: $ISO"; exit 1; }

echo ">> ISO : $ISO ($(du -h "$ISO" | cut -f1))"
: > "$LOG"

KVM=()
if [ -e /dev/kvm ]; then KVM=(-enable-kvm -cpu host); echo ">> KVM: acelerado"; else echo ">> KVM: no disponible (emulación)"; fi

echo ">> Arrancando QEMU headless (serial -> $LOG). Máx ${MAX_SEG}s..."
timeout "$MAX_SEG" qemu-system-x86_64 \
    "${KVM[@]}" \
    -m 2048 -smp 2 \
    -display none \
    -serial file:"$LOG" \
    -cdrom "$ISO" \
    -boot once=d \
    -no-reboot || true

echo
echo ">> Resultado:"
if grep -Eiq "login:" "$LOG"; then
    echo "   OK — la ISO arrancó y llegó a login."
    grep -Ei "Debian GNU/Linux|nimbo-live login:|login:" "$LOG" | tail -3
    exit 0
else
    echo "   AVISO — no se encontró prompt de login en $LOG."
    echo "   Últimas líneas del log:"
    tail -15 "$LOG" || true
    exit 1
fi
