#!/usr/bin/env python3
"""Version-pinned privacy patch for apktool-decoded Bluesky 1.134.0."""

from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

ANDROID = "http://schemas.android.com/apk/res/android"
A = f"{{{ANDROID}}}"
ET.register_namespace("android", ANDROID)


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit(
            f"usage: {sys.argv[0]} APKTOOL_DECODED_ROOT ORIGINAL_SPLIT_CONFIG_XXHDPI_APK"
        )
    root = Path(sys.argv[1]).resolve()
    xxhdpi_split = Path(sys.argv[2]).resolve()
    manifest_path = root / "AndroidManifest.xml"
    tree = ET.parse(manifest_path)
    manifest = tree.getroot()
    app = manifest.find("application")
    if app is None:
        raise RuntimeError("application element missing")
    disabled = {
        "io.sentry.android.core.SentryInitProvider",
        "io.sentry.android.core.SentryPerformanceProvider",
        "io.sentry.ndk.SentryNdkPreloadProvider",
    }
    for node in app:
        if node.get(A + "name") in disabled:
            node.set(A + "enabled", "false")
    for node in app.iter("meta-data"):
        if node.get(A + "name") == "io.sentry.auto-init":
            node.set(A + "value", "false")
    main_activity = app.find(
        "activity[@android:name='xyz.blueskyweb.app.MainActivity']",
        {"android": ANDROID},
    )
    if main_activity is not None and main_activity.get(A + "configChanges") == "0x80002fb4":
        main_activity.set(
            A + "configChanges",
            "assetsPaths|layoutDirection|smallestScreenSize|screenSize|uiMode|screenLayout|orientation|keyboardHidden|keyboard|locale",
        )
    for node in list(app.findall("meta-data")):
        if node.get(A + "resource") == "@null":
            app.remove(node)
    ET.indent(tree, space="    ")
    tree.write(manifest_path, encoding="utf-8", xml_declaration=True)

    # These two drawables are referenced by the base but named and defined only
    # by the density split. Decoding the base alone turns both references into
    # @null, which crashes when React Native creates a native text field.
    drawable = root / "res/drawable/rn_edit_text_material.xml"
    drawable_text = drawable.read_text(encoding="utf-8")
    drawable_text = drawable_text.replace(
        'android:state_enabled="false" android:drawable="@null"',
        'android:state_enabled="false" android:drawable="@drawable/abc_textfield_default_mtrl_alpha"',
    ).replace(
        'android:drawable="@null"',
        'android:drawable="@drawable/abc_textfield_activated_mtrl_alpha"',
        1,
    )
    drawable.write_text(drawable_text, encoding="utf-8")

    public_xml = root / "res/values/public.xml"
    public_text = public_xml.read_text(encoding="utf-8")
    anchor = '    <public type="drawable" name="abc_text_cursor_material" id="0x7f0800c9" />\n'
    additions = (
        '    <public type="drawable" name="abc_textfield_activated_mtrl_alpha" id="0x7f0800cd" />\n'
        '    <public type="drawable" name="abc_textfield_default_mtrl_alpha" id="0x7f0800ce" />\n'
    )
    if "abc_textfield_activated_mtrl_alpha" not in public_text:
        if anchor not in public_text:
            raise RuntimeError("expected Bluesky 1.134.0 public.xml anchor missing")
        public_xml.write_text(public_text.replace(anchor, anchor + additions, 1), encoding="utf-8")

    target_dir = root / "res/drawable-xxhdpi-v4"
    target_dir.mkdir(parents=True, exist_ok=True)
    split_assets = (
        "res/drawable-xxhdpi-v4/abc_textfield_activated_mtrl_alpha.9.png",
        "res/drawable-xxhdpi-v4/abc_textfield_default_mtrl_alpha.9.png",
    )
    with zipfile.ZipFile(xxhdpi_split) as archive:
        for asset in split_assets:
            (target_dir / Path(asset).name).write_bytes(archive.read(asset))

    smali = root / "smali_classes4/io/sentry/react/RNSentryModule.smali"
    text = smali.read_text(encoding="utf-8")
    signature = "initNativeSdk(Lcom/facebook/react/bridge/ReadableMap;Lcom/facebook/react/bridge/Promise;)V"
    pattern = re.compile(
        rf"(^\.method[^\n]*{re.escape(signature)}\n)(.*?)(^\.end method$)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match or "Lio/sentry/react/v;->h0" not in match.group(2):
        raise RuntimeError("expected Bluesky 1.134.0 Sentry bridge marker missing")
    body = """    .locals 1

    # privacy-hardening: decline React Native Sentry initialization.
    const/4 v0, 0x0
    invoke-static {v0}, Ljava/lang/Boolean;->valueOf(Z)Ljava/lang/Boolean;
    move-result-object v0
    invoke-interface {p2, v0}, Lcom/facebook/react/bridge/Promise;->resolve(Ljava/lang/Object;)V
    return-void"""
    replacement = match.group(1) + body + "\n" + match.group(3)
    smali.write_text(text[:match.start()] + replacement + text[match.end():], encoding="utf-8")


if __name__ == "__main__":
    main()
