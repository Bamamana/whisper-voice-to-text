#!/usr/bin/env python3
import argparse
import os
import platform
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
import wave
import shutil
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import numpy as np
import sounddevice as sd


def _configure_windows_cuda_dlls() -> None:
    if platform.system().lower() != "windows":
        return

    app_dir = Path(__file__).resolve().parent
    candidate_dirs = [
        app_dir / ".venv" / "Lib" / "site-packages" / "nvidia" / "cublas" / "bin",
        app_dir / ".venv" / "Lib" / "site-packages" / "nvidia" / "cudnn" / "bin",
        app_dir / ".venv" / "Lib" / "site-packages" / "nvidia" / "cuda_runtime" / "bin",
        app_dir / ".venv" / "Lib" / "site-packages" / "nvidia" / "cuda_runtime" / "lib" / "x64",
    ]

    existing_dirs = [str(path) for path in candidate_dirs if path.exists()]
    if not existing_dirs:
        return

    os.environ["PATH"] = os.pathsep.join(existing_dirs + [os.environ.get("PATH", "")])
    add_dll_directory = getattr(os, "add_dll_directory", None)
    if add_dll_directory is None:
        return

    for dll_dir in existing_dirs:
        try:
            add_dll_directory(dll_dir)
        except OSError:
            continue


_configure_windows_cuda_dlls()

from faster_whisper import WhisperModel

MODEL_CHOICES = ["tiny", "base", "small", "medium", "large-v3"]

_CUDA_ERROR_TOKENS = ("libcublas", "cublas", "cuda", "cudnn", "libcudart", "cudart")


