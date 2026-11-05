"""Lädt Gesetze von gesetze-im-internet.de (XML) und schreibt sie als JSON nach br/data/."""
import io, json, re, sys, zipfile, datetime, urllib.request, xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "br" / "data"

def para_num(enbez):
    m = re.search(r"(\d+)", enbez or "")
    return int(m.group(1)) if m else None

def txt(el):
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()

def render_block(el, out):
    tag = el.tag
    if tag == "DL":
        items = list(el)
        i = 0
        while i < len(items):
            dt = items[i]
            if dt.tag == "DT":
                dd = items[i + 1] if i + 1 < len(items) else None
                sub = []
                if dd is not None:
                    for c in dd:
                        if c.tag == "DL":
                            render_block(c, sub)
                        else:
                            t = txt(c)
                            if t: sub.append(t)
                    if not len(dd) and txt(dd): sub.append(txt(dd))
                first = sub[0] if sub else ""
                out.append(f"{txt(dt)} {first}".strip())
                out.extend("   " + s for s in sub[1:])
                i += 2
            else:
                t = txt(dt)
                if t: out.append(t)
                i += 1
    elif tag in ("P", "LA", "Title", "Subtitle"):
        head, rest = [], []
        if el.text and el.text.strip(): head.append(el.text)
        for c in el:
            if c.tag == "DL":
                if head: out.append(re.sub(r"\s+", " ", "".join(head)).strip()); head = []
                render_block(c, out)
                if c.tail and c.tail.strip(): head.append(c.tail)
            elif c.tag == "BR":
                if head: out.append(re.sub(r"\s+", " ", "".join(head)).strip()); head = []
                if c.tail and c.tail.strip(): head.append(c.tail)
            elif c.tag in ("FnR",):
                if c.tail: head.append(c.tail)
            else:
                head.append("".join(c.itertext()) + (c.tail or ""))
        if head:
            t = re.sub(r"\s+", " ", "".join(head)).strip()
            if t: out.append(t)
    elif tag in ("table", "Table"):
        for row in el.iter("row"):
            cells = [txt(e) for e in row if e.tag == "entry"]
            if any(cells): out.append(" | ".join(cells))
    else:
        t = txt(el)
        if t: out.append(t)

def parse(xml_bytes, law):
    root = ET.fromstring(xml_bytes)
    normen, stand, gl = [], "", ""
    for norm in root.iter("norm"):
        md = norm.find("metadaten")
        if md is None: continue
        for s in md.findall("standangabe"):
            k = s.findtext("standkommentar") or ""
            if s.findtext("standtyp") == "Stand" or (not stand and k):
                stand = re.sub(r"\s+", " ", k).strip()
        g = md.find("gliederungseinheit")
        if g is not None:
            gl = " ".join(x for x in [g.findtext("gliederungsbez"), g.findtext("gliederungstitel")] if x).strip()
        enbez = (md.findtext("enbez") or "").strip()
        if not enbez or enbez in ("Inhaltsübersicht", "Eingangsformel", "Schlußformel", "Schlussformel"):
            continue
        n = para_num(enbez)
        if law.get("von") and (n is None or not (law["von"] <= n <= law["bis"])):
            continue
        titel_el = md.find("titel")
        titel = txt(titel_el) if titel_el is not None else ""
        content = norm.find("textdaten/text/Content")
        lines = []
        if content is not None:
            for c in content:
                render_block(c, lines)
        text = "\n".join(l for l in lines if l)
        if not text and "(weggefallen)" not in titel:
            text = "(weggefallen)" if "weggefallen" in enbez + titel else ""
        normen.append({"p": enbez, "t": titel, "g": gl, "x": text})
    return normen, stand

def fetch(slug):
    import subprocess
    url = f"https://www.gesetze-im-internet.de/{slug}/xml.zip"
    r = subprocess.run(["curl", "-sSfL", "--max-time", "90", "--connect-timeout", "20", "--retry", "2",
                        "-A", "Mozilla/5.0 (BR-Nachschlagen)", url], capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"curl {r.returncode}: {r.stderr.decode(errors='ignore').strip()[:120]}")
    z = zipfile.ZipFile(io.BytesIO(r.stdout))
    name = next(n for n in z.namelist() if n.endswith(".xml"))
    return z.read(name), url.replace("/xml.zip", "/")

def main():
    laws = json.load(open(ROOT / "tools" / "gesetze.json", encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    index, errors = [], []
    old = {}
    if (OUT / "index.json").exists():
        old = {l["id"]: l for l in json.load(open(OUT / "index.json", encoding="utf-8")).get("gesetze", [])}
    from concurrent.futures import ThreadPoolExecutor
    def work(law):
        for slug in law["slugs"]:
            try:
                xml, src = fetch(slug)
                normen, stand = parse(xml, law)
                if not normen: raise ValueError("keine Paragrafen")
                json.dump({"id": law["id"], "kurz": law["kurz"], "name": law["name"], "quelle": src, "stand": stand, "normen": normen},
                          open(OUT / f"{law['id']}.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
                print(f"OK   {law['kurz']:<22} {slug:<16} {len(normen)} Normen", flush=True)
                return {"id": law["id"], "kurz": law["kurz"], "name": law["name"], "quelle": src, "stand": stand, "anzahl": len(normen)}
            except Exception as e:
                print(f"FAIL {law['kurz']:<22} {slug:<16} {e}", flush=True)
        return None
    with ThreadPoolExecutor(max_workers=6) as ex:
        results = list(ex.map(work, laws))
    for law, res in zip(laws, results):
        if res: index.append(res)
        else:
            errors.append(law["kurz"])
            if law["id"] in old and (OUT / f"{law['id']}.json").exists():
                index.append(old[law["id"]])
    index.sort(key=lambda l: [x["id"] for x in laws].index(l["id"]))
    meta = {"abgerufen": datetime.date.today().isoformat(), "gesetze": index, "fehler": errors}
    json.dump(meta, open(OUT / "index.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print("Fehler:", errors)

if __name__ == "__main__":
    main()
