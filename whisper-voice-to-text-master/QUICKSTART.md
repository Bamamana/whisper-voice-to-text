# Quick Start

Use this if you just want the shortest setup steps.

## Windows

1. Easiest option if you have a built installer: run `WhisperVoiceToTextSetup.exe` and follow the prompts.
2. Keep internet access available during setup so the Windows flow can bootstrap Python and FFmpeg if needed.
3. Open Command Prompt in this repo folder.
6. Run:
   ```bat
   setup_windows.bat
   ```
7. Create the desktop shortcut:
   ```bat
   make_windows_shortcut.bat
   ```
8. Start the app:
   ```bat
   windows_launch.bat
   ```

Optional: pre-download all models so switching is fast later:
```bat
.venv\Scripts\python.exe download_models.py
```

By default, `setup_windows.bat` already pre-downloads `tiny`, `base`, and `small`.

## Linux

1. Open a terminal in this repo folder.
2. Run:
   ```bash
   chmod +x install.sh install_cpu.sh install_amd.sh install_nvidia.sh launch.sh desktop_launch.sh make_desktop_shortcut.sh
   ./install.sh
   ```
3. Create the desktop icon:
   ```bash
   ./make_desktop_shortcut.sh
   ```
4. Start the app:
   ```bash
   ./launch.sh
   ```

Optional: pre-download all models so switching is fast later:
```bash
./.venv/bin/python download_models.py
```

## Notes

- Models are stored in `model-cache/`.
- Each model is downloaded once and then reused locally.
- If you want NVIDIA GPU mode, use the default auto-detect installer or the explicit NVIDIA profile.
- If Windows shows a CUDA DLL error, run:
  ```bat
   setup_windows.bat nvidia
  windows_launch.bat
  ```