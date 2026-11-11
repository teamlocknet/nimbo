#!/usr/bin/env bash
# prueba-reposo-navegador.sh — RF-NAV-01 / HU-07 CA-1: "el navegador no genera conexiones
# no solicitadas al abrirse en reposo".
#
# Abre firefox-esr con un perfil NUEVO en about:blank, no toca nada durante NIMBO_IDLE_S
# segundos (120 por defecto) y captura todo el tráfico de la interfaz externa.
#   PASA  <=>  0 paquetes sospechosos (criterio de hermetismo, ver comun.sh)
#
# Rojo primero: ejecútala ANTES de instalar nimbo-nav (Firefox de serie => conexiones) y
# DESPUÉS (=> 0). Se ejecuta en la sesión gráfica de la VM, como el usuario (pide sudo
# para tcpdump):
#   bash packages/nimbo-nav/pruebas/prueba-reposo-navegador.sh [etiqueta]
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$HERE/comun.sh"

if dpkg -s nimbo-nav >/dev/null 2>&1; then ETIQUETA_DEF=con-nimbo-nav; else ETIQUETA_DEF=sin-nimbo-nav; fi
ETIQUETA="${1:-$ETIQUETA_DEF}"
IDLE_S="${NIMBO_IDLE_S:-120}"
IFACE="$(interfaz_externa)"
[ -n "$IFACE" ] || { echo "No hay ruta por defecto: la VM necesita red para esta prueba"; exit 1; }
[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ] || { echo "Ejecuta en la sesión gráfica"; exit 1; }

SALIDA="$PWD/nav01-reposo-$ETIQUETA"
mkdir -p "$SALIDA"
PCAP="$SALIDA/reposo.pcap"
perfil=$(mktemp -d)

sudo -v
sudo tcpdump -i "$IFACE" -nn -U -w "$PCAP" 2>/dev/null &
TCPDUMP=$!
sleep 2
firefox-esr --no-remote --profile "$perfil" about:blank >/dev/null 2>&1 &
FF=$!
echo ">> Firefox abierto en reposo (${IDLE_S}s, perfil nuevo, interfaz $IFACE). No toques nada."
sleep "$IDLE_S"
kill "$FF" 2>/dev/null || true
wait "$FF" 2>/dev/null || true
sleep 1
sudo kill "$TCPDUMP" 2>/dev/null || true
wait "$TCPDUMP" 2>/dev/null || true
rm -rf "$perfil"
sudo chown "$(id -u):$(id -g)" "$PCAP"

TOTAL=$(contar "$PCAP" "")
SOSP=$(contar "$PCAP" "$SOSPECHOSO")
DNS=$(contar "$PCAP" "udp port 53 or tcp port 53")
{
  echo "# RF-NAV-01 — Firefox abierto en reposo ($ETIQUETA)"
  echo
  echo "- Fecha: $(date -Is) · Interfaz: $IFACE · Ventana: ${IDLE_S}s · firefox-esr $(dpkg-query -W -f='${Version}' firefox-esr)"
  echo "- MOZ_REMOTE_SETTINGS_DEVTOOLS=${MOZ_REMOTE_SETTINGS_DEVTOOLS:-<sin definir>} (nimbo-nav la define en la sesión gráfica)"
  echo "- Paquetes capturados: $TOTAL · **Sospechosos: $SOSP** (DNS: $DNS)"
  echo
  echo "## Sospechosos (primeros 50)"
  echo '```'
  tcpdump -nn -r "$PCAP" "$SOSPECHOSO" 2>/dev/null | head -50 || true  # con pipefail, head corta tcpdump (SIGPIPE): no debe abortar el informe
  echo '```'
  echo
  echo "## Nombres consultados por DNS"
  echo '```'
  tcpdump -nn -r "$PCAP" 'udp dst port 53' 2>/dev/null | grep -oE '(A|AAAA|HTTPS)\? [^ ]+' | sort | uniq -c | sort -rn || true
  echo '```'
  echo
  if [ "$SOSP" -eq 0 ]; then
    echo "VEREDICTO: PASA — 0 conexiones no solicitadas"
  else
    echo "VEREDICTO: FALLA — $SOSP paquetes sospechosos"
  fi
} | tee "$SALIDA/informe.md"
[ "$SOSP" -eq 0 ]
