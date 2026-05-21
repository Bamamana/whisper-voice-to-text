#!/usr/bin/env python3
from __future__ import annotations

import json
import tempfile
import threading
import wave
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
import tkinter as tk

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
from google import genai
from google.genai import types
from pypdf import PdfReader, PdfWriter
from pypdf.generic import BooleanObject, NameObject


DEFAULT_GEMINI_MODEL = "gemini-flash-latest"


class GeminiFormFillerApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Whisper Voice To Form - V2")
        self.root.geometry("1040x720")

        self.app_dir = Path(__file__).resolve().parent
        self.api_key_file = self.app_dir / ".gemini-api-key"
        self.model_cache_dir = self.app_dir / "model-cache"
        self.model_cache_dir.mkdir(exist_ok=True)

        self.pdf_path: Path | None = None
        self.pdf_fields: dict[str, dict] = {}
        self.field_values: dict[str, str] = {}
        self.recording = False
        self.record_stream = None
        self.recorded_chunks: list[np.ndarray] = []
        self.sample_rate = 16000
        self.whisper_model: WhisperModel | None = None
        self.is_busy = False

        self.api_key_var = tk.StringVar(value=self._load_api_key())
        self.gemini_model_var = tk.StringVar(value=DEFAULT_GEMINI_MODEL)
        self.whisper_model_var = tk.StringVar(value="base")
        self.pdf_status_var = tk.StringVar(value="No PDF loaded")
        self.recording_status_var = tk.StringVar(value="Mic idle")
        self.status_var = tk.StringVar(value="Ready")

        self._build_ui()

    def _build_ui(self) -> None:
        main = ttk.Frame(self.root, padding=12)
        main.pack(fill=tk.BOTH, expand=True)

        settings = ttk.LabelFrame(main, text="AI Settings", padding=10)
        settings.pack(fill=tk.X)

        ttk.Label(settings, text="Google AI Studio API key").grid(row=0, column=0, sticky="w")
        api_entry = ttk.Entry(settings, textvariable=self.api_key_var, show="*", width=58)
        api_entry.grid(row=0, column=1, sticky="ew", padx=(8, 6))
        ttk.Button(settings, text="Save Key", command=self.save_api_key).grid(row=0, column=2)
        ttk.Button(settings, text="Test Key", command=self.test_api_key).grid(row=0, column=3, padx=(6, 0))

        ttk.Label(settings, text="Gemini model").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(settings, textvariable=self.gemini_model_var, width=28).grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 0))
        ttk.Label(settings, text="Whisper model").grid(row=1, column=1, sticky="e", padx=(0, 130), pady=(8, 0))
        ttk.Combobox(
            settings,
            textvariable=self.whisper_model_var,
            values=["tiny", "base", "small", "medium", "large-v3"],
            width=12,
            state="readonly",
        ).grid(row=1, column=2, sticky="w", pady=(8, 0))
        settings.columnconfigure(1, weight=1)

        actions = ttk.Frame(main)
        actions.pack(fill=tk.X, pady=(10, 8))

        ttk.Button(actions, text="Upload Fillable PDF", command=self.load_pdf).pack(side=tk.LEFT)
        ttk.Button(actions, text="Start Recording", command=self.start_recording).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(actions, text="Stop and Transcribe", command=self.stop_recording).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(actions, text="Send Transcript To PDF", command=self.send_transcript_to_ai).pack(side=tk.LEFT, padx=(16, 0))
        ttk.Button(actions, text="Export Filled PDF", command=self.export_filled_pdf).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(main, textvariable=self.pdf_status_var).pack(anchor="w")
        ttk.Label(main, textvariable=self.recording_status_var).pack(anchor="w", pady=(2, 8))

        body = ttk.PanedWindow(main, orient=tk.HORIZONTAL)
        body.pack(fill=tk.BOTH, expand=True)

        left = ttk.Frame(body, padding=(0, 0, 8, 0))
        right = ttk.Frame(body)
        body.add(left, weight=1)
        body.add(right, weight=1)

        ttk.Label(left, text="Transcript").pack(anchor="w")
        self.transcript_text = tk.Text(left, wrap=tk.WORD, height=26)
        self.transcript_text.pack(fill=tk.BOTH, expand=True)

        ttk.Label(right, text="PDF Fields and AI Values").pack(anchor="w")
        self.fields_tree = ttk.Treeview(right, columns=("value",), show="tree headings")
        self.fields_tree.heading("#0", text="Field")
        self.fields_tree.heading("value", text="Value")
        self.fields_tree.column("#0", width=260)
        self.fields_tree.column("value", width=360)
        self.fields_tree.pack(fill=tk.BOTH, expand=True)
        self.fields_tree.bind("<Double-1>", self.edit_selected_value)

        ttk.Label(main, textvariable=self.status_var).pack(anchor="w", pady=(8, 0))

    def _load_api_key(self) -> str:
        if self.api_key_file.exists():
            return self.api_key_file.read_text(encoding="utf-8").strip()
        return ""

    def save_api_key(self) -> None:
        self.api_key_file.write_text(self.api_key_var.get().strip(), encoding="utf-8")
        self.status_var.set("API key saved locally")

    def test_api_key(self) -> None:
        if self.is_busy:
            return
        if not self.api_key_var.get().strip():
            messagebox.showerror("Missing API key", "Enter your Google AI Studio API key first.")
            return

        self.is_busy = True
        model_name = self.gemini_model_var.get().strip() or DEFAULT_GEMINI_MODEL
        self.status_var.set(f"Testing Gemini API key with {model_name}")
        threading.Thread(target=self._test_api_key_worker, args=(model_name,), daemon=True).start()

    def _test_api_key_worker(self, model_name: str) -> None:
        try:
            client = genai.Client(api_key=self.api_key_var.get().strip())
            response = client.models.generate_content(
                model=model_name,
                contents="Reply with only: OK",
            )
            reply = (response.text or "").strip()
            if "OK" not in reply.upper():
                raise RuntimeError(f"Gemini responded, but with unexpected text: {reply}")
            self.root.after(0, self._test_api_key_done, model_name)
        except Exception as exc:
            self.root.after(0, self._task_failed, "API key test failed", str(exc))

    def _test_api_key_done(self, model_name: str) -> None:
        self.is_busy = False
        self.status_var.set(f"API key works with {model_name}")
        messagebox.showinfo("API key works", f"Gemini responded successfully using:\n{model_name}")

    def load_pdf(self) -> None:
        path = filedialog.askopenfilename(title="Choose a fillable PDF", filetypes=[("PDF files", "*.pdf")])
        if not path:
            return

        try:
            reader = PdfReader(path)
            fields = reader.get_fields() or {}
        except Exception as exc:
            messagebox.showerror("PDF error", str(exc))
            return

        if not fields:
            messagebox.showerror(
                "No fillable fields found",
                "This PDF does not appear to contain fillable form fields. Use Adobe Acrobat Pro > Prepare Form first.",
            )
            return

        self.pdf_path = Path(path)
        self.pdf_fields = fields
        self.field_values = {field_name: "" for field_name in fields}
        self.pdf_status_var.set(f"Loaded PDF: {self.pdf_path.name} ({len(fields)} fields)")
        self.refresh_fields_tree()

    def refresh_fields_tree(self) -> None:
        self.fields_tree.delete(*self.fields_tree.get_children())
        for field_name in sorted(self.pdf_fields):
            self.fields_tree.insert("", tk.END, iid=field_name, text=field_name, values=(self.field_values.get(field_name, ""),))

    def edit_selected_value(self, _event=None) -> None:
        selected = self.fields_tree.selection()
        if not selected:
            return
        field_name = selected[0]
        current_value = self.field_values.get(field_name, "")
        new_value = simpledialog.askstring("Edit field value", field_name, initialvalue=current_value)
        if new_value is None:
            return
        self.field_values[field_name] = new_value
        self.refresh_fields_tree()

    def start_recording(self) -> None:
        if self.recording or self.is_busy:
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
            self.recording_status_var.set("Recording... click Stop and Transcribe when done")
            self.status_var.set("Recording")
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
        temp_wav = tempfile.NamedTemporaryFile(prefix="whisper_form_", suffix=".wav", delete=False)
        temp_wav_path = Path(temp_wav.name)
        temp_wav.close()

        with wave.open(str(temp_wav_path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio.tobytes())

        self.is_busy = True
        self.recording_status_var.set("Transcribing recording...")
        self.status_var.set("Loading Whisper and transcribing")
        threading.Thread(target=self._transcribe_worker, args=(temp_wav_path,), daemon=True).start()

    def _transcribe_worker(self, audio_path: Path) -> None:
        try:
            if self.whisper_model is None:
                self.whisper_model = WhisperModel(
                    self.whisper_model_var.get(),
                    device="cpu",
                    compute_type="int8",
                    download_root=str(self.model_cache_dir),
                )
            segments, _ = self.whisper_model.transcribe(str(audio_path), beam_size=5)
            transcript = "\n".join(segment.text.strip() for segment in segments if segment.text).strip()
            self.root.after(0, self._transcription_done, transcript)
        except Exception as exc:
            self.root.after(0, self._task_failed, "Transcription failed", str(exc))

    def _transcription_done(self, transcript: str) -> None:
        self.is_busy = False
        self.transcript_text.delete("1.0", tk.END)
        self.transcript_text.insert("1.0", transcript)
        self.recording_status_var.set("Mic idle")
        self.status_var.set("Transcript ready")

    def send_transcript_to_ai(self) -> None:
        if self.is_busy:
            return
        if not self.pdf_fields:
            messagebox.showerror("Missing PDF", "Upload a fillable PDF first.")
            return
        if not self.api_key_var.get().strip():
            messagebox.showerror("Missing API key", "Enter your Google AI Studio API key first.")
            return

        transcript = self.transcript_text.get("1.0", tk.END).strip()
        if not transcript:
            messagebox.showerror("Missing transcript", "Record or type a transcript first.")
            return

        self.is_busy = True
        self.status_var.set("Sending transcript and PDF fields to Gemini")
        threading.Thread(target=self._gemini_worker, args=(transcript,), daemon=True).start()

    def _gemini_worker(self, transcript: str) -> None:
        try:
            client = genai.Client(api_key=self.api_key_var.get().strip())
            field_payload = []
            for name, details in self.pdf_fields.items():
                field_payload.append(
                    {
                        "name": name,
                        "type": str(details.get("/FT", "")),
                        "label": str(details.get("/TU", "")),
                        "current_value": str(details.get("/V", "")),
                    }
                )

            prompt = (
                "You fill Adobe PDF form fields from a voice transcript. "
                "Return strict JSON only. Use exact PDF field names as keys. "
                "Use empty strings for fields that are not answered. "
                "Do not invent personal information. For checkboxes, use Yes or Off.\n\n"
                f"PDF fields:\n{json.dumps(field_payload, indent=2)}\n\n"
                f"Transcript:\n{transcript}"
            )
            response = client.models.generate_content(
                model=self.gemini_model_var.get().strip() or DEFAULT_GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json"),
            )
            values = self._parse_json_response(response.text or "")
            clean_values = {name: str(values.get(name, "")) for name in self.pdf_fields}
            self.root.after(0, self._gemini_done, clean_values)
        except Exception as exc:
            self.root.after(0, self._task_failed, "Gemini request failed", str(exc))

    def _parse_json_response(self, text: str) -> dict:
        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = stripped.strip("`")
            if stripped.lower().startswith("json"):
                stripped = stripped[4:].strip()
        parsed = json.loads(stripped)
        if not isinstance(parsed, dict):
            raise ValueError("Gemini did not return a JSON object.")
        return parsed

    def _gemini_done(self, values: dict[str, str]) -> None:
        self.is_busy = False
        self.field_values.update(values)
        self.refresh_fields_tree()
        self.status_var.set("AI values ready for review. Double-click a value to edit it.")

    def export_filled_pdf(self) -> None:
        if self.pdf_path is None:
            messagebox.showerror("Missing PDF", "Upload a fillable PDF first.")
            return

        output_path = filedialog.asksaveasfilename(
            title="Save filled PDF",
            defaultextension=".pdf",
            initialfile=f"{self.pdf_path.stem}-filled.pdf",
            filetypes=[("PDF files", "*.pdf")],
        )
        if not output_path:
            return

        try:
            reader = PdfReader(str(self.pdf_path))
            writer = PdfWriter()
            for page in reader.pages:
                writer.add_page(page)

            if "/AcroForm" in reader.trailer["/Root"]:
                writer._root_object.update({NameObject("/AcroForm"): reader.trailer["/Root"]["/AcroForm"]})
                writer._root_object["/AcroForm"].update({NameObject("/NeedAppearances"): BooleanObject(True)})

            values = {name: value for name, value in self.field_values.items() if value != ""}
            for page in writer.pages:
                writer.update_page_form_field_values(page, values)

            with open(output_path, "wb") as output_file:
                writer.write(output_file)

            self.status_var.set(f"Filled PDF saved: {output_path}")
            messagebox.showinfo("Export complete", f"Saved filled PDF:\n{output_path}")
        except Exception as exc:
            messagebox.showerror("PDF export failed", str(exc))

    def _task_failed(self, title: str, error: str) -> None:
        self.is_busy = False
        self.status_var.set(title)
        self.recording_status_var.set("Mic idle")
        messagebox.showerror(title, error)


def main() -> None:
    root = tk.Tk()
    GeminiFormFillerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
