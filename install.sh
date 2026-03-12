#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$APP_DIR/.venv"
PROFILE_FILE="$APP_DIR/.whisper-profile.env"

usage() {
	cat <<'EOF'
Usage: ./install.sh [auto|cpu|amd|nvidia]

Profiles:
	auto    Detect hardware and choose a sensible setup for this machine
	cpu     Install CPU-only runtime
	amd     Install the AMD profile (currently CPU backend, no CUDA libraries)
	nvidia  Install the NVIDIA CUDA profile
EOF
}

detect_profile() {
	if command -v nvidia-smi >/dev/null 2>&1; then
		echo "nvidia"
		return
	fi

	if command -v rocm-smi >/dev/null 2>&1 || command -v amd-smi >/dev/null 2>&1; then
		echo "amd"
		return
	fi

	if command -v lspci >/dev/null 2>&1; then
		local gpu_lines
		gpu_lines="$(lspci | grep -iE 'vga|3d|display' || true)"
		if grep -qi 'nvidia' <<<"$gpu_lines"; then
			echo "nvidia"
			return
		fi
		if grep -qiE 'amd/ati|advanced micro devices|radeon' <<<"$gpu_lines"; then
			echo "amd"
			return
		fi
	fi

	echo "cpu"
}

write_profile() {
	local profile="$1"
	cat > "$PROFILE_FILE" <<EOF
WHISPER_ACCELERATOR=$profile
EOF
}

PROFILE="${1:-auto}"
case "$PROFILE" in
	auto)
		PROFILE="$(detect_profile)"
		;;
	cpu|amd|nvidia)
		;;
	-h|--help)
		usage
		exit 0
		;;
	*)
		usage
		exit 1
		;;
esac

echo "Selected install profile: $PROFILE"
echo "Installing system packages (sudo may prompt for password)..."
sudo apt-get update
sudo apt-get install -y ffmpeg python3-venv python3-tk libportaudio2 portaudio19-dev pciutils

echo "Recreating virtual environment for selected profile..."
rm -rf "$VENV_DIR"
echo "Creating virtual environment..."
python3 -m venv "$VENV_DIR"

echo "Installing Python packages..."
"$VENV_DIR/bin/pip" install --upgrade pip wheel setuptools
"$VENV_DIR/bin/pip" install faster-whisper sounddevice

if [[ "$PROFILE" == "nvidia" ]]; then
	echo "Installing NVIDIA CUDA libraries for GPU acceleration..."
	"$VENV_DIR/bin/pip" install nvidia-cublas-cu12 nvidia-cudnn-cu12 nvidia-cuda-runtime-cu12
elif [[ "$PROFILE" == "amd" ]]; then
	echo "AMD profile selected. This app uses the CPU backend on AMD with the current faster-whisper build."
	echo "No NVIDIA CUDA libraries will be installed."
else
	echo "CPU profile selected. Skipping GPU-specific runtime libraries."
fi

write_profile "$PROFILE"

echo "Install complete. Launch with: $APP_DIR/launch.sh"
