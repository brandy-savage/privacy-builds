from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qsl, unquote, urlsplit


@dataclass(frozen=True)
class ResourceRequest:
    resource: str
    type: str
    id: str
    extra: dict[str, str]


def parse_resource_path(path: str) -> ResourceRequest | None:
    """Parse Stremio's /resource/type/id[/extra].json route."""
    clean = urlsplit(path).path.strip("/")
    parts = clean.split("/") if clean else []
    if len(parts) not in {3, 4}:
        return None
    resource, media_type, raw_id = parts[:3]
    if resource not in {"catalog", "meta", "stream", "subtitles"}:
        return None
    tail = parts[3] if len(parts) == 4 else ""
    target = tail or raw_id
    if not target.endswith(".json"):
        return None
    if tail:
        raw_id = raw_id
        extra_blob = target[:-5]
    else:
        raw_id = target[:-5]
        extra_blob = ""
    extra = dict(parse_qsl(unquote(extra_blob), keep_blank_values=True))
    return ResourceRequest(resource, unquote(media_type), unquote(raw_id), extra)


def cache_control(max_age: int, stale_revalidate: int = 0, stale_error: int = 0) -> str:
    directives = [f"max-age={max(0, int(max_age))}"]
    if stale_revalidate:
        directives.append(f"stale-while-revalidate={max(0, int(stale_revalidate))}")
    if stale_error:
        directives.append(f"stale-if-error={max(0, int(stale_error))}")
    return ", ".join(directives)
