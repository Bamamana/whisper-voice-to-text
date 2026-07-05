@echo off
setlocal

set "APP_DIR=%~dp0"
set "ROOT_DIR=%APP_DIR%..\"
set "BUNDLED_PY=%ROOT_DIR%python-runtime\python.exe"
set "VENV_PY=%APP_DIR%.venv\Scripts\python.exe"
set "SITE_PACKAGES=%APP_DIR%.venv\Lib\site-packages"
set "FFMPEG_DIR=%ROOT_DIR%tools\ffmpeg\bin"

if exist "%FFMPEG_DIR%\ffmpeg.exe" set "PATH=%FFMPEG_DIR%;%PATH%"

if exist "%BUNDLED_PY%" (
  if not exist "%SITE_PACKAGES%" (
    echo V6 site-packages were not found.
    echo Reinstall the offline package.
    pause
    exit /b 1
  )

  if defined PYTHONPATH (
    set "PYTHONPATH=%SITE_PACKAGES%;%PYTHONPATH%"
  ) else (
    set "PYTHONPATH=%SITE_PACKAGES%"
  )

  "%BUNDLED_PY%" "%APP_DIR%app_v6.py"
  if errorlevel 1 pause
  endlocal
  exit /b %errorlevel%
)

if not exist "%VENV_PY%" (
  echo V6 virtual environment not found.
  echo Run install_windows_v6.bat first or reinstall the offline package.
  pause
  exit /b 1
)

"%VENV_PY%" "%APP_DIR%app_v6.py"
if errorlevel 1 pause

endlocal
