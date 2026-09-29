"""Download Ventora's own brand assets and product photography for the experience.

  ../../.venv/bin/python scripts/harvest_assets.py

Ventora owns all of this imagery; the demo is for Ventora. Everything is resized to
1600px max width and written under static/brand and static/photos/<brand>/ with an
index at static/photos/photos.json. Originals are not kept.
"""
import io, json, re, subprocess, sys
from pathlib import Path
from PIL import Image, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True

ROOT = Path(__file__).resolve().parent.parent
BRAND = ROOT / "static" / "brand"; PHOTOS = ROOT / "static" / "photos"
UA = "Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/128 Safari/537.36"
SQ = "https://images.squarespace-cdn.com/content/v1/69044a2061fb54578c6db844/"
SCRATCH = Path("/private/tmp/claude-502/-Users-jsanders-Claude/45d0fd63-3bff-4964-9e34-19621f86714a/scratchpad/photos/shopify-images.json")

def get(url, referer=None):
    cmd = ["curl", "-s", "-L", "--max-time", "60", "-A", UA] + (["-e", referer] if referer else []) + [url]
    return subprocess.run(cmd, capture_output=True).stdout

def save_image(data, path, max_w=1600, quality=82):
    try:
        im = Image.open(io.BytesIO(data))
    except Exception:
        return None
    try:
        im.load()
    except OSError:
        return None
    if path.suffix.lower() == ".png":
        if im.width > max_w:
            im = im.resize((max_w, int(im.height * max_w / im.width)), Image.LANCZOS)
        im.save(path, optimize=True)
    else:
        if im.mode not in ("RGB",):
            im = im.convert("RGB")
        if im.width > max_w:
            im = im.resize((max_w, int(im.height * max_w / im.width)), Image.LANCZOS)
        im.save(path, "JPEG", quality=quality, optimize=True, progressive=True)
    return path

# 1. logo + marks + hero photos
MARKS = {
    "ventora": "b0d73711-5cf2-4377-9ccc-cec83c791779/ventora_primary-green+RGB.png?format=1500w",
    "stegbar": "38df75d9-fc88-4b81-b9aa-a99a4be2be37/Stegbar_Logo_Resized.png?format=500w",
    "al-windows": "0841a51b-7fe8-42f0-9a79-ea45320900df/A%26L_Logo_Resized.png?format=500w",
    "corinthian": "9d310529-9708-4138-9d05-3608d1ea0a73/Corinthian_Logo_Resized.png?format=500w",
    "trend": "5a928149-9608-44ef-b10b-e43495d494a9/Trend_Logo_Resized.png?format=500w",
    "aneeta": "71b8a365-af50-4864-8b1a-79348d9a59d2/Aneeta_Logo_Resized.png?format=500w",
    "breezway": "2866761b-2844-47c3-9dd1-fb75bccc578f/Breezway_Logo_Resized.png?format=500w",
    "regency": "c197f3c5-38c4-4f4e-b84a-c6b7b7e327a8/Regency_Small.png?format=300w",
    "ventora-glass": "6ba58ff8-fd19-4f93-b7a9-00839c0b4689/VENTORA+Glass_Logo_Resized.png?format=500w",
}
HEROES = {
    "hero-stegbar.jpg": "da7a8190-b2ab-4e17-b45d-40fcd8adec7c/Stegbar_Header.jpg?format=2500w",
    "hero-al.jpg": "cabeed4d-6b6b-4f9a-b3a2-5975365a80f7/A%26L_Innovation.jpg?format=2500w",
    "hero-culture.jpg": "eab1cf70-e8d1-46f5-b1a1-74933b9c325d/Our+Culture.jpg?format=2500w",
}
if __name__ == "__main__" and "--extra" not in sys.argv and "--marks" in sys.argv:
  pass
for slug, rel in ([] if __name__ != "__main__" else MARKS.items()):
    p = save_image(get(SQ + rel), BRAND / f"{slug}.png", max_w=1500 if slug == "ventora" else 600)
    print("mark", slug, "ok" if p else "FAILED")
