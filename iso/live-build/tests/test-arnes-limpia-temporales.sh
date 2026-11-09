#!/usr/bin/env bash
# test-arnes-limpia-temporales.sh — `install-in-qemu.sh arrancar` tiene que borrar su carpeta temporal.
#
# Por qué existe (8-nov): `cmd_arrancar` crea con mktemp el disco auxiliar del verificador
# (`nimbo-verif.XXXXXX`, que lleva una copia de la clave LUKS GENERADA para las pruebas) y lo
# borraba con `trap 'rm -rf "$tools"' EXIT`. Pero `tools` era `local`: cuando el trap corre
# (al salir del script) la variable ya no existe y, con `set -u`, el trap falla con
# "line 1: tools: unbound variable". Resultado: la carpeta (y la copia de la clave) quedaba
# en /tmp. Se encontraron 6.
#
# Cómo prueba: copia el arnés a un directorio temporal y ejecuta `arrancar` con un
# qemu-system-x86_64 FALSO, un OVMF falso y un TMPDIR propio. No arranca ninguna VM.
#
# Uso: ./iso/live-build/tests/test-arnes-limpia-temporales.sh   (sale con 0 solo si pasa)
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$HERE/.."
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

arnes="$TMP/arnes"; tmpd="$TMP/tmpdir"
mkdir -p "$arnes" "$tmpd" "$TMP/bin"
cp "$SRC/install-in-qemu.sh" "$SRC/lib-qemu.sh" "$SRC/verificar-instalado.sh" "$arnes/"
: > "$arnes/nimbo-install.qcow2"            # "instalación" existente (no se arranca de verdad)
: > "$arnes/nimbo-install-vars.fd"
echo "clave-falsa-del-test" > "$arnes/.clave-prueba-luks"
: > "$TMP/OVMF_CODE.fd"; : > "$TMP/OVMF_VARS.fd"

cat > "$TMP/bin/qemu-system-x86_64" <<'Q'
#!/bin/sh
exit 0
Q
chmod +x "$TMP/bin/qemu-system-x86_64"

rc=0
( cd "$arnes" && PATH="$TMP/bin:$PATH" TMPDIR="$tmpd" OVMF_CODE="$TMP/OVMF_CODE.fd" \
    OVMF_VARS="$TMP/OVMF_VARS.fd" NIMBO_QEMU_DISPLAY=none ./install-in-qemu.sh arrancar ) \
    > "$TMP/salida" 2>&1 || rc=$?

fallos=0
ok()    { echo "  ok    $*"; }
falla() { echo "  FALLA $*"; fallos=$((fallos + 1)); }

echo "== install-in-qemu.sh arrancar (QEMU falso)"
[ "$rc" -eq 0 ] && ok "termina con 0" || falla "termina con $rc"
if grep -q "unbound variable" "$TMP/salida"; then
    falla "error del trap: $(grep -m1 'unbound variable' "$TMP/salida")"
else
    ok "sin 'unbound variable'"
fi
restos="$(find "$tmpd" -maxdepth 1 -name 'nimbo-verif.*' | wc -l)"
[ "$restos" -eq 0 ] && ok "no queda ninguna carpeta nimbo-verif.* en TMPDIR" \
    || falla "quedan $restos carpeta(s) nimbo-verif.* en TMPDIR (con la copia de la clave de prueba)"

echo
if [ "$fallos" -ne 0 ]; then
    echo "--- salida del arnés ---"; tail -5 "$TMP/salida"
    echo "RESULTADO: $fallos comprobaciones fallaron"; exit 1
fi
echo "RESULTADO: todo pasa"
