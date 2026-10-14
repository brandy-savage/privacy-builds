from __future__ import annotations

import base64
from typing import Any

from ..http_client import SafeHttpClient, UpstreamError
from ..protocol import ResourceRequest
from ..secrets import SecretStore
from .base import Connector, ConnectorResult


def _encode_id(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")


def _decode_id(value: str) -> str:
    padding = "=" * (-len(value) % 4)
    try:
        return base64.urlsafe_b64decode(value + padding).decode("utf-8")
    except (ValueError, UnicodeDecodeError) as exc:
        raise UpstreamError("Invalid local media identifier") from exc


class PremiumizeConnector(Connector):
    """Exposes only video files already present in the user's private cloud."""

    id = "premiumize"
    HOST = "www.premiumize.me"
    BASE = "https://www.premiumize.me/api"
    VIDEO_SUFFIXES = (".mkv", ".mp4", ".webm", ".avi", ".mov", ".m4v", ".ts")

    def __init__(self, secrets: SecretStore, http: SafeHttpClient):
        self.secrets = secrets
        self.http = http

    def catalogs(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "movie",
                "id": "premiumize-cloud",
                "name": "Private Cloud Videos",
                "extra": [{"name": "search", "isRequired": False}],
            }
        ]

    def _headers(self) -> dict[str, str] | None:
        key = self.secrets.get("premiumize.api_key")
        return {"Authorization": f"Bearer {key}"} if key else None

    @classmethod
    def _is_video(cls, item: dict[str, Any]) -> bool:
        mime = str(item.get("mime_type", "")).lower()
        name = str(item.get("name", "")).lower()
        return item.get("type") == "file" and (
            mime.startswith("video/") or name.endswith(cls.VIDEO_SUFFIXES)
        )

    @classmethod
    def _preview(cls, item: dict[str, Any]) -> dict[str, Any] | None:
        file_id = item.get("id")
        name = item.get("name")
        if not file_id or not name or not cls._is_video(item):
            return None
        return {
            "id": f"pm:{_encode_id(str(file_id))}",
            "type": "movie",
            "name": str(name),
            "description": "A video in your private Premiumize cloud storage.",
        }

    def _request(self, path: str, query: dict[str, str] | None = None) -> dict[str, Any] | None:
        headers = self._headers()
        if not headers:
            return None
        data = self.http.get_json(
            f"{self.BASE}/{path}",
            allowed_host=self.HOST,
            headers=headers,
            query=query,
        )
        if not isinstance(data, dict) or data.get("status") != "success":
            raise UpstreamError("Premiumize returned an unsuccessful response")
        return data

    def catalog(self, request: ResourceRequest) -> ConnectorResult | None:
        if (request.type, request.id) != ("movie", "premiumize-cloud"):
            return None
        search = request.extra.get("search", "").strip()
        data = self._request("folder/search", {"q": search}) if search else self._request("folder/list")
        if data is None:
            return ConnectorResult({"metas": []}, ttl=60)
        content = data.get("content", [])
        metas = [preview for item in content if isinstance(item, dict) if (preview := self._preview(item))]
        # File links are intentionally discarded here, so cached catalogs contain no bearer URLs.
        return ConnectorResult({"metas": metas}, ttl=300, stale_seconds=3600)

    def _details(self, request: ResourceRequest) -> dict[str, Any] | None:
        if not request.id.startswith("pm:"):
            return None
        file_id = _decode_id(request.id[3:])
        return self._request("item/details", {"id": file_id})

    def meta(self, request: ResourceRequest) -> ConnectorResult | None:
        data = self._details(request)
        if data is None:
            return None
        name = data.get("name")
        if not name:
            return ConnectorResult({"meta": None}, ttl=60)
        return ConnectorResult(
            {
                "meta": {
                    "id": request.id,
                    "type": "movie",
                    "name": str(name),
                    "description": "A video in your private Premiumize cloud storage.",
                }
            },
            ttl=300,
            stale_seconds=3600,
        )

    def stream(self, request: ResourceRequest) -> ConnectorResult | None:
        data = self._details(request)
        if data is None:
            return None
        link = data.get("link")
        if not isinstance(link, str) or not link.startswith("https://"):
            return ConnectorResult({"streams": []}, ttl=0, stale_seconds=0, persist=False)
        stream = {
            "url": link,
            "name": "Private cloud",
            "title": str(data.get("name") or "Personal media"),
            "behaviorHints": {"notWebReady": False},
        }
        if data.get("name"):
            stream["behaviorHints"]["filename"] = str(data["name"])
        # The download URL is a capability; never write this response to disk.
        return ConnectorResult({"streams": [stream]}, ttl=0, stale_seconds=0, persist=False)

    def health(self) -> dict[str, Any]:
        return {"id": self.id, "configured": self.secrets.has("premiumize.api_key")}
