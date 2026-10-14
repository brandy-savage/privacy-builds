# Stremio Android APK audit and privacy-edition rebuild plan

## Scope and confidence

This is a read-only static audit of the local Play split APK set at:

`/path/to/device-backup/apks/com.stremio.one/`

No original APK was modified. Static analysis proves that code and configuration are present and how they are wired; it does not prove every optional path executed on this user's device. Findings are therefore labeled as **directly wired**, **reachable SDK behavior**, or **present only** where that distinction matters.

The package is `com.stremio.one`, version `2.4.0` (`versionCode 10242880`), min SDK 32, target SDK 36, compile SDK 37. The base APK is signed with APK Signature Scheme v3 by `CN=Ivo Georgiev, OU=Engineering, O=Stremio, ...`, certificate SHA-256 `7e6a979c968f771e3fbcf2c2e8718ce61e708d87caf91fc13e2d4c19a8022c6b`, and has a verified Google Play source stamp. These facts strongly support that this is a Play-delivered Stremio build rather than an unknown repack.

SHA-256 hashes:

| APK | SHA-256 |
|---|---|
| `base.apk` | `1506a4bb4e03ad0adc79c928ec3f56b3795573491b5f4ff7e77eb67d38f05af1` |
| `split_config.arm64_v8a.apk` | `81a458c9ecba87d2832b7d1b9eba782a0cc0fbaf19a2e99701e0d67237f67f9f` |
| `split_config.en.apk` | `1e233628e28f34e2e4abd2fe82cbd8757b77d4de40988e8d27b4b392facf420c` |
| `split_config.xxhdpi.apk` | `c6a4404b1871e4e02b3dba222c22afb3a5a413edef6890ee4c5ee833d2b11a73` |

## Executive findings

1. **Critical: a trust-all HTTPS client is directly wired into image fetching.** `UnsafeOkHttp3Client.Companion.build()` installs a no-op `X509TrustManager` and a hostname verifier that always returns true. Koin supplies this client to Coil's `OkHttpNetworkFetcher`. A network attacker can substitute poster/artwork responses, and any sensitive image URL or headers sent through this path lose TLS authenticity.

2. **High: the embedded streaming server appears LAN-exposed by default.** Bundled `server.js` invokes `server.listen(port)` for HTTP ports 11470 through 11474 and `(https.createServer(app)).listen(12470)` without a host argument. Node's unspecified host binds to the unspecified address rather than loopback. Only the `/\<SERVER_IPC_KEY\>/downloader` route was found behind the generated IPC-key path; torrent, archive, HLS, subtitle, and other routes are mounted outside it. Multiple responses use `Access-Control-Allow-Origin: *`. On an untrusted LAN, this expands the attack surface substantially.

3. **High privacy impact: two analytics systems plus crash/session identity are included.** The app directly starts a native Stremio analytics publisher every 30 seconds after core initialization. The Android package also auto-initializes Firebase Analytics, Crashlytics, Sessions, Installations, and DataTransport. Crashlytics collection is switched off in `MainActivity.onCreate`, then conditionally changed later from the profile setting, but the provider/components initialize earlier in process startup.

4. **High privacy impact: advertising and Privacy Sandbox access is declared.** The manifest requests Advertising ID, Install Referrer binding, AdServices Attribution, Ad ID, Custom Audience, and Topics permissions. `res/xml/ad_services_config.xml` sets attribution, custom audiences, and topics to `allowAllToAccess="true"`. Google Measurement includes reachable Advertising ID calls and advertising/conversion endpoints. There was no first-party `com.stremio.*` call to `AdvertisingIdClient` found; the path is supplied through linked Google/Facebook SDKs, so this is a **reachable SDK behavior**, not proof of an ad-ID read in this static run.

