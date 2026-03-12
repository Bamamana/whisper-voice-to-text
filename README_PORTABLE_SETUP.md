# Whisper Voice To Text (Portable Folder)

This folder is a portable copy of your Whisper desktop app with selectable CPU, AMD, and NVIDIA install profiles.

## Included files
- `app.py` - GUI app (file transcription + microphone recording)
- `install.sh` - Linux installer with `auto`, `cpu`, `amd`, and `nvidia` profiles
- `install_cpu.sh` - Explicit CPU setup
- `install_amd.sh` - Explicit AMD-oriented setup (CPU backend with current faster-whisper build)
- `install_nvidia.sh` - Explicit NVIDIA CUDA setup
- `launch.sh` - Linux launcher (sets up LD_LIBRARY_PATH for CUDA)
- `desktop_launch.sh` - Desktop-safe launcher wrapper (logs failures to `desktop-launch.log`)
- `choose_profile.py` - Small launcher dialog to choose CPU, AMD, or NVIDIA before starting
- `Whisper-Voice-To-Text.desktop` - Original desktop entry example
- `make_desktop_shortcut.sh` - Rebuilds a correct desktop icon path on a new Linux machine
- `download_models.py` - Pre-download Whisper models into local cache for instant switching
- `windows_launch.bat` - Windows launcher template
- `WINDOWS_NOTES.md` - What to change for Windows

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
   ./install.sh        # auto-detect hardware
   ./install_amd.sh    # force AMD profile
   ./install_nvidia.sh # force NVIDIA profile
   ./make_desktop_shortcut.sh
   ```
4. Double-click the desktop icon `Whisper-Voice-To-Text.desktop`.

### Desktop launcher behavior
- The desktop icon now opens a small chooser before launch.
- You can select `Current`, `CPU`, `AMD`, or `NVIDIA`.
- If you pick a different profile than the one currently installed, the launcher rebuilds `.venv` for that profile and then starts the app.
- The selected profile is persisted in `.whisper-profile.env` by the installer.

## GPU Acceleration (NVIDIA CUDA)

### NVIDIA profile
1. **NVIDIA GPU** with CUDA support
2. **NVIDIA driver** installed (check with `nvidia-smi`)
3. **CUDA runtime libraries** - installed automatically by `./install_nvidia.sh`

### AMD profile
- The AMD profile keeps this app usable on AMD systems without pulling NVIDIA CUDA libraries.
- The current `faster-whisper` build used by this app supports **NVIDIA CUDA or CPU**, not AMD ROCm GPU execution.
- On AMD systems, this app currently runs on the CPU backend and labels the UI accordingly.
- This makes the folder portable across AMD and NVIDIA machines while keeping the setups separated.

### How it works
- The launcher stores the selected install profile in `.whisper-profile.env`
- The app detects the active profile and available hardware at startup
- CUDA libraries (`nvidia-cublas-cu12`, `nvidia-cudnn-cu12`, `nvidia-cuda-runtime-cu12`) are installed in the venv
- `launch.sh` sets `LD_LIBRARY_PATH` to include these libraries
- If CUDA fails, the app automatically falls back to CPU

### Common Pitfalls and Solutions

#### Pitfall 1: "Library libcublas.so.12 is not found"
**Cause**: NVIDIA driver is installed, but CUDA runtime libraries are missing.

**Solution**: The NVIDIA install profile installs these automatically. If you see this error:
```bash
./install_nvidia.sh
```

#### Pitfall 2: CUDA libraries installed but still not found
**Cause**: The libraries are in the venv but not in the library search path.

**Solution**: `launch.sh` now sets `LD_LIBRARY_PATH`. If running Python directly:
```bash
export LD_LIBRARY_PATH="$(pwd)/.venv/lib/python3.12/site-packages/nvidia/cublas/lib:$(pwd)/.venv/lib/python3.12/site-packages/nvidia/cudnn/lib:$(pwd)/.venv/lib/python3.12/site-packages/nvidia/cuda_runtime/lib:$LD_LIBRARY_PATH"
./.venv/bin/python app.py
```

#### Pitfall 3: Old app instance still running after updates
**Cause**: Desktop launch keeps old process running; new code isn't loaded.

**Solution**: Kill existing processes before relaunching:
```bash
pkill -f 'whisper voice to text.*app.py'
```

#### Pitfall 4: CUDA version mismatch
**Cause**: The pip-installed CUDA libraries may not match your driver's CUDA version.

**Solution**: The app will auto-fallback to CPU. For full CUDA support, ensure your NVIDIA driver supports CUDA 12.x. Check with:
```bash
nvidia-smi  # Look for "CUDA Version" in the header
```

### Verifying GPU is being used
1. Launch the app
2. Check the device indicator shows "NVIDIA GPU (CUDA)"
3. Or run in another terminal:
   ```bash
   nvidia-smi
   # Look for the python process in the Processes section
   ```

## Notes
- Models are cached in `model-cache/`.
- Re-running any install profile recreates `.venv` so the runtime matches the selected hardware profile.
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

### Transcription is slow
- Check if GPU is being used (see "Verifying GPU is being used" above)
- If using CPU, consider using a smaller model (tiny, base, small)
- GPU is ~10-50x faster than CPU for transcription

### Model won't load
- Check internet connection (models download from HuggingFace)
- Check disk space (models are 1-3GB each)
- Try a smaller model first

### Microphone not working
- Check system audio permissions
- Try `arecord -l` to list microphones
- Ensure `portaudio19-dev` is installed
