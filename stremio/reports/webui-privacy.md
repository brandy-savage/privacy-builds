# Pinned Stremio Web privacy build

The desktop bundle includes a production build of the official GPL-2.0
`Stremio/stremio-web` client pinned to commit
`9d1d526591b4c076c7307a1ba9ec056d483f169a`.

Local privacy changes:

- the UI transport's analytics method is a no-op, so route, stream-click, and
  interaction events are not forwarded to the Stremio core analytics queue;
- Sentry initialization and its package dependency are removed;
- the immutable build output is copied inside the macOS app and served by the
  bundled Node runtime on `127.0.0.1:18080`;
- the static server allows only GET/HEAD, validates the Host header, prevents
  path traversal, sends no-store/no-referrer/nosniff headers, and listens only
  on loopback; and
- the native shell is always launched with its `--webui-url` pointed at that
  local server, eliminating the mutable `web.stremio.com` code dependency.

This does not make every network request anonymous. Metadata, account sync,
chosen addons, images, subtitles, and media sources still contact their
configured upstreams. The local companion reduces that surface by consolidating
TMDB, Trakt, Premiumize cloud, and approved compatibility connectors, while
keeping credentials out of addon URLs and browser storage.

The source tree and lockfile are retained for reproducibility. The production
build completed successfully under Node 26.11.1 and pnpm 11.25.0.
