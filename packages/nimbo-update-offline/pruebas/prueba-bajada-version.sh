#!/usr/bin/env bash
# prueba-bajada-version.sh — ¿un lote VIEJO bien firmado puede bajar de versión un paquete?
# (ADR-013, límite de v1; revisión de #64).
#
# nimbo-update-offline instala con `apt-get install --no-download -y <debs>`. Esta prueba usa
# exactamente esas opciones con dos paquetes de juguete (nimbo-prueba-bajada 2.0 y 1.0):
#   1. instala la 2.0;
#   2. intenta instalar la 1.0 con las mismas opciones -> se espera que apt SE NIEGUE
#      (sin --allow-downgrades) y que la 2.0 siga instalada.
# Al final purga el paquete de juguete. Necesita root; no necesita red.
#   sudo bash packages/nimbo-update-offline/pruebas/prueba-bajada-version.sh
set -uo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Ejecuta con sudo"; exit 1; }

PAQ=nimbo-prueba-bajada
SALIDA="$PWD/upd-bajada-version"
mkdir -p "$SALIDA"
trabajo=$(mktemp -d)
trap 'apt-get purge -y -qq "$PAQ" >/dev/null 2>&1 || true; rm -rf "$trabajo"' EXIT

construir() {  # construir <versión>
  local d="$trabajo/$PAQ-$1"
  mkdir -p "$d/DEBIAN" "$d/usr/share/doc/$PAQ"
  printf 'Package: %s\nVersion: %s\nArchitecture: all\nMaintainer: nimbo <prueba@invalid>\nDescription: paquete de juguete para la prueba de bajada de versión\n' \
    "$PAQ" "$1" > "$d/DEBIAN/control"
  echo "versión $1" > "$d/usr/share/doc/$PAQ/VERSION"
  dpkg-deb --build --root-owner-group "$d" "$trabajo/${PAQ}_$1_all.deb" >/dev/null
}
construir 2.0
construir 1.0

{
  echo "# Bajada de versión con las opciones de nimbo-update-offline ($(date -Is))"
  echo
  echo '```'
  echo "\$ apt-get install --no-download -y ./${PAQ}_2.0_all.deb"
  apt-get install --no-download -y "$trabajo/${PAQ}_2.0_all.deb" 2>&1 | tail -2; echo "(código ${PIPESTATUS[0]})"
  echo
  echo "\$ apt-get install --no-download -y ./${PAQ}_1.0_all.deb   # lote VIEJO"
  apt-get install --no-download -y "$trabajo/${PAQ}_1.0_all.deb" 2>&1 | tail -4; echo "(código ${PIPESTATUS[0]})"
  echo
  echo "\$ dpkg-query -W $PAQ"
  dpkg-query -W "$PAQ"
  echo '```'
} > "$SALIDA/salida.txt" 2>&1

instalada=$(dpkg-query -W -f='${Version}' "$PAQ" 2>/dev/null)
rc_viejo=$(sed -n '/lote VIEJO/,/^(código/p' "$SALIDA/salida.txt" | tail -1)
{
  cat "$SALIDA/salida.txt"
  echo
  if [ "$instalada" = "2.0" ] && [ "$rc_viejo" != "(código 0)" ]; then
    echo "VEREDICTO: PASA — apt se niega a bajar de versión y la 2.0 sigue instalada"
  else
    echo "VEREDICTO: FALLA — instalada: '$instalada'; apt con el lote viejo: $rc_viejo"
  fi
} > "$SALIDA/informe.md"
tail -1 "$SALIDA/informe.md"
grep -q 'VEREDICTO: PASA' "$SALIDA/informe.md"
