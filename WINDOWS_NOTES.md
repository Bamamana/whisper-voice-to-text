# Windows Setup

This repo now includes a Windows installer and launcher, so you can keep one portable copy for both Linux and Windows.

## Prerequisites
- Internet access during install
- Microsoft Visual C++ Redistributable if a Python wheel asks for it

Important:
- The packaged Windows installer bootstraps Python and FFmpeg for you on a clean machine.
- It installs Python per-user from python.org when Python 3.11+ is missing.
- It installs the Visual C++ Redistributable when `vcruntime140.dll` is missing.
- It downloads an app-local FFmpeg copy into `tools\ffmpeg\bin` when FFmpeg is missing.
- Internet access is still required during setup and model download.

## Install on Windows
Open Command Prompt in this folder and run one of these:

```bat
setup_windows.bat
setup_windows.bat cpu
setup_windows.bat amd
setup_windows.bat nvidia
```

Profiles:
- `auto` detects NVIDIA first, then AMD, then CPU
- `cpu` forces CPU mode
- `amd` keeps the app on the CPU backend
- `nvidia` installs the CUDA runtime libraries needed by `faster-whisper` into the virtual environment and enables GPU use when an NVIDIA GPU is present

What the installer does:
- Recreates or repairs `.venv`
- Downloads and installs Python 3.11+ automatically when needed
- Downloads an app-local FFmpeg build automatically when needed
- Installs the Visual C++ Redistributable automatically when needed
- Installs `faster-whisper`, `sounddevice`, and supporting Python packaging tools
- Installs `nvidia-cublas-cu12`, `nvidia-cudnn-cu12`, and `nvidia-cuda-runtime-cu12` when the selected profile is `nvidia`
- Writes `.whisper-profile.env` so the app knows which hardware profile to prefer
- Pre-downloads the `tiny`, `base`, and `small` models during manual `setup_windows.bat` runs unless `--skip-model-download` is used

## Windows installer

This repo also includes a Windows installer definition for Inno Setup.

To build it from the repo:

```bat
build_windows_installer.bat
```

Output:

```text
dist\windows-installer\WhisperVoiceToTextSetup.exe
```

The installer copies the app into `%LOCALAPPDATA%\Programs\Whisper Voice To Text`, creates Start Menu shortcuts, optionally creates a desktop shortcut, and runs `setup_windows.bat auto --skip-shortcut --skip-model-download` to prepare the runtime.

## Launch on Windows

```bat
windows_launch.bat
```

If `.venv` is missing, the launcher tells you to run `setup_windows.bat` or reinstall the app.

For normal desktop and installer launches, the shortcut path now runs `windows_shortcut_launch.bat` through `cmd.exe`, and that wrapper starts `windows_launch.pyw` with `pythonw.exe` when the virtual environment is ready.
Use `windows_launch.bat` when you want console output for troubleshooting.

## NVIDIA GPU acceleration on Windows

This repo can use CUDA on Windows and the Windows NVIDIA install profile now places the required CUDA runtime libraries inside the virtual environment.

For Windows GPU acceleration you need:
- An NVIDIA GPU with a working driver
- `nvidia-smi` available
- The `nvidia` install profile so the CUDA runtime DLLs are installed into `.venv`

The Windows launchers add those CUDA DLL folders to `PATH` before the app starts. If CUDA still fails at runtime, the app falls back to CPU automatically instead of crashing.

## Desktop shortcut
- Run:

```bat
make_windows_shortcut.bat
```

- This creates a desktop shortcut named `Whisper Voice-to-Text`
- The shortcut resolves the real Windows Desktop folder and launches `windows_shortcut_launch.bat` from the correct working folder

## Troubleshooting

### FFmpeg missing
- The installer now downloads an app-local FFmpeg copy automatically.
- If it was removed later, rerun `setup_windows.bat`.
- Launch again with `windows_launch.bat`

### Microphone not working
- Check `Settings > Privacy & security > Microphone`
- Confirm your default recording device is correct
- Restart the app after changing permissions

### GPU not being used
- Run `nvidia-smi` in another Command Prompt window
- Make sure you installed with `setup_windows.bat nvidia` or `setup_windows.bat`
- If the app still reports CPU, rerun `setup_windows.bat nvidia` to rebuild `.venv` with the CUDA runtime packages
- If the app still reports CPU after reinstalling, the app is using its automatic CPU fallback and you should verify the NVIDIA driver is healthy with `nvidia-smi`

### Error about `cublas64*.dll` or CUDA DLLs not loading
- Close the app completely
- Open Command Prompt in this folder
- Run `setup_windows.bat nvidia`
- Start the app again with `windows_launch.bat`

This rebuilds the virtual environment and reinstalls the CUDA runtime packages that the Windows launcher expects.
