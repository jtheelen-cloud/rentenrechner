package de.theelen.apps;

import android.app.Activity;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.net.Uri;
import android.os.Bundle;
import android.util.Base64;
import android.view.View;
import android.webkit.JavascriptInterface;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.Toast;
import java.io.File;
import java.io.FileOutputStream;

/** Schlanke Hülle: zeigt die Web-App im Vollbild, Teilen/Kopieren/Dateien laufen über Android. */
public class MainActivity extends Activity {
    private WebView web;
    private String prefix;

    // Kleine Brücke für Funktionen, die eine eingebettete Webansicht sonst nicht kann
    private static final String BRIDGE =
        "(function(){if(window.__jt)return;window.__jt=1;var A=window.JTApp;" +
        "navigator.share=function(d){d=d||{};A.share([d.title,d.text,d.url].filter(Boolean).join('\\n'));return Promise.resolve()};" +
        "try{Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:function(t){A.copy(String(t));return Promise.resolve()},readText:function(){return Promise.reject(new Error('nicht erlaubt'))}}})}catch(e){}" +
        "var oc=HTMLAnchorElement.prototype.click;HTMLAnchorElement.prototype.click=function(){var a=this;" +
        "if(a.download&&/^(blob|data):/.test(a.href)){fetch(a.href).then(function(r){return r.blob()}).then(function(b){var f=new FileReader();" +
        "f.onload=function(){A.openFile(a.download,b.type||'application/octet-stream',String(f.result).split(',')[1])};f.readAsDataURL(b)});return}" +
        "return oc.call(a)};})();";

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        prefix = getString(R.string.url_prefix);
        web = new WebView(this);
        web.setBackgroundColor(Color.WHITE);
        // Ab Android 15 zeichnen Apps bis unter die Statusleiste: Rahmen mit Abstand zu den Systemleisten
        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(getColor(R.color.bar));
        root.addView(web);
        root.setOnApplyWindowInsetsListener((v, insets) -> {
            android.graphics.Insets b = insets.getInsets(android.view.WindowInsets.Type.systemBars() | android.view.WindowInsets.Type.ime());
            v.setPadding(b.left, b.top, b.right, b.bottom);
            return android.view.WindowInsets.CONSUMED;
        });
        setContentView(root);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setCacheMode(WebSettings.LOAD_DEFAULT);
        s.setMediaPlaybackRequiresUserGesture(true);
        s.setAllowFileAccess(false);
        s.setUserAgentString(s.getUserAgentString() + " TheelenApp/1");
        web.addJavascriptInterface(new Bridge(), "JTApp");
        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest r) {
                String u = r.getUrl().toString();
                if (u.startsWith(prefix)) return false;          // eigene Seiten in der App
                try { startActivity(new Intent(Intent.ACTION_VIEW, r.getUrl())); } catch (Exception e) { }
                return true;                                      // alles andere im Browser bzw. in der passenden App
            }
            @Override
            public void onPageFinished(WebView v, String url) { v.evaluateJavascript(BRIDGE, null); }
            @Override
            public void onReceivedError(WebView v, int code, String desc, String url) {
                if (url != null && url.startsWith(prefix))
                    v.loadData("<html><body style='font-family:sans-serif;padding:24px;text-align:center'><h2>Keine Verbindung</h2><p>Bitte Internet einschalten und die App neu öffnen.</p></body></html>", "text/html; charset=utf-8", "utf-8");
            }
        });
        if (state != null) web.restoreState(state); else web.loadUrl(getString(R.string.start_url));
    }

    @Override protected void onSaveInstanceState(Bundle out) { super.onSaveInstanceState(out); web.saveState(out); }

    @Override
    public void onBackPressed() { if (web.canGoBack()) web.goBack(); else super.onBackPressed(); }

    private class Bridge {
        @JavascriptInterface
        public void share(String text) {
            runOnUiThread(() -> {
                Intent i = new Intent(Intent.ACTION_SEND);
                i.setType("text/plain");
                i.putExtra(Intent.EXTRA_TEXT, text);
                startActivity(Intent.createChooser(i, "Teilen"));
            });
        }
        @JavascriptInterface
        public void copy(String text) {
            runOnUiThread(() -> {
                ClipboardManager cm = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
                cm.setPrimaryClip(ClipData.newPlainText("Text", text));
                Toast.makeText(MainActivity.this, "Kopiert", Toast.LENGTH_SHORT).show();
            });
        }
        @JavascriptInterface
        public void openFile(String name, String mime, String b64) {
            try {
                File dir = new File(getCacheDir(), "dateien");
                dir.mkdirs();
                String safe = name.replaceAll("[^A-Za-z0-9._-]", "_");
                File f = new File(dir, safe);
                try (FileOutputStream o = new FileOutputStream(f)) { o.write(Base64.decode(b64, Base64.DEFAULT)); }
                Uri uri = Uri.parse("content://" + getPackageName() + ".files/" + Uri.encode(safe));
                Intent i = new Intent(Intent.ACTION_VIEW);
                i.setDataAndType(uri, mime);
                i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                runOnUiThread(() -> {
                    try { startActivity(i); }
                    catch (Exception e) {
                        Intent s = new Intent(Intent.ACTION_SEND);
                        s.setType(mime); s.putExtra(Intent.EXTRA_STREAM, uri); s.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
                        startActivity(Intent.createChooser(s, "Öffnen mit"));
                    }
                });
            } catch (Exception e) {
                runOnUiThread(() -> Toast.makeText(MainActivity.this, "Datei konnte nicht geöffnet werden", Toast.LENGTH_LONG).show());
            }
        }
    }
}