for name, rel in ([] if __name__ != "__main__" else HEROES.items()):
    p = save_image(get(SQ + rel), PHOTOS / name, max_w=2400, quality=80)
    print("hero", name, "ok" if p else "FAILED")

# 2. product photography
index = []
def add(brand, family, page, img_url, alt, referer=None):
    d = PHOTOS / brand; d.mkdir(parents=True, exist_ok=True)
    fname = re.sub(r"[^a-z0-9]+", "-", family.lower()).strip("-")[:60] + ".jpg"
    data = get(img_url, referer or page)
    if not data or len(data) < 8000:
        print("  skip small", brand, family); return
    p = save_image(data, d / fname)
    if not p:
        print("  skip bad", brand, family); return
    index.append({"brand": brand, "family": family, "page_url": page, "file": f"/static/photos/{brand}/{fname}", "alt": alt})
    print("  photo", brand, family)

shop = json.load(open(SCRATCH)) if __name__ == "__main__" else {}
PICK = {
    "stegbar": ["alumiere-sliding-and-stacking-doors", "alumiere-awning-windows", "frameless-shower-screens", "galleria-wardrobe-collection",
                "residential-bi-fold-doors", "timberaul-double-hung-windows", "alumiere-breezway-louvre-windows", "siteline-sliding-doors", "aqua-inline-shower-screen", "colour-collection"],
    "trend": ["quantum-sliding-and-stacking-doors", "botanica-bi-fold-doors", "synergy-double-hung-windows", "thermaarc-windows-and-doors",
              "crestlite-awning-windows", "quantum-breezway-louvre-windows", "botanica-awning-windows", "quantum-hinged-doors"],
    "regency": ["frameless-shower-screens", "galleria-wardrobe-collection", "aqua-series-inline", "framed-sliding-wardrobe-doors", "shaped-mirrors", "colour-collection", "hiro-sliding-doors"],
    "ventoraglass": ["energy-efficient-double-glazed-glass-solutions", "toughened-glass-safe-stylish-amp-compliant", "laminated-glass-safe-quiet-uv-options",
                     "mirror-glass", "painted-glass-sleek-modern-easy-to-maintain", "simplee"],
}
SLUGMAP = {"ventoraglass": "ventora-glass"}
for b, wants in PICK.items():
    items = {it["page"].rstrip("/").split("/")[-1]: it for it in shop.get(b, [])}
    for w in wants:
        it = items.get(w)
        if it:
            add(SLUGMAP.get(b, b), it["title"] or w, it["page"], it["img"], it["title"] or w)

def og_or_big(page):
    html = get(page).decode("utf-8", "ignore")
    m = re.search(r'<meta property="og:image" content="([^"]+)"', html)
    if m and re.search(r"\.(jpe?g|png|webp)", m.group(1), re.I):
        return m.group(1)
    cands = re.findall(r'<img[^>]+(?:data-src|src)="([^"]+\.(?:jpe?g|webp|png))[^"]*"[^>]*>', html, re.I)
    for c in cands:
        if re.search(r"logo|icon|badge|award|svg", c, re.I):
            continue
        if c.startswith("//"): c = "https:" + c
        elif c.startswith("/"): c = re.match(r"https?://[^/]+", page).group(0) + c
        return c
    return None

