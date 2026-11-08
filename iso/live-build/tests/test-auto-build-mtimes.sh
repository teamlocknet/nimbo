#!/usr/bin/env bash
# test-auto-build-mtimes.sh — antes de live-build, todo config/ tiene que estar en SOURCE_DATE_EPOCH.
#
# Por qué existe (H-004): mksquashfs 4.5.1 solo recorta al epoch las fechas POSTERIORES a
# SOURCE_DATE_EPOCH. Los ficheros de config/includes.chroot/ se copian al chroot con su
# mtime, así que si en la copia de trabajo son ANTERIORES al epoch (un checkout que no se
# ha reescrito desde el commit) esa fecha llega tal cual a la ISO. El 8-nov el mismo
# commit dio b6834363… en la copia de trabajo y 48c2e1c5… en un clon recién hecho.
#
# Cómo prueba: ejecuta una copia de auto/build en un directorio temporal con un `lb` falso
# que, al empezar la primera etapa, anota el mtime de cada entrada de config/. No usa
# contenedor, red ni root.
#
# Uso: ./iso/live-build/tests/test-auto-build-mtimes.sh   (sale con 0 solo si todo pasa)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTO_BUILD="$HERE/../auto/build"
[ -f "$AUTO_BUILD" ] || { echo "ERROR: no encuentro $AUTO_BUILD" >&2; exit 2; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

EPOCH=1793814833   # el de main el 8-nov (2026-11-04T17:53:53Z)

# --- lb falso -----------------------------------------------------------------------
# En la etapa bootstrap (la primera) anota "mtime ruta" de todo config/, sin seguir
# enlaces: es lo que verá live-build. En chroot crea un rootfs mínimo para el sortfile.
mkdir -p "$TMP/bin"
cat > "$TMP/bin/lb" <<'LB'
#!/bin/sh
etapa="$1"
if [ "$etapa" = "bootstrap" ]; then
    find config -exec stat -c '%Y %n' {} + | LC_ALL=C sort -k2 > "$LB_MTIMES"
fi
if [ "$etapa" = "chroot" ]; then
    mkdir -p chroot/usr/bin && : > chroot/usr/bin/algo
fi
exit 0
LB
chmod +x "$TMP/bin/lb"

# --- config/ de prueba con fechas como las de una copia de trabajo vieja ------------
dir="$TMP/arbol"
mkdir -p "$dir/auto" "$dir/config/includes.chroot/etc/calamares/modules" \
         "$dir/config/includes.chroot/usr/bin" "$dir/config/hooks/normal"
cp "$AUTO_BUILD" "$dir/auto/build"
echo "requiredRam: 1.0" > "$dir/config/includes.chroot/etc/calamares/modules/welcome.conf"
echo '#!/bin/sh'        > "$dir/config/includes.chroot/usr/bin/nimbo-instalar"
echo '#!/bin/sh'        > "$dir/config/hooks/normal/0100-prueba.hook.chroot"
# Enlace roto a propósito: hay que fechar el enlace, no seguirlo (touch sin -h fallaría).
ln -s /no/existe "$dir/config/includes.chroot/etc/enlace-roto"
# Anteriores al epoch (como el 23-oct de la copia de trabajo de Juan José)…
find "$dir/config" -exec touch -h -d '2026-10-23 11:36:45 UTC' {} +
# …y una posterior, para comprobar que también queda exactamente en el epoch.
touch -d '2026-11-08 21:00:00 UTC' "$dir/config/hooks/normal/0100-prueba.hook.chroot"

echo "== config/ con fechas anteriores y posteriores al epoch ($EPOCH)"
rc=0
( cd "$dir" && PATH="$TMP/bin:$PATH" LB_MTIMES="$TMP/mtimes" SOURCE_DATE_EPOCH="$EPOCH" \
    sh auto/build ) >"$TMP/salida" 2>&1 || rc=$?

fallos=0
ok()    { echo "  ok    $*"; }
falla() { echo "  FALLA $*"; fallos=$((fallos + 1)); }

[ "$rc" -eq 0 ] && ok "auto/build termina con 0" || { falla "auto/build termina con $rc"; cat "$TMP/salida"; }

if [ ! -s "$TMP/mtimes" ]; then
    falla "el lb falso no llegó a anotar los mtimes de config/"
else
    total="$(wc -l < "$TMP/mtimes")"
    distintas="$(awk -v e="$EPOCH" '$1 != e' "$TMP/mtimes")"
    if [ -z "$distintas" ]; then
        ok "las $total entradas de config/ están en $EPOCH al empezar live-build"
    else
        falla "$(printf '%s\n' "$distintas" | wc -l) de $total entradas no están en $EPOCH:"
        printf '%s\n' "$distintas" | sed 's/^/          /'
    fi
fi

echo
if [ "$fallos" -ne 0 ]; then
    echo "RESULTADO: $fallos comprobaciones fallaron"
    exit 1
fi
echo "RESULTADO: todo pasa"
