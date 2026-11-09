#!/usr/bin/env bash
# test-verify-hardening.sh — prueba de verify-hardening.sh (RF-CORE-04) sin tocar el sistema.
#
# Monta una raíz falsa con el endurecimiento correcto y sustituye `sysctl` y `systemctl`
# por dobles que leen valores de ficheros. Comprueba que el verificador:
#   - pasa (código 0) con todo bien;
#   - FALLA (código 1) y nombra el ajuste cuando se rompe cada uno de ellos.
# Uso:  bash security/hardening/3b2/pruebas/test-verify-hardening.sh
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE="$(cd "$HERE/.." && pwd)"
VERIF="$BASE/verify-hardening.sh"
fallos=0

preparar() {  # crea una raíz falsa correcta en $T
  T=$(mktemp -d)
  mkdir -p "$T/root/etc/apt/apt.conf.d" "$T/root/etc/sysctl.d" "$T/root/etc/pam.d" \
           "$T/root/etc/security" "$T/bin"
  printf 'APT::Periodic::Enable "0";\n' > "$T/root/etc/apt/apt.conf.d/99nimbo-no-telemetry"
  cp "$BASE/sysctl/99-nimbo-hardening.conf" "$T/root/etc/sysctl.d/"
  cp "$BASE/pam/faillock.conf" "$T/root/etc/security/faillock.conf"
  cat > "$T/root/etc/pam.d/common-auth" <<'PAM'
auth	requisite			pam_faillock.so preauth
auth	[success=1 default=ignore]	pam_unix.so nullok
auth	[default=die]			pam_faillock.so authfail
auth	sufficient			pam_faillock.so authsucc
auth	requisite			pam_deny.so
auth	required			pam_permit.so
PAM
  printf 'password\t[success=1 default=ignore]\tpam_unix.so obscure yescrypt\n' \
    > "$T/root/etc/pam.d/common-password"
  # Valores "en ejecución" = los de referencia
  grep -vE '^\s*(#|$)' "$BASE/sysctl/99-nimbo-hardening.conf" | sed 's/ *= */=/' > "$T/valores"
  printf 'apt-daily.timer=masked\napt-daily-upgrade.timer=masked\n' > "$T/unidades"
  cat > "$T/bin/sysctl" <<'EOF2'
#!/usr/bin/env bash
# doble de sysctl: "sysctl -n clave"
v=$(grep -m1 "^$2=" "$VALORES" | cut -d= -f2-)
[ -n "$v" ] || { echo "sysctl: cannot stat $2" >&2; exit 255; }
echo "$v"
EOF2
  cat > "$T/bin/systemctl" <<'EOF2'
#!/usr/bin/env bash
# doble de systemctl: "systemctl is-enabled unidad"
v=$(grep -m1 "^$2=" "$UNIDADES" | cut -d= -f2-)
echo "${v:-enabled}"
EOF2
  chmod +x "$T/bin/sysctl" "$T/bin/systemctl"
}

correr() {  # ejecuta el verificador contra $T; deja la salida en $SALIDA y el código en $RC
  SALIDA=$(VALORES="$T/valores" UNIDADES="$T/unidades" NIMBO_RAIZ="$T/root" \
           NIMBO_SYSCTL="$T/bin/sysctl" NIMBO_SYSTEMCTL="$T/bin/systemctl" \
           bash "$VERIF" 2>&1)
  RC=$?
}

caso() {  # caso <nombre> <código esperado> <texto esperado en la salida>
  if [ "$RC" -eq "$2" ] && grep -qF -- "$3" <<<"$SALIDA"; then
    echo "  ok   $1"
  else
    echo "  MAL  $1 (código $RC, esperado $2; buscaba: $3)"
    echo "$SALIDA" | sed 's/^/       | /'
    fallos=$((fallos + 1))
  fi
  rm -rf "$T"
}

echo "test-verify-hardening:"

preparar; correr; caso "todo endurecido pasa" 0 "VEREDICTO: OK"

preparar; sed -i 's/^kernel.kptr_restrict=.*/kernel.kptr_restrict=0/' "$T/valores"; correr
caso "kptr_restrict en 0 falla" 1 "FALLO sysctl kernel.kptr_restrict"

preparar; rm "$T/root/etc/sysctl.d/99-nimbo-hardening.conf"; correr
caso "sin el fichero persistente falla" 1 "FALLO sysctl persistente"

preparar; sed -i 's/^apt-daily.timer=.*/apt-daily.timer=enabled/' "$T/unidades"; correr
caso "apt-daily.timer sin enmascarar falla" 1 "FALLO actualizaciones apt-daily.timer"

preparar; : > "$T/root/etc/apt/apt.conf.d/99nimbo-no-telemetry"; correr
caso "APT::Periodic activo falla" 1 "FALLO actualizaciones APT::Periodic"

preparar; sed -i '/preauth/d' "$T/root/etc/pam.d/common-auth"; correr
caso "sin faillock preauth falla" 1 "FALLO pam faillock preauth"

preparar; sed -i '1{h;d};2{G}' "$T/root/etc/pam.d/common-auth"; correr
caso "faillock preauth después de pam_unix falla" 1 "FALLO pam faillock preauth"

preparar; sed -i 's/^deny = .*/deny = 0/' "$T/root/etc/security/faillock.conf"; correr
caso "faillock deny desactivado falla" 1 "FALLO pam faillock.conf deny"

preparar; printf 'password\trequisite\tpam_pwquality.so retry=3\n' >> "$T/root/etc/pam.d/common-password"; correr
caso "pam_pwquality obligatorio falla (RF-CORE-03)" 1 "FALLO pam pwquality"

echo
if [ "$fallos" -eq 0 ]; then echo "RESULTADO: 9/9 casos OK"; exit 0; fi
echo "RESULTADO: $fallos casos MAL"
exit 1
