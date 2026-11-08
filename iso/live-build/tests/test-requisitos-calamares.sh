#!/usr/bin/env bash
# test-requisitos-calamares.sh — Calamares no puede rechazar un equipo de 1 GiB de RAM (H-002).
#
# Por qué existe: con `requiredRam: 1.0` Calamares se negaba a instalar en una VM de
# 1024 MiB (5-nov). El kernel de esa VM reporta 962 128 KiB y reserva ~135 MiB, así que
# Calamares ve unos 0.79 GiB. El 8-nov se probó que instalando con 1 GiB el disco cifrado se
# desbloquea (cryptsetup calibra argon2id en la propia máquina: 438 MiB). El mínimo
# declarado es 1 GiB nominal → requiredRam tiene que quedar por debajo de lo que ve Calamares.
#
# Uso: ./iso/live-build/tests/test-requisitos-calamares.sh   (sale con 0 solo si pasa)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WELCOME="$HERE/../config/includes.chroot/etc/calamares/modules/welcome.conf"
[ -f "$WELCOME" ] || { echo "ERROR: no encuentro $WELCOME" >&2; exit 2; }

# Lo que una VM de 1024 MiB le muestra a Calamares (GiB), con margen hacia abajo.
VISTO_CON_1GIB="0.78"

valor="$(sed -n 's/^[[:space:]]*requiredRam:[[:space:]]*\([0-9.]*\).*/\1/p' "$WELCOME")"
echo "== requiredRam = ${valor:-?} (un equipo de 1 GiB muestra ~0.79 GiB; límite del test $VISTO_CON_1GIB)"

if [ -z "$valor" ]; then
    echo "  FALLA no encuentro requiredRam en welcome.conf"; exit 1
fi
if awk -v r="$valor" -v l="$VISTO_CON_1GIB" 'BEGIN { exit !(r > 0 && r <= l) }'; then
    echo "  ok    Calamares admite un equipo de 1 GiB"
    echo; echo "RESULTADO: todo pasa"
else
    echo "  FALLA requiredRam=$valor rechaza un equipo de 1 GiB (ve ~0.79 GiB)"
    echo; echo "RESULTADO: 1 comprobación falló"; exit 1
fi
