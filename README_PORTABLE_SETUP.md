# Whisper Voice To Text (Portable Folder)

This folder is a portable copy of your Whisper desktop app.

## Included files
- `app.py` - GUI app (file transcription + microphone recording)
- `install.sh` - Linux installer (installs system + Python deps)
- `launch.sh` - Linux launcher
- `desktop_launch.sh` - Desktop-safe launcher wrapper (logs failures to `desktop-launch.log`)
- `Whisper-Voice-To-Text.desktop` - Original desktop entry example
- `make_desktop_shortcut.sh` - Rebuilds a correct desktop icon path on a new Linux machine
- `download_models.py` - Pre-download Whisper models into local cache for instant switching
- `windows_launch.bat` - Windows launcher template
- `WINDOWS_NOTES.md` - What to change for Windows

## Move to another Linux computer
1. Copy this whole folder to the new computer.
2. Open terminal in this folder.
3. Run:
   ```bash
   chmod +x install.sh launch.sh make_desktop_shortcut.sh
   ./install.sh
   ./make_desktop_shortcut.sh
   ```
4. Double-click the desktop icon `Whisper-Voice-To-Text.desktop`.

## Notes
- Models are cached in `model-cache/`.
- To pre-download all models (tiny/base/small/medium/large-v3), run:
   ```bash
   ./.venv/bin/python download_models.py
   ```
- To pre-download specific models only, run:
   ```bash
   ./.venv/bin/python download_models.py small medium large-v3
   ```
- If desktop asks to trust launcher, choose **Trust and Launch**.
- Transcripts are saved next to the source file as `*.whisper.txt`.
