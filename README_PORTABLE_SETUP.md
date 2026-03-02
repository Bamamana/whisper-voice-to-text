# Whisper Voice To Text (Portable Folder)

This folder is a portable copy of your Whisper desktop app.

## Included files
- `app.py` - GUI app (file transcription + microphone recording)
- `install.sh` - Linux installer (installs system + Python deps)
- `launch.sh` - Linux launcher
- `Whisper-Voice-To-Text.desktop` - Original desktop entry example
- `make_desktop_shortcut.sh` - Rebuilds a correct desktop icon path on a new Linux machine
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
- First run may download the selected model.
- If desktop asks to trust launcher, choose **Trust and Launch**.
- Transcripts are saved next to the source file as `*.whisper.txt`.
