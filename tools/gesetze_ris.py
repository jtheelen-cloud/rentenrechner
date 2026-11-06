"""Lädt die aktuellen Gesetzestexte aus dem amtlichen Rechtsinformationsportal des Bundes
(testphase.rechtsinformationen.bund.de, DigitalService des Bundes) und speichert sie als
br/texte/<id>.json für den Offline-Betrieb der BR-App."""
import json, re, sys, os, datetime, urllib.request, urllib.parse, urllib.error
import xml.etree.ElementTree as ET
B = "https://testphase.rechtsinformationen.bund.de"
HEUTE = datetime.date.today().isoformat()
ABK = {"bgb":"BGB","sgb_9_2018":"SGB IX","a_g":"AÜG","arbgg":"ArbGG","mitbestg":"MitbestG","hinschg":"HinSchG",
       "tvg":"TVG","gewo":"GewO","muschg_2018":"MuSchG","bdsg_2018":"BDSG","burlg":"BUrlG","entgfg":"EntgFG"}
log = open("tools/gesetze_log.txt", "w")
def L(*a): print(*a); print(*a, file=log); log.flush()
def get(u, raw=False):
    r = urllib.request.urlopen(urllib.request.Request(B + u if u.startswith("/") else u,
        headers={"User-Agent": "BR-Nachschlagen (GitHub Pages)", "Accept": "application/json"}), timeout=60)
    d = r.read(); return d if raw else json.loads(d)
NAMEN = {"bgb":["Bürgerliches Gesetzbuch"],"sgb_9_2018":["Rehabilitation und Teilhabe von Menschen mit Behinderungen","Neuntes Buch Sozialgesetzbuch"],
  "a_g":["Arbeitnehmerüberlassung","Gesetz zur Regelung der Arbeitnehmerüberlassung"],"tvg":["Tarifvertragsgesetz"],"arbgg":["Arbeitsgerichtsgesetz"],
  "gewo":["Gewerbeordnung"],"mitbestg":["Gesetz über die Mitbestimmung der Arbeitnehmer"],"hinschg":["Hinweisgeberschutzgesetz","Schutz hinweisgebender Personen"]}
def norm(x): return re.sub(r"[^a-z0-9äöüß]", "", (x or "").lower())
def ok(it, slug, kurz, name):
    ab = {norm(it.get("abbreviation")), norm(it.get("risAbbreviation")), norm(it.get("alternateName"))}
    want = {norm(ABK.get(slug, kurz)), norm(kurz)}
    return bool(ab & want) or norm(it.get("name")) == norm(name)
def find(slug, kurz, name):
    seen = []
    qs = [{"abbreviation": ABK.get(slug, kurz)}, {"risAbbreviation": ABK.get(slug, kurz)}, {"abbreviation": kurz},
          {"searchTerm": ABK.get(slug, kurz)}, {"searchTerm": name}] + [{"searchTerm": n} for n in NAMEN.get(slug, [])]
    for q in qs:
        q.update({"mostRelevantOn": HEUTE, "size": 10})
        try: j = get("/v1/legislation?" + urllib.parse.urlencode(q))
        except Exception as e: seen.append(("ERR", str(e)[:80])); continue
        for m in j.get("member", []):
            it = m["item"]; seen.append((it.get("abbreviation"), it.get("risAbbreviation"), (it.get("name") or "")[:70]))
            if ok(it, slug, kurz, name) or norm(it.get("name")) in {norm(n) for n in NAMEN.get(slug, [])}:
                return it
    L("  Kandidaten", slug, json.dumps(list(dict.fromkeys(map(tuple, seen)))[:25], ensure_ascii=False))
    return None
