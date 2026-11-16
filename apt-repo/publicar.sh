#!/usr/bin/env bash
# Genera el sitio local sin firma; no despliega ni usa claves privadas.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$HERE/aptrepo.py" preparar "$@"
