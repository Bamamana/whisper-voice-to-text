@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "APP_DIR=%~dp0"
set "VENV_DIR=%APP_DIR%.venv"
set "PROFILE_FILE=%APP_DIR%.whisper-profile.env"
set "PYTHON_CMD="
set "PROFILE=%~1"

if "%PROFILE%"=="" set "PROFILE=auto"

if /I "%PROFILE%"=="-h" goto :usage
if /I "%PROFILE%"=="--help" goto :usage
if /I "%PROFILE%"=="auto" goto :resolve_profile
if /I "%PROFILE%"=="cpu" goto :install
if /I "%PROFILE%"=="amd" goto :install
if /I "%PROFILE%"=="nvidia" goto :install

echo Invalid profile: %PROFILE%
echo.
goto :usage

:resolve_profile
call :detect_profile
set "PROFILE=%DETECTED_PROFILE%"
goto :install

:detect_profile
set "DETECTED_PROFILE=cpu"

where nvidia-smi >nul 2>nul
if not errorlevel 1 (
  set "DETECTED_PROFILE=nvidia"
  goto :eof
)

where amd-smi >nul 2>nul
if not errorlevel 1 (
  set "DETECTED_PROFILE=amd"
  goto :eof
)

powershell -NoProfile -Command "$names = Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name; if ($names -match 'NVIDIA') { exit 10 } elseif ($names -match 'AMD|Radeon|Advanced Micro Devices') { exit 11 } else { exit 0 }" >nul 2>nul
if errorlevel 11 (
  set "DETECTED_PROFILE=amd"
  goto :eof
)
if errorlevel 10 (
  set "DETECTED_PROFILE=nvidia"
  goto :eof
)
goto :eof

:install
where py >nul 2>nul
if not errorlevel 1 (
  set "PYTHON_CMD=py -3"
)

if not defined PYTHON_CMD (
  where python >nul 2>nul
  if not errorlevel 1 (
    python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 22)" >nul 2>nul
    if not errorlevel 1 set "PYTHON_CMD=python"
  )
)

if not defined PYTHON_CMD (
  echo Python 3.11 or newer was not found.
  echo Install Python from python.org and enable both the python.exe PATH option and the py launcher.
  echo If python.exe only opens the Microsoft Store, disable the Python App Execution Alias in Windows settings.
  exit /b 1
)

%PYTHON_CMD% -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 22)" >nul 2>nul
if errorlevel 1 (
  echo Python 3.11 or newer is required.
  echo Install a current Python release from python.org, then run this installer again.
  exit /b 1
)

echo Selected Windows install profile: %PROFILE%
echo Using Python command: %PYTHON_CMD%
echo.

where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo Warning: ffmpeg.exe is not in PATH.
  echo Media conversion for many formats will fail until FFmpeg is installed.
  echo.
)

if exist "%VENV_DIR%" (
  echo Removing existing virtual environment...
  rmdir /s /q "%VENV_DIR%"
)

echo Creating virtual environment...
%PYTHON_CMD% -m venv "%VENV_DIR%"
if errorlevel 1 exit /b 1

echo Upgrading packaging tools...
"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip wheel setuptools
if errorlevel 1 exit /b 1

echo Installing Python packages...
"%VENV_DIR%\Scripts\python.exe" -m pip install faster-whisper sounddevice
if errorlevel 1 exit /b 1

if /I "%PROFILE%"=="nvidia" (
  echo Installing NVIDIA CUDA runtime libraries...
  "%VENV_DIR%\Scripts\python.exe" -m pip install nvidia-cublas-cu12 nvidia-cudnn-cu12 nvidia-cuda-runtime-cu12
  if errorlevel 1 exit /b 1
  echo NVIDIA profile selected.
  echo CUDA runtime libraries were installed into the virtual environment.
) else if /I "%PROFILE%"=="amd" (
  echo AMD profile selected. The current faster-whisper setup still uses the CPU backend on AMD.
) else (
  echo CPU profile selected.
)

>"%PROFILE_FILE%" echo WHISPER_ACCELERATOR=%PROFILE%

echo.
echo Install complete. Start the app with:
echo   windows_launch.bat
echo.
echo Optional: create a desktop shortcut with:
echo   make_windows_shortcut.bat
exit /b 0

:usage
echo Usage: install_windows.bat [auto^|cpu^|amd^|nvidia]
echo.
echo Profiles:
echo   auto    Detect hardware and choose a sensible setup for this machine
echo   cpu     Install CPU-only runtime
echo   amd     Install the AMD profile ^(CPU backend with current faster-whisper build^)
echo   nvidia  Prefer NVIDIA CUDA runtime if your Windows machine already provides CUDA/cuDNN
exit /b 1