"""SQLite store for the connected experience: every interaction, feedback,
quality score and handoff. Seeds a plausible synthetic history on first boot
so the Insights view is never empty; live rows append to it.
"""
import json
import random
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB = ROOT / "data" / "experience.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS interactions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  route TEXT NOT NULL,
  audience TEXT,
  brand_scope TEXT,
  question TEXT NOT NULL,
  answer TEXT,
  status TEXT,
  n_sources INTEGER DEFAULT 0,
  brands TEXT,
  doctypes TEXT,
  groundedness REAL,
  answer_relevance REAL,
  context_relevance REAL,
  feedback INTEGER,
  synthetic INTEGER DEFAULT 0,
  topic TEXT
);
CREATE TABLE IF NOT EXISTS handoffs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  kind TEXT NOT NULL,
  destination TEXT NOT NULL,
  state TEXT,
  brand TEXT,
  summary TEXT,
  payload TEXT,
  status TEXT DEFAULT 'sent',
  synthetic INTEGER DEFAULT 0
);
"""

# ------------------------------------------------------------ synthetic seed
AUD = ["builder", "homeowner", "specifier", "trade"]
TOPICS = ["warranty", "energy rating", "bushfire (BAL)", "installation", "care and maintenance",
          "spare parts", "acoustic", "fall prevention", "lead time", "pricing", "sizes", "colours"]
BRAND_LABELS = ["Breezway", "Stegbar", "A&L Windows & Doors", "Trend Windows & Doors",
                "Corinthian Doors", "Aneeta", "Regency", "Ventora Glass"]
Q_TEMPLATES = {
    "warranty": ["How long is the warranty on {b} products?", "Is fading of powder coat covered under the {b} warranty?",
                 "What do I need to lodge a {b} warranty claim?"],
    "energy rating": ["What WERS rating do {b} double glazed units achieve?", "Which {b} products help reach 7 stars?",
                      "What is the U-value of {b} thermally broken frames?"],
    "bushfire (BAL)": ["Which {b} products are tested to BAL-40?", "Can {b} windows be used in a BAL-29 zone?"],
    "installation": ["How do I install a {b} awning window into brick veneer?", "What flashing does {b} recommend for a sliding door?"],
    "care and maintenance": ["How should I clean {b} aluminium frames near the coast?", "How often should {b} tracks be lubricated?"],
    "spare parts": ["Where do I get a replacement winder for a {b} window?", "Can I order {b} rollers online?"],
    "acoustic": ["What acoustic rating can {b} windows achieve?"],
    "fall prevention": ["Do {b} windows comply with fall prevention requirements for second storeys?"],
    "lead time": ["What is the current lead time on {b} orders in Queensland?"],
    "pricing": ["How much does a {b} sliding door cost?", "Is there trade pricing for {b}?"],
    "sizes": ["What is the maximum size for a {b} bi-fold door?"],
    "colours": ["What colours are available for {b} frames?"],
}
NO_CONTEXT_TOPICS = {"lead time", "pricing"}  # the content the public estate does not answer


def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(DB, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def seed_history(con, n=120, force=False):
    cur = con.execute("SELECT COUNT(*) FROM interactions WHERE synthetic=1")
    if cur.fetchone()[0] and not force:
        return
    con.execute("DELETE FROM interactions WHERE synthetic=1")
    con.execute("DELETE FROM handoffs WHERE synthetic=1")
    rnd = random.Random(42)
    now = time.time()
    rows = []
    for i in range(n):
        topic = rnd.choices(list(Q_TEMPLATES), weights=[14, 12, 9, 10, 9, 8, 4, 5, 8, 9, 5, 5])[0]
        brand = rnd.choice(BRAND_LABELS)
        q = rnd.choice(Q_TEMPLATES[topic]).format(b=brand)
        aud = rnd.choices(AUD, weights=[4, 4, 2, 2])[0]
        route = rnd.choices(["/", "/specify", "/brands", "/quote"], weights=[5, 2, 3, 1])[0]
        no_ctx = topic in NO_CONTEXT_TOPICS and rnd.random() < 0.8
        status = "no_context" if no_ctx else "success"
        g = None if no_ctx else round(min(5, max(2.4, rnd.gauss(4.4, 0.5))), 1)
        fb = None
        if not no_ctx and rnd.random() < 0.35:
            fb = 1 if rnd.random() < 0.86 else 0
        if no_ctx and rnd.random() < 0.3:
            fb = 0
        ts = now - rnd.uniform(0, 28 * 86400)
        rows.append((ts, route, aud, brand if route == "/brands" else "", q,
                     "" if no_ctx else "Grounded answer with sources.", status,
                     0 if no_ctx else rnd.randint(2, 7), json.dumps([brand]), json.dumps([]),
                     g, None if g is None else round(min(5, g + rnd.uniform(-0.4, 0.3)), 1),
                     None if g is None else round(min(5, g + rnd.uniform(-0.6, 0.2)), 1), fb, 1, topic))
    con.executemany("""INSERT INTO interactions (ts, route, audience, brand_scope, question, answer, status,
        n_sources, brands, doctypes, groundedness, answer_relevance, context_relevance, feedback, synthetic, topic)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", rows)
    # seeded handoffs (fictional builders and homeowners only)
    hand = [
        ("quote", "Breezway - Brisbane fabricator network", "QLD", "Breezway",
         "Harbourline Homes: 6 x Altair louvre banks, BAL-29, coastal, target 7 stars", "sent"),
        ("quote", "A&L Windows & Doors - NSW sales team", "NSW", "A&L Windows & Doors",
         "Owner-builder, Central Coast: ComfortSmart double glazed sliding doors, 2 openings", "quoted"),
        ("service", "Stegbar - Service, Victoria", "VIC", "Stegbar",
         "Sliding door dragging after 9 months, installed by builder, photos attached", "assigned"),
        ("quote", "Corinthian Doors - retailer: Bellwether Building Supplies", "SA", "Corinthian Doors",
         "Renovator: 9 internal doors, Contemporary collection, pre-hung, left-hand", "sent"),
        ("design-assist", "Breezway - Design Assist", "WA", "Breezway",
         "Architect: school library, Powerlouvre automation, cyclone region C", "in review"),
        ("quote", "Trend Windows & Doors - Sydney showroom", "NSW", "Trend Windows & Doors",
         "Knock-down rebuild, ThermaRange, acoustic glazing to street frontage", "quoted"),
    ]
    for k, dest, st, b, summ, status in hand:
        con.execute("INSERT INTO handoffs (ts, kind, destination, state, brand, summary, payload, status, synthetic) VALUES (?,?,?,?,?,?,?,?,1)",
                    (now - rnd.uniform(3600, 9 * 86400), k, dest, st, b, summ,
                     json.dumps({"summary": summ, "state": st, "brand": b, "kind": k, "contact_preference": "email",
                                 "attachments": ["site-plan.pdf"] if k == "quote" else []}), status))
    con.commit()


