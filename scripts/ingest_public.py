"""Ingest Ventora's PUBLIC estate (pages + technical PDFs) into the digital-experience KB.

  ../../.venv/bin/python scripts/ingest_public.py --build      # build data/corpus-manifest.json from scratchpad url lists
  ../../.venv/bin/python scripts/ingest_public.py --limit 3    # smoke test
  ../../.venv/bin/python scripts/ingest_public.py              # full run (idempotent, resumable)
  ../../.venv/bin/python scripts/ingest_public.py --status     # processing status
  ../../.venv/bin/python scripts/ingest_public.py --purge      # 30-second reset

Every resource gets labels (brand, doctype) + origin.url so the app can hard-scope and cite.
"""
import argparse, hashlib, json, re, sys, time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent
URLDIR = Path("/private/tmp/claude-502/-Users-jsanders-Claude/45d0fd63-3bff-4964-9e34-19621f86714a/scratchpad/ventora-urls")
CORPUS = ROOT / "data" / "corpus-manifest.json"
INGESTED = ROOT / "data" / "kb-manifest.json"
UA = {"User-Agent": "Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/128 Safari/537.36"}

def env():
    e = {}
    for line in (ROOT / ".env").read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, _, v = line.partition("="); e[k.strip()] = v.strip()
    return e
E = env()
KBURL = f"https://{E['ARAG_ZONE']}.rag.progress.cloud/api/v1/kb/{E['ARAG_KB_ID']}"
H = {"x-nuclia-serviceaccount": f"Bearer {E['ARAG_API_KEY']}"}
HJ = {**H, "content-type": "application/json"}

BRAND = {"ventora": "Ventora", "breezway": "Breezway", "stegbar": "Stegbar", "alwindows": "A&L Windows & Doors",
         "trend": "Trend Windows & Doors", "corinthian": "Corinthian Doors", "aneeta": "Aneeta", "regency": "Regency",
         "ventoraglass": "Ventora Glass"}
HOST2BRAND = {"ventora.com.au": "ventora", "breezway.com.au": "breezway", "stegbar.com.au": "stegbar", "alwindows.com.au": "alwindows",
              "trendwindows.com.au": "trend", "corinthian.com.au": "corinthian", "aneetawindows.com.au": "aneeta",
              "regencyscreens.com.au": "regency", "ventoraglass.com.au": "ventoraglass"}
PRIORITY = [  # (regex, doctype, weight) - higher weight = ingest first
    (r"warrant", "warranty", 10), (r"(bal|bushfire)", "compliance", 9), (r"(wers|energy|thermal|glazing|climate)", "energy", 9),
    (r"(acoustic|cyclone|fall[-_ ]?prevent|pool|safety|compliance|standard|as[-_ ]?\d{4}|ncc)", "compliance", 9),
    (r"(install|building[-_ ]in|electrician)", "installation", 8), (r"(care|maintenance|clean)", "care", 8),
    (r"(technical|spec|design[-_ ]manual|tb_|bulletin|test[-_ ]report|performance)", "technical", 8),
    (r"(faq|support|handing|spare|parts|hardware)", "support", 7), (r"(brochure|catalog|ideas|whitepaper|cpd)", "brochure", 6),
    (r"(products?/|window|door|louvre|screen|wardrobe|splashback|mirror|glass|series|range)", "product", 5),
    (r"(about|our-|story|values|contact|credit|trade|specification|architect|commercial)", "corporate", 4),
]
def classify(u):
    for rx, dt, w in PRIORITY:
        if re.search(rx, u, re.I): return dt, w
    return "page", 2

def build():
    cur = json.load(open(URLDIR / "curated.json")); pdfs = json.load(open(URLDIR / "pdfs.json"))
    items = []
    for b, urls in cur.items():
        scored = sorted(((classify(u)[1], u) for u in urls), reverse=True)
        cap = {"corinthian": 45, "stegbar": 50, "trend": 45}.get(b, 40) if b != "ventora" else 26
        for w, u in scored[:cap]:
            dt, _ = classify(u); items.append({"url": u, "kind": "link", "brand": b, "doctype": dt, "weight": w})
    for p, src in pdfs.items():
        host = re.match(r"https?://(?:www\.|cdn\.)?([^/]+)", src).group(1)
        b = HOST2BRAND.get(host, "ventora"); dt, w = classify(p)
        items.append({"url": p, "kind": "file", "brand": b, "doctype": dt, "weight": w + 1, "found_on": src})
    seen, out = set(), []
    for it in sorted(items, key=lambda x: -x["weight"]):
        if it["url"] in seen: continue
        seen.add(it["url"]); it["id"] = hashlib.sha1(it["url"].encode()).hexdigest()[:12]; out.append(it)
    CORPUS.write_text(json.dumps(out, indent=1))
    from collections import Counter
    print(len(out), "items;", Counter(i["kind"] for i in out), Counter(i["brand"] for i in out)); print(Counter(i["doctype"] for i in out))

