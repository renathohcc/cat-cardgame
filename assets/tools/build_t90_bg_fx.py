"""T9.0: cenario do cercado (pen_bg.png), pen.json e efeitos 16x16 (fx.png/json). Pillow, sem IA.
Uso: python assets/tools/build_t90_bg_fx.py
"""
import json
import os
import random
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PEN = os.path.join(ROOT, "assets", "pen")
os.makedirs(PEN, exist_ok=True)


def h(c, a=255):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) + (a,)


OUT = h("#3b2a38")
WALK = (48, 96, 664, 372)
PANEL = (736, 16, 208, 508)
SLEEP = [(120, 170), (330, 150), (610, 175), (110, 410), (400, 430), (620, 400)]
PLAY = [(260, 290), (470, 300), (350, 250)]


def ellipse(d, cx, cy, rx, ry, fill, outline=None):
    d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=fill, outline=outline)


def cushion(d, x, y):
    ellipse(d, x, y + 3, 22, 14, h("#1a2036"))
    ellipse(d, x, y, 21, 13, OUT)
    ellipse(d, x, y - 1, 19, 11, h("#8a3a52"))
    ellipse(d, x - 2, y - 3, 14, 7, h("#a84a66"))
    ellipse(d, x - 4, y - 4, 7, 3, h("#c26a82"))
    d.point((x, y - 1), fill=h("#5c2338"))


def stone_bed(d, x, y):
    ellipse(d, x, y + 4, 23, 12, h("#1a2036"))
    ellipse(d, x, y, 22, 12, OUT)
    ellipse(d, x, y - 1, 20, 10, h("#5d6c96"))
    ellipse(d, x - 2, y - 3, 15, 6, h("#7384ae"))
    ellipse(d, x - 5, y - 4, 7, 2, h("#93a3c8"))


def basket(d, x, y):
    ellipse(d, x, y + 4, 23, 12, h("#1a2036"))
    ellipse(d, x, y, 22, 13, OUT)
    ellipse(d, x, y, 20, 11, h("#6b4a31"))
    ellipse(d, x, y - 1, 16, 8, h("#c9a98a"))
    ellipse(d, x - 2, y - 2, 11, 5, h("#e0c4a6"))
    for i in range(-18, 19, 5):
        d.line((x + i, y + 9, x + i + 2, y + 6), fill=h("#4a3022"))


def yarn(d, x, y):
    ellipse(d, x + 1, y + 8, 9, 3, h("#1a2036"))
    ellipse(d, x, y, 8, 8, OUT)
    ellipse(d, x, y, 7, 7, h("#e0507a"))
    ellipse(d, x - 2, y - 2, 4, 4, h("#f58aa8"))
    d.arc((x - 6, y - 6, x + 6, y + 6), 20, 200, fill=h("#b0305a"))
    d.arc((x - 6, y - 2, x + 6, y + 8), 200, 340, fill=h("#b0305a"))
    d.line((x + 6, y + 5, x + 14, y + 8), fill=h("#e0507a"))
    d.line((x + 14, y + 8, x + 20, y + 6), fill=h("#e0507a"))


def toy_mouse(d, x, y):
    ellipse(d, x + 1, y + 5, 9, 3, h("#1a2036"))
    ellipse(d, x, y, 8, 5, OUT)
    ellipse(d, x, y, 7, 4, h("#9aa0b4"))
    ellipse(d, x - 2, y - 1, 4, 2, h("#c4c9d8"))
    ellipse(d, x - 5, y - 4, 3, 3, OUT)
    ellipse(d, x - 5, y - 4, 2, 2, h("#f09aa8"))
    d.point((x + 5, y), fill=h("#2a1c2a"))
    d.line((x + 8, y + 1, x + 15, y + 3), fill=h("#f09aa8"))


def feather(d, x, y):
    ellipse(d, x, y + 6, 8, 3, h("#1a2036"))
    d.line((x - 14, y + 4, x + 2, y - 8), fill=h("#8a6a2c"), width=1)
    pts = [(x + 2, y - 8), (x + 12, y - 12), (x + 14, y - 4), (x + 8, y + 2)]
    d.polygon(pts, fill=h("#9fd8c4"), outline=OUT)
    d.line((x + 3, y - 7, x + 12, y - 5), fill=h("#d9f3e8"))