5. **Medium/high privacy impact: Facebook SDK auto-initialization is enabled.** `FacebookInitProvider` is manifest-registered and calls `FacebookSdk.sdkInitialize`. The package has Facebook Login UI/components, an app ID/client token, a query for `com.facebook.katana`, and the Facebook App Events implementation, including advertiser-ID collection paths. Keeping Facebook login means retaining a large opaque SDK with independent network behavior.

6. **Medium: global cleartext networking is allowed.** The application sets `android:usesCleartextTraffic="true"` and has no scoped network-security configuration. This is broader than required to reach the loopback streaming server and permits any addon/resource URL to downgrade to HTTP.

7. **Positive: the client is native Compose, not a WebView shell.** No `android.webkit.WebView`, `addJavascriptInterface`, `DexClassLoader`, `PathClassLoader`, or `InMemoryDexClassLoader` reference was found in `com.stremio.*`. Dynamic execution is the bundled, immutable `assets/server.js` evaluated by an embedded Node runtime (`node -e`); no code-download loader was found.

8. **Positive: dangerous Android permissions are limited.** There is no location, contacts, microphone, camera, storage, accessibility, package-usage, or broad package-query permission. The core functional permissions are Internet, notifications, foreground media playback, network state, and wake lock.

## Manifest inventory

### Permissions

Functional:

- `android.permission.INTERNET`
- `android.permission.POST_NOTIFICATIONS`
- `android.permission.FOREGROUND_SERVICE`
- `android.permission.FOREGROUND_SERVICE_MEDIA_PLAYBACK`
- `android.permission.ACCESS_NETWORK_STATE`
- `android.permission.WAKE_LOCK`
- app signature permission `com.stremio.one.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION`

Privacy-related / removable:

- `com.google.android.finsky.permission.BIND_GET_INSTALL_REFERRER_SERVICE`
- `com.google.android.gms.permission.AD_ID`
- `android.permission.ACCESS_ADSERVICES_ATTRIBUTION`
- `android.permission.ACCESS_ADSERVICES_AD_ID`
- `android.permission.ACCESS_ADSERVICES_CUSTOM_AUDIENCE`
- `android.permission.ACCESS_ADSERVICES_TOPICS`

Package visibility currently declares only `com.facebook.katana`.

### App components

- `com.stremio.android.MainActivity`: exported launcher; also accepts `magnet:`, `stremio:`, and `content:` BitTorrent intents.
- `com.stremio.android.ServerService`: non-exported, separate `:stremio_server_process`, foreground media-playback service.
- `com.stremio.common.players.MediaPlaybackService`: exported but protected by `android.permission.BIND_MEDIA_BROWSER_SERVICE`.
- `androidx.media.session.MediaButtonReceiver`: exported for media-button delivery.
- Facebook login activities plus `FacebookInitProvider` and token-change receivers.
- Firebase `FirebaseInitProvider`, component-discovery service, Sessions service, Measurement receiver/services, DataTransport job/alarm components.
- AndroidX profile installer receiver, protected by `android.permission.DUMP`.

No exported arbitrary file provider or unprotected exported app service was found.

## Direct evidence

### Trust-all TLS

Files:

- `smali_classes7/com/stremio/common/platform/UnsafeOkHttp3Client$Companion.smali`
- `smali_classes7/com/stremio/common/platform/UnsafeOkHttp3Client$Companion$ignoreAllSSLErrors$naiveTrustManager$1.smali`
- `smali_classes6/com/stremio/common/platform/KoinKt.smali`

Behavior:

- `checkClientTrusted` and `checkServerTrusted` immediately return.
- `hostnameVerifier` is a lambda that returns true unconditionally.
- `build()` always calls `ignoreAllSSLErrors`.
- `KoinKt.platformModule$lambda$0$2$0()` supplies that client to the image network fetcher.

This is not a dormant utility; it is directly wired.

### Stremio analytics loop

Files:

- `smali_classes6/com/stremio/common/api/StremioApi$loadCore$1.smali`
- `smali_classes6/com/stremio/common/api/StremioApi.smali`
- `smali_classes6/com/stremio/common/api/StremioApi$startAnalyticsPublishing$1.smali`
- `lib/arm64-v8a/libstremio_core_kotlin.so`

