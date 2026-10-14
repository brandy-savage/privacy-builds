# Gmail 2026.10.05.993506826 static privacy audit

## Artifact identity

- Source: APKMirror universal nodpi standalone APK, Android 7.0+.
- Package/version: `com.google.android.gm` `2026.10.05.993506826.Release` (`66088771`).
- Source SHA-256: `2366e138411517cc42949273b26151b72e75f25400d50e90ae2e96f6780435e9`.
- Source signing: APK v2/v3/v3.1 and Google Source Stamp verified.
- Google rotated signer SHA-256 (API 33+): `7ce83c1b71f3d572fed04c8d40c5cb10ff75e6d87d9df6fbd53f0468c2905053`.
- Legacy Google signer SHA-256: `f0fd6c5b410f25cb25c3b53346c8972fae30f8ee7411df910480ad6b2d60db83`.
- Source page: <https://www.apkmirror.com/apk/google-inc/gmail/gmail-2026-10-05-993506826-release-release/gmail-2026-10-05-993506826-release-2-android-apk-download/>

## Findings

1. **Ad identity is declared in a mail client.** The manifest requests `com.google.android.gms.permission.AD_ID`, `ACCESS_ADSERVICES_AD_ID`, and `ACCESS_ADSERVICES_ATTRIBUTION`. The APK also contains Google advertising-ID client code.
2. **Google logging/config infrastructure is embedded.** Clearcut parcelables/client metadata, Performance Primes metadata, client-tracing metadata, survey libraries, and many Phenotype registration blobs are present. The manifest wires Phenotype registration/update components. This establishes code and configuration reachability, not the contents of every uploaded event.
3. **Gmail includes substantial Chat and Meet implementations.** The APK includes Dynamite chat services/UI, conference activities and services, WebRTC/video-chat native libraries, call UI, effects pipelines, and Gemini-related Meet settings. These are not merely external-app links.
4. **AI-assisted composition is present.** Smart Compose assets and AI/GenAI classes are bundled. Static analysis alone cannot establish which account, region, or server-side flag enables each path or whether a given inference runs locally or remotely.
5. **The optional data surface is broad.** Declarations include contacts/profile, calendar, camera, microphone, phone/call state, media, Bluetooth, accounts, boot, wake locks, and package visibility. Several are attributable to bundled Chat/Meet and enterprise mail features.
6. **Cleartext transport is allowed by the application manifest.** `usesCleartextTraffic=true` is declared alongside a network-security configuration. That declaration is capability, not proof that Gmail sends message content over cleartext.

## Patch behavior

- Replaces all three ad-identity permission strings with inert app-local names of identical binary length.
- Hooks the AndroidX startup provider and installs a policy before ordinary app UI startup.
- Enumerates manifest activities/services/receivers/providers and toggles matching optional subsystems through Android's component state API. Turning a switch off restores each component to its manifest default.
- Defaults diagnostics/surveys, componentized AI, Chat/Meet, and trusted/hybrid web bridges to blocked.
- Preserves mail/account/sync/push components by design. Extreme mode expands blocking to optional camera, voice, call, contact/calendar, and people components.
- Exposes the controls through a dynamic launcher shortcut and a repurposed, originally-disabled local activity.

## Verification and limitations

- REA 6.3.0 with pinned `jadx-headless-mcp` 0.7.1 loaded 68,237 classes (72,094 raw classes), 370,829 methods, and 18,173,316 instructions. REA's final process-table cleanup confirmation was denied by the sandbox (`EPERM`), so focused evidence continued with the same JADX backend plus apktool/smali.
- Final APK: zip alignment passed; APK v2/v3 signatures verify; ZIP integrity passed; package/version and removal of all three ad-identity permissions were re-read after signing; all three changed DEX files pass `dexdump` header/checksum parsing.
- Every untouched ZIP payload entry CRC-matches the pristine APK. Surgical archive replacement was used to avoid case-colliding resource loss on macOS.
- No Android runtime smoke test was available because the sandbox could not start ADB's local smart-socket listener.
- Component blocking cannot stop in-process code that has no separate Android component. Native, reflective, remotely delivered, or tightly coupled logging paths may remain.
- Disabling Chat/Meet, AI, or web bridges can produce dead UI affordances or account-specific errors. Extreme mode deliberately sacrifices recipient suggestions, calendar integration, voice/video, and related features.
- Re-signing breaks official updates and may break Google authentication or signature-protected integration even when installation succeeds.
