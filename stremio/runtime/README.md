# Stremio Private Companion Runtime

A dependency-free Python service that speaks the Stremio addon protocol while
keeping personal credentials and most catalog state on the machine running it.
It is a foundation for a private single-user setup, not a public scraping or
credential-sharing service.

## What works

- Stremio `manifest`, `catalog`, `meta`, `stream`, and `subtitles` routes.
- Trakt watchlist catalogs with a fresh user-supplied OAuth token.
- TMDB trending and configurable provider catalogs using a Bearer read token.
- A private Premiumize cloud catalog for video files already in the user's
  account. It does not search third-party sources or create remote transfers.
- Narrow, host-allowlisted compatibility adapters for Cinemeta metadata and
  OpenSubtitles v3. The adapter class can cover other public, non-configured
  addons without accepting opaque upstream URLs.
- Optional local M3U catalogs. Only explicitly configured files are read, and
  only credential-free HTTPS streams on exact allowlisted hosts are returned.
- SQLite response caching, stale-on-error behavior, and scheduled catalog
  refresh. Stream responses are never written to disk.
- `/healthz`, `/readyz`, and an authenticated `/policy/playback.json` handoff
  policy for patched clients.
- A loopback-only `/addons/index.json` plus scoped manifests for the Trakt,
  Premiumize, TMDB, local-playlist, Cinemeta-cache, and OpenSubtitles-cache
  connectors so each appears independently in the client's Addons screen.
- An explicit migration tool for selected configured Stremio addons. Their
  potentially credential-bearing transport URLs live only in a mode-`0600`
  local file and are never copied into the app or source archive.
- macOS Keychain storage via the system `security` tool's stdin prompt, so
  credentials never appear in a process command line. A simple mode-`0600`
  `.env` overlay is read first; the strict file backend remains available for
  systems without Keychain and is explicitly not encrypted at rest.
- `/addons/status.json` reports only configured/not-configured booleans, the
  local credential-file path, and the private build ID. It never returns values.

No analytics, crash reporting, install identifier, viewing telemetry, cookies,
or request-path logging is present.

## Install and run

```sh
cd /path/to/runtime
python3 -m venv .venv
.venv/bin/python -m pip install -e .
mkdir -p "$HOME/.config/stremio-private"
cp config.example.toml "$HOME/.config/stremio-private/config.toml"
```

Credentials start blank. The packaged macOS app creates this file automatically:

```text
~/Library/Application Support/Stremio Private/.env
```

Edit only the blank values you want, then restart the app:

```dotenv
PREMIUMIZE_API_KEY=
TMDB_READ_TOKEN=
TRAKT_CLIENT_ID=
TRAKT_CLIENT_SECRET=
TRAKT_ACCESS_TOKEN=
TRAKT_REFRESH_TOKEN=
```

The file is forced to mode `0600`; its parser allowlists those names and does
not perform shell expansion. Process environment values override the file,
which overrides the configured Keychain/file backend. The Addons screen shows
the exact path and configured/not-configured status without exposing values.
The CLI backend is still available; input is hidden and never echoed:

```sh
.venv/bin/stremio-private secret set premiumize.api_key
.venv/bin/stremio-private secret set tmdb.read_token
.venv/bin/stremio-private secret set trakt.client_id
.venv/bin/stremio-private secret set trakt.access_token
```

The existing Stremio profile is **not** imported automatically. To restore
selected configured stream/catalog addons for this single-user installation,
run `python3 tools/migrate_stremio_addons.py --allow-id EXPLICIT_MANIFEST_ID`.
Repeat `--allow-id` for each descriptor you have inspected and approved. This writes only to
`~/Library/Application Support/Stremio Private/addons.json` with mode `0600`.
These addons remain remote services: their operators receive the requests sent
to them, and the private companion cannot audit or guarantee their behavior.

In particular,
the installed Trakt addon's opaque configuration UUID is not an OAuth token.
Create a fresh Trakt app authorization (device flow or PKCE), then explicitly
store the resulting client ID and access token. A later migration command may
import known fields only after showing a redacted preview; opaque config blobs
must never be replayed.

For standalone use, start the service and install its manifest URL in Stremio:

```sh
.venv/bin/stremio-private serve
.venv/bin/stremio-private url
```

The packaged **Stremio Private** desktop app starts and installs its bundled
copy automatically on `127.0.0.1:17100`; do not start a second copy for that
app. A parent-process watchdog stops the bundled service when the desktop
engine exits. The standalone default listener is `127.0.0.1:7000`. For unattended macOS operation, edit
the two placeholders in `launchd/com.local.stremio-private.plist.example`, copy
it to `~/Library/LaunchAgents/com.local.stremio-private.plist`, and load it with
`launchctl bootstrap gui/$(id -u) ...`. This is the recommended zero-cost host:
the same machine owns the credentials, cache, and service lifetime.

## LAN mode

Change `server.host` only after creating a random local capability:

```sh
.venv/bin/stremio-private secret init-lan-token
```

Non-loopback startup is refused without that token. LAN URLs use a capability
prefix; the server never logs it. Keep the port behind the host firewall and a
private network. Do not expose this HTTP listener to the public internet.

## Player handoff preference

`/policy/playback.json` gives patched clients a deterministic fallback order:

- macOS: VLC → system/default → Stremio internal player.
- Android: VLC → MX Player → system/default → Stremio internal player.

This is metadata for the client patch; the addon protocol cannot itself choose
an installed external-player application. The policy contains no playback URL,
account key, or token.

## Tests

```sh
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for trust boundaries,
connector rules, protocol sources, and the remaining production work.
