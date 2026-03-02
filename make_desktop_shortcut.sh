#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_FILE="$HOME/Desktop/Whisper-Voice-To-Text.desktop"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Whisper Voice To Text
Comment=Transcribe audio/video and microphone speech locally
Exec=/usr/bin/env bash "$APP_DIR/desktop_launch.sh"
Path=$APP_DIR
Icon=audio-input-microphone
Terminal=false
Categories=AudioVideo;Utility;
EOF

chmod +x "$DESKTOP_FILE"
echo "Desktop shortcut created at: $DESKTOP_FILE"
