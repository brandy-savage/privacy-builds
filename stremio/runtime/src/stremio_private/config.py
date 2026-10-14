from __future__ import annotations

import os
import platform
try:
    import tomllib
except ModuleNotFoundError:  # macOS still ships Python 3.9 on some releases.
    from . import _tomllib_compat as tomllib
from dataclasses import dataclass
from pathlib import Path


def default_state_dir() -> Path:
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "StremioPrivate"
    root = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state"))
    return root / "stremio-private"


def default_config_path() -> Path:
    root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "stremio-private" / "config.toml"


def default_credentials_env_path() -> Path:
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Stremio Private" / ".env"
    root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "stremio-private" / ".env"


def default_personal_addons_path() -> Path:
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "Stremio Private" / "addons.json"
    root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return root / "stremio-private" / "addons.json"


@dataclass(frozen=True)
class Config:
    host: str = "127.0.0.1"
    port: int = 7000
    state_dir: Path = default_state_dir()
    cache_ttl_seconds: int = 900
    stale_seconds: int = 86400
    refresh_seconds: int = 900
    request_timeout_seconds: float = 12.0
    max_response_bytes: int = 2_000_000
    secret_backend: str = "keychain"
    credentials_env_path: Path = default_credentials_env_path()
    personal_addons_path: Path = default_personal_addons_path()
    enable_trakt: bool = True
    enable_premiumize: bool = True
    enable_tmdb: bool = True
    enable_compatibility: bool = True
    tmdb_region: str = "US"
    tmdb_providers: tuple[tuple[str, str, int], ...] = (
        ("netflix", "Netflix", 8),
        ("max", "Max", 189),
    )
    macos_players: tuple[str, ...] = ("vlc", "system", "internal")
    android_players: tuple[str, ...] = ("vlc", "mx_player", "system", "internal")
    playlist_files: tuple[Path, ...] = ()
    playlist_allowed_hosts: tuple[str, ...] = ()

    @property
    def cache_path(self) -> Path:
        return self.state_dir / "cache.sqlite3"

    @property
    def secret_file_path(self) -> Path:
        return self.state_dir / "secrets.json"

    @property
    def is_loopback(self) -> bool:
        return self.host in {"127.0.0.1", "::1", "localhost"}


def load_config(path: Path | None = None) -> Config:
    path = path or default_config_path()
    if not path.exists():
        return Config()
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    server = raw.get("server", {})
    cache = raw.get("cache", {})
    connectors = raw.get("connectors", {})
    secrets = raw.get("secrets", {})
    tmdb = raw.get("tmdb", {})
    playback = raw.get("playback", {})
    playlist = raw.get("playlist", {})
    addons = raw.get("addons", {})
    provider_rows = tmdb.get(
        "providers",
        [
            {"id": "netflix", "name": "Netflix", "provider_id": 8},
            {"id": "max", "name": "Max", "provider_id": 189},
        ],
    )
    providers = tuple(
        (str(row["id"]), str(row["name"]), int(row["provider_id"]))
        for row in provider_rows
    )
    return Config(
        host=str(server.get("host", "127.0.0.1")),
        port=int(server.get("port", 7000)),
        state_dir=Path(server.get("state_dir", default_state_dir())).expanduser(),
        cache_ttl_seconds=int(cache.get("ttl_seconds", 900)),
        stale_seconds=int(cache.get("stale_seconds", 86400)),
        refresh_seconds=int(cache.get("refresh_seconds", 900)),
        request_timeout_seconds=float(server.get("request_timeout_seconds", 12)),
        max_response_bytes=int(server.get("max_response_bytes", 2_000_000)),
        secret_backend=str(secrets.get("backend", "keychain")),
        credentials_env_path=Path(
            secrets.get("env_file", default_credentials_env_path())
        ).expanduser(),
        personal_addons_path=Path(
            addons.get("file", default_personal_addons_path())
        ).expanduser(),
        enable_trakt=bool(connectors.get("trakt", True)),
        enable_premiumize=bool(connectors.get("premiumize", True)),
        enable_tmdb=bool(connectors.get("tmdb", True)),
        enable_compatibility=bool(connectors.get("compatibility", True)),
        tmdb_region=str(tmdb.get("region", "US")).upper(),
        tmdb_providers=providers,
        macos_players=tuple(playback.get("macos", ["vlc", "system", "internal"])),
        android_players=tuple(
            playback.get("android", ["vlc", "mx_player", "system", "internal"])
        ),
        playlist_files=tuple(Path(value).expanduser() for value in playlist.get("files", [])),
        playlist_allowed_hosts=tuple(str(value).lower() for value in playlist.get("allowed_hosts", [])),
    )
