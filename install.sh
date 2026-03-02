#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$APP_DIR/.venv"

echo "Installing system packages (sudo may prompt for password)..."
sudo apt-get update
sudo apt-get install -y ffmpeg python3-venv python3-tk libportaudio2 portaudio19-dev

echo "Creating virtual environment..."
python3 -m venv "$VENV_DIR"

echo "Installing Python packages..."
"$VENV_DIR/bin/pip" install --upgrade pip wheel setuptools
"$VENV_DIR/bin/pip" install faster-whisper sounddevice

echo "Installing NVIDIA CUDA libraries for GPU acceleration..."
"$VENV_DIR/bin/pip" install nvidia-cublas-cu12 nvidia-cudnn-cu12 nvidia-cuda-runtime-cu12 || echo "Note: CUDA libraries not installed (GPU acceleration may not be available)"

echo "Install complete. Launch with: $APP_DIR/launch.sh"
