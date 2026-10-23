# lib-qemu.sh — utilidades HOST-SIDE compartidas por los arneses de QEMU (Paso 3C.1+).
#
# Se carga con `. lib-qemu.sh` desde install-in-qemu.sh. NO se hornea en la ISO y NO es
# una dependencia del producto: el firmware OVMF solo existe en el ANFITRIÓN que
# verifica, para emular un PC UEFI. El sistema nimbo arranca con el firmware de la
# máquina real.
#
# Dos piezas:
#
#   nimbo_ovmf_resolver   OVMF SIN Secure Boot, del propio host. Sin rutas fijas:
#       1) OVMF_CODE / OVMF_VARS del entorno, si vienen;
#       2) los descriptores estándar de QEMU (/etc/qemu/firmware, /usr/share/qemu/firmware:
#          *.json, especificación docs/interop/firmware.json de QEMU), que traen Arch,
#          Fedora y Debian. Se elige el de mayor prioridad (orden de nombre) que sea UEFI
#          x86_64 para q35, flash RAW con plantilla de NVRAM y SIN secure-boot/SMM;
#       3) una lista de rutas conocidas (Arch, Fedora, Debian/Ubuntu) como último recurso.
#
#   nimbo_ovmf_secboot    OVMF CON Secure Boot y las llaves de Microsoft inscritas, para
#       que shim (firmado por la CA UEFI de Microsoft) se valide de verdad. Se usa el par
#       OVMF_CODE_4M.secboot.fd + OVMF_VARS_4M.ms.fd de DEBIAN BOOKWORM, sacado del paquete
#       `ovmf` del MISMO snapshot anclado que la ISO (snapshot.env, ADR-004), con SHA-256
#       fijado. Motivo: es el firmware de la distro objetivo y entra en la cadena de
#       anclaje; Arch no publica VARS con llaves inscritas (su descriptor secure-4m no
#       declara "enrolled-keys") y las VARS vacías dejan el firmware en Setup Mode, donde
#       Secure Boot no exige nada. Caché en .cache-ovmf/ (ignorada por git).

NIMBO_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

_nimbo_find_first() { for f in "$@"; do [ -r "$f" ] && { printf '%s\n' "$f"; return 0; }; done; return 1; }

# Imprime "CODE<TAB>VARS" del primer descriptor apto, o nada.
_nimbo_ovmf_por_descriptor() {
    local dirs=() d
    for d in /etc/qemu/firmware /usr/share/qemu/firmware; do [ -d "$d" ] && dirs+=("$d"); done
    [ "${#dirs[@]}" -gt 0 ] || return 1
    # Prioridad según la especificación: orden léxico del NOMBRE de fichero; /etc tapa a
    # /usr/share si el nombre coincide.
    local files; files="$(for d in "${dirs[@]}"; do ls "$d"/*.json 2>/dev/null; done \
        | awk -F/ '{print $NF"\t"$0}' | LC_ALL=C sort -t"$(printf '\t')" -k1,1 -u | cut -f2)"
    [ -n "$files" ] || return 1
    local f
    if command -v jq >/dev/null; then
        while IFS= read -r f; do
            jq -r '
                select((."interface-types" | index("uefi"))
                  and any(.targets[]; .architecture == "x86_64"
                          and any(.machines[]; test("q35")))
                  and .mapping.device == "flash"
                  and .mapping.executable.format == "raw"
                  and (.mapping["nvram-template"].filename != null)
                  and ((.features | index("secure-boot")) | not)
                  and ((.features | index("requires-smm")) | not))
                | "\(.mapping.executable.filename)\t\(.mapping["nvram-template"].filename)"
            ' "$f" 2>/dev/null
        done <<< "$files" | while IFS="$(printf '\t')" read -r c v; do
            [ -r "$c" ] && [ -r "$v" ] && { printf '%s\t%s\n' "$c" "$v"; break; }
        done
    elif command -v python3 >/dev/null; then
        python3 -I - "$files" <<'PY'
import json, os, sys
for f in sys.argv[1].splitlines():
    try:
        d = json.load(open(f))
    except Exception:
        continue
    m = d.get("mapping", {}); feats = d.get("features", [])
    ok = ("uefi" in d.get("interface-types", [])
          and any(t.get("architecture") == "x86_64" and any("q35" in x for x in t.get("machines", []))
                  for t in d.get("targets", []))
          and m.get("device") == "flash"
          and m.get("executable", {}).get("format") == "raw"
          and m.get("nvram-template", {}).get("filename")
          and "secure-boot" not in feats and "requires-smm" not in feats)
    if ok:
        c, v = m["executable"]["filename"], m["nvram-template"]["filename"]
        if os.access(c, os.R_OK) and os.access(v, os.R_OK):
            print(f"{c}\t{v}"); break
PY
    else
        return 1
    fi
}

