#!/usr/bin/env python3
import os
import site
import subprocess
import sys
import traceback
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent
BUNDLED_PYTHON = ROOT_DIR / "python-runtime" / "python.exe"
BUNDLED_PYTHONW = ROOT_DIR / "python-runtime" / "pythonw.exe"
VENV_PYTHON = APP_DIR / ".venv" / "Scripts" / "python.exe"
VENV_PYTHONW = APP_DIR / ".venv" / "Scripts" / "pythonw.exe"
SITE_PACKAGES = APP_DIR / ".venv" / "Lib" / "site-packages"


def show_message(title: str, message: str, style: int) -> None:
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(None, message, title, style)
    except Exception:
        pass


def relaunch_with_venv() -> bool:
    target_pythonw = BUNDLED_PYTHONW if BUNDLED_PYTHONW.exists() else VENV_PYTHONW
    if not target_pythonw.exists():
        return False

    try:
        current_executable = Path(sys.executable).resolve()
        target_executable = target_pythonw.resolve()
    except Exception:
        current_executable = Path(sys.executable)
        target_executable = target_pythonw

    if current_executable == target_executable:
        return False

    subprocess.Popen([str(target_pythonw), str(Path(__file__).resolve())], cwd=str(APP_DIR))
    return True


def configure_environment() -> None:
    os.chdir(APP_DIR)
    os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "1")

    if SITE_PACKAGES.exists():
        site.addsitedir(str(SITE_PACKAGES))
        current_pythonpath = os.environ.get("PYTHONPATH", "")
        os.environ["PYTHONPATH"] = str(SITE_PACKAGES) if not current_pythonpath else os.pathsep.join([str(SITE_PACKAGES), current_pythonpath])

    ffmpeg_bin = ROOT_DIR / "tools" / "ffmpeg" / "bin"
    if (ffmpeg_bin / "ffmpeg.exe").exists():
        os.environ["PATH"] = os.pathsep.join([str(ffmpeg_bin), os.environ.get("PATH", "")])


def main() -> int:
    if relaunch_with_venv():
        return 0

    if not BUNDLED_PYTHON.exists() and not VENV_PYTHON.exists():
        show_message(
            "Whisper Voice To Form V6 setup required",
            "The V6 runtime was not found.\n\nRun install_windows_v6.bat first or reinstall the offline package, then launch the app again.",
            0x10,
        )
        return 1

    if not SITE_PACKAGES.exists():
        show_message(
            "Whisper Voice To Form V6 setup required",
            "The V6 Python packages were not found.\n\nReinstall the offline package or run install_windows_v6.bat.",
            0x10,
        )
        return 1

    configure_environment()

    try:
        from app_v6 import main as app_main

        app_main()
        return 0
    except Exception:
        show_message(
            "Whisper Voice To Form V6 launch failed",
            "Whisper Voice To Form V6 could not start.\n\n"
            "If you need startup details, run launch_windows_v6.bat from Command Prompt.\n\n"
            f"{traceback.format_exc()}",
            0x10,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
