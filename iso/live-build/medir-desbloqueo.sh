#!/usr/bin/env bash
# medir-desbloqueo.sh — mide N desbloqueos LUKS del disco instalado con la clave de PRUEBA.
#
# HOST-SIDE y SOLO DE PRUEBA: no va en la ISO. Arranca el disco con install-in-qemu.sh
# (sin pantalla, con monitor), detecta el prompt de la contraseña en la pantalla emulada,
# teclea la clave GENERADA para la prueba (.clave-prueba-luks, ignorada por git) con
# `sendkey` —teclas físicas, así que el teclado del initrd es el que decide qué carácter
# llega— y clasifica el resultado: greeter (desbloqueó) o no. Apaga limpio y repite.
#
# Sirve para dos mediciones del Paso 4 / H-002:
#   - carrera teclado/prompt: teclear en cuanto aparece el prompt (--retardo 0), N veces;
#   - RAM mínima para desbloquear: --ram 1024, 768, 512…
#
# Requisito: la clave de prueba añadida como keyslot en ESE disco (ver README del arnés).
# La clave nunca se imprime ni se guarda en la evidencia.
#
# Uso: ./medir-desbloqueo.sh [--veces N] [--ram MiB] [--retardo S] [-- args de install-in-qemu]
#      por defecto: --veces 10 --ram 2048 --retardo 0 -- --secure-boot --tpm
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VECES=10; RAM=2048; RETARDO=0
ARGS=(--secure-boot --tpm)
while [ $# -gt 0 ]; do
    case "$1" in
        --veces)   VECES="$2"; shift 2 ;;
        --ram)     RAM="$2"; shift 2 ;;
        --retardo) RETARDO="$2"; shift 2 ;;
        --) shift; ARGS=("$@"); break ;;
        *) sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;;
    esac
done

CLAVE_F="$HERE/.clave-prueba-luks"
[ -s "$CLAVE_F" ] || { echo "ERROR: falta $CLAVE_F (clave de prueba)."; exit 1; }
command -v magick >/dev/null || { echo "ERROR: falta ImageMagick (magick)."; exit 1; }
command -v socat >/dev/null || { echo "ERROR: falta socat."; exit 1; }

OUT="$HERE/medicion-desbloqueo-$(date +%Y%m%dT%H%M%S)-ram$RAM-r$RETARDO"
mkdir -p "$OUT"
CSV="$OUT/resultados.csv"
echo "n,ram_mib,retardo_s,t_prompt_s,resultado,t_hasta_resultado_s,captura" > "$CSV"
M="${XDG_RUNTIME_DIR:-/tmp}/nimbo-medir-$$.sock"

ms() { echo $(( $(date +%s%N) / 1000000 )); }
gt() { awk -v a="$1" -v b="$2" 'BEGIN{exit !(a>b)}'; }   # a > b con decimales, sin bc
seg() { awk -v m="$1" 'BEGIN{printf "%.1f", m/1000}'; }
mon() { printf '%s\n' "$1" | socat - "UNIX-CONNECT:$M" >/dev/null 2>&1 || true; }
frame() { rm -f "$OUT/.f.ppm"; mon "screendump $OUT/.f.ppm"; local i; for i in 1 2 3 4 5 6 7 8 9 10; do [ -s "$OUT/.f.ppm" ] && return 0; sleep 0.05; done; return 1; }
# Métricas de la pantalla: media global, dominancia de azul (menú de GRUB) y media de la
# franja superior (donde aparece el prompt de systemd-cryptsetup).
metricas() { magick "$OUT/.f.ppm" -format '%[fx:mean] %[fx:mean.b-mean.r] ' info: 2>/dev/null; magick "$OUT/.f.ppm" -crop 100%x24+0+0 +repage -format '%[fx:mean]\n' info: 2>/dev/null; }