def log_interaction(con, **kw):
    cols = ["ts", "route", "audience", "brand_scope", "question", "answer", "status", "n_sources", "brands", "doctypes", "topic"]
    vals = [kw.get("ts", time.time()), kw.get("route", "/"), kw.get("audience", ""), kw.get("brand_scope", ""),
            kw.get("question", ""), kw.get("answer", ""), kw.get("status", ""), kw.get("n_sources", 0),
            json.dumps(kw.get("brands", [])), json.dumps(kw.get("doctypes", [])), kw.get("topic", "")]
    cur = con.execute(f"INSERT INTO interactions ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", vals)
    con.commit()
    return cur.lastrowid


def set_quality(con, iid, scores):
    con.execute("UPDATE interactions SET groundedness=?, answer_relevance=?, context_relevance=? WHERE id=?",
                (scores.get("groundedness"), scores.get("answer_relevance"), scores.get("context_relevance"), iid))
    con.commit()


def set_feedback(con, iid, good):
    con.execute("UPDATE interactions SET feedback=? WHERE id=?", (1 if good else 0, iid))
    con.commit()


def add_handoff(con, kind, destination, state, brand, summary, payload):
    cur = con.execute("INSERT INTO handoffs (ts, kind, destination, state, brand, summary, payload) VALUES (?,?,?,?,?,?,?)",
                      (time.time(), kind, destination, state, brand, summary, json.dumps(payload)))
    con.commit()
    return cur.lastrowid


