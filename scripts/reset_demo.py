"""30-second reset for the Ventora connected experience demo.

  ../../.venv/bin/python scripts/reset_demo.py

Clears every LIVE interaction and handoff logged during a demo and re-seeds the
synthetic 28-day history, so Insights and Handoffs are back to their opening state.
Does not touch the content index (that reset is scripts/ingest_public.py --purge
followed by a full re-ingest, which takes hours - never run it mid-demo).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import store  # noqa: E402

con = store.connect()
store.reset_live(con)
n = con.execute("SELECT COUNT(*) FROM interactions").fetchone()[0]
h = con.execute("SELECT COUNT(*) FROM handoffs").fetchone()[0]
print(f"reset complete: {n} synthetic interactions, {h} synthetic handoffs, 0 live rows")