After `Core.initialize`, `loadCore` calls `startAnalyticsPublishing()`. Its coroutine waits `0x7530` ms (30 seconds), calls native `Core.sendNextAnalyticsBatch()`, and repeats forever. Native symbols include `emit_to_analytics`, `flush_analytics`, `analytics_context`, and `send_next_analytics_batch`. The exact native event payload and server-side retention require runtime/network observation or source review; the continuous publisher itself is confirmed.

### Firebase and Facebook

The manifest registers:

- Firebase Analytics connector, Crashlytics + NDK, Sessions, Installations, DataTransport.
- Google Measurement receiver and services.
- Firebase init provider with `initOrder=100`.
- Facebook init provider, activities, token receivers, and app metadata.

First-party references include Crashlytics user ID assignment and playback-error context recording. Known reachable SDK endpoints/hosts present in code include `app-measurement.com`, `firebaseinstallations.googleapis.com`, `firebase-settings.crashlytics.com`, Google ad/conversion hosts, and Facebook Graph endpoints. Endpoint presence alone is not proof of each request.

### Embedded server exposure

Files:

- `assets/server.js`
- `smali_classes6/com/stremio/common/platform/StremioServer.smali`
- `smali_classes6/com/stremio/android/ServerService.smali`

`StremioServer` loads `libnode`, `libstremio-server`, and `libc++_shared`, reads `server.js` from the signed APK asset, and executes it with `node -e`. `ServerService` passes `SERVER_IPC_KEY` when available. In the JS bundle, that key gates only the downloader mount found in this audit. The main HTTP/HTTPS servers do not specify `127.0.0.1` as the listen host.

The server contains torrent/WebTorrent, archive (RAR/ZIP/7z/tar/tgz/NZB), HLS/transcoding, subtitle, casting/DLNA, and addon HTTP functionality. This explains its size and native dependencies but also makes unauthenticated LAN binding materially risky.

### Native libraries

The arm64 split contains:

- Stremio/Node: `libstremio_core_kotlin.so`, `libstremio-server.so`, `libnode.so`
- Players/media: `libmpv.so`, `libvlc.so`, `libvlcjni.so`, FFmpeg `libav*`, `libsw*`, `libmedia3ext.so`, `libmediainfo.so`, `libass.so`, `libasskt.so`, `libgav1JNI.so`, `libplayer.so`
- Firebase NDK crash collection: `libcrashlytics.so`, `libcrashlytics-handler.so`, `libcrashlytics-common.so`, `libcrashlytics-trampoline.so`
- support: `libc++_shared.so`, `libdatastore_shared_counter.so`, `libandroidx.graphics.path.so`

The Firebase crash native libraries can be deleted in a clean source rebuild after Crashlytics NDK is removed; deleting them from a binary patch without removing registrars/references is unsafe.

## Privacy edition: recommended source rebuild

A source rebuild is safer than a broad smali deletion because the APK spans eight DEX files, Rust/JNI core code, embedded Node, and split native libraries. Binary patching should be a short-lived validation build only.

### 1. Remove third-party telemetry at dependency level

- Remove Firebase Analytics, Measurement, Sessions, Installations, DataTransport, Crashlytics, and Crashlytics NDK dependencies/plugins.
- Remove the Facebook Android SDK and Facebook login UI. Retain email/password, token, or local-profile login. If Facebook login is non-negotiable, put it in a separate opt-in build flavor whose default disables `AutoLogAppEvents`, advertiser-ID collection, and automatic init.
- Remove Install Referrer, Google Advertising ID, and AndroidX Privacy Sandbox Ads dependencies.
- Verify the merged release manifest has no Firebase/Facebook providers, Google Measurement components, ad permissions, or `ad_services_config`.
- Remove first-party calls to `FirebaseCrashlytics.setUserId`, `recordException`, and collection toggles. Replace them with local rotating logs, redacted by default and exported only by explicit user action.

