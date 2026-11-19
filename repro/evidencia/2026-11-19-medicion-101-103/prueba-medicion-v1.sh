#!/usr/bin/env bash
# prueba-medicion-v1.sh — mide en el sistema instalado lo que falta de #101 y #103 (19-nov).
#   A. #103: instalar un lote firmado no saca "N: Download is performed unsandboxed".
#   B. #101, cierre NORMAL: con el modo Tor activo y tráfico por SOCKS, se para tor con SIGTERM
#      (cierra sus conexiones como siempre); el contador "fugas" no debe subir. Prueba negativa:
#      una conexión directa de nobody TIENE que contar.
# En la VM:  sudo bash /mnt/lotes/pruebas/prueba-medicion-v1.sh
set -uo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Ejecuta con sudo"; exit 2; }
LOTES=$(dirname "$(dirname "$(readlink -f "$0")")")
contador() { nft list counter inet nimbo_tor fugas 2>/dev/null | sed -n 's/.*packets \([0-9]*\).*/\1/p'; }
trap 'nimbo-tor off >/dev/null 2>&1 || true' EXIT

echo "== A. #103: instalar un lote firmado =="
dpkg -r nimbo-rnf03-prueba >/dev/null 2>&1 || true
salida=$(nimbo-update-offline instalar "$LOTES/20-firmado-release" 2>&1); rc=$?
printf '%s\n' "$salida" | tail -4
if [ $rc -eq 0 ] && dpkg -s nimbo-rnf03-prueba >/dev/null 2>&1 && ! printf '%s' "$salida" | grep -q '^N: .*unsandboxed'; then
  echo "A: VERDE — instalado y sin la nota N: de apt"
else
  echo "A: ROJO — rc=$rc; nota N: $(printf '%s' "$salida" | grep -c 'unsandboxed')"
fi

echo
echo "== B. #101: cierre normal de las conexiones de tor =="
ip route | grep -q '^default' || nimbo-red on || exit 1
desde=$(date '+%F %T')
nimbo-tor on >/dev/null || { echo "nimbo-tor on falló"; exit 1; }
for _ in $(seq 180); do
  journalctl -u tor@default --since "$desde" -o cat | grep -q 'Bootstrapped 100' && break
  sleep 1
done
sleep 5
# Tráfico real por el SOCKS de tor (DNS remoto), como el navegador.
python3 - <<'EOF'
import socket, struct
ok = 0
for _ in range(5):
    try:
        s = socket.create_connection(("127.0.0.1", 9050), timeout=60)
        s.sendall(b"\x05\x01\x00"); s.recv(2)
        h = b"example.com"
        s.sendall(b"\x05\x01\x00\x03" + bytes([len(h)]) + h + struct.pack(">H", 80))
        if s.recv(10)[1] == 0:
            s.sendall(b"HEAD / HTTP/1.0\r\nHost: example.com\r\n\r\n")
            ok += s.recv(64).startswith(b"HTTP/")
        s.close()
    except OSError:
        pass
print(f"peticiones por Tor con respuesta: {ok}/5")
EOF
antes=$(contador)
reles=$(ss -Htnp state established 2>/dev/null | grep -c '"tor"')
echo "conexiones de tor con relés: $reles · fugas antes de parar tor: $antes"
marca=$(date '+%F %T')
systemctl stop tor@default.service
sleep 30
despues=$(contador)
echo "fugas 30 s después de parar tor (SIGTERM): $despues (+$((despues - antes)))"
journalctl -k --since "$marca" -o cat | grep 'nimbo-fuga' | tail -5 | cut -c1-160
runuser -u nobody -- python3 -c \
  "import socket; socket.create_connection(('1.1.1.1', 443), timeout=3)" >/dev/null 2>&1
sleep 2
negativa=$(contador)
echo "PRUEBA NEGATIVA: fugas tras una conexión directa de nobody: $negativa (+$((negativa - despues)))"
if [ "$despues" -eq "$antes" ] && [ "$negativa" -gt "$despues" ]; then
  echo "B: VERDE — el cierre normal no cuenta; la fuga real sí"
else
  echo "B: ROJO o NO CONCLUYENTE"
fi
