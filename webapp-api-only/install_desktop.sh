#!/usr/bin/env bash
# Installer for Whisper V1 API (webapp version).
# Copies the app to a stable location, installs a launcher that starts the
# local HTTP server, and creates a desktop menu entry.
# Usage: ./install_desktop.sh          (install)
#        ./install_desktop.sh remove   (uninstall)

set -euo pipefail

INSTALL_DIR="${HOME}/.local/share/whisper-v1-api"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DESKTOP_DIR="${HOME}/.local/share/applications"
PORT="${WHISPER_API_PORT:-8178}"

remove_installation() {
  rm -f "${DESKTOP_DIR}/whisper-v1-api.desktop"
  rm -rf "${INSTALL_DIR}"
  update-desktop-database "${DESKTOP_DIR}" 2>/dev/null || true
  echo "Whisper V1 API removed."
}

if [ "${1:-}" = "remove" ]; then
  remove_installation
  exit 0
fi

# 1. Copy the app files.
mkdir -p "${INSTALL_DIR}"
cp "${APP_DIR}/Whisper-V1-API.html" "${INSTALL_DIR}/"

# 2. Write the launcher (starts the HTTP server if not running, opens browser).
cat > "${INSTALL_DIR}/launch.sh" << LAUNCHER
#!/usr/bin/env bash
set -euo pipefail
PORT="${PORT}"
if ! curl -s "http://127.0.0.1:\${PORT}/Whisper-V1-API.html" >/dev/null 2>&1; then
  nohup python3 -m http.server "\${PORT}" --bind 127.0.0.1 --directory "${INSTALL_DIR}" \\
    > /tmp/whisper-v1-api-server.log 2>&1 &
  sleep 1
fi
xdg-open "http://127.0.0.1:\${PORT}/Whisper-V1-API.html" >/dev/null 2>&1 || true
LAUNCHER
chmod +x "${INSTALL_DIR}/launch.sh"

# 3. Desktop menu entry.
mkdir -p "${DESKTOP_DIR}"
cat > "${DESKTOP_DIR}/whisper-v1-api.desktop" << DESKTOP
[Desktop Entry]
Type=Application
Name=Whisper V1 API
Comment=API-only voice-to-text (Lemonade, OpenRouter, OpenAI, Gemini, LAN)
Exec=${INSTALL_DIR}/launch.sh
Icon=audio-input-microphone
Terminal=false
Categories=Audio;Utility;
DESKTOP
chmod +x "${DESKTOP_DIR}/whisper-v1-api.desktop"
update-desktop-database "${DESKTOP_DIR}" 2>/dev/null || true

echo "Installed Whisper V1 API:"
echo "  App files:  ${INSTALL_DIR}"
echo "  Menu entry: ${DESKTOP_DIR}/whisper-v1-api.desktop"
echo "  Server:     http://127.0.0.1:${PORT}/Whisper-V1-API.html (starts on launch)"
echo ""
echo "Find 'Whisper V1 API' in your application menu, or run:"
echo "  ${INSTALL_DIR}/launch.sh"
