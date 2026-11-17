#!/usr/bin/env bash
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"
python3 -m unittest discover -s release/tests -v
python3 -m unittest discover -s apt-repo/tests -v
