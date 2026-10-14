# Architecture and privacy boundaries

## Request flow

```text
Stremio client
  -> loopback/LAN-capability HTTP server
  -> route parser and connector registry
  -> fresh/stale SQLite cache
  -> fixed-host connector
  -> upstream API, with credentials in Authorization headers only
```

Stremio's official protocol defines a minimal addon as `manifest.json` plus
`/{resource}/{type}/{id}.json` resource routes. Catalog, metadata, stream, and
subtitle resources are independent, and the SDK supports cache lifetimes and
stale directives. This implementation follows that wire shape without adding
the Node SDK dependency. Sources: [Stremio protocol specification](https://github.com/Stremio/stremio-addon-sdk/blob/master/docs/protocol.md),
[official resource reference](https://github.com/Stremio/stremio-addon-sdk/blob/master/docs/api/README.md),
and [cache behavior](https://github.com/Stremio/stremio-addon-sdk/blob/master/docs/api/requests/defineStreamHandler.md).

## Secrets

The runtime recognizes a small allowlist of secret names. The macOS backend
uses `/usr/bin/security` with its password prompt fed through stdin; the value
never appears in argv. The portable file backend refuses any mode other than `0600`, writes via
an atomic rename, and is documented as plaintext protected only by OS file
permissions.

The SQLite cache is also mode `0600`. It contains personal catalog metadata
(for example, watchlist titles), so it is local state, not anonymous data. WAL
sidecars receive the same mode. Stream responses and cloud download links are
never inserted into it.

Premiumize recommends a Bearer header specifically to avoid credential leakage
through server logs, browser history, referrers, and caches. The connector does
exactly that and discards file download links before catalog data enters the
disk cache. A stream link is resolved only on demand and the entire stream
response is marked non-persistent. Source: [Premiumize API authentication and folder endpoints](https://www.premiumize.me/api).

Trakt credentials also remain in the secret store and are sent as headers.
This build does not reuse the existing addon's server-side configuration UUID.
Trakt's current API project and developer portal describe creating an app and
OAuth-based access; enrollment should use a new PKCE or device-flow grant, with
refresh support added before unattended expiry handling. Source: [Trakt API project](https://github.com/trakt/trakt-api).

TMDB uses only a read-access Bearer token. Query-string API keys are not
supported, so secrets do not enter request URLs. Provider IDs and regions are
ordinary configuration and may be checked into a private config file.

## Compatibility proxy rules

`CompatibilityProxyConnector` accepts a compiled target, not a user-supplied
URL. Every target must be HTTPS, have an exact allowlisted hostname, contain no
query or fragment, and list the resources it may receive. The proxy:

- never forwards cookies, client IP headers, Stremio account state, or local
  authorization headers;
- never accepts installed config blobs or credentials in upstream paths;
- does not persist stream responses;
- uses a bounded response size and refuses redirects, preventing credentials or
  requests from being redirected to a different host.

Cinemeta and OpenSubtitles v3 are enabled as narrow defaults. YouTube and the
public-domain catalog can use the same adapter after their exact public catalog
IDs and stable, non-configured base paths are pinned in tests. Legacy
OpenSubtitles stays disabled. Credential-bearing Torrentio/Debridio paths are
not proxy targets. A future optional Torrentio compatibility module must inject
the user's credential from the local store at request time and must never put it
in the local manifest URL, logs, or persistent cache.

## TV and playlist boundary

Dead or unknown TV services are not mirrored. The intended replacement is a
local playlist adapter with these constraints:

- only local files or HTTPS origins explicitly allowlisted by the user;
- no embedded provider credentials in returned URLs;
- no channel discovery, crawling, or redistribution;
- EPG refresh uses bounded caching and the date-aware Stremio EPG format.

The installed USA TV and Debridio TV hosts were unreachable during inventory,
so this adapter is deliberately not guessed into existence.

## Remaining production work

1. Implement interactive Trakt device/PKCE enrollment and automatic refresh.
2. Add explicit, redacted migration for recognizable legacy fields only.
3. Pin compatibility manifests and response fixtures for YouTube/public-domain
   addons before enabling them.
4. Add a local, allowlisted M3U/EPG connector for user-authorized playlists.
5. Add rate limiting and TLS termination if the service ever leaves a trusted
   private network.
6. Teach the desktop and Android patches to consume the playback policy and
   execute their platform-specific fallback order.
