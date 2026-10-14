package com.google.androidbrowserhelper.trusted;

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
import com.google.android.privacy.PrivacyGate;

public final class ManageDataLauncherActivity extends Activity
        implements CompoundButton.OnCheckedChangeListener, View.OnClickListener {
    private int dp(float value) { return Math.round(value * getResources().getDisplayMetrics().density); }

    @Override public void onCreate(Bundle state) {
        setTheme(android.R.style.Theme_Material_Light_NoActionBar);
        super.onCreate(state);
        requestWindowFeature(Window.FEATURE_NO_TITLE);
        Window window = getWindow();
        window.setBackgroundDrawable(new ColorDrawable(Color.TRANSPARENT));
        window.setDimAmount(0.64f);
        window.addFlags(android.view.WindowManager.LayoutParams.FLAG_DIM_BEHIND);

        ScrollView scroll = new ScrollView(this);
        LinearLayout card = new LinearLayout(this);
        card.setOrientation(LinearLayout.VERTICAL);
        int pad = dp(22);
        card.setPadding(pad, dp(18), pad, dp(18));
        GradientDrawable bg = new GradientDrawable();
        bg.setColor(Color.rgb(250, 250, 252));
        bg.setCornerRadius(dp(22));
        card.setBackground(bg);

        TextView title = text("Gmail Privacy Controls", 24, Color.rgb(22, 25, 31));
        title.setTypeface(null, android.graphics.Typeface.BOLD);
        card.addView(title);
        TextView intro = text("Local kill switches in this rebuilt APK. On means blocked. Long-press the Gmail icon to reopen this panel.", 14, Color.rgb(74, 79, 89));
        intro.setPadding(0, dp(8), 0, dp(12));
        card.addView(intro);
        card.addView(toggle("Block diagnostics, metrics and surveys", "block_measurement", true));
        card.addView(toggle("Block componentized Gemini / AI assist surfaces", "block_ai", true));
        card.addView(toggle("Disable Google Chat and Meet components", "block_chatmeet", true));
        card.addView(toggle("Disable trusted-web and hybrid-web bridges", "block_webbridges", true));
        Switch extreme = toggle("EXTREME: disable camera, voice, call, contact and calendar components", "extreme_mode", false);
        extreme.setTextColor(Color.rgb(154, 30, 42));
        card.addView(extreme);
        TextView note = text("Advertising ID and Android ad-attribution permissions are removed permanently. Extreme mode is reversible here, but any Android runtime permissions already granted must be changed in system settings.", 13, Color.rgb(95, 63, 26));
        note.setPadding(0, dp(10), 0, dp(8));
        card.addView(note);
        card.addView(button("Android permission controls", "permissions"));
        card.addView(button("Close", "close"));
        scroll.addView(card, new ScrollView.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT));
        setContentView(scroll);
        android.view.WindowManager.LayoutParams p = window.getAttributes();
        p.width = Math.min(dp(560), getResources().getDisplayMetrics().widthPixels - dp(24));
        p.height = Math.min(dp(780), getResources().getDisplayMetrics().heightPixels - dp(48));
        p.gravity = Gravity.CENTER;
        window.setAttributes(p);
    }

    private TextView text(String s, int sp, int color) {
        TextView v = new TextView(this); v.setText(s); v.setTextSize(sp); v.setTextColor(color);
        v.setLineSpacing(0f, 1.12f); return v;
    }
    private Switch toggle(String label, String key, boolean def) {
        Switch v = new Switch(this); v.setText(label); v.setTextSize(15);
        v.setTextColor(Color.rgb(35, 39, 47)); v.setGravity(Gravity.CENTER_VERTICAL);
        v.setPadding(0, dp(8), 0, dp(8)); v.setTag(key);
        v.setChecked(PrivacyGate.isBlocked(this, key, def));
        v.setOnCheckedChangeListener(this); return v;
    }
    private Button button(String label, String tag) {
        Button b = new Button(this); b.setText(label); b.setTag(tag); b.setOnClickListener(this);
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(-1, -2); p.topMargin = dp(8);
        b.setLayoutParams(p); return b;
    }
    @Override public void onCheckedChanged(CompoundButton b, boolean checked) {
        Object tag = b.getTag();
        if (tag instanceof String) PrivacyGate.setBlocked(this, (String) tag, checked);
    }
    @Override public void onClick(View v) {
        if ("permissions".equals(v.getTag())) PrivacyGate.openAppSettings(this); else finish();
    }
}