### 2. Disable native Stremio analytics, not only its UI switch

- Delete the unconditional `startAnalyticsPublishing()` call after core initialization.
- Build the Rust/Kotlin core with analytics emission compiled out, or provide a `NoopAnalyticsSink` whose `emit`, `flush`, and `sendNextAnalyticsBatch` never persist or transmit.
- Keep diagnostics local. Never include account IDs, addon URLs containing credentials, full media URLs, info hashes, filenames, IPs, or device IDs in logs.
- Make privacy mode the non-bypassable default for this personal build; an optional diagnostics overlay can show counters locally without networking.

### 3. Restore TLS authenticity

- Replace `UnsafeOkHttp3Client.build()` with a normal `OkHttpClient.Builder().build()` so Android's platform trust manager and hostname verification apply.
- Do not add a permissive certificate bypass toggle. For a local companion, support either a publicly trusted HTTPS certificate or a user-selected pinned certificate/public-key fingerprint.
- If certificate pinning is implemented, pin only the local companion profile and expose certificate rotation/re-pairing explicitly; do not pin public addon ecosystems globally.

### 4. Scope cleartext to loopback

Set `android:usesCleartextTraffic="false"` and add a network-security config that permits cleartext only for exact loopback names needed by the embedded server (`127.0.0.1` and `localhost`). Confirm the IP literal works on every supported Android version with an instrumentation test. If it does not, route the app through `localhost` consistently.

Do not permit blanket RFC1918 cleartext. A LAN companion should use HTTPS. If an HTTP-only developer mode is indispensable, ship it as a separate debug flavor with a conspicuous status indicator and no release signing key.

### 5. Bind and authenticate the embedded server

- Change both HTTP and HTTPS listeners to bind explicitly to `127.0.0.1` by default: `server.listen(port, "127.0.0.1")`.
- Disable network interface enumeration, SSDP/DLNA, casting, and remote control by default. Expose them only through an “Allow LAN playback” toggle.
- Put **all** routes, not just `/downloader`, behind an unguessable per-install bearer capability or a private Unix/local socket bridge.
- Reject requests lacking an exact allowed `Origin`/`Host`; remove wildcard CORS on control and file-management endpoints.
- Rotate the capability on reinstall/logout and never write it to logs or URLs visible to third-party addons.
- Add request body limits, strict path normalization, URL allow/deny rules against SSRF to link-local/cloud metadata addresses, and bounded timeouts/concurrency for torrent/archive/transcode operations.

### 6. Minimal manifest

Keep Internet, network state, wake lock, and foreground-media permissions. Keep notifications only because Android foreground services need user-visible notification behavior. Remove all ad, AdServices, and Install Referrer permissions.

Keep `ServerService` non-exported. `MediaPlaybackService` can remain exported with `BIND_MEDIA_BROWSER_SERVICE`; validate every incoming media ID. Validate all `magnet:`, `stremio:`, and `content:` deep links before dispatch, reject oversized inputs, and never treat query text as an addon install without confirmation.

### 7. Local companion configuration without embedded secrets

The APK should ship with blank configuration and no Premiumize or Trakt key. Recommended flow:

1. The machine-local companion stores the real Premiumize/Trakt credentials in the host OS keychain or a mode-0600 secret file.
2. Android stores only a revocable companion pairing token in Android Keystore-backed storage.
3. The user enters/scans a companion base URL and verifies the displayed TLS fingerprint or a short pairing code.
4. The companion exposes a Stremio addon-compatible `manifest.json`, catalogs, metadata, subtitles, and stream results. It performs Premiumize/Trakt calls server-side and never returns either upstream secret.
5. The app validates URL scheme/host, refuses credentials in URL query strings, redacts the base URL path in diagnostics, and offers a clear “Forget companion” action.

