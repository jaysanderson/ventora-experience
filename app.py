"""Ventora Connected Experience - FastAPI app.

One route per page; the browser talks only to this app's /api/* routes. The
retrieval service key lives server-side (kb.py) and never reaches a client.

Run locally:
    ../../.venv/bin/python -m uvicorn app:app --port 8091
"""
import json
import re
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

import concierge as cz
import kb
import store

ROOT = Path(__file__).resolve().parent
PAGES = ROOT / "static" / "pages"

app = FastAPI(title="Ventora Connected Experience", docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

con = store.connect()
store.seed_history(con)

# Brand presentation (marks, straplines and colours from the group site and brand identities).
BRAND_META = {
    "stegbar": {"colour": "#1F3B73", "accent": "#F2C230", "strapline": "Trusted for over 80 years",
                "hero": "/static/photos/stegbar/alumiere-sliding-and-stacking-doors.jpg", "what": "Windows, doors, showerscreens, wardrobes and splashbacks"},
    "al-windows": {"colour": "#C8102E", "accent": "#C8102E", "strapline": "Always A&L",
                   "hero": "/static/photos/al-windows/aluminium-sliding-doors.jpg", "what": "Aluminium windows and doors, designed and made in Australia"},
    "corinthian": {"colour": "#5B2C86", "accent": "#5B2C86", "strapline": "Your vision brought to life",
                   "hero": "/static/photos/corinthian/coastal-blonde-oak-entrance-door.jpg", "what": "Australia's largest timber door manufacturer"},
    "trend": {"colour": "#0072BC", "accent": "#7AC143", "strapline": "Set your own trend",
              "hero": "/static/photos/trend/quantum-sliding-and-stacking-doors.jpg", "what": "Botanica, Synergy, Quantum, Crestlite and ThermaRange"},
    "aneeta": {"colour": "#1D6FB8", "accent": "#1D6FB8", "strapline": "Light, air and space",
               "hero": "/static/photos/aneeta/vertical-double-glazed-sashless-window-1.jpg", "what": "Sashless window systems for over 25 years"},
    "breezway": {"colour": "#1B75BC", "accent": "#1B75BC", "strapline": "Live uninterrupted",
                 "hero": "/static/photos/breezway/altair-louvres-european-inspired-home-on-the-sunshine-coast.jpg", "what": "Altair louvre windows and natural ventilation"},
    "regency": {"colour": "#B01E2B", "accent": "#B01E2B", "strapline": "Showerscreens, wardrobes, splashbacks",
                "hero": "/static/photos/regency/frameless-shower-screens.jpg", "what": "Showerscreens, wardrobes, splashbacks and mirrors"},
    "ventora-glass": {"colour": "#205C40", "accent": "#205C40", "strapline": "Leader in glass technology",
                      "hero": "/static/photos/ventora-glass/energy-efficient-double-glazed-glass-solutions.jpg", "what": "World-class glass processing"},
}
BRAND_ORDER = ["stegbar", "al-windows", "corinthian", "trend", "aneeta", "breezway", "regency", "ventora-glass"]


def brands_config():
    out = {}
    for slug in BRAND_ORDER:
        b, m = kb.BRANDS[slug], BRAND_META[slug]
        fams = [f for f in cz.FAMILIES if f["brand"] == slug]
        hero = next((f.get("hero") for f in fams if f.get("hero")), m["hero"])
        out[slug] = {"slug": slug, "label": b["label"], "site": b["site"], "mark": f"/static/brand/{slug}.png",
                     "colour": m["colour"], "accent": m["accent"], "strapline": m["strapline"], "what": m["what"], "hero": hero,
                     "links": cz.BRAND_LINKS[slug], "families": [{k: f[k] for k in ("family", "url", "photo", "desc")} for f in fams[:6]]}
    return out


def page(name, config=None):
    html = (PAGES / f"{name}.html").read_text()
    base = {"brands": brands_config(), "brand_order": BRAND_ORDER, "langs": cz.LANGS}
    base.update(config or {})
    return HTMLResponse(html.replace("__CONFIG__", json.dumps(base)))


# ------------------------------------------------------------------ pages
@app.get("/", response_class=HTMLResponse)
def home():
    return page("home", {"route": "home"})


@app.get("/specify", response_class=HTMLResponse)
def specify():
    return page("specify", {"route": "specify"})


@app.get("/brands/{slug}", response_class=HTMLResponse)
def brand(slug: str):
    if slug not in BRAND_META:
        return page("notfound", {"route": "brand"})
    return page("brand", {"route": "brand", "slug": slug})


@app.get("/quote")
def quote():
    return RedirectResponse("/?concierge=quote", status_code=302)


@app.get("/identify")
def identify():
    return RedirectResponse("/?concierge=photo", status_code=302)


@app.get("/quote/handoffs", response_class=HTMLResponse)
def quote_handoffs():
    return page("handoffs", {"route": "handoffs"})


@app.get("/insights", response_class=HTMLResponse)
def insights_page():
    return page("insights", {"route": "insights"})


TOPIC_KEYS = [
    ("warranty", r"warrant|claim|covered|guarantee"), ("energy rating", r"wers|u-value|u value|shgc|energy|7 star|7-star|double glaz|thermal"),
    ("bushfire (BAL)", r"\bbal\b|bushfire|bal-|bal "), ("installation", r"install|flashing|building-in|reveal"),
    ("care and maintenance", r"clean|maintain|maintenance|lubric|care"), ("spare parts", r"spare|replacement|winder|roller|handle|part"),
    ("acoustic", r"acoustic|noise|rw\d|sound"), ("fall prevention", r"fall|as 5203|as5203|second storey|restrict"),
    ("lead time", r"lead time|how long to|delivery"), ("pricing", r"price|cost|how much|quote"),
    ("sizes", r"size|width|height|maximum|span"), ("colours", r"colour|color|finish|powder"),
    ("cyclone", r"cyclone|region c|region d"), ("pool", r"pool|barrier"),
]


def topic_of(q):
    ql = (q or "").lower()
    for t, rx in TOPIC_KEYS:
        if re.search(rx, ql):
            return t
    return "product"


# ------------------------------------------------------------------ answer (streamed, grounded)
@app.post("/api/answer")
async def api_answer(req: Request):
    p = await req.json()
    query = (p.get("query") or "").strip()
    if not query:
        return JSONResponse({"error": "empty question"}, status_code=400)
    mode = p.get("mode") or "general"           # general | specify | quote | service | brand
    lang = p.get("lang") if p.get("lang") in cz.LANGS else "en"
    brand_scope = p.get("brand_scope") if p.get("brand_scope") in BRAND_META else None
    brands = [b for b in (p.get("brands") or []) if b in kb.BRANDS]
    if brand_scope:
        brands = [brand_scope]
    doctypes = [d for d in (p.get("doctypes") or []) if d in kb.DOCTYPES]
    chat_history = p.get("chat_history") or []
    brand_label = kb.BRANDS[brand_scope]["label"] if brand_scope else None
    system = cz.system_prompt("specify" if mode == "specify" else "general", lang, brand_label)
    lead = p.get("lead") or {}
    if mode == "quote":
        known = [k for k in ("state", "product_type", "openings", "glazing", "timing", "contact_preference") if str(lead.get(k) or "").strip().lower() not in ("", "unknown", "none", "n/a")]
        if not known and len(query) > 40:
            # First turn of an enquiry: read what the customer already told us before we reply,
            # so the concierge never asks for something in the message it is answering.
            try:
                lead, _ = kb.ask_json("Extract the enquiry details from this conversation.\n\n" +
                                      "\n".join(f"{'Customer' if h.get('author') in ('user', 'USER') else 'Concierge'}: {h.get('text')}" for h in chat_history)[-5000:] +
                                      f"\nCustomer: {query}", LEAD_SCHEMA, None)
                lead = lead or {}
            except Exception:
                lead = {}
        system += cz.intake_prompt(lead)
    body = kb.base_body(query, brands, doctypes, chat_history, prompt={"system": system})
    route = p.get("route") or "/"
    audience = p.get("audience") or ""

    def gen():
        answer, status, sources, cite_map, order = [], "", {}, {}, []
        for t, item in kb.stream_ask(body):
            if t == "error":
                yield json.dumps({"type": "error"}) + "\n"
                break
            if t == "answer":
                txt = item.get("text") or ""
                answer.append(txt)
                yield json.dumps({"type": "answer", "text": txt}) + "\n"
            elif t == "retrieval":
                for rid, res in ((item.get("results") or {}).get("resources") or {}).items():
                    sources[rid] = kb.resource_meta(res)
            elif t == "citations":
                for key, spans in (item.get("citations") or {}).items():
                    rid = kb.rid_from_cite(key)
                    if rid and rid in sources:
                        if rid not in order:
                            order.append(rid)
                        cite_map.setdefault(rid, [])
                        for s in spans or []:
                            if isinstance(s, list) and len(s) == 2:
                                cite_map[rid].append(s)
            elif t == "status":
                status = item.get("status") or ""
        full = "".join(answer)
        cited = [dict(sources[r], n=i + 1) for i, r in enumerate(order)]
        if status == "no_context" or (not cited and re.search(r"not enough data", full, re.I)):
            status = "no_context"
        if mode == "quote" and status == "no_context":
            # The customer is describing a project rather than asking a question: keep the
            # intake moving honestly by asking only for what is still missing.
            full = concierge_followup(chat_history + [{"author": "user", "text": query}], lang)
            status = "intake"
            yield json.dumps({"type": "answer", "text": full, "replace": True}) + "\n"
        iid = store.log_interaction(con, route=route, audience=audience, brand_scope=brand_scope or "", question=query,
                                    answer=full, status=status or ("success" if full else "error"),
                                    n_sources=len(cited), brands=sorted({c["brand"] for c in cited}) or ([kb.BRANDS[b]["label"] for b in brands]),
                                    doctypes=doctypes, topic=topic_of(query))
        blocks = {}
        if status not in ("no_context", "error"):
            blocks = {"products": cz.product_cards(full, cited, brand_scope, lang),
                      "actions": cz.actions(full, cited, "service" if mode == "service" else ("specify" if mode == "specify" else "general"), brand_scope, lang),
                      "followups": cz.followups(full, cited, "specify" if mode == "specify" else "general", lang)}
        elif status == "no_context":
            fallback_brand = brand_scope or "ventora"
            blocks = {"products": [], "followups": [],
                      "actions": [{"label": cz.t("person", lang), "url": cz.BRAND_LINKS[fallback_brand]["contact"], "kind": "link", "brand": fallback_brand}]}
        if mode == "quote" and lead:
            lead["destination"] = route_destination(lead.get("kind", "quote"), lead.get("brand_interest", ""), lead.get("state", ""))
            blocks["lead"] = lead
        yield json.dumps({"type": "sources", "sources": cited, "status": status, "interaction_id": iid, **blocks}) + "\n"
        yield json.dumps({"type": "done"}) + "\n"

    return StreamingResponse(gen(), media_type="application/x-ndjson")


# ------------------------------------------------------------------ quality, feedback
@app.post("/api/remi")
async def api_remi(req: Request):
    p = await req.json()
    brands = [b for b in (p.get("brands") or []) if b in kb.BRANDS]
    doctypes = [d for d in (p.get("doctypes") or []) if d in kb.DOCTYPES]
    scores = kb.remi(p.get("query") or "", p.get("answer") or "", brands, doctypes)
    if scores.get("available") and p.get("interaction_id"):
        store.set_quality(con, int(p["interaction_id"]), scores)
    return scores


@app.post("/api/feedback")
async def api_feedback(req: Request):
    p = await req.json()
    if p.get("interaction_id"):
        store.set_feedback(con, int(p["interaction_id"]), bool(p.get("good")))
    return {"ok": True}


# ------------------------------------------------------------------ quote intake
LEAD_SCHEMA = {
    "name": "ventora_enquiry",
    "description": "Structured enquiry extracted from a conversation with a customer or specifier",
    "parameters": {
        "type": "object",
        "properties": {
            "kind": {"type": "string", "description": "One of: quote, service, design-assist, commercial, unknown"},
            "state": {"type": "string", "description": "Australian state or territory abbreviation (NSW, VIC, QLD, SA, WA, TAS, NT, ACT) or unknown"},
            "brand_interest": {"type": "string", "description": "Ventora brand the enquiry belongs to (Breezway, Stegbar, A&L Windows & Doors, Trend Windows & Doors, Corinthian Doors, Aneeta, Regency, Ventora Glass). If not named, infer from the product: louvres -> Breezway; timber or internal doors -> Corinthian Doors; shower screens, wardrobes, splashbacks or mirrors -> Regency; sashless windows -> Aneeta; glass processing -> Ventora Glass; aluminium windows or sliding doors with no brand named -> A&L Windows & Doors. Only use unknown when nothing indicates a product."},
            "product_type": {"type": "string", "description": "Product family or type, e.g. louvre windows, sliding doors, shower screen, or unknown"},
            "openings": {"type": "string", "description": "Number and approximate sizes of openings, or unknown"},
            "glazing": {"type": "string", "description": "Glazing preference such as single, double, low-e, acoustic, or unknown"},
            "bal_level": {"type": "string", "description": "Bushfire attack level such as BAL-12.5, BAL-29, BAL-40, FZ, none, or unknown"},
            "timing": {"type": "string", "description": "When the work is needed, or unknown"},
            "contact_preference": {"type": "string", "description": "email, phone, either, or unknown"},
            "project_context": {"type": "string", "description": "Who the customer is and what they are building or fixing, one sentence"},
            "missing": {"type": "string", "description": "Comma-separated list of the detail names still unknown, or none"},
            "summary": {"type": "string", "description": "Two-sentence plain-language summary for the receiving team"},
        },
        "required": ["kind", "state", "brand_interest", "product_type", "openings", "glazing", "bal_level", "timing",
                     "contact_preference", "project_context", "missing", "summary"],
    },
}
STATE_NAMES = {"NSW": "New South Wales", "VIC": "Victoria", "QLD": "Queensland", "SA": "South Australia",
               "WA": "Western Australia", "TAS": "Tasmania", "NT": "Northern Territory", "ACT": "ACT"}


def route_destination(kind, brand_label, state):
    st = STATE_NAMES.get((state or "").upper(), state or "your state")
    slug = kb.LABEL2SLUG.get(brand_label, "")
    if kind == "design-assist":
        return "Breezway - Design Assist team" if slug == "breezway" else f"{brand_label} - specification support"
    if kind == "service":
        return f"{brand_label or 'Ventora'} - Service, {st}"
    if kind == "commercial":
        return f"{brand_label or 'Ventora'} - Commercial projects"
    if slug == "breezway":
        return f"Breezway - {st} fabricator network"
    if slug == "corinthian":
        return f"Corinthian Doors - retailer network, {st}"
    if slug == "aneeta":
        return f"Aneeta - {st} distributor"
    if slug in ("stegbar", "trend", "al-windows", "regency"):
        return f"{brand_label} - {st} sales team"
    if slug == "ventora-glass":
        return "Ventora Glass - commercial enquiries"
    return f"Ventora - {st} enquiries desk"


FIELD_LABELS = {
    "en": {"state": "which state or territory the project is in", "brand_interest": "which brand or product you are interested in",
           "product_type": "what type of product you need", "openings": "how many openings and roughly what size",
           "glazing": "your glazing preference (single, double, low-e or acoustic)", "bal_level": "whether the site has a bushfire (BAL) rating",
           "timing": "when you need it", "contact_preference": "how you would like to be contacted"},
}
ASK_ORDER = ["state", "product_type", "openings", "glazing", "bal_level", "timing", "contact_preference"]
INTAKE_STRINGS = {
    "en": ("Thanks, noted: {got}. ", "Thanks. ", "To get this to the right team I just need {asks}.", " and ", "I have what I need. "),
    "zh": ("谢谢，已记录：{got}。", "谢谢。", "为了转给合适的团队，我还需要了解{asks}。", "以及", "我已经掌握了所需信息。"),
    "vi": ("Cảm ơn, đã ghi nhận: {got}. ", "Cảm ơn. ", "Để chuyển đến đúng bộ phận, tôi chỉ cần biết {asks}.", " và ", "Tôi đã có đủ thông tin. "),
    "ar": ("شكراً، تم التسجيل: {got}. ", "شكراً. ", "لتحويل طلبك إلى الفريق المناسب أحتاج فقط إلى {asks}.", " و ", "لدي كل ما أحتاجه. "),
    "el": ("Ευχαριστώ, σημειώθηκε: {got}. ", "Ευχαριστώ. ", "Για να το προωθήσω στη σωστή ομάδα χρειάζομαι μόνο {asks}.", " και ", "Έχω ό,τι χρειάζομαι. "),
    "it": ("Grazie, annotato: {got}. ", "Grazie. ", "Per inoltrarlo al team giusto mi serve solo {asks}.", " e ", "Ho tutto ciò che mi serve. "),
    "hi": ("धन्यवाद, नोट कर लिया: {got}। ", "धन्यवाद। ", "सही टीम तक पहुँचाने के लिए मुझे बस {asks} चाहिए।", " और ", "मेरे पास सारी जानकारी है। "),
}


def concierge_followup(history, lang="en"):
    transcript = "\n".join(f"{'Customer' if h.get('author') in ('user', 'USER') else 'Concierge'}: {h.get('text')}" for h in history)
    try:
        lead, _ = kb.ask_json("Extract the enquiry details from this conversation.\n\n" + transcript[-6000:], LEAD_SCHEMA, None)
    except Exception:
        lead = {}
    known = [k for k in ASK_ORDER if (lead.get(k) or "unknown").strip().lower() not in ("unknown", "", "n/a", "none")]
    missing = [k for k in ASK_ORDER if k not in known and k != "bal_level"]
    if lead.get("bal_level", "unknown").lower() == "unknown":
        missing.append("bal_level")
    got = []
    if lead.get("project_context") and lead["project_context"].lower() != "unknown":
        got.append(lead["project_context"].rstrip("."))
    s = INTAKE_STRINGS.get(lang, INTAKE_STRINGS["en"])
    if not missing:
        return s[4] + (lead.get("summary") or "")
    labels = FIELD_LABELS["en"]
    asks = [labels[k] for k in missing[:2]]
    lead_in = s[0].format(got=got[0]) if got else s[1]
    return lead_in + s[2].format(asks=s[3].join(asks))


@app.post("/api/intake/extract")
async def api_intake_extract(req: Request):
    p = await req.json()
    history = p.get("chat_history") or []
    transcript = "\n".join(f"{'Customer' if h.get('author') in ('user', 'USER') else 'Concierge'}: {h.get('text')}" for h in history)
    query = "Extract the enquiry details from this conversation.\n\n" + transcript[-6000:]
    try:
        lead, status = kb.ask_json(query, LEAD_SCHEMA, None)
    except Exception:
        lead, status = {}, "error"
    if not lead:
        return {"ok": False, "status": status}
    lead["destination"] = route_destination(lead.get("kind", "quote"), lead.get("brand_interest", ""), lead.get("state", ""))
    return {"ok": True, "lead": lead, "status": status}


@app.post("/api/handoff")
async def api_handoff(req: Request):
    p = await req.json()
    lead = p.get("lead") or {}
    dest = lead.get("destination") or route_destination(lead.get("kind", "quote"), lead.get("brand_interest", ""), lead.get("state", ""))
    hid = store.add_handoff(con, lead.get("kind", "quote"), dest, lead.get("state", ""), lead.get("brand_interest", ""),
                            lead.get("summary", ""), {**lead, "transcript": p.get("chat_history") or [], "lang": p.get("lang") or "en"})
    return {"ok": True, "id": hid, "destination": dest, "reference": f"VEN-{int(time.time()) % 100000:05d}"}


@app.get("/api/handoffs")
def api_handoffs():
    rows = store.handoffs(con)
    for r in rows:
        try:
            r["payload"] = json.loads(r["payload"] or "{}")
        except Exception:
            r["payload"] = {}
    return {"handoffs": rows}


# ------------------------------------------------------------------ identify by photo
SAMPLES = {"breezway": ("samples/breezway.jpg", "image/jpeg"), "corinthian": ("samples/corinthian.jpg", "image/jpeg"),
           "stegbar": ("samples/stegbar.jpg", "image/jpeg")}


@app.post("/api/identify")
async def api_identify(req: Request):
    p = await req.json()
    lang = p.get("lang") if p.get("lang") in cz.LANGS else "en"
    query = (p.get("query") or "What product is this, and where do I find care instructions or spare parts for it?").strip()
    if lang != "en":
        query += f" Reply in {cz.LANGS[lang]['name']}."
    query += " Write in plain Australian English (colour, customised), never mention 'the context' or 'the documents provided', speak as Ventora, and never use exclamation marks."
    if p.get("sample") in SAMPLES:
        rel, ctype = SAMPLES[p["sample"]]
        b64 = kb.to_b64((ROOT / "static" / rel).read_bytes())
    elif p.get("b64") and p.get("content_type", "").startswith("image/"):
        b64, ctype = p["b64"], p["content_type"]
    else:
        return JSONResponse({"error": "no image"}, status_code=400)
    code, d, desc = kb.ask_image(query, b64, ctype)
    if code != 200:
        return {"enabled": False, "reason": f"Photo search returned HTTP {code} on this environment."}
    sources = {rid: kb.resource_meta(r) for rid, r in ((d.get("retrieval_results") or {}).get("resources") or {}).items()}
    order = []
    for key in (d.get("citations") or {}):
        rid = kb.rid_from_cite(key)
        if rid in sources and rid not in order:
            order.append(rid)
    cited = [dict(sources[r], n=i + 1) for i, r in enumerate(order)]
    status = d.get("status") or ""
    answer = d.get("answer") or ""
    store.log_interaction(con, route="/identify", audience="homeowner", question=f"[photo] {query}", answer=answer,
                          status=status, n_sources=len(cited), brands=sorted({c["brand"] for c in cited}), topic="spare parts")
    return {"enabled": True, "answer": answer, "status": status, "sources": cited, "seen": desc,
            "products": cz.product_cards(answer, cited, None, lang), "actions": cz.actions(answer, cited, "service", None, lang),
            "followups": cz.followups(answer, cited, "general", lang)}


# ------------------------------------------------------------------ insights, health, reset
@app.get("/api/insights")
def api_insights():
    return store.insights(con)


@app.get("/api/health")
def api_health():
    c = kb.counters()
    n = con.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
    return {"ok": bool(c), "documents": c.get("resources"), "paragraphs": c.get("paragraphs"), "interactions": n}


@app.post("/api/reset")
def api_reset():
    store.reset_live(con)
    return {"ok": True}
