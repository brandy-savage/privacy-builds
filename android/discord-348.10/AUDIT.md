# Discord 348.10 static privacy audit

## Artifact identity

- Package/version: `com.discord` `348.10 - Stable` (`348010`).
- Baseline base-APK SHA-256: `f55d93282953cb8cb5f0375a69e6358f5a33641a14c56d7a7b79692c064ea6e7`.
- Baseline signer SHA-256: `3c39d23cf9367849a5c699395647fe0e5bfea5a1f1f40d8c717ddc70f8bfa113`.
- The inspected install was a base plus arm64, English-language, and xxhdpi
  configuration splits.

## Findings

1. **Advertising attribution is wired.** The manifest requests Google
   Advertising ID and Android AdServices attribution. AppsFlyer code, Google
   Install Referrer code, and Discord's React Native install-referrer bridge are
   present.
2. **AppsFlyer is explicitly started by Discord code.** The inspected
   `DeepLinks.init(Context)` path configures and starts AppsFlyer for deferred
   link attribution.
3. **Touch/view analytics has an explicit switch.** The inspected
   `TouchEventAnalyticsModule.enableTouchLogging()` path enables Discord's touch
   logging machinery.
4. **Crash reporting spans Java and native code.** Sentry startup providers,
   Discord's crash-reporting wrapper, and the native libdiscore Sentry reporter
   are all wired in this version.
5. **Other telemetry SDK code remains bundled.** Broad string/class searches
   also found Braze- and Facebook/React-related code. Library presence alone is
   not proof that every SDK or path runs for every account.

## Patch behavior

- Removes `com.google.android.gms.permission.AD_ID` and
  `android.permission.ACCESS_ADSERVICES_ATTRIBUTION`.
- Disables Google Analytics receiver/service/job components and Sentry's two
  automatic Android startup providers.
- Forces `io.sentry.auto-init=false`.
- Makes Discord's `CrashReporting.isDisabled()` return true.
- Replaces `DeepLinks.init(Context)` with a no-op, preventing the inspected
  AppsFlyer initialization and deferred-link attribution path.
- Makes `enableTouchLogging()` a no-op.
- Makes the install-referrer bridge resolve with no payload.
- Makes native Sentry-reporter installation a no-op.

## Verification and limitations

- The rebuilt split set passed ZIP alignment and APK signature verification.
- It was installed on Android 17 and reached Discord's welcome/login UI without
  a fatal process crash.
- This is a narrow binary patch, not proof that all Discord telemetry is gone.
  SDK classes and native libraries remain bundled, and uninspected or
  server-driven paths may still transmit diagnostics or usage data.
- Disabling attribution or crash reporting may change deep links, campaigns,
  experiments, support diagnostics, or notification behavior.
- Re-signing breaks official in-place updates and may affect OAuth, integrity,
  or signature checks. Installing over an official build generally requires an
  uninstall, which can erase local app data.
