# Whisper Voice To Text (Portable Folder)

This folder is a portable copy of your Whisper desktop app with selectable CPU, AMD, and NVIDIA install profiles.

## Required software

Linux:
- internet access during install and first model download
- `sudo` access for the installer to install system packages
- Debian/Ubuntu style package management if you use `install.sh` as-is
- NVIDIA driver plus `nvidia-smi` if you want GPU mode

Windows:
- internet access during install and first model download
- NVIDIA driver plus `nvidia-smi` if you want GPU mode
- Microsoft Visual C++ Redistributable if a Python wheel requires it

Important:
- `setup_windows.bat` bootstraps Python 3.11+, FFmpeg, and the Visual C++ Redistributable on a clean machine when needed.
- The packaged Windows installer uses `setup_windows.bat auto --skip-shortcut --skip-model-download` so first install skips optional model pre-downloads.
- Manual `setup_windows.bat` still pre-downloads `tiny`, `base`, and `small` unless you pass `--skip-model-download`.

## Included files
- `app.py` - GUI app (file transcription + microphone recording)
- `install.sh` - Linux installer with `auto`, `cpu`, `amd`, and `nvidia` profiles
- `install_cpu.sh` - Explicit CPU setup
- `install_amd.sh` - Explicit AMD-oriented setup (CPU backend with current faster-whisper build)
- `install_nvidia.sh` - Explicit NVIDIA CUDA setup
- `install_windows.bat` - Lower-level Windows environment installer
- `setup_windows.bat` - Windows bootstrapper for Python, FFmpeg, VC++, install, and optional model download
- `launch.sh` - Linux launcher (sets up LD_LIBRARY_PATH for CUDA)
- `desktop_launch.sh` - Desktop-safe launcher wrapper (logs failures to `desktop-launch.log`)
- `choose_profile.py` - Small launcher dialog to choose CPU, AMD, or NVIDIA before starting
- `Whisper-Voice-To-Text.desktop` - Original desktop entry example
- `make_desktop_shortcut.sh` - Rebuilds a correct desktop icon path on a new Linux machine
- `download_models.py` - Pre-download Whisper models into local cache for instant switching
- `windows_launch.bat` - Console Windows launcher for troubleshooting
- `windows_launch.pyw` - GUI Windows launcher for normal desktop starts
- `windows_shortcut_launch.bat` - Shortcut-safe Windows wrapper that delegates to `windows_launch.pyw`
- `make_windows_shortcut.bat` - Creates a Windows desktop shortcut for the wrapper launcher
- `WINDOWS_NOTES.md` - Windows install and troubleshooting guide

## Features
- **Model preloading**: Select a model from the dropdown and it loads automatically
- **Model status indicator**: Shows "Current model loaded: <model>" when ready
- **Copy button**: One-click copy of transcript to clipboard
- **GPU acceleration**: Automatically uses NVIDIA GPU if available
- **Device indicator**: Shows "NVIDIA GPU (CUDA)" or "CPU" in the UI
- **Auto fallback**: If CUDA fails, automatically switches to CPU

## Move to another Linux computer
1. Copy this whole folder to the new computer.
2. Open terminal in this folder.
3. Run one of these:
   ```bash
   chmod +x install.sh install_cpu.sh install_amd.sh install_nvidia.sh launch.sh make_desktop_shortcut.sh
   ./install.sh
   ./install_amd.sh
   ./install_nvidia.sh
   ./make_desktop_shortcut.sh
   ```
4. Double-click the desktop icon `Whisper-Voice-To-Text.desktop`.

## Move to a Windows computer
1. Copy this whole folder to the Windows machine.
2. Keep internet access available during setup so the scripts can bootstrap Python, FFmpeg, and VC++ if needed.
3. Open Command Prompt in this folder and run one of these:
   ```bat
   setup_windows.bat
   setup_windows.bat cpu
   setup_windows.bat amd
   setup_windows.bat nvidia
   ```
4. Start the app with:
   ```bat
   windows_launch.bat
   ```
5. Create a desktop shortcut with:
   ```bat
   make_windows_shortcut.bat
   ```

### Windows profile behavior
- `auto` prefers `nvidia` when `nvidia-smi` is available, then `amd`, then `cpu`.
- `cpu` is the safest Windows option and requires no GPU runtime.
- `amd` currently uses the CPU backend, matching the Linux AMD profile.
- `nvidia` installs the CUDA runtime packages into `.venv` and keeps the app in CUDA mode when your Windows machine has a working NVIDIA driver.
- If CUDA is selected but unavailable at runtime, the app falls back to CPU automatically.

### Desktop launcher behavior
- The desktop icon uses the real Windows Desktop path instead of assuming `%USERPROFILE%\Desktop`.
- Shortcuts target `cmd.exe`, which calls `windows_shortcut_launch.bat` instead of pointing directly at `.venv\Scripts\pythonw.exe`.
- `windows_shortcut_launch.bat` starts `windows_launch.pyw` when the virtual environment is ready and falls back to `windows_launch.bat` for troubleshooting.

## GPU Acceleration (NVIDIA CUDA)

### NVIDIA profile
1. **NVIDIA GPU** with CUDA support
2. **NVIDIA driver** installed (check with `nvidia-smi`)
3. **CUDA runtime libraries** - installed automatically by `./install_nvidia.sh` on Linux or `setup_windows.bat nvidia` on Windows

### AMD profile
- The AMD profile keeps this app usable on AMD systems without pulling NVIDIA CUDA libraries.
- The current `faster-whisper` build used by this app supports **NVIDIA CUDA or CPU**, not AMD ROCm GPU execution.
- On AMD systems, this app currently runs on the CPU backend and labels the UI accordingly.

### How it works
- The launcher stores the selected install profile in `.whisper-profile.env`
- The app detects the active profile and available hardware at startup
- CUDA libraries (`nvidia-cublas-cu12`, `nvidia-cudnn-cu12`, `nvidia-cuda-runtime-cu12`) are installed in the venv
- `launch.sh`, `windows_launch.bat`, and `windows_launch.pyw` set the required library paths before the app starts
- If CUDA fails, the app automatically falls back to CPU

### Windows NVIDIA note
- The Windows NVIDIA profile now installs the CUDA runtime packages into the venv.
- For Windows GPU acceleration, you need a working NVIDIA driver and a successful `setup_windows.bat nvidia` run.
- If a CUDA DLL error appears after an update or a broken install, rerun `setup_windows.bat nvidia` to rebuild the environment.

## Notes
- Models are cached in `model-cache/`.
- Models are downloaded once into `model-cache/` and reused locally on future launches.
- If you pre-download them with `download_models.py`, switching models later is much faster because the app loads the local copy instead of downloading on demand.
- The packaged Windows installer skips model pre-downloads during install for a more reliable first run.
- Re-running any install profile recreates or repairs `.venv` so the runtime matches the selected hardware profile.
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

## Troubleshooting

### App won't start
1. Check `desktop-launch.log` for errors
2. Try running directly: `./launch.sh`
3. Ensure venv exists: `ls .venv/bin/python`
4. On Windows, run `windows_launch.bat` from Command Prompt so you can see the startup error.

### Transcription is slow
- Check if GPU is being used
- If using CPU, consider using a smaller model (`tiny`, `base`, `small`)
- GPU is much faster than CPU for transcription

### Model won't load
- Check internet connection
- Check disk space
- Try a smaller model first

### Microphone not working
- Check system audio permissions
- Try `arecord -l` to list microphones
- Ensure `portaudio19-dev` is installed
