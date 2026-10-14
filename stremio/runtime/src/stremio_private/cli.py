from __future__ import annotations

import argparse
import getpass
import os
import secrets as token_secrets
import sys
import threading
import time
from pathlib import Path

from .app import CompanionApp
from .cache import CacheStore
from .config import default_config_path, load_config
from .connectors import (
    CompatibilityProxyConnector,
    CompatibilityTarget,
    ConnectorRegistry,
    LocalPlaylistConnector,
    PremiumizeConnector,
    TMDBConnector,
    TraktConnector,
)
from .http_client import SafeHttpClient
from .scheduler import RefreshScheduler
from .secrets import (
    ALLOWED_SECRET_NAMES,
    DotEnvSecretStore,
    SecretStoreError,
    create_secret_store,
    ensure_dotenv_template,
)
from .server import RuntimeServer


PARENT_PID_ENV = "STREMIO_PRIVATE_PARENT_PID"


def _watch_parent(server: RuntimeServer, parent_pid: int, poll_interval: float = 0.5) -> None:
    """Stop the companion if the desktop engine that launched it disappears."""
    while os.getppid() == parent_pid:
        time.sleep(poll_interval)
    server.shutdown()


def build_app(config_path: Path | None = None) -> CompanionApp:
    config = load_config(config_path)
    config.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    ensure_dotenv_template(config.credentials_env_path)
    secret_store = DotEnvSecretStore(
        config.credentials_env_path,
        create_secret_store(config.secret_backend, config.secret_file_path),
    )
    http = SafeHttpClient(
        timeout=config.request_timeout_seconds,
        max_bytes=config.max_response_bytes,
    )
    connectors = []
    if config.enable_trakt:
        connectors.append(TraktConnector(secret_store, http))
    if config.enable_premiumize:
        connectors.append(PremiumizeConnector(secret_store, http))
    if config.enable_tmdb:
        connectors.append(
            TMDBConnector(
                secret_store,
                http,
                region=config.tmdb_region,
                providers=config.tmdb_providers,
            )
        )
    # Keep the local-playlist connector present even before it is configured so
    # its blank-auth addon surface is visible and ready for local setup.
    connectors.append(
        LocalPlaylistConnector(config.playlist_files, config.playlist_allowed_hosts)
    )
    if config.enable_compatibility:
        connectors.extend(
            [
                CompatibilityProxyConnector(
                    CompatibilityTarget(
                        id="cinemeta",
                        base_url="https://v3-cinemeta.strem.io",
                        allowed_host="v3-cinemeta.strem.io",
                        resources=frozenset({"catalog", "meta"}),
                        catalogs=(
                            {"type": "movie", "id": "top", "name": "Cinemeta Popular"},
                            {"type": "series", "id": "top", "name": "Cinemeta Popular"},
                        ),
                    ),
                    http,
                ),
                CompatibilityProxyConnector(
                    CompatibilityTarget(
                        id="opensubtitles-v3",
                        base_url="https://opensubtitles-v3.strem.io",
                        allowed_host="opensubtitles-v3.strem.io",
                        resources=frozenset({"subtitles"}),
                    ),
                    http,
                ),
            ]
        )
    return CompanionApp(
        config,
        secret_store,
        CacheStore(config.cache_path),
        ConnectorRegistry(connectors),
    )


def _set_secret(app: CompanionApp, name: str) -> int:
    if name not in ALLOWED_SECRET_NAMES:
        print("Unsupported secret name", file=sys.stderr)
        return 2
    value = getpass.getpass(f"Enter {name}: ")
    if not value:
        print("Empty value rejected", file=sys.stderr)
        return 2
    app.secrets.set(name, value)
    print(f"Stored {name}; value was not printed.")
    return 0


def _status(app: CompanionApp) -> int:
    status = app.status()
    print(f"ready: {str(status['ready']).lower()}")
    for connector in status["connectors"]:
        print(f"{connector['id']}: {'configured' if connector['configured'] else 'not configured'}")
    return 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="stremio-private")
    result.add_argument("--config", type=Path, default=default_config_path())
    sub = result.add_subparsers(dest="command", required=True)
    sub.add_parser("serve", help="Run the local addon service")
    sub.add_parser("status", help="Show readiness without secret values")
    sub.add_parser("url", help="Print the manifest URL")
    secret = sub.add_parser("secret", help="Manage machine-local secrets")
    secret_sub = secret.add_subparsers(dest="secret_command", required=True)
    set_parser = secret_sub.add_parser("set")
    set_parser.add_argument("name", choices=sorted(ALLOWED_SECRET_NAMES))
    secret_sub.add_parser("init-lan-token")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    app: CompanionApp | None = None
    try:
        app = build_app(args.config)
        if args.command == "status":
            return _status(app)
        if args.command == "url":
            print(app.install_url())
            return 0
        if args.command == "secret":
            if args.secret_command == "set":
                return _set_secret(app, args.name)
            if args.secret_command == "init-lan-token":
                app.secrets.set("runtime.lan_token", token_secrets.token_urlsafe(32))
                print("Stored a new LAN capability token; value was not printed.")
                return 0
        if args.command == "serve":
            if not app.config.is_loopback and not app.secrets.has("runtime.lan_token"):
                print("Refusing LAN bind without runtime.lan_token", file=sys.stderr)
                return 2
            scheduler = RefreshScheduler(app, app.config.refresh_seconds)
            server = RuntimeServer((app.config.host, app.config.port), app)
            parent_pid_text = os.environ.get(PARENT_PID_ENV)
            if parent_pid_text:
                try:
                    parent_pid = int(parent_pid_text)
                except ValueError:
                    print(f"Ignoring invalid {PARENT_PID_ENV}", file=sys.stderr)
                else:
                    threading.Thread(
                        target=_watch_parent,
                        args=(server, parent_pid),
                        name="desktop-parent-watch",
                        daemon=True,
                    ).start()
            scheduler.start()
            print(f"Stremio private runtime listening on {app.config.host}:{app.config.port}")
            print("Request paths and credential values are not logged.")
            try:
                server.serve_forever(poll_interval=0.5)
            except KeyboardInterrupt:
                pass
            finally:
                scheduler.stop()
                server.server_close()
            return 0
    except (SecretStoreError, OSError, RuntimeError) as exc:
        print(f"stremio-private: {exc}", file=sys.stderr)
        return 1
    finally:
        if app:
            app.close()
    return 0
