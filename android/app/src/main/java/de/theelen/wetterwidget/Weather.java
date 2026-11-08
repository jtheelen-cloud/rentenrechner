package de.theelen.wetterwidget;

import android.content.Context;
import android.content.SharedPreferences;
import org.json.JSONArray;
import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.net.URLEncoder;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;

/** Holt die Wetterdaten bei Open-Meteo (kostenlos, ohne Anmeldung). */
public class Weather {
    public static final String APP_URL = "https://jtheelen-cloud.github.io/rentenrechner/wetter/";

    public static SharedPreferences prefs(Context c) { return c.getSharedPreferences("wetter", Context.MODE_PRIVATE); }
    public static String placeName(Context c) { return prefs(c).getString("n", "Mülheim an der Ruhr"); }
    public static double lat(Context c) { return Double.parseDouble(prefs(c).getString("lat", "51.427")); }
    public static double lon(Context c) { return Double.parseDouble(prefs(c).getString("lon", "6.883")); }
    public static void savePlace(Context c, String n, double lat, double lon) {
        prefs(c).edit().putString("n", n).putString("lat", String.valueOf(lat)).putString("lon", String.valueOf(lon)).apply();
    }

    public static String get(String u) throws Exception {
        HttpURLConnection con = (HttpURLConnection) new URL(u).openConnection();
        con.setConnectTimeout(8000); con.setReadTimeout(8000);
        if (con.getResponseCode() != 200) throw new Exception("HTTP " + con.getResponseCode());
        BufferedReader r = new BufferedReader(new InputStreamReader(con.getInputStream(), "UTF-8"));
        StringBuilder sb = new StringBuilder(); String l;
        while ((l = r.readLine()) != null) sb.append(l);
        r.close(); return sb.toString();
    }

    public static JSONArray search(String q) throws Exception {
        JSONObject j = new JSONObject(get("https://geocoding-api.open-meteo.com/v1/search?count=15&language=de&format=json&name=" + URLEncoder.encode(q, "UTF-8")));
        return j.optJSONArray("results") == null ? new JSONArray() : j.getJSONArray("results");
    }

    public static JSONObject forecast(double lat, double lon) throws Exception {
        return new JSONObject(get("https://api.open-meteo.com/v1/forecast?latitude=" + lat + "&longitude=" + lon
            + "&current=temperature_2m,weather_code,is_day"
            + "&minutely_15=precipitation&forecast_minutely_15=9"
            + "&hourly=temperature_2m,weather_code,is_day,precipitation_probability&forecast_hours=8"
            + "&daily=temperature_2m_max,temperature_2m_min&forecast_days=1"
            + "&timezone=auto&timeformat=unixtime"));
    }

    public static String icon(int c, int day) {
        if (day == 0 && (c == 0 || c == 1)) return "🌙";
        if (c == 0) return "☀️"; if (c == 1) return "🌤️"; if (c == 2) return day == 0 ? "☁️" : "⛅"; if (c == 3) return "☁️";
        if (c == 45 || c == 48) return "🌫️"; if (c >= 51 && c <= 57) return "🌦️"; if (c >= 61 && c <= 67) return "🌧️";
        if (c >= 71 && c <= 77) return "🌨️"; if (c >= 80 && c <= 82) return "🌦️"; if (c == 85 || c == 86) return "🌨️"; if (c >= 95) return "⛈️";
        return "❔";
    }

    public static String text(int c) {
        if (c == 0) return "Klar"; if (c == 1) return "Überwiegend klar"; if (c == 2) return "Teilweise bewölkt"; if (c == 3) return "Bedeckt";
        if (c == 45 || c == 48) return "Nebel"; if (c >= 51 && c <= 57) return "Nieselregen"; if (c >= 61 && c <= 67) return "Regen";
        if (c >= 71 && c <= 77) return "Schnee"; if (c >= 80 && c <= 82) return "Schauer"; if (c == 85 || c == 86) return "Schneeschauer"; if (c >= 95) return "Gewitter";
        return "";
    }

    public static String hm(long unix, String tz) {
        SimpleDateFormat f = new SimpleDateFormat("HH:mm", Locale.GERMANY);
        f.setTimeZone(TimeZone.getTimeZone(tz)); return f.format(new Date(unix * 1000));
    }

    /** Regen in den nächsten 2 Stunden als kurzer Satz. */
    public static String rainText(JSONObject j, String tz) throws Exception {
        JSONObject m = j.getJSONObject("minutely_15");
        JSONArray t = m.getJSONArray("time"), p = m.getJSONArray("precipitation");
        long now = System.currentTimeMillis() / 1000;
        int start = -1, end = -1; double max = 0;
        for (int i = 0; i < t.length(); i++) {
            if (t.getLong(i) + 900 < now) continue;
            double v = p.isNull(i) ? 0 : p.getDouble(i);
            if (v >= 0.05) { if (start < 0) start = i; end = i; max = Math.max(max, v); }
        }
        if (start < 0) return "Kein Regen in den nächsten 2 Std.";
        String st = max * 4 < 2.5 ? "leichter Regen" : max * 4 < 8 ? "Regen" : "starker Regen";
        String from = t.getLong(start) <= now ? "jetzt" : "ab " + hm(t.getLong(start), tz);
        if (end < t.length() - 1) return st.substring(0, 1).toUpperCase() + st.substring(1) + " " + from + " bis " + hm(t.getLong(end) + 900, tz);
        return st.substring(0, 1).toUpperCase() + st.substring(1) + " " + from;
    }
}
