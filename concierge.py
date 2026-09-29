"""Concierge composition: turns a grounded answer plus the material it used into the
blocks the customer sees - product cards (with Ventora's own photography), action
buttons that lead somewhere real, follow-up prompts - in the customer's language.

Everything here is deterministic. The model writes the prose; it never invents a URL.
"""
import json
import re
from pathlib import Path

import kb

ROOT = Path(__file__).resolve().parent
PHOTOS = json.loads((ROOT / "static" / "photos" / "photos.json").read_text())
FAMILIES = json.loads((ROOT / "static" / "photos" / "families.json").read_text())

# Real destinations on the brand sites (verified 11 Sep 2026). None of these is invented.
BRAND_LINKS = {
    "stegbar": {"quote": "https://www.stegbar.com.au/#enquire-now", "locate": "https://www.stegbar.com.au/pages/store-locator",
                "care": "https://www.stegbar.com.au/pages/care-and-maintenance-centre", "warranty": "https://www.stegbar.com.au/pages/warranty",
                "parts": "https://www.stegbar.com.au/collections/spare-parts", "contact": "https://www.stegbar.com.au/pages/store-locator",
                "locate_label": "showroom"},
    "al-windows": {"quote": "https://www.alwindows.com.au/contacts/", "locate": "https://www.alwindows.com.au/contacts/find-a-display/",
                   "care": "https://www.alwindows.com.au/resources/product-care/", "warranty": "https://www.alwindows.com.au/about-us/warranty/",
                   "parts": "https://www.alwindows.com.au/spare-parts/", "contact": "https://www.alwindows.com.au/contacts/",
                   "locate_label": "display centre"},
    "corinthian": {"quote": "https://www.corinthian.com.au/retailers/", "locate": "https://www.corinthian.com.au/retailers/",
                   "care": "https://www.corinthian.com.au/care-and-maintenance/", "warranty": "https://www.corinthian.com.au/warranty/",
                   "parts": "https://www.corinthian.com.au/care-and-maintenance/", "contact": "https://www.corinthian.com.au/contact/",
                   "locate_label": "retailer"},
    "trend": {"quote": "https://www.trendwindows.com.au/pages/enquiry", "locate": "https://www.trendwindows.com.au/pages/showrooms",
              "care": "https://www.trendwindows.com.au/pages/product-care", "warranty": "https://www.trendwindows.com.au/pages/warranty",
              "parts": "https://www.trendwindows.com.au/pages/product-care", "contact": "https://www.trendwindows.com.au/pages/contact-us",
              "locate_label": "showroom"},
    "aneeta": {"quote": "https://aneetawindows.com.au/contact/", "locate": "https://aneetawindows.com.au/contact/",
               "care": "https://aneetawindows.com.au/technical/care-maintenance/", "warranty": "https://aneetawindows.com.au/technical/warranty/",
               "parts": "https://aneetawindows.com.au/technical/care-maintenance/", "contact": "https://aneetawindows.com.au/contact/",
               "locate_label": "distributor"},
    "breezway": {"quote": "https://www.breezway.com.au/view-buy/", "locate": "https://www.breezway.com.au/view-buy/",
                 "care": "https://www.breezway.com.au/technical/care-maintenance-warranty/", "warranty": "https://www.breezway.com.au/technical/care-maintenance-warranty/",
                 "parts": "https://www.breezway.com.au/technical/care-maintenance-warranty/", "contact": "https://www.breezway.com.au/contact/",
                 "locate_label": "fabricator"},
    "regency": {"quote": "https://www.regencyscreens.com.au/pages/enquiry", "locate": "https://www.regencyscreens.com.au/pages/store-locator",
                "care": "https://www.regencyscreens.com.au/pages/help-support", "warranty": "https://www.regencyscreens.com.au/pages/warranty",
                "parts": "https://www.regencyscreens.com.au/pages/help-support", "contact": "https://www.regencyscreens.com.au/pages/contact",
                "locate_label": "showroom"},
    "ventora-glass": {"quote": "https://ventoraglass.com.au/pages/request-a-quote", "locate": "https://ventoraglass.com.au/pages/contact",
                      "care": "https://ventoraglass.com.au/pages/warranty", "warranty": "https://ventoraglass.com.au/pages/warranty",
                      "parts": "https://ventoraglass.com.au/pages/contact", "contact": "https://ventoraglass.com.au/pages/contact",
                      "locate_label": "office"},
    "ventora": {"quote": "https://www.ventora.com.au/contact", "locate": "https://www.ventora.com.au/brands",
                "care": "https://www.ventora.com.au/warranty", "warranty": "https://www.ventora.com.au/warranty",
                "parts": "https://www.ventora.com.au/contact", "contact": "https://www.ventora.com.au/contact", "locate_label": "brand"},
}

