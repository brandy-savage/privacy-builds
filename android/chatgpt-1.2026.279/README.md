# ChatGPT Android 1.2026.279

Static audit and version-pinned apktool manifest patch for
`com.openai.chatgpt` version `1.2026.279` (`2627911`). This experiment removes
the Advertising ID permission and blocks the inspected Datadog RUM, Sentry NDK,
and internal performance-listener startup paths.

The patch expects an apktool-decoded split-APK base. Rebuild and sign the base
and every configuration split with one local certificate before installing the
set together.

No APK, signing key, decompiled application tree, account data, or credentials
are included. See [AUDIT.md](AUDIT.md) for evidence and coverage limits.
