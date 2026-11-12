#!/usr/bin/env bash
# test-modulos-en-receta.sh — los módulos propios y el hardening 3B.2 entran en la ISO por la
# receta, con una sola lista y sin dejar huecos en CI (ADR-020).
#
# Por qué existe (12-nov): hasta #77 la receta solo sabía construir nimbo-audit (exigía
# exactamente un .deb). Al integrar más módulos hay cuatro sitios que deben ir a la par:
# la lista de módulos, el build, los hooks y los filtros de los workflows. Si uno se queda
# atrás, un cambio en un módulo no recompila la ISO o el módulo no llega al instalado.
# Además, nimbo-update-offline no compilaba como .deb en el contenedor anclado: sus tests
# generan claves y gpg sin gpg-agent (con --no-install-recommends) falla.
#
# Uso: ./iso/live-build/tests/test-modulos-en-receta.sh   (sale con 0 solo si pasa)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LB="$(cd "$HERE/.." && pwd)"
REPO="$(cd "$LB/../.." && pwd)"
HOOKS="$LB/config/hooks/normal"
LISTA="$LB/config/includes.chroot/usr/share/nimbo/modulos.list"

fallos=0
ok()    { echo "  ok    $*"; }
falla() { echo "  FALLA $*"; fallos=$((fallos + 1)); }
versionado() { git -C "$REPO" check-ignore -q "$1" && return 1 || return 0; }

echo "== lista de módulos"
MODULOS=""
if [ -f "$LISTA" ]; then
    MODULOS="$(grep -v '^[[:space:]]*#' "$LISTA" | grep -v '^[[:space:]]*$' || true)"
    versionado "$LISTA" && ok "modulos.list versionada" || falla "modulos.list ignorada por git"
else
    falla "falta $LISTA"
fi
for m in nimbo-audit nimbo-red nimbo-update-offline; do
    printf '%s\n' "$MODULOS" | grep -qx "$m" && ok "lista $m" || falla "la lista no incluye $m"
done
for m in $MODULOS; do
    [ -f "$REPO/packages/$m/debian/control" ] && ok "$m tiene debian/control" \
        || falla "$m no tiene packages/$m/debian/control"
    if grep -Eq '^ *gpg,?$' "$REPO/packages/$m/debian/control"; then
        grep -Eq '^ *gpg-agent,?$' "$REPO/packages/$m/debian/control" \
            && ok "$m: Build-Depends con gpg-agent" \
            || falla "$m usa gpg al compilar sin gpg-agent en Build-Depends"
    fi
done

echo "== build-in-container.sh"
B="$LB/build-in-container.sh"
grep -q 'usr/share/nimbo/modulos.list' "$B" && ok "lee la lista de módulos" \
    || falla "no lee modulos.list"
grep -q ':/src/packages\$SRC_VOL' "$B" && ok "monta packages/" || falla "no monta packages/"
grep -q ':/src/hardening-3b2\$SRC_VOL' "$B" && ok "monta security/hardening/3b2" \
    || falla "no monta security/hardening/3b2"
grep -q 'apt-get build-dep' "$B" && ok "instala las Build-Depends de cada módulo" \
    || falla "no instala las Build-Depends de los módulos"
if grep -q '= nimbo-audit \]' "$B"; then falla "sigue atado a nimbo-audit"; else ok "un .deb por módulo de la lista"; fi

echo "== hooks"
for h in 0170-nimbo-hardening-3b2.hook.chroot 0185-nimbo-modulos.hook.chroot; do
    if [ -f "$HOOKS/$h" ]; then
        [ -x "$HOOKS/$h" ] && ok "$h ejecutable" || falla "$h no es ejecutable"
        versionado "$HOOKS/$h" && ok "$h versionado" || falla "$h ignorado por git"
    else
        falla "falta $h"
    fi
done
[ -f "$HOOKS/0185-nimbo-modulos.hook.chroot" ] && grep -q '/usr/share/nimbo/modulos.list' "$HOOKS/0185-nimbo-modulos.hook.chroot" \
    && ok "0185 recorre la misma lista" || falla "0185 no lee modulos.list"
[ -f "$HOOKS/0170-nimbo-hardening-3b2.hook.chroot" ] && grep -q 'pam-auth-update --package --enable nimbo-faillock nimbo-faillock-preauth' "$HOOKS/0170-nimbo-hardening-3b2.hook.chroot" \
    && ok "0170 activa los perfiles PAM" || falla "0170 no activa nimbo-faillock"

echo "== ningún módulo propio en el pool local"
for f in "$HOOKS/0200-nimbo-pool-local.hook.chroot" "$LB/verificar-cli-rootfs.sh"; do
    grep -q 'nimbo-\*)' "$f" && ok "$(basename "$f") rechaza nimbo-*" \
        || falla "$(basename "$f") solo rechaza nimbo-audit"
done

echo "== filtros de los workflows"
for w in build-iso.yml repro-verify.yml; do
    rutas=("security/hardening/3b2/**")
    for m in $MODULOS; do rutas+=("packages/$m/**"); done
    for ruta in "${rutas[@]}"; do
        grep -qF "\"$ruta\"" "$REPO/.github/workflows/$w" && ok "$w vigila $ruta" \
            || falla "$w no recompila con cambios en $ruta"
    done
done

echo "== CI"
for t in iso/live-build/tests/test-modulos-en-receta.sh security/hardening/3b2/pruebas/test-verify-hardening.sh; do
    grep -qF "$t" "$REPO/.github/workflows/ci.yml" && ok "ci.yml corre $t" || falla "ci.yml no corre $t"
done

echo
if [ "$fallos" -eq 0 ]; then echo "OK: receta de módulos coherente"; else echo "FALLA: $fallos comprobación(es)"; fi
[ "$fallos" -eq 0 ]
