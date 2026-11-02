@echo off
REM Starts the local whisper.cpp STT backend and the OpenAI-compatible proxy.
REM Use this after a reboot, or whenever the app reports it cannot reach the server.
REM Then in the app choose provider "Local whisper.cpp (this PC)" (Base URL http://127.0.0.1:8090/v1).

set "WHISPER_DIR=%USERPROFILE%\whisper.cpp"
set "MODEL=%WHISPER_DIR%\models\ggml-large-v3-turbo-q8_0.bin"
set "PROXY=%~dp0local_whisper_openai_proxy.py"
REM CUDA (NVIDIA) backend; falls back to the CPU build if the CUDA build is missing.
set "WHISPER_EXE=%WHISPER_DIR%\cuda\Release\whisper-server.exe"
if not exist "%WHISPER_EXE%" set "WHISPER_EXE=%WHISPER_DIR%\build\bin\whisper-server.exe"

if not exist "%MODEL%" (
  echo Model not found at "%MODEL%".
  pause
  exit /b 1
)

echo Starting whisper.cpp backend on http://127.0.0.1:8080 ...
start "whisper.cpp backend" "%WHISPER_EXE%" -m "%MODEL%" --host 127.0.0.1 --port 8080 --convert --tmp-dir "%TEMP%" -l auto

echo Starting OpenAI-compatible proxy on http://127.0.0.1:8090/v1 ...
start "whisper OpenAI proxy" python "%PROXY%" --host 127.0.0.1 --port 8090

echo.
echo Both services launched in separate windows. Leave them running while you use the app.
