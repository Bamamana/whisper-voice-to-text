@echo off
setlocal EnableExtensions

set "APP_DIR=%~dp0"
set "ROOT_DIR=%APP_DIR%..\"
set "BOOTSTRAP_PS=%ROOT_DIR%bootstrap_windows.ps1"
set "VENV_DIR=%APP_DIR%.venv"
set "PYTHON_CMD="

for /f "usebackq delims=" %%I in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%BOOTSTRAP_PS%" -Action ensure-python`) do (
  if not defined PYTHON_CMD set "PYTHON_CMD=%%~I"
)

if not defined PYTHON_CMD (
  echo Python 3.11 or newer could not be prepared automatically.
  exit /b 1
)

if exist "%ROOT_DIR%tools\ffmpeg\bin\ffmpeg.exe" set "PATH=%ROOT_DIR%tools\ffmpeg\bin;%PATH%"

where ffmpeg >nul 2>nul
if errorlevel 1 (
  for /f "usebackq delims=" %%I in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%BOOTSTRAP_PS%" -Action ensure-ffmpeg -AppDir "%ROOT_DIR%"`) do (
    set "FFMPEG_BIN_DIR=%%~I"
  )
  if defined FFMPEG_BIN_DIR set "PATH=%FFMPEG_BIN_DIR%;%PATH%"
)

where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo FFmpeg could not be prepared automatically.
  exit /b 1
)

if not exist "%VENV_DIR%\Scripts\python.exe" (
  echo Creating v2 virtual environment...
  "%PYTHON_CMD%" -m venv "%VENV_DIR%"
  if errorlevel 1 exit /b 1
)

echo Installing v2 packages...
"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip wheel setuptools
if errorlevel 1 exit /b 1

"%VENV_DIR%\Scripts\python.exe" -m pip install -r "%APP_DIR%requirements.txt"
if errorlevel 1 exit /b 1

echo.
echo V2 install complete. Start it with:
echo   launch_windows_v2.bat
exit /b 0
