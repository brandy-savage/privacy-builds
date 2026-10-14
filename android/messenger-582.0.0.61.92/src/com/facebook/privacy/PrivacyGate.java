package com.facebook.privacy;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.content.pm.ShortcutInfo;
import android.content.pm.ShortcutManager;
import android.net.Uri;
import android.os.Build;
import android.provider.Settings;

import java.util.Arrays;
import java.util.Collections;

public final class PrivacyGate {
    public static final String PREFS = "messenger_privacy_controls";
    private static volatile Context appContext;

    private PrivacyGate() {}

    public static void remember(Context context) {
        if (context != null) appContext = context.getApplicationContext();
    }

    public static boolean isBlocked(Context context, String key, boolean defaultValue) {
        remember(context);
        return context == null ? defaultValue : context.getSharedPreferences(PREFS, 0)
                .getBoolean(key, defaultValue);
    }

    public static void setBlocked(Context context, String key, boolean blocked) {
        remember(context);
        context.getSharedPreferences(PREFS, 0).edit().putBoolean(key, blocked).apply();
        syncComponents(context);
        if (blocked && "block_contacts".equals(key)) revokeContacts(context);
    }

    public static void install(Context context) {
        remember(context);
        syncComponents(context);
        if (isBlocked(context, "block_contacts", true)) revokeContacts(context);
        ComponentName panel = new ComponentName(context,
                "com.facebook.messaging.about.MessengerAboutLicenseActivity");
        try {
            context.getPackageManager().setComponentEnabledSetting(panel,
                    PackageManager.COMPONENT_ENABLED_STATE_ENABLED,
                    PackageManager.DONT_KILL_APP);
        } catch (RuntimeException ignored) {}
        if (Build.VERSION.SDK_INT >= 25) {
            try {
                Intent intent = new Intent(Intent.ACTION_VIEW).setComponent(panel)
                        .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                ShortcutInfo shortcut = new ShortcutInfo.Builder(context, "messenger_privacy_controls")
                        .setShortLabel("Privacy controls")
                        .setLongLabel("Messenger Privacy Controls")
                        .setIntent(intent).build();
                ShortcutManager manager = context.getSystemService(ShortcutManager.class);
                if (manager != null) manager.addDynamicShortcuts(Collections.singletonList(shortcut));
            } catch (RuntimeException ignored) {}
        }
    }

    public static void syncComponents(Context context) {
        boolean papaya = isBlocked(context, "block_papaya", true);
        block(context, "com.facebook.papaya.fb.messenger.MessengerPapayaExecutionJobService", papaya);

        boolean contacts = isBlocked(context, "block_contacts", true);
        block(context, "com.facebook.messaging.stella.contacts.StellaContactsService", contacts);
        block(context, "com.facebook.messaging.stella.contacts.StellaContactBroadcastReceiver", contacts);
        block(context, "com.facebook.messaging.phonebookintegration.account.MessengerSyncAdapterService", contacts);

        boolean background = isBlocked(context, "block_background", true);
        block(context, "com.facebook.conditionalworker.ConditionalWorkerService", background);
        block(context, "com.facebook.conditionalworker.ConditionalWorkerServiceReceiver", background);
        block(context, "com.facebook.conditionalworker.LollipopConditionalWorkerService", background);
        block(context, "com.facebook.conditionalworker.GooglePlayConditionalWorkerService", background);

        boolean capture = isBlocked(context, "block_smartcapture", true);
        block(context, "com.facebook.smartcapture.view.SelfieCaptureActivity", capture);
        block(context, "com.facebook.smartcapture.view.SelfieCapturePermissionsActivity", capture);
        block(context, "com.facebook.smartcapture.view.SelfieOnboardingActivity", capture);
        block(context, "com.facebook.smartcapture.view.SelfieDataInformationActivity", capture);
        block(context, "com.facebook.smartcapture.view.PermissionsActivity", capture);
        block(context, "com.facebook.smartcapture.view.IdCaptureActivity", capture);
        block(context, "com.facebook.smartcapture.view.PhotoReviewActivity", capture);
    }

    private static void block(Context context, String name, boolean blocked) {
        try {
            context.getPackageManager().setComponentEnabledSetting(new ComponentName(context, name),
                    blocked ? PackageManager.COMPONENT_ENABLED_STATE_DISABLED
                            : PackageManager.COMPONENT_ENABLED_STATE_DEFAULT,
                    PackageManager.DONT_KILL_APP);
        } catch (RuntimeException ignored) {}
    }

    private static void revokeContacts(Context context) {
        if (Build.VERSION.SDK_INT >= 33) {
            try {
                context.revokeSelfPermissionsOnKill(Arrays.asList(
                        "android.permission.READ_CONTACTS", "android.permission.WRITE_CONTACTS",
                        "android.permission.READ_PROFILE", "android.permission.GET_ACCOUNTS"));
            } catch (RuntimeException ignored) {}
        }
    }

    public static void applyExtreme(Activity activity) {
        if (Build.VERSION.SDK_INT >= 33) {
            try {
                activity.revokeSelfPermissionsOnKill(Arrays.asList(
                        "android.permission.CAMERA", "android.permission.RECORD_AUDIO",
                        "android.permission.ACCESS_FINE_LOCATION", "android.permission.ACCESS_COARSE_LOCATION",
                        "android.permission.READ_CONTACTS", "android.permission.WRITE_CONTACTS",
                        "android.permission.READ_PROFILE", "android.permission.GET_ACCOUNTS",
                        "android.permission.READ_PHONE_STATE", "android.permission.READ_PHONE_NUMBERS",
                        "android.permission.CALL_PHONE", "android.permission.READ_CALENDAR",
                        "android.permission.WRITE_CALENDAR", "android.permission.READ_MEDIA_IMAGES",
                        "android.permission.READ_MEDIA_VIDEO", "android.permission.READ_MEDIA_AUDIO",
                        "android.permission.BLUETOOTH_CONNECT"));
                return;
            } catch (RuntimeException ignored) {}
        }
        openAppSettings(activity);
    }

    public static void openAppSettings(Context context) {
        Intent intent = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                Uri.parse("package:" + context.getPackageName()));
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        context.startActivity(intent);
    }
}
