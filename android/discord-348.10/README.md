# Discord Android 348.10

Static audit and version-pinned apktool/smali patch for `com.discord` version
`348.10 - Stable` (`348010`). The experiment blocks inspected crash reporting,
AppsFlyer/deferred-link initialization, install-referrer delivery, view/touch
analytics, Google Analytics components, and advertising-identity permissions.

The patch expects an apktool-decoded split-APK base. Rebuild and sign the base
and every configuration split with one local certificate before installing the
set together.

No APK, signing key, decompiled application tree, account data, or credentials
are included. See [AUDIT.md](AUDIT.md) for evidence and coverage limits.
