from __future__ import annotations

from abc import ABC
from dataclasses import dataclass
from typing import Any

from ..protocol import ResourceRequest


@dataclass(frozen=True)
class ConnectorResult:
    payload: dict[str, Any]
    ttl: int = 900
    stale_seconds: int = 86400
    persist: bool = True


class Connector(ABC):
    id = "connector"

    def catalogs(self) -> list[dict[str, Any]]:
        return []

    def catalog(self, request: ResourceRequest) -> ConnectorResult | None:
        return None

    def meta(self, request: ResourceRequest) -> ConnectorResult | None:
        return None

    def stream(self, request: ResourceRequest) -> ConnectorResult | None:
        return None

    def subtitles(self, request: ResourceRequest) -> ConnectorResult | None:
        return None

    def health(self) -> dict[str, Any]:
        return {"id": self.id, "configured": True}


class ConnectorRegistry:
    def __init__(self, connectors: list[Connector]):
        self.connectors = tuple(connectors)
        self._connectors = {connector.id: connector for connector in connectors}
        if len(self._connectors) != len(self.connectors):
            raise ValueError("Duplicate connector id")
        self._catalogs: dict[tuple[str, str], Connector] = {}
        for connector in connectors:
            for catalog in connector.catalogs():
                key = (str(catalog["type"]), str(catalog["id"]))
                if key in self._catalogs:
                    raise ValueError(f"Duplicate catalog {key}")
                self._catalogs[key] = connector

    def connector(self, connector_id: str) -> Connector | None:
        return self._connectors.get(connector_id)

    def catalogs(self, connector_id: str | None = None) -> list[dict[str, Any]]:
        connectors = self.connectors if connector_id is None else (
            (connector,) if (connector := self.connector(connector_id)) is not None else ()
        )
        return [catalog for connector in connectors for catalog in connector.catalogs()]

    def dispatch(self, request: ResourceRequest, connector_id: str | None = None) -> ConnectorResult:
        connectors = self.connectors if connector_id is None else (
            (connector,) if (connector := self.connector(connector_id)) is not None else ()
        )
        if request.resource == "catalog":
            connector = self._catalogs.get((request.type, request.id))
            if connector_id is not None and connector not in connectors:
                connector = None
            result = connector.catalog(request) if connector else None
            return result or ConnectorResult({"metas": []}, ttl=60)

        method_name = request.resource
        if method_name == "stream":
            streams: list[dict[str, Any]] = []
            for connector in connectors:
                result = connector.stream(request)
                if result:
                    streams.extend(result.payload.get("streams", []))
            return ConnectorResult({"streams": streams}, ttl=0, stale_seconds=0, persist=False)

        empty_key = "subtitles" if method_name == "subtitles" else "meta"
        for connector in connectors:
            method = getattr(connector, method_name)
            result = method(request)
            if result:
                return result
        fallback: dict[str, Any] = {empty_key: [] if empty_key == "subtitles" else None}
        return ConnectorResult(fallback, ttl=60)

    def health(self) -> list[dict[str, Any]]:
        return [connector.health() for connector in self.connectors]
