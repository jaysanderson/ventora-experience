# Ventora Connected Experience

Ventora's group digital front door with a concierge in it. Presents as Ventora's own site
(their fonts, palette, logo, brand marks and photography), with grounded answers, product
cards, action buttons and a quote flow underneath. The retrieval service key lives
server-side only; the browser talks to this app's `/api/*` routes.

Live: https://ventora-experience.fly.dev
Repo: https://github.com/jaysanderson/ventora-experience (private)

## Run

    cd apps/ventora-experience
    python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
    cp .env.example .env   # fill in the real values below
    .venv/bin/python -m uvicorn app:app --port 8091

Open http://127.0.0.1:8091.

## Environment variables (`.env`, never committed - see `.env.example`)

| Variable | What it is |
|---|---|
| `ARAG_ZONE` | The Nuclia/ARAG zone this app's Knowledge Box lives in (Sydney: `aws-ap-southeast-2-1`). |
| `ARAG_KB_ID` | The Knowledge Box id. |
| `ARAG_API_KEY` | The KB's own service-account token (`X-NUCLIA-SERVICEACCOUNT`) - never the account-level NUA key. |

Optional: `ARAG_MODEL` to pin a specific generative model (falls back to the KB's own
configured model when unset).

## Pages

| Route | What it is |
|---|---|
| `/` | Home: hero with the concierge invitation, "Find your match" audience cards, the eight brand tiles, Specify band. |
| `/specify` | Specify with Confidence: editorial answer, Resources grid of the documents used (download or open), Design Assist, a real answer-confidence meter. Auto-runs the first question on load. |
| `/brands/{slug}` | Brand mini-site (stegbar, al-windows, corinthian, trend, aneeta, breezway, regency, ventora-glass): hero, product families with photography, "Ask <brand>" locked to that brand, resources. |
| `/insights` | Management view (the only page that shows plumbing): volumes, content backlog, low-groundedness answers, sold-or-solved handoffs, languages. |
| `/quote/handoffs` | Handoff list with full context payloads. |
| `/quote`, `/identify` | Redirect into the concierge in quote or photo mode. |

## The Concierge

A modal over roughly three-quarters of the viewport, opened from the header button, the
hero field, any brand tile, audience card or chip. Header: mode pill (Building, Renovating,
Specifying, Service), language selector (English, 中文, Tiếng Việt, العربية with RTL,
Ελληνικά, Italiano, हिन्दी), photo button. Left rail: goals (Find the right product, Get a
quote, Solve a problem, Find a document, Show me a photo), the live enquiry summary in quote
mode, recently viewed products. Every reply is prose, then product cards (Ventora's own
photography from `static/photos/photos.json`), then 2-4 action buttons that go to real pages
(PDF downloads, product pages, the brand's quote and locator pages, care guides, "Log a
service request", "Talk to a person"), then three follow-up chips, then a discreet "Based on
N Ventora documents" drawer. Buttons are derived from the documents the answer used and the
brand routing table in `concierge.py`; the model never invents a URL.

Quote flow: the goal card or a "Get a quote" button switches to quote mode; the concierge
answers product questions and asks only for what is missing; the rail summary fills as
details are learned; when complete a "Send to <destination>" button appears and the handoff
card shows the reference and what happens next.

## Demo narrative

1. Home. Type "Two-storey home in coastal NSW, BAL-29. Which louvres and sliding doors suit,
   and what does the warranty cover?" into the hero field. The concierge opens, streams the
   answer, shows Altair louvre product cards with photos, then "View What makes a Breezway
   louvre window compliant", "Get a quote", "Find a fabricator", "Talk to a person".
2. Switch the language to 中文 and ask "Altair 百叶窗的保修范围是什么？" - the answer, buttons
   and chips come back in Chinese.
3. Click "Get a quote" in the rail. Type "Renovating a Queenslander in Brisbane, replacing 6
   louvre windows about 900 x 1200, clear glass, no BAL, needed by March, phone is best". The
   summary card fills; click "Send to Breezway - Queensland fabricator network" for the
   handoff card. `/quote/handoffs` shows it with full context.
4. Click the photo button and drop a photo of a window or door; the concierge identifies the
   likely family, shows a product card and offers care, spare parts or replacement buttons.
5. `/brands/corinthian`: chips such as "How do I work out door handing?" answer from
   Corinthian material only; ask about louvres and it offers to hand you to Ask Ventora.
6. `/specify`: pick "Which louvre products have BAL-29 and BAL-40 test reports..." for the
   article-style answer, the Resources grid with the test reports as downloads, and the
   confidence meter.
7. `/insights`: the management loop - what was asked, what could not be answered, what was
   sold or solved.

## Reset (30 seconds)

    ../../.venv/bin/python scripts/reset_demo.py

Clears live interactions and handoffs and re-seeds the synthetic history. The knowledge
content is untouched (`scripts/ingest_public.py --purge` would clear it; do not run that
before a demo).

## Assets and scripts

- `scripts/harvest_assets.py`, `scripts/curate_photos.py`, `scripts/fix_marks.py`: Ventora
  logo, brand marks (background removed and cropped), hero photography and ~50 product photos
  from the brand sites, resized to 1600px, indexed in `static/photos/photos.json`.
- `scripts/ingest_public.py`: the public estate into the Knowledge Box (559 documents).
- `scripts/retitle.py`: gives web-page resources their real page titles.
- `scripts/qa_shots.py`: Playwright design-QA screenshots at 1440x900 and 390x844 to `shots/`.

## Known limits

- Answers come from the published material only; lead times and pricing are refused by design.
- Product cards depend on the photo index: a family without a photo gets no card.
- Photo identification works from a two-step description-then-ask; unusual photos may return
  the honest "not covered" state.
- The intake extraction runs after each quote-mode reply (a few seconds); the summary card
  catches up rather than blocking the conversation.
- Some brand pages were still being processed by the platform at build time; those answers
  improve as processing completes.
