#!/usr/bin/env bash
# verify-hardening.sh — verificación automatizada del endurecimiento (RF-CORE-04, HU-04).
#
# "La verificación automatizada confirma cada ajuste en la ISO y en el sistema instalado."
# Se ejecuta igual en la sesión live y en el sistema instalado (como root o con sudo):
#   sudo bash verify-hardening.sh
#
# Comprueba, sin modificar nada:
#   1. Actualizaciones automáticas deshabilitadas (las cerró 3B.1, hook 0100; aquí solo se
#      VERIFICAN): apt-daily*.timer enmascarados y APT::Periodic::Enable "0".   (HU-04 CA-3)
#   2. Cada parámetro de sysctl de la lista de referencia tiene su valor en ejecución, y el
#      fichero persistente está en /etc/sysctl.d/.
#   3. PAM: pam_faillock (preauth antes de pam_unix, authfail y authsucc) con deny > 0, y
#      SIN pam_pwquality (RF-CORE-03: el instalador sugiere contraseñas fuertes, no obliga).
#
# Salida: una línea OK/FALLO por ajuste y "VEREDICTO: OK — 0 fallos". Código 0 si todo
# está bien, 1 si algo falla.
#
# Variables para las pruebas (pruebas/test-verify-hardening.sh), no para uso normal:
#   NIMBO_RAIZ (prefijo de /etc), NIMBO_SYSCTL, NIMBO_SYSTEMCTL, NIMBO_REF_SYSCTL
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RAIZ="${NIMBO_RAIZ:-}"
SYSCTL="${NIMBO_SYSCTL:-sysctl}"
SYSTEMCTL="${NIMBO_SYSTEMCTL:-systemctl}"
if [ -n "${NIMBO_REF_SYSCTL:-}" ]; then
  REF="$NIMBO_REF_SYSCTL"
elif [ -f "$HERE/sysctl/99-nimbo-hardening.conf" ]; then
  REF="$HERE/sysctl/99-nimbo-hardening.conf"
else
  REF="/usr/share/nimbo/hardening/99-nimbo-hardening.conf"
fi

fallos=0
total=0
ok()    { total=$((total + 1)); echo "OK     $*"; }
fallo() { total=$((total + 1)); fallos=$((fallos + 1)); echo "FALLO $*"; }

[ -f "$REF" ] || { echo "FALLO no se encuentra la lista de referencia $REF"; exit 1; }

# --- 1. Actualizaciones automáticas -----------------------------------------------------
echo "== Actualizaciones automáticas (HU-04 CA-3)"
for unidad in apt-daily.timer apt-daily-upgrade.timer; do
  estado=$("$SYSTEMCTL" is-enabled "$unidad" 2>/dev/null || true)
  if [ "$estado" = "masked" ]; then
    ok "actualizaciones $unidad enmascarado"
  else
    fallo "actualizaciones $unidad está '$estado' (esperado: masked)"
  fi
