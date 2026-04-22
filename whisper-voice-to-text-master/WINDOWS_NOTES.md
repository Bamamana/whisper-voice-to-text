# Windows Setup

This repo now includes a Windows installer and launcher, so you can keep one portable copy for both Linux and Windows.

## Prerequisites
- Internet access during install
- Microsoft Visual C++ Redistributable if a Python wheel asks for it

Important:
- The packaged Windows installer now bootstraps Python and FFmpeg for you on a clean machine.
- It installs Python per-user from python.org when Python 3.11+ is missing.
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
- Reuses an existing `.venv` when it is healthy, and repairs or recreates it only when needed
- Downloads and installs Python 3.11+ automatically when needed
- Downloads an app-local FFmpeg build automatically when needed
- Installs `faster-whisper`, `sounddevice`, and supporting Python packaging tools
- Installs `nvidia-cublas-cu12`, `nvidia-cudnn-cu12`, and `nvidia-cuda-runtime-cu12` when the selected profile is `nvidia`
- Writes `.whisper-profile.env` so the app knows which hardware profile to prefer
- Pre-downloads the `tiny`, `base`, and `small` models during setup, reusing any models already present in `model-cache\`

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

The installer copies the app into `%LOCALAPPDATA%\Programs\Whisper Voice To Text`, creates Start Menu shortcuts, optionally creates a desktop shortcut, and runs `setup_windows.bat` to prepare the runtime.

Installed shortcuts and Start Menu entries launch `.venv\Scripts\pythonw.exe` with `windows_launch.pyw`, so the app is searchable from Windows Search and opens without a console window.

## Launch on Windows

```bat
windows_launch.bat
```

If `.venv` is missing, the launcher tells you to run `setup_windows.bat` or reinstall the app.

## Installer smoke checklist

Use this when validating a newly built `dist\windows-installer\WhisperVoiceToTextSetup.exe`.

1. Build the installer from the repo root:

	```bat
	.\build_windows_installer.bat
	```

2. Confirm `dist\windows-installer\WhisperVoiceToTextSetup.exe` exists.
3. Run `WhisperVoiceToTextSetup.exe` on a clean Windows user profile or test machine.
4. Confirm the installer copies files and then runs `setup_windows.bat auto --skip-shortcut` automatically.
5. Confirm setup finishes without asking for a preinstalled Python or FFmpeg path.
6. Confirm the installed app folder contains `.venv`, `windows_launch.pyw`, and `tools\ffmpeg\bin\ffmpeg.exe` when FFmpeg had to be bootstrapped.
7. Launch the installed Start Menu shortcut or search for `Whisper Voice To Text` from Windows Search.
8. Confirm the app opens through `pythonw.exe` with no visible console window.
9. Open the installed app once with `windows_launch.bat` only if you need troubleshooting output.
10. Verify the main window opens, file transcription works, and startup does not fail on missing runtime dependencies.
11. Record the validation date, machine profile used (`auto`, `cpu`, `amd`, or `nvidia`), and any fallback behavior that occurred.

## NVIDIA GPU acceleration on Windows

This repo can use CUDA on Windows and the Windows NVIDIA install profile now places the required CUDA runtime libraries inside the virtual environment.

For Windows GPU acceleration you need:
- An NVIDIA GPU with a working driver
- `nvidia-smi` available
- The `nvidia` install profile so the CUDA runtime DLLs are installed into `.venv`

The Windows launcher adds those CUDA DLL folders to `PATH` before the app starts. If CUDA still fails at runtime, the app falls back to CPU automatically instead of crashing.

## Desktop shortcut
- Run:

```bat
make_windows_shortcut.bat
```

- This creates a desktop shortcut named `Whisper Voice-to-Text`
- The shortcut launches `windows_launch.bat` from the correct working folder

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
