from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from ..protocol import ResourceRequest
from .base import Connector, ConnectorResult


_ATTRIBUTE = re.compile(r'([\w-]+)="([^"]*)"')


@dataclass(frozen=True)
class Channel:
    id: str
    name: str
    url: str
    logo: str | None
    group: str | None


class LocalPlaylistConnector(Connector):
    """Explicit local M3U files with a strict HTTPS origin allowlist."""

    id = "local-playlist"

    def __init__(self, paths: tuple[Path, ...], allowed_hosts: tuple[str, ...]):
        self.paths = paths
        self.allowed_hosts = frozenset(allowed_hosts)

    def catalogs(self) -> list[dict[str, Any]]:
        return [
            {"type": "tv", "id": "local-authorized-tv", "name": "Authorized Local TV"}
        ]

    def _channels(self) -> list[Channel]:
        channels: list[Channel] = []
        for path in self.paths:
            if not path.is_absolute() or not path.is_file():
                continue
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            pending: dict[str, str] | None = None
            for raw in lines:
                line = raw.strip()
                if line.startswith("#EXTINF:"):
                    attrs = dict(_ATTRIBUTE.findall(line))
                    display = line.rsplit(",", 1)[-1].strip()
                    pending = {
                        "name": attrs.get("tvg-name") or display,
                        "logo": attrs.get("tvg-logo", ""),
                        "group": attrs.get("group-title", ""),
                    }
                    continue
                if not pending or not line or line.startswith("#"):
                    continue
                parsed = urlsplit(line)
                # Query strings, URL userinfo and unencrypted sources may carry
                # reusable provider credentials, so this conservative adapter rejects them.
                if (
                    parsed.scheme != "https"
                    or parsed.hostname not in self.allowed_hosts
                    or parsed.username
                    or parsed.password
                    or parsed.query
                    or parsed.fragment
                ):
                    pending = None
                    continue
                digest = hashlib.sha256(line.encode("utf-8")).hexdigest()[:24]
                channels.append(
                    Channel(
                        id=f"localtv:{digest}",
                        name=pending["name"] or "Unnamed channel",
                        url=line,
                        logo=pending["logo"] or None,
                        group=pending["group"] or None,
                    )
                )
                pending = None
        return channels

    @staticmethod
    def _meta(channel: Channel) -> dict[str, Any]:
        meta: dict[str, Any] = {
            "id": channel.id,
            "type": "tv",
            "name": channel.name,
            "behaviorHints": {"isLive": True},
        }
        if channel.logo:
            meta["poster"] = channel.logo
            meta["posterShape"] = "square"
        if channel.group:
            meta["genres"] = [channel.group]
        return meta

    def catalog(self, request: ResourceRequest) -> ConnectorResult | None:
        if (request.type, request.id) != ("tv", "local-authorized-tv"):
            return None
        return ConnectorResult(
            {"metas": [self._meta(channel) for channel in self._channels()]},
            ttl=300,
            stale_seconds=1800,
        )

    def meta(self, request: ResourceRequest) -> ConnectorResult | None:
        if not request.id.startswith("localtv:"):
            return None
        channel = next((item for item in self._channels() if item.id == request.id), None)
        return ConnectorResult({"meta": self._meta(channel) if channel else None}, ttl=300)

    def stream(self, request: ResourceRequest) -> ConnectorResult | None:
        if not request.id.startswith("localtv:"):
            return None
        channel = next((item for item in self._channels() if item.id == request.id), None)
        streams = [] if channel is None else [
            {
                "url": channel.url,
                "name": "Authorized playlist",
                "title": channel.name,
                "behaviorHints": {"notWebReady": False},
            }
        ]
        return ConnectorResult({"streams": streams}, ttl=0, stale_seconds=0, persist=False)

    def health(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "configured": bool(self.paths and self.allowed_hosts),
            "files": len(self.paths),
        }
