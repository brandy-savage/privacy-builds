package com.google.android.privacy;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.pm.ActivityInfo;
import android.content.pm.ComponentInfo;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.ProviderInfo;
import android.content.pm.ServiceInfo;
import android.content.pm.ShortcutInfo;
import android.content.pm.ShortcutManager;
import android.graphics.drawable.Icon;
import android.net.Uri;
import android.os.Build;
import android.provider.Settings;

import java.util.Collections;
import java.util.Locale;

public final class PrivacyGate {
    public static final String PREFS = "gmail_privacy_controls";
    public static final String CONTROL =
            "com.google.androidbrowserhelper.trusted.ManageDataLauncherActivity";

    private PrivacyGate() {}

    public static boolean isBlocked(Context context, String key, boolean defaultValue) {
        return context == null ? defaultValue : context.getSharedPreferences(PREFS, 0)
                .getBoolean(key, defaultValue);
    }

    public static void setBlocked(Context context, String key, boolean blocked) {
        context.getSharedPreferences(PREFS, 0).edit().putBoolean(key, blocked).apply();
        syncComponents(context);
    }

    public static void install(Context context) {
        if (context == null) return;
        enableControl(context);
        syncComponents(context);
        if (Build.VERSION.SDK_INT >= 25) {
            try {
                ComponentName panel = new ComponentName(context, CONTROL);
                Intent intent = new Intent("com.google.android.gm.PRIVACY_CONTROLS")
                        .setComponent(panel).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                ShortcutInfo shortcut = new ShortcutInfo.Builder(context, "gmail_privacy_controls")
                        .setShortLabel("Privacy controls")
                        .setLongLabel("Gmail Privacy Controls")
                        .setIcon(Icon.createWithResource(context, android.R.drawable.ic_secure))
                        .setIntent(intent).build();
                ShortcutManager manager = context.getSystemService(ShortcutManager.class);
                if (manager != null) manager.addDynamicShortcuts(Collections.singletonList(shortcut));
            } catch (RuntimeException ignored) {}
        }
    }

    private static void enableControl(Context context) {
        try {
            context.getPackageManager().setComponentEnabledSetting(
                    new ComponentName(context, CONTROL),
                    PackageManager.COMPONENT_ENABLED_STATE_ENABLED,
                    PackageManager.DONT_KILL_APP);
        } catch (RuntimeException ignored) {}
    }

    public static void syncComponents(Context context) {
        if (context == null) return;
        try {
            PackageManager pm = context.getPackageManager();
            int flags = PackageManager.GET_ACTIVITIES | PackageManager.GET_SERVICES
                    | PackageManager.GET_RECEIVERS | PackageManager.GET_PROVIDERS
                    | PackageManager.GET_DISABLED_COMPONENTS;
            PackageInfo info = pm.getPackageInfo(context.getPackageName(), flags);
            apply(context, info.activities);
            apply(context, info.services);
            apply(context, info.receivers);
            apply(context, info.providers);
        } catch (Exception ignored) {}
        enableControl(context);
    }

    private static void apply(Context context, ComponentInfo[] components) {
        if (components == null) return;
        for (ComponentInfo component : components) {
            if (component == null || component.name == null || CONTROL.equals(component.name)) continue;
            String n = component.name.toLowerCase(Locale.US);
            boolean block = false;
            boolean managed = false;
            boolean match = has(n, "clearcut", "performance.primes", ".surveys.",
                    "telemetry", "clienttracing", "metrics");
            managed |= match;
            block |= match && isBlocked(context, "block_measurement", true);
            match = has(n, "gemini", "smartcompose", "smartreply", "genai", "aicore");
            managed |= match;
            block |= match && isBlocked(context, "block_ai", true);
            match = has(n, "apps.dynamite", "communications.conference", "videochat", "hangouts");
            managed |= match;
            block |= match && isBlocked(context, "block_chatmeet", true);
            match = has(n, "androidbrowserhelper.trusted", "hybridtwa");
            managed |= match;
            block |= match && isBlocked(context, "block_webbridges", true);
            match = has(n, "camera", "voice", "effectspipe", "audiocapture",
                    ".call", "contacts", "calendar", "peoplekit");
            managed |= match;
            block |= match && isBlocked(context, "extreme_mode", false);
            if (managed) set(context, component.name, block);
        }
    }

    private static boolean has(String value, String... needles) {
        for (String needle : needles) if (value.contains(needle)) return true;
        return false;
    }

    private static void set(Context context, String name, boolean blocked) {
        try {
            context.getPackageManager().setComponentEnabledSetting(
                    new ComponentName(context, name),
                    blocked ? PackageManager.COMPONENT_ENABLED_STATE_DISABLED
                            : PackageManager.COMPONENT_ENABLED_STATE_DEFAULT,
                    PackageManager.DONT_KILL_APP);
        } catch (RuntimeException ignored) {}
    }

    public static void openAppSettings(Context context) {
        Intent intent = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                Uri.parse("package:" + context.getPackageName()));
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        context.startActivity(intent);
    }
}
