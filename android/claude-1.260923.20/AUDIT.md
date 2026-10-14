# Claude 1.260923.20 static privacy audit

## Artifact identity

- Package/version: `com.anthropic.claude` `1.260923.20` (`26092320`).
- Baseline base-APK SHA-256: `6ad972d250cb73125d324f651b7541f62dd960cce38d3545136116d9b40a98bb`.
- Baseline signer SHA-256: `305a1e8a432e5ec0c612b2465359c3b88e3c95d6253599ac6088562b818b64a0`.
- The inspected install was a base plus arm64 and xxhdpi configuration splits.

## Findings

1. **Sentry has automatic and explicit initialization paths.** The manifest
   declares Sentry init and performance providers, while application code
   explicitly configures a Sentry Android client.
2. **Datadog startup providers are declared.** Profiling and RUM content
   providers can initialize before ordinary application components.
3. **Segment event queuing is implemented in application bytecode.** The
   inspected queue path accepts events and starts a background worker.
4. **Attribution-related and telemetry SDK code remains bundled.** Static
   searches found install-referrer and advertising-identity code as well as
   Sentry, Datadog, and Segment classes. Library presence alone does not prove
   that every capability runs for every account or session.
5. **The manifest exposes health, location, calendar, and microphone
   capabilities.** Those declarations support application features and are not
   by themselves evidence of telemetry, so this patch does not remove them.

## Patch behavior

- Disables Sentry's automatic init and performance providers and forces
  `io.sentry.auto-init=false`.
- Disables Datadog's profiling and RUM startup providers.
- Disables the explicitly configured Sentry client.
- Discards events at the inspected Segment queue boundary and prevents its
  queue worker from starting.
- Retains feature permissions and application services not shown to be
  telemetry-specific.

## Verification and limitations

- The locally prepared split set passed ZIP alignment and APK signature
  verification. The public patch script was also applied to a fresh decode of
  the baseline base APK and rebuilt successfully.
- The modified build was not installed because the same official package was
  present in more than one Android user profile. Android enforces one package
  signature device-wide, so testing the re-signed build would require removing
  the official package from every profile where it is installed and could erase
  local app data.
- This is a narrow binary patch, not proof that all Claude telemetry is gone.
  SDK classes and native libraries remain bundled, and uninspected direct,
  native, or server-driven paths may remain.
- Returning no Segment event can affect code that expected the original event
  object. Disabling diagnostics can also reduce support information.
- Re-signing breaks official in-place updates and may affect OAuth, integrity,
  or signature checks.
