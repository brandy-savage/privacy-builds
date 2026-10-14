# Spotify Android 9.1.90.2270

Static audit and policy-layer excerpts for `com.spotify.music`. The experiment
neutralizes ad-identity permissions, hard-gates inspected Comscore startup, and
gates componentized measurement, device-ID, scanner/voice/camera, engagement,
and cross-device surfaces. Extreme mode additionally disables discovery and
external-control components.

No APK, signing key, decompiled application tree, account data, or credentials
are included. See [AUDIT.md](AUDIT.md) for compatibility and coverage limits.
