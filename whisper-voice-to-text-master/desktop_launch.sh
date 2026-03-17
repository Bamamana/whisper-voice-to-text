#!/usr/bin/env bash
set -u

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="$APP_DIR/desktop-launch.log"
PROFILE_FILE="$APP_DIR/.whisper-profile.env"

CURRENT_PROFILE="auto"
if [[ -f "$PROFILE_FILE" ]]; then
  while IFS='=' read -r key value; do
    if [[ "$key" == "WHISPER_ACCELERATOR" ]]; then
      CURRENT_PROFILE="${value,,}"
      break
    fi
  done < "$PROFILE_FILE"
fi

SELECTED_PROFILE="$(python3 "$APP_DIR/choose_profile.py" "$CURRENT_PROFILE" 2>>"$LOG_FILE")"
CHOOSER_STATUS=$?

if [[ $CHOOSER_STATUS -ne 0 || -z "$SELECTED_PROFILE" ]]; then
  exit 0
fi

{
  echo "===== $(date '+%Y-%m-%d %H:%M:%S') desktop launch ====="
  echo "Current profile: $CURRENT_PROFILE"
  echo "Selected profile: $SELECTED_PROFILE"
  if [[ "$SELECTED_PROFILE" != "$CURRENT_PROFILE" ]]; then
    echo "Rebuilding environment for profile: $SELECTED_PROFILE"
    "$APP_DIR/install.sh" "$SELECTED_PROFILE"
  fi
  "$APP_DIR/launch.sh"
} >> "$LOG_FILE" 2>&1
STATUS=$?

if [[ $STATUS -ne 0 ]]; then
  if command -v notify-send >/dev/null 2>&1; then
    notify-send "Whisper launch failed" "See: $LOG_FILE"
  fi
  exit $STATUS
fi