LANGS = {
    "en": {"name": "English", "native": "English", "rtl": False},
    "zh": {"name": "Simplified Chinese", "native": "中文", "rtl": False},
    "vi": {"name": "Vietnamese", "native": "Tiếng Việt", "rtl": False},
    "ar": {"name": "Arabic", "native": "العربية", "rtl": True},
    "el": {"name": "Greek", "native": "Ελληνικά", "rtl": False},
    "it": {"name": "Italian", "native": "Italiano", "rtl": False},
    "hi": {"name": "Hindi", "native": "हिन्दी", "rtl": False},
}

# Fixed button labels in every supported language. Document titles stay as published.
L = {
    "quote":    {"en": "Get a quote", "zh": "获取报价", "vi": "Nhận báo giá", "ar": "اطلب عرض سعر", "el": "Ζητήστε προσφορά", "it": "Richiedi un preventivo", "hi": "कोटेशन प्राप्त करें"},
    "locate":   {"en": "Find a {what}", "zh": "查找{what}", "vi": "Tìm {what}", "ar": "ابحث عن {what}", "el": "Βρείτε {what}", "it": "Trova {what}", "hi": "{what} खोजें"},
    "download": {"en": "Download {doc}", "zh": "下载 {doc}", "vi": "Tải xuống {doc}", "ar": "تنزيل {doc}", "el": "Λήψη {doc}", "it": "Scarica {doc}", "hi": "{doc} डाउनलोड करें"},
    "view":     {"en": "View {doc}", "zh": "查看 {doc}", "vi": "Xem {doc}", "ar": "عرض {doc}", "el": "Δείτε {doc}", "it": "Vedi {doc}", "hi": "{doc} देखें"},
    "warranty": {"en": "Download the warranty", "zh": "下载保修条款", "vi": "Tải bảo hành", "ar": "تنزيل الضمان", "el": "Λήψη εγγύησης", "it": "Scarica la garanzia", "hi": "वारंटी डाउनलोड करें"},
    "care":     {"en": "See the care guide", "zh": "查看保养指南", "vi": "Xem hướng dẫn bảo dưỡng", "ar": "دليل العناية", "el": "Οδηγός φροντίδας", "it": "Guida alla cura", "hi": "देखभाल गाइड देखें"},
    "parts":    {"en": "Order spare parts", "zh": "订购备件", "vi": "Đặt phụ tùng", "ar": "اطلب قطع الغيار", "el": "Ανταλλακτικά", "it": "Ordina ricambi", "hi": "स्पेयर पार्ट्स ऑर्डर करें"},
    "service":  {"en": "Log a service request", "zh": "提交服务请求", "vi": "Gửi yêu cầu dịch vụ", "ar": "سجّل طلب خدمة", "el": "Αίτημα σέρβις", "it": "Apri una richiesta di assistenza", "hi": "सर्विस अनुरोध दर्ज करें"},
    "person":   {"en": "Talk to a person", "zh": "联系客服", "vi": "Nói chuyện với nhân viên", "ar": "تحدث مع شخص", "el": "Μιλήστε με κάποιον", "it": "Parla con una persona", "hi": "किसी व्यक्ति से बात करें"},
    "design":   {"en": "Book Design Assist", "zh": "预约设计协助", "vi": "Đặt lịch Design Assist", "ar": "احجز Design Assist", "el": "Κλείστε Design Assist", "it": "Prenota Design Assist", "hi": "Design Assist बुक करें"},
    "explore":  {"en": "Explore {brand}", "zh": "探索 {brand}", "vi": "Khám phá {brand}", "ar": "استكشف {brand}", "el": "Εξερευνήστε {brand}", "it": "Scopri {brand}", "hi": "{brand} देखें"},
    "askabout": {"en": "Ask about this", "zh": "询问此产品", "vi": "Hỏi về sản phẩm này", "ar": "اسأل عن هذا", "el": "Ρωτήστε γι' αυτό", "it": "Chiedi di questo", "hi": "इसके बारे में पूछें"},
    "viewprod": {"en": "View product", "zh": "查看产品", "vi": "Xem sản phẩm", "ar": "عرض المنتج", "el": "Δείτε το προϊόν", "it": "Vedi prodotto", "hi": "उत्पाद देखें"},
    "viewfam":  {"en": "View {fam}", "zh": "查看 {fam}", "vi": "Xem {fam}", "ar": "عرض {fam}", "el": "Δείτε {fam}", "it": "Vedi {fam}", "hi": "{fam} देखें"},
    "viewpage": {"en": "View product page", "zh": "查看产品页面", "vi": "Xem trang sản phẩm", "ar": "عرض صفحة المنتج", "el": "Σελίδα προϊόντος", "it": "Vedi la pagina prodotto", "hi": "उत्पाद पेज देखें"},
    "balreport": {"en": "Download the {bal} report", "zh": "下载 {bal} 报告", "vi": "Tải báo cáo {bal}", "ar": "تنزيل تقرير {bal}", "el": "Λήψη αναφοράς {bal}", "it": "Scarica il rapporto {bal}", "hi": "{bal} रिपोर्ट डाउनलोड करें"},
    "bulletin": {"en": "Read the technical bulletin", "zh": "阅读技术公告", "vi": "Đọc bản tin kỹ thuật", "ar": "اقرأ النشرة الفنية", "el": "Τεχνικό δελτίο", "it": "Leggi il bollettino tecnico", "hi": "तकनीकी बुलेटिन पढ़ें"},
    "manual":   {"en": "Download the design manual", "zh": "下载设计手册", "vi": "Tải sổ tay thiết kế", "ar": "تنزيل دليل التصميم", "el": "Λήψη εγχειριδίου", "it": "Scarica il manuale", "hi": "डिज़ाइन मैनुअल डाउनलोड करें"},
    "report":   {"en": "Download the report", "zh": "下载报告", "vi": "Tải báo cáo", "ar": "تنزيل التقرير", "el": "Λήψη αναφοράς", "it": "Scarica il rapporto", "hi": "रिपोर्ट डाउनलोड करें"},
    "brochure": {"en": "Download the brochure", "zh": "下载产品手册", "vi": "Tải tài liệu", "ar": "تنزيل الكتيب", "el": "Λήψη φυλλαδίου", "it": "Scarica la brochure", "hi": "ब्रोशर डाउनलोड करें"},
    "installguide": {"en": "See the installation guide", "zh": "查看安装指南", "vi": "Xem hướng dẫn lắp đặt", "ar": "دليل التركيب", "el": "Οδηγός τοποθέτησης", "it": "Guida all'installazione", "hi": "इंस्टॉलेशन गाइड देखें"},
    "energy":   {"en": "See the energy ratings", "zh": "查看能效等级", "vi": "Xem xếp hạng năng lượng", "ar": "تصنيفات الطاقة", "el": "Ενεργειακές βαθμολογίες", "it": "Vedi le classi energetiche", "hi": "ऊर्जा रेटिंग देखें"},
}
MAXLABEL = 28
LOCATE_WHAT = {
    "showroom": {"en": "showroom", "zh": "展厅", "vi": "phòng trưng bày", "ar": "صالة عرض", "el": "έκθεση", "it": "showroom", "hi": "शोरूम"},
    "display centre": {"en": "display centre", "zh": "展示中心", "vi": "trung tâm trưng bày", "ar": "مركز عرض", "el": "κέντρο επίδειξης", "it": "centro espositivo", "hi": "डिस्प्ले सेंटर"},
    "retailer": {"en": "retailer", "zh": "零售商", "vi": "nhà bán lẻ", "ar": "بائع تجزئة", "el": "κατάστημα", "it": "rivenditore", "hi": "रिटेलर"},
    "distributor": {"en": "distributor", "zh": "经销商", "vi": "nhà phân phối", "ar": "موزّع", "el": "διανομέα", "it": "distributore", "hi": "वितरक"},
    "fabricator": {"en": "fabricator", "zh": "加工商", "vi": "nhà gia công", "ar": "مصنّع", "el": "κατασκευαστή", "it": "installatore", "hi": "फैब्रिकेटर"},
    "office": {"en": "office", "zh": "办公室", "vi": "văn phòng", "ar": "مكتب", "el": "γραφείο", "it": "ufficio", "hi": "कार्यालय"},
    "brand": {"en": "brand", "zh": "品牌", "vi": "thương hiệu", "ar": "علامة", "el": "μάρκα", "it": "marchio", "hi": "ब्रांड"},
}