def handoffs(con, limit=40):
    return [dict(r) for r in con.execute("SELECT * FROM handoffs ORDER BY ts DESC LIMIT ?", (limit,))]


def insights(con):
    rows = [dict(r) for r in con.execute("SELECT * FROM interactions ORDER BY ts DESC")]
    total = len(rows)
    by_brand, by_aud, topics = {}, {}, {}
    fb_good = fb_bad = 0
    unanswered, low_g = [], []
    g_vals = []
    for r in rows:
        for b in json.loads(r.get("brands") or "[]") or ["Ventora"]:
            by_brand[b] = by_brand.get(b, 0) + 1
        by_aud[r.get("audience") or "unknown"] = by_aud.get(r.get("audience") or "unknown", 0) + 1
        t = r.get("topic") or "other"
        topics[t] = topics.get(t, 0) + 1
        if r.get("feedback") == 1:
            fb_good += 1
        elif r.get("feedback") == 0:
            fb_bad += 1
        if r.get("status") == "no_context":
            unanswered.append(r)
        if r.get("groundedness") is not None:
            g_vals.append(r["groundedness"])
            if r["groundedness"] < 3.5:
                low_g.append(r)
    # 14-day daily volume
    days = []
    for i in range(13, -1, -1):
        d0 = datetime.now() - timedelta(days=i)
        lo = datetime(d0.year, d0.month, d0.day).timestamp()
        days.append({"day": d0.strftime("%d %b"), "n": sum(1 for r in rows if lo <= r["ts"] < lo + 86400)})
    # backlog: cluster unanswered by topic
    backlog = {}
    for r in unanswered:
        k = r.get("topic") or "other"
        backlog.setdefault(k, {"topic": k, "n": 0, "examples": []})
        backlog[k]["n"] += 1
        if len(backlog[k]["examples"]) < 3:
            backlog[k]["examples"].append(r["question"])
    return {
        "handoffs": con.execute("SELECT COUNT(*) FROM handoffs").fetchone()[0],
        "total": total,
        "answered": total - len(unanswered),
        "unanswered": len(unanswered),
        "avg_groundedness": round(sum(g_vals) / len(g_vals), 2) if g_vals else None,
        "feedback": {"good": fb_good, "bad": fb_bad},
        "by_brand": sorted(by_brand.items(), key=lambda x: -x[1]),
        "by_audience": sorted(by_aud.items(), key=lambda x: -x[1]),
        "topics": sorted(topics.items(), key=lambda x: -x[1])[:12],
        "daily": days,
        "backlog": sorted(backlog.values(), key=lambda x: -x["n"]),
        "low_groundedness": [{"question": r["question"], "groundedness": r["groundedness"], "brands": json.loads(r["brands"] or "[]"), "ts": r["ts"]} for r in low_g[:10]],
        "latest": [{"id": r["id"], "ts": r["ts"], "route": r["route"], "audience": r["audience"], "question": r["question"],
                    "status": r["status"], "n_sources": r["n_sources"], "groundedness": r["groundedness"],
                    "feedback": r["feedback"], "brands": json.loads(r["brands"] or "[]"), "live": not r["synthetic"]}
                   for r in rows[:20]],
    }


def reset_live(con):
    con.execute("DELETE FROM interactions WHERE synthetic=0")
    con.execute("DELETE FROM handoffs WHERE synthetic=0")
    con.commit()
    seed_history(con, force=True)
