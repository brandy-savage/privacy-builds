# X 12.33.1-prod.01 static privacy audit

## Artifact identity

- Package/version: `com.twitter.android` `12.33.1-prod.01` (`312331001`).
- Baseline base-APK SHA-256: `18d8b0ce5df0554ca67716181ab3af085e5e79efdddc14b31c30da2599f67b27`.
- Baseline signer SHA-256: `0fd9a0cfb07b65950997b4eaebdc53931392391aa406538a3b04073bc2ce2fe9`.
- The inspected install was a base plus arm64, English-language, and xxhdpi
  configuration splits.

## Findings

1. **Advertising identity is broadly wired.** The manifest requests Google
   Advertising ID plus Android AdServices ID and attribution, and declares the
   optional AdServices extension library.
2. **Google measurement components are active manifest entry points.** The
   AppMeasurement receiver, service, and job service are declared along with a
   Firebase Analytics connector registrar.
3. **Firebase performance and crash libraries are componentized.** Firebase
   Performance registrars can be removed cleanly. In contrast, removing the
   Crashlytics component registrars makes this X version crash during startup,
   even when collection is meant to be disabled.
4. **Braze push/engagement UI and receivers are declared.** The inspected
   manifest exposes Braze web/content-card activities and push-delivery
   receivers.
5. **Other telemetry/diagnostic code remains bundled.** Static searches found
   Datadog, Sentry, ad-ID/referrer, and other diagnostic or attribution code.
   Broad library presence does not prove every path runs.

## Patch behavior

- Removes Google Advertising ID and Android AdServices ID/attribution
  permissions, plus the optional `android.ext.adservices` library.
- Disables Google AppMeasurement receiver/service/job components.
- Removes Firebase Analytics connector and Firebase Performance registrars.
- Keeps both Crashlytics registrars because the app requires the component at
  startup, while forcing `firebase_crashlytics_collection_enabled=false`.
- Forces `google_analytics_adid_collection_enabled=false` and
  `io.sentry.send-default-pii=false`, and removes Sentry DSN metadata.
- Disables selected Braze web/content-card/push components and X's performance
  diagnostics activity.
- Leaves Firebase Cloud Messaging infrastructure intact for ordinary push.

## Verification and limitations

- The rebuilt split set passed ZIP alignment and APK signature verification.
- An initial build without Crashlytics registrars failed at startup with a
  missing-component exception. The corrected build retained the component,
  disabled collection metadata, and reached X's login UI on Android 17 without
  a fatal process crash.
- This does not prove all telemetry is removed. The Crashlytics component and
  many SDK classes remain in-process; configuration, native code, or
  server-driven code may bypass the inspected manifest controls.
- Disabling Braze can change marketing or some notification behavior.
- Re-signing breaks official in-place updates and may affect OAuth, integrity,
  or signature checks. Installing over an official build generally requires an
  uninstall, which can erase local app data.