def t(key, lang, **kw):
    s = L[key].get(lang) or L[key]["en"]
    return s.format(**kw)


def short_title(title):
    t_ = re.sub(r"\.(pdf|PDF)$", "", title or "").strip()
    t_ = re.sub(r"\s+", " ", t_)
    return t_[:34].rstrip() + ("…" if len(t_) > 34 else "")


def _slug_words(url):
    seg = re.sub(r"[?#].*$", "", url or "").rstrip("/").split("/")[-1]
    return set(w for w in re.split(r"[-_]+", seg.lower()) if len(w) > 2)


def family_for_url(url):
    """The product family whose page a cited resource belongs to, if any."""
    u = (url or "").lower().rstrip("/")
    for f in FAMILIES:
        fu = f["url"].lower().rstrip("/")
        if u == fu or (u.startswith(fu) and len(fu) > 30):
            return f
    # Shopify product pages carry the family name in the slug (e.g. quantum-sliding-windows)
    words = _slug_words(u)
    best = None
    for f in FAMILIES:
        for k in f["keywords"]:
            kw = k.replace("-", " ").split()
            if kw and all(w in words for w in kw) and (u.split("/")[2] if "//" in u else "") in f["url"]:
                best = f
    return best


def product_cards(answer, cited, brand_scope=None, lang="en", limit=3):
    """Photographed FAMILY cards for the product families the answer actually talks about
    (or whose pages it used). One card per family, never a project photo as a family."""
    text = (answer or "").lower()
    scored = {}
    for c in cited or []:
        f = family_for_url(c.get("url"))
        if f and (not brand_scope or f["brand"] == brand_scope):
            scored[f["family"]] = scored.get(f["family"], 0) + 4
    for f in FAMILIES:
        if brand_scope and f["brand"] != brand_scope:
            continue
        hits = sum(1 for k in f["keywords"] if k in text)
        if f["family"].lower() in text:
            hits += 2
        if hits:
            scored[f["family"]] = scored.get(f["family"], 0) + hits * 2
    cited_brands = {c.get("slug") for c in cited or []}
    out = []
    for fam, sc in sorted(scored.items(), key=lambda x: -x[1]):
        f = next(x for x in FAMILIES if x["family"] == fam)
        if f["brand"] in cited_brands:
            sc += 1
        if sc < 2:
            continue
        b = kb.BRANDS.get(f["brand"], {})
        out.append({"brand": f["brand"], "brand_label": b.get("label", f["brand"]), "family": f["family"], "desc": f["desc"],
                    "photo": f["photo"], "alt": f["family"] + ", " + b.get("label", ""), "url": f["url"],
                    "view": t("viewprod", lang), "ask": t("askabout", lang)})
        if len(out) >= limit:
            break
    return out


