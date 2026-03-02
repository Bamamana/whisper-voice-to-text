#!/usr/bin/env python3
import os
import tempfile
import threading
import tkinter as tk
import wave
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel


class WhisperApp:
    def __init__(self, root: tk.Tk) -> None:
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
        self.model_cache_dir = Path(__file__).resolve().parent / "model-cache"
        self.model_cache_dir.mkdir(parents=True, exist_ok=True)

        self._build_ui()

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=12)
        container.pack(fill=tk.BOTH, expand=True)

        top = ttk.Frame(container)
        top.pack(fill=tk.X)

        ttk.Button(top, text="Choose Audio/Video File", command=self.choose_file).pack(side=tk.LEFT)
        ttk.Button(top, text="🎤 Start Mic", command=self.start_recording).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(top, text="⏹ Stop Mic", command=self.stop_recording).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Label(top, text="Model:").pack(side=tk.LEFT, padx=(12, 4))
        ttk.Combobox(
            top,
            textvariable=self.model_var,
            values=["tiny", "base", "small", "medium", "large-v3"],
            width=10,
            state="readonly",
        ).pack(side=tk.LEFT)
        self.transcribe_button = ttk.Button(top, text="Transcribe", command=self.start_transcribe)
        self.transcribe_button.pack(side=tk.LEFT, padx=(12, 0))

        ttk.Label(container, textvariable=self.file_var).pack(anchor="w", pady=(10, 8))
        ttk.Label(container, textvariable=self.recording_status_var).pack(anchor="w", pady=(0, 8))

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
            model = WhisperModel(
                model_name,
                device="cpu",
                compute_type="int8",
                download_root=str(self.model_cache_dir),
            )
            segments, _ = model.transcribe(filepath, beam_size=5)
            text = "\n".join(segment.text.strip() for segment in segments if segment.text).strip()

            output_dir = Path(filepath).parent
            output_file = output_dir / f"{Path(filepath).stem}.whisper.txt"
            output_file.write_text(text, encoding="utf-8")

            self.root.after(0, self._show_result, text, str(output_file), job_id)
        except Exception as exc:
            self.root.after(0, self._show_error, str(exc), job_id)

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
