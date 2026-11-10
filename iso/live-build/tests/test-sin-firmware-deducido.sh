#!/usr/bin/env bash
# test-sin-firmware-deducido.sh — la ISO no instala firmware deducido del índice Contents.
#
# Por qué existe (10-nov, ADR-018): con --firmware-chroot (por defecto en live-build)
# la ISO instalaba 20 paquetes deducidos de Contents-{all,amd64} (45 MB): firmware de
# hardware muy concreto e indi-dsi, que arrastraba libcurl3-gnutls, libssh2-1, librtmp1…
# El 8-nov, sin Contents (doble barra en el espejo), la etapa no instaló nada SIN dar
# error y la ISO cambió en silencio. Ahora el firmware solo entra si se lista a mano.
#
# Uso: ./iso/live-build/tests/test-sin-firmware-deducido.sh   (sale con 0 solo si pasa)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LB="$HERE/.."

fallos=0
ok()    { echo "  ok    $*"; }
falla() { echo "  FALLA $*"; fallos=$((fallos + 1)); }

echo "== auto/config"
for opcion in "--firmware-chroot false" "--firmware-binary false"; do
    grep -Eq -- "^\s*${opcion% *} +${opcion#* }\b" "$LB/auto/config" \
        && ok "pasa '$opcion' a lb config" || falla "falta '$opcion' en auto/config"
done

# Los 20 paquetes que solo entraban por la etapa de firmware (medido el 10-nov sobre la ISO
# de CI 5e7aff5c: incluye firmware-linux-free y alsa-topology-conf, que solo eran Recomienda).
SOLO_FIRMWARE="firmware-linux-free alsa-topology-conf firmware-ath9k-htc hdmi2usb-fx2-firmware indi-dsi ixo-usb-jtag wireless-regdb
libcfitsio10 libcurl3-gnutls libfftw3-double3 libgomp1 libindi-data libindidriver1
libnghttp2-14 libnova-0.16-0 libpsl5 librtmp1 libssh2-1 libtheora0 libusb-1.0-0"

echo "== paquetes-linea-base-3b1.txt"
quedan=""
for p in $SOLO_FIRMWARE; do
    grep -Eq "^${p//./\\.}(:[a-z0-9]+)?	" "$LB/paquetes-linea-base-3b1.txt" && quedan="$quedan $p"
done
[ -z "$quedan" ] && ok "sin los 20 paquetes del firmware deducido" \
    || falla "la línea base aún lista:$quedan"

echo
if [ "$fallos" -ne 0 ]; then echo "RESULTADO: $fallos comprobaciones fallaron"; exit 1; fi
echo "RESULTADO: OK"
