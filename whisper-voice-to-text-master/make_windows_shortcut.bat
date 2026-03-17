@echo off
setlocal

set "APP_DIR=%~dp0"
set "SHORTCUT_NAME=Whisper Voice-to-Text.lnk"
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\%SHORTCUT_NAME%"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$shell = New-Object -ComObject WScript.Shell;" ^
  "$shortcut = $shell.CreateShortcut('%SHORTCUT_PATH%');" ^
  "$shortcut.TargetPath = '%APP_DIR%windows_launch.bat';" ^
  "$shortcut.WorkingDirectory = '%APP_DIR%';" ^
  "$shortcut.IconLocation = '%SystemRoot%\\System32\\shell32.dll,22';" ^
  "$shortcut.Save()"

if errorlevel 1 (
  echo Failed to create desktop shortcut.
  exit /b 1
)

echo Desktop shortcut created:
echo   %SHORTCUT_PATH%
exit /b 0