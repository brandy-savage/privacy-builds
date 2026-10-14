from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlencode, urlsplit

from ..http_client import SafeHttpClient
from ..protocol import ResourceRequest
from .base import Connector, ConnectorResult


@dataclass(frozen=True)
class CompatibilityTarget:
    id: str
    base_url: str
    allowed_host: str
    resources: frozenset[str]
    catalogs: tuple[dict[str, Any], ...] = ()

    def __post_init__(self) -> None:
        parsed = urlsplit(self.base_url)
        if (
            parsed.scheme != "https"
            or parsed.hostname != self.allowed_host
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("Compatibility targets must be fixed, HTTPS, allowlisted URLs")


class CompatibilityProxyConnector(Connector):
    """Narrow cache proxy for public addons with no user data in their URL."""

    def __init__(self, target: CompatibilityTarget, http: SafeHttpClient):
        self.target = target
        self.http = http
        self.id = f"compat-{target.id}"

    def catalogs(self) -> list[dict[str, Any]]:
        return [dict(catalog) for catalog in self.target.catalogs]

    def _forward(self, request: ResourceRequest) -> ConnectorResult | None:
        if request.resource not in self.target.resources:
            return None
        path = "/".join(
            quote(part, safe=":") for part in (request.resource, request.type, request.id)
        )
        if request.extra:
            path += "/" + quote(urlencode(request.extra), safe="=&")
        url = f"{self.target.base_url.rstrip('/')}/{path}.json"
        data = self.http.get_json(url, allowed_host=self.target.allowed_host)
        if not isinstance(data, dict):
            return None
        if request.resource == "stream":
            return ConnectorResult(data, ttl=0, stale_seconds=0, persist=False)
        ttl = 300 if request.resource == "subtitles" else 3600
        return ConnectorResult(data, ttl=ttl, stale_seconds=86400)

    def catalog(self, request: ResourceRequest) -> ConnectorResult | None:
        ids = {(catalog["type"], catalog["id"]) for catalog in self.target.catalogs}
        return self._forward(request) if (request.type, request.id) in ids else None

    def meta(self, request: ResourceRequest) -> ConnectorResult | None:
        return self._forward(request)

    def stream(self, request: ResourceRequest) -> ConnectorResult | None:
        return self._forward(request)

    def subtitles(self, request: ResourceRequest) -> ConnectorResult | None:
        return self._forward(request)

    def health(self) -> dict[str, Any]:
        return {"id": self.id, "configured": True}
