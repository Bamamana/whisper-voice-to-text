#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DESKTOP_FILE="$HOME/Desktop/Whisper-Voice-To-Text.desktop"
APPLICATIONS_DIR="$HOME/.local/share/applications"
APPLICATIONS_FILE="$APPLICATIONS_DIR/Whisper-Voice-To-Text.desktop"

mkdir -p "$APPLICATIONS_DIR"

write_launcher() {
	local target_file="$1"

	cat > "$target_file" <<EOF
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
}

write_launcher "$DESKTOP_FILE"
write_launcher "$APPLICATIONS_FILE"

chmod +x "$DESKTOP_FILE"
chmod +x "$APPLICATIONS_FILE"

echo "Desktop shortcut created at: $DESKTOP_FILE"
echo "Applications menu entry created at: $APPLICATIONS_FILE"
