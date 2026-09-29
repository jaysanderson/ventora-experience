"""Server-side knowledge helpers for the Ventora connected experience.

Everything that talks to the retrieval platform lives here and runs on the
server. The browser only ever calls this app's own /api/* routes; the service
key never leaves this process.
"""
import base64
import json
import os
import re
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent

# --- minimal .env loader (real env wins) ---
_env = ROOT / ".env"
if _env.exists():
    for _line in _env.read_text().splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())

ZONE = os.environ.get("ARAG_ZONE", "")
KB = os.environ.get("ARAG_KB_ID", "")
KEY = os.environ.get("ARAG_API_KEY", "")
MODEL = os.environ.get("ARAG_MODEL", "gemini-3.1-flash-lite")
KBURL = f"https://{ZONE}.rag.progress.cloud/api/v1/kb/{KB}"
HJSON = {"x-nuclia-serviceaccount": f"Bearer {KEY}", "content-type": "application/json",
         "accept": "application/json"}
HSYNC = {**HJSON, "x-synchronous": "true"}

BRANDS = {
    "breezway": {"label": "Breezway", "colour": "#0072BC", "site": "https://www.breezway.com.au",
                 "tagline": "Altair louvre windows and natural ventilation",
                 "next": [("Find a fabricator or showroom", "https://www.breezway.com.au/view-buy/"),
                          ("Ask the Design Assist team", "/quote?brand=breezway&kind=design-assist")]},
    "stegbar": {"label": "Stegbar", "colour": "#7A1F2B", "site": "https://www.stegbar.com.au",
                "tagline": "Windows, doors, shower screens and wardrobes for over 80 years",
                "next": [("Request a quote", "/quote?brand=stegbar"),
                         ("Find a showroom", "https://www.stegbar.com.au/pages/find-a-showroom")]},
    "al-windows": {"label": "A&L Windows & Doors", "colour": "#1E6F3C", "site": "https://www.alwindows.com.au",
                   "tagline": "Aluminium windows and doors, designed and made in Australia",
                   "next": [("Request a quote", "/quote?brand=al-windows"),
                            ("Technical centre", "https://www.alwindows.com.au/resources/")]},
    "trend": {"label": "Trend Windows & Doors", "colour": "#C8102E", "site": "https://www.trendwindows.com.au",
              "tagline": "Botanica, Synergy, Quantum, Crestlite and ThermaRange",
              "next": [("Request a quote", "/quote?brand=trend"),
                       ("Find a showroom", "https://www.trendwindows.com.au/pages/showrooms")]},
    "corinthian": {"label": "Corinthian Doors", "colour": "#5B3A29", "site": "https://www.corinthian.com.au",
                   "tagline": "Australia's largest timber door manufacturer",
                   "next": [("Find a retailer", "https://www.corinthian.com.au/find-a-retailer/"),
                            ("Installation and door handing help", "/quote?brand=corinthian&kind=service")]},
    "aneeta": {"label": "Aneeta", "colour": "#00747A", "site": "https://www.aneetawindows.com.au",
               "tagline": "Sashless window systems",
               "next": [("Find a distributor", "https://www.aneetawindows.com.au/distributors/"),
                        ("Specify with confidence", "/specify")]},
    "regency": {"label": "Regency", "colour": "#6D4C9F", "site": "https://www.regencyscreens.com.au",
                "tagline": "Shower screens, wardrobes, splashbacks and mirrors",
                "next": [("Request a quote", "/quote?brand=regency"),
                         ("Warranty and care", "https://www.regencyscreens.com.au/pages/warranty")]},
    "ventora-glass": {"label": "Ventora Glass", "colour": "#3B7EA1", "site": "https://www.ventoraglass.com.au",
                      "tagline": "Glass processing for Ventora brands and external customers",
                      "next": [("Commercial enquiry", "/quote?brand=ventora-glass&kind=commercial")]},
    "ventora": {"label": "Ventora", "colour": "#0F2440", "site": "https://www.ventora.com.au",
                "tagline": "The group behind eight Australian building-product brands",
                "next": [("Ask Ventora", "/"), ("Specify with confidence", "/specify")]},
}
LABEL2SLUG = {v["label"]: k for k, v in BRANDS.items()}
DOCTYPES = ["warranty", "compliance", "energy", "installation", "care", "technical", "support",
            "brochure", "product", "corporate", "page"]


def _label_filters(brands=None, doctypes=None):
    """Label filters: OR within a facet, AND across facets."""
    out = []
    if brands:
        out.append({"any": [f"/classification.labels/brand/{BRANDS[b]['label']}" for b in brands if b in BRANDS]})
    if doctypes:
        out.append({"any": [f"/classification.labels/doctype/{d}" for d in doctypes if d in DOCTYPES]})
    return out


