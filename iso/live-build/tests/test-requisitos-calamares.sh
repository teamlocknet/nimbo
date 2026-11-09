#!/usr/bin/env bash
# test-requisitos-calamares.sh — comprobaciones estáticas de la configuración de Calamares.
#
# 1. RAM (H-002, ADR-009): con `requiredRam: 1.0` Calamares se negaba a instalar en una VM
#    de 1024 MiB (5-nov): el kernel reporta 962 128 KiB y reserva ~135 MiB, así que
#    Calamares ve unos 0.79 GiB. El mínimo declarado es 1 GiB nominal → requiredRam tiene
#    que quedar por debajo de lo que ve Calamares.
# 2. Idioma, zona y swap (3C.2, ADR-017): el instalador pregunta idioma y zona SIN geoip
#    (hermetismo), los aplica en el destino (locale + localecfg) y crea un archivo de swap
#    dentro de la raíz cifrada.
#
# Uso: ./iso/live-build/tests/test-requisitos-calamares.sh   (sale con 0 solo si todo pasa)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CFG="$HERE/../config"
CAL="$CFG/includes.chroot/etc/calamares"
WELCOME="$CAL/modules/welcome.conf"
SETTINGS="$CAL/settings.conf"
PARTITION="$CAL/modules/partition.conf"
LOCALE="$CAL/modules/locale.conf"
for f in "$WELCOME" "$SETTINGS" "$PARTITION"; do
    [ -f "$f" ] || { echo "ERROR: no encuentro $f" >&2; exit 2; }
done

fallos=0
ok()    { echo "  ok    $*"; }
falla() { echo "  FALLA $*"; fallos=$((fallos + 1)); }

# Bloque de una sección de `sequence:` (show/exec) por orden de aparición: n=1 show, 2 exec.
bloque() { awk -v n="$1" '/^- (show|exec):$/{k++; next} /^- /{if(k==n) exit} k==n' "$SETTINGS"; }

# --- 1. RAM ------------------------------------------------------------------------------
VISTO_CON_1GIB="0.78"   # lo que una VM de 1024 MiB le muestra a Calamares (GiB), con margen
echo "== 1. RAM mínima (H-002)"
valor="$(sed -n 's/^[[:space:]]*requiredRam:[[:space:]]*\([0-9.]*\).*/\1/p' "$WELCOME")"
if [ -n "$valor" ] && awk -v r="$valor" -v l="$VISTO_CON_1GIB" 'BEGIN { exit !(r > 0 && r <= l) }'; then
    ok "requiredRam=$valor: Calamares admite un equipo de 1 GiB (ve ~0.79 GiB)"
else
    falla "requiredRam='${valor}' rechaza un equipo de 1 GiB (ve ~0.79 GiB)"
fi

# --- 2. Idioma y zona --------------------------------------------------------------------
echo "== 2. Idioma y zona horaria (3C.2)"
bloque 1 | grep -qx '  - locale' && ok "pantalla 'locale' en show" || falla "falta la pantalla 'locale' en show"
bloque 2 | grep -qx '  - locale' && ok "'locale' en exec (aplica la zona horaria)" || falla "falta 'locale' en exec"
bloque 2 | grep -qx '  - localecfg' && ok "'localecfg' en exec (genera el idioma)" || falla "falta 'localecfg' en exec"
if [ -f "$LOCALE" ]; then
    grep -Eq '^[[:space:]]+style:[[:space:]]*"?none"?' "$LOCALE" && ok "locale.conf: geoip desactivado (style: none)" || falla "locale.conf: geoip no está en style: none (hermetismo)"
    grep -Eq '^[[:space:]]*url:' "$LOCALE" && falla "locale.conf: hay una url (no puede salir a la red)" || ok "locale.conf: sin url"
else
    falla "no existe $LOCALE"
fi
grep -qx 'locales' "$CFG/package-lists/desktop.list.chroot" && ok "paquete 'locales' en desktop.list.chroot" || falla "falta el paquete 'locales' (Calamares lo necesita para listar y generar idiomas)"

# --- 3. Swap -----------------------------------------------------------------------------
echo "== 3. Swap (3C.2)"
grep -Eq '^userSwapChoices:[[:space:]]*\[.*\bfile\b.*\]' "$PARTITION" && ok "userSwapChoices incluye 'file'" || falla "userSwapChoices no ofrece 'file' (archivo de swap)"
grep -Eq '^initialSwapChoice:[[:space:]]*file$' "$PARTITION" && ok "initialSwapChoice: file" || falla "initialSwapChoice no es 'file'"

echo
if [ "$fallos" -ne 0 ]; then
    echo "RESULTADO: $fallos comprobaciones fallaron"
    exit 1
fi
echo "RESULTADO: todo pasa"
