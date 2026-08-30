#!/usr/bin/env python3
"""Local Whisper HTTP bridge for the webapp.

Serves the webapp folder and exposes /transcribe + /models so the browser
app can use the locally installed faster-whisper models.
"""

import argparse
import json
import tempfile
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
WEBAPP_DIR = APP_DIR / "webapp"
MODEL_CACHE_DIR = APP_DIR / "model-cache"

MODEL_CHOICES = ["tiny", "base", "small", "medium", "large-v3"]
_loaded_models: dict = {}


def get_model(name: str):
    """Load a faster-whisper model, caching loaded instances."""
    if name in _loaded_models:
        return _loaded_models[name]
    from faster_whisper import WhisperModel

    model = WhisperModel(name, device="cpu", compute_type="int8", download_root=str(MODEL_CACHE_DIR))
    _loaded_models[name] = model
    return model


def format_timestamp(seconds: float) -> str:
    total_ms = int(round(max(0.0, seconds) * 1000))
    hours, remainder = divmod(total_ms, 3600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def transcribe_file(model, filepath: str, with_timestamps: bool) -> str:
    segments, _info = model.transcribe(filepath, beam_size=5)
    lines = []
    for segment in segments:
        text = segment.text.strip()
        if not text:
            continue
        if with_timestamps:
            lines.append(f"[{format_timestamp(segment.start)} --> {format_timestamp(segment.end)}] {text}")
        else:
            lines.append(text)
    return "\n".join(lines).strip()


class BridgeHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(WEBAPP_DIR), **kwargs)

    def log_message(self, format, *args):  # noqa: A002 - stdlib signature
        pass  # keep the console quiet

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self):
        if self.path == "/models":
            self._send_json({"models": [{"id": name, "label": name} for name in MODEL_CHOICES]})
            return
        super().do_GET()

    def do_POST(self):
        if self.path != "/transcribe":
            self._send_json({"error": "not found"}, status=404)
            return

        content_type = self.headers.get("Content-Type", "")
        boundary_token = None
        for part in content_type.split(";"):
            part = part.strip()
            if part.startswith("boundary="):
                boundary_token = part[len("boundary="):].strip('"')
        if not boundary_token:
            self._send_json({"error": "expected multipart form data"}, status=400)
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length)
        fields, file_bytes = parse_multipart(body, boundary_token.encode())

        model_name = fields.get("model", "base")
        if model_name not in MODEL_CHOICES:
            model_name = "base"
        with_timestamps = fields.get("timestamps", "false").lower() == "true"

        if not file_bytes:
            self._send_json({"error": "no audio file received"}, status=400)
            return

        try:
            model = get_model(model_name)
        except Exception as exc:  # noqa: BLE001
            self._send_json({"error": f"model load failed: {exc}"}, status=500)
            return

        with tempfile.NamedTemporaryFile(prefix="wv1_", suffix=".wav", delete=False) as handle:
            handle.write(file_bytes)
            temp_path = handle.name

        try:
            text = transcribe_file(model, temp_path, with_timestamps)
        except Exception as exc:  # noqa: BLE001
            self._send_json({"error": f"transcription failed: {exc}"}, status=500)
            return
        finally:
            Path(temp_path).unlink(missing_ok=True)

        self._send_json({"text": text, "model": model_name})


def parse_multipart(body: bytes, boundary: bytes):
    """Minimal multipart/form-data parser: returns (fields, file_bytes)."""
    fields: dict = {}
    file_bytes = b""
    delimiter = b"--" + boundary

    for part in body.split(delimiter):
        part = part.strip(b"\r\n")
        if not part or part == b"--":
            continue
        header_blob, _sep, content = part.partition(b"\r\n\r\n")
        if not _sep:
            continue
        name = None
        is_file = False
        for line in header_blob.split(b"\r\n"):
            lowered = line.decode("utf-8", "replace").lower()
            if lowered.startswith("content-disposition:"):
                if 'name="' in lowered:
                    name = lowered.split('name="', 1)[1].split('"', 1)[0]
                is_file = 'filename="' in lowered
        if name is None:
            continue
        if is_file and content:
            file_bytes = content
        else:
            fields[name] = content.decode("utf-8", "replace").strip()
    return fields, file_bytes


def main() -> None:
    parser = argparse.ArgumentParser(description="Local Whisper bridge for the webapp")
    parser.add_argument("--port", type=int, default=8177)
    args = parser.parse_args()

    server = HTTPServer(("127.0.0.1", args.port), BridgeHandler)
    print(f"Whisper bridge serving webapp at http://127.0.0.1:{args.port}")
    print(f"Model cache: {MODEL_CACHE_DIR}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
