#!/usr/bin/env bash
# preparar-vm.sh — deja nimbo-nav instalado en una VM Debian 12 (bookworm) limpia, sin
# pasos a mano (ADR-012, prototipo). Se ejecuta DENTRO de la VM, como root, desde el clon:
#   sudo bash packages/nimbo-nav/pruebas/preparar-vm.sh
# Usa los repositorios que tenga la VM (necesita red). Antes, haz un snapshot de la VM.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Ejecuta con sudo"; exit 1; }
grep -q 'VERSION_CODENAME=bookworm' /etc/os-release || { echo "Solo Debian 12 (bookworm)"; exit 1; }

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PKG="$(cd "$HERE/.." && pwd)"
export DEBIAN_FRONTEND=noninteractive

apt-get update -qq
apt-get install -y -qq --no-install-recommends \
  build-essential fakeroot debhelper dh-python pybuild-plugin-pyproject \
  python3-all python3-setuptools python3-pytest \
  firefox-esr tor nftables iproute2 libnotify-bin tcpdump curl

trabajo=$(mktemp -d)
cp -a "$PKG" "$trabajo/nimbo-nav"
( cd "$trabajo/nimbo-nav" && dpkg-buildpackage -us -uc -b )
apt-get install -y "$trabajo"/nimbo-nav_*_all.deb

echo
echo "== Comprobaciones de la instalación"
dpkg -s nimbo-nav | grep -E '^(Status|Version):'
echo "tor habilitado al arrancar: $(systemctl is-enabled tor@default.service 2>/dev/null || true) (esperado: disabled)"
echo "tor activo ahora:           $(systemctl is-active tor@default.service 2>/dev/null || true) (esperado: inactive)"
echo "puerto 9050 en escucha:     $(ss -Hltn 'sport = :9050' | wc -l) (esperado: 0)"
echo "políticas de Firefox:       $(test -f /etc/firefox/policies/policies.json && echo instaladas || echo FALTAN)"
echo
echo "Listo. Siguientes pruebas (como tu usuario, en la sesión gráfica):"
echo "  bash $HERE/prueba-reposo-navegador.sh      # RF-NAV-01"
echo "  bash $HERE/prueba-fugas-tor.sh             # RF-NAV-02"