This remains understandable authentication: base URL + one pairing code/token, with no hidden vendor account or opaque relay.

## External player fallback chain

### Current behavior

`smali_classes6/com/stremio/common/players/ExternalPlayerContract.smali` `createIntent()` creates a generic `android.intent.action.VIEW`, adds:

- `return_result=true`
- `startfrom=<position>`
- `position=<position>`
- data URI with MIME `video/*`

It does not prefer a package. Its result parser already understands:

- VLC: `org.videolan.vlc.player.result`
- MX Player: `com.mxtech.intent.result.VIEW`
- MPV: `is.xyz.mpv.MPVActivity.result`
- Vimu: `net.gtvbox.videoplayer.result`

The launch call is in `smali_classes6/com/stremio/android/ui/screens/player/PlayerScreenKt.smali`, method `PlayerScreen$lambda$38$0$0`, immediately after constructing `ExternalPlayerInput`. It catches general exceptions and currently only shows a toast.

### Requested order

Add package visibility declarations for:

```xml
<queries>
    <package android:name="org.videolan.vlc" />
    <package android:name="com.mxtech.videoplayer.pro" />
    <package android:name="com.mxtech.videoplayer.ad" />
    <intent>
        <action android:name="android.intent.action.VIEW" />
        <data android:mimeType="video/*" />
    </intent>
</queries>
```

Implement a resolver in source, not a one-off chooser hack:

1. Build the same base intent/extras as today.
2. Try explicit package `org.videolan.vlc` if resolvable.
3. Try MX Player Pro `com.mxtech.videoplayer.pro`, then Free `com.mxtech.videoplayer.ad`.
4. Try the unscoped generic `ACTION_VIEW` so the Android default/chooser gets a chance.
5. If no handler resolves, or launch throws `ActivityNotFoundException`/`SecurityException`, switch the view model to the internal player and continue at the same position. Do not merely toast.

Resolve the final intent immediately before launch, because installed packages may change while the app is paused. Preserve returned position/duration and completion handling already in `ExternalPlayerContract`.

## Validation gates for the rebuilt APK

- `apkanalyzer`/`aapt dump badging`: no AD_ID, AdServices, Install Referrer permissions.
- Merged manifest: no Firebase/Facebook/Measurement providers, services, or receivers; no global cleartext.
- DEX/native scan: no `com.google.firebase`, `com.google.android.gms.measurement`, `com.facebook`, `AdvertisingIdClient`, or Crashlytics native libraries.
- Unit test: analytics sink records zero outbound requests and the 30-second publisher coroutine is absent.
- TLS test: MITM/self-signed artwork certificate fails closed.
- Socket test: `ss`/`netstat` shows 11470–11474 and 12470 on loopback only unless the explicit LAN toggle is on.
- Route tests: unauthenticated requests to every server route return 401/403; malicious `Origin`, `Host`, traversal, and SSRF targets are rejected.
- External-player tests: VLC → MX Pro → MX Free → system/default → internal, with resume position preserved.
- Clean-install test: configuration is blank, no secret exists in APK resources/Dex/native strings, and companion pairing is explicit.
- Reproducible release build, private signing key, SBOM/dependency lock, and update documentation. A privacy build must use a different application ID or uninstall the official app first because it cannot be signed with Stremio's key.

## Binary privacy build produced

A working APK-level patch was applied in `work/stremio-private/android/build/privacy-base`, then rebuilt with apktool, zip-aligned, and signed as one consistent split set in `work/stremio-private/android/dist`. Originals remain byte-for-byte untouched.

Implemented in the binary build:

