@echo off
setlocal

set "APP_DIR=%~dp0"
set "VENV_PY=%APP_DIR%.venv\Scripts\python.exe"
set "NVIDIA_SITE_PACKAGES=%APP_DIR%.venv\Lib\site-packages\nvidia"
set "BUNDLED_FFMPEG_DIR=%APP_DIR%tools\ffmpeg\bin"

set HF_HUB_ENABLE_HF_TRANSFER=1

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

if exist "%NVIDIA_SITE_PACKAGES%\cublas\bin" set "PATH=%NVIDIA_SITE_PACKAGES%\cublas\bin;%PATH%"
if exist "%NVIDIA_SITE_PACKAGES%\cudnn\bin" set "PATH=%NVIDIA_SITE_PACKAGES%\cudnn\bin;%PATH%"
if exist "%NVIDIA_SITE_PACKAGES%\cuda_runtime\bin" set "PATH=%NVIDIA_SITE_PACKAGES%\cuda_runtime\bin;%PATH%"
if exist "%NVIDIA_SITE_PACKAGES%\cuda_runtime\lib\x64" set "PATH=%NVIDIA_SITE_PACKAGES%\cuda_runtime\lib\x64;%PATH%"
if exist "%BUNDLED_FFMPEG_DIR%\ffmpeg.exe" set "PATH=%BUNDLED_FFMPEG_DIR%;%PATH%"

where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo Warning: ffmpeg.exe is not in PATH.
  echo Audio files such as WAV may still work, but video and many compressed formats will fail until FFmpeg is installed.
  echo.
)

"%VENV_PY%" "%APP_DIR%app.py"
if errorlevel 1 pause

endlocal
