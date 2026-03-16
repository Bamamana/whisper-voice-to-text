@echo off
setlocal

set "APP_DIR=%~dp0"
set "VENV_PY=%APP_DIR%.venv\Scripts\python.exe"

if not exist "%VENV_PY%" (
  echo Python virtual environment not found.
  echo Run this first:
  echo   install_windows.bat
  pause
  exit /b 1
)

if not exist "%APP_DIR%.whisper-profile.env" (
  >"%APP_DIR%.whisper-profile.env" echo WHISPER_ACCELERATOR=auto
)

where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo Warning: ffmpeg.exe is not in PATH.
  echo Audio files such as WAV may still work, but video and many compressed formats will fail until FFmpeg is installed.
  echo.
)

"%VENV_PY%" "%APP_DIR%app.py"
if errorlevel 1 pause

endlocal