def _command_output(command: list[str]) -> str:
    try:
        return subprocess.check_output(command, text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return ""


def _detect_windows_gpu_vendor() -> str:
    if shutil.which("nvidia-smi") is not None:
        return "nvidia"
    if shutil.which("amd-smi") is not None:
        return "amd"

    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if powershell is None:
        return "unknown"

    output = _command_output(
        [
            powershell,
            "-NoProfile",
            "-Command",
            "(Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name) -join \"`n\"",
        ]
    )
    lowered = output.lower()
    if "nvidia" in lowered:
        return "nvidia"
    if any(token in lowered for token in ["amd", "radeon", "advanced micro devices"]):
        return "amd"
    return "unknown"


def _detect_linux_gpu_vendor() -> str:
    if shutil.which("nvidia-smi") is not None:
        return "nvidia"
    if shutil.which("rocm-smi") is not None or shutil.which("amd-smi") is not None:
        return "amd"

    lspci = shutil.which("lspci")
    if lspci is None:
        return "unknown"

    output = _command_output([lspci])
    lowered = output.lower()
    if "nvidia" in lowered:
        return "nvidia"
    if any(token in lowered for token in ["amd/ati", "advanced micro devices", "radeon"]):
        return "amd"
    return "unknown"


def detect_gpu_vendor() -> str:
    system_name = platform.system().lower()
    if system_name == "windows":
        return _detect_windows_gpu_vendor()
    if system_name == "linux":
        return _detect_linux_gpu_vendor()
    return "unknown"


def load_install_profile(app_dir: Path) -> str:
    env_value = os.environ.get("WHISPER_ACCELERATOR", "").strip().lower()
    if env_value in {"auto", "cpu", "nvidia", "amd"}:
        return env_value

    profile_file = app_dir / ".whisper-profile.env"
    if not profile_file.exists():
        return "auto"

    for line in profile_file.read_text(encoding="utf-8").splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip() == "WHISPER_ACCELERATOR":
            candidate = value.strip().lower()
            if candidate in {"auto", "cpu", "nvidia", "amd"}:
                return candidate
    return "auto"


def resolve_compute_backend(install_profile: str, detected_gpu_vendor: str) -> tuple[str, str, str]:
    if install_profile == "nvidia":
        if detected_gpu_vendor == "nvidia":
            return "cuda", "float16", "NVIDIA GPU (CUDA)"
        return "cpu", "int8", "CPU (NVIDIA profile selected, but no NVIDIA GPU detected)"

    if install_profile == "amd":
        if detected_gpu_vendor == "amd":
            return "cpu", "int8", "AMD GPU detected (CPU backend active)"
        return "cpu", "int8", "CPU (AMD profile selected)"

    if detected_gpu_vendor == "nvidia":
        return "cuda", "float16", "NVIDIA GPU (CUDA)"
    if detected_gpu_vendor == "amd":
        return "cpu", "int8", "AMD GPU detected (CPU backend active)"
    return "cpu", "int8", "CPU"


def _is_cuda_error(error_text: str) -> bool:
    lowered = error_text.lower()
    return any(token in lowered for token in _CUDA_ERROR_TOKENS)


def format_timestamp(seconds: float) -> str:
    total_ms = int(round(max(0.0, seconds) * 1000))
    hours, remainder = divmod(total_ms, 3600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def transcribe_audio(model: WhisperModel, filepath: str, with_timestamps: bool = False, progress_callback=None) -> str:
    segments, info = model.transcribe(filepath, beam_size=5)
    duration = getattr(info, "duration", 0.0) or 0.0

    lines = []
    for segment in segments:
        text = segment.text.strip()
        if text:
            if with_timestamps:
                lines.append(f"[{format_timestamp(segment.start)} --> {format_timestamp(segment.end)}] {text}")
            else:
                lines.append(text)
        if progress_callback is not None and duration > 0:
            progress_callback(min(99.0, max(0.0, segment.end / duration * 100.0)))

    if progress_callback is not None:
        progress_callback(100.0)
    return "\n".join(lines).strip()


def load_model_with_fallback(model_name: str, device: str, compute_type: str, cache_dir) -> tuple[WhisperModel, str, str, str | None]:
    try:
        model = WhisperModel(
            model_name,
            device=device,
            compute_type=compute_type,
            download_root=str(cache_dir),
        )
        return model, device, compute_type, None
    except Exception as exc:
        if device == "cuda" and _is_cuda_error(str(exc)):
            model = WhisperModel(
                model_name,
                device="cpu",
                compute_type="int8",
                download_root=str(cache_dir),
            )
            return model, "cpu", "int8", str(exc)
        raise


def transcribe_with_cuda_fallback(
    model: WhisperModel,
    model_name: str,
    device: str,
    compute_type: str,
    cache_dir,
    filepath: str,
    with_timestamps: bool = False,
    progress_callback=None,
) -> tuple[str, WhisperModel, str, str, str | None]:
    try:
        text = transcribe_audio(model, filepath, with_timestamps, progress_callback)
        return text, model, device, compute_type, None
    except Exception as exc:
        if device == "cuda" and _is_cuda_error(str(exc)):
            fallback_model = WhisperModel(
                model_name,
                device="cpu",
                compute_type="int8",
                download_root=str(cache_dir),
            )
            text = transcribe_audio(fallback_model, filepath, with_timestamps, progress_callback)
            return text, fallback_model, "cpu", "int8", str(exc)
        raise


class WhisperApp:
    def __init__(self, root: tk.Tk) -> None:
        self.app_dir = Path(__file__).resolve().parent
        self.root = root
        self.root.title("Whisper Voice-to-Text")
        self.root.geometry("920x560")

        self.model_var = tk.StringVar(value="base")
        self.timestamps_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value="Ready")
        self.file_var = tk.StringVar(value="No audio file selected")
        self.recording_status_var = tk.StringVar(value="Mic idle")
        self.recording = False
        self.record_stream = None
        self.recorded_chunks = []
        self.sample_rate = 16000
        self.is_transcribing = False
        self.current_job_id = 0
        self.model_cache_dir = self.app_dir / "model-cache"
        self.model_cache_dir.mkdir(parents=True, exist_ok=True)
        self.loaded_model_name = None
        self.loaded_model = None
        self.model_loading = False
        self.install_profile = self._load_install_profile()
        self.detected_gpu_vendor = self._detect_gpu_vendor()
        self.device, self.compute_type, self.device_label = self._resolve_compute_backend()

        self.model_load_status_var = tk.StringVar(value="No model loaded")
        self.device_status_var = tk.StringVar(value=self._device_status_text())

        self._build_ui()
        self._request_model_load(self.model_var.get())

    def _load_install_profile(self) -> str:
        return load_install_profile(self.app_dir)

    def _detect_gpu_vendor(self) -> str:
        return detect_gpu_vendor()

    def _resolve_compute_backend(self) -> tuple[str, str, str]:
        return resolve_compute_backend(self.install_profile, self.detected_gpu_vendor)

    def _device_status_text(self) -> str:
        profile_text = f"Install profile: {self.install_profile}"
        return f"Compute device: {self.device_label} | {profile_text}"

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=12)
        container.pack(fill=tk.BOTH, expand=True)

        top = ttk.Frame(container)
        top.pack(fill=tk.X)

        ttk.Button(top, text="Choose Audio/Video File", command=self.choose_file).pack(side=tk.LEFT)
        ttk.Button(top, text="🎤 Start Mic", command=self.start_recording).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(top, text="⏹ Stop Mic", command=self.stop_recording).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Label(top, text="Model:").pack(side=tk.LEFT, padx=(12, 4))
        self.model_combo = ttk.Combobox(
            top,
            textvariable=self.model_var,
            values=MODEL_CHOICES,
            width=10,
            state="readonly",
        )
        self.model_combo.pack(side=tk.LEFT)
        self.model_combo.bind("<<ComboboxSelected>>", self._on_model_changed)

        self.load_model_button = ttk.Button(top, text="Load Model", command=self.load_selected_model)
        self.load_model_button.pack(side=tk.LEFT, padx=(6, 0))

        ttk.Checkbutton(top, text="Timestamps", variable=self.timestamps_var).pack(side=tk.LEFT, padx=(8, 0))

        self.transcribe_button = ttk.Button(top, text="Transcribe", command=self.start_transcribe)
        self.transcribe_button.pack(side=tk.LEFT, padx=(12, 0))
        self.copy_button = ttk.Button(top, text="Copy", command=self.copy_output)
        self.copy_button.pack(side=tk.LEFT, padx=(6, 0))

        ttk.Label(container, textvariable=self.file_var).pack(anchor="w", pady=(10, 8))
        ttk.Label(container, textvariable=self.recording_status_var).pack(anchor="w", pady=(0, 8))
        ttk.Label(container, textvariable=self.model_load_status_var).pack(anchor="w", pady=(0, 4))
        ttk.Label(container, textvariable=self.device_status_var).pack(anchor="w", pady=(0, 8))

        self.output = tk.Text(container, wrap=tk.WORD, height=22)
        self.output.pack(fill=tk.BOTH, expand=True)

        self.progress = ttk.Progressbar(container, mode="indeterminate")
        self.progress.pack(fill=tk.X, pady=(8, 0))

        status = ttk.Label(container, textvariable=self.status_var)
        status.pack(anchor="w", pady=(8, 0))

    def choose_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Select audio or video file",
            filetypes=[
                ("Media files", "*.mp3 *.wav *.m4a *.flac *.mp4 *.mkv *.mov *.webm"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self.file_var.set(path)

    def _on_model_changed(self, _event=None) -> None:
        self._request_model_load(self.model_var.get())

    def load_selected_model(self) -> None:
        self._request_model_load(self.model_var.get())

    def _request_model_load(self, model_name: str) -> None:
        if self.model_loading:
            self.status_var.set("Model load already running. Please wait.")
            return
        if self.loaded_model_name == model_name and self.loaded_model is not None:
            self.model_load_status_var.set(f"Current model loaded: {model_name}")
            return

        self.model_loading = True
        self.model_load_status_var.set(f"Loading model: {model_name}...")
        self.status_var.set(f"Loading model: {model_name}")
        self.transcribe_button.configure(state=tk.DISABLED)
        self.load_model_button.configure(state=tk.DISABLED)
        self.progress.configure(mode="indeterminate")
        self.progress.start(10)

        thread = threading.Thread(target=self._load_model_worker, args=(model_name,), daemon=True)
        thread.start()

    def _load_model_worker(self, model_name: str) -> None:
        try:
            model, device, compute_type, fallback_error = load_model_with_fallback(
                model_name,
                self.device,
                self.compute_type,
                self.model_cache_dir,
            )
            if fallback_error is not None:
                self.device = device
                self.compute_type = compute_type
                self.root.after(0, self._model_loaded_with_fallback, model_name, model, fallback_error)
                return
            self.root.after(0, self._model_loaded, model_name, model)
        except Exception as exc:
            self.root.after(0, self._model_load_failed, model_name, str(exc))

    def _model_loaded_with_fallback(self, model_name: str, model: WhisperModel, original_error: str) -> None:
        self.device_label = "CPU (CUDA unavailable)"
        self.device_status_var.set(self._device_status_text())
        self._model_loaded(model_name, model)
        self.status_var.set("Model loaded on CPU (CUDA unavailable)")
        messagebox.showwarning(
            "CUDA unavailable",
            "NVIDIA CUDA libraries were not available, so the app switched to CPU automatically.\n\n"
            f"Original error:\n{original_error}",
        )

    def _model_loaded(self, model_name: str, model: WhisperModel) -> None:
        self.loaded_model = model
        self.loaded_model_name = model_name
        self.model_loading = False
        self.progress.stop()
        self.load_model_button.configure(state=tk.NORMAL)
        self.transcribe_button.configure(state=tk.NORMAL if not self.is_transcribing else tk.DISABLED)
        self.model_load_status_var.set(f"Current model loaded: {model_name}")
        self.status_var.set(f"Model ready: {model_name}")

    def _model_load_failed(self, model_name: str, error: str) -> None:
        self.model_loading = False
        self.progress.stop()
        self.load_model_button.configure(state=tk.NORMAL)
        self.transcribe_button.configure(state=tk.NORMAL if not self.is_transcribing else tk.DISABLED)
        self.model_load_status_var.set(f"Model load failed: {model_name}")
        self.status_var.set("Model load failed")
        messagebox.showerror("Model load error", error)

    def copy_output(self) -> None:
        text = self.output.get("1.0", tk.END).strip()
        if not text:
            self.status_var.set("Nothing to copy")
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.status_var.set("Transcript copied to clipboard")

    def start_transcribe(self) -> None:
        filepath = self.file_var.get()
        if filepath == "No audio file selected" or not os.path.exists(filepath):
            messagebox.showerror("No file", "Please choose a valid audio/video file first.")
            return

        self._start_transcription(filepath, "Loading model and transcribing... this can take a while.")

    def start_recording(self) -> None:
        if self.recording:
            return

        self.recorded_chunks = []

        def callback(indata, frames, time_info, status):
            if status:
                self.root.after(0, self.recording_status_var.set, f"Mic warning: {status}")
            self.recorded_chunks.append(indata.copy())

        try:
            self.record_stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype="int16",
                callback=callback,
            )
            self.record_stream.start()
            self.recording = True
            self.recording_status_var.set("Recording... click Stop Mic when done")
            self.status_var.set("Mic recording in progress")
        except Exception as exc:
            self.recording = False
            self.record_stream = None
            messagebox.showerror("Mic error", str(exc))

    def stop_recording(self) -> None:
        if not self.recording or self.record_stream is None:
            return

        try:
            self.record_stream.stop()
            self.record_stream.close()
        finally:
            self.record_stream = None
            self.recording = False

        if not self.recorded_chunks:
            self.recording_status_var.set("Mic idle")
            messagebox.showerror("No audio", "No microphone audio was captured.")
            return

        audio = np.concatenate(self.recorded_chunks, axis=0)
        temp_wav = tempfile.NamedTemporaryFile(prefix="whisper_mic_", suffix=".wav", delete=False)
        temp_wav_path = temp_wav.name
        temp_wav.close()

        with wave.open(temp_wav_path, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio.tobytes())

        self.file_var.set(temp_wav_path)
        self.recording_status_var.set("Mic recording saved, transcribing now...")
        self._start_transcription(temp_wav_path, "Loading model and transcribing mic recording...")

    def _start_transcription(self, filepath: str, status_message: str) -> None:
        if self.is_transcribing:
            self.status_var.set("Transcription already running. Please wait.")
            return

        if self.model_loading:
            self.status_var.set("Wait for model loading to finish.")
            return

        if self.loaded_model is None or self.loaded_model_name != self.model_var.get():
            self.status_var.set("Selected model is not loaded yet. Loading now...")
            self._request_model_load(self.model_var.get())
            return

        self.is_transcribing = True
        self.current_job_id += 1
        job_id = self.current_job_id
        self.status_var.set(status_message)
        self.output.delete("1.0", tk.END)
        self.transcribe_button.configure(state=tk.DISABLED)
        self.progress.configure(mode="determinate", maximum=100, value=0)

        with_timestamps = self.timestamps_var.get()
        thread = threading.Thread(target=self._transcribe, args=(filepath, self.model_var.get(), job_id, with_timestamps), daemon=True)
        thread.start()

    def _update_progress(self, percent: float, job_id: int) -> None:
        if job_id != self.current_job_id:
            return

        self.progress.configure(value=percent)
        if percent < 100:
            self.status_var.set(f"Transcribing... {percent:.0f}%")

    def _transcribe(self, filepath: str, model_name: str, job_id: int, with_timestamps: bool) -> None:
        def report_progress(percent: float) -> None:
            self.root.after(0, self._update_progress, percent, job_id)

        try:
            model = self.loaded_model
            if model is None or self.loaded_model_name != model_name:
                raise RuntimeError("Selected model is not loaded. Please load the model first.")
            text, model, device, compute_type, fallback_error = transcribe_with_cuda_fallback(
                model,
                model_name,
                self.device,
                self.compute_type,
                self.model_cache_dir,
                filepath,
                with_timestamps,
                report_progress,
            )

            output_dir = Path(filepath).parent
            output_file = output_dir / f"{Path(filepath).stem}.whisper.txt"
            output_file.write_text(text, encoding="utf-8")

            if fallback_error is not None:
                self.root.after(0, self._transcribe_fallback_success, model_name, model, text, str(output_file), job_id)
                return
            self.root.after(0, self._show_result, text, str(output_file), job_id)
        except Exception as exc:
            self.root.after(0, self._show_error, str(exc), job_id)

    def _transcribe_fallback_success(self, model_name: str, model: WhisperModel, text: str, output_file: str, job_id: int) -> None:
        self.device = "cpu"
        self.compute_type = "int8"
        self.device_label = "CPU (CUDA unavailable)"
        self.loaded_model = model
        self.loaded_model_name = model_name
        self.device_status_var.set(self._device_status_text())
        self._show_result(text, output_file, job_id)
        messagebox.showwarning(
            "CUDA unavailable during transcription",
            "CUDA failed while transcribing, so the app automatically switched to CPU and completed the transcript.",
        )

    def _show_result(self, text: str, output_file: str, job_id: int) -> None:
        if job_id != self.current_job_id:
            return

        self.output.delete("1.0", tk.END)
        self.output.insert("1.0", text)
        self.is_transcribing = False
        self.progress.stop()
        self.progress.configure(value=100)
        self.transcribe_button.configure(state=tk.NORMAL)
        self.status_var.set(f"Done. Saved transcript to: {output_file}")

    def _show_error(self, error: str, job_id: int) -> None:
        if job_id != self.current_job_id:
            return

        self.is_transcribing = False
        self.progress.stop()
        self.transcribe_button.configure(state=tk.NORMAL)
        self.status_var.set("Transcription failed")
        messagebox.showerror("Error", error)


def _parse_bool_arg(value) -> bool:
    if isinstance(value, bool):
        return value
    lowered = str(value).strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"expected true or false, got: {value}")


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="whisper-voice-to-text",
        description="Local Whisper voice-to-text. Pass an audio/video file for command-line transcription, or run with no arguments to launch the desktop app.",
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Audio or video file to transcribe (for example: input.mp3). Omit to launch the GUI.",
    )
    parser.add_argument(
        "--model",
        "-model",
        default="base",
        choices=MODEL_CHOICES,
        help="Whisper model to use (default: base)",
    )
    parser.add_argument(
        "--timestamps",
        "-timestamps",
        nargs="?",
        const=True,
        default=False,
        type=_parse_bool_arg,
        help="Prefix each segment with [HH:MM:SS.mmm --> HH:MM:SS.mmm]. Use '--timestamps', '--timestamps true', or '--timestamps false' (default: false)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Where to save the transcript (default: <input name>.whisper.txt next to the source file)",
    )
    return parser


