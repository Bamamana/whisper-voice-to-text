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
2. If you are building that installer from the repo yourself, run:
   ```bat
   build_windows_installer.bat
   ```
   That writes the installer to `dist\windows-installer\WhisperVoiceToTextSetup.exe`.
3. On a fresh Windows machine, keep internet access available during setup so the installer can bootstrap Python, FFmpeg, and the Visual C++ runtime if needed.
4. If you are installing from the repo directly instead of using the packaged installer, open Command Prompt in this repo folder.
5. Run:
   ```bat
   setup_windows.bat
   ```
6. Create the desktop shortcut:
   ```bat
   make_windows_shortcut.bat
   ```
7. Start the app:
   ```bat
   windows_launch.bat
   ```
   Or just double-click the desktop shortcut, which uses the wrapper-based no-console launcher path.

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

If you use the Windows installer, it bootstraps Python from python.org, installs the Visual C++ Redistributable when needed, and downloads an app-local FFmpeg build automatically when they are missing.

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

Manual `setup_windows.bat` runs pre-download `tiny`, `base`, and `small` by default.
The packaged Windows installer skips optional model pre-downloads during install so the first install path is more reliable.

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
- the shortcut resolves the real Windows Desktop folder and launches a wrapper script through `cmd`, which then starts the no-console `windows_launch.pyw` path when available

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
- restart your terminal if you were already using one
- launch the app again

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
- creates a Start Menu shortcut
- optionally creates a desktop shortcut
- runs `setup_windows.bat` to bootstrap Python, FFmpeg, and the Visual C++ runtime automatically when they are missing
- runs the app dependency setup and prepares the virtual environment
- skips optional model pre-downloads during installer-driven setup so first install is less fragile
- launches the app through a wrapper-based shortcut path so normal GUI starts do not depend on a direct `.venv\Scripts\pythonw.exe` shortcut target

If you are sharing the app with a non-developer Windows user, this installer is the simplest path.

## More Detailed Docs

- [QUICKSTART.md](QUICKSTART.md)
- [FIRST_RUN.md](FIRST_RUN.md)
- [README_PORTABLE_SETUP.md](README_PORTABLE_SETUP.md)
- [WINDOWS_NOTES.md](WINDOWS_NOTES.md)
