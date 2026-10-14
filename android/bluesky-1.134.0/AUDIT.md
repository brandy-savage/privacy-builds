# Bluesky 1.134.0 static privacy audit

## Artifact identity

- Package/version: `xyz.blueskyweb.app` `1.134.0` (`1608`).
- Baseline base-APK SHA-256: `497ddb5dd2a9786f99609c1cb65e5f100bec051bf5ea2394cd3e619ac95ac334`.
- Baseline signer SHA-256: `c14d3c6bb5d6d9aecfc50bbcc19b296dd4e6874636d54c1a641c1408bf7ef962`.
- The inspected install was a base plus arm64 and xxhdpi configuration splits.

## Findings

1. **Sentry is wired across Android, native, and React Native layers.** The
   manifest declares automatic Sentry startup/performance/NDK providers, and
   the React Native bridge contains an explicit native-SDK initialization path.
2. **The build includes Sentry metadata and replay/profiling-related library
   code.** Bundled code is not proof that every capability is enabled in every
   session.
3. **No Advertising ID manifest permission was present.** Search hits for
   “amplitude” were inspected and were waveform/UI amplitude references, not
   evidence of the Amplitude analytics SDK. This audit does not label them as
   analytics.
4. **Expo/Firebase messaging is used for notifications.** It was deliberately
   kept to avoid disabling ordinary push delivery.

## Patch behavior

- Disables the automatic Sentry init, performance, and NDK preload providers.
- Forces `io.sentry.auto-init=false` where that metadata exists.
- Replaces the React Native `initNativeSdk` bridge with a resolved `false`
  result, preventing the inspected Java/React initialization call.
- Preserves Firebase/Expo notification services.
- Normalizes one Android 17 `configChanges` bitmask to equivalent symbolic
  names and removes two optional `@null` notification-icon metadata resources
  solely to survive apktool/aapt2 round-tripping.
- Restores the original resource IDs and xxhdpi payloads for two split-only
  AppCompat text-field drawables that apktool otherwise decodes as `@null`.

## Verification and limitations

- The rebuilt split set passed ZIP alignment and APK signature verification.
- An initial Android 17 smoke test reached Bluesky's landing screen but exposed
  an apktool split-resource loss when the credential form created a native text
  input. The final patch restores the two original text-field assets and their
  resource IDs; the corrected build was retested through the credential form.
- The Hermes JavaScript bundle was not rewritten. Sentry classes and native
  libraries remain bundled, so uninspected direct/native paths could remain.
- The manifest and text-field resource normalizations are build-tool
  compatibility changes, not privacy features.
- Re-signing breaks official in-place updates and may affect OAuth, integrity,
  or signature checks. Installing over an official build generally requires an
  uninstall, which can erase local app data.
