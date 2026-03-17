#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$APP_DIR/.venv"
PROFILE_FILE="$APP_DIR/.whisper-profile.env"

if [[ -f "$PROFILE_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$PROFILE_FILE"
fi

: "${WHISPER_ACCELERATOR:=auto}"

if [[ ! -x "$VENV_DIR/bin/python" ]]; then
  "$APP_DIR/install.sh"
fi

if [[ "$WHISPER_ACCELERATOR" == "nvidia" || "$WHISPER_ACCELERATOR" == "auto" ]]; then
  SITE_PACKAGES="$($VENV_DIR/bin/python -c 'import site; print(site.getsitepackages()[0])')"
  NVIDIA_LIB_DIRS=(
    "$SITE_PACKAGES/nvidia/cublas/lib"
    "$SITE_PACKAGES/nvidia/cudnn/lib"
    "$SITE_PACKAGES/nvidia/cuda_runtime/lib"
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
fi

exec "$VENV_DIR/bin/python" "$APP_DIR/app.py"
