@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "APP_DIR=%~dp0"
set "BOOTSTRAP_PS=%APP_DIR%bootstrap_windows.ps1"
set "PROFILE=auto"
set "CREATE_SHORTCUT=1"
set "DOWNLOAD_MODELS=tiny base small"

:parse_args
if "%~1"=="" goto :main
if /I "%~1"=="-h" goto :usage
if /I "%~1"=="--help" goto :usage
if /I "%~1"=="auto" set "PROFILE=auto" & shift & goto :parse_args
if /I "%~1"=="cpu" set "PROFILE=cpu" & shift & goto :parse_args
if /I "%~1"=="amd" set "PROFILE=amd" & shift & goto :parse_args
if /I "%~1"=="nvidia" set "PROFILE=nvidia" & shift & goto :parse_args
if /I "%~1"=="--skip-shortcut" set "CREATE_SHORTCUT=0" & shift & goto :parse_args
if /I "%~1"=="--skip-model-download" set "DOWNLOAD_MODELS=" & shift & goto :parse_args
if /I "%~1"=="--download-models" (
  shift
  if "%~1"=="" (
    echo Missing model list after --download-models
    exit /b 1
  )
  set "DOWNLOAD_MODELS=%~1"
  shift
  :collect_models
  if "%~1"=="" goto :main
  set "DOWNLOAD_MODELS=!DOWNLOAD_MODELS! %~1"
  shift
  goto :collect_models
)

echo Unknown option: %~1
echo.
goto :usage

:main
call :ensure_python
if errorlevel 1 exit /b 1

call :ensure_vcredist
if errorlevel 1 exit /b 1

call :ensure_ffmpeg
if errorlevel 1 exit /b 1

set "WHISPER_BOOTSTRAP_PYTHON=%BOOTSTRAP_PYTHON%"
if defined FFMPEG_BIN_DIR set "PATH=%FFMPEG_BIN_DIR%;%PATH%"

echo Running Windows app installer with profile: %PROFILE%
call "%APP_DIR%install_windows.bat" %PROFILE%
if errorlevel 1 exit /b 1

if "%CREATE_SHORTCUT%"=="1" (
  echo Creating desktop shortcut...
  call "%APP_DIR%make_windows_shortcut.bat"
  if errorlevel 1 exit /b 1
)

if defined DOWNLOAD_MODELS (
  echo Pre-downloading models: %DOWNLOAD_MODELS%
  "%APP_DIR%.venv\Scripts\python.exe" "%APP_DIR%download_models.py" %DOWNLOAD_MODELS%
  if errorlevel 1 exit /b 1
)

echo.
echo Setup complete.
echo Start the app with:
echo   windows_launch.bat
exit /b 0

:ensure_python
set "BOOTSTRAP_PYTHON="
for /f "usebackq delims=" %%I in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%BOOTSTRAP_PS%" -Action ensure-python`) do (
  if not defined BOOTSTRAP_PYTHON set "BOOTSTRAP_PYTHON=%%~I"
)

if defined BOOTSTRAP_PYTHON goto :eof

echo Python 3.11 or newer could not be prepared automatically.
exit /b 1

:ensure_ffmpeg
set "FFMPEG_BIN_DIR="
for /f "usebackq delims=" %%I in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%BOOTSTRAP_PS%" -Action ensure-ffmpeg -AppDir "%APP_DIR%"`) do (
  if not defined FFMPEG_BIN_DIR set "FFMPEG_BIN_DIR=%%~I"
)

if defined FFMPEG_BIN_DIR goto :eof

echo FFmpeg could not be prepared automatically.
exit /b 1
goto :eof

:ensure_vcredist
set "VCREDIST_DLL="
for /f "usebackq delims=" %%I in (`powershell -NoProfile -ExecutionPolicy Bypass -File "%BOOTSTRAP_PS%" -Action ensure-vcredist`) do (
  if not defined VCREDIST_DLL set "VCREDIST_DLL=%%~I"
)

if defined VCREDIST_DLL goto :eof

echo Microsoft Visual C++ Redistributable could not be prepared automatically.
exit /b 1
goto :eof

:usage
echo Usage: setup_windows.bat [auto^|cpu^|amd^|nvidia] [--skip-shortcut] [--skip-model-download] [--download-models model1 model2 ...]
echo.
echo Examples:
echo   setup_windows.bat
echo   setup_windows.bat nvidia
echo   setup_windows.bat auto --download-models tiny base small
echo   setup_windows.bat auto --skip-model-download
exit /b 1