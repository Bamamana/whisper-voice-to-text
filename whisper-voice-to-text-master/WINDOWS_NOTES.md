# Windows Setup

This repo now includes a Windows installer and launcher, so you can keep one portable copy for both Linux and Windows.

## Prerequisites
- Python 3.11 or newer from python.org
- FFmpeg in `PATH`
- Microsoft Visual C++ Redistributable if a Python wheel asks for it

Important:
- The Windows Store `python.exe` alias is not enough for this project
- Install the real Python distribution from python.org
- During install, enable `Add python.exe to PATH`
- Leave the `py` launcher enabled if offered

Check the basics from Command Prompt:

```bat
py --version
python --version
ffmpeg -version
```

If `python` opens the Microsoft Store instead of printing a version, disable the Python App Execution Alias in `Settings > Apps > Advanced app settings > App execution aliases` and install Python from python.org.

## Install on Windows
Open Command Prompt in this folder and run one of these:

```bat
install_windows.bat
install_windows.bat cpu
install_windows.bat amd
install_windows.bat nvidia
```

Profiles:
- `auto` detects NVIDIA first, then AMD, then CPU
- `cpu` forces CPU mode
- `amd` keeps the app on the CPU backend
- `nvidia` installs the CUDA runtime libraries needed by `faster-whisper` into the virtual environment and enables GPU use when an NVIDIA GPU is present

What the installer does:
- Recreates `.venv`
- Installs `faster-whisper`, `sounddevice`, and supporting Python packaging tools
- Installs `nvidia-cublas-cu12`, `nvidia-cudnn-cu12`, and `nvidia-cuda-runtime-cu12` when the selected profile is `nvidia`
- Writes `.whisper-profile.env` so the app knows which hardware profile to prefer

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

## Launch on Windows

```bat
windows_launch.bat
```

If `.venv` is missing, the launcher tells you to run `install_windows.bat` first.

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
- Install FFmpeg and add it to `PATH`
- Restart Command Prompt
- Launch again with `windows_launch.bat`

### Microphone not working
- Check `Settings > Privacy & security > Microphone`
- Confirm your default recording device is correct
- Restart the app after changing permissions

### GPU not being used
- Run `nvidia-smi` in another Command Prompt window
- Make sure you installed with `install_windows.bat nvidia` or `install_windows.bat`
- If the app still reports CPU, rerun `install_windows.bat nvidia` to rebuild `.venv` with the CUDA runtime packages
- If the app still reports CPU after reinstalling, the app is using its automatic CPU fallback and you should verify the NVIDIA driver is healthy with `nvidia-smi`

### Error about `cublas64*.dll` or CUDA DLLs not loading
- Close the app completely
- Open Command Prompt in this folder
- Run `install_windows.bat nvidia`
- Start the app again with `windows_launch.bat`

This rebuilds the virtual environment and reinstalls the CUDA runtime packages that the Windows launcher expects.
