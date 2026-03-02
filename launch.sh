#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$APP_DIR/.venv"

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  "$APP_DIR/install.sh"
fi

exec "$VENV_DIR/bin/python" "$APP_DIR/app.py"
