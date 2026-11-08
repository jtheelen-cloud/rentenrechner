package de.theelen.wetterwidget;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.Gravity;
import android.view.inputmethod.EditorInfo;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import org.json.JSONArray;
import org.json.JSONObject;

/** Ort für das Widget wählen (Suche wie in der Wetter-App). */
public class MainActivity extends Activity {
    LinearLayout list; TextView cur; final Handler ui = new Handler(Looper.getMainLooper());

    @Override protected void onCreate(Bundle b) {
        super.onCreate(b);
        int pad = dp(16);
        LinearLayout root = new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL); root.setPadding(pad, pad * 2, pad, pad);
        root.setBackgroundColor(Color.parseColor("#141414"));
        TextView title = tv("Wetter-Widget", 24, Color.WHITE); root.addView(title);
        cur = tv("", 15, Color.parseColor("#C8C8C8")); cur.setPadding(0, dp(6), 0, dp(14)); root.addView(cur); showCur();
        EditText q = new EditText(this); q.setHint("Ort suchen, z. B. Corralejo"); q.setSingleLine(true); q.setTextColor(Color.WHITE); q.setHintTextColor(Color.GRAY);
        q.setImeOptions(EditorInfo.IME_ACTION_SEARCH);
        q.setOnEditorActionListener((v, a, e) -> { search(q.getText().toString()); return true; });
        root.addView(q);
        Button go = new Button(this); go.setText("Suchen"); go.setOnClickListener(v -> search(q.getText().toString())); root.addView(go);
        ScrollView sv = new ScrollView(this); list = new LinearLayout(this); list.setOrientation(LinearLayout.VERTICAL); sv.addView(list);
        root.addView(sv, new LinearLayout.LayoutParams(-1, 0, 1));
        TextView help = tv("So legst du das Widget an: lange auf eine freie Stelle des Startbildschirms drücken → „Widgets“ → „Wetter-Widget“ suchen → auf den Startbildschirm ziehen.\n\nTippen aufs Widget öffnet die Wetter-App, Tippen auf den Ortsnamen öffnet diese Seite, ⟳ aktualisiert.", 13, Color.parseColor("#9A9A9A"));
        help.setPadding(0, dp(10), 0, dp(10)); root.addView(help);
        Button app = new Button(this); app.setText("Wetter-App öffnen"); app.setOnClickListener(v -> startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(Weather.APP_URL)))); root.addView(app);
        setContentView(root);
    }

    void showCur() { cur.setText("Ort im Widget: " + Weather.placeName(this)); }

    void search(String s) {
        if (s.trim().length() < 2) return;
        list.removeAllViews(); list.addView(tv("Suche …", 15, Color.GRAY));
        new Thread(() -> {
            try {
                JSONArray r = Weather.search(s.trim());
                ui.post(() -> {
                    list.removeAllViews();
                    if (r.length() == 0) list.addView(tv("Kein Ort gefunden.", 15, Color.GRAY));
                    for (int i = 0; i < r.length(); i++) {
                        JSONObject o = r.optJSONObject(i); if (o == null) continue;
                        String n = o.optString("name"), sub = join(o.optString("admin1"), o.optString("country"));
                        double la = o.optDouble("latitude"), lo = o.optDouble("longitude");
                        TextView row = tv(n + "\n" + sub, 16, Color.WHITE); row.setPadding(0, dp(12), 0, dp(12));
                        row.setOnClickListener(v -> { Weather.savePlace(this, n, la, lo); showCur(); WeatherWidget.updateAll(this); list.removeAllViews(); list.addView(tv("✓ " + n + " gespeichert. Das Widget aktualisiert sich gleich.", 15, Color.parseColor("#7CC0FF"))); });
                        list.addView(row);
                    }
                });
            } catch (Exception e) { ui.post(() -> { list.removeAllViews(); list.addView(tv("Suche gerade nicht erreichbar.", 15, Color.GRAY)); }); }
        }).start();
    }

    static String join(String a, String b) { return (a == null || a.isEmpty() || a.equals("null")) ? b : a + ", " + b; }
    TextView tv(String s, int sp, int col) { TextView t = new TextView(this); t.setText(s); t.setTextSize(sp); t.setTextColor(col); t.setGravity(Gravity.START); return t; }
    int dp(int v) { return Math.round(v * getResources().getDisplayMetrics().density); }
}
