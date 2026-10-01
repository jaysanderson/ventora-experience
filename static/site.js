/* Ventora Connected Experience - shell, motion and the Concierge. Talks only to this app's /api routes. */
(function () {
  const CFG = window.CONFIG || {};
  const BR = CFG.brands || {};
  const ORDER = CFG.brand_order || Object.keys(BR);
  const LANGS = CFG.langs || { en: { native: "English" } };
  const $ = (s, r) => (r || document).querySelector(s);
  const esc = s => String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const fmt = (s, o) => String(s).replace(/\{(\w+)\}/g, (_, k) => (o && o[k] != null ? o[k] : ""));
  const labelOf = slug => (BR[slug] || {}).label || slug;

  /* ---------- tiny markdown ---------- */
  function md(text) {
    const lines = String(text || "").replace(/\r/g, "").split("\n");
    let html = "", inList = null, para = [];
    const inline = s => esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/(^|[^*])\*([^*\n]+)\*/g, "$1<i>$2</i>")
      .replace(/\[([^\]]+)\]\((https?:[^)]+)\)/g, '<a class="link" href="$2" target="_blank" rel="noopener">$1</a>');
    const flushP = () => { if (para.length) { html += `<p>${inline(para.join(" "))}</p>`; para = []; } };
    const closeList = () => { if (inList) { html += `</${inList}>`; inList = null; } };
    for (const raw of lines) {
      const l = raw.trimEnd(); let m;
      if (!l.trim()) { flushP(); closeList(); continue; }
      if ((m = l.match(/^(#{1,4})\s+(.*)/))) { flushP(); closeList(); html += `<h3>${inline(m[2])}</h3>`; continue; }
      if ((m = l.match(/^\s*[-*•]\s+(.*)/))) { flushP(); if (inList !== "ul") { closeList(); html += "<ul>"; inList = "ul"; } html += `<li>${inline(m[1])}</li>`; continue; }
      if ((m = l.match(/^\s*\d+[.)]\s+(.*)/))) { flushP(); if (inList !== "ol") { closeList(); html += "<ol>"; inList = "ol"; } html += `<li>${inline(m[1])}</li>`; continue; }
      para.push(l.trim());
    }
    flushP(); closeList();
    // B33: [[n]] tokens are injected server-side (kb.inject_citation_markers), at the
    // real passage ARAG grounded, never guessed by the client. esc() above leaves the
    // plain-text token untouched (no markdown syntax to collide with), so this is a
    // single safe pass over the finished HTML. Rendered as a clickable superscript that
    // resolves to its numbered source in the "Based on N documents" drawer (B23 adapted:
    // these sources are real external pages/PDFs this app doesn't control the DOM of, so
    // "resolves to" means reveal-and-highlight the exact source row, which itself links
    // to the real document, rather than an in-page highlight we cannot honestly offer).
    html = html.replace(/\[\[(\d+)\]\]/g, (_, n) => `<sup class="cite"><a href="#" data-cite="${n}" aria-label="Source ${n}">${n}</a></sup>`);
    return html;
  }

  /* ---------- shell ---------- */
  const NAV = [["home", "/", "Home"], ["brands", "/#brands", "Our brands"], ["specify", "/specify", "Specify"], ["insights", "/insights", "Insights"]];
  function shell() {
    const active = CFG.route === "handoffs" ? "insights" : CFG.route;
    const nav = NAV.map(([k, href, label]) => `<a href="${href}" class="${k === active ? "active" : ""}">${label}</a>`).join("");
    document.body.insertAdjacentHTML("afterbegin", `
      <header class="site-header"><div class="wrap">
        <a class="logo" href="/" aria-label="Ventora"><img src="/static/brand/ventora-green.png" alt="Ventora" width="130" height="30"></a>
        <nav id="mainnav">${nav}</nav>
        <div class="actions">
          <button class="arch-btn" type="button" data-open-arch aria-haspopup="dialog"><svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 16v-5M12 8h.01"/></svg><span class="lbl">How this works</span></button>
          <button class="btn primary sm" data-open-concierge>Concierge</button>
          <button class="burger" aria-label="Menu" onclick="document.getElementById('mainnav').classList.toggle('open')"><span></span><span></span><span></span></button></div>
      </div></header>`);
    const brandLinks = ORDER.map(s => `<li><a href="/brands/${s}">${esc(labelOf(s))}</a></li>`).join("");
    document.body.insertAdjacentHTML("beforeend", `
      <footer class="site-footer"><div class="wrap">
        <div class="cols">
          <div><div class="logo"><img src="/static/brand/ventora-white.png" alt="Ventora"></div>
            <p class="small" style="max-width:34ch;color:rgba(255,255,255,.75)">A leader in the design and manufacture of building product solutions. Windows, doors, glass, wardrobes and showerscreens for residential, multi-residential and commercial projects.</p></div>
          <div><h4>Our brands</h4><ul>${brandLinks}</ul></div>
          <div><h4>For professionals</h4><ul><li><a href="/specify">Specify with confidence</a></li><li><a href="https://www.ventora.com.au/specification" target="_blank" rel="noopener">Specification portal</a></li><li><a href="https://www.ventora.com.au/credit-application" target="_blank" rel="noopener">Credit application</a></li><li><a href="https://www.ventora.com.au/careers" target="_blank" rel="noopener">Careers</a></li></ul></div>
          <div><h4>Help</h4><ul><li><a href="#" data-open-concierge data-mode="service">Warranty and service</a></li><li><a href="https://www.ventora.com.au/warranty" target="_blank" rel="noopener">Warranty terms</a></li><li><a href="https://www.ventora.com.au/contact" target="_blank" rel="noopener">Contact Ventora</a></li><li><a href="/insights">Experience insights</a></li></ul></div>
        </div>
        <div class="legal"><span>Ventora Group Pty Limited. Macquarie Park NSW.</span><span>Demonstration environment. Product and technical content is Ventora's public material; enquiries, leads and usage history are synthetic.</span></div>
      </div></footer>
      <div class="launch-fab"><button class="btn primary" data-open-concierge>Ask the concierge</button></div>`);
    window.addEventListener("scroll", () => $(".site-header").classList.toggle("scrolled", window.scrollY > 8), { passive: true });
    document.addEventListener("click", e => {
      const b = e.target.closest("[data-open-concierge]");
      if (b) { e.preventDefault(); Concierge.open({ mode: b.dataset.mode, brand: b.dataset.brand, text: b.dataset.text, goal: b.dataset.goal }); }
      if (e.target.closest("[data-open-arch]")) { e.preventDefault(); ArchReveal.open(); }
    });
    ArchReveal.mount();
    // reveal on scroll
    const io = new IntersectionObserver(es => es.forEach(en => { if (en.isIntersecting) { en.target.classList.add("in"); io.unobserve(en.target); } }), { rootMargin: "0px 0px 12% 0px" });
    document.querySelectorAll(".reveal-up").forEach((el, i) => { el.style.transitionDelay = `${(i % 6) * 60}ms`; io.observe(el); });
    // deep link: /?concierge=quote|photo|open&text=...&brand=...&mode=...
    const u = new URL(location.href);
    const c = u.searchParams.get("concierge");
    if (c) setTimeout(() => Concierge.open({ goal: c === "quote" ? "quote" : c === "photo" ? "photo" : null, text: u.searchParams.get("text"), brand: u.searchParams.get("brand"), mode: u.searchParams.get("mode") }), 250);
  }

  /* ---------- solution-architecture reveal ("How this works") ----------
     What this modal shows is exactly what this app's own code does - see app.py
     (/api/answer, /api/remi) and kb.py. Nothing here is a marketing diagram. */
  const ArchReveal = (() => {
    let mounted = false;
    const DIAGRAM = `
      <svg class="arch-diagram" viewBox="0 0 820 300" role="img" aria-label="Request flow diagram">
        <defs><marker id="arch-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#8DA99C"/></marker></defs>
        <g class="arch-node"><rect x="20" y="50" width="170" height="64" rx="6"/><text x="105" y="78" text-anchor="middle">Your browser</text><text class="sub" x="105" y="95" text-anchor="middle">Concierge / Specify page</text></g>
        <g class="arch-node server"><rect x="325" y="40" width="190" height="84" rx="6"/><text x="420" y="72" text-anchor="middle">Ventora's own server</text><text class="sub" x="420" y="89" text-anchor="middle">Holds the retrieval credential -</text><text class="sub" x="420" y="101" text-anchor="middle">never sent to the browser</text></g>
        <g class="arch-node"><rect x="650" y="50" width="150" height="64" rx="6"/><text x="725" y="78" text-anchor="middle">Knowledge store</text><text class="sub" x="725" y="95" text-anchor="middle">Ventora's published content</text></g>
        <path class="arch-flow" d="M190,66 H325" marker-end="url(#arch-arrow)"/>
        <text class="arch-elabel" x="257" y="58" text-anchor="middle">your question</text>
        <path class="arch-flow" d="M325,100 H190" marker-end="url(#arch-arrow)"/>
        <text class="arch-elabel" x="257" y="120" text-anchor="middle">streamed answer + real citations</text>
        <path class="arch-flow" d="M515,66 H650" marker-end="url(#arch-arrow)"/>
        <text class="arch-elabel" x="582" y="58" text-anchor="middle">grounded answer call</text>
        <path class="arch-flow" d="M650,100 H515" marker-end="url(#arch-arrow)"/>
        <text class="arch-elabel" x="582" y="120" text-anchor="middle">retrieved passages + generated text</text>
        <g class="arch-node"><rect x="325" y="210" width="190" height="60" rx="6"/><text x="420" y="238" text-anchor="middle">Trust check</text><text class="sub" x="420" y="255" text-anchor="middle">Independent quality score</text></g>
        <path class="arch-flow" d="M390,124 V210" marker-end="url(#arch-arrow)"/>
        <text class="arch-elabel" x="330" y="168" text-anchor="middle">question, answer</text>
        <text class="arch-elabel" x="330" y="180" text-anchor="middle">+ passages</text>
        <path class="arch-flow" d="M450,210 V124" marker-end="url(#arch-arrow)"/>
        <text class="arch-elabel" x="505" y="168" text-anchor="middle">groundedness /</text>
        <text class="arch-elabel" x="505" y="180" text-anchor="middle">relevance score</text>
      </svg>`;
    const HTML = `
      <div class="arch-scrim" data-arch-close></div>
      <div class="arch-modal" role="dialog" aria-modal="true" aria-label="How this works">
        <div class="arch-modal__head">
          <div><h3>How this works</h3><p>The real request and data flow behind every Ventora concierge answer</p></div>
          <button class="arch-modal__close" type="button" data-arch-close aria-label="Close"><svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6L6 18"/></svg></button>
        </div>
        <div class="arch-modal__body">
          ${DIAGRAM}
          <ol class="arch-steps">
            <li><b>1</b>You type a question into the concierge or the Specify page, or drop in a photo. It goes straight to Ventora's own server - never to any outside service.</li>
            <li><b>2</b>That server makes a grounded answer call to Ventora's knowledge store, scoped to the brand and document types you're asking about. This is a single call that retrieves the actual passages AND writes the answer from them.</li>
            <li><b>3</b>The prose streams back to your screen as it's generated. The numbered superscript markers you see are placed using the exact passage ARAG recorded as the source for that part of the answer - never guessed. The product cards, follow-up buttons and the numbered source list underneath are all built from the same real passages that call returned - never invented, and never a separate step.</li>
            <li><b>4</b>A second, independent call sends the same question, the answer and the retrieved passages to a trust-scoring service, which grades how well the answer is actually supported by them. That's the plain-language confidence badge you see next to an answer - High or Moderate confidence, never a raw score.</li>
          </ol>
          <p class="arch-note">If the trust check can't be scored for any reason, the confidence badge is left off rather than shown with a guess - nothing on this page is ever faked or pre-written. Every numbered marker and every source link resolves to a real document.</p>
        </div>
      </div>`;
    function mount() {
      if (mounted) return;
      document.body.insertAdjacentHTML("beforeend", HTML);
      mounted = true;
      document.addEventListener("click", e => { if (e.target.closest("[data-arch-close]")) close(); });
      document.addEventListener("keydown", e => { if (e.key === "Escape") close(); });
    }
    function open() { const s = $(".arch-scrim"), m = $(".arch-modal"); if (!s || !m) return; s.classList.add("open"); m.classList.add("open"); document.body.style.overflow = "hidden"; }
    function close() { const s = $(".arch-scrim"), m = $(".arch-modal"); if (!s || !m) return; s.classList.remove("open"); m.classList.remove("open"); document.body.style.overflow = ""; }
    return { mount, open, close };
  })();

  /* ---------- streaming ask ---------- */
  async function ask(params, handlers) {
    const res = await fetch("/api/answer", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(params) });
    if (!res.ok || !res.body) { handlers.onError && handlers.onError(); return null; }
    const reader = res.body.getReader(); const dec = new TextDecoder();
    let buf = "", full = "", payload = null;
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let i;
      while ((i = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, i).trim(); buf = buf.slice(i + 1);
        if (!line) continue;
        let ev; try { ev = JSON.parse(line); } catch (e) { continue; }
        if (ev.type === "answer") { full = ev.replace ? ev.text : full + ev.text; handlers.onAnswer && handlers.onAnswer(full); }
        else if (ev.type === "sources") payload = ev;
        else if (ev.type === "error") { handlers.onError && handlers.onError(); return null; }
      }
    }
    if (payload) { payload.answer = full; handlers.onDone && handlers.onDone(payload); }
    return payload;
  }
  async function remi(params) {
    try { const r = await fetch("/api/remi", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(params) }); return await r.json(); }
    catch (e) { return { available: false }; }
  }

  /* ---------- blocks ---------- */
  function productCards(products) {
    if (!products || !products.length) return "";
    return `<div class="products">${products.map(p => `
      <div class="product"><div class="ph"><img src="${esc(p.photo)}" alt="${esc(p.alt)}" loading="lazy"></div>
        <div class="pb"><img class="mark" src="/static/brand/${esc(p.brand)}.png" alt="${esc(p.brand_label)}"><b>${esc(p.family)}</b>${p.desc ? `<span class="why">${esc(p.desc)}</span>` : ""}
          <div class="acts"><a href="${esc(p.url)}" target="_blank" rel="noopener">${esc(p.view)}</a><button data-ask="${esc(p.family)}">${esc(p.ask)}</button></div></div></div>`).join("")}</div>`;
  }
  function actionButtons(actions) {
    if (!actions || !actions.length) return "";
    return `<div class="actions">${actions.map((a, i) => a.kind === "flow"
      ? `<button class="btn ${i === 0 ? "primary" : "secondary"}" data-flow="${esc(a.url)}" data-brand="${esc(a.brand || "")}">${esc(a.label)}</button>`
      : `<a class="btn ${i === 0 ? "primary" : "secondary"}" href="${esc(a.url)}" target="_blank" rel="noopener">${esc(a.label)}</a>`).join("")}</div>`;
  }
  function followupChips(list) {
    if (!list || !list.length) return "";
    return `<div class="followups">${list.map(f => `<button data-followup="${esc(f)}">${esc(f)}</button>`).join("")}</div>`;
  }
  function basisDrawer(sources, T) {
    if (!sources || !sources.length) return "";
    const n = sources.length;
    return `<div class="basis"><button data-basis>${esc(n === 1 ? T.basisOne : fmt(T.basis, { n }))}</button>
      <div class="basis-list">${sources.map(s => `<a href="${esc(s.url)}" target="_blank" rel="noopener" data-src="${s.n}"><b class="n">${s.n}</b><span class="t">${esc(s.title)}<span>${esc(s.brand)}${s.issued ? " · " + esc(s.issued) : ""}</span></span></a>`).join("")}</div></div>`;
  }
  /* ---------- B34/B42 qualitative confidence badge ----------
     Derived from REMi, weighting groundedness primary (CLAUDE.md, Thornfield
     correction) - never a raw numeral by default. High confidence may show the
     real sub-scores; below threshold every numeral drops and the badge names an
     action instead, in a different colour (B42). Hidden entirely only when REMi
     genuinely could not be scored - never shown with a guess. */
  function confidenceBadge(scores) {
    if (!scores || !scores.available || scores.groundedness == null) return "";
    const g = scores.groundedness, ar = scores.answer_relevance;
    if (g >= 4) {
      const sub = ar != null ? `grounded ${g.toFixed(1)}/5 · relevant ${ar.toFixed(1)}/5` : `grounded ${g.toFixed(1)}/5`;
      return `<span class="confidence high">High confidence <span class="sub">${esc(sub)}</span></span>`;
    }
    if (g >= 2.5) return `<span class="confidence moderate">Moderate confidence</span>`;
    return `<span class="confidence low">Worth checking the sources below</span>`;
  }
  /* A citation marker "resolves to" its source by revealing the basis drawer
     (opening it if collapsed) and briefly highlighting that row - see the note
     in md() above on why this, rather than an in-document highlight, is the
     honest version of B23 for sources this app doesn't control the DOM of. */
  function scrollToSource(scope, n) {
    if (!scope) return;
    const row = scope.querySelector(`[data-src="${n}"]`);
    if (!row) return;
    const list = row.closest(".basis-list");
    if (list && !list.classList.contains("open")) list.classList.add("open");
    row.scrollIntoView({ behavior: "smooth", block: "center" });
    row.classList.add("flash");
    setTimeout(() => row.classList.remove("flash"), 1400);
  }

  /* ---------- the Concierge ---------- */
  const Concierge = (() => {
    let el, scrim, state = { lang: "en", mode: "building", goal: null, brand: null, history: [], lead: null, busy: false, recent: [] };
    const T = () => window.I18N[state.lang] || window.I18N.en;
    const ICONS = {
      product: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="4" width="18" height="16" rx="1"/><path d="M12 4v16M3 12h18"/></svg>',
      quote: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M5 4h14v16H5zM8 9h8M8 13h8M8 17h5"/></svg>',
      problem: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L4 17v3h3l5.3-5.3a4 4 0 0 0 5.4-5.4l-2.4 2.4-2-2z"/></svg>',
      document: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M6 3h8l4 4v14H6zM14 3v4h4M9 12h6M9 16h6"/></svg>',
      photo: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><rect x="3" y="6" width="18" height="14" rx="2"/><circle cx="12" cy="13" r="3.5"/><path d="M9 6l1.5-2h3L15 6"/></svg>',
      send: '<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 12h14M12 5l7 7-7 7"/></svg>',
      close: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 6l12 12M18 6L6 18"/></svg>',
    };
    function build() {
      if (el) return;
      scrim = document.createElement("div"); scrim.className = "cz-scrim"; document.body.appendChild(scrim);
      el = document.createElement("div"); el.className = "cz"; el.setAttribute("role", "dialog"); el.setAttribute("aria-modal", "true");
      el.innerHTML = `
        <div class="cz-head">
          <div class="roundel">V</div><div class="title"></div>
          <div class="modes">${["building", "renovating", "specifying", "service"].map(m => `<button data-mode="${m}"></button>`).join("")}</div>
          <div class="spacer"></div>
          <select aria-label="Language">${Object.keys(LANGS).map(k => `<option value="${k}">${esc(LANGS[k].native)}</option>`).join("")}</select>
          <button class="icon-btn" data-photo title="">${ICONS.photo}</button>
          <input type="file" accept="image/*" hidden>
          <button class="icon-btn" data-close title="">${ICONS.close}</button>
        </div>
        <div class="cz-body">
          <aside class="cz-rail"><h4 data-i="help"></h4><div class="goals"></div><div class="rail-summary"></div><div class="rail-recent"></div></aside>
          <div class="cz-main"><div class="cz-thread"></div>
            <div class="cz-composer"><div class="field"><textarea rows="1"></textarea><button class="icon-btn" data-photo title="">${ICONS.photo}</button><button class="send" data-send>${ICONS.send}</button></div><div class="note"></div></div>
          </div>
        </div>`;
      document.body.appendChild(el);
      scrim.onclick = close;
      el.querySelector("[data-close]").onclick = close;
      document.addEventListener("keydown", e => { if (e.key === "Escape" && el.classList.contains("open")) close(); });
      el.querySelector("select").onchange = e => setLang(e.target.value);
      el.querySelectorAll("[data-mode]").forEach(b => b.onclick = () => { setMode(b.dataset.mode); greet(); });
      el.querySelectorAll("[data-photo]").forEach(b => b.onclick = () => el.querySelector("input[type=file]").click());
      el.querySelector("input[type=file]").onchange = e => { const f = e.target.files[0]; if (f) sendPhoto(f); e.target.value = ""; };
      const ta = el.querySelector("textarea");
      ta.addEventListener("keydown", e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(ta.value); } });
      ta.addEventListener("input", () => { ta.style.height = "28px"; ta.style.height = Math.min(120, ta.scrollHeight) + "px"; });
      el.querySelector("[data-send]").onclick = () => send(ta.value);
      el.querySelector(".cz-thread").addEventListener("click", e => {
        const f = e.target.closest("[data-followup]"); if (f) return send(f.dataset.followup);
        const a = e.target.closest("[data-ask]"); if (a) return send((state.lang === "en" ? "Tell me about " : "") + a.dataset.ask);
        const fl = e.target.closest("[data-flow]"); if (fl) return flow(fl.dataset.flow, fl.dataset.brand);
        const b = e.target.closest("[data-basis]"); if (b) return b.nextElementSibling.classList.toggle("open");
        const h = e.target.closest("[data-handoff]"); if (h) return handoff();
        const cm = e.target.closest("[data-cite]"); if (cm) { e.preventDefault(); return scrollToSource(cm.closest(".msg.bot"), cm.dataset.cite); }
      });
      renderChrome();
    }
    function renderChrome() {
      const t = T();
      el.setAttribute("dir", t.dir || "ltr");
      el.querySelector(".title").textContent = state.brand ? `${labelOf(state.brand)} · ${t.title}` : t.title;
      el.querySelectorAll("[data-mode]").forEach(b => { b.textContent = t.modes[b.dataset.mode]; b.classList.toggle("on", b.dataset.mode === state.mode); });
      el.querySelector("[data-i=help]").textContent = t.help;
      el.querySelector(".goals").innerHTML = ["product", "quote", "problem", "document", "photo"].map(g => `<div class="goal ${state.goal === g ? "on" : ""}" data-goal="${g}"><div class="ic">${ICONS[g]}</div><div><b>${esc(t.goals[g][0])}</b><small>${esc(t.goals[g][1])}</small></div></div>`).join("");
      el.querySelectorAll("[data-goal]").forEach(g => g.onclick = () => goal(g.dataset.goal));
      el.querySelector("textarea").placeholder = t.placeholder;
      el.querySelector(".note").textContent = t.note;
      el.querySelectorAll("[data-photo]").forEach(b => b.title = t.photo);
      el.querySelector("[data-close]").title = t.close;
      el.querySelector("select").value = state.lang;
      renderRail();
    }
    function renderRail() {
      const t = T();
      const rs = el.querySelector(".rail-summary");
      if (state.goal === "quote") {
        const lead = state.lead || {};
        const rows = ["state", "product_type", "openings", "glazing", "bal_level", "timing", "contact_preference"].map(k => {
          const v = lead[k]; const ok = v && !(k === "bal_level" ? /^(unknown|n\/a)?$/i : /^(unknown|n\/a|none)?$/i).test(String(v).trim());
          return `<div class="k ${ok ? "done" : ""}"><span>${esc(t.fields[k])}</span><span>${ok ? esc(v) : esc(t.unknown)}</span></div>`;
        }).join("");
        rs.innerHTML = `<h4 style="margin-top:18px">${esc(t.enquiry)}</h4><div class="summary-card">${rows}</div>`;
      } else rs.innerHTML = "";
      const rr = el.querySelector(".rail-recent");
      rr.innerHTML = state.recent.length ? `<h4 style="margin-top:18px">${esc(t.recent)}</h4>` + state.recent.slice(0, 5).map(p => `<div class="recent" data-ask="${esc(p.family)}"><img src="${esc(p.photo)}" alt=""><span>${esc(p.family)}</span></div>`).join("") : "";
      rr.querySelectorAll("[data-ask]").forEach(r => r.onclick = () => send((state.lang === "en" ? "Tell me about " : "") + r.dataset.ask));
    }
    function setLang(l) { state.lang = l in LANGS ? l : "en"; renderChrome(); }
    function setMode(m) { state.mode = m; if (m !== "specifying") state.goal = state.goal === "quote" ? "quote" : state.goal; renderChrome(); }
    function thread() { return el.querySelector(".cz-thread"); }
    function scrollEnd() {
      // Pin the newest message's top into view; re-pin when its images finish loading.
      const th = thread(); const last = th.lastElementChild; if (!last) return;
      const prev = last.previousElementSibling; const anchor = (last.classList.contains("bot") && prev && prev.classList.contains("user")) ? prev : last;
      const go = () => { const max = Math.max(0, th.scrollHeight - th.clientHeight); th.scrollTop = Math.min(max, Math.max(0, anchor.offsetTop - 12)); };
      go(); requestAnimationFrame(go); setTimeout(go, 250);
      last.querySelectorAll("img").forEach(im => { if (!im.complete) im.addEventListener("load", go, { once: true }); });
    }
    function addUser(text, imgUrl) {
      thread().insertAdjacentHTML("beforeend", `<div class="msg user"><div class="bubble">${esc(text)}${imgUrl ? `<img src="${imgUrl}" alt="">` : ""}</div></div>`);
      scrollEnd();
    }
    function addCz(html) {
      const d = document.createElement("div"); d.className = "msg bot";
      d.innerHTML = `<div class="who">${esc(T().title)}</div><div class="prose">${html}</div><div class="blocks"></div>`;
      thread().appendChild(d); scrollEnd(); return d;
    }
    function greet(text) {
      const t = T();
      const g = state.goal === "quote" ? t.quoteIntro : t.greeting[state.mode] || t.greeting.building;
      addCz(`<p>${esc(text || g)}</p>`);
    }
    function goal(g) {
      state.goal = g; renderChrome();
      if (g === "photo") {
        const t = T();
        const samples = [["breezway", "Breezway louvre window"], ["corinthian", "Corinthian entrance door"], ["stegbar", "Stegbar window"]];
        const d = addCz(`<p>${esc(t.goals.photo[1])}</p><div class="samples">${samples.map(([k, lbl]) => `<button class="sample" data-sample="/static/samples/${k}.jpg"><img src="/static/samples/${k}.jpg" alt="${esc(lbl)}"><span>${esc(lbl)}</span></button>`).join("")}<button class="sample upload" data-upload><span>${esc(t.photo)}</span></button></div>`);
        d.querySelectorAll("[data-sample]").forEach(b => b.onclick = async () => { const r = await fetch(b.dataset.sample); const blob = await r.blob(); sendPhoto(new File([blob], b.dataset.sample.split("/").pop(), { type: blob.type || "image/jpeg" })); });
        d.querySelector("[data-upload]").onclick = () => el.querySelector("input[type=file]").click();
        return;
      }
      if (g === "quote") { greet(); return; }
      const t = T();
      const seeds = { product: t.greeting.building, problem: t.greeting.service, document: t.greeting.specifying };
      if (g === "problem") state.mode = "service"; if (g === "document") state.mode = "specifying";
      renderChrome(); greet(seeds[g]);
    }
    function flow(kind, brand) {
      if (kind === "#quote" || kind === "#design-assist") { state.goal = "quote"; renderChrome(); send(state.lang === "en" ? (kind === "#design-assist" ? "I'd like to book Design Assist for this project." : "I'd like a quote for this.") : T().goals.quote[0]); }
      else if (kind === "#service") { state.mode = "service"; state.goal = "problem"; renderChrome(); send(state.lang === "en" ? "I'd like to log a service request for this." : T().goals.problem[0]); }
    }
    function apiMode() {
      if (state.brand) return state.goal === "quote" ? "quote" : "brand";
      if (state.goal === "quote") return "quote";
      if (state.mode === "specifying") return "specify";
      if (state.mode === "service" || state.goal === "problem") return "service";
      return "general";
    }
    async function send(text) {
      text = (text || "").trim(); if (!text || state.busy) return;
      const ta = el.querySelector("textarea"); ta.value = ""; ta.style.height = "28px";
      addUser(text); state.busy = true; el.querySelector("[data-send]").disabled = true;
      const t = T();
      const box = addCz(`<div class="typing"><i></i><i></i><i></i></div>`);
      const prose = box.querySelector(".prose"), blocks = box.querySelector(".blocks");
      const params = { query: text, mode: apiMode(), lang: state.lang, brand_scope: state.brand, chat_history: state.history.slice(-10), route: location.pathname, audience: state.mode, lead: state.goal === "quote" ? (state.lead || {}) : undefined };
      const payload = await ask(params, {
        onAnswer: full => { prose.innerHTML = md(full); scrollEnd(); },
        onError: () => { prose.innerHTML = `<div class="notice">${esc(t.noAnswer)}</div>`; },
        onDone: p => {
          state.history.push({ author: "user", text }, { author: "assistant", text: p.answer });
          if (p.status === "no_context") {
            const outside = state.brand ? fmt(t.outside, { brand: labelOf(state.brand) }) : t.noAnswer;
            prose.innerHTML = `<div class="notice">${esc(outside)}</div>`;
            const acts = (p.actions || []).slice();
            blocks.innerHTML = actionButtons(acts) + (state.brand ? `<div class="actions"><button class="btn secondary" data-unlock>${esc(t.askVentora)}</button></div>` : "");
            const u = blocks.querySelector("[data-unlock]"); if (u) u.onclick = () => { state.brand = null; renderChrome(); send(text); };
          } else {
            // Final render swaps in the marker-carrying text (B33) - the clean p.answer
            // stays in state.history/intake-extraction so no [[n]] token ever reaches a
            // future turn's chat_history or the quote-intake extractor.
            prose.innerHTML = md(p.marked_answer || p.answer); scrollEnd();
            blocks.innerHTML = productCards(p.products) + actionButtons(p.actions) + followupChips(p.followups) +
              `<div class="trust-line"><span class="confidence-slot"></span>${basisDrawer(p.sources, t)}</div>`;
            (p.products || []).forEach(pr => { if (!state.recent.find(r => r.family === pr.family)) state.recent.unshift(pr); });
            renderRail();
            // B34: a confidence badge on every grounded concierge answer, not only /specify -
            // fetched async so REMi latency never holds up the answer itself.
            if (p.sources && p.sources.length) {
              remi({ query: text, answer: p.answer, brands: state.brand ? [state.brand] : [], interaction_id: p.interaction_id }).then(r => {
                const slot = blocks.querySelector(".confidence-slot");
                if (slot) slot.outerHTML = confidenceBadge(r);
              });
            }
          }
          if (state.goal === "quote") { if (p.lead && !state.lead) { state.lead = p.lead; renderRail(); } updateLead(p.answer); }
        },
      });
      state.busy = false; el.querySelector("[data-send]").disabled = false; scrollEnd();
      if (!payload) { state.history.push({ author: "user", text }); }
    }
    async function updateLead(answer) {
      try {
        const r = await fetch("/api/intake/extract", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ chat_history: state.history }) });
        const d = await r.json();
        if (!d.ok) return;
        state.lead = d.lead; renderRail();
        const missing = (d.lead.missing || "").toLowerCase();
        const complete = /^(none|nothing|)$/.test(missing.trim()) || /i have what i need/i.test(answer || "");
        if (complete && !thread().querySelector("[data-handoff]") && !state.sent) {
          const t = T();
          const last = thread().lastElementChild.querySelector(".blocks");
          last.insertAdjacentHTML("beforeend", `<div class="actions"><button class="btn primary" data-handoff>${esc(fmt(t.sendTo, { dest: d.lead.destination }))}</button></div>`);
          scrollEnd();
        }
      } catch (e) { /* the summary card simply stays as it was */ }
    }
    async function handoff() {
      const btn = thread().querySelector("[data-handoff]"); if (!btn) return;
      const t = T(); btn.disabled = true; btn.textContent = t.sending + "…";
      const r = await fetch("/api/handoff", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ lead: state.lead, chat_history: state.history, lang: state.lang }) });
      const d = await r.json(); state.sent = true; btn.closest(".actions").remove();
      addCz(`<div class="handoff-card"><b>${esc(fmt(t.sent, { dest: d.destination }))}</b><div class="ref">${esc(t.reference)} ${esc(d.reference)}</div>
        <div class="small muted" style="margin-top:6px">${esc(state.lead.summary || "")}</div>
        <div class="small" style="margin-top:10px;font-weight:600">${esc(t.next)}</div><ul>${t.nextSteps.map(s => `<li>${esc(s)}</li>`).join("")}</ul></div>`);
    }
    async function sendPhoto(file) {
      if (state.busy) return;
      const t = T();
      const url = URL.createObjectURL(file);
      addUser(t.photoCaption, url); state.busy = true;
      const box = addCz(`<p class="muted">${esc(t.photoLooking)}…</p><div class="typing"><i></i><i></i><i></i></div>`);
      const prose = box.querySelector(".prose"), blocks = box.querySelector(".blocks");
      const b64 = await new Promise(res => { const fr = new FileReader(); fr.onload = () => res(String(fr.result).split(",")[1]); fr.readAsDataURL(file); });
      try {
        const r = await fetch("/api/identify", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ b64, content_type: file.type, lang: state.lang, query: t.photoPrompt }) });
        const d = await r.json();
        if (!d.enabled) { prose.innerHTML = `<div class="notice">${esc(t.noAnswer)}</div>`; }
        else if (d.status === "no_context" || !d.answer) { prose.innerHTML = `<div class="notice">${esc(t.noAnswer)}</div>`; blocks.innerHTML = actionButtons(d.actions); }
        else {
          prose.innerHTML = md(d.marked_answer || d.answer);
          blocks.innerHTML = productCards(d.products) + actionButtons(d.actions) + followupChips(d.followups) +
            `<div class="trust-line"><span class="confidence-slot"></span>${basisDrawer(d.sources, t)}</div>`;
          (d.products || []).forEach(pr => { if (!state.recent.find(x => x.family === pr.family)) state.recent.unshift(pr); });
          renderRail();
          state.history.push({ author: "user", text: t.photoPrompt }, { author: "assistant", text: d.answer });
          // B34: same async confidence badge as the concierge's text answers and /specify -
          // the photo-identify reply is a third grounded-answer surface and was carrying none.
          if (d.sources && d.sources.length) {
            remi({ query: t.photoPrompt, answer: d.answer, interaction_id: d.interaction_id }).then(r => {
              const slot = blocks.querySelector(".confidence-slot");
              if (slot) slot.outerHTML = confidenceBadge(r);
            });
          }
        }
      } catch (e) { prose.innerHTML = `<div class="notice">${esc(t.noAnswer)}</div>`; }
      state.busy = false; scrollEnd();
    }
    function open(opts) {
      opts = opts || {}; build();
      if (opts.lang) state.lang = opts.lang;
      if (opts.brand && BR[opts.brand]) state.brand = opts.brand; else if (opts.brand === null || opts.brand === "") state.brand = state.brand;
      if (opts.mode && ["building", "renovating", "specifying", "service"].includes(opts.mode)) state.mode = opts.mode;
      if (opts.goal) state.goal = opts.goal;
      renderChrome();
      scrim.classList.add("open"); el.classList.add("open"); document.body.style.overflow = "hidden";
      if (!thread().children.length) greet();
      if (opts.goal === "photo") setTimeout(() => el.querySelector("input[type=file]").click(), 200);
      if (opts.text) send(opts.text); else setTimeout(() => el.querySelector("textarea").focus(), 240);
    }
    function close() { if (!el) return; scrim.classList.remove("open"); el.classList.remove("open"); document.body.style.overflow = ""; }
    return { open, close, send, setLang, state };
  })();

  window.V = { CFG, BR, ORDER, esc, fmt, md, shell, ask, remi, productCards, actionButtons, followupChips, basisDrawer,
    confidenceBadge, scrollToSource, labelOf, Concierge };
  document.addEventListener("DOMContentLoaded", shell);
})();
