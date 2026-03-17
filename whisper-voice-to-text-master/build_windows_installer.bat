@echo off
setlocal EnableExtensions

set "APP_DIR=%~dp0"
set "ISS_FILE=%APP_DIR%installer\WhisperVoiceToText.iss"
set "ISCC_CMD="

where iscc >nul 2>nul
if not errorlevel 1 (
  for /f "delims=" %%I in ('where iscc') do (
    set "ISCC_CMD=%%I"
    goto :compile
  )
)

if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC_CMD=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC_CMD if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC_CMD=%ProgramFiles%\Inno Setup 6\ISCC.exe"

if not defined ISCC_CMD (
  echo Inno Setup 6 was not found.
  echo Install it from https://jrsoftware.org/isinfo.php and rerun this script.
  exit /b 1
)

:compile
echo Building Windows installer...
"%ISCC_CMD%" "%ISS_FILE%"
if errorlevel 1 exit /b 1

echo.
echo Installer build complete.
echo Output folder:
echo   %APP_DIR%dist\windows-installer
exit /b 0