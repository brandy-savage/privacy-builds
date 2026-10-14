#!/usr/bin/env python3
"""Version-pinned privacy patch for apktool-decoded Claude 1.260923.20."""

from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ANDROID = "http://schemas.android.com/apk/res/android"
A = f"{{{ANDROID}}}"
ET.register_namespace("android", ANDROID)


def replace_method(path: Path, signature: str, marker: str, body: str) -> None:
    text = path.read_text(encoding="utf-8")
    pattern = re.compile(
        rf"(^\.method[^\n]*{re.escape(signature)}\n)(.*?)(^\.end method$)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match or marker not in match.group(2):
        raise RuntimeError(
            f"expected Claude 1.260923.20 method marker missing: {path}:{signature}"
        )
    replacement = match.group(1) + body.rstrip() + "\n" + match.group(3)
    path.write_text(text[:match.start()] + replacement + text[match.end():], encoding="utf-8")


def patch_manifest(root: Path) -> None:
    path = root / "AndroidManifest.xml"
    tree = ET.parse(path)
    manifest = tree.getroot()
    app = manifest.find("application")
    if app is None:
        raise RuntimeError("application element missing")
    disabled = {
        "io.sentry.android.core.SentryInitProvider",
        "io.sentry.android.core.SentryPerformanceProvider",
        "com.datadog.android.profiling.DdProfilingContentProvider",
        "com.datadog.android.rum.DdRumContentProvider",
    }
    for node in app:
        if node.get(A + "name") in disabled:
            node.set(A + "enabled", "false")
    for node in app.iter("meta-data"):
        if node.get(A + "name") == "io.sentry.auto-init":
            node.set(A + "value", "false")
    ET.indent(tree, space="    ")
    tree.write(path, encoding="utf-8", xml_declaration=True)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} APKTOOL_DECODED_ROOT")
    root = Path(sys.argv[1]).resolve()
    patch_manifest(root)
    replace_method(
        root / "smali/jyp.smali",
        "b(Lio/sentry/android/core/SentryAndroidOptions;)V",
        "setDsn",
        """    .locals 1

    # privacy-hardening: disable the explicitly configured Sentry client.
    const/4 v0, 0x0
    invoke-virtual {p1, v0}, Lio/sentry/w6;->setEnabled(Z)V
    return-void""",
    )
    replace_method(
        root / "smali/c0s.smali",
        "a(Lcom/segment/analytics/kotlin/core/a;)Lcom/segment/analytics/kotlin/core/a;",
        "SegmentStartupQueue queueing event",
        """    .locals 1

    # privacy-hardening: discard Segment events before queueing or upload.
    const/4 v0, 0x0
    return-object v0""",
    )
    replace_method(
        root / "smali/c0s.smali",
        "b(Lw60;)V",
        "Lp9a;->S",
        """    .locals 0

    # privacy-hardening: retain construction semantics but never start the queue worker.
    iput-object p1, p0, Lc0s;->v:Lw60;
    return-void""",
    )


if __name__ == "__main__":
    main()
