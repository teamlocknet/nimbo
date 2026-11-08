#!/usr/bin/env bash
# ci-espejo.sh — arranca el espejo parcial del snapshot en un runner de CI y resume su uso (ADR-016).
#
#   ci-espejo.sh arrancar   lanza espejo.py en segundo plano (127.0.0.1:$PUERTO) y espera a que escuche
#   ci-espejo.sh resumen    cuenta CACHE/DESCARGA/ERROR del registro, lo escribe en el summary
#                           y deja `descargas=N` en $GITHUB_OUTPUT (la CI guarda caché solo si N > 0)
#
# Variables: NIMBO_ESPEJO_DIR (por defecto ~/.cache/nimbo-espejo), NIMBO_ESPEJO_PUERTO (8765).
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIR="${NIMBO_ESPEJO_DIR:-$HOME/.cache/nimbo-espejo}"
PUERTO="${NIMBO_ESPEJO_PUERTO:-8765}"
TMPD="${RUNNER_TEMP:-/tmp}"
REGISTRO="$TMPD/espejo.registro"
SALIDA="$TMPD/espejo.salida"

case "${1:-}" in
    arrancar)
        : > "$REGISTRO"
        nohup python3 -I "$HERE/espejo.py" --dir "$DIR" --puerto "$PUERTO" \
            --registro "$REGISTRO" > "$SALIDA" 2>&1 &
        for _ in $(seq 1 30); do
            if (exec 3<>"/dev/tcp/127.0.0.1/$PUERTO") 2>/dev/null; then
                cat "$SALIDA"
                echo ">> caché restaurada: $(find "$DIR" -type f 2>/dev/null | wc -l) ficheros, $(du -sh "$DIR" 2>/dev/null | cut -f1)"
                exit 0
            fi
            sleep 1
        done
        echo "::error::el espejo no arrancó en 30 s"; cat "$SALIDA"; exit 1
        ;;
    resumen)
        contar() { grep -c "^$1 " "$REGISTRO" 2>/dev/null || true; }
        cache="$(contar CACHE)"; desc="$(contar DESCARGA)"; err="$(contar ERROR)"
        nof="$(contar NO-ENCONTRADO)"; rech="$(contar RECHAZADA)"
        echo ">> espejo: ${cache:-0} de caché · ${desc:-0} descargados del snapshot · ${err:-0} errores · ${nof:-0} no encontrados · ${rech:-0} rechazados"
        grep "^ERROR " "$REGISTRO" 2>/dev/null | head -20 || true
        echo "descargas=${desc:-0}" >> "${GITHUB_OUTPUT:-/dev/null}"
        {
            echo "### Espejo del snapshot (ADR-016)"
            echo ""
            echo "- servidos de caché: **${cache:-0}** · descargados del snapshot: **${desc:-0}** · errores: **${err:-0}**"
            echo "- tamaño del espejo: $(du -sh "$DIR" 2>/dev/null | cut -f1)"
        } >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
        ;;
    *)
        echo "uso: $0 arrancar|resumen" >&2; exit 2 ;;
esac
