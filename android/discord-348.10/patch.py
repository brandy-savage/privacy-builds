#!/usr/bin/env python3
"""Version-pinned privacy patch for apktool-decoded Discord 348.10."""

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
        raise RuntimeError(f"expected 348.10 method marker missing: {path}:{signature}")
    replacement = match.group(1) + body.rstrip() + "\n" + match.group(3)
    path.write_text(text[:match.start()] + replacement + text[match.end():], encoding="utf-8")


def patch_manifest(root: Path) -> None:
    path = root / "AndroidManifest.xml"
    tree = ET.parse(path)
    manifest = tree.getroot()
    for node in list(manifest):
        if node.tag.startswith("uses-permission") and node.get(A + "name") in {
            "com.google.android.gms.permission.AD_ID",
            "android.permission.ACCESS_ADSERVICES_ATTRIBUTION",
        }:
            manifest.remove(node)
    app = manifest.find("application")
    if app is None:
        raise RuntimeError("application element missing")
    disabled = {
        "com.google.android.gms.analytics.AnalyticsReceiver",
        "com.google.android.gms.analytics.AnalyticsService",
        "com.google.android.gms.analytics.AnalyticsJobService",
        "io.sentry.android.core.SentryInitProvider",
        "io.sentry.android.core.SentryPerformanceProvider",
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
    replace_method(root / "smali/com/discord/crash_reporting/CrashReporting.smali", "isDisabled()Z", "return", """    .locals 1

    # privacy-hardening: use Discord's own disabled path.
    const/4 v0, 0x1
    return v0""")
    replace_method(root / "smali/com/discord/deep_link/DeepLinks.smali", "init(Landroid/content/Context;)V", "AppsFlyerLib", """    .locals 0

    # privacy-hardening: disable AppsFlyer and deferred-link attribution.
    return-void""")
    replace_method(root / "smali/com/discord/analytics/touch/TouchEventAnalyticsModule.smali", "enableTouchLogging()V", "Enabling touch logging", """    .locals 0

    # privacy-hardening: prevent touch/view analytics collection.
    return-void""")
    replace_method(root / "smali/com/discord/analytics/InstallReferrerModule.smali", "get(Lcom/facebook/react/bridge/Promise;)V", "InstallReferrer", """    .locals 1

    # privacy-hardening: return no install-referrer payload.
    const/4 v0, 0x0
    invoke-interface {p1, v0}, Lcom/facebook/react/bridge/Promise;->resolve(Ljava/lang/Object;)V
    return-void""")
    replace_method(root / "smali/com/discord/libdiscore/LibdiscoreModuleClass$LibdiscoreModule.smali", "installSentryReporter()V", "jniInstallSentryReporter", """    .locals 0

    # privacy-hardening: do not install the native Sentry reporter.
    return-void""")


if __name__ == "__main__":
    main()
