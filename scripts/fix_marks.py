"""Make the brand marks usable in a real layout: drop the light-grey background, crop to
content with a small margin, and produce a white wordmark for dark surfaces."""
from PIL import Image
from pathlib import Path
B = Path(__file__).resolve().parent.parent / "static" / "brand"

def transparent(im, key=(236, 236, 236), tol=8):
    im = im.convert("RGBA"); px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            if abs(r - key[0]) <= tol and abs(g - key[1]) <= tol and abs(b - key[2]) <= tol:
                px[x, y] = (r, g, b, 0)
    return im

def crop(im, margin=0.06):
    bbox = im.getchannel("A").getbbox()
    if not bbox: return im
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    mx, my = int(w * margin), int(h * margin)
    return im.crop((max(0, bbox[0] - mx), max(0, bbox[1] - my), min(im.width, bbox[2] + mx), min(im.height, bbox[3] + my)))

for n in ["stegbar", "breezway", "corinthian", "trend", "aneeta", "al-windows", "ventora-glass", "regency"]:
    p = B / f"{n}.png"; im = Image.open(p)
    im = crop(transparent(im)) if n != "regency" else crop(transparent(im))
    im.save(p); print(n, im.size)
# Ventora wordmark: keep the green block as the primary logo; make a white-on-transparent version too
v = Image.open(B / "ventora.png").convert("RGBA"); px = v.load()
w = v.copy(); wp = w.load()
for y in range(w.height):
    for x in range(w.width):
        r, g, b, a = wp[x, y]
        if g > r + 20 and g > b + 10:   # the green field
            wp[x, y] = (255, 255, 255, 0)
        else:
            wp[x, y] = (255, 255, 255, a)
w = crop(w, 0.02); w.save(B / "ventora-white.png"); print("ventora-white", w.size)
# and a green-on-transparent wordmark (text only) for light surfaces
g = v.copy(); gp = g.load()
for y in range(g.height):
    for x in range(g.width):
        r, gg, b, a = gp[x, y]
        gp[x, y] = (32, 92, 64, a) if (r > 200 and gg > 200 and b > 200) else (32, 92, 64, 0)
g = crop(g, 0.02); g.save(B / "ventora-green.png"); print("ventora-green", g.size)
