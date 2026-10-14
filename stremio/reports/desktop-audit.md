# Stremio macOS desktop audit

Date: 2026-10-12
Scope: `/Applications/Stremio.app`, the bundled streaming server, and metadata-only inspection of Stremio's local support stores. User/account values were not extracted. The installed application was not modified.

## Executive summary

The macOS package is a native Rust/WebKit/mpv shell around a remote Web UI, plus a bundled Node streaming server. The most important privacy/security issues are:

1. **The streaming server listens on every interface, not only loopback.** At runtime, the Node process listened on `*:11470` and `*:12470`. The code calls `server.listen(port)` and `https.createServer(app).listen(12470)` without a host, and does not apply authentication globally.
2. **The exposed server has broad, stateful and URL-processing endpoints.** `/settings` is both GET and POST, and the POST directly extends and saves settings. Other routes accept user-supplied URLs or file-style inputs for probing, tracks, subtitles, HLS, proxying, and casting. CORS is an incomplete boundary and raw LAN clients are unaffected by it.
3. **The shell loads mutable remote code and grants it a native IPC bridge.** The default native shell URL is `https://web.stremio.com/` (the server redirect default is `https://app.strem.io/shell-v4.4/`). The binary injects a `window.webkit.messageHandlers.ipc` wrapper and a per-launch IPC token into the page. The token prevents unrelated unauthenticated messages, but the remote page itself necessarily receives the token and can invoke supported native methods.
4. **This installed copy fails code-signature verification.** `codesign --verify --deep --strict` reports `invalid signature (code or signature have been modified)` for both the bundle and main executable. It has a Team ID and a stapled notarization ticket, but strict validation currently fails. This does not prove malware; it does mean this install cannot be used as a trusted pristine baseline.
5. **Account state is stored in WebKit LocalStorage.** The store has keys including `profile`, `installation_id`, `library`, `streams`, and `streaming_server_urls`. Values were deliberately not read. `profile` is roughly 50–58 KB and `installation_id` is 44 bytes in the observed stores. No Keychain item API symbols were found in the shell binary, so credentials embedded in the profile/add-on configuration should be assumed recoverable from the local database until independently disproved.
6. **No dedicated telemetry SDK was found in the packaged native shell or Node server.** There were no attributable Sentry, Mixpanel, Amplitude, Datadog, New Relic, PostHog, or Google Analytics integrations in those two packaged components. However, the Web UI is fetched remotely and is therefore outside the static bundle. WebKit's resource-load database records `doubleclick.net` as a subresource under the localhost-hosted UI, plus many Stremio, metadata, video, and add-on domains. This proves a request relationship, not the purpose or payload; YouTube embedding is a plausible source of DoubleClick traffic.

## Package identity and architecture

| Item | Evidence |
|---|---|
| Bundle | `com.westbridge.stremio5-mac`, version `5.1.27` from `Contents/Info.plist` |
| Main shell | `/Applications/Stremio.app/Contents/MacOS/Stremio`, arm64 Mach-O, 8,339,088 bytes |
| Streaming server | `/Applications/Stremio.app/Contents/MacOS/server.js`, webpack bundle, 113,012 lines, 6,676,503 bytes |
| Node runtime | `/Applications/Stremio.app/Contents/MacOS/node`, 78,614,800 bytes |
| Media layer | Bundled `libmpv.2.dylib`, ffmpeg, ffprobe, FFmpeg codec libraries |
| Server package | `stremio-server` `4.21.0` at `server.js:35870-35871` |
| Local addon package | `stremio-local-addon` `1.10.0` at `server.js:43416-43417` |
| UI model | Native WRY/WebKit shell; default remote UI string `https://web.stremio.com/` |

SHA-256 values for reproducibility:

```text
1f005a5edc6b9c3b51fb42dea2df44d57362098e42c207e8ecb5ff46e8f89efb  Stremio
405eb494d6708406a30e716c3cfb5abae7a5e9c7a8b79446d64c3f821385930f  server.js
694e418b36bd4e525f63fb083f3984143f48b82e71010e24ed39b889aabab448  node
```