# Exporta OVMF_CODE y OVMF_VARS_TPL (OVMF sin Secure Boot) y OVMF_ORIGEN (de dónde salió).
nimbo_ovmf_resolver() {
    if [ -n "${OVMF_CODE:-}" ] && [ -n "${OVMF_VARS:-}" ]; then
        OVMF_VARS_TPL="$OVMF_VARS"; OVMF_ORIGEN="entorno (OVMF_CODE/OVMF_VARS)"; return 0
    fi
    local par
    par="$(_nimbo_ovmf_por_descriptor || true)"
    if [ -n "$par" ]; then
        OVMF_CODE="${par%%$'\t'*}"; OVMF_VARS_TPL="${par#*$'\t'}"
        OVMF_ORIGEN="descriptor de firmware de QEMU"; return 0
    fi
    # Último recurso: rutas conocidas. Arch (edk2-ovmf), Fedora (edk2-ovmf), Debian/Ubuntu (ovmf).
    OVMF_CODE="$(_nimbo_find_first /usr/share/edk2/x64/OVMF_CODE.4m.fd /usr/share/edk2/ovmf/OVMF_CODE.fd \
        /usr/share/OVMF/OVMF_CODE_4M.fd /usr/share/OVMF/OVMF_CODE.fd || true)"
    OVMF_VARS_TPL="$(_nimbo_find_first /usr/share/edk2/x64/OVMF_VARS.4m.fd /usr/share/edk2/ovmf/OVMF_VARS.fd \
        /usr/share/OVMF/OVMF_VARS_4M.fd /usr/share/OVMF/OVMF_VARS.fd || true)"
    OVMF_ORIGEN="rutas conocidas"
    [ -n "$OVMF_CODE" ] && [ -n "$OVMF_VARS_TPL" ]
}

# --- Secure Boot: par de Debian bookworm, anclado -------------------------------------
# Paquete y hashes del snapshot 20260901T000000Z. El SHA-256 del .deb es el del índice
# Packages del snapshot (firmado vía Release); los de los .fd se fijan para detectar
# cualquier cambio en la extracción. Si se sube el snapshot, hay que actualizar los tres.
NIMBO_OVMF_DEB="pool/main/e/edk2/ovmf_2022.11-6+deb12u2_all.deb"
NIMBO_OVMF_DEB_SHA256="e73d3d1a8799f7f6fc16b73501d913edcdd86237556fbff30693e747e6dc262e"
NIMBO_OVMF_SB_CODE_SHA256="d50189a486d22af418198226a3a5bcb6ddac775590f6a808bd629474ee034d62"
NIMBO_OVMF_SB_VARS_SHA256="e6044c5d1fd81998a5967d907ec425e48da534832c7d9b0b4c7a702b62019c50"

_nimbo_sha_ok() { [ "$(sha256sum "$1" 2>/dev/null | cut -d' ' -f1)" = "$2" ]; }

# Exporta OVMF_CODE y OVMF_VARS_TPL con el par Secure Boot + llaves MS de Debian.
nimbo_ovmf_secboot() {
    local cache="$NIMBO_LIB_DIR/.cache-ovmf"
    local code="$cache/OVMF_CODE_4M.secboot.fd" vars="$cache/OVMF_VARS_4M.ms.fd"
    if _nimbo_sha_ok "$code" "$NIMBO_OVMF_SB_CODE_SHA256" && _nimbo_sha_ok "$vars" "$NIMBO_OVMF_SB_VARS_SHA256"; then
        OVMF_CODE="$code"; OVMF_VARS_TPL="$vars"; OVMF_ORIGEN="Debian bookworm ovmf (snapshot, caché verificada)"; return 0
    fi
    command -v curl >/dev/null || { echo "ERROR: falta curl para descargar el OVMF de Debian"; return 1; }
    command -v bsdtar >/dev/null || { echo "ERROR: falta bsdtar (libarchive) para extraer el .deb"; return 1; }
    # shellcheck source=snapshot.env
    . "$NIMBO_LIB_DIR/snapshot.env"
    local url="https://snapshot.debian.org/archive/debian/${NIMBO_SNAPSHOT}/${NIMBO_OVMF_DEB}"
    local deb="$cache/$(basename "$NIMBO_OVMF_DEB")"
    mkdir -p "$cache"
    if ! _nimbo_sha_ok "$deb" "$NIMBO_OVMF_DEB_SHA256"; then
        echo ">> Descargando OVMF de Debian (host-side, NO va en la ISO): $url"
        curl -fsSL --retry 5 -o "$deb.part" "$url" || { echo "ERROR: no pude descargar $url"; return 1; }
        mv "$deb.part" "$deb"
    fi
    if ! _nimbo_sha_ok "$deb" "$NIMBO_OVMF_DEB_SHA256"; then
        echo "ERROR: SHA-256 del .deb de OVMF no coincide con el fijado:"
        echo "   esperado : $NIMBO_OVMF_DEB_SHA256"
        echo "   obtenido : $(sha256sum "$deb" | cut -d' ' -f1)"
        rm -f "$deb"; return 1
    fi
    local tmp; tmp="$(mktemp -d "${TMPDIR:-/tmp}/nimbo-ovmf.XXXXXX")"
    bsdtar -xOf "$deb" 'data.tar.*' | bsdtar -xf - -C "$tmp" \
        ./usr/share/OVMF/OVMF_CODE_4M.secboot.fd ./usr/share/OVMF/OVMF_VARS_4M.ms.fd
    cp "$tmp/usr/share/OVMF/OVMF_CODE_4M.secboot.fd" "$code"
    cp "$tmp/usr/share/OVMF/OVMF_VARS_4M.ms.fd" "$vars"
    rm -rf "$tmp"
    if ! _nimbo_sha_ok "$code" "$NIMBO_OVMF_SB_CODE_SHA256" || ! _nimbo_sha_ok "$vars" "$NIMBO_OVMF_SB_VARS_SHA256"; then
        echo "ERROR: los .fd extraídos no coinciden con los SHA-256 fijados"; rm -f "$code" "$vars"; return 1
    fi
    OVMF_CODE="$code"; OVMF_VARS_TPL="$vars"; OVMF_ORIGEN="Debian bookworm ovmf (snapshot $NIMBO_SNAPSHOT, SHA-256 verificado)"
}
