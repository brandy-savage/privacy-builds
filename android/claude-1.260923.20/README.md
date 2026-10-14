# Claude Android 1.260923.20

Static audit and version-pinned apktool/smali patch for
`com.anthropic.claude` version `1.260923.20` (`26092320`). This experiment
blocks the inspected Sentry, Datadog, and Segment startup or event-queue paths.

The patch expects an apktool-decoded split-APK base. Rebuild and sign the base
and every configuration split with one local certificate before installing the
set together.

No APK, signing key, decompiled application tree, account data, or credentials
are included. See [AUDIT.md](AUDIT.md) for evidence and coverage limits.