def doc_label(c, lang):
    """A button label a designer would accept: verb + what it is, never a truncated title."""
    title = (c.get("title") or "").lower()
    dt = c.get("doctype") or ""
    if c.get("kind") == "pdf":
        m = re.search(r"bal[\s-]?(12\.5|19|29|40|fz)", title)
        if m and ("report" in title or dt == "compliance"):
            return t("balreport", lang, bal="BAL-" + m.group(1).upper())
        if dt == "warranty" or "warranty" in title:
            return t("warranty", lang)
        if "bulletin" in title or title.startswith("technical bulletin") or title.startswith("tb "):
            return t("bulletin", lang)
        if "design manual" in title or "manual" in title:
            return t("manual", lang)
        if dt == "brochure" or "brochure" in title or "ideas book" in title:
            return t("brochure", lang)
        if dt == "installation" or "building-in" in title or "install" in title:
            return t("installguide", lang)
        if dt == "energy" or "wers" in title or "energy" in title:
            return t("energy", lang)
        return t("report", lang)
    if dt == "warranty":
        return t("warranty", lang)
    if dt == "care":
        return t("care", lang)
    if dt == "installation":
        return t("installguide", lang)
    if dt == "energy":
        return t("energy", lang)
    if dt == "product":
        f = family_for_url(c.get("url"))
        if f:
            lab = t("viewfam", lang, fam=f["family"])
            if len(lab) <= MAXLABEL:
                return lab
        return t("viewpage", lang)
    return ""


