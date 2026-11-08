package de.theelen.wetterwidget;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.widget.RemoteViews;
import org.json.JSONArray;
import org.json.JSONObject;

public class WeatherWidget extends AppWidgetProvider {
    static final String REFRESH = "de.theelen.wetterwidget.REFRESH";
    static final int[] H = {R.id.h0, R.id.h1, R.id.h2, R.id.h3, R.id.h4, R.id.h5};

    @Override public void onUpdate(Context c, AppWidgetManager m, int[] ids) { refresh(c); }

    @Override public void onReceive(Context c, Intent i) {
        super.onReceive(c, i);
        if (REFRESH.equals(i.getAction())) refresh(c);
    }

    public static void updateAll(Context c) {
        Intent i = new Intent(c, WeatherWidget.class).setAction(REFRESH);
        c.sendBroadcast(i);
    }

    void refresh(Context ctx) {
        final Context c = ctx.getApplicationContext();
        final PendingResult pr = goAsync();
        new Thread(() -> {
            RemoteViews v = new RemoteViews(c.getPackageName(), R.layout.widget);
            wire(c, v);
            v.setTextViewText(R.id.place, Weather.placeName(c));
            try {
                JSONObject j = Weather.forecast(Weather.lat(c), Weather.lon(c));
                String tz = j.optString("timezone", "Europe/Berlin");
                JSONObject cu = j.getJSONObject("current");
                int code = cu.optInt("weather_code"), day = cu.optInt("is_day", 1);
                v.setTextViewText(R.id.icon, Weather.icon(code, day));
                v.setTextViewText(R.id.temp, Math.round(cu.getDouble("temperature_2m")) + "°");
                JSONObject d = j.getJSONObject("daily");
                v.setTextViewText(R.id.desc, Weather.text(code) + " · " + Math.round(d.getJSONArray("temperature_2m_min").getDouble(0)) + "° / " + Math.round(d.getJSONArray("temperature_2m_max").getDouble(0)) + "°");
                v.setTextViewText(R.id.rain, Weather.rainText(j, tz));
                JSONObject h = j.getJSONObject("hourly");
                JSONArray t = h.getJSONArray("time"), tt = h.getJSONArray("temperature_2m"), wc = h.getJSONArray("weather_code"), dy = h.getJSONArray("is_day"), pp = h.getJSONArray("precipitation_probability");
                long now = System.currentTimeMillis() / 1000; int k = 0;
                for (int i = 0; i < t.length() && k < H.length; i++) {
                    if (t.getLong(i) < now - 1800) continue;
                    if (k == 0 && t.getLong(i) < now) continue;
                    int p = pp.isNull(i) ? 0 : pp.getInt(i);
                    String s = Weather.hm(t.getLong(i), tz).substring(0, 2) + " Uhr\n" + Weather.icon(wc.getInt(i), dy.getInt(i)) + "\n" + Math.round(tt.getDouble(i)) + "°" + (p >= 20 ? "\n💧" + p + "%" : "\n ");
                    v.setTextViewText(H[k++], s);
                }
            } catch (Exception e) {
                v.setTextViewText(R.id.rain, "Keine Verbindung – tippe ⟳");
            }
            AppWidgetManager m = AppWidgetManager.getInstance(c);
            m.updateAppWidget(new ComponentName(c, WeatherWidget.class), v);
            pr.finish();
        }).start();
    }

    static void wire(Context c, RemoteViews v) {
        int fl = PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE;
        PendingIntent open = PendingIntent.getActivity(c, 1, new Intent(Intent.ACTION_VIEW, Uri.parse(Weather.APP_URL)), fl);
        v.setOnClickPendingIntent(R.id.root, open);
        PendingIntent cfg = PendingIntent.getActivity(c, 2, new Intent(c, MainActivity.class), fl);
        v.setOnClickPendingIntent(R.id.place, cfg);
        PendingIntent rf = PendingIntent.getBroadcast(c, 3, new Intent(c, WeatherWidget.class).setAction(REFRESH), fl);
        v.setOnClickPendingIntent(R.id.refresh, rf);
    }
}
