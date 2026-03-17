# First Run Guide

Use this guide if you want the app fully ready before you start using it.

## Goal

After these steps you will have:
- the app installed
- a desktop shortcut or icon
- the local model cache ready for fast loading
- the correct runtime for CPU or NVIDIA GPU use

## Windows First Run

If you already have a built installer, you can run `WhisperVoiceToTextSetup.exe` and let it copy the app, create shortcuts, and run the Windows setup flow for you.

### 1. Install required software

- Install Python 3.11 or newer from python.org
- During install, enable `Add python.exe to PATH`
- Keep the `py` launcher enabled
- Install FFmpeg and make sure `ffmpeg.exe` is in `PATH`

### 2. Install the app

Open Command Prompt in this repo folder and run:

```bat
install_windows.bat
```

Alternative maintainer flow for packaging:

```bat
build_windows_installer.bat
```

That creates `dist\windows-installer\WhisperVoiceToTextSetup.exe`.

If you want to force a specific profile:

```bat
install_windows.bat cpu
install_windows.bat amd
install_windows.bat nvidia
```

### 3. Create the desktop shortcut

```bat
make_windows_shortcut.bat
```

### 4. Pre-download the models

Download all models:

```bat
.venv\Scripts\python.exe download_models.py
```

Or download only the smaller models first:

```bat
.venv\Scripts\python.exe download_models.py tiny base small
```

This stores the models in `model-cache/`.
After that, choosing a model is much faster because the app loads the local copy instead of downloading it on first use.

### 5. Start the app

```bat
windows_launch.bat
```

Or double-click the desktop shortcut.

### 6. If you want GPU mode

- Make sure `nvidia-smi` works
- Use `install_windows.bat nvidia` if needed
- If a CUDA DLL error appears, rerun:

```bat
install_windows.bat nvidia
windows_launch.bat
```

## Linux First Run

### 1. Open a terminal in this repo folder

Make the scripts executable:

```bash
chmod +x install.sh install_cpu.sh install_amd.sh install_nvidia.sh launch.sh desktop_launch.sh make_desktop_shortcut.sh
```

### 2. Install the app

Run:

```bash
./install.sh
```

If you want to force a specific profile:

```bash
./install_cpu.sh
./install_amd.sh
./install_nvidia.sh
```

### 3. Create the desktop icon

```bash
./make_desktop_shortcut.sh
```

### 4. Pre-download the models

Download all models:

```bash
./.venv/bin/python download_models.py
```

Or download only the smaller models first:

```bash
./.venv/bin/python download_models.py tiny base small
```

This stores the models in `model-cache/`.
After that, choosing a model is much faster because the app loads the local copy instead of downloading it on first use.

### 5. Start the app

```bash
./launch.sh
```

Or double-click the desktop icon.

## Recommended first test

1. Start the app.
2. Choose the `tiny` or `base` model.
3. Load a short audio file or record a short microphone sample.
4. Confirm a `*.whisper.txt` file is written next to the source file.

## After first run

- You can switch models from the dropdown.
- Pre-downloaded models load from local cache.
- Transcripts are saved next to the source file.
- If GPU is active, the device indicator should show NVIDIA GPU.