done
if grep -qsE '^\s*APT::Periodic::Enable\s+"0"' "$RAIZ"/etc/apt/apt.conf.d/*; then
  ok "actualizaciones APT::Periodic::Enable \"0\""
else
  fallo "actualizaciones APT::Periodic::Enable no está a \"0\""
fi

# --- 2. sysctl ----------------------------------------------------------------------------
echo "== Parámetros del kernel (sysctl)"
if [ -f "$RAIZ/etc/sysctl.d/99-nimbo-hardening.conf" ]; then
  ok "sysctl persistente /etc/sysctl.d/99-nimbo-hardening.conf"
else
  fallo "sysctl persistente: falta /etc/sysctl.d/99-nimbo-hardening.conf"
fi
while IFS= read -r linea; do
  linea="${linea%%#*}"
  [ -n "${linea// /}" ] || continue
  clave=$(echo "${linea%%=*}" | tr -d '[:space:]')
  esperado=$(echo "${linea#*=}" | tr -s '[:space:]' ' ' | sed 's/^ //; s/ $//')
  actual=$("$SYSCTL" -n "$clave" 2>/dev/null | tr -s '[:space:]' ' ' | sed 's/^ //; s/ $//')
  if [ "$actual" = "$esperado" ]; then
    ok "sysctl $clave = $esperado"
  else
    fallo "sysctl $clave = '${actual:-<no existe>}' (esperado: $esperado)"
  fi
done < "$REF"

# --- 3. PAM -------------------------------------------------------------------------------
echo "== Autenticación (PAM)"
AUTH="$RAIZ/etc/pam.d/common-auth"
pre=$(grep -nE '^\s*auth\s.*pam_faillock\.so\s+preauth' "$AUTH" 2>/dev/null | head -1 | cut -d: -f1)
unix=$(grep -nE '^\s*auth\s.*pam_unix\.so' "$AUTH" 2>/dev/null | head -1 | cut -d: -f1)
if [ -n "$pre" ] && [ -n "$unix" ] && [ "$pre" -lt "$unix" ]; then
  ok "pam faillock preauth antes de pam_unix"
else
  fallo "pam faillock preauth ausente o después de pam_unix en common-auth"
fi
if grep -qE '^\s*auth\s.*pam_faillock\.so\s+authfail' "$AUTH" 2>/dev/null; then
  ok "pam faillock authfail"
else
  fallo "pam faillock authfail ausente en common-auth"
fi
# authsucc es código muerto con pam-auth-update: el salto de pam_unix al acertar lo omite
# siempre. El contador lo pone a cero la fase account (revisión de #47).
if grep -qE '^\s*auth\s.*pam_faillock\.so\s+authsucc' "$AUTH" 2>/dev/null; then
  fallo "pam faillock authsucc presente en common-auth: no se ejecuta nunca; usar la fase account"
else
  ok "pam faillock authsucc ausente (el contador lo limpia account)"
fi
# account: pam_faillock "required" DESPUÉS de pam_unix (bloque Additional), para que se
# ejecute siempre tras un acierto y ponga el contador a cero.
ACCOUNT="$RAIZ/etc/pam.d/common-account"
unix_acc=$(grep -nE '^\s*account\s.*pam_unix\.so' "$ACCOUNT" 2>/dev/null | head -1 | cut -d: -f1)
fl_acc=$(grep -nE '^\s*account\s+required\s+pam_faillock\.so' "$ACCOUNT" 2>/dev/null | head -1 | cut -d: -f1)
if [ -n "$fl_acc" ] && [ -n "$unix_acc" ] && [ "$fl_acc" -gt "$unix_acc" ]; then
  ok "pam faillock account (required, después de pam_unix: pone a cero el contador)"
else
  fallo "pam faillock account ausente, no 'required' o antes de pam_unix en common-account: el contador no se pone a cero tras un acierto"
fi
FCONF="$RAIZ/etc/security/faillock.conf"
deny=$(sed -n 's/^\s*deny\s*=\s*\([0-9]*\).*/\1/p' "$FCONF" 2>/dev/null | tail -1)
if [ -n "$deny" ] && [ "$deny" -gt 0 ]; then
  ok "pam faillock.conf deny = $deny"
else
  fallo "pam faillock.conf deny = '${deny:-<sin definir>}' (esperado > 0)"
fi
if grep -qE '^\s*silent\s*$' "$FCONF" 2>/dev/null; then
  fallo "pam faillock.conf silent: oculta 'cuenta bloqueada' a la persona (mensajes honestos, ADR-009)"
else
  ok "pam faillock.conf sin silent (la persona ve que la cuenta está bloqueada)"
fi
if grep -qsE '^\s*password\s.*pam_pwquality\.so' "$RAIZ/etc/pam.d/common-password"; then
  fallo "pam pwquality activo en common-password: obliga contraseñas fuertes (RF-CORE-03 pide sugerir, no obligar)"
else
  ok "pam pwquality no obliga (RF-CORE-03)"
fi

echo
if [ "$fallos" -eq 0 ]; then
  echo "VEREDICTO: OK — 0 fallos ($total comprobaciones)"
  exit 0
fi
echo "VEREDICTO: FALLO — $fallos de $total comprobaciones"
exit 1
