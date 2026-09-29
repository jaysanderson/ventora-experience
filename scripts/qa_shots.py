"""Design QA screenshots (Playwright). Run with the server on :8091.
  ../../.venv/bin/python scripts/qa_shots.py            # all routes, desktop + phone, plus the concierge
  ../../.venv/bin/python scripts/qa_shots.py --quick    # desktop only, no concierge
"""
import sys, time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "shots"; OUT.mkdir(exist_ok=True)
BASE = "http://127.0.0.1:8091"
ROUTES = [("home", "/"), ("specify", "/specify"), ("brand-breezway", "/brands/breezway"), ("brand-corinthian", "/brands/corinthian"),
          ("insights", "/insights"), ("handoffs", "/quote/handoffs")]
QUICK = "--quick" in sys.argv
ONLY_CZ = "--concierge" in sys.argv
CONSOLE = []


def settle(page, ms=1500):
    page.wait_for_load_state("networkidle", timeout=60000)
    page.evaluate("document.fonts && document.fonts.ready")
    page.evaluate("document.querySelectorAll('.reveal-up').forEach(e => e.classList.add('in'))")
    page.wait_for_timeout(ms)


def shoot(page, name, full=True):
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=full)
    print("shot", name)


with sync_playwright() as p:
    b = p.chromium.launch()
    for label, w, h in ([("desktop", 1440, 900)] if (QUICK or ONLY_CZ) else [("desktop", 1440, 900), ("phone", 390, 844)]):
        ctx = b.new_context(viewport={"width": w, "height": h}, device_scale_factor=1)
        page = ctx.new_page()
        page.on("console", lambda m: CONSOLE.append((m.type, m.text)) if m.type in ("error",) else None)
        page.on("pageerror", lambda e: CONSOLE.append(("pageerror", str(e))))
        for name, route in ([] if ONLY_CZ else ROUTES):
            page.goto(BASE + route)
            settle(page, 2500 if name == "specify" else 1200)
            if name == "specify":
                # wait for the auto-run answer and its resources
                try:
                    page.wait_for_selector("#docs .doc", timeout=90000)
                except Exception:
                    pass
                page.wait_for_timeout(1500)
            shoot(page, f"{label}-{name}")
        if not QUICK and label == "desktop":
            # the concierge, opened from the home hero, with a real answer
            page.goto(BASE + "/"); settle(page, 800)
            page.fill("#invite-input", "Two-storey home in coastal NSW, BAL-29. Which louvres and sliding doors suit, and what does the warranty cover?")
            page.click("#invite .btn")
            page.wait_for_selector(".cz.open", timeout=10000)
            try:
                page.wait_for_selector(".cz .actions .btn", timeout=120000)
            except Exception:
                pass
            page.wait_for_timeout(1200)
            shoot(page, "desktop-concierge-answer", full=False)
            # Chinese
            page.select_option(".cz-head select", "zh")
            page.fill(".cz-composer textarea", "Altair 百叶窗的保修范围是什么？")
            page.press(".cz-composer textarea", "Enter")
            try:
                page.wait_for_selector(".cz .msg.bot:last-child .actions .btn", timeout=120000)
            except Exception:
                pass
            page.wait_for_timeout(1200)
            shoot(page, "desktop-concierge-zh", full=False)
            # quote flow
            page.select_option(".cz-head select", "en")
            page.click(".cz-rail [data-goal=quote]")
            page.wait_for_timeout(600)
            page.fill(".cz-composer textarea", "Renovating a Queenslander in Brisbane, replacing 6 louvre windows about 900 x 1200, clear glass, no BAL, needed by March, phone is best")
            page.press(".cz-composer textarea", "Enter")
            try:
                page.wait_for_selector(".cz [data-handoff]", timeout=150000)
            except Exception:
                pass
            page.wait_for_timeout(800)
            shoot(page, "desktop-concierge-quote", full=False)
        if not QUICK and label == "phone":
            page.goto(BASE + "/?concierge=open&mode=renovating"); settle(page, 1200)
            shoot(page, "phone-concierge", full=False)
        ctx.close()
    b.close()
print("console errors:", CONSOLE if CONSOLE else "none")
