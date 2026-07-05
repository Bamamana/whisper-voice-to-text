@echo off
setlocal EnableExtensions

set "APP_DIR=%~dp0"
set "ISS_FILE=%APP_DIR%installer\WhisperVoiceToFormV3Offline.iss"
set "PREPARE_PS=%APP_DIR%prepare_v3_offline_payload.ps1"
set "STAGE_DIR=%APP_DIR%build\offline-v3-stage"
set "ISCC_CMD="

where iscc >nul 2>nul
if not errorlevel 1 (
  for /f "delims=" %%I in ('where iscc') do (
    set "ISCC_CMD=%%I"
    goto :compile
  )
)

if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" set "ISCC_CMD=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC_CMD=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC_CMD if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC_CMD=%ProgramFiles%\Inno Setup 6\ISCC.exe"

if not defined ISCC_CMD (
  echo Inno Setup 6 was not found.
  echo Install it from https://jrsoftware.org/isinfo.php and rerun this script.
  exit /b 1
)

:compile
echo Preparing V3 offline installer payload...
powershell -NoProfile -ExecutionPolicy Bypass -File "%PREPARE_PS%" -StageDir "%STAGE_DIR%"
if errorlevel 1 exit /b 1

echo Building V3 Offline Windows installer...
"%ISCC_CMD%" "/DOfflineStageDir=%STAGE_DIR%" "%ISS_FILE%"
if errorlevel 1 exit /b 1

echo.
echo V3 offline installer build complete.
echo Output folder:
echo   %APP_DIR%dist\windows-installer-v3-offline
exit /b 0
