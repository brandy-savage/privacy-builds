# Messenger 582.0.0.61.92 static privacy audit

## Artifact identity

- Source: APKMirror standalone `arm64-v8a`, nodpi APK.
- Package: `com.facebook.orca`
- Version: `582.0.0.61.92` (`346415755`)
- Source SHA-256: `2f822a507ab042a71805058e9ef0f6d175ee7c067ad71fce21c0565ab90c9433`
- Source signature: verified APK Signature Scheme v3/v3.1 and Google Source Stamp.
- Meta certificate SHA-256 (Android 13+ signer): `911d604446084ca7f4760b775bfc160fa8702441240a7258645d7a72c4312d27`
- Legacy Facebook certificate SHA-256: `e3f9e1e0cf99d0e56a055ba65e241b3399f7cea524326b0cdd6ec1327ed0fdc1`

## Observations

1. **Papaya is wired for execution.** The manifest declares the enabled `com.facebook.papaya.fb.messenger.MessengerPapayaExecutionJobService`. Its implementation creates an executor, loads Papaya configuration, and includes the failure log `Failed to run papaya`. Messenger-specific batch, lightweight, double-logging, federated-analytics, and text-suggestion classes are present.
2. **Contact collection/upload is explicit.** `ContactsUploadServiceHandler` logs upload batch sizes and passes contact collections toward upload code. XCCU includes `DeviceContactsUpdaterAsync` and `DeviceContactsUploaderAsync`. The manifest also declares Stella contact components and `MessengerSyncAdapterService`.
3. **SmartCapture includes identity evidence flows.** The manifest declares selfie capture/onboarding/data-information activities and ID capture/review activities. `SelfieEvidence` is a parcelable record containing multiple timestamps/values and an immutable evidence list.
4. **Conditional background execution exists.** ConditionalWorker services and their receiver are declared; several services start disabled in the manifest but can be enabled/scheduled by application logic.
5. **Advertising-ID code and permission are present.** The source declares `com.google.android.gms.permission.AD_ID` and includes Google's `AdvertisingIdClient`.
6. **The source asks for broad optional access.** Relevant declarations include contacts/profile/accounts, camera, microphone, fine/coarse location, phone state/numbers/calling, media, calendar, Bluetooth, NFC, overlay, exact alarms, boot completion, wake locks, and battery-optimization exemption.

## Corrections to the earlier Facebook findings

- A bounded exact-name search found no `GLCService`, `DeviceDetails`, or Messenger equivalent of Facebook's GLC registration service. `crash_dump_sys_libs` occurs in ACRA as a crash-attachment file path. That is not enough evidence to claim Messenger performs the same stable library-hash device registration.
- A bounded exact-name search found no `OnDeviceSignalsTouchListener` or `SelfieEvidenceRecorderProvider`. SmartCapture identity/selfie code is present, but this artifact does not support the earlier claim that Messenger installs that exact window-callback touch collector.

## Patch behavior

- Replaces the AD-ID manifest permission with an inert app-local permission of identical binary-string length.
- Installs an early main-activity hook that applies component policy and exposes a local privacy panel via an Android dynamic shortcut.
- Defaults Papaya, contact sync/upload, SmartCapture identity activities, and ConditionalWorker components to blocked.
- Adds a hard gate to `ContactsUploadServiceHandler.Bi5`: while contact blocking is enabled it returns a successful no-op result before the original upload dispatcher runs.
- Preserves user toggles in app-private preferences. Components can be restored to their manifest defaults from the panel.
- Adds an opt-in extreme permission revocation action.

## Verification and limitations

- REA 6.3.0 with pinned `jadx-headless-mcp` 0.7.1 authenticated the source digest and loaded 137,570 classes, 455,691 methods, and 25,392,297 instructions. The sandbox denied REA's final process-table cleanup inspection (`EPERM`), so its CLI returned `cleanup_incomplete`; focused evidence was completed with the same pinned JADX artifact plus apktool/smali inspection.
- Static analysis establishes code and declarations, not that every path executes for every account or region.
- The rebuilt APK was zip-aligned and its local v3 signature verifies. Package/version, hardened permission string, injected DEX symbols, main-activity hook, and contact hard-gate marker were checked after signing.
- No Android device/emulator smoke test was available. Calls, push delivery, login, E2EE messaging, media capture, and OEM-specific behavior remain unverified.
- Privacy-sensitive code remains in the APK. Component and handler gates reduce reachability; they do not prove that every reflective/native/dynamically delivered path is eliminated.
- Blocking ConditionalWorker may delay benign configuration, cleanup, or reliability jobs. Blocking SmartCapture may prevent identity/payment verification. Contact blocking intentionally disables contact discovery/sync.
