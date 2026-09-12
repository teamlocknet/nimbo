#!/usr/bin/env bash
# measure-ram-in-qemu.sh — arranca la ISO con Xfce4 en QEMU headless, toma evidencia
# visual del escritorio y MIDE la RAM usada en reposo (idle), contra el techo de 500 MB
# (RNF-04 / Acta). Paso 3A.
#
# HONESTO Y HOST-SIDE: este arnés NO viaja en la ISO del producto. No hornea ningún
# servicio ni snippet de medición en la imagen. Todo lo que necesita lo hace DESDE EL
# HOST: arranca la VM, pinta el escritorio en la VGA emulada (aunque -display none),
# entra por la consola serie (getty que ya existe por console=ttyS0) y lee la memoria
# del propio guest. Mismo settle, misma RAM de VM, misma fórmula => reproducible.
#
# Evidencia que produce:
#   - ram-desktop.png   : screendump de la VGA con el escritorio Xfce4 (verificación
#                         con los ojos de que arranca a escritorio, no a consola).
#   - ram-idle.log      : salida cruda de /proc/meminfo + `free -m` del guest + el
#                         número calculado (used MiB) y el veredicto vs 500 MB.
#
# Fórmula (la misma que usa `free`): used = MemTotal - MemAvailable (kernel >= 3.14).
# MemAvailable es la estimación del kernel de cuánta RAM hay realmente disponible sin
# swap; Total - Available = huella real en reposo, independiente del tamaño de la VM.
#
# Uso:   ./measure-ram-in-qemu.sh [ruta-al-iso]
# Env:   NIMBO_LIVE_USER (def. nimbo)  NIMBO_LIVE_PASS (def. live, el de live-config)
#        NIMBO_RAM_CAP_MB (def. 500)   NIMBO_SETTLE_S (def. 90)  NIMBO_VM_MB (def. 2048)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ISO="${1:-$HERE/live-image-amd64.hybrid.iso}"

USER_LIVE="${NIMBO_LIVE_USER:-nimbo}"
PASS_LIVE="${NIMBO_LIVE_PASS-live}"   # contraseña por defecto de live-config (confirmada)
CAP_MB="${NIMBO_RAM_CAP_MB:-500}"
SETTLE_S="${NIMBO_SETTLE_S:-90}"        # tiempo FIJO de estabilización (determinismo)
VM_MB="${NIMBO_VM_MB:-2048}"            # RAM de la VM (fija; no afecta a used=Total-Avail)

SERIAL_SOCK="$(mktemp -u /tmp/nimbo-qemu-ser.XXXXXX.sock)"
MON_SOCK="$(mktemp -u /tmp/nimbo-qemu-mon.XXXXXX.sock)"
SERIAL_LOG="$HERE/ram-serial.log"      # serial crudo persistente (evidencia/depuración; *.log gitignored)
SHOT="$HERE/ram-desktop.png"
REPORT="$HERE/ram-idle.log"
MARK="NIMBO_RAM_MARK_8812"              # marcador único para acotar la salida del guest

[ -f "$ISO" ] || { echo "ERROR: no existe la ISO: $ISO"; exit 1; }
command -v socat  >/dev/null || { echo "ERROR: falta socat";  exit 1; }
command -v qemu-system-x86_64 >/dev/null || { echo "ERROR: falta qemu-system-x86_64"; exit 1; }
command -v convert >/dev/null || echo ">> AVISO: falta ImageMagick 'convert'; la captura quedará en .ppm"

echo ">> ISO   : $ISO ($(du -h "$ISO" | cut -f1))"
echo ">> Settle: ${SETTLE_S}s  ·  VM RAM: ${VM_MB} MiB  ·  Techo: ${CAP_MB} MB  ·  Usuario: $USER_LIVE"

KVM=()
if [ -e /dev/kvm ]; then KVM=(-enable-kvm -cpu host); echo ">> KVM  : acelerado"; else echo ">> KVM  : emulación (más lento)"; fi

# --- Arranque de QEMU: VGA std (para pintar y capturar Xfce) + serie por socket -----
echo ">> Arrancando QEMU headless..."
qemu-system-x86_64 \
    "${KVM[@]}" \
    -m "$VM_MB" -smp 2 \
    -display none \
    -vga std \
    -serial "unix:$SERIAL_SOCK,server,nowait" \
    -monitor "unix:$MON_SOCK,server,nowait" \
    -cdrom "$ISO" \
    -boot d \
    -no-reboot &
QPID=$!

cleanup() { kill "$QPID" 2>/dev/null || true; rm -f "$SERIAL_SOCK" "$MON_SOCK" "$HERE/.ram.ppm" 2>/dev/null || true; }
trap cleanup EXIT

mon() { printf '%s\n' "$1" | socat - "UNIX-CONNECT:$MON_SOCK" >/dev/null 2>&1 || true; }

# Esperar los sockets del monitor y de la serie
for _ in $(seq 1 40); do [ -S "$MON_SOCK" ] && [ -S "$SERIAL_SOCK" ] && break; sleep 0.5; done