- removed Install Referrer, AD_ID, and all declared AdServices permissions, plus the optional AdServices shared-library entry;
- disabled Firebase and Facebook init providers, Firebase component discovery, Facebook login/token components, Firebase Sessions, Google Measurement components, and DataTransport schedulers in the final binary manifest;
- deactivated Firebase/Facebook collection metadata and replaced direct Firebase Analytics and Crashlytics entry points with inert behavior;
- replaced `startAnalyticsPublishing()` with a two-instruction no-op (`.locals 0`, `return-void`), so the native 30-second batch coroutine is never started;
- replaced `UnsafeOkHttp3Client.Companion.build()` with a normal `OkHttpClient.Builder().build()` call; Koin still requests this provider, but it now receives a platform-validating client rather than the original trust-all configuration;
- set global cleartext off, added loopback-only cleartext policy, and patched every discovered `server.listen(port)` plus the port 12470 HTTPS listener to pass `127.0.0.1` explicitly;
- added executable package resolution in `ExternalPlayerContract`: VLC, MX Pro, MX Free, then package-unscoped Android `ACTION_VIEW`; this is not manifest-only—the rebuilt DEX contains `PrivacyExternalPlayerResolver` and the contract invokes it;
- left Premiumize/Trakt/companion credentials absent. The existing addon URL UI remains the runtime configuration path; a LAN companion should be exposed through trusted HTTPS.

Compiled-output verification re-decoded the final signed base APK and confirmed:

- `startAnalyticsPublishing()` contains only `return-void`;
- the OkHttp builder contains no call to `ignoreAllSSLErrors`;
- the external-player resolver and all three package IDs are present and invoked;
- the embedded JS contains loopback-bound generic, initial, retry, restart, addon HTTP, and HTTPS listener sites, with no remaining unscoped forms of those exact control/addon listener calls;
- both init providers, both Facebook token receivers, Firebase component discovery, Measurement, and DataTransport have `android:enabled="false"` in the compiled manifest;
- all four APKs pass zip alignment and APK Signature Scheme v3 verification under signer SHA-256 `706c5db01e32eff39e6d717c090a068b44619f3aa4ca3c21384367d11b53096d`.

Final APK SHA-256 values:

| APK | SHA-256 |
|---|---|
| `base.apk` | `f7bf48ee5167596a41a5da8f7283e3cb3dc7644794eb14465df4dcdc0b969a39` |
| `split_config.arm64_v8a.apk` | `febd42602a61eeab9f484eb020f08dffda6de18f71be786b6dfcc0e412bc1f3b` |
| `split_config.en.apk` | `122f238b9244bd7c268562452bea31bcf09b71277a81d885e158384883b66a30` |
| `split_config.xxhdpi.apk` | `8d8296fb549c9e256760a9a4176a582a3ab278bede5be4333361c4cb39e43ece` |

The patch deliberately disables Facebook login rather than leaving the SDK reachable. Firebase/Facebook classes and Crashlytics native libraries still occupy the split files, but their startup components are disabled; full bytecode/native removal remains a clean-source rebuild task. No Android device was connected, so launch, playback, TLS rejection, socket visibility, and the complete player fallback chain remain on-device smoke-test gates rather than claimed runtime results.

## Reproducible command notes

Tools used locally:

```sh
AAPT=/path/to/android-sdk/build-tools/37.0.0/aapt
APKTOOL=/path/to/apktool.jar
JAVA_HOME='/Applications/Burp Suite Professional.app/Contents/Resources/jre.bundle/Contents/Home'
BASE='/path/to/original/base.apk'
SPLIT='/path/to/original/split_config.arm64_v8a.apk'

"$AAPT" dump badging "$BASE"
"$JAVA_HOME/bin/java" -jar "$APKTOOL" d -f --no-src "$BASE" -o apktool-base
"$JAVA_HOME/bin/java" -jar "$APKTOOL" d -f --no-res "$BASE" -o apktool-smali
unzip -l "$SPLIT" | rg '\.so$'
shasum -a 256 /path/to/original/*.apk
```

Signing verification used Android build-tools `apksigner verify --verbose --print-certs` with the same `JAVA_HOME`. Endpoint discovery was limited to hard-coded URL/domain strings; no account store or credential value was read or printed.