def ln(e): return e.tag.rsplit("}", 1)[-1]
SKIP = {"authorialNote", "num", "heading", "subheading", "ref_skip"}
def txt(e):
    s = []
    def w(x):
        if ln(x) == "authorialNote": 
            if x.tail: s.append(x.tail); 
            return
        if x.text: s.append(x.text)
        for c in x: w(c)
        if x.tail: s.append(x.tail)
    if e.text: s.append(e.text)
    for c in e: w(c)
    return re.sub(r"\s+", " ", "".join(s)).strip()
def child(e, name):
    for c in e:
        if ln(c) == name: return c
def lines(e, depth=0, prefix=""):
    out = []
    for c in e:
        t = ln(c)
        if t in SKIP: continue
        if t in ("p", "td", "th"):
            s = txt(c)
            if s: out.append((depth, (prefix + " " + s).strip() if prefix else s)); prefix = ""
        elif t in ("tr",):
            s = " | ".join(txt(x) for x in c if txt(x))
            if s: out.append((depth, s))
        else:
            n = child(c, "num")
            sub = lines(c, depth + (1 if n is not None and t in ("point","item","list","indent","alinea") else 0),
                        txt(n) if n is not None else "")
            if prefix and sub: sub[0] = (sub[0][0], prefix + " " + sub[0][1]); prefix = ""
            out += sub
    if prefix: out.append((depth, prefix))
    return out
def parse(xml, nums_wanted=None):
    root = ET.fromstring(xml)
    arts = []
    for a in root.iter():
        if ln(a) != "article": continue
        n = child(a, "num"); h = child(a, "heading")
        num = txt(n) if n is not None else ""
        m = re.match(r"(§§?|Art\.?|Artikel)\s*([\dA-Za-z]+)", num)
        key = m.group(2) if m else num
        if nums_wanted and not nums_wanted(key): continue
        body = [("  " * d) + s for d, s in lines(a)]
        arts.append([key, num, txt(h) if h is not None else "", body])
    return arts
def bgb_filter(cur):
    want = {x[0] for x in cur}
    def f(k):
        mm = re.match(r"(\d+)", k); n = int(mm.group(1)) if mm else 0
        return k in want or 611 <= n <= 630
    return f

# ---------- Ersatzquelle: Open Legal Data (spiegelt gesetze-im-internet.de) ----------
import html as _html, time
from html.parser import HTMLParser
O = "https://de.openlegaldata.io/api"
OLD_CODES = {"tvg":["TVG"],"mitbestg":["MitbestG"],"bgb":["BGB"],"sgb_9_2018":["SGB 9","SGB IX","SGB 9 2018"],"a_g":["AÜG"],"arbgg":["ArbGG"],"gewo":["GewO"],"hinschg":["HinSchG"]}
class _P(HTMLParser):
    def __init__(s): super().__init__(); s.out=[]; s.cur=None; s.depth=0; s.skip=0
    def _new(s, pre=""): s._flush(); s.cur=[s.depth, pre]
    def _flush(s):
        if s.cur is not None:
            t=re.sub(r"\s+"," ",s.cur[1]).strip()
            if t: s.out.append(("  "*s.cur[0])+t)
        s.cur=None
    def handle_starttag(s,t,a):
        t=t.lower()
        if t in ("sup","fnr"): s.skip+=1; return
        if t=="dl": s._flush(); s.depth+=1
        elif t=="dt": s._new("")
        elif t=="dd": pass
        elif t in ("p","tr","row"): s._new("")
        elif t in ("entry","td"): 
            if s.cur is None: s._new("")
            else: s.cur[1]+=" | "
        elif t=="br": 
            if s.cur is not None: s.cur[1]+=" "
    def handle_endtag(s,t):
        t=t.lower()
        if t in ("sup","fnr"): s.skip=max(0,s.skip-1); return
        if t=="dl": s._flush(); s.depth=max(0,s.depth-1)
        elif t=="dt":
            if s.cur is not None: s.cur[1]+=" "
        elif t in ("p","tr","row"): s._flush()
    def handle_data(s,d):
        if s.skip: return
        if s.cur is None: s._new("")
        s.cur[1]+=d
