#!/usr/bin/env python3
import os
import platform
import subprocess
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


class WhisperApp:
    def __init__(self, root: tk.Tk) -> None:
        self.app_dir = Path(__file__).resolve().parent
        self.root = root
        self.root.title("Whisper Voice-to-Text")
        self.root.geometry("800x560")

        self.model_var = tk.StringVar(value="base")
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
        env_value = os.environ.get("WHISPER_ACCELERATOR", "").strip().lower()
        if env_value in {"auto", "cpu", "nvidia", "amd"}:
            return env_value

        profile_file = self.app_dir / ".whisper-profile.env"
        if not profile_file.exists():
            return "auto"

        for line in profile_file.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("=")
            if sep and key.strip() == "WHISPER_ACCELERATOR":
                candidate = value.strip().lower()
                if candidate in {"auto", "cpu", "nvidia", "amd"}:
                    return candidate
        return "auto"

    def _command_output(self, command: list[str]) -> str:
        try:
            return subprocess.check_output(command, text=True, stderr=subprocess.DEVNULL)
        except Exception:
            return ""

    def _detect_windows_gpu_vendor(self) -> str:
        if shutil.which("nvidia-smi") is not None:
            return "nvidia"
        if shutil.which("amd-smi") is not None:
            return "amd"

        powershell = shutil.which("powershell") or shutil.which("pwsh")
        if powershell is None:
            return "unknown"

        output = self._command_output(
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

    def _detect_linux_gpu_vendor(self) -> str:
        if shutil.which("nvidia-smi") is not None:
            return "nvidia"
        if shutil.which("rocm-smi") is not None or shutil.which("amd-smi") is not None:
            return "amd"

        lspci = shutil.which("lspci")
        if lspci is None:
            return "unknown"

        output = self._command_output([lspci])
        lowered = output.lower()
        if "nvidia" in lowered:
            return "nvidia"
        if any(token in lowered for token in ["amd/ati", "advanced micro devices", "radeon"]):
            return "amd"
        return "unknown"

    def _detect_gpu_vendor(self) -> str:
        system_name = platform.system().lower()
        if system_name == "windows":
            return self._detect_windows_gpu_vendor()
        if system_name == "linux":
            return self._detect_linux_gpu_vendor()
        return "unknown"

    def _resolve_compute_backend(self) -> tuple[str, str, str]:
        if self.install_profile == "nvidia":
            if self.detected_gpu_vendor == "nvidia":
                return "cuda", "float16", "NVIDIA GPU (CUDA)"
            return "cpu", "int8", "CPU (NVIDIA profile selected, but no NVIDIA GPU detected)"

        if self.install_profile == "amd":
            if self.detected_gpu_vendor == "amd":
                return "cpu", "int8", "AMD GPU detected (CPU backend active)"
            return "cpu", "int8", "CPU (AMD profile selected)"

        if self.detected_gpu_vendor == "nvidia":
            return "cuda", "float16", "NVIDIA GPU (CUDA)"
        if self.detected_gpu_vendor == "amd":
            return "cpu", "int8", "AMD GPU detected (CPU backend active)"
        return "cpu", "int8", "CPU"

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
            values=["tiny", "base", "small", "medium", "large-v3"],
            width=10,
            state="readonly",
        )
        self.model_combo.pack(side=tk.LEFT)
        self.model_combo.bind("<<ComboboxSelected>>", self._on_model_changed)

        self.load_model_button = ttk.Button(top, text="Load Model", command=self.load_selected_model)
        self.load_model_button.pack(side=tk.LEFT, padx=(6, 0))

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
        self.progress.start(10)

        thread = threading.Thread(target=self._load_model_worker, args=(model_name,), daemon=True)
        thread.start()

    def _load_model_worker(self, model_name: str) -> None:
        try:
            model = WhisperModel(
                model_name,
                device=self.device,
                compute_type=self.compute_type,
                download_root=str(self.model_cache_dir),
            )
            self.root.after(0, self._model_loaded, model_name, model)
        except Exception as exc:
            error_text = str(exc)
            cuda_error = any(token in error_text.lower() for token in ["libcublas", "cublas", "cuda", "cudnn", "libcudart", "cudart"])
            if self.device == "cuda" and cuda_error:
                try:
                    self.device = "cpu"
                    self.compute_type = "int8"
                    model = WhisperModel(
                        model_name,
                        device=self.device,
                        compute_type=self.compute_type,
                        download_root=str(self.model_cache_dir),
                    )
                    self.root.after(0, self._model_loaded_with_fallback, model_name, model, error_text)
                    return
                except Exception as fallback_exc:
                    self.root.after(0, self._model_load_failed, model_name, str(fallback_exc))
                    return
            self.root.after(0, self._model_load_failed, model_name, error_text)

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
        self.progress.start(10)

        thread = threading.Thread(target=self._transcribe, args=(filepath, self.model_var.get(), job_id), daemon=True)
        thread.start()

    def _transcribe(self, filepath: str, model_name: str, job_id: int) -> None:
        try:
            model = self.loaded_model
            if model is None or self.loaded_model_name != model_name:
                raise RuntimeError("Selected model is not loaded. Please load the model first.")
            segments, _ = model.transcribe(filepath, beam_size=5)
            text = "\n".join(segment.text.strip() for segment in segments if segment.text).strip()

            output_dir = Path(filepath).parent
            output_file = output_dir / f"{Path(filepath).stem}.whisper.txt"
            output_file.write_text(text, encoding="utf-8")

            self.root.after(0, self._show_result, text, str(output_file), job_id)
        except Exception as exc:
            error_text = str(exc)
            cuda_error = any(token in error_text.lower() for token in ["libcublas", "cublas", "cuda", "cudnn", "libcudart", "cudart"])
            if self.device == "cuda" and cuda_error:
                try:
                    fallback_model = WhisperModel(
                        model_name,
                        device="cpu",
                        compute_type="int8",
                        download_root=str(self.model_cache_dir),
                    )
                    segments, _ = fallback_model.transcribe(filepath, beam_size=5)
                    text = "\n".join(segment.text.strip() for segment in segments if segment.text).strip()

                    output_dir = Path(filepath).parent
                    output_file = output_dir / f"{Path(filepath).stem}.whisper.txt"
                    output_file.write_text(text, encoding="utf-8")

                    self.root.after(0, self._transcribe_fallback_success, model_name, fallback_model, text, str(output_file), job_id)
                    return
                except Exception as fallback_exc:
                    self.root.after(0, self._show_error, str(fallback_exc), job_id)
                    return
            self.root.after(0, self._show_error, error_text, job_id)

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


def main() -> None:
    root = tk.Tk()
    app = WhisperApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
