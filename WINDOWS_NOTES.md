# Windows Setup

This repo now includes a Windows installer and launcher, so you can keep one portable copy for both Linux and Windows.

## Prerequisites
- Python 3.11 or newer from python.org
- FFmpeg in `PATH`
- Microsoft Visual C++ Redistributable if a Python wheel asks for it

Check the basics from Command Prompt:

```bat
py --version
ffmpeg -version
```

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
- `nvidia` marks the install for CUDA use if your Windows machine already has CUDA and cuDNN runtime libraries available

What the installer does:
- Recreates `.venv`
- Installs `faster-whisper`, `sounddevice`, and supporting Python packaging tools
- Writes `.whisper-profile.env` so the app knows which hardware profile to prefer

## Launch on Windows

```bat
windows_launch.bat
```

If `.venv` is missing, the launcher tells you to run `install_windows.bat` first.

## NVIDIA GPU acceleration on Windows

This repo can use CUDA on Windows, but the Windows installer does not bundle CUDA runtime DLLs into the virtual environment the way the Linux installer does.

For Windows GPU acceleration you need:
- An NVIDIA GPU with a working driver
- `nvidia-smi` available
- Compatible CUDA and cuDNN runtime DLLs available in `PATH`

If those libraries are missing, the app falls back to CPU automatically instead of crashing.

## Desktop shortcut
- Right-click `windows_launch.bat`
- Choose `Send to > Desktop (create shortcut)`
- Rename the shortcut if you want

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
- If the app still reports CPU, your CUDA/cuDNN runtime is not available to the process and the app is using its automatic CPU fallback