def html_lines(h):
    p=_P(); p.feed(h); p._flush(); return p.out
def oget(u):
    for k in range(1):
        try:
            time.sleep(1.1); return get(u)
        except urllib.error.HTTPError as e:
            if e.code == 429 and k < 7: time.sleep(45 + 15 * k); continue
            raise
        except Exception:
            if k >= 3: raise
            time.sleep(5)
class Budget(Exception): pass
OLD_LEFT = [int(os.environ.get("OLD_BUDGET", "45"))]
def oreq(u):
    if OLD_LEFT[0] <= 0: raise Budget()
    OLD_LEFT[0] -= 1
    try:
        time.sleep(1.2); return get(u)
    except urllib.error.HTTPError as e:
        if e.code == 429: OLD_LEFT[0] = 0; raise Budget()
        raise
FILTER = {"sgb_9_2018": lambda n: 151 <= n <= 241, "gewo": lambda n: 105 <= n <= 110}
def old_fetch(g, want=None):
    """Lädt ein Gesetz von Open Legal Data schrittweise; Fortschritt in tools/olcache/<slug>.json."""
    slug = g["slug"]; os.makedirs("tools/olcache", exist_ok=True)
    cp = f"tools/olcache/{slug}.json"
    c = json.load(open(cp)) if os.path.exists(cp) else {}
    curated = {x[0] for x in g["p"]}
    def wanted(key):
        if want: return want(key)
        f = FILTER.get(slug)
        if not f: return True
        mm = re.match(r"(\d+)", key); n = int(mm.group(1)) if mm else 0
        return key in curated or f(n)
    try:
        if not c.get("book") or c.get("checked") != HEUTE:
            book = None
            for code in OLD_CODES.get(slug, [g["kurz"]]):
                j = oreq(O + "/law_books/?" + urllib.parse.urlencode({"code": code}))
                bs = [b for b in j.get("results", []) if b.get("latest")]
                if bs: book = bs[0]; break
            if not book: L("  OLD: kein Buch", slug); return None
            if c.get("book", {}).get("id") != book["id"] or c.get("book", {}).get("revision_date") != book.get("revision_date"):
                c = {"book": book, "list": None, "sec": {}}
            c["checked"] = HEUTE
        book = c["book"]
        if not c.get("list"):
            items, u = [], O + "/laws/?" + urllib.parse.urlencode({"book_id": book["id"], "limit": 500})
            while u:
                j = oreq(u)
                if j.get("results") and not all(x.get("book") == book["id"] for x in j["results"]):
                    L("  OLD: Filter geht nicht", slug); return None
                items += [[x["id"], (x.get("section") or "").strip(), (x.get("title") or "").strip(), x.get("order") or 0] for x in j.get("results", [])]
                u = j.get("next")
            items.sort(key=lambda x: (x[3], x[0]))
            lst = []
            for lid, sec, title, _ in items:
                m = re.match(r"(§§?|Art\.?|Artikel)\s*([\dA-Za-z]+)", sec)
                if m and wanted(m.group(2)): lst.append([lid, m.group(2), sec, title])
            c["list"] = lst
        for lid, key, sec, title in c["list"]:
            if str(lid) in c["sec"]: continue
            d = oreq(O + f"/laws/{lid}/")
            c["sec"][str(lid)] = html_lines(d.get("content") or "")
    except Budget:
        json.dump(c, open(cp, "w"), ensure_ascii=False)
        done = len(c.get("sec", {})); tot = len(c.get("list") or [])
        L(f"  OLD: Abruf-Limit erreicht bei {slug}, Fortschritt {done}/{tot or '?'} – geht beim nächsten Lauf weiter"); return None
    json.dump(c, open(cp, "w"), ensure_ascii=False)
    arts = [[key, sec, title, c["sec"][str(lid)]] for lid, key, sec, title in c["list"]]
    return {"id": g["id"], "kurz": book.get("code"), "name": book.get("title"), "eli": "", "stand": book.get("revision_date", ""),
            "abgerufen": HEUTE, "url": "https://www.gesetze-im-internet.de/" + slug + "/", "quelle": "Open Legal Data (Daten von gesetze-im-internet.de)", "p": arts}

