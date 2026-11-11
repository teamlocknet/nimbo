#!/usr/bin/env bash
# prueba-fugas-tor.sh — RF-NAV-02 / HU-08: navegación por Tor con detección de fugas.
#
#  1. sudo nimbo-tor on y espera a que tor complete el arranque (Bootstrapped 100%).
#  2. Captura la interfaz externa mientras firefox-esr (perfil Tor, sin cabeza) carga
#     varias páginas, y anota a qué relés está conectado tor.
#     PASA <=> 0 DNS y 0 paquetes que no sean de/hacia los relés de tor (CA-1, CA-2),
#              y nimbo-leakcheck sale con 0.
#  3. PRUEBA NEGATIVA (CA-3, rojo a propósito): curl directo, saltándose Tor.
#     PASA <=> nimbo-leakcheck detecta la fuga (sale con 1).
#  4. sudo nimbo-tor off (también si algo falla).
# Se ejecuta en la VM, como el usuario (pide sudo):
#   bash packages/nimbo-nav/pruebas/prueba-fugas-tor.sh
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/comun.sh"

IFACE="$(interfaz_externa)"
[ -n "$IFACE" ] || { echo "No hay ruta por defecto: la VM necesita red para esta prueba"; exit 1; }
SITIOS=(https://check.torproject.org/ https://example.com/ https://www.debian.org/)
SALIDA="$PWD/nav02-fugas"
mkdir -p "$SALIDA"
PCAP="$SALIDA/tor.pcap"
RELES="$SALIDA/reles.txt"
: > "$RELES"

sudo -v
VIGIA=""
TCPDUMP=""
limpiar() {
  [ -n "$VIGIA" ] && kill "$VIGIA" 2>/dev/null || true
  [ -n "$TCPDUMP" ] && sudo kill "$TCPDUMP" 2>/dev/null || true
  sudo nimbo-tor off >/dev/null 2>&1 || true
}
trap limpiar EXIT

sudo nimbo-tor on
echo ">> Esperando a que tor complete el arranque (máx. 180 s)..."
listo=0
for _ in $(seq 180); do
  if sudo journalctl -u tor@default.service --since "-5min" -o cat 2>/dev/null | grep -q 'Bootstrapped 100%'; then
    listo=1
    break
  fi
  sleep 1
done
[ "$listo" -eq 1 ] || { echo "tor no completó el arranque"; exit 1; }

sudo tcpdump -i "$IFACE" -nn -U -w "$PCAP" 2>/dev/null &
TCPDUMP=$!
(
  while :; do
    sudo ss -Htnp state established 2>/dev/null | grep '"tor"' | awk '{print $4}' >> "$RELES"
    sleep 1
  done
) &
VIGIA=$!
sleep 2

perfil=$(mktemp -d)
cp /usr/share/nimbo-nav/tor-user.js "$perfil/user.js"
for url in "${SITIOS[@]}"; do
  echo ">> Cargando por Tor: $url"
  nombre=$(echo "$url" | tr -c 'a-z0-9' '_')
  timeout 120 firefox-esr --headless --no-remote --profile "$perfil" \
    --screenshot "$SALIDA/$nombre.png" "$url" >/dev/null 2>&1 || true
done
rm -rf "$perfil"

sleep 2
kill "$VIGIA" 2>/dev/null || true
VIGIA=""
sudo kill "$TCPDUMP" 2>/dev/null || true
wait "$TCPDUMP" 2>/dev/null || true
TCPDUMP=""
sudo chown "$(id -u):$(id -g)" "$PCAP"

# IP de los relés de tor vistos (sin puerto; IPv6 sin corchetes)
sort -u "$RELES" | sed -E 's/^\[?([^]]*)\]?:[0-9]+$/\1/' | sort -u > "$SALIDA/reles-ip.txt"
FILTRO_RELES=$(sed 's/^/host /' "$SALIDA/reles-ip.txt" | paste -sd'|' | sed 's/|/ or /g')
PUESTA='arp or udp port 67 or udp port 68 or (icmp6 and (dst net ff02::/16 or dst net fe80::/10))'
if [ -n "$FILTRO_RELES" ]; then
  FUERA="not ($FILTRO_RELES) and not ($PUESTA)"
else
  FUERA="not ($PUESTA)"
fi

TOTAL=$(contar "$PCAP" "")
DNS=$(contar "$PCAP" "udp port 53 or tcp port 53")
FUERA_N=$(contar "$PCAP" "$FUERA")

set +e
sudo nimbo-leakcheck > "$SALIDA/leakcheck-limpio.txt"
RC_LIMPIO=$?
echo ">> PRUEBA NEGATIVA: curl directo, saltándose Tor (debe detectarse)"
curl -s -m 8 -o /dev/null https://example.com/
RC_CURL=$?
sudo nimbo-leakcheck > "$SALIDA/leakcheck-negativa.txt"
RC_NEG=$?
set -e

OK=1
[ "$DNS" -eq 0 ] || OK=0
[ "$FUERA_N" -eq 0 ] || OK=0
[ "$RC_LIMPIO" -eq 0 ] || OK=0
[ "$RC_NEG" -eq 1 ] || OK=0

{
  echo "# RF-NAV-02 — Navegación por Tor y detección de fugas"
  echo
  echo "- Fecha: $(date -Is) · Interfaz: $IFACE · tor $(dpkg-query -W -f='${Version}' tor) · firefox-esr $(dpkg-query -W -f='${Version}' firefox-esr)"
  echo "- Sitios cargados por el perfil Tor: ${SITIOS[*]} (capturas .png en esta carpeta)"
  echo "- Relés de tor vistos: $(wc -l < "$SALIDA/reles-ip.txt")"
  echo "- Paquetes capturados: $TOTAL · **DNS: $DNS** · **Fuera del túnel: $FUERA_N**"
  echo "- nimbo-leakcheck con Tor activo: código $RC_LIMPIO (esperado 0)"
  echo "- Prueba negativa: curl directo terminó con código $RC_CURL (esperado distinto de 0: la tabla lo bloquea); nimbo-leakcheck: código $RC_NEG (esperado 1)"
  echo
  echo "## Paquetes fuera del túnel (primeros 50)"
  echo '```'
  tcpdump -nn -r "$PCAP" "$FUERA" 2>/dev/null | head -50 || true  # con pipefail, head corta tcpdump (SIGPIPE): no debe abortar el informe
  echo '```'
  echo
  echo "## nimbo-leakcheck en la prueba negativa"
  echo '```'
  cat "$SALIDA/leakcheck-negativa.txt"
  echo '```'
  echo
  if [ "$OK" -eq 1 ]; then
    echo "VEREDICTO: PASA — 0 fugas con Tor y la fuga provocada se detecta"
  else
    echo "VEREDICTO: FALLA — revisar arriba"
  fi
} | tee "$SALIDA/informe.md"
[ "$OK" -eq 1 ]
