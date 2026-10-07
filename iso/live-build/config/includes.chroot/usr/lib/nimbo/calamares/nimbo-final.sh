#!/bin/sh
# nimbo-final.sh — Paso 3C.1 (ADR-006). Lo ejecuta Calamares (shellprocess) DENTRO del
# sistema destino, después de `bootloader` y antes de regenerar el initramfs.
#
# Deja el sistema INSTALADO sin rastro del instalador ni de la sesión live, y lo
# COMPRUEBA: si alguna comprobación falla, sale con error y Calamares marca la
# instalación como fallida (nada se da por bueno en silencio).
set -eu

DIR=/usr/lib/nimbo/calamares
LISTA="$DIR/solo-instalador.list"
export DEBIAN_FRONTEND=noninteractive

# --- (1) Paquetes: instalador + live, y sus dependencias huérfanas --------------------------
PAQUETES=$(grep -v '^[[:space:]]*#' "$LISTA" | grep -v '^[[:space:]]*$' | tr '\n' ' ')
echo "nimbo-final: purgando: $PAQUETES"
# SuggestsImportant=false: por defecto APT conserva lo que algún paquete instalado solo
# "Sugiere" (apt sugiere gnupg; perl-modules y perl se recomiendan en círculo...), y eso
# dejaba en el instalado ~17 paquetes de gnupg y perl que solo trajo Calamares. Lo que
# alguien "Recomienda" o "Depende" se conserva igual.
# shellcheck disable=SC2086
apt-get --yes --purge -o APT::AutoRemove::SuggestsImportant=false autoremove $PAQUETES

# --- (1b) Teclado de consola para el initramfs ----------------------------------------------
# El módulo `keyboard` ya escribió /etc/default/keyboard con la distribución elegida.
# Se regenera la caché de console-setup para que el initramfs (que Calamares reconstruye
# después de este script) lleve ESA distribución: la contraseña LUKS se teclea en el
# arranque con el mismo teclado con que se definió.
if command -v setupcon >/dev/null 2>&1; then
    setupcon --save-only || echo "nimbo-final: AVISO — setupcon --save-only falló" >&2
fi

# --- (2) Lo que NO pertenece a ningún paquete (vino por includes.chroot) --------------------
# apt no lo quita: se borra explícito. Incluye este mismo directorio (el script ya está
# cargado por sh; borrar su fichero no interrumpe la ejecución).
rm -rf /etc/calamares
rm -f  /usr/share/applications/nimbo-instalar.desktop
rm -f  /usr/bin/nimbo-instalar
rm -f  /lib/live/config/0150-nimbo-autologin /lib/live/config/0160-nimbo-instalador
rmdir  /lib/live/config /lib/live 2>/dev/null || true
rm -rf "$DIR"
rmdir  /usr/lib/nimbo 2>/dev/null || true

# --- (3) Comprobaciones (fallan la instalación si no se cumplen) -----------------------------
fallo=0
ko() { echo "nimbo-final: FALLO — $*" >&2; fallo=1; }

# Ningún paquete de backports, ni Calamares, ni paquetes live.
bpo=$(dpkg-query -W -f='${Package} ${Version}\n' | grep '~bpo' || true)
[ -z "$bpo" ] || ko "paquetes de backports instalados: $bpo"
for p in $PAQUETES; do
    if dpkg-query -W -f='${db:Status-Status}' "$p" 2>/dev/null | grep -q '^installed$'; then
        ko "sigue instalado: $p"
    fi
done
# Ninguna fuente APT remota ni de backports.
if grep -rhs '^[[:space:]]*deb' /etc/apt/sources.list /etc/apt/sources.list.d 2>/dev/null \
        | grep -v '^deb \[trusted=yes\] file:/usr/share/nimbo/pool \./$' | grep -q .; then
    ko "hay fuentes APT distintas del pool local"
fi
grep -rqs 'backports' /etc/apt && ko "queda una referencia a backports en /etc/apt"
# D14: sin autologin.
if grep -rqs '^[[:space:]]*autologin-user' /etc/lightdm; then ko "lightdm tiene autologin"; fi
# Hermetismo 3B.1: apt-daily* sigue enmascarado.
for u in apt-daily.timer apt-daily-upgrade.timer apt-daily.service apt-daily-upgrade.service; do
    [ "$(readlink "/etc/systemd/system/$u" 2>/dev/null)" = "/dev/null" ] || ko "$u no está enmascarado"
done
[ -f /etc/apt/apt.conf.d/99nimbo-no-telemetry ] || ko "falta 99nimbo-no-telemetry"
# Restos del instalador.
for f in /etc/calamares /usr/lib/nimbo/calamares /usr/bin/nimbo-instalar \
         /usr/share/applications/nimbo-instalar.desktop /lib/live/config; do
    [ ! -e "$f" ] || ko "queda $f"
done
# D17: lo que necesitará nimbo-tpm-setup es instalable SIN RED desde el pool (simulación).
if ! sim=$(apt-get --simulate --no-install-recommends install dracut tpm2-tools \
        libtss2-esys-3.0.2-0 libtss2-mu0 libtss2-rc0 libtss2-tcti-device0 libtss2-tctildr0 2>&1); then
    ko "dracut/tpm2-tools/libtss2 no son instalables desde el pool local:"
    printf '%s\n' "$sim" | tail -n 25 >&2
fi

[ "$fallo" = 0 ] || exit 1
echo "nimbo-final: OK — sin instalador, sin live, sin backports, sin autologin; hermetismo intacto"
