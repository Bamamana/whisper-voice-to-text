@echo off
setlocal

set "APP_DIR=%~dp0"
set "VENV_PY=%APP_DIR%.venv\Scripts\python.exe"

if not exist "%VENV_PY%" (
  echo Python virtual environment not found.
  echo Run these first:
  echo   py -m venv .venv
  echo   .venv\Scripts\python -m pip install --upgrade pip wheel setuptools
  echo   .venv\Scripts\pip install faster-whisper sounddevice
  pause
  exit /b 1
)

"%VENV_PY%" "%APP_DIR%app.py"
if errorlevel 1 pause
