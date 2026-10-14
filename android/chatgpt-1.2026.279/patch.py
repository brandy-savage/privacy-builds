#!/usr/bin/env python3
"""Version-pinned privacy patch for apktool-decoded ChatGPT 1.2026.279."""

from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ANDROID = "http://schemas.android.com/apk/res/android"
A = f"{{{ANDROID}}}"
ET.register_namespace("android", ANDROID)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} APKTOOL_DECODED_ROOT")
    root = Path(sys.argv[1]).resolve()
    path = root / "AndroidManifest.xml"
    tree = ET.parse(path)
    manifest = tree.getroot()

    for node in list(manifest):
        if (
            node.tag.startswith("uses-permission")
            and node.get(A + "name") == "com.google.android.gms.permission.AD_ID"
        ):
            manifest.remove(node)

    app = manifest.find("application")
    if app is None:
        raise RuntimeError("application element missing")
    disabled = {
        "com.datadog.android.rum.DdRumContentProvider",
        "io.sentry.ndk.SentryNdkPreloadProvider",
        "papa.internal.PerfsAppStartListener",
    }
    for node in app:
        if node.get(A + "name") in disabled:
            node.set(A + "enabled", "false")

    for parent in manifest.iter():
        for node in list(parent):
            if node.tag != "meta-data":
                continue
            name = node.get(A + "name", "")
            if "io.sentry.gradle-plugin-integrations" in name:
                parent.remove(node)
            elif name == "io.sentry.auto-init":
                node.set(A + "value", "false")

    ET.indent(tree, space="    ")
    tree.write(path, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    main()
