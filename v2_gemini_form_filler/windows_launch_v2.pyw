#!/usr/bin/env python3
import os
import subprocess
import sys
import traceback
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
VENV_PYTHON = APP_DIR / ".venv" / "Scripts" / "python.exe"
VENV_PYTHONW = APP_DIR / ".venv" / "Scripts" / "pythonw.exe"


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

    ffmpeg_bin = ROOT_DIR / "tools" / "ffmpeg" / "bin"
    if (ffmpeg_bin / "ffmpeg.exe").exists():
        os.environ["PATH"] = os.pathsep.join([str(ffmpeg_bin), os.environ.get("PATH", "")])


def main() -> int:
    if relaunch_with_venv():
        return 0

    if not VENV_PYTHON.exists():
        show_message(
            "Whisper Voice To Form V2 setup required",
            "The V2 Python environment was not found.\n\nRun install_windows_v2.bat first, then launch the app again.",
            0x10,
        )
        return 1

    configure_environment()

    try:
        from app_v2 import main as app_main

        app_main()
        return 0
    except Exception:
        show_message(
            "Whisper Voice To Form V2 launch failed",
            "Whisper Voice To Form V2 could not start.\n\n"
            "If you need startup details, run launch_windows_v2.bat from Command Prompt.\n\n"
            f"{traceback.format_exc()}",
            0x10,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
