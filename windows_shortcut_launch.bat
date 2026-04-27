@echo off
setlocal

set "APP_DIR=%~dp0"
set "VENV_PYTHONW=%APP_DIR%.venv\Scripts\pythonw.exe"
set "LAUNCHER_PYW=%APP_DIR%windows_launch.pyw"

if exist "%VENV_PYTHONW%" if exist "%LAUNCHER_PYW%" (
  start "" "%VENV_PYTHONW%" "%LAUNCHER_PYW%"
  exit /b 0
)

call "%APP_DIR%windows_launch.bat"
exit /b %ERRORLEVEL%