# X Android 12.33.1-prod.01

Static audit and version-pinned manifest patch for `com.twitter.android`
version `12.33.1-prod.01` (`312331001`). The experiment removes advertising
identity/AdServices access and disables selected Braze, Google measurement,
Firebase performance/analytics, and diagnostic entry points.

No APK, signing key, decompiled application tree, account data, or credentials
are included. See [AUDIT.md](AUDIT.md) for the important compatibility boundary
around Crashlytics.
