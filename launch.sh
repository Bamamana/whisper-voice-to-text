#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$APP_DIR/.venv"

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  "$APP_DIR/install.sh"
fi

# Set LD_LIBRARY_PATH for CUDA libraries installed via pip (nvidia-cublas-cu12, etc.)
NVIDIA_LIB_DIRS=(
  "$VENV_DIR/lib/python3.12/site-packages/nvidia/cublas/lib"
  "$VENV_DIR/lib/python3.12/site-packages/nvidia/cudnn/lib"
  "$VENV_DIR/lib/python3.12/site-packages/nvidia/cuda_runtime/lib"
)
CUDA_LD_PATH=""
for dir in "${NVIDIA_LIB_DIRS[@]}"; do
  if [[ -d "$dir" ]]; then
    if [[ -n "$CUDA_LD_PATH" ]]; then
      CUDA_LD_PATH="$CUDA_LD_PATH:$dir"
    else
      CUDA_LD_PATH="$dir"
    fi
  fi
done
if [[ -n "$CUDA_LD_PATH" ]]; then
  export LD_LIBRARY_PATH="$CUDA_LD_PATH${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
fi

exec "$VENV_DIR/bin/python" "$APP_DIR/app.py"
