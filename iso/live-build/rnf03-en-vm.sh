#!/bin/sh
# rnf03-en-vm.sh — RNF-03 (operación sin conexión) y RF-UPD-01 dentro del sistema INSTALADO.
#
# NO se hornea en la ISO. Viaja en el disco de herramientas del arnés
# (`NIMBO_SIN_RED=1 install-in-qemu.sh arrancar`); dentro del guest, en una terminal:
#       sudo mount -o ro /dev/vdb1 /mnt && sudo sh /mnt/rnf03-en-vm.sh
#
# RNF-03: "la instalación completa y el uso de cada módulo funcionan en una máquina virtual
# sin red". La VM arranca SIN tarjeta de red (-nic none). Por módulo se comprueba un uso
# real que no necesita red, y que lo que sí la necesita (Tor, WireGuard, nimbo-red on)
# falla con un mensaje y sin traceback, en vez de colgarse.
#
# RF-UPD-01: "rechaza el 100 % de los paquetes con firma inválida". Si existe /mnt/lotes
# (NIMBO_LOTES, generado por preparar-lotes-rnf03.py), cada línea de /mnt/lotes/ESPERADO
# dice qué debe pasar con cada lote:
#     <lote> prueba   ACEPTADO|RECHAZADO    verificar --anillo /mnt/lotes/anillo-prueba.gpg
#     <lote> nimbo    ACEPTADO|RECHAZADO    verificar con el anillo de nimbo (el de la ISO)
#     <lote> instalar INSTALADO|RECHAZADO   sudo nimbo-update-offline instalar <lote>
#
# Salida por pantalla y por la consola serie (el arnés la guarda en el host), entre
# NIMBO_RNF03_BEGIN y NIMBO_RNF03_END. Ninguna comprobación imprime credenciales.
set -u

SALIDA=/dev/null
[ -w /dev/ttyS0 ] && SALIDA=/dev/ttyS0
fallos=0; total=0
p()  { printf '%s\n' "$*"; printf '%s\r\n' "$*" > "$SALIDA" 2>/dev/null || true; }
ok() { total=$((total+1)); p "  OK     $*"; }
ko() { total=$((total+1)); fallos=$((fallos+1)); p "  FALLO  $*"; }
sec(){ p ""; p "== $* =="; }

[ "$(id -u)" = 0 ] || { echo "Ejecuta como root (sudo)."; exit 2; }
USUARIO="${SUDO_USER:-}"
[ -n "$USUARIO" ] && [ "$USUARIO" != root ] || { echo "Ejecuta con sudo desde tu usuario (no como root directo)."; exit 2; }
DIR="$(dirname "$0")"
TRABAJO="$(mktemp -d /tmp/nimbo-rnf03.XXXXXX)"
chown "$USUARIO" "$TRABAJO"
trap 'rm -rf "$TRABAJO"' EXIT

# corre <segundos> <fichero-salida> <orden...>: ejecuta con límite de tiempo; deja la salida
# en el fichero y devuelve el código (124 = se colgó).
corre() { t="$1"; f="$2"; shift 2; timeout "$t" "$@" > "$f" 2>&1; }
# Las órdenes "como la persona" van con runuser escrito en la línea: timeout ejecuta
# programas, no funciones de shell (primera pasada, 16-nov).
HOGAR="$(getent passwd "$USUARIO" | cut -d: -f6)"
muestra() { sed -n '1,6p' "$1" | while IFS= read -r l; do p "         | $l"; done; }
limpio() { ! grep -q 'Traceback' "$1"; }

p "NIMBO_RNF03_BEGIN"
p "fecha: $(date -u +%Y-%m-%dT%H:%M:%SZ) · kernel: $(uname -r) · usuario: $USUARIO"

sec "1. Sin red"
ifaces="$(ip -o link show | awk -F': ' '{print $2}' | grep -v '^lo$' || true)"
if [ -z "$ifaces" ]; then ok "solo existe lo (la VM no tiene tarjeta de red)"
else ko "hay interfaces además de lo: $(echo "$ifaces" | tr '\n' ' ') (¿se arrancó sin NIMBO_SIN_RED=1?)"; fi
if ip route show default | grep -q .; then ko "hay ruta por defecto: $(ip route show default)"
else ok "sin ruta por defecto"; fi

sec "2. Módulos instalados (modulos.list)"
for m in $(grep -v '^#' /usr/share/nimbo/modulos.list | grep .); do
    if dpkg-query -W -f='${Status}' "$m" 2>/dev/null | grep -q 'install ok installed'; then
        ok "$m instalado ($(dpkg-query -W -f='${Version}' "$m"))"
    else ko "$m no está instalado"; fi
done

sec "3. nimbo-audit: init → capture → report → verify (como $USUARIO)"
f="$TRABAJO/audit.txt"
echo "evidencia de la prueba RNF-03" > "$TRABAJO/evidencia.txt"; chown "$USUARIO" "$TRABAJO/evidencia.txt"
caso="$TRABAJO/casos/rnf03"
mkdir "$TRABAJO/casos"; chown "$USUARIO" "$TRABAJO/casos"
if corre 60 "$f" runuser -u "$USUARIO" -- env HOME="$HOGAR" nimbo-audit init rnf03 --dir "$TRABAJO/casos" \
   && corre 60 "$f.c" runuser -u "$USUARIO" -- env HOME="$HOGAR" nimbo-audit capture "$TRABAJO/evidencia.txt" --dir "$caso" \
   && corre 60 "$f.r" runuser -u "$USUARIO" -- env HOME="$HOGAR" nimbo-audit report --dir "$caso" \
   && corre 60 "$f.v" runuser -u "$USUARIO" -- env HOME="$HOGAR" nimbo-audit verify "$caso"; then
    ok "ciclo completo sin red; salida de verify:"; muestra "$f.v"
