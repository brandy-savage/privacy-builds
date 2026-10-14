#!/usr/bin/env python3
"""Version-pinned manifest privacy patch for apktool-decoded X 12.33.1."""

from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ANDROID = "http://schemas.android.com/apk/res/android"
A = f"{{{ANDROID}}}"
ET.register_namespace("android", ANDROID)

REMOVE_PERMISSIONS = {
    "com.google.android.gms.permission.AD_ID",
    "android.permission.ACCESS_ADSERVICES_AD_ID",
    "android.permission.ACCESS_ADSERVICES_ATTRIBUTION",
}
DISABLE = {
    "com.google.android.gms.measurement.AppMeasurementReceiver",
    "com.google.android.gms.measurement.AppMeasurementService",
    "com.google.android.gms.measurement.AppMeasurementJobService",
    "com.braze.ui.BrazeWebViewActivity",
    "com.braze.ui.activities.ContentCardsActivity",
    "com.braze.push.NotificationTrampolineActivity",
    "com.braze.push.BrazePushReceiver",
    "com.braze.BrazeFlushPushDeliveryReceiver",
    "com.x.perfdiagnostics.ui.PerfDiagnosticsActivity",
}
REMOVE_METADATA = {
    "com.google.firebase.components:com.google.firebase.analytics.connector.internal.AnalyticsConnectorRegistrar",
    "com.google.firebase.components:com.google.firebase.perf.FirebasePerfRegistrar",
    "com.google.firebase.components:com.google.firebase.perf.FirebasePerfKtxRegistrar",
    "io.sentry.dsn",
}
FALSE_METADATA = {
    "firebase_crashlytics_collection_enabled",
    "google_analytics_adid_collection_enabled",
    "io.sentry.send-default-pii",
}
REQUIRED_CRASHLYTICS = {
    "com.google.firebase.components:com.google.firebase.crashlytics.CrashlyticsRegistrar",
    "com.google.firebase.components:com.google.firebase.crashlytics.FirebaseCrashlyticsKtxRegistrar",
}


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {sys.argv[0]} APKTOOL_DECODED_ROOT")
    path = Path(sys.argv[1]).resolve() / "AndroidManifest.xml"
    tree = ET.parse(path)
    manifest = tree.getroot()
    for node in list(manifest):
        if node.tag.startswith("uses-permission") and node.get(A + "name") in REMOVE_PERMISSIONS:
            manifest.remove(node)
    app = manifest.find("application")
    if app is None:
        raise RuntimeError("application element missing")
    for parent in manifest.iter():
        for node in list(parent):
            if node.tag == "uses-library" and node.get(A + "name") == "android.ext.adservices":
                parent.remove(node)
            elif node.tag == "meta-data":
                name = node.get(A + "name", "")
                if name in REMOVE_METADATA:
                    parent.remove(node)
                elif name in FALSE_METADATA:
                    node.set(A + "value", "false")
    for node in app:
        if node.get(A + "name") in DISABLE:
            node.set(A + "enabled", "false")
    discovery = app.find(
        "service[@android:name='com.google.firebase.components.ComponentDiscoveryService']",
        {"android": ANDROID},
    )
    if discovery is None:
        raise RuntimeError("Firebase ComponentDiscoveryService missing")
    present = {node.get(A + "name") for node in discovery.findall("meta-data")}
    for name in REQUIRED_CRASHLYTICS - present:
        ET.SubElement(discovery, "meta-data", {
            A + "name": name,
            A + "value": "com.google.firebase.components.ComponentRegistrar",
        })
    ET.indent(tree, space="    ")
    tree.write(path, encoding="utf-8", xml_declaration=True)


if __name__ == "__main__":
    main()
