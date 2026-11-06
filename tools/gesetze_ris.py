"""Lädt die aktuellen Gesetzestexte aus dem amtlichen Rechtsinformationsportal des Bundes
(testphase.rechtsinformationen.bund.de, DigitalService des Bundes) und speichert sie als
br/texte/<id>.json für den Offline-Betrieb der BR-App."""
import json, re, sys, os, datetime, urllib.request, urllib.parse
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
def find(slug, kurz, name):
    tries = [("abbreviation", ABK.get(slug, kurz)), ("risAbbreviation", ABK.get(slug, kurz)), ("abbreviation", kurz)]
    for key, val in tries:
        j = get("/v1/legislation?" + urllib.parse.urlencode({key: val, "mostRelevantOn": HEUTE, "size": 5}))
        for m in j.get("member", []):
            it = m["item"]
            if it.get("legislationLegalForce") == "InForce" or True:
                return it
    j = get("/v1/legislation?" + urllib.parse.urlencode({"searchTerm": name, "mostRelevantOn": HEUTE, "size": 5}))
    for m in j.get("member", []):
        if m["item"].get("name", "").lower() == name.lower(): return m["item"]
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
os.makedirs("br/texte", exist_ok=True)
liste = json.load(open("tools/gesetze_liste.json"))
index = {"stand": HEUTE, "quelle": "Rechtsinformationsportal des Bundes (rechtsinformationen.bund.de)", "gesetze": {}}
fehler = 0
for g in liste:
    slug, kurz, name = g["slug"], g["kurz"], g["name"].split(" (")[0]
    try:
        it = find(slug, kurz, name)
        if not it: L("NICHT GEFUNDEN", slug, kurz); fehler += 1; continue
        if not it.get("encoding"): it = get(it["@id"])
        xmlu = [e["contentUrl"] for e in it.get("encoding", []) if e.get("encodingFormat") == "application/xml"]
        if not xmlu: L("KEIN XML", slug, it.get("@id")); fehler += 1; continue
        xml = get(xmlu[0], raw=True)
        if slug == "sgb_9_2018" and len(sys.argv) > 1: open("tools/debug_sgb9.xml", "wb").write(xml[:20000])
        if slug == "betrvg": open("tools/debug_betrvg.xml", "wb").write(xml[:15000])
        arts = parse(xml, bgb_filter(g["p"]) if slug == "bgb" else None)
        stand = re.search(r"/(\d{4}-\d{2}-\d{2})/regelungstext", xmlu[0])
        doc = {"id": g["id"], "kurz": it.get("abbreviation") or kurz, "name": it.get("name"), "eli": it.get("legislationIdentifier"),
               "stand": stand.group(1) if stand else "", "abgerufen": HEUTE,
               "url": B + xmlu[0].replace(".xml", ".html"), "p": arts}
        if not arts: L("LEER", slug); fehler += 1; continue
        json.dump(doc, open(f"br/texte/{g['id']}.json", "w"), ensure_ascii=False, separators=(",", ":"))
        index["gesetze"][g["id"]] = {"stand": doc["stand"], "n": len(arts), "name": doc["name"], "kurz": doc["kurz"]}
        L("OK", slug, doc["kurz"], "|", doc["name"][:60], "| Paragrafen:", len(arts), "| Stand", doc["stand"],
          "| Bytes", os.path.getsize(f"br/texte/{g['id']}.json"))
    except Exception as e:
        L("FEHLER", slug, repr(e)[:300]); fehler += 1
json.dump(index, open("br/texte/index.json", "w"), ensure_ascii=False, indent=1)
L("FERTIG, Fehler:", fehler)
