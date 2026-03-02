#!/usr/bin/env bash
set -u

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$APP_DIR/desktop-launch.log"

{
  echo "===== $(date '+%Y-%m-%d %H:%M:%S') desktop launch ====="
  "$APP_DIR/launch.sh"
} >> "$LOG_FILE" 2>&1
STATUS=$?

if [[ $STATUS -ne 0 ]]; then
  if command -v notify-send >/dev/null 2>&1; then
    notify-send "Whisper launch failed" "See: $LOG_FILE"
  fi
  exit $STATUS
fi