# Puente bidireccional a la consola serie: un FIFO de entrada -> socket; socket -> log.
SER_IN="$(mktemp -u /tmp/nimbo-ser-in.XXXXXX)"
mkfifo "$SER_IN"
socat "UNIX-CONNECT:$SERIAL_SOCK" - <"$SER_IN" >"$SERIAL_LOG" 2>/dev/null &
SPID=$!
# Mantener el FIFO abierto para escritura durante toda la sesión (fd 3).
exec 3>"$SER_IN"
# Envío pausado carácter-a-carácter + CR: evita pérdidas/reordenación en la serie con
# el getty (115200 sin control de flujo). \r porque el getty/login espera CR (ICRNL).
send() { local s="$1" i; for ((i=0;i<${#s};i++)); do printf '%s' "${s:$i:1}" >&3; sleep 0.03; done; printf '\r' >&3; }
wait_for() {  # wait_for <regex> <timeout_s>
    local re="$1" to="$2" i
    for i in $(seq 1 "$to"); do
        grep -Eiq "$re" "$SERIAL_LOG" && return 0
        kill -0 "$QPID" 2>/dev/null || return 2
        sleep 1
    done
    return 1
}

# El menú de isolinux/grub pinta en VGA y espera tecla: enviamos Enter varias veces.
for t in 3 5 8; do sleep "$t"; mon "sendkey ret"; done

# --- Estabilización idle (tiempo FIJO desde que aparece el prompt de login) ---------
echo ">> Esperando el prompt de login en serie (máx 240s)..."
if ! wait_for "login:" 240; then
    echo ">> ERROR: no apareció 'login:' en la serie. Últimas líneas:" >&2
    tail -20 "$SERIAL_LOG" >&2 || true
    exit 1
fi
echo ">> Login detectado. Estabilizando ${SETTLE_S}s para medir en reposo..."
sleep "$SETTLE_S"

# --- Captura visual del escritorio Xfce (VGA) ---------------------------------------
echo ">> Capturando el escritorio (screendump VGA)..."
rm -f "$SHOT" "$HERE/.ram.ppm"
mon "screendump $HERE/.ram.ppm"
sleep 2
if [ -f "$HERE/.ram.ppm" ]; then
    if command -v convert >/dev/null; then convert "$HERE/.ram.ppm" "$SHOT" && rm -f "$HERE/.ram.ppm"
    else SHOT="$HERE/ram-desktop.ppm"; mv "$HERE/.ram.ppm" "$SHOT"; fi
fi

# --- Login por serie + lectura de memoria del guest ---------------------------------
echo ">> Entrando por la consola serie para leer la memoria (usuario $USER_LIVE)..."
printf '\r' >&3; sleep 1                       # limpia la línea del getty
wait_for "login:" 10 || true
send "$USER_LIVE"
if wait_for "[Pp]assword:" 10; then send "$PASS_LIVE"; fi
# Confirmar la SESIÓN con una sonda 'id' acotada (uid=): si el usuario no existiera o la
# contraseña fallara, saldría "Login incorrect" y no habría uid= → lo reportamos claro.
sleep 3
send "echo ${MARK}_ID; id"
if ! wait_for "uid=[0-9]" 12; then
    echo ">> ERROR: no se obtuvo shell (¿usuario '$USER_LIVE' inexistente o contraseña?)." >&2
    echo ">> Últimas líneas del serial:" >&2; tail -8 "$SERIAL_LOG" >&2 || true
fi

# Comando acotado por marcadores (LC_ALL=C para números estables; sin swap).
send "echo ${MARK}_BEGIN; cat /proc/meminfo | grep -E '^(MemTotal|MemAvailable|MemFree|Cached|Buffers):'; echo ---; free -m; echo ${MARK}_END"
wait_for "${MARK}_END" 20 || echo ">> AVISO: no llegó el marcador de fin; la salida puede estar incompleta." >&2
sleep 1

# --- Cálculo de used = MemTotal - MemAvailable (igual que `free`) --------------------
block="$(awk "/${MARK}_BEGIN/{f=1;next} /${MARK}_END/{f=0} f" "$SERIAL_LOG")"
memtotal_kb="$(printf '%s\n' "$block" | awk '/^MemTotal:/{print $2; exit}')"
memavail_kb="$(printf '%s\n' "$block" | awk '/^MemAvailable:/{print $2; exit}')"

{
    echo "# nimbo — medición de RAM idle con Xfce4 (Paso 3A)"
    echo "# ISO    : $(basename "$ISO")  ($(stat -c%s "$ISO") bytes)"
    echo "# VM     : ${VM_MB} MiB RAM, 2 vCPU  ·  settle=${SETTLE_S}s  ·  $( [ -e /dev/kvm ] && echo KVM || echo emulación )"
    echo "# Fórmula: used = MemTotal - MemAvailable (idéntica a \`free\`)"
    echo "#------------------------------------------------------------------"
    echo "$block"
    echo "#------------------------------------------------------------------"
    if [ -n "${memtotal_kb:-}" ] && [ -n "${memavail_kb:-}" ]; then
        used_kb=$(( memtotal_kb - memavail_kb ))
        used_mib=$(( used_kb / 1024 ))
        echo "MemTotal     : ${memtotal_kb} kB"
        echo "MemAvailable : ${memavail_kb} kB"
        echo "USED (idle)  : ${used_mib} MiB   [= (Total - Available)]"
        echo "TECHO        : ${CAP_MB} MB (RNF-04)"
        if [ "$used_mib" -lt "$CAP_MB" ]; then
            echo "VEREDICTO    : OK ✅  (${used_mib} MiB < ${CAP_MB} MB)"
        else
            echo "VEREDICTO    : EXCEDE ❌  (${used_mib} MiB >= ${CAP_MB} MB)"
        fi
    else
        echo "VEREDICTO    : ⚠️  no se pudo parsear meminfo (revisar el bloque de arriba y el raw serial)"
    fi
} | tee "$REPORT"

# Cierre limpio
exec 3>&- || true
kill "$SPID" 2>/dev/null || true
mon "quit"; sleep 1; kill "$QPID" 2>/dev/null || true

echo
echo ">> Evidencia:"
echo "   - Reporte RAM : $REPORT"
[ -f "$SHOT" ] && echo "   - Captura Xfce: $SHOT"
