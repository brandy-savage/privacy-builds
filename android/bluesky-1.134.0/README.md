# Bluesky Android 1.134.0

Static audit and version-pinned apktool/smali patch for
`xyz.blueskyweb.app` version `1.134.0` (`1608`). This experiment blocks the
inspected Java, native, and React Native Sentry startup paths while retaining
Firebase/Expo notification delivery.

The patch command also takes the original xxhdpi configuration split so it can
restore two split-only React Native text-field drawables that apktool otherwise
decodes as `@null`:

```text
python3 patch.py APKTOOL_DECODED_ROOT ORIGINAL_SPLIT_CONFIG_XXHDPI_APK
```

No APK, signing key, decompiled application tree, account data, or credentials
are included. See [AUDIT.md](AUDIT.md) for evidence and coverage limits.
