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
    case "$paquete" in nimbo-*) fallar "modulo propio en el pool local: $paquete" ;; esac
    case "$version" in *~bpo*) fallar "backports en pool: $paquete $version" ;; esac
    cantidad=$((cantidad+1))
done
[ "$cantidad" -gt 0 ] || fallar "pool local vacio"
echo "P: [PR-B] pool local: $cantidad paquetes, sin modulos nimbo-* ni backports"

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

# ADR-020: el resto de módulos de la lista, manuales y con sus órdenes utilizables.
LISTA="$ROOT/usr/share/nimbo/modulos.list"
[ -s "$LISTA" ] || fallar "falta /usr/share/nimbo/modulos.list"
for m in $(grep -v '^[[:space:]]*#' "$LISTA" | grep -v '^[[:space:]]*$'); do
    estado="$(dpkg-query --admindir="$ROOT/var/lib/dpkg" -W -f='${db:Status-Status}' "$m" 2>/dev/null || true)"
    [ "$estado" = installed ] || fallar "$m no instalado en el squashfs (estado: ${estado:-ausente})"
    printf '%s\n' "$manuales" | grep -qx "$m" || fallar "$m no esta marcado manual"
    for b in $(chroot "$ROOT" dpkg -L "$m" | grep '^/usr/bin/'); do
        chroot "$ROOT" "$b" --help >/dev/null || fallar "$b --help falla"
    done
    echo "P: [ADR-020] $m $(dpkg-query --admindir="$ROOT/var/lib/dpkg" -W -f='${Version}' "$m"): manual y utilizable"
done

# ADR-020: hardening 3B.2 en el squashfs (los valores en vivo los mide verify-hardening).
for f in etc/sysctl.d/99-zz-nimbo-hardening.conf usr/share/nimbo/hardening/99-zz-nimbo-hardening.conf \
         etc/security/faillock.conf usr/lib/nimbo/verify-hardening; do
    [ -s "$ROOT/$f" ] || fallar "3B.2: falta /$f"
done
grep -q 'pam_faillock.so preauth' "$ROOT/etc/pam.d/common-auth" || fallar "3B.2: common-auth sin faillock"
grep -q 'pam_faillock.so' "$ROOT/etc/pam.d/common-account" || fallar "3B.2: common-account sin faillock"
echo "P: [ADR-020] OK: hardening 3B.2 en el squashfs (sysctl 99-zz-, faillock en auth y account)"
