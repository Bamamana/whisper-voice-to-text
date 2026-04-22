# Whisper Voice To Text

This repo is a portable desktop app for local Whisper transcription on Linux and Windows.

It is aimed at people who want a practical local voice-to-text app they can run themselves, with a repo-based setup path and a packaged Windows installer.

It supports:
- audio and video file transcription
- microphone recording
- model switching (`tiny`, `base`, `small`, `medium`, `large-v3`)
- NVIDIA GPU acceleration when available
- desktop launchers on both Linux and Windows
- a packaged Windows installer (`WhisperVoiceToTextSetup.exe`)

## Current Status

Working now:
- Windows repo-based install flow
- Linux repo-based install flow
- packaged Windows installer via Inno Setup
- desktop shortcut or icon setup on both platforms
- microphone recording and file transcription
- local model caching in `model-cache/`
- Windows NVIDIA GPU support with automatic CPU fallback

## Start Here

Pick your operating system and follow that checklist.

If you are on Windows:
1. Easiest option if you have the packaged installer: run `WhisperVoiceToTextSetup.exe` and follow the prompts.
2. Keep internet access available during setup so the installer can bootstrap Python and FFmpeg if needed.
3. After install finishes, launch `Whisper Voice To Text` from the Start Menu or Windows Search. The desktop shortcut is optional and only appears if you selected it in the installer.
4. Use `windows_launch.bat` only when you want troubleshooting output from a repo copy or an installed copy.
5. If you are building that installer from the repo yourself, run:
   ```bat
   build_windows_installer.bat
   ```
   That writes the installer to `dist\windows-installer\WhisperVoiceToTextSetup.exe`.
6. If you are installing from the repo directly instead of using the packaged installer, open Command Prompt in this repo folder.
7. Run:
   ```bat
   setup_windows.bat
   ```
8. Create the desktop shortcut only if you want one:
   ```bat
   make_windows_shortcut.bat
   ```
9. Start the app:
   ```bat
   windows_launch.bat
   ```
   Or use the Start Menu entry or desktop shortcut, which launch the no-console `windows_launch.pyw` path.

If you are on Linux:
1. Open a terminal in this repo folder.
2. Make the scripts executable:
   ```bash
   chmod +x install.sh install_cpu.sh install_amd.sh install_nvidia.sh launch.sh desktop_launch.sh make_desktop_shortcut.sh
   ```
3. Run:
   ```bash
   ./install.sh
   ```
4. Create the desktop icon:
   ```bash
   ./make_desktop_shortcut.sh
   ```
5. Start the app:
   ```bash
   ./launch.sh
   ```
   Or just double-click the desktop icon.

## Required Software

Windows:
- Microsoft Visual C++ Redistributable if a wheel requires it
- internet access during install and the first model download

If you use the Windows installer, it bootstraps Python from python.org and downloads an app-local FFmpeg build automatically when they are missing.

Linux:
- internet access during install and the first model download
- `sudo` access for the installer
- Debian/Ubuntu style `apt` packages if you use `install.sh` as-is

The Linux installer installs these packages for you:
- `ffmpeg`
- `python3-venv`
- `python3-tk`
- `libportaudio2`
- `portaudio19-dev`
- `pciutils`

NVIDIA GPU mode on either platform also needs:
- a working NVIDIA driver
- `nvidia-smi`

## Install Profiles

Windows:
- `setup_windows.bat` uses auto-detection and prepares the full Windows runtime
- `setup_windows.bat cpu` forces CPU mode
- `setup_windows.bat amd` uses the AMD profile, which currently still runs on CPU
- `setup_windows.bat nvidia` installs the NVIDIA CUDA runtime packages into `.venv` and enables GPU use when the NVIDIA driver is healthy

Linux:
- `./install.sh` uses auto-detection
- `./install_cpu.sh` forces CPU mode
- `./install_amd.sh` uses the AMD profile, which currently still runs on CPU
- `./install_nvidia.sh` installs the NVIDIA CUDA runtime packages into `.venv`

## Model Downloads

Models are stored under `model-cache/`.

That means each model is downloaded once and then reused locally from this repo folder.
The app does not need to download the same model every time you start it.

If you want fast model switching, pre-download the models after install.
Then changing the dropdown loads the local copy instead of waiting for a network download.

Download all models:

Windows:
```bat
.venv\Scripts\python.exe download_models.py
```

Linux:
```bash
./.venv/bin/python download_models.py
```

Download only specific models:

Windows:
```bat
.venv\Scripts\python.exe download_models.py tiny base small
```

Linux:
```bash
./.venv/bin/python download_models.py tiny base small
```

If you do not pre-download models, the app downloads a model the first time you choose it and keeps it in `model-cache/` for future launches.

## Desktop Launchers

Windows:
- `make_windows_shortcut.bat` creates a desktop shortcut named `Whisper Voice-to-Text`
- the shortcut launches `windows_launch.pyw` via `pythonw.exe` so the app opens without an extra console window

Linux:
- `make_desktop_shortcut.sh` creates a desktop icon and an applications-menu entry
- the desktop icon launches `desktop_launch.sh`

## GPU Notes

NVIDIA:
- Linux and Windows both install the NVIDIA runtime packages into `.venv` when using the `nvidia` profile
- the launchers set the required library paths before starting the app
- if CUDA fails at runtime, the app automatically falls back to CPU instead of crashing

AMD:
- the current faster-whisper setup in this repo uses CPU on AMD systems

## Output Files

Each transcript is saved next to the source file as `filename.whisper.txt`.

## Common Problems

If Python on Windows opens the Microsoft Store instead of printing a version:
- disable the Python App Execution Alias in Windows settings
- install Python from python.org

If FFmpeg is missing:
- rerun `setup_windows.bat`
- if you used the packaged installer, reinstall or rerun setup from the installed app folder
- then launch the app again

If you see a Windows CUDA DLL error such as `cublas64*.dll`:
```bat
setup_windows.bat nvidia
windows_launch.bat
```

If the app is slow:
- check whether the device indicator shows GPU or CPU
- use `tiny` or `base` for faster transcription

## Windows Installer

The repo now includes a working Windows installer built with Inno Setup.

To build it:
1. Install Inno Setup 6.
2. Open Command Prompt in this repo folder.
3. Run:
   ```bat
   build_windows_installer.bat
   ```

The generated installer is written to:

```text
dist\windows-installer\WhisperVoiceToTextSetup.exe
```

What the installer does:
- copies the app into a per-user install folder under `%LOCALAPPDATA%\Programs`
- creates a Start Menu shortcut that is searchable from Windows Search
- optionally creates a desktop shortcut
- runs `setup_windows.bat auto --skip-shortcut` to bootstrap Python and FFmpeg automatically when they are missing
- runs the app dependency setup and prepares the virtual environment, reusing a healthy `.venv` when one already exists
- pre-downloads the `tiny`, `base`, and `small` models during install, reusing models already present in `model-cache\`
- launches the app through `windows_launch.pyw` so normal GUI starts do not leave a black console window open

If you are sharing the app with a non-developer Windows user, this installer is the simplest path.

## More Detailed Docs

- [QUICKSTART.md](QUICKSTART.md)
- [FIRST_RUN.md](FIRST_RUN.md)
- [README_PORTABLE_SETUP.md](README_PORTABLE_SETUP.md)
- [WINDOWS_NOTES.md](WINDOWS_NOTES.md)
