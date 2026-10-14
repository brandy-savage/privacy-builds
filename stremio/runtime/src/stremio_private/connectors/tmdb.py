from __future__ import annotations

from typing import Any

from ..http_client import SafeHttpClient, UpstreamError
from ..protocol import ResourceRequest
from ..secrets import SecretStore
from .base import Connector, ConnectorResult


class TMDBConnector(Connector):
    id = "tmdb"
    HOST = "api.themoviedb.org"
    BASE = "https://api.themoviedb.org/3"
    IMAGE_BASE = "https://image.tmdb.org/t/p"

    def __init__(
        self,
        secrets: SecretStore,
        http: SafeHttpClient,
        *,
        region: str,
        providers: tuple[tuple[str, str, int], ...],
    ):
        self.secrets = secrets
        self.http = http
        self.region = region
        self.providers = providers

    def catalogs(self) -> list[dict[str, Any]]:
        extras = [
            {"name": "search", "isRequired": False},
            {"name": "skip", "isRequired": False},
        ]
        catalogs = [
            {"type": "movie", "id": "tmdb-trending-movies", "name": "Trending Movies", "extra": extras},
            {"type": "series", "id": "tmdb-trending-series", "name": "Trending Series", "extra": extras},
        ]
        for slug, name, _provider_id in self.providers:
            catalogs.extend(
                [
                    {"type": "movie", "id": f"tmdb-provider-{slug}-movies", "name": f"{name} Movies", "extra": extras},
                    {"type": "series", "id": f"tmdb-provider-{slug}-series", "name": f"{name} Series", "extra": extras},
                ]
            )
        return catalogs

    def _headers(self) -> dict[str, str] | None:
        token = self.secrets.get("tmdb.read_token")
        return {"Authorization": f"Bearer {token}", "accept": "application/json"} if token else None

    @staticmethod
    def _tmdb_type(media_type: str) -> str:
        return "tv" if media_type == "series" else "movie"

    @classmethod
    def _meta(cls, media_type: str, item: dict[str, Any]) -> dict[str, Any] | None:
        item_id = item.get("id")
        name = item.get("title") or item.get("name")
        if item_id is None or not name:
            return None
        result: dict[str, Any] = {
            "id": f"tmdb:{media_type}:{item_id}",
            "type": media_type,
            "name": str(name),
        }
        if item.get("overview"):
            result["description"] = str(item["overview"])
        date = item.get("release_date") or item.get("first_air_date")
        if date:
            result["releaseInfo"] = str(date)[:4]
        if item.get("poster_path"):
            result["poster"] = f"{cls.IMAGE_BASE}/w500{item['poster_path']}"
        if item.get("backdrop_path"):
            result["background"] = f"{cls.IMAGE_BASE}/original{item['backdrop_path']}"
        genres = item.get("genres")
        if isinstance(genres, list):
            result["genres"] = [
                str(genre.get("name"))
                for genre in genres
                if isinstance(genre, dict) and genre.get("name")
            ]
        return result

    def catalog(self, request: ResourceRequest) -> ConnectorResult | None:
        if not request.id.startswith("tmdb-"):
            return None
        headers = self._headers()
        if not headers:
            return ConnectorResult({"metas": []}, ttl=60)
        media = self._tmdb_type(request.type)
        skip = max(0, int(request.extra.get("skip", "0") or 0))
        page = skip // 20 + 1
        search = request.extra.get("search", "").strip()
        query = {"language": "en-US", "page": str(page)}
        if search:
            endpoint = f"search/{media}"
            query["query"] = search
        elif request.id.startswith("tmdb-trending-"):
            endpoint = f"trending/{media}/week"
        else:
            provider = next(
                (row for row in self.providers if f"tmdb-provider-{row[0]}-" in request.id),
                None,
            )
            if provider is None:
                return None
            endpoint = f"discover/{media}"
            query.update(
                {
                    "watch_region": self.region,
                    "with_watch_providers": str(provider[2]),
                    "sort_by": "popularity.desc",
                }
            )
        data = self.http.get_json(
            f"{self.BASE}/{endpoint}", allowed_host=self.HOST, headers=headers, query=query
        )
        if not isinstance(data, dict) or not isinstance(data.get("results"), list):
            raise UpstreamError("TMDB response had an unexpected shape")
        metas = [
            meta
            for item in data["results"]
            if isinstance(item, dict)
            if (meta := self._meta(request.type, item))
        ]
        return ConnectorResult({"metas": metas}, ttl=3600, stale_seconds=86400)

    def meta(self, request: ResourceRequest) -> ConnectorResult | None:
        parts = request.id.split(":")
        if len(parts) != 3 or parts[0] != "tmdb" or parts[1] != request.type or not parts[2].isdigit():
            return None
        headers = self._headers()
        if not headers:
            return None
        media = self._tmdb_type(request.type)
        data = self.http.get_json(
            f"{self.BASE}/{media}/{parts[2]}",
            allowed_host=self.HOST,
            headers=headers,
            query={"language": "en-US", "append_to_response": "external_ids"},
        )
        if not isinstance(data, dict):
            raise UpstreamError("TMDB response had an unexpected shape")
        meta = self._meta(request.type, data)
        external = data.get("external_ids") or {}
        if meta and (imdb_id := data.get("imdb_id") or external.get("imdb_id")):
            meta["imdb_id"] = imdb_id
        return ConnectorResult({"meta": meta}, ttl=86400, stale_seconds=604800)

    def health(self) -> dict[str, Any]:
        return {"id": self.id, "configured": self.secrets.has("tmdb.read_token")}
