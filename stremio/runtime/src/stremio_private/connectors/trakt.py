from __future__ import annotations

from typing import Any

from ..http_client import SafeHttpClient, UpstreamError
from ..protocol import ResourceRequest
from ..secrets import SecretStore
from .base import Connector, ConnectorResult


class TraktConnector(Connector):
    id = "trakt"
    HOST = "api.trakt.tv"
    BASE = "https://api.trakt.tv"

    def __init__(self, secrets: SecretStore, http: SafeHttpClient):
        self.secrets = secrets
        self.http = http

    def catalogs(self) -> list[dict[str, Any]]:
        extra = [{"name": "skip", "isRequired": False}]
        return [
            {"type": "movie", "id": "trakt-watchlist-movies", "name": "Trakt Watchlist", "extra": extra},
            {"type": "series", "id": "trakt-watchlist-series", "name": "Trakt Watchlist", "extra": extra},
        ]

    def _headers(self, *, authenticated: bool = True) -> dict[str, str] | None:
        client_id = self.secrets.get("trakt.client_id")
        token = self.secrets.get("trakt.access_token")
        if not client_id or (authenticated and not token):
            return None
        headers = {
            "Content-Type": "application/json",
            "trakt-api-version": "2",
            "trakt-api-key": client_id,
        }
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    @staticmethod
    def _preview(media_type: str, item: dict[str, Any]) -> dict[str, Any] | None:
        ids = item.get("ids") or {}
        item_id = ids.get("imdb") or (f"trakt:{ids.get('trakt')}" if ids.get("trakt") else None)
        title = item.get("title") or item.get("name")
        if not item_id or not title:
            return None
        preview: dict[str, Any] = {
            "id": str(item_id),
            "type": media_type,
            "name": str(title),
        }
        year = item.get("year")
        if year:
            preview["releaseInfo"] = str(year)
        if item.get("overview"):
            preview["description"] = str(item["overview"])
        genres = item.get("genres")
        if isinstance(genres, list):
            preview["genres"] = [str(genre) for genre in genres]
        return preview

    def catalog(self, request: ResourceRequest) -> ConnectorResult | None:
        mapping = {
            ("movie", "trakt-watchlist-movies"): ("movies", "movie"),
            ("series", "trakt-watchlist-series"): ("shows", "show"),
        }
        target = mapping.get((request.type, request.id))
        if not target:
            return None
        headers = self._headers(authenticated=True)
        if not headers:
            return ConnectorResult({"metas": []}, ttl=60)
        endpoint, object_key = target
        skip = max(0, int(request.extra.get("skip", "0") or 0))
        page = skip // 100 + 1
        data = self.http.get_json(
            f"{self.BASE}/sync/watchlist/{endpoint}/added",
            allowed_host=self.HOST,
            headers=headers,
            query={"extended": "full", "page": str(page), "limit": "100"},
        )
        if not isinstance(data, list):
            raise UpstreamError("Trakt watchlist response had an unexpected shape")
        metas = []
        for wrapper in data:
            item = wrapper.get(object_key, {}) if isinstance(wrapper, dict) else {}
            preview = self._preview(request.type, item)
            if preview:
                metas.append(preview)
        return ConnectorResult({"metas": metas}, ttl=900, stale_seconds=86400)

    def meta(self, request: ResourceRequest) -> ConnectorResult | None:
        if not request.id.startswith("tt"):
            return None
        headers = self._headers(authenticated=False)
        if not headers:
            return None
        data = self.http.get_json(
            f"{self.BASE}/search/imdb/{request.id}",
            allowed_host=self.HOST,
            headers=headers,
            query={"type": "movie,show", "extended": "full"},
        )
        if not isinstance(data, list):
            raise UpstreamError("Trakt search response had an unexpected shape")
        wanted_key = "movie" if request.type == "movie" else "show"
        for wrapper in data:
            if not isinstance(wrapper, dict) or wanted_key not in wrapper:
                continue
            meta = self._preview(request.type, wrapper[wanted_key])
            if meta:
                return ConnectorResult({"meta": meta}, ttl=86400, stale_seconds=604800)
        return ConnectorResult({"meta": None}, ttl=300)

    def health(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "configured": self.secrets.has("trakt.client_id")
            and self.secrets.has("trakt.access_token"),
        }
