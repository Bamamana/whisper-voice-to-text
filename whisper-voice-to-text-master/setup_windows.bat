@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "APP_DIR=%~dp0"
set "PROFILE=auto"
set "CREATE_SHORTCUT=1"
set "DOWNLOAD_MODELS="

:parse_args
if "%~1"=="" goto :main
if /I "%~1"=="-h" goto :usage
if /I "%~1"=="--help" goto :usage
if /I "%~1"=="auto" set "PROFILE=auto" & shift & goto :parse_args
if /I "%~1"=="cpu" set "PROFILE=cpu" & shift & goto :parse_args
if /I "%~1"=="amd" set "PROFILE=amd" & shift & goto :parse_args
if /I "%~1"=="nvidia" set "PROFILE=nvidia" & shift & goto :parse_args
if /I "%~1"=="--skip-shortcut" set "CREATE_SHORTCUT=0" & shift & goto :parse_args
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

call :ensure_ffmpeg

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
where py >nul 2>nul
if not errorlevel 1 goto :eof

where python >nul 2>nul
if errorlevel 1 goto :install_python
python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul
if not errorlevel 1 goto :eof

:install_python
where winget >nul 2>nul
if errorlevel 1 (
  echo Python 3.11 or newer is required.
  echo Install Python from python.org and rerun setup_windows.bat.
  exit /b 1
)

echo Python 3.11+ was not found. Installing with winget...
winget install --exact --id Python.Python.3.11 --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
  echo Failed to install Python automatically.
  exit /b 1
)

if exist "%SystemRoot%\py.exe" set "PATH=%SystemRoot%;%PATH%"
if exist "%LocalAppData%\Programs\Python\Launcher\py.exe" set "PATH=%LocalAppData%\Programs\Python\Launcher;%PATH%"

where py >nul 2>nul
if not errorlevel 1 goto :eof

echo Python was installed, but the py launcher is not visible in this shell yet.
echo Close this window and rerun setup_windows.bat.
exit /b 1

:ensure_ffmpeg
where ffmpeg >nul 2>nul
if not errorlevel 1 goto :eof

where winget >nul 2>nul
if errorlevel 1 (
  echo Warning: FFmpeg was not found and winget is unavailable.
  echo Install FFmpeg manually later if you need video and compressed audio formats.
  goto :eof
)

echo FFmpeg was not found. Installing with winget...
winget install --exact --id Gyan.FFmpeg --accept-package-agreements --accept-source-agreements
if errorlevel 1 (
  echo Warning: Failed to install FFmpeg automatically.
  echo Install FFmpeg manually later if needed.
  goto :eof
)

if exist "%LocalAppData%\Microsoft\WinGet\Links\ffmpeg.exe" set "PATH=%LocalAppData%\Microsoft\WinGet\Links;%PATH%"
if exist "%ProgramFiles%\WinGet\Links\ffmpeg.exe" set "PATH=%ProgramFiles%\WinGet\Links;%PATH%"
if exist "%ProgramFiles(x86)%\WinGet\Links\ffmpeg.exe" set "PATH=%ProgramFiles(x86)%\WinGet\Links;%PATH%"
goto :eof

:usage
echo Usage: setup_windows.bat [auto^|cpu^|amd^|nvidia] [--skip-shortcut] [--download-models model1 model2 ...]
echo.
echo Examples:
echo   setup_windows.bat
echo   setup_windows.bat nvidia
echo   setup_windows.bat auto --download-models tiny base small
exit /b 1