The shell exposes useful replacement hooks without binary patching:

- `--webui-url`: override the Web UI URL.
- `--server-url`: use an existing streaming server and do not start the bundled one.
- `--autoupdater-endpoint`: override the updater endpoint.
- `--server-ipc-key`: set the server communication key; otherwise one is generated.

These strings are present around file offset `0x3edfda` in the main executable.

## Finding D-01: unauthenticated LAN listeners

Severity: **high**

Runtime evidence:

```text
node PID 76858 TCP *:11470 (LISTEN)
node PID 76858 TCP *:12470 (LISTEN)
node PID 76858 UDP 192.168.12.211:<ephemeral>
node PID 76858 UDP *:5353
```

Static evidence:

- `server.js:46857-46859`: creates an HTTP server and calls `server.listen(port)` on 11470–11474 with no host argument.
- `server.js:46873-46875`: creates HTTPS and calls `.listen(12470)` with no host argument.
- `server.js:46862-46864`: advertises both `127.0.0.1` and the LAN address as server base URLs.
- `server.js:46807-46817`: unauthenticated GET and POST `/settings`; POST calls `settings.extend(req.body)` and persists it.
- `server.js:46724-46780`: routes accept remote URLs for probing, tracks, subtitles, and hashes.
- `server.js:46614-46624`: HLS path accepts `file` and `url` modes and constructs `file://` or remote media inputs.
- `server.js:46855`: mounts `/proxy`.
- `server.js:46968`: only the `/downloader` subtree is protected by `SERVER_IPC_KEY`; no equivalent global guard exists.

CORS does not make this safe:

- `server.js:46600` conditionally adds permissive CORS headers for Stremio origins and several other domains.
- `server.js:18285-18289` emits `Access-Control-Allow-Origin: *` when invoked.
- Requests from raw LAN clients do not use browser CORS. Browser “simple” requests can still be sent even when the response cannot be read, subject to the browser's private-network controls.

Impact: other devices or hostile local processes can reach media-processing, proxy, discovery, and settings surfaces. URL-processing routes expand the risk to SSRF and resource-exhaustion classes; exact exploitability was not tested because this was a read-only audit.

Recommended replacement:

- Bind all service listeners explicitly to `127.0.0.1`/`::1`.
- Require a high-entropy bearer token on every route, not only the downloader route.
- Use a strict exact-origin allowlist; do not use substring-like regular expressions.
- Remove or allowlist arbitrary URL and `file://` inputs.
- Disable HTTPS certificate provisioning and LAN casting by default; enable them only through an explicit user toggle.
- Add request-size, concurrency, media-duration, and transcode limits.

## Finding D-02: remote Web UI has native privileges

Severity: **high (supply-chain boundary)**

The shell binary contains and uses:

- `https://web.stremio.com/` as the normal UI source.
- An initialization object that calls `window.webkit.messageHandlers.ipc.postMessage(...)` (string at approximately `0x4796e3`).
- An injected `window.stremio_server_ipc_key='...'` value (approximately `0x4b454d`).
- `authenticated_ipc_message` in the Rust symbol table.
- Remote-page RPC methods including `open-external`, `play-external`, `app-error`, `app-load-error`, and `win-set-cursor`; native responses include media open/state, update availability, visibility, media keys, and Discord status.

This design intentionally trusts code served by the Web UI origin. A compromise, DNS/TLS trust failure, or unwanted server-side UI update therefore has more impact than an ordinary website compromise.

Recommended replacement:

- Serve an immutable, version-pinned UI from loopback or package it inside a new shell.
- Apply a restrictive Content Security Policy with no third-party scripts and a minimal `connect-src` allowlist.
- Retain an unguessable IPC capability, but also validate the top-frame origin and use a narrow typed RPC allowlist.
- Require explicit user interaction for external URL opens, update installation, file access, and any command that leaves the app sandbox.

