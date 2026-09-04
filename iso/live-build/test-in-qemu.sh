#!/usr/bin/env bash
# test-in-qemu.sh — arranca la ISO en QEMU headless y captura evidencia de que
# llega a login. Doble evidencia:
#   - boot-serial.log   : consola serie (kernel + getty por console=ttyS0)
#   - boot-screenshot.png: captura de la pantalla VGA en el prompt de login
#
# El menú de isolinux espera una tecla (pinta sólo en VGA); por eso enviamos un
# Enter por el monitor de QEMU para arrancar la entrada por defecto (Live).
#
# Uso:   ./test-in-qemu.sh [ruta-al-iso]
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ISO="${1:-$HERE/live-image-amd64.hybrid.iso}"
LOG="$HERE/boot-serial.log"
SHOT="$HERE/boot-screenshot.png"
MON="$(mktemp -u /tmp/nimbo-qemu-mon.XXXXXX.sock)"
MAX_SEG=200

[ -f "$ISO" ] || { echo "ERROR: no existe la ISO: $ISO"; exit 1; }
command -v socat >/dev/null || { echo "ERROR: falta socat"; exit 1; }

echo ">> ISO : $ISO ($(du -h "$ISO" | cut -f1))"
: > "$LOG"; rm -f "$SHOT"

KVM=()
if [ -e /dev/kvm ]; then KVM=(-enable-kvm -cpu host); echo ">> KVM: acelerado"; else echo ">> KVM: emulación"; fi

mon() { printf '%s\n' "$1" | socat - "UNIX-CONNECT:$MON" >/dev/null 2>&1 || true; }

echo ">> Arrancando QEMU headless (serial -> boot-serial.log, monitor -> socket)..."
qemu-system-x86_64 \
    "${KVM[@]}" \
    -m 2048 -smp 2 \
    -display none \
    -vga std \
    -serial file:"$LOG" \
    -monitor "unix:$MON,server,nowait" \
    -cdrom "$ISO" \
    -boot d \
    -no-reboot &
QPID=$!
trap 'kill $QPID 2>/dev/null || true; rm -f "$MON"' EXIT

# Esperar a que el socket del monitor exista
for _ in $(seq 1 20); do [ -S "$MON" ] && break; sleep 0.5; done

# Enviar Enter al menú de isolinux (varias veces por si tarda en pintar)
for t in 3 6 10; do sleep "$t"; mon "sendkey ret"; done

echo ">> Esperando el prompt de login (máx ${MAX_SEG}s)..."
ok=0
for _ in $(seq 1 $((MAX_SEG/5))); do
    if grep -Eiq "login:" "$LOG"; then ok=1; break; fi
    kill -0 $QPID 2>/dev/null || break
    sleep 5
done

# Captura de pantalla VGA como evidencia visual (PPM -> PNG)
mon "screendump $HERE/.boot.ppm"
sleep 2
if [ -f "$HERE/.boot.ppm" ]; then convert "$HERE/.boot.ppm" "$SHOT" 2>/dev/null && rm -f "$HERE/.boot.ppm"; fi

mon "quit"; sleep 1; kill $QPID 2>/dev/null || true

echo
echo ">> Resultado:"
if [ "$ok" = 1 ]; then
    echo "   OK — la ISO arrancó y llegó a login."
    grep -Ei "Debian GNU/Linux|nimbo-live login:|login:" "$LOG" | tail -3
else
    echo "   AVISO — no se detectó 'login:' en el serial. Últimas líneas:"
    tail -15 "$LOG" || true
fi
[ -f "$SHOT" ] && echo "   Captura VGA: $SHOT"
