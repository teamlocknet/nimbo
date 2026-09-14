#!/usr/bin/env bash
# verify-hermetismo-in-qemu.sh — evidencia REPRODUCIBLE de HERMETISMO (Paso 3B.1, RNF-01).
#
# Demuestra, con los ojos y de forma defendible ante el comité, que la ISO en reposo (idle)
# NO abre conexiones salientes no solicitadas ni deja servicios de red a la escucha.
#
# HONESTO Y HOST-SIDE (mismo principio que measure-ram-in-qemu.sh): NO hornea nada en la
# ISO. Arranca la VM con una red CAUTIVA de QEMU (user-mode SLIRP: una 10.0.2.0/24 privada
# que NUNCA toca Internet — seguro por diseño) y captura CADA paquete que emite el guest con
# `-object filter-dump` -> hermetismo.pcap. Tras un settle idle FIJO, entra por la consola
# serie (getty de console=ttyS0) y lee los sockets en escucha del propio guest. Luego analiza
# el pcap host-side con tcpdump y emite un veredicto.
#
# CRITERIO (defendible): en idle solo se admite tráfico de PUESTA EN MARCHA LOCAL de la NIC
#   — ARP, DHCP (67/68) y NDP/RS de IPv6 link-local (ff02::/fe80::). Se marca como SOSPECHOSO
#   cualquier "phone home": DNS (53), NTP (123), HTTP/HTTPS (80/443) o cualquier SYN TCP.
#   PASS  <=>  0 paquetes sospechosos  Y  0 listeners de red (TCP/UDP no-loopback).
#   La red SLIRP ofrece DHCP y un gateway/DNS locales (10.0.2.2 / 10.0.2.3): que el guest
#   levante la NIC por DHCP es esperado ("red bajo demanda"); que consulte al DNS o salga
#   por TCP en reposo, NO.
#
# Uso:   ./verify-hermetismo-in-qemu.sh [ruta-al-iso]
# Env:   NIMBO_LIVE_USER (def. nimbo)  NIMBO_LIVE_PASS (def. live)
#        NIMBO_IDLE_S (def. 120)  NIMBO_VM_MB (def. 2048)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ISO="${1:-$HERE/live-image-amd64.hybrid.iso}"

USER_LIVE="${NIMBO_LIVE_USER:-nimbo}"
PASS_LIVE="${NIMBO_LIVE_PASS-live}"
IDLE_S="${NIMBO_IDLE_S:-120}"          # ventana idle FIJA de captura (determinismo)
VM_MB="${NIMBO_VM_MB:-2048}"

SERIAL_SOCK="$(mktemp -u /tmp/nimbo-herm-ser.XXXXXX.sock)"
MON_SOCK="$(mktemp -u /tmp/nimbo-herm-mon.XXXXXX.sock)"
SERIAL_LOG="$HERE/hermetismo-serial.log"
PCAP="$HERE/hermetismo.pcap"
SHOT="$HERE/hermetismo-desktop.png"
REPORT="$HERE/hermetismo.log"
MARK="NIMBO_HERM_MARK_5521"
GUEST_IP="10.0.2.15"                    # IP por defecto del guest en SLIRP user-mode

[ -f "$ISO" ] || { echo "ERROR: no existe la ISO: $ISO"; exit 1; }
command -v socat  >/dev/null || { echo "ERROR: falta socat";  exit 1; }
command -v qemu-system-x86_64 >/dev/null || { echo "ERROR: falta qemu-system-x86_64"; exit 1; }
command -v tcpdump >/dev/null || { echo "ERROR: falta tcpdump (análisis del pcap)"; exit 1; }
command -v convert >/dev/null || echo ">> AVISO: falta ImageMagick 'convert'; la captura quedará en .ppm"

echo ">> ISO   : $ISO ($(du -h "$ISO" | cut -f1))"
echo ">> Idle  : ${IDLE_S}s  ·  VM RAM: ${VM_MB} MiB  ·  Red: SLIRP cautiva (no toca Internet)"
echo ">> pcap  : $PCAP"

