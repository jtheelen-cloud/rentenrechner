// App-Nutzung – Zähler für die Apps von Herrn Theelen
// In der Google-Tabelle „App-Nutzung“: Erweiterungen → Apps Script → alles ersetzen durch diesen Text.
// Den SCHLUESSEL unten selbst ausdenken (z. B. 12 Zeichen) und im Dashboard einmal eingeben.
const SCHLUESSEL = 'HIER-EIGENEN-SCHLUESSEL-EINTRAGEN';
const BLATT = 'Aufrufe';

function doGet(e) {
  const p = (e && e.parameter) || {};
  if (p.key !== undefined) {
    if (p.key !== SCHLUESSEL) return json({ error: 'key' });
    const werte = blatt().getDataRange().getValues().slice(1);
    const sum = {};
    werte.forEach(function (r) {
      const k = r[1] + '|' + r[2];
      const t = new Date(r[0]).getTime();
      const a = sum[k] || (sum[k] = { app: r[1], dev: r[2], n: 0, last: 0 });
      a.n++; if (t > a.last) a.last = t;
    });
    return json({ rows: Object.keys(sum).map(function (k) { return sum[k]; }), total: werte.length });
  }
  const app = String(p.a || '').toLowerCase().replace(/[^a-z]/g, '').slice(0, 12);
  const dev = String(p.d || '').toUpperCase().replace(/[^A-Z0-9-]/g, '').slice(0, 9);
  if (app && dev) blatt().appendRow([new Date(), app, dev]);
  return ContentService.createTextOutput('ok');
}

function blatt() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let b = ss.getSheetByName(BLATT);
  if (!b) { b = ss.insertSheet(BLATT); b.appendRow(['Zeit', 'App', 'Gerätenummer']); }
  return b;
}

function json(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}
