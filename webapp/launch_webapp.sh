#!/usr/bin/env bash
# Launch Whisper V1 webapp: starts the local bridge (for local whisper models)
# and opens the app in the default browser.

set -euo pipefail
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${WHISPER_BRIDGE_PORT:-8177}"

# Start the bridge in the background (only needed for the Local Whisper backend,
# but harmless to always run).
if ! curl -s "http://127.0.0.1:${PORT}/models" >/dev/null 2>&1; then
  if [ -x "${APP_DIR}/.venv/bin/python" ]; then
    PY="${APP_DIR}/.venv/bin/python"
  else
    PY="python3"
  fi
  nohup "${PY}" "${APP_DIR}/webapp/bridge_server.py" --port "${PORT}" \
    > /tmp/whisper-bridge.log 2>&1 &
  echo "Bridge starting on port ${PORT} (log: /tmp/whisper-bridge.log)"
fi

sleep 1
xdg-open "http://127.0.0.1:${PORT}/" >/dev/null 2>&1 || true
echo "Whisper V1 opened in your browser."
