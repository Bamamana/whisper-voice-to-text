@echo off
setlocal EnableExtensions

REM One-click launcher: starts the local whisper.cpp (CUDA) STT backend and the
REM OpenAI-compatible proxy if they are not already running, waits until they are
REM ready, then opens the web app in the default browser.
REM
REM Double-click this, or use the "Whisper Voice-to-Text (Local)" desktop shortcut.

set "APP_DIR=%~dp0"
set "WHISPER_DIR=%USERPROFILE%\whisper.cpp"
set "MODEL=%WHISPER_DIR%\models\ggml-large-v3-turbo-q8_0.bin"
set "PROXY=%APP_DIR%local_whisper_openai_proxy.py"
set "WHISPER_EXE=%WHISPER_DIR%\cuda\Release\whisper-server.exe"
if not exist "%WHISPER_EXE%" set "WHISPER_EXE=%WHISPER_DIR%\build\bin\whisper-server.exe"

REM Web app to open. Change this line to open Whisper-V1.html instead if preferred.
set "HTML=%APP_DIR%Whisper-V1-API.html"

if not exist "%MODEL%" (
  echo Model not found at "%MODEL%".
  pause
  exit /b 1
)

if not exist "%HTML%" (
  echo App page not found at "%HTML%".
  pause
  exit /b 1
)

call :portopen 8080
if errorlevel 1 (
  echo Starting whisper.cpp backend on http://127.0.0.1:8080 ...
  start "whisper.cpp backend" "%WHISPER_EXE%" -m "%MODEL%" --host 127.0.0.1 --port 8080 --convert --tmp-dir "%TEMP%" -l auto
) else (
  echo whisper.cpp backend already running on port 8080.
)

call :portopen 8090
if errorlevel 1 (
  echo Starting OpenAI-compatible proxy on http://127.0.0.1:8090/v1 ...
  start "whisper OpenAI proxy" python "%PROXY%" --host 127.0.0.1 --port 8090
) else (
  echo OpenAI-compatible proxy already running on port 8090.
)

echo Waiting for the local speech-to-text server to be ready...
for /l %%i in (1,1,90) do (
  call :portopen 8080
  if not errorlevel 1 (
    call :portopen 8090
    if not errorlevel 1 goto ready
  )
  >nul 2>&1 timeout /t 1 /nobreak
)
echo WARNING: timed out waiting for the server. Opening the app anyway.

:ready
REM Open the app as a file:// URL with "#local" so it selects the local server
REM (this works from a plain file path, unlike passing a fragment to "start").
set "HTML_URL=file:///%HTML:\=/%"
start "" "%HTML_URL%#local"
exit /b 0

:portopen
powershell -NoProfile -Command "$c=New-Object Net.Sockets.TcpClient;try{$c.Connect('127.0.0.1',%1);$c.Close();exit 0}catch{exit 1}"
exit /b %errorlevel%
