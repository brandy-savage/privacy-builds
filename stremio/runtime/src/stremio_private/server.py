from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .app import CompanionApp


class RuntimeServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], app: CompanionApp):
        self.app = app
        super().__init__(address, RequestHandler)


class RequestHandler(BaseHTTPRequestHandler):
    server: RuntimeServer

    def do_GET(self) -> None:
        self._serve("GET")

    def do_OPTIONS(self) -> None:
        self._serve("OPTIONS")

    def do_POST(self) -> None:
        self._serve("POST")

    def _serve(self, method: str) -> None:
        response = self.server.app.handle(self.path, method=method)
        raw = b"" if response.status == 204 else json.dumps(
            response.body, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        self.send_response(response.status)
        for name, value in response.headers.items():
            self.send_header(name, value)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        if raw:
            self.wfile.write(raw)

    def log_message(self, format: str, *args: object) -> None:
        # Default logging includes the full path. That can contain the private LAN
        # capability, search terms, or media identifiers, so requests are not logged.
        return
