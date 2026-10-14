from __future__ import annotations

import hashlib
import hmac
import json
import re
import stat
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlsplit

from .cache import CacheStore
from .config import Config
from .connectors import ConnectorRegistry
from .protocol import ResourceRequest, cache_control, parse_resource_path
from .secrets import SecretStore


@dataclass(frozen=True)
class AppResponse:
    status: int
    body: dict[str, Any]
    headers: dict[str, str]


class CompanionApp:
    BUILD_ID = "2026.10.13-personal-streams-r13"
    VIRTUAL_ADDONS = {
        "trakt": {
            "manifest_id": "local.privacy.trakt",
            "name": "Private Trakt",
            "description": "Local Trakt watchlists and metadata. Add credentials locally to enable.",
            "resources": ["catalog", "meta"],
            "types": ["movie", "series"],
        },
        "premiumize": {
            "manifest_id": "local.privacy.premiumize",
            "name": "Private Premiumize",
            "description": "Local access to account-owned Premiumize cloud files. Add credentials locally to enable.",
            "resources": ["catalog", "meta", "stream"],
            "types": ["movie"],
        },
        "tmdb": {
            "manifest_id": "local.privacy.tmdb",
            "name": "Private TMDB",
            "description": "Locally cached trending and provider catalogs. Add a TMDB read token locally to enable.",
            "resources": ["catalog", "meta"],
            "types": ["movie", "series"],
        },
        "local-playlist": {
            "manifest_id": "local.privacy.playlist",
            "name": "Private Local TV",
            "description": "Allowlisted local playlists with credential-free HTTPS streams.",
            "resources": ["catalog", "meta", "stream"],
            "types": ["tv"],
        },
        "compat-cinemeta": {
            "manifest_id": "local.privacy.cinemeta-cache",
            "name": "Cinemeta Privacy Cache",
            "description": "Narrow local caching proxy for Cinemeta metadata and catalogs.",
            "resources": ["catalog", "meta"],
            "types": ["movie", "series"],
        },
        "compat-opensubtitles-v3": {
            "manifest_id": "local.privacy.opensubtitles-cache",
            "name": "OpenSubtitles Privacy Cache",
            "description": "Narrow local caching proxy for OpenSubtitles v3.",
            "resources": ["subtitles"],
            "types": ["movie", "series"],
        },
    }

    def __init__(
        self,
        config: Config,
        secrets: SecretStore,
        cache: CacheStore,
        registry: ConnectorRegistry,
    ):
        self.config = config
        self.secrets = secrets
        self.cache = cache
        self.registry = registry
        self._refresh_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="refresh")

    @property
    def manifest(self) -> dict[str, Any]:
        return {
            "id": "local.privacy.stremio.companion",
            "version": "0.1.0",
            "name": "Private Companion",
            "description": "Local-first personal catalogs and private cloud media.",
            "resources": [
                "catalog",
                {
                    "name": "meta",
                    "types": ["movie", "series", "tv"],
                    "idPrefixes": ["tt", "trakt:", "pm:", "localtv:"],
                },
                {
                    "name": "stream",
                    "types": ["movie", "series", "tv"],
                    "idPrefixes": ["pm:", "localtv:"],
                },
                "subtitles",
            ],
            "types": ["movie", "series", "tv"],
            "catalogs": self.registry.catalogs(),
            "behaviorHints": {"configurable": False, "configurationRequired": False},
        }

    def _virtual_manifest(self, connector_id: str) -> dict[str, Any] | None:
        definition = self.VIRTUAL_ADDONS.get(connector_id)
        if definition is None or self.registry.connector(connector_id) is None:
            return None
        return {
            "id": definition["manifest_id"],
            "version": "0.1.0",
            "name": definition["name"],
            "description": definition["description"],
            "resources": definition["resources"],
            "types": definition["types"],
            "catalogs": self.registry.catalogs(connector_id),
            "behaviorHints": {"configurable": False, "configurationRequired": False},
        }

    def _base_url(self) -> str:
        host = "127.0.0.1" if self.config.host == "0.0.0.0" else self.config.host
        return f"http://{host}:{self.config.port}"

    def addon_descriptors(self) -> list[dict[str, Any]]:
        descriptors = [{"transportUrl": self.install_url(), "manifest": self.manifest}]
        base_url = self._base_url()
        for connector_id in self.VIRTUAL_ADDONS:
            manifest = self._virtual_manifest(connector_id)
            if manifest is not None:
                descriptors.append({
                    "transportUrl": f"{base_url}/addons/{connector_id}/manifest.json",
                    "manifest": manifest,
                })
        descriptors.extend(self._personal_addon_descriptors())
        return descriptors

    def _personal_addon_descriptors(self) -> list[dict[str, Any]]:
        path = self.config.personal_addons_path
        try:
            file_stat = path.stat()
            if stat.S_IMODE(file_stat.st_mode) != 0o600 or file_stat.st_size > 2_000_000:
                return []
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return []

        rows = raw.get("addons", []) if isinstance(raw, dict) else []
        if not isinstance(rows, list) or len(rows) > 64:
            return []
        descriptors: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            transport_url = row.get("transportUrl")
            manifest = row.get("manifest")
            if not isinstance(transport_url, str) or not isinstance(manifest, dict):
                continue
            parsed = urlsplit(transport_url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
                continue
            manifest_id = manifest.get("id")
            manifest_name = manifest.get("name")
            if not isinstance(manifest_id, str) or not manifest_id.strip():
                continue
            if not isinstance(manifest_name, str) or not manifest_name.strip():
                continue
            if (
                manifest_id == "org.stremio.watchhub"
                or parsed.hostname.lower() == "watchhub.strem.io"
                or manifest_id.startswith("local.privacy.")
            ):
                continue
            descriptors.append({"transportUrl": transport_url, "manifest": manifest})
        return descriptors

    def _base_headers(self, content_type: str = "application/json; charset=utf-8") -> dict[str, str]:
        return {
            "Content-Type": content_type,
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type",
            "Referrer-Policy": "no-referrer",
            "X-Content-Type-Options": "nosniff",
            "Content-Security-Policy": "default-src 'none'; frame-ancestors 'none'",
        }

    def _response(
        self,
        status: int,
        body: dict[str, Any],
        *,
        max_age: int = 0,
        stale: int = 0,
    ) -> AppResponse:
        headers = self._base_headers()
        headers["Cache-Control"] = cache_control(max_age, stale, stale)
        return AppResponse(status, body, headers)

    def _authorized_path(self, path: str) -> str | None:
        clean = urlsplit(path).path
        if self.config.is_loopback:
            return clean
        token = self.secrets.get("runtime.lan_token")
        if not token:
            return None
        parts = clean.split("/")
        if len(parts) < 4 or parts[1] != "a" or not hmac.compare_digest(parts[2], token):
            return None
        return "/" + "/".join(parts[3:])

    @staticmethod
    def _cache_key(request: ResourceRequest, connector_id: str | None = None) -> str:
        raw = json.dumps(
            {
                "resource": request.resource,
                "type": request.type,
                "id": request.id,
                "extra": request.extra,
                "connector": connector_id,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _load(self, request: ResourceRequest, key: str, connector_id: str | None = None) -> AppResponse:
        result = self.registry.dispatch(request, connector_id)
        if result.persist and result.ttl > 0:
            self.cache.put(
                key,
                result.payload,
                ttl=result.ttl,
                stale_seconds=result.stale_seconds,
            )
        return self._response(
            200,
            result.payload,
            max_age=result.ttl,
            stale=result.stale_seconds,
        )

    def _refresh(self, request: ResourceRequest, key: str, connector_id: str | None = None) -> None:
        try:
            result = self.registry.dispatch(request, connector_id)
            if result.persist and result.ttl > 0:
                self.cache.put(
                    key,
                    result.payload,
                    ttl=result.ttl,
                    stale_seconds=result.stale_seconds,
                )
        except Exception:
            # Background refresh failures are deliberately silent and never include
            # upstream response bodies, URLs, tokens, or file names in logs.
            return

    def handle(self, path: str, *, method: str = "GET") -> AppResponse:
        public_path = urlsplit(path).path
        if method == "OPTIONS":
            return AppResponse(204, {}, self._base_headers())
        if method != "GET":
            return self._response(405, {"error": "method_not_allowed"})
        if public_path == "/healthz":
            return self._response(200, {"status": "ok"})
        if public_path == "/readyz":
            ready = self.cache.writable()
            return self._response(200 if ready else 503, {"status": "ready" if ready else "unavailable"})

        clean_path = self._authorized_path(path)
        if clean_path is None:
            return self._response(404, {"error": "not_found"})
        if clean_path == "/manifest.json":
            return self._response(200, self.manifest, max_age=300)
        if clean_path == "/addons/index.json":
            return self._response(200, {"addons": self.addon_descriptors()}, max_age=60)
        if clean_path == "/addons/status.json":
            status = self.status()
            connector_status = {
                item["id"]: bool(item["configured"])
                for item in status["connectors"]
            }
            env_path = self.config.credentials_env_path
            try:
                display_path = "~/" + str(env_path.relative_to(env_path.home()))
            except ValueError:
                display_path = str(env_path)
            return self._response(
                200,
                {
                    "build": self.BUILD_ID,
                    "ready": status["ready"],
                    "credentials": {
                        "path": str(env_path),
                        "displayPath": display_path,
                        "directoryUrl": env_path.parent.as_uri(),
                        "restartAfterEditing": True,
                    },
                    "connectors": connector_status,
                },
            )
        if clean_path == "/policy/playback.json":
            return self._response(
                200,
                {
                    "version": 1,
                    "macos": list(self.config.macos_players),
                    "android": list(self.config.android_players),
                    "note": "Client-side preference only; no credentials or playback URLs are stored here.",
                },
                max_age=300,
            )

        connector_id = None
        virtual_match = re.fullmatch(r"/addons/([^/]+)(/.*)", clean_path)
        if virtual_match:
            connector_id, clean_path = virtual_match.groups()
            manifest = self._virtual_manifest(connector_id)
            if manifest is None:
                return self._response(404, {"error": "not_found"})
            if clean_path == "/manifest.json":
                return self._response(200, manifest, max_age=300)

        request = parse_resource_path(clean_path)
        if request is None:
            return self._response(404, {"error": "not_found"})
        key = self._cache_key(request, connector_id)
        hit = None if request.resource == "stream" else self.cache.get(key)
        if hit and hit.state == "fresh":
            return self._response(200, hit.value, max_age=self.config.cache_ttl_seconds)
        if hit and hit.state == "stale":
            self._refresh_pool.submit(self._refresh, request, key, connector_id)
            return self._response(200, hit.value, max_age=0, stale=self.config.stale_seconds)
        try:
            return self._load(request, key, connector_id)
        except Exception:
            return self._response(503, {"error": "upstream_unavailable"})

    def refresh_catalogs(self) -> None:
        for catalog in self.registry.catalogs():
            request = ResourceRequest("catalog", str(catalog["type"]), str(catalog["id"]), {})
            self._refresh(request, self._cache_key(request))
        self.cache.delete_expired()

    def status(self) -> dict[str, Any]:
        return {
            "ready": self.cache.writable(),
            "connectors": self.registry.health(),
        }

    def install_url(self) -> str:
        host = self.config.host
        if host == "0.0.0.0":
            host = "127.0.0.1"
        prefix = ""
        if not self.config.is_loopback:
            token = self.secrets.get("runtime.lan_token")
            if not token:
                raise RuntimeError("LAN mode requires runtime.lan_token")
            prefix = f"/a/{quote(token, safe='')}"
        return f"http://{host}:{self.config.port}{prefix}/manifest.json"

    def close(self) -> None:
        self._refresh_pool.shutdown(wait=False, cancel_futures=True)