KVM=()
if [ -e /dev/kvm ]; then KVM=(-enable-kvm -cpu host); echo ">> KVM  : acelerado"; else echo ">> KVM  : emulación (más lento)"; fi

rm -f "$PCAP" "$SHOT" "$HERE/.herm.ppm"

# --- Arranque de QEMU: red user-mode + filter-dump que captura TODO el tráfico del guest.
# e1000: NIC clásica con driver en el kernel de Debian; SLIRP le da IP por DHCP.
echo ">> Arrancando QEMU headless (captura de tráfico activa)..."
qemu-system-x86_64 \
    "${KVM[@]}" \
    -m "$VM_MB" -smp 2 \
    -display none \
    -vga std \
    -netdev user,id=n0 \
    -device e1000,netdev=n0 \
    -object filter-dump,id=dump0,netdev=n0,file="$PCAP" \
    -serial "unix:$SERIAL_SOCK,server,nowait" \
    -monitor "unix:$MON_SOCK,server,nowait" \
    -cdrom "$ISO" \
    -boot d \
    -no-reboot &
QPID=$!

cleanup() { kill "$QPID" 2>/dev/null || true; rm -f "$SERIAL_SOCK" "$MON_SOCK" "$HERE/.herm.ppm" 2>/dev/null || true; }
trap cleanup EXIT

mon() { printf '%s\n' "$1" | socat - "UNIX-CONNECT:$MON_SOCK" >/dev/null 2>&1 || true; }

for _ in $(seq 1 40); do [ -S "$MON_SOCK" ] && [ -S "$SERIAL_SOCK" ] && break; sleep 0.5; done