_AUTHOR = {"user": "USER", "assistant": "NUCLIA", "USER": "USER", "NUCLIA": "NUCLIA"}


def history(chat_history):
    """Client turns use plain role names; the platform wants its own author tokens."""
    return [{"author": _AUTHOR.get(h.get("author", "user"), "USER"), "text": h.get("text", "")}
            for h in chat_history if h.get("text")][-12:]


def base_body(query, brands=None, doctypes=None, chat_history=None, prompt=None, max_tokens=600):
    body = {
        "query": query,
        "features": ["keyword", "semantic"],
        "citations": True,
        "rephrase": True,
        "prefer_markdown": True,
        "show": ["basic", "origin"],
        "max_tokens": max_tokens,
        "generative_model": MODEL,
        "rag_strategies": [{"name": "neighbouring_paragraphs", "before": 1, "after": 1}],
    }
    flt = _label_filters(brands, doctypes)
    if flt:
        body["filters"] = flt
    if chat_history:
        body["chat_history"] = history(chat_history)
    if prompt:
        body["prompt"] = prompt
    return body


_MONTHS = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
_MON_ABBR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _fmt_my(m, y):
    if y < 100:
        y += 2000
    if not (2000 <= y <= 2035 and 1 <= m <= 12):
        return ""
    return f"{_MON_ABBR[m - 1]} {y}"


def issued_date(title, url):
    """Best-effort issue date from the document's own name (filename or title), e.g.
    'march-24', 'March_2024', 'Sept23', '290726', '150116', '05_04_2012', '20240903',
    '/2024/07/'. Returns a label like 'Mar 2024' or '2026', or '' when nothing is found.
    Never derived from the indexing timestamp."""
    text = " ".join(t for t in (title or "", (url or "").rsplit("/", 1)[-1]) if t)
    text = re.sub(r"[?#].*$", "", text)
    m = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*[-_ ]?(20\d{2}|\d{2})\b", text, re.I)
    if m:
        lab = _fmt_my(_MONTHS[m.group(1).lower()[:3]], int(m.group(2)))
        if lab:
            return lab
    m = re.search(r"(?<!\d)(\d{2})[-_. ](\d{2})[-_. ](20\d{2})(?!\d)", text)
    if m:
        lab = _fmt_my(int(m.group(2)), int(m.group(3)))
        if lab:
            return lab
    m = re.search(r"(?<!\d)(20\d{2})(\d{2})(\d{2})(?!\d)", text)
    if m and 1 <= int(m.group(2)) <= 12 and 1 <= int(m.group(3)) <= 31:
        lab = _fmt_my(int(m.group(2)), int(m.group(1)))
        if lab:
            return lab
    m = re.search(r"(?<!\d)(\d{2})(\d{2})(\d{2})(?!\d)", text)
    if m and 1 <= int(m.group(1)) <= 31 and 1 <= int(m.group(2)) <= 12:
        lab = _fmt_my(int(m.group(2)), int(m.group(3)))
        if lab:
            return lab
    m = re.search(r"/(20\d{2})/(\d{2})/", url or "")
    if m:
        lab = _fmt_my(int(m.group(2)), int(m.group(1)))
        if lab:
            return lab
    m = re.search(r"(?<!\d)(20[12]\d)(?!\d)", text)
    if m:
        return m.group(1)
    return ""


def _fmt_iso_day(iso):
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", iso or "")
    if not m:
        return ""
    return f"{int(m.group(3))} {_MON_ABBR[int(m.group(2)) - 1]} {m.group(1)}"


_ABBR = {"tb": "Technical bulletin", "dm": "Design manual", "wers": "WERS", "bal": "BAL", "bal29": "BAL-29", "bal40": "BAL-40",
         "igu": "IGU", "cpd": "CPD", "lfl": "LFL", "csiro": "CSIRO", "agwa": "AGWA", "faq": "FAQ", "faqs": "FAQs", "diy": "DIY",
         "nsw": "NSW", "qld": "QLD", "vic": "VIC", "sa": "SA", "wa": "WA", "au": "AU", "sl2": "SL2", "sl3": "SL3", "mm": "mm"}
