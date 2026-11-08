#!/usr/bin/env bash
# test-auto-build-falla.sh — si una etapa de live-build falla, auto/build tiene que fallar.
#
# Por qué existe: el 4 y el 5-nov la etapa `lb chroot` abortó en CI (descargas caídas de
# snapshot.debian.org) y aun así `auto/build` terminó con código 0, porque cada etapa va
# por una tubería hacia `tee` y /bin/sh no tiene `pipefail`. La CI solo lo detectaba un
# paso después, al no encontrar la ISO.
#
# Cómo prueba: ejecuta una copia de auto/build en un directorio temporal con un `lb` falso
# que anota cada etapa y falla en la que se le pida. No usa contenedor, red ni root.
#
# Uso: ./iso/live-build/tests/test-auto-build-falla.sh   (sale con 0 solo si todo pasa)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
AUTO_BUILD="$HERE/../auto/build"
[ -f "$AUTO_BUILD" ] || { echo "ERROR: no encuentro $AUTO_BUILD" >&2; exit 2; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# --- lb falso -----------------------------------------------------------------------
# Anota la etapa en $LB_REGISTRO, imprime una línea (para comprobar el log) y sale con 1
# si la etapa coincide con $LB_FALLAR_EN. En la etapa chroot crea un rootfs mínimo, como
# haría la de verdad, para que auto/build pueda generar el sortfile.
mkdir -p "$TMP/bin"
cat > "$TMP/bin/lb" <<'LB'
#!/bin/sh
etapa="$1"
echo "$etapa" >> "$LB_REGISTRO"
echo "lb-falso: etapa $etapa"
if [ "$etapa" = "chroot" ]; then
    mkdir -p chroot/usr/bin && : > chroot/usr/bin/algo
fi
if [ "$etapa" = "${LB_FALLAR_EN:-}" ]; then
    echo "lb-falso: fallo simulado en $etapa" >&2
    exit 1
fi
exit 0
LB
chmod +x "$TMP/bin/lb"

fallos=0
ok()    { echo "  ok    $*"; }
falla() { echo "  FALLA $*"; fallos=$((fallos + 1)); }

# caso <nombre> <etapa-que-falla|""> <rc-esperado: 0|no0> <etapas-esperadas>
caso() {
    local nombre="$1" fallar_en="$2" rc_esperado="$3" esperadas="$4"
    local dir="$TMP/$nombre"
    # config/ existe siempre en un build real (lo crea `lb config`); auto/build fija sus fechas.
    mkdir -p "$dir/auto" "$dir/config"
    cp "$AUTO_BUILD" "$dir/auto/build"
    echo "== $nombre"

    local rc=0
    ( cd "$dir" && PATH="$TMP/bin:$PATH" LB_REGISTRO="$dir/registro" LB_FALLAR_EN="$fallar_en" \
        SOURCE_DATE_EPOCH=0 sh auto/build ) >"$dir/salida" 2>&1 || rc=$?

    case "$rc_esperado" in
        0)   [ "$rc" -eq 0 ] && ok "termina con 0" || falla "termina con $rc (se esperaba 0)" ;;
        no0) [ "$rc" -ne 0 ] && ok "termina con $rc (distinto de 0)" || falla "termina con 0 aunque falló '$fallar_en'" ;;
    esac

    local corridas
    corridas="$(tr '\n' ' ' < "$dir/registro" 2>/dev/null | sed 's/ $//')"
    [ "$corridas" = "$esperadas" ] && ok "etapas: $corridas" \
        || falla "etapas: '$corridas' (se esperaba '$esperadas')"

    # El log sigue recogiendo la salida de todas las etapas que corrieron.
    local etapa
    for etapa in $esperadas; do
        grep -q "lb-falso: etapa $etapa" "$dir/binary.buildlog" 2>/dev/null \
            && ok "binary.buildlog tiene la etapa $etapa" \
            || falla "binary.buildlog no tiene la etapa $etapa"
    done
}

caso todo-bien       ""          0   "bootstrap chroot installer binary"
caso falla-bootstrap bootstrap   no0 "bootstrap"
caso falla-chroot    chroot      no0 "bootstrap chroot"
caso falla-installer installer   no0 "bootstrap chroot installer"
caso falla-binary    binary      no0 "bootstrap chroot installer binary"

echo
if [ "$fallos" -ne 0 ]; then
    echo "RESULTADO: $fallos comprobaciones fallaron"
    exit 1
fi
echo "RESULTADO: todo pasa"
