#!/usr/bin/env bash
set -Eeuo pipefail
ENGINE_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
PYTHON="$(command -v python3.11 || true)"
[[ -n "$PYTHON" ]] || { echo 'Se necesita Python 3.11.' >&2; exit 2; }
exec "$PYTHON" "$ENGINE_DIR/engine.py" stop
