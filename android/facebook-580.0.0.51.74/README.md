# Facebook Android 580.0.0.51.74

Static audit and source excerpts for a local privacy-control experiment against
`com.facebook.katana`. The policy layer defaults GLC, Papaya, SmartCapture touch
signals, card federated analytics, ConditionalWorker, and BLE scanning gates to
blocked, with an optional extreme permission-revocation mode.

No APK, decompiled vendor source, signing key, or personal configuration is
included. Review [AUDIT.md](AUDIT.md) before adapting the excerpts in `src/`.
The code is version-specific and requires independently obtained, verified
inputs plus manual manifest/DEX integration.
