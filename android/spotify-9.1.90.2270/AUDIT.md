# Spotify 9.1.90.2270 static privacy audit

## Artifact identity

- Source: APKMirror universal nodpi standalone APK, Android 7.0+.
- Package/version: `com.spotify.music` `9.1.90.2270` (`147078674`).
- Source SHA-256: `5c05366de31788fd0eec6e046c3610311acf5e63c15345e5bdaca6e8f09fb3b4`.
- Source signing: APK v2/v3 and Google Source Stamp verified.
- Spotify signer SHA-256: `6505b181933344f93893d586e399b94616183f04349cb572a9e81a3335e28ffd`.
- Source page: <https://www.apkmirror.com/apk/spotify-ab/spotify-music-podcasts/spotify-music-and-podcasts-9-1-90-2270-release/spotify-music-and-podcasts-9-1-90-2270-2-android-apk-download/>

## Findings

1. **Comscore audience measurement is explicitly wired.** Spotify's `p/e9g` handler builds a Comscore publisher configuration with publisher ID `15654041`, enables automatic usage-property updates, starts `com.comscore.Analytics` with the application context, and forwards foreground/background plus UX-active/UX-inactive lifecycle events.
2. **No Nielsen implementation was found in this artifact.** A bounded class/reference search found Comscore, not Nielsen. Store-description language about Nielsen is not treated as code evidence for this version.
3. **Ad identity is declared and implemented.** The manifest requests Google Advertising ID plus Android AdServices ID/attribution, and Google `AdvertisingIdClient` code is present.
4. **A separate fraud/device-ID surface is exported.** The manifest declares exported `com.ravelin.core.repository.services.DeviceIdService` with Ravelin's device action. Disabling it may break checkout or fraud checks.
5. **Diagnostics and session transport are bundled.** Firebase Sessions, Crashlytics registrars, Analytics connector metadata, Google DataTransport backends/jobs, and Spotify performance/traffic metrics code are present. Presence does not establish the payload of every event.
6. **The nearby/device surface is broad.** Permissions include location, Bluetooth scan/connect/advertise, nearby Wi-Fi, local-network access, phone state, camera, mic, NFC and media. Enabled components include Bluetooth connection-state monitoring, while Spotify Connect, Cast, media-route, car, Alexa/inter-app, and external-device code is extensively bundled.
7. **OS engagement and cross-device publishing are wired.** Exported Google Engage continuation/recommendation receivers and Microsoft/Samsung integration metadata/components are declared.

## Patch behavior

- Replaces all three ad-identity permission strings with inert app-local names of identical binary length.
- Hooks the AndroidX startup provider so policy is applied before ordinary app UI startup.
- Adds a hard branch before Spotify's Comscore publisher configuration and `Analytics.start` call; it returns without initialization when measurement blocking is enabled.
- Enumerates manifest activities/services/receivers/providers and toggles optional component groups through Android's component state API. Turning a switch off restores manifest defaults.
- Defaults measurement, Ravelin/device-ID, scanner/voice/camera, and OS/cross-device recommendation components to blocked.
- Leaves local-device discovery enabled in normal mode to preserve Spotify Connect. Extreme mode blocks it and related Bluetooth/Cast/car/external-control components.
- Exposes controls through a dynamic launcher shortcut and a repurposed, originally-disabled local activity.

## Verification and limitations

- REA 6.3.0 with pinned `jadx-headless-mcp` 0.7.1 loaded 98,076 classes (102,471 raw classes), 492,753 methods, and 21,276,161 instructions. REA's final process-table cleanup confirmation was denied by the sandbox (`EPERM`); focused evidence continued with the same JADX backend plus apktool/smali.
- Final APK: zip alignment passed; APK v2/v3 signatures verify; ZIP integrity passed; package/version and removal of all three ad-identity permissions were re-read after signing; both changed DEX files pass `dexdump` header/checksum parsing.
- Every untouched ZIP payload entry CRC-matches the pristine APK. Only the binary manifest, base DEX, new privacy DEX, source stamp, and local signing metadata differ.
- No Android runtime smoke test was available because the sandbox could not start ADB's local smart-socket listener.
- The hard gate prevents configured Comscore startup but does not delete the SDK. Later no-op lifecycle calls and native/reflective paths remain possible.
- Component blocking cannot stop in-process code without a separate Android component. Native code, server-driven paths, DRM, ads, playback telemetry, or tightly coupled logging may remain.
- Blocking Ravelin can break purchases. Blocking scanner/voice affects Spotify Codes and voice features. Extreme mode intentionally breaks Spotify Connect, Bluetooth/Cast discovery, cars, and external control.
- Re-signing breaks official updates and may trigger signature, integrity, DRM, OAuth, or account checks.
