/* Offline-Unterstützung für Rentenrechner, BR-Nachschlagen, Wetterkarte und Ahnenspur.
   Immer zuerst aus dem Netz (damit Updates sofort ankommen), ohne Netz aus dem Zwischenspeicher. */
const CACHE = "jt-apps-v3";
const CORE = ["./", "index.html", "kennzahlen.json", "manifest.json", "icon-192.png",
              "br/", "br/index.html", "br/tarif.json", "br/manifest.json", "br/icon-192.png",
              "wetter/", "wetter/index.html", "wetter/manifest.json", "wetter/icon-192.png",
              "ahnen/", "ahnen/index.html", "ahnen/manifest.json", "ahnen/icon-192.png"];
self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => Promise.all(CORE.map(u => c.add(u).catch(() => {})))).then(() => self.skipWaiting()));
});
self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  const same = url.origin === self.location.origin;
  const fonts = url.hostname === "fonts.googleapis.com" || url.hostname === "fonts.gstatic.com";
  if (!same && !fonts) return;
  e.respondWith(
    fetch(req).then(res => {
      if (res && (res.ok || res.type === "opaque")) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); }
      return res;
    }).catch(() => caches.match(req, { ignoreSearch: true }).then(r => r || (req.mode === "navigate" ? caches.match(url.pathname.includes("/br/") ? "br/index.html" : url.pathname.includes("/wetter/") ? "wetter/index.html" : url.pathname.includes("/ahnen/") ? "ahnen/index.html" : "index.html") : undefined)))
  );
});