def actions(answer, cited, mode="general", brand_scope=None, lang="en", limit=4):
    """Real buttons, most specific first: the documents and pages the answer rests on,
    then the brand's own quote and locator pages, then a person."""
    out, seen = [], set()

    def push(label, url, kind, brand=None):
        if not url or url in seen or len(out) >= limit or any(o["label"] == label for o in out):
            return
        seen.add(url)
        out.append({"label": label, "url": url, "kind": kind, "brand": brand})

    cited = cited or []
    brands_in_order = []
    for c in cited:
        s = c.get("slug")
        if s and s != "ventora" and s not in brands_in_order:
            brands_in_order.append(s)
    if brand_scope and brand_scope not in brands_in_order:
        brands_in_order.insert(0, brand_scope)
    text = (answer or "").lower()
    is_service = mode == "service" or bool(re.search(r"\bclaim\b|repair|sticking|broken|leak|spare part|fault|not (closing|opening)|damaged|cracked", text))
    is_care = re.search(r"clean|maintain|maintenance|lubric|care ", text)

    # 1. documents and pages actually used (PDFs first), one per kind of thing
    for c in sorted(cited, key=lambda c: 0 if c.get("kind") == "pdf" else 1):
        lab = doc_label(c, lang)
        if not lab or len(lab) > MAXLABEL + 6:
            continue
        if c.get("kind") != "pdf" and c.get("doctype") == "product" and brands_in_order and c.get("slug") != brands_in_order[0]:
            continue
        push(lab, c["url"], "download" if c.get("kind") == "pdf" else "link", c.get("slug"))
        if len(out) >= 2:
            break

    # 2. the flow: quote / service / locator for the leading brand
    lead = brands_in_order[0] if brands_in_order else "ventora"
    links = BRAND_LINKS.get(lead, BRAND_LINKS["ventora"])
    if is_service:
        push(t("service", lang), "#service", "flow", lead)
        if not is_care:
            push(t("care", lang), links["care"], "link", lead)
        push(t("parts", lang), links["parts"], "link", lead)
    elif mode == "specify":
        push(t("design", lang), "#design-assist", "flow", lead)
        push(t("quote", lang), "#quote", "flow", lead)
    else:
        push(t("quote", lang), "#quote", "flow", lead)
        what = LOCATE_WHAT.get(links["locate_label"], LOCATE_WHAT["showroom"]).get(lang, links["locate_label"])
        push(t("locate", lang, what=what), links["locate"], "link", lead)
    # 3. always a person
    push(t("person", lang), links["contact"], "link", lead)
    return out[:limit]


FOLLOWUPS = {
    "en": {"warranty": "What does the warranty cover?", "install": "How is it installed?", "energy": "How does it perform for energy efficiency?",
           "bal": "Is it suitable for a bushfire (BAL) zone?", "care": "How do I look after it?", "quote": "Can you prepare a quote for this?",
           "compare": "How does it compare with the other Ventora brands?", "colours": "What colours and finishes are available?"},
    "zh": {"warranty": "保修范围是什么？", "install": "如何安装？", "energy": "节能表现如何？", "bal": "适合林火（BAL）区域吗？", "care": "如何保养？", "quote": "可以为我准备报价吗？", "compare": "与 Ventora 其他品牌相比如何？", "colours": "有哪些颜色和饰面？"},
    "vi": {"warranty": "Bảo hành bao gồm những gì?", "install": "Lắp đặt như thế nào?", "energy": "Hiệu quả năng lượng ra sao?", "bal": "Có phù hợp vùng cháy rừng (BAL) không?", "care": "Bảo dưỡng như thế nào?", "quote": "Bạn có thể chuẩn bị báo giá không?", "compare": "So với các thương hiệu Ventora khác thế nào?", "colours": "Có những màu và hoàn thiện nào?"},
    "ar": {"warranty": "ماذا يغطي الضمان؟", "install": "كيف يتم التركيب؟", "energy": "ما أداؤه في كفاءة الطاقة؟", "bal": "هل يناسب مناطق حرائق الغابات (BAL)؟", "care": "كيف أعتني به؟", "quote": "هل يمكنك تجهيز عرض سعر؟", "compare": "كيف يقارن بعلامات Ventora الأخرى؟", "colours": "ما الألوان والتشطيبات المتاحة؟"},
    "el": {"warranty": "Τι καλύπτει η εγγύηση;", "install": "Πώς τοποθετείται;", "energy": "Πώς αποδίδει ενεργειακά;", "bal": "Είναι κατάλληλο για ζώνη πυρκαγιάς (BAL);", "care": "Πώς το συντηρώ;", "quote": "Μπορείτε να ετοιμάσετε προσφορά;", "compare": "Πώς συγκρίνεται με τις άλλες μάρκες Ventora;", "colours": "Ποια χρώματα και φινιρίσματα υπάρχουν;"},
    "it": {"warranty": "Cosa copre la garanzia?", "install": "Come si installa?", "energy": "Come si comporta in efficienza energetica?", "bal": "È adatto a una zona a rischio incendi (BAL)?", "care": "Come lo mantengo?", "quote": "Puoi preparare un preventivo?", "compare": "Come si confronta con gli altri marchi Ventora?", "colours": "Quali colori e finiture sono disponibili?"},
    "hi": {"warranty": "वारंटी में क्या शामिल है?", "install": "इसे कैसे लगाया जाता है?", "energy": "ऊर्जा दक्षता में यह कैसा है?", "bal": "क्या यह बुशफायर (BAL) क्षेत्र के लिए उपयुक्त है?", "care": "इसकी देखभाल कैसे करूँ?", "quote": "क्या आप इसका कोटेशन बना सकते हैं?", "compare": "अन्य Ventora ब्रांडों की तुलना में यह कैसा है?", "colours": "कौन से रंग और फिनिश उपलब्ध हैं?"},
}


