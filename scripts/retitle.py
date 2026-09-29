"""Give web-page resources their real page titles (fetched from the page), so answer
resources read as Ventora names them, not as URL slugs. Idempotent; PDFs keep filenames
(cleaned at display time). Run: ../../.venv/bin/python scripts/retitle.py"""
import json, re, subprocess, html
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import requests
ROOT = Path(__file__).resolve().parent.parent
E = dict(l.split("=", 1) for l in (ROOT / ".env").read_text().split("\n") if "=" in l)
KB = f"https://{E['ARAG_ZONE']}.rag.progress.cloud/api/v1/kb/{E['ARAG_KB_ID']}"
H = {"x-nuclia-serviceaccount": f"Bearer {E['ARAG_API_KEY']}", "content-type": "application/json"}
UA = "Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/128 Safari/537.36"
man = json.loads((ROOT / "data" / "kb-manifest.json").read_text())
done_path = ROOT / "data" / "retitled.json"
done = json.loads(done_path.read_text()) if done_path.exists() else {}
SUFFIX = re.compile(r"\s*[|\-–—:]\s*(Stegbar|Breezway|Trend Windows(?: & Doors| and Doors)?|Corinthian(?: Doors)?|A&L Windows(?: & Doors| and Doors)?|A&amp;L.*|Aneeta(?: Windows)?|Regency(?: Screens)?|Ventora(?: Glass)?|VENTORA)\s*$", re.I)

def page_title(url):
    out = subprocess.run(["curl", "-s", "-L", "--max-time", "40", "-A", UA, url], capture_output=True).stdout.decode("utf-8", "ignore")
    m = re.search(r'<meta property="og:title" content="([^"]+)"', out) or re.search(r"<title[^>]*>(.*?)</title>", out, re.S)
    if not m: return ""
    t = html.unescape(re.sub(r"\s+", " ", m.group(1))).strip()
    t = SUFFIX.sub("", t).strip(" -|–—:")
    return t[:110]

def work(item):
    k, v = item
    if v["kind"] != "link" or not v["rid"] or v["rid"] in ("DUP", "SKIP") or k in done: return
    t = page_title(v["url"])
    if not t or len(t) < 3: return
    r = requests.patch(f"{KB}/resource/{v['rid']}", headers=H, json={"title": t}, timeout=60)
    done[k] = {"title": t, "ok": r.status_code}
    print(r.status_code, t[:70], flush=True)

with ThreadPoolExecutor(8) as ex:
    list(ex.map(work, list(man.items())))
done_path.write_text(json.dumps(done, indent=1))
print("retitled", len(done))
