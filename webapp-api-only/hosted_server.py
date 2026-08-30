#!/usr/bin/env python3
"""Whisper V1 hosted server: serves the app and proxies /v1 to Lemonade.

Same-origin design: the browser talks only to this server, so there is no
CORS at all. Cloudflare Access sits in front of the public hostname.

Routes:
  /            -> webapp-api-only files (Whisper-V1-API.html, etc.)
  /v1/<path>   -> reverse proxy to Lemonade (http://localhost:13305/v1/<path>)
"""

import argparse
import urllib.request
import urllib.error
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
HTML_FILE = APP_DIR.parent / "Whisper-V1-API.html"
LEMONADE_BASE = "http://localhost:13305"

HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "host", "content-length",
}


class ProxyHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        # Serve the repo root so /Whisper-V1-API.html resolves; "/" maps to it.
        super().__init__(*args, directory=str(APP_DIR.parent), **kwargs)

    def log_message(self, format, *args):  # noqa: A002
        pass  # keep console quiet

    # --- helpers ---

    def _is_api_path(self) -> bool:
        return self.path == "/v1" or self.path.startswith("/v1/")

    def _relay(self, method: str) -> None:
        target = f"{LEMONADE_BASE}{self.path}"
        body = None
        if method in ("POST", "PUT", "PATCH"):
            length = int(self.headers.get("Content-Length", "0") or 0)
            body = self.rfile.read(length) if length else None

        request = urllib.request.Request(target, data=body, method=method)
        for key, value in self.headers.items():
            if key.lower() not in HOP_BY_HOP:
                request.add_header(key, value)

        try:
            with urllib.request.urlopen(request, timeout=600) as response:
                payload = response.read()
                self.send_response(response.status)
                for key, value in response.headers.items():
                    if key.lower() not in HOP_BY_HOP and key.lower() != "content-encoding":
                        self.send_header(key, value)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
        except urllib.error.HTTPError as error:
            payload = error.read()
            self.send_response(error.code)
            for key, value in error.headers.items():
                if key.lower() not in HOP_BY_HOP and key.lower() != "content-encoding":
                    self.send_header(key, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        except Exception as exc:  # noqa: BLE001
            message = f'{{"error": "proxy failure: {exc}"}}'.encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(message)))
            self.end_headers()
            self.wfile.write(message)

    def _serve_app(self) -> None:
        if self.path in ("/", "/index.html", "/app"):
            self.path = "/Whisper-V1-API.html"
        super().do_GET()

    # --- verbs ---

    def do_GET(self):
        if self._is_api_path():
            self._relay("GET")
        else:
            self._serve_app()

    def do_POST(self):
        if self._is_api_path():
            self._relay("POST")
        else:
            self.send_response(404)
            self.end_headers()

    def do_PUT(self):
        self._relay("PUT") if self._is_api_path() else self.send_response(404)
        if not self._is_api_path():
            self.end_headers()

    def do_OPTIONS(self):
        # Same-origin app: no CORS preflight needed, but answer politely.
        self.send_response(204)
        self.send_header("Content-Length", "0")
        self.end_headers()


def main() -> None:
    global LEMONADE_BASE
    parser = argparse.ArgumentParser(description="Whisper V1 hosted server")
    parser.add_argument("--port", type=int, default=8179)
    parser.add_argument("--lemonade", default=LEMONADE_BASE)
    args = parser.parse_args()

    LEMONADE_BASE = args.lemonade.rstrip("/")

    if not HTML_FILE.exists():
        raise SystemExit(f"Missing {HTML_FILE} — run build_singlefile.py first")

    server = ThreadingHTTPServer(("127.0.0.1", args.port), ProxyHandler)
    print(f"Whisper V1 hosted server on http://127.0.0.1:{args.port}")
    print(f"  app      -> {HTML_FILE.name}")
    print(f"  /v1/*    -> {LEMONADE_BASE}/v1/*")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
