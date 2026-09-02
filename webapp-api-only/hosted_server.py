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
import json
from urllib.parse import urlsplit
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
HTML_FILE = APP_DIR.parent / "Whisper-V1-API.html"
LEMONADE_BASE = "http://localhost:13305"
LOADABLE_LIVE_MODELS = {"Moonshine-Medium-Streaming", "Whisper-Large-v3-Turbo"}

HOP_BY_HOP = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade", "host", "content-length",
    "origin",
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

    def _is_model_load_path(self) -> bool:
        return self.path == "/v1/internal/model-load"

    def _relay(self, method: str) -> None:
        body = None
        if method in ("POST", "PUT", "PATCH"):
            length = int(self.headers.get("Content-Length", "0") or 0)
            body = self.rfile.read(length) if length else None

        target = f"{LEMONADE_BASE}{self.path}"
        if self._is_model_load_path():
            try:
                model_name = str(json.loads((body or b"{}").decode()).get("model_name", ""))
            except (UnicodeDecodeError, json.JSONDecodeError):
                self._send_json_error(400, "Invalid model load request.")
                return
            if model_name not in LOADABLE_LIVE_MODELS:
                self._send_json_error(400, "This model cannot be loaded through the live transcription app.")
                return
            target = f"{LEMONADE_BASE}/api/v1/load"

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

    def _send_json_error(self, status: int, message: str) -> None:
        payload = json.dumps({"error": message}).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _serve_app(self) -> None:
        if self.path in ("/", "/index.html", "/app"):
            self.path = "/Whisper-V1-API.html"
        super().do_GET()

    # --- verbs ---

    def do_GET(self):
        if self._is_api_path():
            if self._is_websocket_upgrade():
                self._relay_websocket()
            else:
                self._relay("GET")
        else:
            self._serve_app()

    def _is_websocket_upgrade(self) -> bool:
        return self.headers.get("Upgrade", "").lower() == "websocket"

    def _relay_websocket(self) -> None:
        """Hand the raw socket to Lemonade's realtime WS endpoint (127.0.0.1:8177-style
        TCP relay). We perform the upgrade handshake against Lemonade, then splice
        bytes both directions."""
        import socket

        upstream_url = urlsplit(LEMONADE_BASE)
        target_host = upstream_url.hostname
        if not target_host:
            self.send_response(502)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        target_port = upstream_url.port or (443 if upstream_url.scheme == "https" else 80)
        target_path = f"{upstream_url.path.rstrip('/')}{self.path}"
        try:
            upstream = socket.create_connection((target_host, target_port), timeout=10)
            if upstream_url.scheme == "https":
                import ssl
                upstream = ssl.create_default_context().wrap_socket(upstream, server_hostname=target_host)
        except Exception as exc:  # noqa: BLE001
            self.send_response(502)
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        # Rebuild the raw HTTP upgrade request for Lemonade.
        lines = [
            f"GET {target_path} HTTP/1.1",
            f"Host: {target_host}:{target_port}",
            "Upgrade: websocket",
            "Connection: Upgrade",
            f"Sec-WebSocket-Key: {self.headers.get('Sec-WebSocket-Key', '')}",
            f"Sec-WebSocket-Version: {self.headers.get('Sec-WebSocket-Version', '13')}",
        ]
        extensions = self.headers.get("Sec-WebSocket-Extensions")
        if extensions:
            lines.append(f"Sec-WebSocket-Extensions: {extensions}")
        protocol = self.headers.get("Sec-WebSocket-Protocol")
        if protocol:
            lines.append(f"Sec-WebSocket-Protocol: {protocol}")
        raw_request = ("\r\n".join(lines) + "\r\n\r\n").encode("utf-8")
        upstream.sendall(raw_request)

        # Read the upstream handshake response and forward it verbatim.
        upstream.settimeout(10)
        response = b""
        while b"\r\n\r\n" not in response:
            chunk = upstream.recv(4096)
            if not chunk:
                upstream.close()
                self.send_response(502)
                self.end_headers()
                return
            response += chunk

        head, _, rest = response.partition(b"\r\n\r\n")
        status_line = head.split(b"\r\n")[0]
        try:
            code = int(status_line.split()[1])
        except (IndexError, ValueError):
            code = 502
        self.send_response(code)
        for line in head.split(b"\r\n")[1:]:
            name, _sep, value = line.partition(b":")
            name_lower = name.strip().lower().decode("utf-8", "replace")
            if name_lower in ("transfer-encoding", "connection", "upgrade"):
                continue
            self.send_header(name.strip().decode("utf-8", "replace"), value.strip().decode("utf-8", "replace"))
        self.send_header("Connection", "Upgrade")
        self.send_header("Upgrade", "websocket")
        self.end_headers()

        if code != 101:
            if rest:
                self.wfile.write(rest)
            upstream.close()
            return

        # 101 Switching Protocols — splice raw bytes both directions.
        self.connection.sendall(rest)
        self.connection.settimeout(None)
        upstream.settimeout(None)
        self._splice_sockets(self.connection, upstream)
        upstream.close()

    def _splice_sockets(self, client_socket, upstream_socket) -> None:
        """Bidirectional byte relay until either side closes."""
        import selectors

        selector = selectors.DefaultSelector()
        client_socket.setblocking(False)
        upstream_socket.setblocking(False)
        selector.register(client_socket, selectors.EVENT_READ, data="to_upstream")
        selector.register(upstream_socket, selectors.EVENT_READ, data="to_client")

        try:
            while True:
                for key, _mask in selector.select(timeout=3600):
                    source = key.fileobj
                    target = upstream_socket if key.data == "to_upstream" else client_socket
                    try:
                        data = source.recv(65536)
                    except (ConnectionResetError, BrokenPipeError, OSError):
                        return
                    if not data:
                        return
                    try:
                        target.sendall(data)
                    except (ConnectionResetError, BrokenPipeError, OSError):
                        return
        except Exception:  # noqa: BLE001
            pass
        finally:
            selector.close()

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