def title_from(u):
    t = re.sub(r"[?#].*$", "", u).rstrip("/").split("/")[-1]; t = re.sub(r"\.pdf$", "", t, flags=re.I)
    return re.sub(r"[-_]+", " ", t).strip().title() or u

def create_link(it):
    body = {"title": title_from(it["url"]), "slug": "vx-" + it["id"],
            "links": {"link": {"uri": it["url"], "css_selector": "main, article, .main-content, #MainContent, body"}},
            "origin": {"url": it["url"], "source_id": "ventora-public"},
            "usermetadata": {"classifications": [{"labelset": "brand", "label": BRAND[it["brand"]]}, {"labelset": "doctype", "label": it["doctype"]}]}}
    r = requests.post(f"{KBURL}/resources", headers=HJ, json=body, timeout=60)
    if r.status_code == 409:  # slug exists
        return "DUP"
    r.raise_for_status(); return r.json()["uuid"]

def create_file(it):
    import subprocess
    cp = subprocess.run(["curl", "-s", "-L", "--max-time", "90", "-A", UA["User-Agent"], "-e", it.get("found_on", it["url"]), it["url"]], capture_output=True)
    content = cp.stdout
    if not content[:5].startswith(b"%PDF"): print("  skip (not a pdf)", it["url"][:90]); return "SKIP"
    fname = re.sub(r"[?#].*$", "", it["url"]).split("/")[-1]
    r = requests.post(f"{KBURL}/upload", headers={**H, "X-Filename": fname, "Content-Type": "application/pdf", "X-Md5": hashlib.md5(content).hexdigest()},
                      data=content, timeout=300)
    if r.status_code == 409: return "DUP"
    r.raise_for_status(); rid = r.json()["uuid"]
    patch = {"title": title_from(it["url"]), "origin": {"url": it["url"], "source_id": "ventora-public"},
             "usermetadata": {"classifications": [{"labelset": "brand", "label": BRAND[it["brand"]]}, {"labelset": "doctype", "label": it["doctype"]}]}}
    requests.patch(f"{KBURL}/resource/{rid}", headers=HJ, json=patch, timeout=60)
    return rid

def ensure_labelsets():
    for ls, labels in {"brand": list(BRAND.values()), "doctype": sorted({d for _, d, _ in PRIORITY} | {"page"})}.items():
        requests.post(f"{KBURL}/labelset/{ls}", headers=HJ, json={"title": ls, "kind": ["RESOURCES"], "labels": [{"title": l} for l in labels]}, timeout=30)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--build", action="store_true"); ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--status", action="store_true"); ap.add_argument("--purge", action="store_true"); a = ap.parse_args()
    if a.build: return build()
    if a.status:
        print(requests.get(f"{KBURL}/counters", headers=H, timeout=60).json())
        from collections import Counter; st = Counter(); page = 0
        while True:
            r = requests.get(f"{KBURL}/resources", params={"page": page, "size": 100}, headers=H, timeout=60).json()
            for x in r.get("resources", []): st[(x.get("metadata") or {}).get("status", "?")] += 1
            if not r.get("pagination", {}).get("more"): break
            page += 1
        print(dict(st)); return
    if a.purge:
        n = 0
        while True:
            r = requests.get(f"{KBURL}/resources", params={"page": 0, "size": 100}, headers=H, timeout=60).json(); res = r.get("resources", [])
            if not res: break
            for x in res: requests.delete(f"{KBURL}/resource/{x['id']}", headers=H, timeout=60); n += 1
        print("deleted", n); INGESTED.exists() and INGESTED.unlink(); return
    ensure_labelsets()
    items = json.loads(CORPUS.read_text()); done = json.loads(INGESTED.read_text()) if INGESTED.exists() else {}
    todo = [i for i in items if i["id"] not in done][: a.limit or None]
    import threading
    from concurrent.futures import ThreadPoolExecutor
    lock = threading.Lock(); count = [0]
    def work(it):
        try:
            rid = create_link(it) if it["kind"] == "link" else create_file(it)
        except Exception as ex:
            print(f"  ERR {it['url'][:90]} {ex}", flush=True); return
        with lock:
            done[it["id"]] = {"rid": rid, "url": it["url"], "brand": it["brand"], "doctype": it["doctype"], "kind": it["kind"]}
            INGESTED.write_text(json.dumps(done, indent=1)); count[0] += 1
            print(f"{count[0]}/{len(todo)} {it['kind']:4s} {it['brand']:12s} {it['doctype']:12s} {rid} {it['url'][:80]}", flush=True)
    with ThreadPoolExecutor(14) as ex:
        list(ex.map(work, todo))
    print("ingested total:", len(done), flush=True)

if __name__ == "__main__": main()