os.makedirs("br/texte", exist_ok=True)
def save(g, doc):
    json.dump(doc, open(f"br/texte/{g['id']}.json", "w"), ensure_ascii=False, separators=(",", ":"))
    index["gesetze"][g["id"]] = {"stand": doc["stand"], "n": len(doc["p"]), "name": doc["name"], "kurz": doc["kurz"], "quelle": doc["quelle"]}
    L("OK", g["slug"], doc["kurz"], "|", (doc["name"] or "")[:60], "| Paragrafen:", len(doc["p"]), "| Stand", doc["stand"], "|", doc["quelle"],
      "| Bytes", os.path.getsize(f"br/texte/{g['id']}.json"))
liste = json.load(open("tools/gesetze_liste.json"))
index = {"stand": HEUTE, "gesetze": {}}
try: index["gesetze"] = json.load(open("br/texte/index.json")).get("gesetze", {})
except Exception: pass
PRIO = ["tvg", "hinschg", "a_g", "mitbestg", "arbgg", "gewo", "sgb_9_2018", "bgb"]
spaeter = []
fehler = 0
for g in liste:
    slug, kurz, name = g["slug"], g["kurz"], g["name"].split(" (")[0]
    try:
        it = find(slug, kurz, name)
        doc = None
        if it:
            if not it.get("encoding"): it = get(it["@id"])
            xmlu = [e["contentUrl"] for e in it.get("encoding", []) if e.get("encodingFormat") == "application/xml"]
            if xmlu:
                xml = get(xmlu[0], raw=True)
                arts = parse(xml, bgb_filter(g["p"]) if slug == "bgb" else None)
                stand = re.search(r"/(\d{4}-\d{2}-\d{2})/regelungstext", xmlu[0])
                if arts:
                    doc = {"id": g["id"], "kurz": it.get("abbreviation") or kurz, "name": it.get("name"), "eli": it.get("legislationIdentifier"),
                           "stand": stand.group(1) if stand else "", "abgerufen": HEUTE, "url": B + xmlu[0].replace(".xml", ".html"),
                           "quelle": "Rechtsinformationsportal des Bundes", "p": arts}
        if not doc:
            if slug in PRIO: spaeter.append(g)
            else: L("PORTAL-FEHLER", slug, "– letzte gespeicherte Fassung bleibt"); fehler += 1
            continue
        save(g, doc)
    except Exception as e:
        L("FEHLER", slug, repr(e)[:300]); fehler += 1
spaeter.sort(key=lambda g: PRIO.index(g["slug"]) if g["slug"] in PRIO else 99)
for g in spaeter:
    try:
        doc = old_fetch(g, bgb_filter(g["p"]) if g["slug"] == "bgb" else None)
        if doc and doc["p"]: save(g, doc)
        else:
            fehler += 1
            if not os.path.exists(f"br/texte/{g['id']}.json"): L("NOCH NICHT DA", g["slug"], "(App öffnet Originaltext)")
            else: L("BEHALTEN", g["slug"], "(letzte gespeicherte Fassung)")
    except Exception as e:
        L("FEHLER", g["slug"], repr(e)[:200]); fehler += 1
json.dump(index, open("br/texte/index.json", "w"), ensure_ascii=False, indent=1)
for f in os.listdir("br/texte"):
    if f.endswith(".json") and f != "index.json" and f[:-5] not in index["gesetze"]:
        os.remove("br/texte/" + f); L("ENTFERNT (nicht geprüft)", f)
L("FERTIG, Fehler:", fehler)
