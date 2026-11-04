"""T9.2: cenario organico do cercado em 3 zonas (pen_bg.png) e pen.json. Pillow + numpy, sem IA.
Uso: python assets/tools/build_t92_bg.py
"""
import json
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from build_t92_layout import AMBIENT, PANEL, RECTS, WALK, ZONES  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PEN = os.path.join(ROOT, "assets", "pen")
W, H = 960, 540
OUT = (59, 42, 56, 255)


def h(c, a=255):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) + (a,)


def noise(w, hh, cell, seed):
    r = np.random.RandomState(seed)
    g = r.rand(hh // cell + 3, w // cell + 3).astype(np.float32)
    im = Image.fromarray((g * 255).astype(np.uint8)).resize(((w // cell + 3) * cell, (hh // cell + 3) * cell), Image.BICUBIC)
    return np.asarray(im)[:hh, :w].astype(np.float32) / 255.0


def sdf_rrect(x0, y0, x1, y1, r):
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    qx = np.abs(xx - cx) - ((x1 - x0) / 2 - r)
    qy = np.abs(yy - cy) - ((y1 - y0) / 2 - r)
    return np.hypot(np.maximum(qx, 0), np.maximum(qy, 0)) + np.minimum(np.maximum(qx, qy), 0) - r


def zone_mask(name, nz):
    x, y, w, hh = RECTS[name]
    inner = {"adultos": dict(r=1), "breed": dict(l=1, b=1), "filhotes": dict(l=1, t=1)}[name]
    mo, mi = 18, 2
    ml = mi if inner.get("l") else mo
    mr = mi if inner.get("r") else mo
    mt = mi if inner.get("t") else mo
    mb = mi if inner.get("b") else mo
    d = sdf_rrect(x - ml, y - mt, x + w + mr, y + hh + mb, 46)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    dist = np.full((H, W), 99, np.float32)
    if inner.get("r"):
        dist = np.minimum(dist, np.abs(xx - 492))
    if inner.get("l"):
        dist = np.minimum(dist, np.abs(xx - 492))
    if inner.get("t"):
        dist = np.minimum(dist, np.abs(yy - 282))
    if inner.get("b"):
        dist = np.minimum(dist, np.abs(yy - 282))
    amp = 1.5 + 12.5 * np.clip(dist / 24, 0, 1)
    return (d + amp * (nz - 0.5) * 2) < 0


def dil(m, n=1):
    for _ in range(n):
        o = m.copy()
        o[1:] |= m[:-1]
        o[:-1] |= m[1:]
        o[:, 1:] |= m[:, :-1]
        o[:, :-1] |= m[:, 1:]
        m = o
    return m


def ero(m, n=1):
    return ~dil(~m, n)


def paint(arr, mask, color):
    arr[mask] = color


def ellipse(d, cx, cy, rx, ry, fill, outline=None):
    d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=fill, outline=outline)


def bush(d, x, y, r, rnd, flowers=None):
    dk, md, lt = h("#12302c"), h("#1f4a40"), h("#2f6a52")
    for dx, dy, rr in ((-r * 0.7, 0, r * 0.7), (r * 0.7, 0, r * 0.7), (0, -r * 0.5, r * 0.85)):
        ellipse(d, round(x + dx), round(y + dy), round(rr), round(rr), dk)
    for dx, dy, rr in ((-r * 0.7, 0, r * 0.7), (r * 0.7, 0, r * 0.7), (0, -r * 0.5, r * 0.85)):
        ellipse(d, round(x + dx), round(y + dy), round(rr) - 1, round(rr) - 1, md)
    ellipse(d, round(x - r * 0.3), round(y - r * 0.8), round(r * 0.45), round(r * 0.3), lt)
    if flowers:
        for _ in range(3):
            d.point((round(x + rnd.uniform(-r, r)), round(y + rnd.uniform(-r * .8, r * .2))), fill=flowers)


def tuft(d, x, y, c1, c2):
    d.line((x, y, x - 2, y - 4), fill=c1)
    d.line((x + 1, y, x + 1, y - 5), fill=c2)
    d.line((x + 2, y, x + 4, y - 3), fill=c1)


def stone(d, x, y, rnd, big=1):
    rx, ry = rnd.randint(3, 5) * big, rnd.randint(2, 3) * big
    ellipse(d, x, y + 1, rx, ry, h("#141a2c"))
    ellipse(d, x, y, rx, ry, OUT)
    ellipse(d, x, y, rx - 1, ry - 1, h("#6a7aa0"))
    ellipse(d, x - 1, y - 1, max(rx - 3, 1), max(ry - 2, 1), h("#8a9ac0"))


def flower(d, x, y, col):
    d.point((x, y), fill=col)
    d.point((x - 1, y), fill=col)
    d.point((x + 1, y), fill=col)
    d.point((x, y - 1), fill=col)
    d.point((x, y + 1), fill=col)
    d.point((x, y), fill=h("#ffe28a"))


def tree(d, x, y, r, rnd):
    d.rectangle((x - 3, y - 4, x + 3, y + 30), fill=h("#1c1624"))
    d.rectangle((x - 2, y - 4, x, y + 30), fill=h("#2a2234"))
    for dx, dy, rr in ((-r * .5, 0, r * .7), (r * .55, -4, r * .7), (0, -r * .6, r * .85), (0, r * .1, r * .8)):
        ellipse(d, round(x + dx), round(y + dy), round(rr), round(rr), h("#0e2226"))
    for dx, dy, rr in ((-r * .5, 0, r * .7), (r * .55, -4, r * .7), (0, -r * .6, r * .85), (0, r * .1, r * .8)):
        ellipse(d, round(x + dx), round(y + dy), round(rr) - 2, round(rr) - 2, h("#163438"))
    ellipse(d, round(x - r * .3), round(y - r * .8), round(r * .45), round(r * .3), h("#1f4a4a"))


def pine(d, x, base, hgt, col):
    for k in range(4):
        w = int(hgt * (0.18 + 0.1 * k))
        y = base - hgt + k * hgt // 4 + hgt // 5
        d.polygon([(x, base - hgt + k * hgt // 5), (x - w, y + hgt // 4), (x + w, y + hgt // 4)], fill=col)
    d.rectangle((x - 1, base - 4, x + 1, base), fill=col)


def fence_h(d, x0, x1, y, pastel=False):
    c_post = h("#d8c9b0") if pastel else h("#4a5a82")
    c_lt = h("#f0e4cc") if pastel else h("#5d6c96")
    c_rail = h("#b8a890") if pastel else h("#3d4a6e")
    for ry in (y - 4, y + 3):
        d.rectangle((x0, ry, x1, ry + 2), fill=OUT)
        d.line((x0, ry + 1, x1, ry + 1), fill=c_rail)
    for px in range(x0 + 2, x1, 12):
        d.rectangle((px, y - 9, px + 4, y + 8), fill=OUT)
        d.rectangle((px + 1, y - 8, px + 3, y + 7), fill=c_post)
        d.line((px + 1, y - 8, px + 1, y + 7), fill=c_lt)
        d.polygon([(px, y - 9), (px + 4, y - 9), (px + 2, y - 12)], fill=OUT)


def fence_v(d, x, y0, y1, pastel=False):
    c_post = h("#d8c9b0") if pastel else h("#4a5a82")
    c_lt = h("#f0e4cc") if pastel else h("#5d6c96")
    for py in range(y0, y1, 11):
        d.rectangle((x - 3, py - 8, x + 3, py + 3), fill=OUT)
        d.rectangle((x - 2, py - 7, x + 2, py + 2), fill=c_post)
        d.line((x - 2, py - 7, x - 2, py + 2), fill=c_lt)
    d.rectangle((x - 1, y0 - 8, x, y1 + 2), fill=OUT)


def build():
    rnd = random.Random(92)
    nrnd = np.random.RandomState(92)
    arr = np.zeros((H, W, 4), np.uint8)
    arr[:] = h("#14222b")
    # chao externo (floresta)
    n1, n2 = noise(W, H, 20, 1), noise(W, H, 5, 2)
    ext = [h("#101c26"), h("#14222b"), h("#182a32"), h("#0f1a22")]
    idx = np.clip(((n1 * 0.6 + n2 * 0.4) * 4).astype(int), 0, 3)
    for i, c in enumerate(ext):
        arr[idx == i] = c
    # ceu
    for y in range(0, 52):
        t = y / 52
        c = tuple(int(a + (b - a) * t) for a, b in zip(h("#0a0e20")[:3], h("#1b2848")[:3])) + (255,)
        arr[y, :] = c
    im = Image.fromarray(arr, "RGBA")
    d = ImageDraw.Draw(im)
    for _ in range(70):
        d.point((rnd.randrange(W), rnd.randrange(0, 46)), fill=rnd.choice([h("#3a4a7a"), h("#5a6a98"), h("#8a9ac0")]))
    # silhueta de floresta ao fundo
    for x in range(-10, W + 10, 14):
        hg = rnd.randint(34, 52)
        pine(d, x + rnd.randint(-3, 3), 90, hg, h("#0b1822"))
    for x in range(0, W, 22):
        hg = rnd.randint(26, 40)
        pine(d, x + rnd.randint(-4, 4), 96, hg, h("#10242c"))
    d.rectangle((0, 90, W, 112), fill=h("#14222b"))
    arr = np.asarray(im).copy()
    # tufos de grama externos
    im = Image.fromarray(arr, "RGBA")
    d = ImageDraw.Draw(im)
    for _ in range(2600):
        x, y = rnd.randrange(W), rnd.randrange(96, H)
        tuft(d, x, y, rnd.choice([h("#16303a"), h("#1a3640"), h("#12262e")]), h("#1f4048"))
    arr = np.asarray(im).copy()

    pal = {
        "adultos": ([h("#1f3d3b"), h("#234440"), h("#1c3836"), h("#274a45")], h("#10282a"), h("#315f54")),
        "breed": ([h("#4a3a44"), h("#523f48"), h("#42343f"), h("#5a454c")], h("#241a28"), h("#6a4a4c")),
        "filhotes": ([h("#2b4f42"), h("#2f5646"), h("#274a3e"), h("#335b4a")], h("#16302c"), h("#52806a")),
    }
    masks = {}
    for zi, name in enumerate(("adultos", "breed", "filhotes")):
        m = zone_mask(name, noise(W, H, 44, 10 + zi) * 0.7 + noise(W, H, 14, 20 + zi) * 0.3)
        masks[name] = m
        cols, bankc, lipc = pal[name]
        bank = dil(m, 4) & ~m
        paint(arr, dil(m, 5) & ~dil(m, 4), h("#0b1416"))
        paint(arr, bank, bankc)
        # barranco: faixa mais escura abaixo
        sh = np.zeros_like(m)
        sh[3:] = m[:-3]
        paint(arr, dil(m, 3) & ~m & ~sh * 0 & (np.arange(H)[:, None] > 0), bankc)
        a = noise(W, H, 30, 30 + zi)
        b = noise(W, H, 3, 40 + zi)
        ix = np.clip(((a * 0.35 + b * 0.65 - 0.1) * 5.5).astype(int), 0, 3)
        for i, c in enumerate(cols):
            paint(arr, m & (ix == i), c)
        if name == "breed":
            moss = noise(W, H, 12, 50) > 0.8
            paint(arr, m & moss, h("#2f4a3e"))
            paint(arr, m & moss & (noise(W, H, 4, 51) > 0.6), h("#38574a"))
        paint(arr, m & ~ero(m, 2), lipc)
        paint(arr, m & ~ero(m, 1), bankc if name != "adultos" else h("#244a44"))
    im = Image.fromarray(arr, "RGBA")
    d = ImageDraw.Draw(im)

    # caminhos de terra no cercado dos adultos
    path = Image.new("L", (W, H), 0)
    pd = ImageDraw.Draw(path)

    def road(pts, wd):
        for (ax, ay), (bx, by) in zip(pts, pts[1:]):
            n = int(math.hypot(bx - ax, by - ay) / 3) + 1
            for i in range(n + 1):
                u = i / n
                px, py = ax + (bx - ax) * u + rnd.uniform(-1.5, 1.5), ay + (by - ay) * u + rnd.uniform(-1.5, 1.5)
                r = wd / 2 + rnd.uniform(-1.5, 1.5)
                pd.ellipse((px - r, py - r * 0.75, px + r, py + r * 0.75), fill=255)
    road([(70, 380), (140, 330), (210, 335), (290, 300), (350, 270), (430, 250), (470, 215)], 16)
    road([(290, 300), (270, 360), (250, 430)], 12)
    road([(140, 330), (110, 250), (110, 200)], 12)
    road([(350, 270), (340, 200), (270, 170)], 12)
    pm = (np.asarray(path) > 128) & masks["adultos"] & ero(masks["adultos"], 5)
    pm &= noise(W, H, 5, 60) > 0.05
    arr = np.asarray(im).copy()
    dirt = [h("#4a3e48"), h("#554752"), h("#40353f"), h("#5e4e56")]
    ix = np.clip((noise(W, H, 5, 61) * 4).astype(int), 0, 3)
    edge = pm & ~ero(pm, 1)
    for i, c in enumerate(dirt):
        paint(arr, pm & (ix == i), c)
    paint(arr, edge, h("#33293a"))
    # pedras de passo no recanto do breed
    im = Image.fromarray(arr, "RGBA")
    d = ImageDraw.Draw(im)
    for x, y in ((520, 208), (536, 222), (572, 214), (596, 208), (626, 216), (650, 210), (676, 218), (690, 236),
                 (556, 270), (640, 270)):
        if masks["breed"][y, x]:
            ellipse(d, x, y, 7, 4, h("#241a28"))
            ellipse(d, x, y - 1, 6, 3, h("#6a5a6a"))
            ellipse(d, x - 1, y - 2, 4, 1, h("#8a7a88"))

    # decoracao interna (longe dos objetos)
    objs = [(o["x"], o["y"]) for z in ZONES.values() for o in z["objects"]]

    def free(x, y, r=34):
        return all(abs(x - ox) > r or abs(y - oy) > r * 0.8 for ox, oy in objs)

    for name, cnt, kind in (("adultos", 330, "g"), ("breed", 110, "b"), ("filhotes", 170, "f")):
        m = masks[name]
        inner = ero(m, 4)
        rx0, ry0, rw0, rh0 = RECTS[name]
        for _ in range(cnt * 2):
            x, y = rnd.randrange(rx0, rx0 + rw0), rnd.randrange(ry0, ry0 + rh0)
            if not inner[y, x] or (name == "adultos" and pm[y, x]):
                continue
            if not free(x, y, 22):
                continue
            r = rnd.random()
            if name == "adultos":
                if r < 0.7:
                    tuft(d, x, y, h("#2a5249"), h("#3a6a5a"))
                elif r < 0.85:
                    stone(d, x, y, rnd, 1)
                else:
                    flower(d, x, y, rnd.choice([h("#c9b6e8"), h("#f0b8c8"), h("#f6e3c8")]))
            elif name == "breed":
                if r < 0.4:
                    tuft(d, x, y, h("#3a5a48"), h("#4a7058"))
                elif r < 0.7:
                    flower(d, x, y, rnd.choice([h("#f09aa8"), h("#e8a0b0")]))
                else:
                    d.point((x, y), fill=h("#8a5a4c"))
                    d.point((x + 1, y), fill=h("#a8685a"))
            else:
                if r < 0.45:
                    tuft(d, x, y, h("#3f6a58"), h("#52806a"))
                elif r < 0.85:
                    flower(d, x, y, rnd.choice([h("#ffffff"), h("#f8c4cc"), h("#bcd0f0"), h("#fff0b0")]))
                else:  # bloquinho de brinquedo
                    c = rnd.choice([h("#f58aa8"), h("#9fd8c4"), h("#f5e07a"), h("#9fb8e0")])
                    d.rectangle((x - 3, y - 3, x + 3, y + 3), fill=OUT)
                    d.rectangle((x - 2, y - 2, x + 2, y + 2), fill=c)
                    d.point((x - 1, y - 1), fill=h("#ffffff"))

    # bordas: pedras, arbustos e flores ao redor de cada zona
    for name, m in masks.items():
        e = dil(m, 5) & ~dil(m, 4)
        ys, xs = np.nonzero(e)
        pts = list(zip(xs.tolist(), ys.tolist()))
        rnd.shuffle(pts)
        placed = []
        for x, y in pts:
            if any(abs(x - px) < 13 and abs(y - py) < 10 for px, py in placed):
                continue
            if name == "adultos" and x > 484 and y > 96:
                continue
            if name != "adultos" and x < 500 and y > 96:
                continue
            if name == "filhotes" and y < 292:
                continue
            if name == "breed" and y > 270 and x < 718:
                continue
            placed.append((x, y))
            r = rnd.random()
            if r < 0.4:
                bush(d, x, y + 2, rnd.randint(5, 7), rnd, h("#f09aa8") if name == "breed" else None)
            elif r < 0.7:
                stone(d, x, y + 1, rnd)
            elif r < 0.85:
                flower(d, x, y, rnd.choice([h("#c9b6e8"), h("#f0b8c8"), h("#f6e3c8")]))
            else:
                tuft(d, x, y + 2, h("#2a5249"), h("#3a6a5a"))

    # divisorias baixas
    # vertical x=492 com passagens y 180..232 (breed) e 372..424 (filhotes)
    for (ya, yb) in ((100, 180), (232, 372), (424, 466)):
        for yy in range(ya, yb, 15):
            bush(d, 492, yy + 6, 6, rnd)
        for yy in range(ya + 7, yb, 15):
            if rnd.random() < 0.5:
                stone(d, 492, yy + 8, rnd)
    # horizontal y=282 entre breed e filhotes, passagem x 582..642 (cerquinha pastel)
    fence_h(d, 502, 582, 282, pastel=True)
    fence_h(d, 642, 712, 282, pastel=True)
    # cercadinho pastel do viveiro: laterais baixas
    fence_v(d, 710, 296, 466, pastel=True)

    # luzinhas penduradas no recanto do breed
    pts = []
    for i in range(0, 17):
        u = i / 16
        x = 502 + u * 204
        y = 108 + 7 * math.sin(math.pi * u) + (i % 2) * 0
        pts.append((x, y))
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        d.line((ax, ay, bx, by), fill=h("#2a2234"))
    for i, (x, y) in enumerate(pts[1:-1:2]):
        c = [h("#ffd84a"), h("#f09aa8"), h("#ffe8a0")][i % 3]
        d.rectangle((x - 1, y + 1, x + 1, y + 3), fill=c)
        d.point((x, y + 4), fill=h("#c98a4a"))

    # cerca superior e arvores/arbustos externos
    fence_h(d, 84, 676, 90)
    # arvores laterais
    for tx, ty, tr in ((14, 190, 26), (10, 330, 22), (18, 440, 24), (730, 200, 22), (728, 420, 24)):
        tree(d, tx, ty, tr, rnd)
    # moitas esparsas fora do cercado (sem linha reta)
    for _ in range(60):
        x, y = rnd.randrange(0, 736), rnd.randrange(484, 536)
        if 330 < x < 430 and y > 490:
            continue
        bush(d, x, y, rnd.randint(6, 9), rnd, h("#f0b8c8") if rnd.random() < 0.3 else None)
    for _ in range(80):
        x, y = rnd.randrange(0, 736), rnd.randrange(496, 536)
        flower(d, x, y, rnd.choice([h("#c9b6e8"), h("#f0b8c8"), h("#fff0b0"), h("#9fd8c4")]))
    for _ in range(60):
        x, y = rnd.randrange(0, 736), rnd.randrange(500, 538)
        tuft(d, x, y, h("#1e4a3e"), h("#2a5a4a"))

    arr = np.asarray(im).copy().astype(np.float32)
    # poças de luz das lanternas (aneis discretos)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    for a in AMBIENT:
        if a["kind"] != "lanterna":
            continue
        dd = np.hypot((xx - a["x"]) / 1.0, (yy - a["y"] + 6) / 0.7)
        for rad, k in ((60, 0.03), (42, 0.035), (24, 0.04)):
            msk = dd < rad
            arr[msk, 0] += (255 - arr[msk, 0]) * k
            arr[msk, 1] += (190 - arr[msk, 1]) * k
            arr[msk, 2] += (100 - arr[msk, 2]) * k
    # painel direito: escurecido e discreto
    pm2 = np.zeros((H, W), np.float32)
    pm2[:, 740:] = 1
    pm2 = np.asarray(Image.fromarray((pm2 * 255).astype(np.uint8)).filter(__import__("PIL.ImageFilter", fromlist=["x"]).GaussianBlur(10))) / 255.0
    arr[:, :, :3] *= (1 - 0.38 * pm2)[:, :, None]
    # vinheta suave
    v = np.hypot((xx - 380) / 520, (yy - 290) / 330)
    arr[:, :, :3] *= np.clip(1.08 - 0.25 * v ** 2, 0.7, 1.0)[:, :, None]
    out = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA")
    out = out.convert("RGB")
    out.save(os.path.join(PEN, "pen_bg.png"))
    return masks


def write_json():
    pen = {"bg": "pen_bg.png", "walk_area": WALK, "panel": PANEL,
           "anchors": "x,y = centro-base do objeto; slots = offsets (dx,dy) do centro-base do gato; layer floor = abaixo de todos os gatos, sorted = ordenar por y",
           "zones": ZONES, "ambient": AMBIENT}
    with open(os.path.join(PEN, "pen.json"), "w") as f:
        json.dump(pen, f, indent=1)


if __name__ == "__main__":
    build()
    write_json()
    print("ok")
