#!/usr/bin/env python3
"""OpenAI-compatible STT proxy in front of a whisper.cpp server.

The app posts OpenAI-style requests to ``/v1/audio/transcriptions`` and probes
``/v1/models``. whisper.cpp's own server only exposes ``/inference`` (and no
models endpoint), so this thin, dependency-free proxy exposes the routes the app
expects and forwards transcription requests to whisper.cpp.

Run the whisper.cpp backend first, for example:

    whisper-server.exe -m models/ggml-large-v3-turbo-q8_0.bin --port 8080 --convert

Then run this proxy and point the app's Base URL at http://127.0.0.1:8090/v1
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DEFAULT_BACKEND = "http://127.0.0.1:8080/inference"
DEFAULT_MODEL_ID = "whisper-1"

DEFAULT_MODELS = {
    "object": "list",
    "data": [
        {"id": DEFAULT_MODEL_ID, "object": "model", "owned_by": "whisper.cpp"},
    ],
}


class ProxyHandler(BaseHTTPRequestHandler):
    server_version = "LocalWhisperProxy/1.0"
    backend = DEFAULT_BACKEND
    model_id = DEFAULT_MODEL_ID

    def _send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Authorization,Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")

    def _send_json(self, status, payload_bytes):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self._send_cors()
        self.send_header("Content-Length", str(len(payload_bytes)))
        self.end_headers()
        self.wfile.write(payload_bytes)

    def do_OPTIONS(self):
        self.send_response(204)
        self._send_cors()
        self.end_headers()

    def do_GET(self):
        path = self.path.split("?", 1)[0].rstrip("/")
        if path.endswith("/v1/models") or path.endswith("/models"):
            payload = {
                "object": "list",
                "data": [
                    {"id": self.model_id, "object": "model", "owned_by": "whisper.cpp"},
                ],
            }
            self._send_json(200, json.dumps(payload).encode("utf-8"))
            return
        if path.endswith("/health"):
            self._send_json(200, b'{"status":"ok"}')
            return
        self._send_json(404, b'{"error":{"message":"not found"}}')

    def do_POST(self):
        path = self.path.split("?", 1)[0].rstrip("/")
        if not path.endswith("/audio/transcriptions"):
            self._send_json(404, b'{"error":{"message":"not found"}}')
            return

        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else b""

        request = urllib.request.Request(self.backend, data=body, method="POST")
        content_type = self.headers.get("Content-Type", "application/octet-stream")
        request.add_header("Content-Type", content_type)

        try:
            with urllib.request.urlopen(request) as response:
                data = response.read()
                status = response.status
                response_type = response.headers.get("Content-Type", "application/json")
        except urllib.error.HTTPError as error:
            data = error.read()
            status = error.code
            response_type = error.headers.get("Content-Type", "application/json")
        except Exception as error:  # noqa: BLE001 - surface any backend failure to the client
            data = json.dumps({"error": {"message": str(error)}}).encode("utf-8")
            status = 502
            response_type = "application/json"

        self.send_response(status)
        self.send_header("Content-Type", response_type)
        self._send_cors()
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))
        sys.stderr.flush()


def main():
    parser = argparse.ArgumentParser(description="OpenAI-compatible proxy for whisper.cpp")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8090)
    parser.add_argument("--backend", default=DEFAULT_BACKEND, help="whisper.cpp /inference URL")
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID, help="model id returned by /v1/models")
    args = parser.parse_args()

    ProxyHandler.backend = args.backend
    ProxyHandler.model_id = args.model_id

    server = ThreadingHTTPServer((args.host, args.port), ProxyHandler)
    server.daemon_threads = True
    print(
        f"OpenAI-compatible STT proxy listening on http://{args.host}:{args.port}/v1 "
        f"-> {args.backend}",
        flush=True,
    )
    server.serve_forever()


if __name__ == "__main__":
    main()