## Finding D-03: installed signature does not validate

Severity: **high until provenance is re-established**

Commands and results:

```text
codesign --verify --deep --strict --verbose=4 /Applications/Stremio.app
/Applications/Stremio.app: invalid signature (code or signature have been modified)

codesign --verify --strict --verbose=6 /Applications/Stremio.app/Contents/MacOS/Stremio
.../Stremio: invalid signature (code or signature have been modified)
```

The signature metadata reports Team ID `BH62GT22G7`, hardened runtime, and a stapled notarization ticket, but `Authority=(unavailable)` and strict verification fails. The executable mtime is 2026-09-11 and ctime is 2026-10-08.

The entitlements also relax several hardened-runtime controls:

- `com.apple.security.cs.allow-dyld-environment-variables`
- `com.apple.security.cs.allow-jit`
- `com.apple.security.cs.allow-unsigned-executable-memory`
- `com.apple.security.cs.disable-executable-page-protection`
- `com.apple.security.cs.disable-library-validation`

Some of these may be needed for WebKit/mpv/JIT behavior, but together they increase the consequences of loading an untrusted library or gaining code execution.

Recommended action: obtain a fresh official installer, record its hash, verify it before first launch, and compare the bundle. Do not overwrite this copy until the current state is preserved for comparison.

## Finding D-04: broad cleartext transport allowance

Severity: **medium**

`Info.plist` enables:

- `NSAllowsArbitraryLoads = true`
- `NSAllowsArbitraryLoadsInWebContent = true`
- `NSThirdPartyExceptionAllowsInsecureHTTPLoads = true`
- HTTP exceptions for localhost and 127.0.0.1

The server bundle includes cleartext external defaults such as `http://api.opensubtitles.org/xml-rpc` (`server.js:70052`) and an older HTTP certificate endpoint default (`server.js:70881`), although the active top-level certificate default is HTTPS (`server.js:46585`).

Recommended replacement: allow HTTP only on exact loopback origins, migrate external services to HTTPS, and reject redirects from HTTPS to HTTP.

## Finding D-05: request URLs are logged in full

Severity: **medium**

- `server.js:46591`: `enginefs.loggingEnabled = true`.
- `server.js:18276`: logs the HTTP method, `url.parse(req.url).path`, and Range header.

Because `.path` includes the query string, remote media URLs, signed URLs, add-on configuration values, or tokens passed as query parameters can be copied to stdout. The running process has stdout/stderr pipes back to the native shell. No persistent server log was found in `~/Library/Application Support/stremio-server`, but non-persistence was not proven for all launch contexts.

Recommended replacement: disable request logging by default, or log only method plus a normalized route template. Redact query strings, Authorization/Cookie headers, signed URLs, info hashes, and filenames.

## Finding D-06: local identity/account state is WebKit LocalStorage

Severity: **medium**

Observed stores:

- `~/Library/WebKit/com.westbridge.stremio5-mac/.../LocalStorage/localstorage.sqlite3`
- `~/Library/WebKit/com.stremio.stremio-shell-macos/.../LocalStorage/localstorage.sqlite3`

Only the schema, key names, and byte lengths were inspected. The stores use `ItemTable(key TEXT, value BLOB)` and include:

- `installation_id` (44 bytes)
- `profile` (approximately 50–58 KB)
- `library`, `library_recent`, `notifications`, `search_history`
- `streams`, `stream_presets`, `streaming_server_urls`

The database files are ordinary user-readable files. The shell had no imported `SecItemAdd`, `SecItemCopyMatching`, `SecItemUpdate`, or `SecItemDelete` symbols, and no Keychain-related strings were found. That is strong evidence the shell itself does not move these web values into Keychain, but it is not proof about every framework or server-side value.

Recommended replacement: store Premiumize/Trakt/access credentials in macOS Keychain. The local service should inject credentials into outbound requests at call time; the UI, add-on manifest/config URLs, logs, and LocalStorage should never receive them.

