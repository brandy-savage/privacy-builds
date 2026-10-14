package com.facebook.zero.v2.simulation;

import android.app.Activity;
import android.graphics.Color;
import android.graphics.drawable.ColorDrawable;
import android.graphics.drawable.GradientDrawable;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.widget.Button;
import android.widget.CompoundButton;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Switch;
import android.widget.TextView;

import com.facebook.privacy.PrivacyGate;

public final class ZeroV2SimulationActivity extends Activity
        implements CompoundButton.OnCheckedChangeListener, View.OnClickListener {

    private int dp(float value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    @Override
    public void onCreate(Bundle state) {
        super.onCreate(state);
        PrivacyGate.remember(this);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        Window window = getWindow();
        window.setBackgroundDrawable(new ColorDrawable(Color.TRANSPARENT));
        window.setDimAmount(0.62f);
        window.addFlags(android.view.WindowManager.LayoutParams.FLAG_DIM_BEHIND);

        ScrollView scroll = new ScrollView(this);
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        int pad = dp(22);
        card.setPadding(pad, dp(18), pad, dp(18));

        GradientDrawable background = new GradientDrawable();
        background.setColor(Color.rgb(250, 250, 252));
        background.setCornerRadius(dp(22));
        card.setBackground(background);

        TextView title = text("Facebook Privacy Controls", 24, Color.rgb(22, 25, 31));
        title.setTypeface(null, android.graphics.Typeface.BOLD);
        card.addView(title);

        TextView intro = text(
                "Local kill switches added to this rebuilt APK. Blocked is the privacy-safe state. " +
                "Long-press the Facebook icon to reopen this panel.",
                14, Color.rgb(74, 79, 89));
        intro.setPadding(0, dp(8), 0, dp(12));
        card.addView(intro);

        card.addView(toggle("Block GLC device/library fingerprinting", "block_glc", true));
        card.addView(toggle("Block Papaya federated jobs", "block_papaya", true));
        card.addView(toggle("Block SmartCapture touch telemetry", "block_touch", true));
        card.addView(toggle("Block scanned-card federated analytics", "block_card_fa", true));
        card.addView(toggle("Block ConditionalWorker background jobs", "block_background", true));
        card.addView(toggle("Block Bluetooth/BLE proximity scans", "block_ble", true));

        Switch extreme = toggle(
                "EXTREME: block identity/selfie capture + revoke sensitive permissions",
                "extreme_mode", false);
        extreme.setTextColor(Color.rgb(154, 30, 42));
        card.addView(extreme);

        TextView note = text(
                "Extreme mode blocks Facebook SmartCapture ID/selfie entry points. On Android 13+ it " +
                "also schedules revocation of camera, microphone, location, contacts, and media " +
                "permissions when the process exits. Turning it off does not silently re-grant them.",
                13, Color.rgb(95, 63, 26));
        note.setPadding(0, dp(10), 0, dp(8));
        card.addView(note);

        Button permissions = button("Android permission controls", "permissions");
        card.addView(permissions);
        Button close = button("Close", "close");
        card.addView(close);

        scroll.addView(card, new ScrollView.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT));
        setContentView(scroll);

        android.view.WindowManager.LayoutParams params = window.getAttributes();
        params.width = Math.min(dp(560), getResources().getDisplayMetrics().widthPixels - dp(24));
        params.height = Math.min(dp(760), getResources().getDisplayMetrics().heightPixels - dp(48));
        params.gravity = Gravity.CENTER;
        window.setAttributes(params);
    }

    private TextView text(String value, int sp, int color) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(sp);
        view.setTextColor(color);
        view.setLineSpacing(0f, 1.12f);
        return view;
    }

    private Switch toggle(String label, String key, boolean defaultValue) {
        Switch view = new Switch(this);
        view.setText(label);
        view.setTextSize(15);
        view.setTextColor(Color.rgb(35, 39, 47));
        view.setGravity(Gravity.CENTER_VERTICAL);
        view.setPadding(0, dp(8), 0, dp(8));
        view.setTag(key);
        view.setChecked(PrivacyGate.isBlocked(this, key, defaultValue));
        view.setOnCheckedChangeListener(this);
        return view;
    }

    private Button button(String label, String tag) {
        Button button = new Button(this);
        button.setText(label);
        button.setTag(tag);
        button.setOnClickListener(this);
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        params.topMargin = dp(8);
        button.setLayoutParams(params);
        return button;
    }

    @Override
    public void onCheckedChanged(CompoundButton button, boolean checked) {
        Object tag = button.getTag();
        if (!(tag instanceof String)) return;
        String key = (String) tag;
        PrivacyGate.setBlocked(this, key, checked);
        if ("extreme_mode".equals(key) && checked) {
            PrivacyGate.applyExtreme(this);
        }
    }

    @Override
    public void onClick(View view) {
        if ("permissions".equals(view.getTag())) {
            PrivacyGate.openAppSettings(this);
        } else {
            finish();
        }
    }
}