def tuft(d, x, y, c1, c2):
    d.line((x, y, x - 2, y - 4), fill=c1)
    d.line((x + 1, y, x + 1, y - 5), fill=c2)
    d.line((x + 2, y, x + 4, y - 3), fill=c1)


def fence(d, x0, y, x1):
    for px in range(x0 + 6, x1, 22):
        d.rectangle((px, y - 14, px + 8, y + 24), fill=OUT)
        d.rectangle((px + 1, y - 12, px + 7, y + 23), fill=h("#4a5a82"))
        d.rectangle((px + 1, y - 12, px + 3, y + 23), fill=h("#5d6c96"))
        d.polygon([(px, y - 14), (px + 8, y - 14), (px + 4, y - 19)], fill=OUT)
        d.polygon([(px + 1, y - 14), (px + 7, y - 14), (px + 4, y - 17)], fill=h("#5d6c96"))
    for ry in (y - 4, y + 12):
        d.rectangle((x0, ry, x1, ry + 4), fill=OUT)
        d.rectangle((x0, ry + 1, x1, ry + 3), fill=h("#3d4a6e"))
        d.line((x0, ry + 1, x1, ry + 1), fill=h("#5d6c96"))


def build_bg():
    rnd = random.Random(90)
    W, H = 960, 540
    im = Image.new("RGBA", (W, H), h("#16242c"))
    d = ImageDraw.Draw(im)
    grass = [h("#16242c"), h("#1a2c33"), h("#142029")]
    for _ in range(3200):
        tuft(d, rnd.randrange(W), rnd.randrange(H), rnd.choice(grass), h("#1f3640"))
    halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    hd = ImageDraw.Draw(halo)
    for r, a in ((260, 9), (200, 10), (140, 12), (90, 14)):
        ellipse(hd, 420, 20, r * 2, r, (159, 216, 196, a))
    im.alpha_composite(halo)
    d = ImageDraw.Draw(im)
    # lua em crescente
    ellipse(d, 660, 34, 11, 11, h("#e8efe0"))
    ellipse(d, 664, 31, 10, 10, h("#16242c"))
    x, y, w, hh = WALK
    d.rectangle((x - 6, y - 6, x + w + 5, y + hh + 5), fill=h("#0f1424"))
    d.rectangle((x - 4, y - 4, x + w + 3, y + hh + 3), fill=h("#3d4a6e"))
    d.rectangle((x - 2, y - 2, x + w + 1, y + hh + 1), fill=h("#2a3350"))
    d.rectangle((x, y, x + w - 1, y + hh - 1), fill=h("#2c3553"))
    for _ in range(900):
        px, py = x + rnd.randrange(w - 3), y + rnd.randrange(hh - 2)
        d.rectangle((px, py, px + rnd.randrange(1, 4), py), fill=rnd.choice([h("#2f3857"), h("#29314e")]))
    for gx in range(x, x + w, 83):
        d.line((gx, y, gx, y + hh - 1), fill=h("#2a3250"))
    for gy in range(y, y + hh, 62):
        d.line((x, gy, x + w - 1, gy), fill=h("#2a3250"))
    cyc = [cushion, stone_bed, basket]
    for i, (sx, sy) in enumerate(SLEEP):
        cyc[i % 3](d, sx, sy)
    for fn, (px, py) in zip([yarn, toy_mouse, feather], PLAY):
        fn(d, px, py)
    fence(d, 0, 58, 736)
    for i in range(0, 736, 14):
        hh2 = 6 + (i * 7) % 5
        ellipse(d, i + 7, 490 + hh2 // 2, 10, hh2, h("#10211f"))
        ellipse(d, i + 5, 488 + hh2 // 2, 7, hh2 - 2, h("#173028"))
    for _ in range(40):
        px = rnd.randrange(0, 736)
        py = rnd.choice([rnd.randrange(505, 536), rnd.randrange(78, 92)])
        d.point((px, py), fill=rnd.choice([h("#d9b65c"), h("#9fd8c4"), h("#c9b6e8")]))
    d.rectangle((736, 0, W, H), fill=h("#101526"))
    d.rectangle((728, 0, 735, H), fill=h("#0b0f1c"))
    d.line((735, 0, 735, H), fill=h("#252d47"))
    for _ in range(120):
        d.point((rnd.randrange(742, 958), rnd.randrange(4, 536)), fill=h("#141b30"))
    im.save(os.path.join(PEN, "pen_bg.png"))


HEART = """
..ooo...ooo..
.orRRo.orrro.
orRRrrorrrrdo
orRrrrrrrrrdo
orrrrrrrrrddo
.orrrrrrrrdo.
..orrrrrrdo..
...orrrrdo...
....orrdo....
.....odo.....
......o......
""".split()

MASKS = {
    "z": ("""
#########
#########
.....###.
....###..
...###...
..###....
.###.....
#########
#########
""".split(), (232, 244, 255), (150, 180, 230)),
    "note": ("""
....#####
....#####
....##.##
....##..#
....##...
....##...
....##...
.#####...
#######..
#######..
.#####...
""".split(), (200, 255, 230), (110, 200, 170)),
    "sparkle": ("""
....#....
....#....
...###...
...###...
#########
...###...
...###...
....#....
....#....
""".split(), (255, 240, 150), (240, 190, 70)),
    "star": ("""
.....#.....
.....#.....
....###....
###########
.#########.
..#######..
..#######..
.####.####.
.###...###.
""".split(), (255, 226, 110), (230, 160, 50)),
}


def draw_mask(rows, light, dark):
    w, hh = max(map(len, rows)), len(rows)
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    ox, oy = (16 - w) // 2, (16 - hh) // 2
    px = img.load()
    fill = {}
    for j, r in enumerate(rows):
        for i, ch in enumerate(r):
            if ch == "#":
                lit = (i + j * 0.6) < (w + hh * 0.6) * 0.45
                fill[(ox + i, oy + j)] = (light if lit else dark) + (255,)
    for (x, y) in fill:
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            q = (x + dx, y + dy)
            if q not in fill and 0 <= q[0] < 16 and 0 <= q[1] < 16:
                px[q] = OUT
    for (x, y), c in fill.items():
        px[x, y] = c
    return img


def draw_heart():
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    pal = {"o": OUT, "r": h("#f26b8a"), "R": h("#ffb3c4"), "d": h("#c94370")}
    for j, r in enumerate(HEART):
        for i, ch in enumerate(r):
            if ch in pal:
                img.putpixel((1 + i, 2 + j), pal[ch])
    return img


def build_fx():
    names = ["heart", "z", "note", "sparkle", "star"]
    imgs = {"heart": draw_heart()}
    for k, (rows, a, b) in MASKS.items():
        imgs[k] = draw_mask(rows, a, b)
    sheet = Image.new("RGBA", (16 * len(names), 16), (0, 0, 0, 0))
    meta = {}
    for i, n in enumerate(names):
        sheet.alpha_composite(imgs[n], (16 * i, 0))
        meta[n] = {"x": 16 * i, "y": 0, "w": 16, "h": 16}
    sheet.save(os.path.join(PEN, "fx.png"))
    with open(os.path.join(PEN, "fx.json"), "w", encoding="utf-8") as f:
        json.dump({"image": "fx.png", "size": list(sheet.size), "sprites": meta}, f, indent=1)


def build_pen_json():
    data = {"bg": "pen_bg.png", "walk_area": list(WALK), "panel": list(PANEL),
            "sleep_spots": [list(p) for p in SLEEP], "spot_radius": 24,
            "play_spots": [list(p) for p in PLAY]}
    with open(os.path.join(PEN, "pen.json"), "w", encoding="utf-8") as f:
        json.dump(data, f, indent=1)


if __name__ == "__main__":
    build_bg()
    build_fx()
    build_pen_json()
    print("ok")
