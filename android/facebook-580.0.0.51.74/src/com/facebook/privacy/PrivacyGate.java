package com.facebook.privacy;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.content.pm.ShortcutInfo;
import android.content.pm.ShortcutManager;
import android.net.Uri;
import android.os.Build;
import android.provider.Settings;

import java.util.Arrays;
import java.util.Collections;

public final class PrivacyGate {
    public static final String PREFS = "fb_privacy_controls";
    private static volatile Context appContext;

    private PrivacyGate() {}

    public static void remember(Context context) {
        if (context != null) {
            appContext = context.getApplicationContext();
        }
    }

    public static boolean isBlocked(Context context, String key, boolean defaultValue) {
        remember(context);
        return context == null
                ? defaultValue
                : context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                    .getBoolean(key, defaultValue);
    }

    public static boolean isBlocked(String key, boolean defaultValue) {
        Context context = appContext;
        return context == null ? defaultValue : isBlocked(context, key, defaultValue);
    }

    public static void setBlocked(Context context, String key, boolean blocked) {
        remember(context);
        context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
                .edit().putBoolean(key, blocked).apply();
        syncComponents(context);
    }

    public static void install(Context context) {
        remember(context);
        syncComponents(context);

        PackageManager packageManager = context.getPackageManager();
        ComponentName panel = new ComponentName(
                context,
                "com.facebook.zero.v2.simulation.ZeroV2SimulationActivity");
        try {
            packageManager.setComponentEnabledSetting(
                    panel,
                    PackageManager.COMPONENT_ENABLED_STATE_ENABLED,
                    PackageManager.DONT_KILL_APP);
        } catch (RuntimeException ignored) {}

        if (Build.VERSION.SDK_INT >= 25) {
            try {
                Intent intent = new Intent(Intent.ACTION_VIEW);
                intent.setComponent(panel);
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                ShortcutInfo shortcut = new ShortcutInfo.Builder(context, "fb_privacy_controls")
                        .setShortLabel("Privacy controls")
                        .setLongLabel("Facebook Privacy Controls")
                        .setIntent(intent)
                        .build();
                ShortcutManager manager = context.getSystemService(ShortcutManager.class);
                if (manager != null) {
                    manager.addDynamicShortcuts(Collections.singletonList(shortcut));
                }
            } catch (RuntimeException ignored) {}
        }
    }

    public static void syncComponents(Context context) {
        boolean glcBlocked = isBlocked(context, "block_glc", true);
        setComponentBlocked(context, "com.facebook.glc.GLCServiceSchedulerReceiver", glcBlocked);
        setComponentBlocked(context, "com.facebook.glc.ScheduledWifiMonitorService", glcBlocked);
        setComponentBlocked(context, "com.facebook.glc.LongRunningWifiMonitorService", glcBlocked);
        setComponentBlocked(context, "com.facebook.glc.GLCService", glcBlocked);

        boolean papayaBlocked = isBlocked(context, "block_papaya", true);
        setComponentBlocked(context,
                "com.facebook.papaya.fb.client.services.FBPapayaJobService", papayaBlocked);

        boolean backgroundBlocked = isBlocked(context, "block_background", true);
        setComponentBlocked(context,
                "com.facebook.conditionalworker.ConditionalWorkerService", backgroundBlocked);
        setComponentBlocked(context,
                "com.facebook.conditionalworker.ConditionalWorkerServiceReceiver", backgroundBlocked);
        setComponentBlocked(context,
                "com.facebook.conditionalworker.LollipopConditionalWorkerService", backgroundBlocked);
        setComponentBlocked(context,
                "com.facebook.conditionalworker.GooglePlayConditionalWorkerService", backgroundBlocked);
    }

    private static void setComponentBlocked(Context context, String className, boolean blocked) {
        try {
            context.getPackageManager().setComponentEnabledSetting(
                    new ComponentName(context, className),
                    blocked ? PackageManager.COMPONENT_ENABLED_STATE_DISABLED
                            : PackageManager.COMPONENT_ENABLED_STATE_DEFAULT,
                    PackageManager.DONT_KILL_APP);
        } catch (RuntimeException ignored) {}
    }

    public static void applyExtreme(Activity activity) {
        if (Build.VERSION.SDK_INT >= 33) {
            try {
                activity.revokeSelfPermissionsOnKill(Arrays.asList(
                        "android.permission.CAMERA",
                        "android.permission.RECORD_AUDIO",
                        "android.permission.ACCESS_FINE_LOCATION",
                        "android.permission.ACCESS_COARSE_LOCATION",
                        "android.permission.READ_CONTACTS",
                        "android.permission.WRITE_CONTACTS",
                        "android.permission.READ_MEDIA_IMAGES",
                        "android.permission.READ_MEDIA_VIDEO",
                        "android.permission.READ_MEDIA_AUDIO"));
            } catch (RuntimeException ignored) {
                openAppSettings(activity);
            }
        } else {
            openAppSettings(activity);
        }
    }

    public static void openAppSettings(Context context) {
        Intent intent = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                Uri.parse("package:" + context.getPackageName()));
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        context.startActivity(intent);
    }
}
