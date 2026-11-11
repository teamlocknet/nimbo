#!/usr/bin/env bash
# aplicar-en-vm.sh — aplica el endurecimiento 3B.2 en una VM Debian 12 y lo MIDE antes y
# después (ADR-014). Solo para la VM de prueba: en la ISO lo aplicará el PR de integración.
#
#   ⚠ PAM puede dejarte sin poder entrar. Antes: snapshot de la VM y una terminal de root
#     abierta (sudo -i) que NO cierres hasta comprobar que el inicio de sesión funciona.
#
#   sudo bash security/hardening/3b2/aplicar-en-vm.sh
#
# Deja en ./hardening-3b2-<fecha>/: lynis antes/después, verify-hardening antes/después y
# la comprobación de las herramientas de auditoría.
set -euo pipefail
[ "$(id -u)" -eq 0 ] || { echo "Ejecuta con sudo"; exit 1; }
grep -q 'VERSION_CODENAME=bookworm' /etc/os-release || { echo "Solo Debian 12 (bookworm)"; exit 1; }

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SALIDA="$PWD/hardening-3b2-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$SALIDA"
export DEBIAN_FRONTEND=noninteractive

apt-get install -y -qq --no-install-recommends lynis tcpdump >/dev/null

indice() { sed -n 's/.*Hardening index : \([0-9]*\).*/\1/p' "$1" | head -1; }

herramientas() {  # las herramientas de auditoría siguen funcionando
  {
    timeout 5 tcpdump -i lo -c 1 -nn >/dev/null 2>&1 &
    local td=$!
    sleep 1
    ping -c1 -W1 127.0.0.1 >/dev/null 2>&1 || true
    if wait "$td"; then echo "tcpdump en lo: ok"; else echo "tcpdump en lo: FALLA"; fi
    echo "ping sin root: $(su -s /bin/sh nobody -c 'ping -c1 -W1 127.0.0.1 >/dev/null 2>&1 && echo ok || echo FALLA')"
    command -v nimbo-audit >/dev/null && echo "nimbo-audit: $(nimbo-audit --help >/dev/null 2>&1 && echo ok || echo FALLA)"
    command -v firefox-esr >/dev/null && echo "firefox-esr: $(firefox-esr --version 2>/dev/null)"
    echo "faillock: $(faillock --user root >/dev/null 2>&1 && echo ok || echo FALLA)"
  } 2>&1
}

echo ">> ANTES"
lynis audit system --quick --no-colors > "$SALIDA/lynis-antes.txt" 2>&1 || true
bash "$HERE/verify-hardening.sh" > "$SALIDA/verify-antes.txt" 2>&1 || true
herramientas > "$SALIDA/herramientas-antes.txt"

echo ">> Aplicando sysctl y PAM"
install -m 0644 "$HERE/sysctl/99-nimbo-hardening.conf" /etc/sysctl.d/
mkdir -p /usr/share/nimbo/hardening
install -m 0644 "$HERE/sysctl/99-nimbo-hardening.conf" /usr/share/nimbo/hardening/
sysctl --system > "$SALIDA/sysctl-system.txt" 2>&1
cp -a /etc/security/faillock.conf "$SALIDA/faillock.conf.original" 2>/dev/null || true
install -m 0644 "$HERE/pam/faillock.conf" /etc/security/faillock.conf
install -m 0644 "$HERE/pam/nimbo-faillock" "$HERE/pam/nimbo-faillock-preauth" /usr/share/pam-configs/
cp -a /etc/pam.d/common-auth "$SALIDA/common-auth.original"
pam-auth-update --package --enable nimbo-faillock nimbo-faillock-preauth
cp -a /etc/pam.d/common-auth "$SALIDA/common-auth.nuevo"

echo ">> DESPUÉS"
lynis audit system --quick --no-colors > "$SALIDA/lynis-despues.txt" 2>&1 || true
set +e
bash "$HERE/verify-hardening.sh" | tee "$SALIDA/verify-despues.txt"
RC=$?
set -e
herramientas > "$SALIDA/herramientas-despues.txt"

{
  echo "# 3B.2 — medición antes/después ($(date -Is))"
  echo
  echo "- lynis, índice de endurecimiento: antes $(indice "$SALIDA/lynis-antes.txt") → después $(indice "$SALIDA/lynis-despues.txt")"
  echo "- verify-hardening: antes $(tail -1 "$SALIDA/verify-antes.txt") · después $(tail -1 "$SALIDA/verify-despues.txt")"
  echo
  echo "## Herramientas de auditoría (después)"
  echo '```'
  cat "$SALIDA/herramientas-despues.txt"
  echo '```'
  echo
  echo "## common-auth después de pam-auth-update"
  echo '```'
  grep -v '^#' "$SALIDA/common-auth.nuevo" | sed '/^$/d'
  echo '```'
  echo
  echo "FALTA A MANO (no se automatiza a propósito), en otra consola (Ctrl+Alt+F3) y con una"
  echo "sesión de root abierta en la primera:"
  echo "  1. 3 contraseñas mal -> 1 bien (entra) -> 2 mal: NO debe bloquear (el acierto pone a cero)."
  echo "  2. 5 mal seguidas: debe BLOQUEAR y decir que la cuenta está bloqueada."
  echo "  3. 'sudo faillock --user <tú>' muestra los fallos; '--reset' desbloquea."
  echo "Anotar el resultado de cada paso aquí."
} | tee "$SALIDA/informe.md"
exit "$RC"