_DATE_TOKENS = re.compile(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*[-_ ]?(20\d{2}|\d{2})\b|\b\d{6,8}\b|\b20[12]\d\b|\bv\d+\b", re.I)


def pretty_title(title, url, kind):
    """A document name a person would print: filename codes and date stamps out, known
    abbreviations expanded, Title Case. Web pages keep their real page title."""
    t = (title or "").strip()
    if kind != "pdf" and t and not re.search(r"[_]|\.pdf$", t, re.I):
        return t
    t = re.sub(r"\.(pdf|PDF)$", "", t)
    t = re.sub(r"[_\-]+", " ", t)
    t = _DATE_TOKENS.sub(" ", t)
    t = re.sub(r"^\s*\d{3,4}[a-z]?\s+", "", t, flags=re.I)          # leading catalogue codes like 0456P
    small = {"of", "and", "the", "for", "in", "a", "to", "with", "on", "at", "by", "vs"}
    out = []
    for i, w in enumerate([w for w in t.split() if w]):
        lw = w.lower()
        if lw in _ABBR:
            out.append(_ABBR[lw] if i == 0 else (_ABBR[lw] if _ABBR[lw].isupper() or lw in ("mm",) else _ABBR[lw].lower()))
        elif w.isupper() and len(w) <= 5 and not w.isdigit():
            out.append(w)
        elif lw in small and i:
            out.append(lw)
        else:
            out.append(w[:1].upper() + w[1:].lower() if not re.search(r"\d", w) else w)
    s = re.sub(r"\s+", " ", " ".join(out)).strip()
    s = re.sub(r"\bBuilding in\b", "Building-in", s)
    return s if s else (title or url or "Document")


def resource_meta(res):
    """Normalise one retrieval resource into what the UI shows."""
    labels = {}
    for c in ((res.get("usermetadata") or {}).get("classifications") or []):
        labels[c.get("labelset")] = c.get("label")
    origin = res.get("origin") or {}
    url = origin.get("url") or ""
    brand_label = labels.get("brand") or "Ventora"
    kind = "pdf" if (res.get("icon") == "application/pdf" or url.lower().endswith(".pdf")) else "web"
    return {
        "rid": res.get("id"),
        "title": pretty_title(res.get("title") or url or "Untitled", url, kind),
        "url": url,
        "brand": brand_label,
        "slug": LABEL2SLUG.get(brand_label, "ventora"),
        "doctype": labels.get("doctype") or "page",
        "kind": "pdf" if (res.get("icon") == "application/pdf" or url.lower().endswith(".pdf")) else "web",
        "issued": issued_date(res.get("title") or "", url),
        "indexed": _fmt_iso_day(res.get("created") or res.get("modified") or ""),
    }


def stream_ask(body):
    """Yield (item_type, item) tuples from a streaming ask."""
    with requests.post(f"{KBURL}/ask", headers=HJSON, json=body, stream=True, timeout=180) as r:
        if r.status_code != 200:
            yield ("error", {"http": r.status_code, "text": r.text[:300]})
            return
        for line in r.iter_lines():
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            item = d.get("item") or {}
            yield (item.get("type"), item)


def ask_sync(body):
    r = requests.post(f"{KBURL}/ask", headers=HSYNC, json=body, timeout=180)
    r.raise_for_status()
    return r.json()


def ask_json(query, schema, chat_history=None, brands=None):
    """Structured extraction. Kept separate from the cited call (the two are
    mutually exclusive on the platform), and every property is required."""
    body = {
        "query": query,
        "features": ["keyword", "semantic"],
        "answer_json_schema": schema,
        "generative_model": MODEL,
        "show": ["basic"],
        "max_tokens": 500,
    }
    if chat_history:
        body["chat_history"] = history(chat_history)
    flt = _label_filters(brands, None)
    if flt:
        body["filters"] = flt
    d = ask_sync(body)
    return d.get("answer_json") or {}, d.get("status")


def describe_image(b64, content_type):
    """Step 1 of photo search: the vision model describes what is in the photo.
    Returns (http_status, description_text)."""
    body = {
        "query": "Describe only what is visible in this photo, in two short sentences: the type of window, door, screen or "
                 "joinery (for example louvre window, sliding door, entrance door, shower screen, wardrobe), the frame material "
                 "and colour, the glass or blade style, and the setting. Do not name a brand. Do not use the reference material.",
        "query_image": {"b64encoded": b64, "content_type": content_type},
        "features": ["semantic"], "rephrase": False, "citations": False, "show": ["basic"], "max_tokens": 160,
        "generative_model": MODEL,
        "prompt": {"system": "You describe photographs of building products precisely and briefly. Ignore any reference material; describe only the photo."},
    }
    r = requests.post(f"{KBURL}/ask", headers=HSYNC, json=body, timeout=240)
    if r.status_code != 200:
        return r.status_code, ""
    desc = (r.json().get("answer") or "").strip()
    if not desc or re.search(r"not enough data", desc, re.I):
        # The model sometimes declines to describe when the retrieved material is unrelated;
        # ask again with a plainer instruction before giving up on the description.
        body["query"] = "What kind of window, door, screen or joinery is in this photo? Answer in two short sentences describing only the photo."
        body["features"] = ["keyword", "semantic"]
        r = requests.post(f"{KBURL}/ask", headers=HSYNC, json=body, timeout=240)
        desc = (r.json().get("answer") or "").strip() if r.status_code == 200 else ""
        if re.search(r"not enough data", desc, re.I):
            desc = ""
    return 200, desc


# Product-routing heuristics for photo search: an unambiguous product word in the
# description narrows retrieval to the brands that make that product (real product
# logic, the same routing a human at the enquiries desk would apply).
PHOTO_ROUTES = [
    (r"louvre|louver|slat blades|glass blades", ["breezway", "stegbar", "trend", "al-windows"]),
    (r"entrance door|front door|internal door|timber door|panel door|barn door", ["corinthian"]),
    (r"shower screen|shower|wardrobe|splashback|mirror", ["regency", "stegbar"]),
    (r"sashless", ["aneeta", "stegbar", "trend"]),
]


def photo_scope(desc):
    for rx, brands in PHOTO_ROUTES:
        if re.search(rx, desc or "", re.I):
            return brands, ["product", "care", "support", "technical", "brochure", "page"]
    return None, ["product", "care", "support", "technical", "brochure", "page"]


def ask_image(query, b64, content_type, max_tokens=400):
    """Photo search, two real steps: (1) vision description of the photo, (2) a grounded,
    cited text ask built from that description. Returns (http_status, ask_response, description)."""
    code, desc = describe_image(b64, content_type)
    if code != 200:
        return code, {}, ""
    if re.search(r"not enough data", desc, re.I) or not desc:
        desc = ""
    q2 = (f"Photo description: {desc} " if desc else "") + \
         "Which Ventora product family does this match, and where are its care instructions, spare parts or replacement options? " + query
    brands, doctypes = photo_scope(desc)
    body = base_body(q2, brands=brands, doctypes=doctypes, max_tokens=max_tokens, prompt={"system": (
        "You match a customer's photo description to Ventora product material. Say which product family is the closest match and why, "
        "using only the supplied material, then point to the care, spare parts or replacement material. "
        "If nothing in the material matches the description, say so plainly.")})
    if not desc:
        # No usable description: fall back to a single-step image query so the customer
        # still gets whatever the material can match, with sources.
        body = base_body(query, max_tokens=max_tokens)
        body["query_image"] = {"b64encoded": b64, "content_type": content_type}
    r = requests.post(f"{KBURL}/ask", headers=HSYNC, json=body, timeout=240)
    return r.status_code, (r.json() if r.headers.get("content-type", "").startswith("application/json") else {"text": r.text[:300]}), desc


def find_contexts(query, brands=None, doctypes=None, n=8):
    fb = {"query": query, "features": ["keyword", "semantic"], "show": ["basic"], "page_size": n}
    flt = _label_filters(brands, doctypes)
    if flt:
        fb["filters"] = flt
    scored = []
    try:
        fr = requests.post(f"{KBURL}/find", headers=HJSON, json=fb, timeout=40)
        for rv in (fr.json().get("resources") or {}).values():
            for fld in (rv.get("fields") or {}).values():
                for para in (fld.get("paragraphs") or {}).values():
                    t = (para or {}).get("text")
                    if t and t.strip():
                        scored.append(((para or {}).get("score", 0), t.strip()))
    except Exception:
        pass
    scored.sort(key=lambda x: x[0], reverse=True)
    return [t for _s, t in scored[:n]]


def remi(query, answer, brands=None, doctypes=None):
    """Real quality scores (0-5) for a completed answer against what was
    retrieved for it. Never fabricated: returns available=False on any failure."""
    if not (answer or "").strip():
        return {"available": False}
    top = find_contexts(query, brands, doctypes)
    if not top:
        return {"available": False}
    try:
        rr = requests.post(f"{KBURL}/predict/remi", headers=HJSON,
                           json={"user_id": "ventora-experience", "question": query, "answer": answer,
                                 "contexts": ["\n\n".join(top)]}, timeout=60)
        if rr.status_code != 200:
            return {"available": False}
        d = rr.json()
    except Exception:
        return {"available": False}

    def _val(x):
        vals = [v for v in x if isinstance(v, (int, float))] if isinstance(x, list) else []
        return vals[0] if vals else None

    ar = d.get("answer_relevance") or {}
    return {"available": True,
            "answer_relevance": ar.get("score") if isinstance(ar, dict) else ar,
            "context_relevance": _val(d.get("context_relevance")),
            "groundedness": _val(d.get("groundedness")),
            "scale": 5, "n_contexts": len(top)}


def counters():
    try:
        return requests.get(f"{KBURL}/counters", headers=HJSON, timeout=20).json()
    except Exception:
        return {}


def to_b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


CITE_KEY_RE = re.compile(r"^([0-9a-f]{32})/")


def rid_from_cite(key: str):
    m = CITE_KEY_RE.match(key or "")
    return m.group(1) if m else None
