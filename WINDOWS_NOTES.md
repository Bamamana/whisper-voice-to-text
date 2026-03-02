# Windows Notes (What to Change)

This project was built on Linux. To run on Windows, use the same `app.py` but adjust setup/launch.

## 1) Install prerequisites on Windows
- Python 3.11+ (from python.org)
- FFmpeg (add to PATH)
- Visual C++ Redistributable (usually required by Python packages)

## 2) Create virtual environment
From Command Prompt in this folder:
```bat
py -m venv .venv
.venv\Scripts\python -m pip install --upgrade pip wheel setuptools
.venv\Scripts\pip install faster-whisper sounddevice
```

## 3) Launch app
```bat
windows_launch.bat
```

## 4) Desktop icon on Windows
- Right-click `windows_launch.bat` > Send to > Desktop (create shortcut)
- Optional: rename shortcut to "Whisper Voice To Text"

## 5) If microphone does not work
- Check Windows microphone privacy permissions.
- Confirm default recording device is set.
- Restart app after granting mic access.

## 6) If FFmpeg is not found
- Install FFmpeg and ensure `ffmpeg.exe` is available in PATH.
- Reopen Command Prompt and run the app again.
