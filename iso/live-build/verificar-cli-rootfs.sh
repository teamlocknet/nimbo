#!/usr/bin/env bash
# PR-B: inspeccion del squashfs extraido; no va dentro del producto.
set -euo pipefail
ROOT="${1:?Uso: verificar-cli-rootfs.sh <rootfs-extraido>}"
ROOT="$(cd "$ROOT" && pwd)"
fallar() { echo "E: [PR-B] $*" >&2; exit 1; }

estado="$(dpkg-query --admindir="$ROOT/var/lib/dpkg" -W     -f='${db:Status-Status}' nimbo-audit 2>/dev/null || true)"
[ "$estado" = installed ] || fallar "nimbo-audit NO instalado en el squashfs (estado: ${estado:-ausente})"
[ -x "$ROOT/usr/bin/nimbo-audit" ] || fallar "falta /usr/bin/nimbo-audit"
echo "P: [PR-B] nimbo-audit instalado: $(dpkg-query --admindir="$ROOT/var/lib/dpkg" -W -f='${Version}' nimbo-audit)"

test -s "$ROOT/usr/share/man/man1/nimbo-audit.1.gz" || fallar "manual ausente"
gzip -t "$ROOT/usr/share/man/man1/nimbo-audit.1.gz" || fallar "manual corrupto"

# La fuente temporal de live-build no debe viajar a live ni al instalado.
for resto in root/packages root/packages.chroot etc/apt/sources.list.d/packages.list etc/apt/sources.list.d/zz-sources.list; do
    [ ! -e "$ROOT/$resto" ] && [ ! -L "$ROOT/$resto" ] || fallar "resto del repo temporal: /$resto"
done
for fuente in "$ROOT/etc/apt/sources.list" "$ROOT/etc/apt/sources.list.d"; do
    [ -e "$fuente" ] || continue
    rc=0
    grep -rEn 'file:/*root/packages|config/packages[.]chroot' "$fuente" || rc=$?
    case "$rc" in
        0) fallar "fuente APT temporal en el squashfs" ;;
        1) ;;
        *) fallar "no se pudieron inspeccionar las fuentes APT" ;;
    esac
done
if [ -d "$ROOT/var/lib/apt/lists" ]; then
    restos="$(find "$ROOT/var/lib/apt/lists" -name '*root_packages*' -print)"
    [ -z "$restos" ] || fallar "indices del repo temporal: $restos"
fi
echo "P: [PR-B] repo temporal limpio: /root/packages, sources.list.d y apt/lists sin rastro"

# Inspeccionar metadatos, no solamente nombres de archivos.
POOL="$ROOT/usr/share/nimbo/pool"
[ -d "$POOL" ] || fallar "falta pool local"
cantidad=0
for deb in "$POOL"/*.deb; do
    [ -f "$deb" ] || continue
    paquete="$(dpkg-deb -f "$deb" Package)"
    version="$(dpkg-deb -f "$deb" Version)"
    [ "$paquete" != nimbo-audit ] || fallar "nimbo-audit entro en el pool local"
    case "$version" in *~bpo*) fallar "backports en pool: $paquete $version" ;; esac
    cantidad=$((cantidad+1))
done
[ "$cantidad" -gt 0 ] || fallar "pool local vacio"
echo "P: [PR-B] pool local: $cantidad paquetes, sin nimbo-audit ni backports"

bpo="$(dpkg-query --admindir="$ROOT/var/lib/dpkg" -W -f='${Package} ${Version}
' | grep '~bpo' || true)"
[ -n "$bpo" ] || fallar "falta Calamares de backports en live"
otros="$(printf '%s
' "$bpo" | awk 'NF && $1 != "calamares"')"
[ -z "$otros" ] || fallar "backports no autorizados: $otros"
echo "P: [PR-B] backports del squashfs: solo $bpo"

# Confirmar presencia de dependencias runtime y que no sera autoremovido.
for paquete in python3 python3-typer python3-click; do
    estado="$(dpkg-query --admindir="$ROOT/var/lib/dpkg" -W -f='${db:Status-Status}' "$paquete" 2>/dev/null || true)"
    [ "$estado" = installed ] || fallar "dependencia runtime ausente: $paquete"
done
[ "$(id -u)" = 0 ] || fallar "la comprobacion funcional necesita root dentro del contenedor"
manuales="$(chroot "$ROOT" apt-mark showmanual)"
printf '%s\n' "$manuales" | grep -qx nimbo-audit || fallar "nimbo-audit no esta marcado manual"
chroot "$ROOT" nimbo-audit --help
chroot "$ROOT" nimbo-audit verify --help
echo "P: [PR-B] OK: CLI y verify utilizables en squashfs limpio"
