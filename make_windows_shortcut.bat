@echo off
setlocal

set "APP_DIR=%~dp0"
set "SHORTCUT_NAME=Whisper Voice-to-Text.lnk"

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$shell = New-Object -ComObject WScript.Shell;" ^
  "$desktopPath = [Environment]::GetFolderPath('Desktop');" ^
  "$shortcutPath = Join-Path $desktopPath '%SHORTCUT_NAME%';" ^
  "$shortcut = $shell.CreateShortcut($shortcutPath);" ^
  "$shortcut.TargetPath = $env:ComSpec;" ^
  "$shortcut.Arguments = '/d /c """"%APP_DIR%windows_shortcut_launch.bat""""';" ^
  "$shortcut.WorkingDirectory = '%APP_DIR%';" ^
  "$shortcut.IconLocation = '%SystemRoot%\System32\shell32.dll,22';" ^
  "$shortcut.Save();" ^
  "Write-Output $shortcutPath"

if errorlevel 1 (
  echo Failed to create desktop shortcut.
  exit /b 1
)

echo Desktop shortcut created:
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "[Environment]::GetFolderPath('Desktop')"`) do set "DESKTOP_PATH=%%~I"
echo   %DESKTOP_PATH%\%SHORTCUT_NAME%
exit /b 0