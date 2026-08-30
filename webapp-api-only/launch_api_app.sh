#!/usr/bin/env bash
# Serve Whisper-V1-API.html over local HTTP so browser CORS works with Lemonade.
# (Lemonade rejects Origin: null from file:// pages but accepts http origins.)

set -euo pipefail
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${WHISPER_API_PORT:-8178}"

if ! curl -s "http://127.0.0.1:${PORT}/Whisper-V1-API.html" >/dev/null 2>&1; then
  nohup python3 -m http.server "${PORT}" --bind 127.0.0.1 --directory "${APP_DIR}" \
    > /tmp/whisper-api-server.log 2>&1 &
  sleep 1
fi

xdg-open "http://127.0.0.1:${PORT}/Whisper-V1-API.html" >/dev/null 2>&1 || true
echo "Whisper V1 API opened at http://127.0.0.1:${PORT}/Whisper-V1-API.html"
