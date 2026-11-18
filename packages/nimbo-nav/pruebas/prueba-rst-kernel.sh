#!/usr/bin/env bash
# prueba-rst-kernel.sh — ¿cuenta el vigilante como "fuga" los paquetes que el KERNEL manda, sin
# proceso dueño, al cerrarse una conexión de tor? (ensayo de la demo, 18-nov; #101)
#
# Con la tabla indicada (por defecto, la instalada):
#   1. activa el modo Tor y espera a que tor complete el arranque;
#   2. mata tor de golpe: sus conexiones con los relés se cierran y lo que siga llegando lo
#      contesta el kernel (RST, ACK de TIME_WAIT), sin proceso dueño;
#   3. mira el contador "fugas" y las líneas "nimbo-fuga" del kernel;
#   4. PRUEBA NEGATIVA: una conexión directa de otro usuario (nobody) TIENE que contarse.
# Al final apaga el modo Tor y deja la tabla instalada como estaba.
#
# En la VM, como root:
#   sudo bash prueba-rst-kernel.sh                      # tabla instalada (rojo esperado)
#   sudo bash prueba-rst-kernel.sh nimbo-tor-nueva.nft  # tabla propuesta (verde esperado)
set -uo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Ejecuta con sudo"; exit 2; }
INSTALADA=/usr/share/nimbo-nav/nimbo-tor.nft
TABLA="${1:-$INSTALADA}"

contador() { nft list counter inet nimbo_tor fugas 2>/dev/null | sed -n 's/.*packets \([0-9]*\).*/\1/p'; }

nimbo-tor off >/dev/null 2>&1 || true
cp "$INSTALADA" /tmp/nimbo-tor.nft.instalada
restaurar() {
  nimbo-tor off >/dev/null 2>&1 || true
  cp /tmp/nimbo-tor.nft.instalada "$INSTALADA"
}
trap restaurar EXIT

if [ "$TABLA" != "$INSTALADA" ]; then
  nft -c -f "$TABLA" || { echo "La tabla no pasa 'nft -c'"; exit 1; }
  echo "nft -c: sintaxis OK"
  cp "$TABLA" "$INSTALADA"
fi
echo "Tabla: $TABLA (sha256 $(sha256sum "$INSTALADA" | cut -c1-16)…)"

ip route | grep -q '^default' || nimbo-red on || exit 1
desde=$(date '+%F %T')
nimbo-tor on >/dev/null || { echo "nimbo-tor on falló"; exit 1; }
for _ in $(seq 180); do
  journalctl -u tor@default --since "$desde" -o cat | grep -q 'Bootstrapped 100' && break
  sleep 1
done
sleep 10
antes=$(contador)
reles=$(ss -Htnp state established 2>/dev/null | grep -c '"tor"')
echo "tor arrancado: $reles conexiones con relés · fugas antes de matar tor: $antes"

marca=$(date '+%F %T')
systemctl kill -s KILL tor@default.service
sleep 30
despues=$(contador)
echo "fugas 30 s después de matar tor: $despues (+$((despues - antes)))"
echo "Líneas nimbo-fuga del kernel desde que se mató tor (últimas 5):"
journalctl -k --since "$marca" -o cat | grep 'nimbo-fuga' | tail -5 | cut -c1-160

runuser -u nobody -- python3 -c \
  "import socket; socket.create_connection(('1.1.1.1', 443), timeout=3)" >/dev/null 2>&1
sleep 2
negativa=$(contador)
echo "PRUEBA NEGATIVA: fugas tras una conexión directa de nobody: $negativa (+$((negativa - despues)))"

if [ "$despues" -eq "$antes" ] && [ "$negativa" -gt "$despues" ]; then
  echo "VEREDICTO: VERDE — los paquetes del kernel de tor no cuentan; la fuga real sí"
elif [ "$despues" -gt "$antes" ]; then
  echo "VEREDICTO: ROJO — el contador sube sin ninguna fuga (paquetes del kernel de tor)"
else
  echo "VEREDICTO: FALLA — la prueba negativa no se detectó"
fi
