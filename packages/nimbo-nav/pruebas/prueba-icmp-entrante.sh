#!/usr/bin/env bash
# prueba-icmp-entrante.sh — ¿cuenta el vigilante como "fuga" el ICMP de error que manda el
# KERNEL en respuesta a tráfico que LLEGA de fuera? (observación de #84; medición del 18-nov)
#
# En #84, con el modo Tor activo, el otro par de WireGuard siguió mandando UDP/51820 y el kernel
# contestó "puerto inalcanzable" (ICMP 3/3). Esa conexión no la abrió tor: no lleva la marca
# 0x6e74 de #101: con esa tabla cuenta como fuga (ROJO, 18-nov). Con nimbo-nav 0.1.4-1, que
# acepta el ICMP de error en dirección de respuesta, debe dar VERDE.
#
# Sin segunda VM: un namespace "nimbo-par" unido por un par veth hace de otro par.
#   0. CONTROL sin modo Tor: el par manda UDP/51820 y TIENE que recibir el ICMP 3/3 (si no,
#      el kernel no lo genera y la prueba no dice nada).
#   1. Con el modo Tor activo, lo mismo: se mira el contador "fugas" y si el ICMP llegó al par.
# Al final borra el namespace y apaga el modo Tor. El veth es local: nada sale al cable.
#
# En la VM, como root:
#   sudo bash prueba-icmp-entrante.sh
set -uo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Ejecuta con sudo"; exit 2; }
NS=nimbo-par
YO=10.251.0.1
PAR=10.251.0.2

contador() { nft list counter inet nimbo_tor fugas 2>/dev/null | sed -n 's/.*packets \([0-9]*\).*/\1/p'; }

# El par manda 3 datagramas a YO:51820 (nadie escucha) y cuenta los ICMP 3/3 que recibe.
icmp_recibidos() {
  ip netns exec "$NS" python3 - "$YO" <<'EOF'
import socket, sys, time
r = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
r.settimeout(0.5)
u = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
for _ in range(3):
    u.sendto(b"nimbo", (sys.argv[1], 51820))
    time.sleep(1.1)  # el kernel limita los ICMP de error a ~1/s
n, fin = 0, time.time() + 2
while time.time() < fin:
    try:
        d = r.recv(2048)
    except socket.timeout:
        continue
    ihl = (d[0] & 0x0F) * 4
    if d[ihl] == 3 and d[ihl + 1] == 3:
        n += 1
print(n)
EOF
}

limpiar() {
  ip netns del "$NS" 2>/dev/null || true
  nimbo-tor off >/dev/null 2>&1 || true
}
trap limpiar EXIT

nimbo-tor off >/dev/null 2>&1 || true
ip netns del "$NS" 2>/dev/null || true
ip netns add "$NS"
ip link add nimbo-v0 type veth peer name nimbo-v1 netns "$NS"
ip addr add "$YO/30" dev nimbo-v0
ip link set nimbo-v0 up
ip netns exec "$NS" ip addr add "$PAR/30" dev nimbo-v1
ip netns exec "$NS" ip link set nimbo-v1 up
ip netns exec "$NS" ip link set lo up
sleep 1

control=$(icmp_recibidos)
echo "CONTROL (sin modo Tor): ICMP 3/3 recibidos por el par: $control"
[ "$control" -ge 1 ] || { echo "VEREDICTO: NO CONCLUYENTE — el kernel no generó el ICMP ni sin la tabla"; exit 1; }

ip route | grep -q '^default' || nimbo-red on || exit 1
nimbo-tor on >/dev/null || { echo "nimbo-tor on falló"; exit 1; }
sleep 3
nft list table inet nimbo_tor >/dev/null 2>&1 || { echo "La tabla nimbo_tor no está cargada"; exit 1; }
echo "Tabla: /usr/share/nimbo-nav/nimbo-tor.nft (sha256 $(sha256sum /usr/share/nimbo-nav/nimbo-tor.nft | cut -c1-16)…)"

antes=$(contador)
marca=$(date '+%F %T')
con_tor=$(icmp_recibidos)
sleep 1
despues=$(contador)
echo "Con modo Tor: ICMP 3/3 recibidos por el par: $con_tor · fugas: $antes -> $despues (+$((despues - antes)))"
echo "Líneas nimbo-fuga del kernel (últimas 5):"
journalctl -k --since "$marca" -o cat | grep 'nimbo-fuga' | tail -5 | cut -c1-160

if [ "$despues" -gt "$antes" ] && [ "$con_tor" -eq 0 ]; then
  echo "VEREDICTO: ROJO — el ICMP del kernel a tráfico entrante se descarta y CUENTA como fuga (falso positivo)"
elif [ "$despues" -eq "$antes" ] && [ "$con_tor" -ge 1 ]; then
  echo "VEREDICTO: VERDE — el ICMP sale y no cuenta como fuga"
else
  echo "VEREDICTO: NO CONCLUYENTE — contador +$((despues - antes)), ICMP recibidos $con_tor"
fi