WP = {
    "breezway": [("Altair louvre windows", "https://www.breezway.com.au/products/altair-louvre-window/"),
                 ("Powerlouvre automated louvres", "https://www.breezway.com.au/products/powerlouvre-system/"),
                 ("Stronghold fall prevention", "https://www.breezway.com.au/products/stronghold-system/"),
                 ("IGLU double-glazed louvres", "https://www.breezway.com.au/products/iglu-system/"),
                 ("Customising options", "https://www.breezway.com.au/products/customising-options/"),
                 ("Breezway", "https://www.breezway.com.au/")],
    "al-windows": [("Aluminium sliding doors", "https://www.alwindows.com.au/products/aluminium-doors/aluminium-sliding-doors/"),
                   ("Aluminium awning windows", "https://www.alwindows.com.au/products/aluminium-windows/aluminium-awning-windows/"),
                   ("Boutique bi-fold doors", "https://www.alwindows.com.au/products/aluminium-doors/boutique-aluminium-bifold-doors/"),
                   ("Aluminium double hung windows", "https://www.alwindows.com.au/products/aluminium-windows/aluminium-double-hung-windows/"),
                   ("Aluminium louvre windows", "https://www.alwindows.com.au/products/aluminium-windows/aluminium-louvre-windows/"),
                   ("Entry frames", "https://www.alwindows.com.au/products/entry-frames/"),
                   ("Aluminium windows", "https://www.alwindows.com.au/products/aluminium-windows/"),
                   ("Aluminium doors", "https://www.alwindows.com.au/products/aluminium-doors/")],
    "corinthian": [("Entrance doors", "https://www.corinthian.com.au/doors/category/entrance/"),
                   ("Internal doors", "https://www.corinthian.com.au/doors/category/internal/"),
                   ("Sidelights", "https://www.corinthian.com.au/doors/category/sidelight/"),
                   ("Veneer doors", "https://www.corinthian.com.au/doors/category/veneer/"),
                   ("Corinthian Doors", "https://www.corinthian.com.au/"),
                   ("Blonde Oak entrance door", "https://www.corinthian.com.au/doors/entrance/awo-21/")],
    "aneeta": [("Horizontal single glazed sashless", "https://aneetawindows.com.au/category/horizontal-single-glazed/"),
               ("Vertical double glazed sashless", "https://aneetawindows.com.au/category/vertical-double-glazed/"),
               ("Vertical single glazed sashless", "https://aneetawindows.com.au/category/vertical-single-glazed/"),
               ("Aneeta sashless windows", "https://aneetawindows.com.au/"),
               ("Gallery", "https://aneetawindows.com.au/gallery/")],
}
for b, pages in ([] if __name__ != "__main__" else WP.items()):
    for fam, page in pages:
        u = og_or_big(page)
        if u:
            add(b, fam, page, u, fam, referer=page)
        else:
            print("  no image for", b, fam)

if __name__ == "__main__" and "--extra" not in sys.argv:
    json.dump(index, open(PHOTOS / "photos.json", "w"), indent=1)
    print("index", len(index))

# 3. extra: Breezway project photography and Aneeta picture gallery (sitemap images)
def sitemap_images(url):
    x = get(url).decode("utf-8", "ignore")
    out = []
    for block in re.findall(r"<url>(.*?)</url>", x, re.S):
        loc = re.search(r"<loc>([^<]+)", block); img = re.search(r"<image:loc>([^<]+)", block); t = re.search(r"<image:title>([^<]+)", block)
        if loc and img:
            out.append((loc.group(1), img.group(1).replace("&amp;", "&"), (t.group(1) if t else "").replace("&amp;", "&")))
    return out

if __name__ == "__main__" and "--extra" in sys.argv:
    index = json.load(open(PHOTOS / "photos.json"))
    bw = sitemap_images("https://www.breezway.com.au/project-sitemap.xml")
    want = ["chrismont-winery", "canada-bay", "contemporary-beach-box", "young-family-home", "queenslander", "beyond-house", "coogee-house", "sunshine-coast"]
    for page, img, title in bw:
        if any(w in page for w in want):
            fam = re.sub(r"-", " ", page.rstrip("/").split("/")[-1]).capitalize()
            add("breezway", "Altair louvres - " + fam[:50], page, img, "Breezway Altair louvre windows, " + fam, referer=page)
    an = sitemap_images("https://aneetawindows.com.au/picture-sitemap.xml")
    n = 0
    for page, img, title in an:
        if n >= 6: break
        if "double-glazed" in page or "single-glazed" in page:
            fam = "Sashless " + ("double glazed" if "double" in page else "single glazed") + (" vertical" if "vertical" in page else " horizontal") + f" {n+1}"
            add("aneeta", fam, page, img, "Aneeta sashless window", referer=page); n += 1
    json.dump(index, open(PHOTOS / "photos.json", "w"), indent=1)
    print("index", len(index))
