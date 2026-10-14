from __future__ import annotations

import json
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class UpstreamError(RuntimeError):
    pass


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001
        return None


class SafeHttpClient:
    def __init__(self, *, timeout: float, max_bytes: int):
        self.timeout = timeout
        self.max_bytes = max_bytes
        self._opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(context=ssl.create_default_context()), _NoRedirect()
        )

    def get_json(
        self,
        url: str,
        *,
        allowed_host: str,
        headers: dict[str, str] | None = None,
        query: dict[str, str] | None = None,
    ) -> dict[str, Any] | list[Any]:
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname != allowed_host:
            raise UpstreamError("Blocked non-HTTPS or unexpected upstream host")
        if query:
            url = urllib.parse.urlunsplit(
                parsed._replace(query=urllib.parse.urlencode(query))
            )
        safe_headers = {"User-Agent": "stremio-private-runtime/0.1"}
        safe_headers.update(headers or {})
        request = urllib.request.Request(url, headers=safe_headers, method="GET")
        try:
            with self._opener.open(request, timeout=self.timeout) as response:
                raw = response.read(self.max_bytes + 1)
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise UpstreamError("Upstream request failed") from exc
        if len(raw) > self.max_bytes:
            raise UpstreamError("Upstream response exceeded size limit")
        try:
            return json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise UpstreamError("Upstream returned invalid JSON") from exc
