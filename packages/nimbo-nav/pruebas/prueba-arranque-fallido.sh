#!/usr/bin/env bash
# prueba-arranque-fallido.sh — el modo Tor falla cerrado y nimbo-tor dice la verdad
# (ADR-012; revisión de #59 y #64).
#
# Provoca a propósito que tor NO pueda arrancar (enmascara tor@default.service) y comprueba:
#   1. `nimbo-tor on` sale con error y no dice "ACTIVO".
#   2. La unidad nimbo-modo-tor queda "failed", pero ExecStopPost= ya borró la tabla
#      nftables "inet nimbo_tor": la red NO queda cerrada por un arranque a medias.
#   3. `nimbo-tor estado` dice que falló.
#   4. `nimbo-tor off` NO dice "red restaurada" (la unidad estaba en fallo) y la limpia.
#   5. Después, `nimbo-tor estado` dice inactivo.
# Al final deshace el enmascarado, pase lo que pase.
#
# Se ejecuta en la VM con nimbo-nav instalado, como root:
#   sudo bash packages/nimbo-nav/pruebas/prueba-arranque-fallido.sh
set -uo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Ejecuta con sudo"; exit 1; }
command -v nimbo-tor >/dev/null || { echo "Falta nimbo-nav (pruebas/preparar-vm.sh)"; exit 1; }

SALIDA="$PWD/nav-arranque-fallido"
mkdir -p "$SALIDA"
ok=1
paso() { printf '%-62s %s\n' "$1" "$2"; [ "$2" = "OK" ] || ok=0; }

limpiar() {
  systemctl unmask tor@default.service >/dev/null 2>&1 || true
  systemctl reset-failed nimbo-modo-tor.service >/dev/null 2>&1 || true
}
trap limpiar EXIT

systemctl stop nimbo-modo-tor.service >/dev/null 2>&1 || true
systemctl reset-failed nimbo-modo-tor.service >/dev/null 2>&1 || true
systemctl mask --runtime tor@default.service >/dev/null

{
  echo "# Modo Tor: arranque fallido provocado ($(date -Is))"
  echo
  echo "tor@default.service enmascarado a propósito: $(systemctl is-enabled tor@default.service 2>&1)"
  echo
  echo '```'
  echo '$ nimbo-tor on'
  nimbo-tor on; echo "(código $?)"
  echo
  echo '$ systemctl is-active nimbo-modo-tor.service'
  systemctl is-active nimbo-modo-tor.service
  echo
  echo '$ nft list table inet nimbo_tor'
  nft list table inet nimbo_tor 2>&1 | head -3; echo "(código ${PIPESTATUS[0]})"
  echo
  echo '$ nimbo-tor estado'
  nimbo-tor estado; echo "(código $?)"
  echo
  echo '$ nimbo-tor off'
  nimbo-tor off; echo "(código $?)"
  echo
  echo '$ nimbo-tor estado'
  nimbo-tor estado; echo "(código $?)"
  echo '```'
} > "$SALIDA/salida.txt" 2>&1

# Comprobaciones sobre la salida capturada
on=$(sed -n '/^\$ nimbo-tor on$/,/^(código/p' "$SALIDA/salida.txt")
estado1=$(sed -n '/^\$ systemctl is-active/{n;p}' "$SALIDA/salida.txt")
tabla=$(sed -n '/^\$ nft list table/,/^(código/p' "$SALIDA/salida.txt" | tail -1)
est=$(sed -n '/^\$ nimbo-tor estado$/,/^(código/p' "$SALIDA/salida.txt")
off=$(sed -n '/^\$ nimbo-tor off$/,/^(código/p' "$SALIDA/salida.txt")

grep -q '(código 0)' <<<"$on" && paso "1. nimbo-tor on falla" "MAL (salió con 0)" || \
  { grep -q 'ACTIVO' <<<"$on" && paso "1. nimbo-tor on falla" "MAL (dice ACTIVO)" || paso "1. nimbo-tor on falla y no dice ACTIVO" "OK"; }
[ "$estado1" = "failed" ] && paso "2a. la unidad queda en 'failed'" "OK" || paso "2a. la unidad queda en 'failed'" "MAL ($estado1)"
[ "$tabla" != "(código 0)" ] && paso "2b. ExecStopPost borró la tabla inet nimbo_tor" "OK" || paso "2b. ExecStopPost borró la tabla inet nimbo_tor" "MAL (sigue)"
grep -q 'falló' <<<"$(head -3 <<<"$est")" && paso "3. nimbo-tor estado dice que falló" "OK" || paso "3. nimbo-tor estado dice que falló" "MAL"
grep -q 'restaurada' <<<"$off" && paso "4. nimbo-tor off no dice 'red restaurada'" "MAL" || paso "4. nimbo-tor off no dice 'red restaurada'" "OK"
grep -q 'inactivo' <<<"$(tail -3 <<<"$est")" && paso "5. después, estado inactivo" "OK" || paso "5. después, estado inactivo" "MAL"

{
  cat "$SALIDA/salida.txt"
  echo
  if [ "$ok" -eq 1 ]; then echo "VEREDICTO: PASA — el arranque fallido deja la red como estaba y nimbo-tor dice la verdad"
  else echo "VEREDICTO: FALLA — revisar arriba"; fi
} > "$SALIDA/informe.md"
tail -1 "$SALIDA/informe.md"
[ "$ok" -eq 1 ]
