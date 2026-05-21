@echo off
setlocal

set "APP_DIR=%~dp0"
set "ROOT_DIR=%APP_DIR%..\"
set "VENV_PY=%APP_DIR%.venv\Scripts\python.exe"
set "FFMPEG_DIR=%ROOT_DIR%tools\ffmpeg\bin"

if not exist "%VENV_PY%" (
  echo V5 virtual environment not found.
  echo Run this first:
  echo   install_windows_v5.bat
  pause
  exit /b 1
)

if exist "%FFMPEG_DIR%\ffmpeg.exe" set "PATH=%FFMPEG_DIR%;%PATH%"

"%VENV_PY%" "%APP_DIR%app_v5.py"
if errorlevel 1 pause

endlocal