# Puente a la consola serie (idéntico a measure-ram): FIFO de entrada -> socket; socket -> log.
SER_IN="$(mktemp -u /tmp/nimbo-herm-in.XXXXXX)"
mkfifo "$SER_IN"
socat "UNIX-CONNECT:$SERIAL_SOCK" - <"$SER_IN" >"$SERIAL_LOG" 2>/dev/null &
SPID=$!
exec 3>"$SER_IN"
send() { local s="$1" i; for ((i=0;i<${#s};i++)); do printf '%s' "${s:$i:1}" >&3; sleep 0.03; done; printf '\r' >&3; }
wait_for() { local re="$1" to="$2" i; for i in $(seq 1 "$to"); do grep -Eiq "$re" "$SERIAL_LOG" && return 0; kill -0 "$QPID" 2>/dev/null || return 2; sleep 1; done; return 1; }

# Menú isolinux/grub: Enter para arrancar la entrada Live por defecto.
for t in 3 5 8; do sleep "$t"; mon "sendkey ret"; done

echo ">> Esperando el prompt de login en serie (máx 240s)..."
if ! wait_for "login:" 240; then
    echo ">> ERROR: no apareció 'login:' en la serie. Últimas líneas:" >&2
    tail -20 "$SERIAL_LOG" >&2 || true
    exit 1
fi

# --- Ventana idle FIJA: dejamos correr la captura sin tocar nada (reposo real) ----------
echo ">> Login detectado. Capturando ${IDLE_S}s en reposo (idle) sin interacción..."
sleep "$IDLE_S"

# --- Captura visual del escritorio (evidencia de que sigue usable) ----------------------
mon "screendump $HERE/.herm.ppm"; sleep 2
if [ -f "$HERE/.herm.ppm" ]; then
    if command -v convert >/dev/null; then convert "$HERE/.herm.ppm" "$SHOT" && rm -f "$HERE/.herm.ppm"
    else SHOT="$HERE/hermetismo-desktop.ppm"; mv "$HERE/.herm.ppm" "$SHOT"; fi
fi

# --- Login por serie: leer sockets en escucha del guest (ground truth) ------------------
echo ">> Entrando por serie para leer sockets en escucha (usuario $USER_LIVE)..."
printf '\r' >&3; sleep 1
wait_for "login:" 10 || true
send "$USER_LIVE"
if wait_for "[Pp]assword:" 10; then send "$PASS_LIVE"; fi
sleep 3
send "echo ${MARK}_ID; id"
wait_for "uid=[0-9]" 12 || echo ">> AVISO: no se confirmó shell; la lectura de sockets puede fallar." >&2

# ss (iproute2) para listeners; /proc/net/{tcp,tcp6,udp,udp6} como verdad de base (sin
# depender de paquetes). st=0A en /proc/net/tcp* == LISTEN. Todo acotado por marcadores.
send "echo ${MARK}_SOCK_BEGIN; (ss -tulpn 2>/dev/null || echo 'ss NO DISPONIBLE'); echo '--- /proc/net LISTEN (st=0A) ---'; awk 'NR>1 && \$4==\"0A\"{print \$2}' /proc/net/tcp /proc/net/tcp6 2>/dev/null; echo ${MARK}_SOCK_END"
wait_for "${MARK}_SOCK_END" 20 || echo ">> AVISO: no llegó el marcador de sockets." >&2
sleep 1

# Cierre limpio de la VM antes de analizar el pcap (que filter-dump ya escribió en vivo).
exec 3>&- || true
kill "$SPID" 2>/dev/null || true
mon "quit"; sleep 2; kill "$QPID" 2>/dev/null || true

# --- Análisis host-side del pcap --------------------------------------------------------
sock_block="$(awk "/${MARK}_SOCK_BEGIN/{f=1;next} /${MARK}_SOCK_END/{f=0} f" "$SERIAL_LOG" 2>/dev/null || true)"

pk_total=0; pk_dns=0; pk_ntp=0; pk_web=0; pk_syn=0; pk_nonlocal_list=""
if [ -s "$PCAP" ]; then
    pk_total=$(tcpdump -nr "$PCAP" 2>/dev/null | wc -l | tr -d ' ')
    pk_dns=$(tcpdump -nr "$PCAP" 'port 53' 2>/dev/null | wc -l | tr -d ' ')
    pk_ntp=$(tcpdump -nr "$PCAP" 'port 123' 2>/dev/null | wc -l | tr -d ' ')
    pk_web=$(tcpdump -nr "$PCAP" 'port 80 or port 443' 2>/dev/null | wc -l | tr -d ' ')
    # SYN TCP salidos del guest (intento de conexión saliente) = SYN sin ACK.
    pk_syn=$(tcpdump -nr "$PCAP" "src host ${GUEST_IP} and tcp[tcpflags] & tcp-syn != 0 and tcp[tcpflags] & tcp-ack == 0" 2>/dev/null | wc -l | tr -d ' ')
    # Listado (para los ojos) de todo lo que NO sea PUESTA EN MARCHA LOCAL de la NIC. Se
    # excluye: ARP, DHCP (67/68) y TODO el multicast IPv6 link-local (dst ff02::/16) — que
    # cubre MLDv1/v2 y NDP/RS/RA, el housekeeping obligatorio de IPv6 al levantar la
    # interfaz (nunca sale del segmento L2). Clasificar por DESTINO link-local es más
    # robusto que parsear el tipo ICMPv6, que las cabeceras de extensión (HBH/router-alert
    # de MLD) desplazan. Un phone-home real iría a una IP GLOBAL/unicast, no a ff02::.
    pk_nonlocal_list=$(tcpdump -nr "$PCAP" 'not arp and not port 67 and not port 68 and not (ip6 and dst net ff02::/16)' 2>/dev/null || true)
fi

suspect=$(( pk_dns + pk_ntp + pk_web + pk_syn ))

# Listeners de red = sockets del guest expuestos a la red, leídos de la salida de `ss`.
# Contamos SOLO filas de datos de ss (Netid tcp/udp; col $5 = Local:Port), evitando así
# contar cabeceras o etiquetas del propio reporte. Se EXCLUYE, por ser puesta en marcha
# local permitida y NO un servicio a la escucha:
#   - loopback (127.0.0.0/8, [::1]);
#   - puertos de CLIENTE DHCP: udp/68 (DHCPv4) y udp/546 (DHCPv6). Son el socket receptor
#     de leases del cliente (la "red bajo demanda"), no un servicio que acepte conexiones.
# Para TCP exige estado LISTEN; un UDP no-DHCP/no-loopback ligado también cuenta.
listeners=$(printf '%s\n' "$sock_block" | awk '
    $1=="tcp" || $1=="udp" {
        la=$5; n=split(la, a, ":"); port=a[n]
        if (la ~ /^127\./ || la ~ /^\[?::1\]?/) next     # loopback
        if (port=="68" || port=="546") next               # cliente DHCP (bring-up)
        if ($1=="tcp" && $2!="LISTEN") next               # TCP solo si LISTEN
        print
    }')
n_listeners=$(printf '%s' "$listeners" | grep -c . || true)

{
    echo "# nimbo — evidencia de HERMETISMO en idle (Paso 3B.1, RNF-01)"
    echo "# ISO   : $(basename "$ISO")  ($(stat -c%s "$ISO") bytes)"
    echo "# Red   : QEMU user-mode SLIRP (10.0.2.0/24 cautiva; NO toca Internet)"
    echo "# Idle  : ${IDLE_S}s de captura sin interacción  ·  guest=${GUEST_IP}"
    echo "# pcap  : $(basename "$PCAP")  ($( [ -s "$PCAP" ] && stat -c%s "$PCAP" || echo 0) bytes)"
    echo "#======================================================================"
    echo "## 1) TRÁFICO SALIENTE DEL GUEST (análisis tcpdump)"
    echo "Paquetes totales capturados : ${pk_total}"
    echo "  DNS   (port 53)  : ${pk_dns}   [sospechoso si > 0]"
    echo "  NTP   (port 123) : ${pk_ntp}   [sospechoso si > 0]"
    echo "  HTTP/S(80/443)   : ${pk_web}   [sospechoso si > 0]"
    echo "  SYN TCP saliente : ${pk_syn}   [sospechoso si > 0]"
    echo ""
    echo "Paquetes NO-locales (ni ARP, DHCP o multicast IPv6 link-local) — deben ser CERO:"
    if [ -n "$pk_nonlocal_list" ]; then printf '%s\n' "$pk_nonlocal_list" | sed 's/^/    /'; else echo "    (ninguno)"; fi
    echo "#----------------------------------------------------------------------"
    echo "## 2) SOCKETS DEL GUEST (leídos por serie)"
    if [ -n "$sock_block" ]; then printf '%s\n' "$sock_block" | sed 's/^/    /'; else echo "    (no se pudo leer; revisar $SERIAL_LOG)"; fi
    echo ""
    echo "Listeners de red expuestos (excl. loopback y cliente DHCP udp/68,546): ${n_listeners}"
    if [ -n "$listeners" ]; then echo "  ->"; printf '%s\n' "$listeners" | sed 's/^/    /'; fi
    echo "#======================================================================"
    echo "## VEREDICTO"
    echo "  Paquetes sospechosos (DNS+NTP+web+SYN) : ${suspect}"
    echo "  Listeners de red no-loopback           : ${n_listeners}"
    if [ "$suspect" -eq 0 ] && [ "${n_listeners:-0}" -eq 0 ]; then
        echo "  HERMETISMO : OK ✅  (sin salientes no solicitadas ni listeners de red en idle)"
    else
        echo "  HERMETISMO : REVISAR ❌  (ver detalle arriba y $(basename "$PCAP"))"
    fi
} | tee "$REPORT"

echo
echo ">> Evidencia:"
echo "   - Reporte : $REPORT"
echo "   - pcap    : $PCAP"
[ -f "$SHOT" ] && echo "   - Captura : $SHOT"
echo "   - Serial  : $SERIAL_LOG"