## Telemetry and observed domains

No dedicated analytics/crash-upload SDK was attributable to the packaged shell or server. The only native crash artifact found was Apple's local CrashReporter metadata plist containing a date.

WebKit's resource-load statistics database records the following classes of domains under the localhost/127.0.0.1 top frame:

- Stremio infrastructure: `strem.io`, `stremio.com`, `stremio.net`.
- Metadata/media: `metahub.space`, `tmdb.org`, `thetvdb.com`, `ratingposterdb.com`, `justwatch.com`, `media-amazon.com`.
- Google/YouTube: `gstatic.com`, `ggpht.com`, `googlevideo.com`, `youtube.com`, `ytimg.com`, `googleusercontent.com`, `jnn-pa.googleapis.com`.
- Advertising-related: `doubleclick.net` was recorded as a subresource under `localhost`.
- Add-on/service-looking domains: `baby-beamup.club`, `debridio.com`, `strem.fun`, `torrentsdb.com`, `dexter21767.com`, and `johnserv531.github.io`.

This database does not record payload intent and must not be treated as proof that every domain is a tracker or currently installed add-on. It does prove that the WebKit view observed requests involving these registrable domains.

## Other network behavior

- Casting is enabled by default on desktop unless `CASTING_DISABLED` is set (`server.js:46704-46708`). Runtime UDP sockets include mDNS on port 5353.
- `/network-info` enumerates non-loopback IPv4 interfaces (`server.js:46782-46800`). `NO_NETWORK_INTERFACES=1` suppresses this response, but does not change the bind address.
- HTTPS on port 12470 obtains certificates through the configured Stremio certificate endpoint (`server.js:46823-46840`, `46868-46875`).
- Operational outbound defaults include Cinemeta/Metahub, OpenSubtitles, YouTube, GitHub's ytdl-core release API, and BitTorrent trackers.
- The native auto-updater checks Stremio updater endpoints. Its embedded macOS update script includes `rm -rf /Applications/Stremio.app` followed by replacement and relaunch. That is normal updater behavior, but it makes signature/provenance verification important.

## Practical migration / patch boundary

The lowest-risk route is not to patch the installed bundle in place. Build a local companion and launch a verified shell using its existing override flags:

```text
Stremio --webui-url=http://127.0.0.1:<ui-port> \
        --server-url=http://127.0.0.1:<engine-port>
```

The replacement engine/UI should enforce:

1. Loopback-only listeners and bearer authentication on every route.
2. Keychain-backed secrets and short-lived in-memory access tokens.
3. No third-party scripts, ads, analytics, Discord presence, mDNS, SSDP, or LAN enumeration by default.
4. Explicit toggles for casting, local-file indexing, torrent/DHT, remote-control access, and diagnostics.
5. Exact outbound host allowlists per connector, with a UI showing which connector caused each request.
6. Query/header redaction and an opt-in, bounded local diagnostic log.
7. Immutable pinned UI assets and reproducible builds.
8. A firewall-style “deny unknown destination” policy so a newly changed add-on cannot silently expand its network reach.

If the existing `server.js` is temporarily retained, the minimum code changes are: bind both servers to loopback, add global auth before every router, disable casting and certificate provisioning by default, remove full-URL logging, and gate all proxy/URL/file routes behind strict validation.

## Limitations

- This was static analysis plus read-only process/file metadata. Localhost HTTP requests from the audit sandbox were blocked, so endpoints were not dynamically exercised.
- The Web UI is remote and mutable; its current JavaScript was not captured here. Therefore telemetry claims about the complete desktop experience cannot be made solely from the app bundle.
- LocalStorage values were intentionally not decoded, copied, or printed. Add-on/account inventory must be performed through a redacted UI or a purpose-built parser that never emits secrets.
- The code-signature failure establishes loss of verifiable integrity, not who changed the files or why.
