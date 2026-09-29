"""Second pass over static/photos: drop weak harvests, add hand-picked product photography.
  ../../.venv/bin/python scripts/curate_photos.py
"""
import json, re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from harvest_assets import add, get, save_image, PHOTOS, sitemap_images  # noqa
import harvest_assets as H

idx = json.load(open(PHOTOS / "photos.json"))
DROP_FILES = {"/static/photos/al-windows/aluminium-sliding-doors.jpg", "/static/photos/al-windows/aluminium-awning-windows.jpg",
              "/static/photos/al-windows/boutique-bi-fold-doors.jpg", "/static/photos/al-windows/aluminium-double-hung-windows.jpg",
              "/static/photos/al-windows/aluminium-louvre-windows.jpg", "/static/photos/al-windows/entry-frames.jpg",
              "/static/photos/al-windows/aluminium-windows.jpg", "/static/photos/al-windows/aluminium-doors.jpg",
              "/static/photos/corinthian/entrance-doors.jpg", "/static/photos/corinthian/internal-doors.jpg",
              "/static/photos/corinthian/sidelights.jpg", "/static/photos/corinthian/veneer-doors.jpg",
              "/static/photos/breezway/powerlouvre-automated-louvres.jpg", "/static/photos/ventora-glass/simplee.jpg",
              "/static/photos/aneeta/aneeta-sashless-windows.jpg"}
keep = [it for it in idx if it["file"] not in DROP_FILES]
for f in DROP_FILES:
    p = Path("." + f) if f.startswith("/") else Path(f)
    p = PHOTOS.parent.parent / f.lstrip("/")
    if p.exists(): p.unlink()
H.index = keep

AL = "https://cdn.alwindows.com.au/wp-content/uploads/"
AL_PAGE = "https://www.alwindows.com.au/products/"
for fam, rel, page in [
    ("Aluminium sliding doors", "2017/12/3-Panel-Sliding-Door.jpg", AL_PAGE + "aluminium-doors/aluminium-sliding-doors/"),
    ("Boutique aluminium range", "2017/11/boutique-1.jpg", AL_PAGE + "aluminium-doors/boutique-aluminium-bifold-doors/"),
    ("A&L showroom", "2017/11/CB385_AL_Showroom_112.jpg", AL_PAGE + "aluminium-windows/"),
    ("Aluminium doors", "2017/11/August_AL_Doors_8931_Sky-1-1.png", AL_PAGE + "aluminium-doors/"),
    ("Windows and doors", "2017/12/AL-Windows-and-Doors-Hi-res-6.jpg", AL_PAGE + "aluminium-windows/"),
    ("Bi-parting sliding doors", "2017/12/Bi-Parting-Sliding-Doors-2.png", AL_PAGE + "aluminium-doors/aluminium-sliding-doors/"),
]:
    ok = False
    for cand in (AL + rel, AL + re.sub(r"\.(jpg|png)$", r"-768x432.\1", rel), AL + re.sub(r"\.(jpg|png)$", r"-480x270.\1", rel)):
        before = len(H.index); add("al-windows", fam, page, cand, "A&L " + fam, referer=page)
        if len(H.index) > before: ok = True; break
    if not ok: print("  A&L failed", fam)

CO = "https://cdn.corinthian.com.au/wp-content/uploads/"
for fam, rel in [("Coastal Blonde Oak entrance door", "2024/07/15065125/Coastal-Blonde-Oak-AWO-5.jpg"),
                 ("Contemporary Manhattan door", "2024/07/15065657/Contemporary-Manhattan-BHAT-13.jpg"),
                 ("Farmhouse Blonde Oak entrance", "2024/07/15065726/Farmhouse-Blonde-Oak-AWO-40-Exterior.jpg"),
                 ("Palm Springs Urban entrance", "2024/07/15065917/Palm-Springs-Urban-PURB-1-Exterior.jpg"),
                 ("Roma internal doors", "2025/04/22160512/Roma_Gallery_1440x960_hero_1.jpg"),
                 ("Entrance door H17", "2025/05/08100909/H17_FRONT.jpg")]:
    page = "https://www.corinthian.com.au/doors/category/entrance/"
    ok = False
    for cand in (CO + rel, CO + re.sub(r"\.(jpg)$", r"-1024x768.\1", rel), CO + re.sub(r"\.(jpg)$", r"-600x450.\1", rel)):
        before = len(H.index); add("corinthian", fam, page, cand, "Corinthian " + fam, referer=page)
        if len(H.index) > before: ok = True; break
    if not ok: print("  Corinthian failed", fam)

bw = sitemap_images("https://www.breezway.com.au/project-sitemap.xml")
want = ["chrismont-winery", "canada-bay", "contemporary-beach-box", "young-family-home", "queenslander", "beyond-house", "coogee-house", "sunshine-coast", "elegant-l-shaped"]
for page, img, title in bw:
    if any(w in page for w in want):
        fam = re.sub(r"-", " ", page.rstrip("/").split("/")[-1])
        fam = fam[0].upper() + fam[1:]
        add("breezway", "Altair louvres - " + fam[:44], page, img, "Breezway Altair louvre windows, " + fam, referer=page)

an = sitemap_images("https://aneetawindows.com.au/picture-sitemap.xml")
n = 0
for page, img, title in an:
    if n >= 6: break
    if "glazed" in page:
        kind = ("Vertical" if "vertical" in page else "Horizontal") + (" double glazed" if "double" in page else " single glazed")
        add("aneeta", f"{kind} sashless window {n+1}", page, img, "Aneeta sashless window, " + kind.lower(), referer=page); n += 1

json.dump(H.index, open(PHOTOS / "photos.json", "w"), indent=1)
print("index", len(H.index))
