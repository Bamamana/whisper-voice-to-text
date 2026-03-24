#!/usr/bin/env python3
import os
import subprocess
import sys
import traceback
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
VENV_PYTHON = APP_DIR / ".venv" / "Scripts" / "python.exe"
VENV_PYTHONW = APP_DIR / ".venv" / "Scripts" / "pythonw.exe"
PROFILE_FILE = APP_DIR / ".whisper-profile.env"


def show_message(title: str, message: str, style: int) -> None:
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, message, title, style)
    except Exception:
        pass


def relaunch_with_venv() -> bool:
    if not VENV_PYTHONW.exists():
        return False

    try:
        current_executable = Path(sys.executable).resolve()
        target_executable = VENV_PYTHONW.resolve()
    except Exception:
        current_executable = Path(sys.executable)
        target_executable = VENV_PYTHONW

    if current_executable == target_executable:
        return False

    subprocess.Popen([str(VENV_PYTHONW), str(Path(__file__).resolve())], cwd=str(APP_DIR))
    return True


def configure_environment() -> None:
    os.chdir(APP_DIR)
    os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")

    if not PROFILE_FILE.exists():
        PROFILE_FILE.write_text("WHISPER_ACCELERATOR=auto\n", encoding="utf-8")

    nvidia_site_packages = APP_DIR / ".venv" / "Lib" / "site-packages" / "nvidia"
    path_parts = []
    for relative_path in [
        Path("cublas") / "bin",
        Path("cudnn") / "bin",
        Path("cuda_runtime") / "bin",
        Path("cuda_runtime") / "lib" / "x64",
    ]:
        candidate = nvidia_site_packages / relative_path
        if candidate.exists():
            path_parts.append(str(candidate))

    if path_parts:
        os.environ["PATH"] = os.pathsep.join(path_parts + [os.environ.get("PATH", "")])


def main() -> int:
    if relaunch_with_venv():
        return 0

    if not VENV_PYTHON.exists():
        show_message(
            "Whisper Voice To Text setup required",
            "The Whisper Voice To Text Python environment was not found.\n\nRun setup_windows.bat first, then launch the app again.",
            0x10,
        )
        return 1

    configure_environment()

    try:
        from app import main as app_main

        app_main()
        return 0
    except Exception:
        show_message(
            "Whisper Voice To Text launch failed",
            "Whisper Voice To Text could not start.\n\n"
            "If you need startup details, run windows_launch.bat from Command Prompt.\n\n"
            f"{traceback.format_exc()}",
            0x10,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())