# Clave → teclas físicas, con el initrd en distribución ESPAÑOLA: si el initrd tuviera
# la de EE. UU., estas mismas teclas producirían otros caracteres y el desbloqueo fallaría.
teclear_clave() {
    local clave c k i
    clave="$(cat "$CLAVE_F")"
    for ((i = 0; i < ${#clave}; i++)); do
        c="${clave:$i:1}"
        case "$c" in
            [a-z0-9]) k="$c" ;;
            [A-Z])    k="shift-${c,,}" ;;
            -)        k="slash" ;;          # ES: '-' está en la tecla del '/' de EE. UU.
            /)        k="shift-7" ;;        # ES: '/' es Mayús+7
            ñ)        k="semicolon" ;;      # ES: 'ñ' está en la tecla del ';' de EE. UU.
            Ñ)        k="shift-semicolon" ;;
            *) echo "ERROR: carácter no soportado en la clave de prueba"; exit 1 ;;
        esac
        mon "sendkey $k"; sleep 0.04
    done
    mon "sendkey ret"
}

echo ">> Medición: $VECES arranques · RAM ${RAM} MiB · retardo ${RETARDO}s · args: ${ARGS[*]}"
echo ">> Resultados: $OUT"
for n in $(seq 1 "$VECES"); do
    rm -f "$M"
    NIMBO_QEMU_DISPLAY=none NIMBO_QEMU_MONITOR="$M" NIMBO_VM_MB_INST="$RAM" \
        "$HERE/install-in-qemu.sh" "${ARGS[@]}" arrancar > "$OUT/arranque-$n.log" 2>&1 &
    QPID=$!
    for _ in $(seq 1 100); do [ -S "$M" ] && break; sleep 0.1; done
    t0=$(ms); grub_visto=0; t_prompt=""; resultado="sin-prompt"; t_res=""
    # 1) Esperar el prompt (máx. 90 s); Intro en el menú de GRUB para no esperar su cuenta.
    while :; do
        el=$(( $(ms) - t0 ))
        [ "$el" -gt 90000 ] && break
        kill -0 "$QPID" 2>/dev/null || { resultado="qemu-terminó"; break; }
        frame || { sleep 0.2; continue; }
        read -r media azul franja < <(metricas)
        if gt "$azul" 0.3; then
            [ "$grub_visto" = 0 ] && { mon "sendkey ret"; grub_visto=1; }
        elif [ "$grub_visto" = 1 ] && gt "$franja" 0.008 && gt 0.01 "$azul"; then
            t_prompt=$(seg "$el"); break
        fi
        sleep 0.2
    done
    if [ -n "$t_prompt" ]; then
        cp "$OUT/.f.ppm" "$OUT/prompt-$n.ppm"
        sleep "$RETARDO"
        t1=$(ms)
        teclear_clave
        # 2) Resultado (máx. 120 s): el greeter gráfico tiene mucha más luz que la consola.
        resultado="no-desbloqueó"
        while :; do
            el=$(( $(ms) - t1 ))
            [ "$el" -gt 120000 ] && break
            kill -0 "$QPID" 2>/dev/null || { resultado="qemu-terminó"; break; }
            sleep 1
            frame || continue
            read -r media azul franja < <(metricas)
            if gt "$media" 0.05; then resultado="desbloqueó"; break; fi
        done
        t_res=$(seg "$el")
    fi
    cap="$OUT/final-$n.png"; frame && magick "$OUT/.f.ppm" "$cap" 2>/dev/null || cap=""
    [ -f "$OUT/prompt-$n.ppm" ] && magick "$OUT/prompt-$n.ppm" "$OUT/prompt-$n.png" && rm -f "$OUT/prompt-$n.ppm"
    echo "$n,$RAM,$RETARDO,${t_prompt:-},$resultado,${t_res:-},$(basename "${cap:-}")" >> "$CSV"
    printf '   arranque %2d: prompt a %5ss · %-14s · %ss\n' "$n" "${t_prompt:--}" "$resultado" "${t_res:--}"
    # 3) Apagado: limpio si desbloqueó (ACPI → el sistema se apaga), forzado si no (initrd).
    if [ "$resultado" = "desbloqueó" ]; then
        sleep 5; mon "system_powerdown"
        for _ in $(seq 1 90); do kill -0 "$QPID" 2>/dev/null || break; sleep 1; done
    fi
    mon "quit"; wait "$QPID" 2>/dev/null || true
done
rm -f "$OUT/.f.ppm" "$M"
echo
echo ">> Resumen ($CSV):"
cut -d, -f5 "$CSV" | tail -n +2 | sort | uniq -c