def followups(answer, cited, mode="general", lang="en"):
    text = (answer or "").lower()
    keys = []
    doctypes = {c.get("doctype") for c in cited or []}
    if "warranty" not in doctypes and "warrant" not in text:
        keys.append("warranty")
    if "installation" not in doctypes:
        keys.append("install")
    if mode == "specify":
        keys = ["bal", "energy", "compare"]
    elif "bal" in text or "bushfire" in text:
        keys.append("energy")
    else:
        keys.append("colours")
    keys.append("quote")
    seen, out = set(), []
    for k in keys:
        if k in seen:
            continue
        seen.add(k)
        out.append(FOLLOWUPS.get(lang, FOLLOWUPS["en"])[k])
    return out[:3]


def intake_prompt(lead):
    """Tell the concierge what the enquiry already holds so it never re-asks."""
    fields = [("state", "state"), ("product_type", "product"), ("openings", "openings"), ("glazing", "glazing"),
              ("bal_level", "bushfire level"), ("timing", "timing"), ("contact_preference", "contact preference")]
    known, missing = [], []
    for k, label in fields:
        v = (lead or {}).get(k)
        blank = ("unknown", "", "n/a") if k == "bal_level" else ("unknown", "", "n/a", "none")
        if v and str(v).strip().lower() not in blank:
            known.append(f"{label} {v}")
        else:
            missing.append(label)
    return (" You are also collecting a quote enquiry. Known so far: " + ("; ".join(known) if known else "nothing yet") +
            ". Still needed: " + (", ".join(missing) if missing else "nothing") +
            ". After answering any product question, ask only for what is still needed, one or two questions at a time, and never ask again for anything already known. "
            "When nothing is still needed, start your reply with 'I have what I need' and give a two-sentence summary.")


def system_prompt(mode, lang, brand_label=None):
    base = ("You are the Ventora concierge, speaking for Ventora's eight building-product brands. Answer only from the supplied material. "
            "Write warmly and plainly, in short paragraphs, at most 120 words before you stop. Do not list sources, document names or citations in the text; "
            "the page shows them. Never quote prices or lead times. Never say 'the context' or 'the documents provided'; speak as Ventora. "
            "If the material does not cover the question, say so in one sentence and suggest speaking to the right team. Use Australian English spelling (customised, colour, organise). Never use exclamation marks.")
    if mode == "specify":
        base = ("You are answering an architect, estimator or certifier on behalf of Ventora. Be precise and comparative across brands where the material allows. "
                "State what the test reports, ratings and manuals show; never assert a compliance outcome - say final compliance is confirmed by the certifier or energy assessor. "
                "Short paragraphs, plain Australian English, no citations in the text. Never say 'the context'. Never use exclamation marks.")
    if brand_label:
        base += f" You are answering only for {brand_label}; if the question is about another brand, say it is outside {brand_label}'s range."
    if lang != "en":
        base += f" Reply in {LANGS[lang]['name']}. Keep product names, brand names and document titles as published."
    return base