else ko "el ciclo de nimbo-audit falló:"; for x in "$f" "$f.c" "$f.r" "$f.v"; do [ -f "$x" ] && muestra "$x"; done; fi

sec "4. nimbo-red (red a demanda)"
f="$TRABAJO/red.txt"
if corre 30 "$f" nimbo-red estado && limpio "$f"; then ok "estado responde: $(head -1 "$f")"
else ko "nimbo-red estado (código $?)"; muestra "$f"; fi
corre 60 "$f" nimbo-red on; c=$?
if [ "$c" -ne 0 ] && [ "$c" -ne 124 ] && limpio "$f"; then ok "on sin tarjeta falla con mensaje (código $c): $(head -1 "$f")"
else ko "nimbo-red on sin tarjeta: código $c"; muestra "$f"; fi

sec "5. nimbo-net (WireGuard)"
f="$TRABAJO/net.txt"
if corre 30 "$f" nimbo-net status && limpio "$f"; then ok "status responde: $(head -1 "$f")"
else ko "nimbo-net status (código $?)"; muestra "$f"; fi
[ -e /sys/class/net/wg-nimbo ] && ko "wg-nimbo existe sin haber hecho join" || ok "wg-nimbo no existe"

sec "6. nimbo-nav (Firefox endurecido y modo Tor)"
f="$TRABAJO/ff.txt"
corre 120 "$f" runuser -u "$USUARIO" -- env HOME="$HOGAR" firefox-esr --headless --screenshot "$TRABAJO/ff.png" "file:///usr/share/doc/firefox-esr/copyright"
if [ -s "$TRABAJO/ff.png" ]; then ok "Firefox abre un fichero local sin red (captura de $(stat -c %s "$TRABAJO/ff.png") bytes)"
else ko "Firefox no generó la captura"; muestra "$f"; fi
f="$TRABAJO/tor.txt"
if corre 30 "$f" nimbo-tor estado && limpio "$f"; then ok "nimbo-tor estado: $(head -1 "$f")"
else ko "nimbo-tor estado (código $?)"; muestra "$f"; fi
corre 180 "$f" nimbo-tor on; c=$?
if [ "$c" -eq 124 ]; then ko "nimbo-tor on se colgó sin red (más de 180 s)"
elif limpio "$f"; then ok "nimbo-tor on sin red termina (código $c): $(head -1 "$f")"
else ko "nimbo-tor on: traceback"; muestra "$f"; fi
corre 60 "$f" nimbo-tor off; c=$?
if nft list tables 2>/dev/null | grep -q nimbo_tor; then ko "tras off queda la tabla nimbo_tor"
else ok "tras off no queda la tabla nimbo_tor (off, código $c)"; fi
if systemctl is-active --quiet tor@default; then ko "tor@default sigue activo tras off"; else ok "tor@default inactivo tras off"; fi

sec "7. Hardening 3B.2"
f="$TRABAJO/hard.txt"
if corre 120 "$f" /usr/lib/nimbo/verify-hardening; then ok "verify-hardening: $(grep -h 'VEREDICTO' "$f" | head -1)"
else ko "verify-hardening (código $?)"; grep -h 'FALLO\|VEREDICTO' "$f" | while IFS= read -r l; do p "         | $l"; done; fi

sec "8. nimbo-update-offline (RF-UPD-01)"
ANILLO=/usr/share/nimbo/keyrings/nimbo-actualizaciones.gpg
if [ -s "$ANILLO" ]; then ok "anillo de nimbo presente ($ANILLO, sha256 $(sha256sum "$ANILLO" | cut -c1-16)…)"
else ko "falta el anillo de nimbo ($ANILLO): ningún lote, ni uno bien firmado, se podrá instalar"; fi
L="$DIR/lotes"
if [ ! -f "$L/ESPERADO" ]; then
    p "  (sin /mnt/lotes: arranca con NIMBO_LOTES=<dir> para probar los lotes)"
else
    invalidos=0; rechazados=0
    while read -r lote modo esperado; do
        case "$lote" in ''|'#'*) continue ;; esac
        f="$TRABAJO/upd.txt"
        case "$modo" in
            prueba)   corre 60 "$f" nimbo-update-offline verificar "$L/$lote" --anillo "$L/anillo-prueba.gpg" ;;
            nimbo)    corre 60 "$f" nimbo-update-offline verificar "$L/$lote" ;;
            instalar) corre 600 "$f" nimbo-update-offline instalar "$L/$lote" ;;
            *) ko "ESPERADO: modo desconocido '$modo'"; continue ;;
        esac
        c=$?
        if [ "$c" -eq 0 ]; then obtenido=ACEPTADO; [ "$modo" = instalar ] && obtenido=INSTALADO
        else obtenido=RECHAZADO; fi
        if [ "$esperado" = RECHAZADO ] && [ "$modo" != instalar ]; then
            invalidos=$((invalidos+1)); [ "$obtenido" = RECHAZADO ] && rechazados=$((rechazados+1))
        fi
        motivo="$(grep -h 'ACEPTADO\|RECHAZADO\|apt-get\|instalada' "$f" | head -1)"
        if [ "$obtenido" = "$esperado" ] && limpio "$f"; then ok "$lote [$modo] $obtenido — $motivo"
        else ko "$lote [$modo] esperado $esperado, obtenido $obtenido (código $c) — $motivo"; fi
    done < "$L/ESPERADO"
    p "  lotes inválidos rechazados: $rechazados de $invalidos"
fi

sec "Resumen"
p "VEREDICTO: $([ "$fallos" -eq 0 ] && echo OK || echo FALLA) — $fallos fallos de $total comprobaciones"
p "NIMBO_RNF03_END"
[ "$fallos" -eq 0 ]