def run_cli(args: argparse.Namespace) -> int:
    input_path = Path(args.input).expanduser()
    if not input_path.exists():
        print(f"Error: input file not found: {input_path}", file=sys.stderr)
        return 2

    app_dir = Path(__file__).resolve().parent
    cache_dir = app_dir / "model-cache"
    cache_dir.mkdir(parents=True, exist_ok=True)

    install_profile = load_install_profile(app_dir)
    device, compute_type, device_label = resolve_compute_backend(install_profile, detect_gpu_vendor())
    print(f"Compute device: {device_label} | Install profile: {install_profile}")

    print(f"Loading model: {args.model} ...", flush=True)
    try:
        model, device, compute_type, fallback_error = load_model_with_fallback(
            args.model, device, compute_type, cache_dir
        )
    except Exception as exc:
        print(f"Error: model load failed: {exc}", file=sys.stderr)
        return 1
    if fallback_error is not None:
        print("CUDA unavailable, switched to CPU automatically.", file=sys.stderr)

    def report_progress(percent: float) -> None:
        print(f"\rTranscribing... {percent:5.1f}%", end="", file=sys.stderr, flush=True)

    try:
        text, model, device, compute_type, fallback_error = transcribe_with_cuda_fallback(
            model,
            args.model,
            device,
            compute_type,
            cache_dir,
            str(input_path),
            with_timestamps=args.timestamps,
            progress_callback=report_progress,
        )
    except Exception as exc:
        print(f"\nError: transcription failed: {exc}", file=sys.stderr)
        return 1
    print(file=sys.stderr)
    if fallback_error is not None:
        print("CUDA failed during transcription, completed on CPU.", file=sys.stderr)

    if args.output:
        output_path = Path(args.output).expanduser()
    else:
        output_path = input_path.parent / f"{input_path.stem}.whisper.txt"
    output_path.write_text(text, encoding="utf-8")

    print(f"Saved transcript to: {output_path}")
    print(text)
    return 0


def main() -> None:
    args = build_argument_parser().parse_args()
    if args.input:
        raise SystemExit(run_cli(args))

    root = tk.Tk()
    app = WhisperApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
