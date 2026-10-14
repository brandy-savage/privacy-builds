# ChatGPT 1.2026.279 static privacy audit

## Artifact identity

- Package/version: `com.openai.chatgpt` `1.2026.279` (`2627911`).
- Baseline base-APK SHA-256: `a30ab9145da62893cd1c2a3ccee7d05764110908ff4819de0d7e9e8aa222055e`.
- Baseline signer SHA-256: `b24f4bfbb3cf293f938703b9d87027c1102cc36dc4fa206910e08927db40473c`.
- The inspected install was a base plus arm64, English-language, and xxhdpi
  configuration splits.

## Findings

1. **Advertising ID access is declared.** The manifest requests
   `com.google.android.gms.permission.AD_ID`.
2. **Telemetry and performance startup components are declared.** The manifest
   includes a Datadog RUM provider, a Sentry NDK preload provider, and an
   internal performance application-start listener.
3. **Sentry build integration metadata is present.** The inspected manifest
   records Sentry Gradle integration data in addition to its native preload
   component.
4. **Other SDK code remains bundled.** Broad static searches found Datadog,
   Segment, Sentry, install-referrer, and advertising-identity code. Library or
   string presence alone does not prove a path runs in every session.
5. **Camera, microphone, contacts, phone, SMS, and location permissions are
   declared for product capabilities.** A permission is not evidence that its
   data is used for telemetry, so this patch does not remove those declarations.

## Patch behavior

- Removes `com.google.android.gms.permission.AD_ID`.
- Disables the Datadog RUM content provider, Sentry NDK preload provider, and
  internal performance application-start listener.
- Forces `io.sentry.auto-init=false` where that metadata exists.
- Removes Sentry Gradle integration metadata.
- Retains the application's custom Firebase initialization and unrelated
  feature services to reduce the risk of breaking sign-in, messaging, and
  ordinary product behavior.

## Verification and limitations

- The locally prepared split set passed ZIP alignment and APK signature
  verification. The public patch script was also applied to a fresh decode of
  the baseline base APK and rebuilt successfully.
- The modified build was not installed because the same official package was
  present in more than one Android user profile. Android enforces one package
  signature device-wide, so testing the re-signed build would require removing
  the official package from every profile where it is installed and could erase
  local app data.
- This is a narrow manifest patch, not proof that all ChatGPT telemetry is
  gone. SDK classes and native libraries remain bundled, and in-process,
  native, direct, or server-driven paths may remain.
- Advertising ID code remains bundled but loses the inspected permission.
- Disabling diagnostics may reduce support information or affect performance
  monitoring.
- Re-signing breaks official in-place updates and may affect OAuth, integrity,
  or signature checks.
