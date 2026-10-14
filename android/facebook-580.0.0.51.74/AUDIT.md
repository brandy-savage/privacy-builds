# DeepSeek claim review and patch notes

## Bottom line

DeepSeek found real, privacy-sensitive subsystems and was strongest on concrete code
identification. Its biggest weakness was turning capability and static wiring into
claims about scope, activation, persistence, and intent. Under an aggressive threat
model these are reasonable things to harden, but they are not all established facts.

## Claim-by-claim assessment

### GLC device fingerprinting — core finding confirmed; interpretation overstated

Confirmed in the supplied base APK:

- `com.facebook.glc.GLCService` exists with scheduled and long-running Wi-Fi monitor
  components.
- `X.Qbf.A00` SHA-1 hashes `Build.FINGERPRINT`.
- the library collector walks system/APEX library roots including `/system`,
  `/apex/com.android.art`, `/apex/com.android.i18n`, and
  `/apex/com.android.runtime`, selecting `lib`/`lib64` paths;
- library metadata/hashes are built, and selected system libraries can be gzip-compressed
  and uploaded;
- device creation/update and library-upload failure strings match DeepSeek's report.

What was too strong: this is primarily an OS-build/system-image fingerprint, not a
direct measurement of immutable hardware identity. It could help a server re-associate
the same phone after reinstall, account change, or ad-ID reset, but static code alone
does not prove server retention/matching policy or guaranteed persistence across OS
updates. Verdict: **technically strong finding, privacy conclusion plausible, persistence
claim not proven**.

### Papaya federated analytics/learning — framework confirmed; activation not proven

Confirmed:

- `FBPapayaJobService`, `PapayaEarlyInitializer`, `FBTransport`, PapayaStore, and the
  heavy-hitters, histogram, percentile, and generic analytics executor factories exist;
- the heavy-hitters native executor and federated-learning/analytics configuration
  strings are present;
- the job service and initializer provide real execution wiring, not isolated dead
  strings.

Static analysis still cannot prove which experiments/configurations were enabled for a
particular account or device, what records were selected, or how often execution
occurred. “The phone can act as a federated-computing node” is supported; “it definitely
does so continuously” is not. Verdict: **confirmed capability and scheduling path;
runtime use is configuration-dependent**.

### SmartCapture touch/selfie/document behavior — code confirmed; scope was overstated

Confirmed:

- `OnDeviceSignalsTouchListener` wraps a `Window.Callback` in `X.h2S`;
- `dispatchTouchEvent` records timestamp, action phase, coordinates, touch radius,
  tolerance, pressure, and tool type, and batches records;
- the SmartCapture package includes selfie evidence recording, liveness/challenge,
  document-authentication, and card-scanner paths;
- `CardDataLogger.logFederatedAnalyticsCardData` writes card-related fields into
  PapayaStore with a 720-hour TTL before triggering analytics execution.

Important correction: the discovered window hook belongs to configured SmartCapture
flows. It is not evidence that Facebook wraps every window and records every touch
throughout the entire app. Calling it “behavioral biometrics” is a defensible risk
description, but the downstream model/intent is not proven merely by the collected
features. Co-location of touch, selfie, liveness, and document code also does not mean
every verification flow uses all of them together. Verdict: **strong code finding,
materially narrower scope than the headline implied**.

### Other claims

- ConditionalWorker: **confirmed** as a generic conditional background-work framework.
- Activity recognition: **overstated**. Activity-transition code/receiver permission
  references exist, but the APK does not declare the `ACTIVITY_RECOGNITION`
  uses-permission. That sharply limits the claim.
- Nearby/BLE: **code exists**, but the manifest lacks modern `BLUETOOTH_SCAN`; effective
  behavior depends on OS version, permission state, and configuration.
- UsageStatsManager/clipboard: **references exist; covert collection not established**.
  There is no `PACKAGE_USAGE_STATS` declaration.
- AI/automation package visibility: **confirmed**. The manifest queried ChatGPT,
  Gemini/Bard, Copilot, Claude, Perplexity, Replika, Character AI, Poe, Pi, Replit,
  Tasker, IFTTT, Zapier, MacroDroid, Automate, Home Assistant, Notion, Airtable, and
  related tools. This build neutralizes those query targets.
- No accessibility service, no demonstrated secret ambient-mic path, and no basis for
  interpreting the `SPYWARE` classification strings as self-description: **DeepSeek's
  negative findings were correct**.

## Verification performed

- Original supplied base APK SHA-256:
  `04e53c4343399d335415e92d186a9a060e5429882de8db14fbb0975131bc3a90`.
- Original embedded base signature verified as Meta's v3/v3.1 signer before rebuilding.
- Patched smali assembled across all original dex files without errors.
- New panel/control code compiled with D8 at min API 30 and is present in
  `classes21.dex` as `com.facebook.privacy.PrivacyGate` and the repurposed activity.
- The rebuilt binary manifest parses as package `com.facebook.katana`, version
  `580.0.0.51.74`; neutralized permissions/package queries are visible in the parsed
  output.
- Base and density split are zip-aligned and verify with the same local certificate.
- No device runtime test was completed because the sandbox blocked ADB daemon socket
  creation.
