# Ventora Connected Experience - design specification (v2, the A+ rebuild)

The bar: a flagship consumer experience Ventora's own marketing team would ship. Calm, spacious,
photographic, confident. Every screen must survive "would a CMO put this on ventora.com.au today?"
Nothing may read as a developer tool: no cards-of-cards, no citation numbers, no filter chips in
the customer's face, no "Sources" panels. The intelligence shows up as a better answer, a better
next step and a richer page, never as plumbing.

## 1. Brand system (taken from ventora.com.au and the brand sites, 11 Sep 2026)

Fonts (Google Fonts, load with `<link>`; system fallback stacks):
- Headings: **Lexend** 300/400/500/600. Ventora sets section headlines in UPPERCASE Lexend with
  wide tracking ("LET'S RAISE THE BAR", "FIND YOUR MATCH", "LIVE UNINTERRUPTED"). Use that
  for section eyebrows and hero titles. Sentence-case Lexend 400/500 for page and card titles.
- Body: **Pontano Sans** 400, 17px/1.6 on desktop.

Colour tokens (Ventora's Squarespace theme variables):
- `--v-green` #205C40 (hsl 152 48% 24%) - primary, hero bands, primary buttons, logo.
- `--v-green-deep` #17472F - hover, footer.
- `--v-sage` #8DA99C (hsl 152 14% 61%) - accents, dividers, secondary buttons, tag backgrounds.
- `--v-sage-tint` #E9F0EC - soft panels behind imagery.
- `--v-slate` #2C3A3F (hsl 196 18% 21%) - body text on light, dark UI surfaces.
- `--v-mist` #F1F1F4 (hsl 240 8% 95%) - page background sections.
- `--v-white` #FFFFFF - cards and the main page ground.
- `--v-ink` #272727, `--v-ink-2` #3E3E3E - headline text. `--v-line` #E7E7E7 - hairlines.
- Brand colours for brand tiles and brand pages (each brand's own mark colour): Stegbar
  #1F3B73 blue with #F2C230 yellow; A&L #C8102E red; Corinthian #5B2C86 purple; Trend #0072BC
  blue with #7AC143 green; Aneeta #1D6FB8 blue; Breezway #1B75BC blue; Regency #B01E2B red;
  Ventora Glass #205C40 green.
No amber, no navy: that was the old demo palette and it is gone.

Logo and marks (Ventora owns these; download once into static/brand/ at build time, never hotlink):
- Ventora primary logo (green on transparent): https://images.squarespace-cdn.com/content/v1/69044a2061fb54578c6db844/b0d73711-5cf2-4377-9ccc-cec83c791779/ventora_primary-green+RGB.png?format=1500w
  Also make a white version for dark bands (CSS `filter: brightness(0) invert(1)` on the PNG is acceptable).
- Brand marks (2000x2000 PNGs on the group site): Stegbar `38df75d9-fc88-4b81-b9aa-a99a4be2be37/Stegbar_Logo_Resized.png`, A&L `0841a51b-7fe8-42f0-9a79-ea45320900df/A%26L_Logo_Resized.png`, Corinthian `9d310529-9708-4138-9d05-3608d1ea0a73/Corinthian_Logo_Resized.png`, Trend `5a928149-9608-44ef-b10b-e43495d494a9/Trend_Logo_Resized.png`, Aneeta `71b8a365-af50-4864-8b1a-79348d9a59d2/Aneeta_Logo_Resized.png`, Breezway `2866761b-2844-47c3-9dd1-fb75bccc578f/Breezway_Logo_Resized.png`, Regency `c197f3c5-38c4-4f4e-b84a-c6b7b7e327a8/Regency_Small.png`, Ventora Glass `6ba58ff8-fd19-4f93-b7a9-00839c0b4689/VENTORA+Glass_Logo_Resized.png` - all under `https://images.squarespace-cdn.com/content/v1/69044a2061fb54578c6db844/` with `?format=500w`.
- Group hero photography: `da7a8190-b2ab-4e17-b45d-40fcd8adec7c/Stegbar_Header.jpg` (8131x3481, use `?format=2500w`), `cabeed4d-6b6b-4f9a-b3a2-5975365a80f7/A%26L_Innovation.jpg`, `eab1cf70-e8d1-46f5-b1a1-74933b9c325d/Our+Culture.jpg`.
- Product photography: harvest 4-8 images per brand from the brand sites' product sitemaps
  (Shopify product sitemaps carry `<image:loc>` per product: Stegbar, Trend, Regency, Ventora Glass;
  WordPress sites: take `og:image` of product pages for Breezway, A&L, Corinthian, Aneeta; known good:
  Trend Quantum `https://www.trendwindows.com.au/cdn/shop/files/Web_and_Insta_Res-59.jpg?width=2048`,
  Corinthian `https://cdn.corinthian.com.au/wp-content/uploads/2024/07/15065859/Hamptons-Peninsula-PPENWS-2-scaled.jpg`).
  Store in static/photos/<brand>/ with a `photos.json` index {brand, product family, page url, file, alt}.
  The concierge and product cards use this index to show a photograph with every product it mentions.

## 2. Layout language

- 12-column grid, max content width 1240px, outer gutter 32px (16px on phones). Section rhythm
  96px desktop / 56px mobile. Generous whitespace; hairline dividers, not boxes.
- Cards only where an object is a real thing (a product, a resource, a brand). Cards have a photo
  (4:3 or 3:2), a title in Lexend, one line of Pontano, one action. Radius 6px. Shadow only on hover
  (0 12px 32px rgba(32,92,64,.12)). Photos scale 1.03 on hover over 400ms ease-out.
- Buttons: primary = green fill, white Lexend 500 15px, 14px 22px padding, radius 3px, uppercase
  with .08em tracking (Ventora's button style); secondary = 1px sage outline; tertiary = green text
  with a 1px underline that thickens on hover. Focus rings 2px sage offset 2px.
- Header: white, 72px, logo left (height 30px), nav in Lexend 400 15px uppercase tracking .06em,
  a "Concierge" button on the right (green). Sticky, with a 1px line on scroll. Footer: deep green,
  logo in white, brand list, contact, "Demonstration environment" disclosure in 12px sage.
- Motion: content fades up 16px over 500ms on first view (IntersectionObserver), staggered 60ms;
  respect `prefers-reduced-motion`. Skeleton shimmer for anything loading; never an empty box.
- Type scale: hero 56/1.05 Lexend 300 (uppercase eyebrow above in 13px tracking .18em); section
  titles 36/1.15; card titles 20/1.3; body 17/1.6; small 14; micro 12. Max line length 68ch.
- Photography treatment: full-bleed hero with a green-to-transparent gradient (rgba(32,92,64,.55)
  to 0) so white text sits cleanly; never a grey overlay.
- Mobile: single column, sticky concierge button at the bottom, hero 48/1.05.

## 3. Pages (one route each; all seeded on first paint)

1. `/` Home - what ventora.com.au could be with the concierge in it:
   - Full-bleed hero (Stegbar_Header.jpg): eyebrow "WINDOWS · DOORS · GLASS · WARDROBES · SHOWERSCREENS",
     title "Bring light, air and space to every project.", one line of body, and the concierge
     entry: a wide white search field styled as an invitation ("Tell us what you're building or
     fixing...") that opens the concierge modal with the text carried in, plus three quiet
     example prompts beneath as text links.
   - "Find your match" band (their headline): three photo cards for the audiences - I'm building
     (builder), I'm renovating or replacing (homeowner), I'm specifying (architect) - each opens
     the concierge in that mode.
   - "Our brands" grid: eight brand tiles, each a product photograph with the brand mark on a
     white plaque, brand strapline, hover reveals "Explore" and "Ask <brand>". Straplines from the
     group site: Stegbar "Trusted for over 80 years"; A&L "Always A&L"; Corinthian "Your vision
     brought to life"; Trend "Set your own trend"; Aneeta "Light, air and space"; Breezway "Live
     uninterrupted"; Regency "Over 40 years of showerscreens, wardrobes and splashbacks";
     Ventora Glass "Leader in glass technology".
   - "Specify with confidence" band on mist: two columns, copy + a photo, one button to /specify.
   - Footer.
2. `/specify` - for architects, estimators and certifiers. Editorial layout: a short hero on mist
   with the promise; then a working area: a single elegant question field with a brand selector
   as a row of brand marks (toggle), a compact row of resource types (Test reports, Energy ratings,
   Installation, Care, Warranty) rendered as underlined text toggles, and the answer as an
   article: title-cased summary, then "What the documents say" prose, then a **Resources** grid
   of document cards (PDF icon or page thumbnail, brand mark, title, issued date, "Download" or
   "Open page"), then "Talk to a specialist" (Design Assist, prefilled) as a quiet CTA. Quality
   signal stays here but understated: a single line "Every statement above is drawn from the
   documents listed" plus a small "Answer confidence" meter fed by REMi (real score or hidden if
   unavailable). No filter chips visible until the question is asked.
3. `/brands/{slug}` - the brand page as a mini-site: brand hero photo, brand mark, strapline,
   three product-family photo cards (from photos.json), a "Ask <brand>" section that opens the
   concierge locked to that brand (brand accent colour on the modal header), and the brand's
   resources (warranty, care, installation) as document cards. Answers are limited to that brand;
   a cross-brand question gets a graceful "That's a <other brand> question - I can hand you over"
   with a button that reopens the concierge unlocked.
4. `/insights` - the management view; the ONLY page that shows plumbing. Reskin to the brand
   system (Lexend numbers, sage bars) and keep the content. Add a "What the concierge sold or
   solved this week" panel: handoffs by destination, top CTAs clicked, languages used.
5. `/quote/handoffs` - handoff list, reskinned. `/quote` and `/identify` are folded INTO the
   concierge (see 4) and redirect to `/` with the concierge open in that mode; keep the routes.

## 4. The Concierge (the centrepiece)

Opens as a modal covering about 75% of the viewport (max 1180px wide, 86vh tall), centred, radius
10px, white, with a scrim of rgba(23,71,47,.55) and a 220ms scale/fade in. Escape and the scrim
close it. It replaces the corner-widget pattern entirely (Stegbar's Barla is the anti-pattern:
tiny box, plain text, "took too long to respond").

Anatomy:
- Header bar (white, hairline below): a small green "V" roundel, "Ventora Concierge",
  a mode pill (Building · Renovating · Specifying · Service), a **language selector** (English,
  中文, Tiếng Việt, العربية, Ελληνικά, Italiano, हिन्दी; UI strings and the answer language switch
  together; RTL for Arabic), a "Send a photo" icon button, and close.
- Left rail (280px, mist): "What I can help with" - four goal cards with icons (Find the right
  product, Get a quote, Solve a problem, Find a document); under them, "Recently viewed" products
  as tiny photo rows. Collapses on mobile.
- Conversation (centre): messages as clean paragraphs, no bubbles for the concierge, a soft sage
  bubble for the user. The concierge's reply is composed of blocks, in this order when present:
  1. Answer prose (streamed, Pontano 17px, short paragraphs, never more than ~120 words before an action).
  2. **Product cards** (photo, brand mark, family name, one-line why-it-fits, "View product" and
     "Ask about this") - shown whenever a product family is named; photo from photos.json.
  3. **Action buttons**: every reply ends with 2-4 CTAs rendered as real buttons: "Get a quote",
     "Find a showroom / retailer / fabricator", "Download the test report", "Book Design Assist",
     "See care guide", "Talk to a person". They link to the actual pages (brand quote pages,
     locators, PDFs) or drive the flow (quote intake, handoff). CTAs are derived deterministically
     from what the answer used (cited pages and PDFs become links; brand routing becomes quote and
     locator buttons; a service question adds "Log a service request"); the model never invents URLs.
  4. Follow-up chips (3) in sage outline.
- Composer (bottom): a single large field with placeholder in the chosen language, send button,
  a paperclip for photos, and a one-line "Answers come from Ventora's published material" in 12px.
- The quote flow lives here: when the goal is a quote, the concierge asks only for what is
  missing (state, product, openings, glazing, BAL, timing, contact preference), shows a live
  summary card on the right rail as fields fill, and finishes with a **handoff card**: "Sent to
  Breezway - Queensland fabricator network" with a reference number and what happens next.
- Photo mode: drop or pick a photo; the concierge shows the photo in the thread, identifies the
  likely product family with a product card, and offers care, spare parts or replacement CTAs.
- Service mode: warranty and care answers end with "Log a service request" and "Download the warranty".
- Honesty: when the material does not cover it, the concierge says so in one sentence and offers
  "Talk to a person" with the right brand's contact page. Never a raw error, never "no_context".
- Latency: show the reply streaming within ~1 s; a three-dot pulse before the first token; keep the
  scroll pinned to the newest block; never a spinner in the middle of the screen.
- Grounding stays invisible to the customer: no citation numbers, no sources list. A tiny
  "Based on 6 Ventora documents" link at the end of a reply opens a small drawer listing them
  (title, brand, open link) for the curious. That is the only trace of the machinery.

## 5. Quality gates for this build (in addition to the factory DoP)

- Screenshot every route at 1440x900 and 390x844 with Playwright and LOOK at each one; fix
  anything that would embarrass a designer: misaligned baselines, orphan words in titles, cards
  of unequal height, images with wrong crop, text over busy photo areas, inconsistent radii,
  default-blue links, unstyled form controls, layout shift while streaming.
- Real photographs on every page and in every product card; no placeholder blocks, no icons
  standing in for photos.
- Every CTA button leads somewhere real (a Ventora page, a PDF, or a working in-app flow).
- All copy in Australian English, sentence case except Ventora's uppercase eyebrows, no
  exclamation marks, no "AI" in customer-facing copy (say "concierge").
- Lighthouse-style sanity: images lazy-loaded with width/height, fonts preloaded, no console errors.
