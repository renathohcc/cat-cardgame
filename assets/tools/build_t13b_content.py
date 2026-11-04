"""T13.3b: arte do conteudo das areas 4 a 6 (lagoa+jardim, patio nobre/cama do casal 3, pomar+arvore grande).
Pillow, 100% script proprio, so paleta PEN, alpha 0/255. Saida: assets/pen/lock/conteudo/ + conteudo.json.
Nao altera os retangulos de areas.json (le de la)."""
from __future__ import annotations
import json, math, random
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT / "pen" / "lock"
OUT = LOCK / "conteudo"
_raw = json.loads((ROOT / "pen" / "palette_pen.json").read_text(encoding="utf-8"))
C = {k: tuple(int(v.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)) + (255,) for k, v in _raw.items() if isinstance(v, str)}
O = C["outline"]
CLEAR = (0, 0, 0, 0)
AREAS = {a["id"]: a for a in json.loads((LOCK / "areas.json").read_text(encoding="utf-8"))["areas"]}


def px(im, x, y, c):
    x, y = int(round(x)), int(round(y))
    if 0 <= x < im.width and 0 <= y < im.height:
        im.putpixel((x, y), c)


def ell(im, cx, cy, rx, ry, c):
    for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
        for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
            if ((x - cx) / (rx + .3)) ** 2 + ((y - cy) / (ry + .3)) ** 2 <= 1:
                px(im, x, y, c)


def disk(im, cx, cy, r, c):
    ell(im, cx, cy, r, r, c)


def rect(im, x, y, w, h, c, outline=None):
    ImageDraw.Draw(im).rectangle([x, y, x + w - 1, y + h - 1], fill=c, outline=outline)


def outline_outer(im):
    src = im.copy()
    for y in range(im.height):
        for x in range(im.width):
            if src.getpixel((x, y))[3] == 0 and any(
                    0 <= x + dx < im.width and 0 <= y + dy < im.height and src.getpixel((x + dx, y + dy))[3]
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                im.putpixel((x, y), O)


def flower(im, x, y, col):
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        px(im, x + dx, y + dy, col)
    px(im, x, y, C["yellow"])


def shadow(im, cx, cy, rx, ry):
    for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
        for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
            d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
            if d <= .6 or (d <= 1 and (x + y) % 2 == 0):
                px(im, x, y, C["grass_dark"])


def bed(im, x, y, w, h):
    """canteiro de flores visto de cima, com borda de madeira."""
    rect(im, x, y, w, h, C["dirt"], O)
    d = ImageDraw.Draw(im)
    d.line([x + 1, y + h - 2, x + w - 2, y + h - 2], fill=C["dirt_dark"])
    d.line([x + 1, y + 1, x + w - 2, y + 1], fill=C["wood_light"])
    cols = [C["flower_pink"], C["flower_red"], C["yellow"], C["x8"], C["flower_pink"], C["flower_red"]]
    for i, xx in enumerate(range(x + 5, x + w - 4, 7)):
        px(im, xx, y + h - 5, C["bush"]); px(im, xx, y + h - 4, C["bush_dark"])
        px(im, xx - 1, y + h - 5, C["bush_light"]); px(im, xx + 1, y + h - 5, C["bush_light"])
        flower(im, xx, y + 6, cols[i % len(cols)])


# ---------------- lagoa e jardim (area 4) ----------------
PC, PRX, PRY = (108, 70), 52, 30


def pond_r(th):
    return 1 + .10 * math.sin(2 * th + 1) + .07 * math.sin(3 * th + 2) + .04 * math.sin(5 * th)


def pond_d(x, y):
    dx, dy = (x - PC[0]) / PRX, (y - PC[1]) / PRY
    return math.hypot(dx, dy) / pond_r(math.atan2(dy, dx))


def lily(im, x, y, flowerc=None):
    ell(im, x, y, 4, 2, C["bush_dark"]); ell(im, x, y, 3, 1.4, C["bush_light"])
    px(im, x + 3, y, C["teal"]); px(im, x + 2, y, C["teal"])
    px(im, x - 1, y - 1, C["grass_light"])
    if flowerc:
        px(im, x - 1, y - 1, flowerc); px(im, x, y - 2, C["cream_light"]); px(im, x + 1, y - 1, flowerc)


def reed(im, x, y, h):
    for k in range(h):
        px(im, x, y - k, C["bush_light"] if k % 3 else C["bush"])
        if k > h // 2:
            px(im, x + 1, y - k, C["bush_dark"])
    for k in range(3):
        px(im, x, y - h - k, C["wood"]); px(im, x + 1, y - h - k, C["wood_dark"])
    px(im, x - 1, y - h // 2, C["bush"]); px(im, x - 2, y - h // 2 - 1, C["bush"])


def stone(im, x, y):
    ell(im, x, y, 4, 2.5, O)
    ell(im, x, y - .5, 3, 1.5, C["stone"])
    px(im, x - 1, y - 1, C["stone_light"]); px(im, x - 2, y - 1, C["stone_light"])
    px(im, x + 2, y, C["stone_dark"]); px(im, x + 1, y + 1, C["stone_dark"])


RIPPLES = [(-30, -6, 4), (-10, 8, 5), (14, -12, 4), (28, 4, 5), (0, -2, 3), (-22, 16, 3), (36, -8, 3), (-4, 18, 4)]


def build_lagoa(frame=0):
    im = Image.new("RGBA", (192, 144), CLEAR)
    for y in range(144):
        for x in range(192):
            d = pond_d(x, y)
            if d <= 1.17:
                if d <= 1.0:
                    im.putpixel((x, y), C["teal"])
                else:
                    t = (x - PC[0]) + (y - PC[1])
                    c = C["path"]
                    if t < -10 and (x + y) % 2 == 0:
                        c = C["path_light"]
                    if t < -25:
                        c = C["path_light"]
                    if t > 25 and (x + y) % 2:
                        c = C["path_dark"]
                    im.putpixel((x, y), c)
    for y in range(144):   # contorno e sombra da margem dentro da agua
        for x in range(192):
            d = pond_d(x, y)
            if d <= 1.0:
                if d > .93:
                    im.putpixel((x, y), O)
                elif pond_d(x - 2, y - 3) > 1.0 or pond_d(x - 1, y - 2) > 1.0:
                    im.putpixel((x, y), C["teal_dark"])
                elif pond_d(x + 2, y + 2) > .93 and (x + y) % 2 == 0:
                    im.putpixel((x, y), C["teal_light"])
    for i, (dx, dy, ln) in enumerate(RIPPLES):
        if (frame + i) % 4 < 2:
            for k in range(ln):
                px(im, PC[0] + dx + k, PC[1] + dy, C["teal_light"])
        elif (frame + i) % 4 == 2:
            for k in range(ln - 2):
                px(im, PC[0] + dx + 1 + k, PC[1] + dy, C["x16"])
    for i, (dx, dy) in enumerate(((-16, -14), (22, 12), (-36, 8))):   # brilhinhos
        if (frame + i) % 4 == 0:
            px(im, PC[0] + dx, PC[1] + dy, C["cream_light"])
            px(im, PC[0] + dx + 1, PC[1] + dy, C["cream_light"])
    lily(im, PC[0] - 18, PC[1] + 6, C["flower_pink"]); lily(im, PC[0] + 12, PC[1] - 8)
    lily(im, PC[0] + 26, PC[1] + 12, C["cream_light"]); lily(im, PC[0] - 34, PC[1] - 10)
    for x, y, h in ((PC[0] - 52, PC[1] + 8, 12), (PC[0] - 49, PC[1] + 12, 9), (PC[0] + 50, PC[1] - 2, 11),
                    (PC[0] + 47, PC[1] + 4, 8), (PC[0] + 53, PC[1] + 5, 10)):
        reed(im, x, y, h)
    for x, y in ((PC[0] - 40, PC[1] + 30), (PC[0] - 28, PC[1] + 34), (PC[0] + 34, PC[1] + 31),
                 (PC[0] + 46, PC[1] + 22), (PC[0] - 54, PC[1] - 10), (PC[0] + 8, PC[1] - 36), (PC[0] + 22, PC[1] - 34)):
        stone(im, x, y)
    bed(im, 8, 10, 44, 20); bed(im, 140, 10, 44, 20)   # jardim: canteiros, trilha e flores
    for x, y in ((14, 112), (26, 116), (38, 110), (150, 114), (162, 110), (174, 116)):
        stone(im, x, y)
    for x, y, col in ((14, 50, C["flower_pink"]), (22, 56, C["flower_red"]), (10, 64, C["yellow"]), (172, 56, C["flower_pink"]),
                      (180, 66, C["flower_red"]), (166, 70, C["x8"]), (30, 90, C["flower_pink"]), (160, 96, C["yellow"]),
                      (92, 118, C["flower_red"]), (118, 120, C["flower_pink"]), (60, 122, C["yellow"])):
        flower(im, x, y, col)
    for x, y in ((6, 80), (184, 84)):    # arbustinhos floridos
        disk(im, x + 3, y + 3, 6, O); disk(im, x + 3, y + 3, 5, C["bush_dark"]); disk(im, x + 2, y + 2, 4, C["bush"])
        px(im, x + 1, y + 1, C["bush_light"]); px(im, x + 3, y + 3, C["flower_pink"]); px(im, x + 5, y + 1, C["flower_red"])
    return im


# ---------------- patio nobre / cama do casal 3 (area 5) ----------------
def pillow(im, cx, cy):
    ell(im, cx, cy, 9, 5, O); ell(im, cx, cy, 8, 4, C["cream_light"])
    ImageDraw.Draw(im).line([cx - 6, cy + 3, cx + 6, cy + 3], fill=C["cream_dark"])
    px(im, cx - 5, cy - 2, C["cream"])


def heart(im, cx, cy):
    for col, k in ((O, 1), (C["x3"], 0)):
        ell(im, cx - 4, cy - 2, 4 + k, 4 + k, col); ell(im, cx + 4, cy - 2, 4 + k, 4 + k, col)
        for y in range(cy - 2, cy + 8):
            w = max(0, 8 + k - max(0, y - (cy - 1)))
            ImageDraw.Draw(im).line([cx - w, y, cx + w, y], fill=col)
    px(im, cx - 6, cy - 3, C["x8"]); px(im, cx - 5, cy - 4, C["x8"])


def build_cama_nobre():
    s = Image.new("RGBA", (140, 90), CLEAR)
    cx, cy = 70, 52
    ell(s, cx, cy - 2, 57, 29, C["rose_dark"])        # cabeceira em arco
    ell(s, cx, cy - 3, 55, 27, C["rose"])
    ell(s, cx, cy - 1, 48, 22, C["rose_light"])
    for a in range(200, 341, 10):
        px(s, cx + math.cos(math.radians(a)) * 54, cy - 3 + math.sin(math.radians(a)) * 26, C["yellow"])
    ell(s, cx, cy + 6, 62, 30, C["rose_dark"])        # anel externo
    ell(s, cx, cy + 4, 62, 29, C["rose"])
    ell(s, cx - 1, cy + 2, 58, 25, C["rose_light"])
    ell(s, cx, cy + 3, 55, 23, C["rose"])
    ell(s, cx, cy + 4, 51, 20, C["cream_dark"])
    ell(s, cx, cy + 3, 50, 19, C["cream"])
    ell(s, cx - 2, cy + 1, 40, 14, C["cream_light"])
    for a in range(0, 360, 12):
        px(s, cx + math.cos(math.radians(a)) * 57, cy + 3 + math.sin(math.radians(a)) * 24, C["yellow"])
    for xx in range(cx - 36, cx + 37, 12):            # capitone
        px(s, xx, cy + 10, C["cream_dark"]); px(s, xx + 6, cy + 4, C["cream_dark"])
    pillow(s, cx - 26, cy - 6); pillow(s, cx + 26, cy - 6)
    heart(s, cx, cy - 8)
    pts = [(cx - 8, cy - 28), (cx - 8, cy - 34), (cx - 4, cy - 31), (cx, cy - 36), (cx + 4, cy - 31), (cx + 8, cy - 34), (cx + 8, cy - 28)]
    ImageDraw.Draw(s).polygon(pts, fill=C["yellow"], outline=O)   # coroa na cabeceira
    px(s, cx, cy - 34, C["cream_light"]); px(s, cx - 6, cy - 31, C["x3"]); px(s, cx + 6, cy - 31, C["flower_pink"])
    outline_outer(s)
    return s, (cx, 84)


def topiary(im, x, y):
    rect(im, x - 5, y + 6, 10, 8, C["wood"], O)
    ImageDraw.Draw(im).line([x - 4, y + 7, x + 3, y + 7], fill=C["wood_light"])
    disk(im, x, y, 9, O); disk(im, x, y, 8, C["bush_dark"]); disk(im, x - 1, y - 1, 7, C["bush"])
    disk(im, x - 3, y - 3, 3, C["bush_light"]); px(im, x - 4, y - 4, C["grass_light"])
    for dx, dy in ((3, 2), (-2, 4), (4, -2)):
        px(im, x + dx, y + dy, C["flower_pink"])


def build_nobre():
    im = Image.new("RGBA", (192, 144), CLEAR)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([6, 8, 185, 131], radius=10, fill=O)    # praca de ladrilhos com borda de pedra
    d.rounded_rectangle([7, 9, 184, 130], radius=9, fill=C["stone"])
    d.rounded_rectangle([9, 11, 182, 128], radius=8, fill=C["path"])
    for y in range(12, 128):
        for x in range(10, 182):
            if im.getpixel((x, y)) != C["path"]:
                continue
            if (x - 10) % 12 == 0 or (y - 12) % 12 == 0:
                im.putpixel((x, y), C["path_dark"])
            elif ((x - 10) // 12 + (y - 12) // 12) % 2 == 0 and (x - 10) % 12 < 3 and (y - 12) % 12 < 2:
                im.putpixel((x, y), C["path_light"])
    for x, y in ((14, 12), (20, 12), (172, 12), (14, 122), (176, 122)):
        px(im, x, y - 2, C["stone_light"]); px(im, x + 1, y - 2, C["stone_light"])
    ell(im, 96, 92, 82, 34, O); ell(im, 96, 92, 81, 33, C["rose_dark"]); ell(im, 96, 91, 79, 31, C["rose"])   # tapete
    ell(im, 96, 91, 72, 26, C["rose_light"]); ell(im, 96, 92, 70, 25, C["rose"])
    for a in range(0, 360, 6):
        px(im, 96 + math.cos(math.radians(a)) * 74, 91 + math.sin(math.radians(a)) * 27, C["yellow"])
    sprite, (ax, ay) = build_cama_nobre()
    bx, by = 96, 100
    im.alpha_composite(sprite, (bx - ax, by - ay))
    for x, y in ((24, 22), (168, 22), (24, 110), (168, 110)):
        topiary(im, x, y)
    for x, y, col in ((50, 26, C["flower_pink"]), (140, 26, C["flower_red"]), (48, 124, C["yellow"]), (146, 124, C["flower_pink"])):
        flower(im, x, y, col)
    return im, (bx, by)


# ---------------- pomar e arvore grande (area 6) ----------------
def crown(im, clumps, rng):
    for cx, cy, r in sorted(clumps, key=lambda c: c[1]):
        disk(im, cx + 1, cy + 2, r, C["bush_dark"])
        disk(im, cx, cy, r - 1, C["bush"])
        disk(im, cx - r * .3, cy - r * .35, r * .55, C["bush_light"])
        for _ in range(int(r * .9)):
            a, rr = rng.uniform(0, 6.28), rng.uniform(0, r * .55)
            px(im, cx - r * .3 + math.cos(a) * rr, cy - r * .35 + math.sin(a) * rr, C["grass_light"] if rng.random() < .5 else C["x5"])
        for _ in range(int(r * .7)):
            a, rr = rng.uniform(0, 6.28), rng.uniform(r * .4, r * .9)
            px(im, cx + math.cos(a) * rr + 1, cy + math.sin(a) * rr + 2, C["bush_dark"])


def apples(im, pts, n, rng):
    ok = [(x, y) for (x, y) in pts if im.getpixel((x, y))[3]]
    for x, y in rng.sample(ok, min(n, len(ok))):
        rect(im, x, y, 3, 3, C["flower_red"])
        px(im, x, y, C["x8"]); px(im, x + 2, y + 2, C["x3"])
        px(im, x + 1, y - 1, C["bush_dark"])


def trunk(im, cx, y0, y1, w):
    for y in range(y0, y1 + 1):
        t = (y - y0) / max(1, y1 - y0)
        hw = w // 2 + (int((t - .65) * 14) if t > .65 else 0)
        for x in range(cx - hw, cx + hw + 1):
            c = C["wood"]
            if x <= cx - hw + 1:
                c = C["wood_light"]
            if x >= cx + hw - 2:
                c = C["wood_dark"]
            px(im, x, y, c)
        if y % 5 == 0:
            px(im, cx + 1, y, C["wood_dark"])


def build_arvore_grande():
    rng = random.Random(4003)
    im = Image.new("RGBA", (112, 96), CLEAR)
    trunk(im, 56, 54, 91, 12)
    crown(im, [(56, 16, 16), (34, 28, 15), (78, 28, 16), (56, 34, 20), (20, 44, 12), (92, 44, 13), (42, 52, 14), (70, 54, 14)], rng)
    apples(im, [(x, y) for y in range(10, 66) for x in range(10, 104)], 14, rng)
    outline_outer(im)
    return im, (56, 92)


def build_arvore_pequena():
    rng = random.Random(4004)
    im = Image.new("RGBA", (40, 46), CLEAR)
    trunk(im, 20, 28, 42, 6)
    crown(im, [(20, 12, 10), (11, 20, 9), (29, 20, 9), (20, 22, 11)], rng)
    apples(im, [(x, y) for y in range(6, 30) for x in range(4, 36)], 5, rng)
    outline_outer(im)
    return im, (20, 43)


def build_pomar_floor(big, smalls):
    rng = random.Random(4005)
    im = Image.new("RGBA", (128, 144), CLEAR)
    shadow(im, big[0], big[1] + 2, 36, 9)
    for ax, ay in smalls:
        shadow(im, ax, ay + 1, 15, 4)
    for _ in range(16):
        x, y = rng.randint(6, 120), rng.randint(104, 138)
        for k in range(3):
            px(im, x, y - k, C["grass_dark"]); px(im, x + 2, y - k + 1, C["grass_light"])
    for x, y, col in ((18, 96, C["flower_pink"]), (110, 100, C["yellow"]), (60, 134, C["flower_red"]), (8, 70, C["flower_pink"]),
                      (118, 74, C["flower_red"]), (40, 124, C["yellow"]), (98, 134, C["flower_pink"])):
        flower(im, x, y, col)
    for x, y in ((44, 108), (52, 112), (80, 106), (86, 110), (70, 114), (58, 100)):   # macas caidas
        disk(im, x, y, 2, O); px(im, x, y, C["flower_red"]); px(im, x + 1, y, C["flower_red"]); px(im, x - 1, y - 1, C["x8"])
    rect(im, 94, 108, 18, 12, C["wood"], O)                                              # caixote de macas
    d = ImageDraw.Draw(im)
    for xx in (97, 103, 109):
        d.line([xx, 109, xx, 118], fill=C["wood_dark"])
    d.line([95, 109, 110, 109], fill=C["wood_light"])
    for x, y in ((98, 106), (104, 105), (108, 107), (101, 108)):
        disk(im, x, y, 2, O); disk(im, x, y, 1, C["flower_red"]); px(im, x - 1, y - 1, C["x8"])
    for dx in (-8, 8):                                                                   # raizes
        for k in range(5):
            px(im, big[0] + dx * (1 + k * .35), big[1] - 1 + k // 2, C["wood_dark"])
    rect(im, 22, 112, 3, 2, C["cream_light"], O)                                         # cogumelo
    for x in (22, 23, 24):
        px(im, x, 111, C["x3"])
    return im


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    objs = {}
    r = AREAS["jardim-lagoa"]["rect"]
    frames = [build_lagoa(f) for f in range(4)]
    frames[0].save(OUT / "jardim-lagoa_floor.png")
    sheet = Image.new("RGBA", (192 * 4, 144), CLEAR)
    for i, f in enumerate(frames):
        sheet.paste(f, (i * 192, 0))
    sheet.save(OUT / "jardim-lagoa_floor_anim.png")
    objs["jardim-lagoa"] = {
        "rect": r, "floor": "jardim-lagoa_floor.png",
        "floor_anim": {"file": "jardim-lagoa_floor_anim.png", "frame_size": [192, 144], "frames": 4, "fps": 3, "loop": True},
        "sorted": [],
        "objects": [{"kind": "lagoa", "x": r[0] + PC[0], "y": r[1] + PC[1] + 30, "layer": "floor",
                     "slots": [[-60, -22], [60, -22], [0, 8]], "slot_use": "play"}]}
    r = AREAS["patio-casais-nobre"]["rect"]
    im, (bx, by) = build_nobre()
    im.save(OUT / "patio-casais-nobre_floor.png")
    objs["patio-casais-nobre"] = {
        "rect": r, "floor": "patio-casais-nobre_floor.png", "sorted": [],
        "objects": [{"kind": "cama_casal_nobre", "x": r[0] + bx, "y": r[1] + by, "layer": "floor",
                     "slots": [[-24, -14], [24, -14]], "slot_use": "sleep",
                     "note": "cama ja desenhada no floor; x,y = centro-base (convencao de cama_casal)"}]}
    r = AREAS["pomar"]["rect"]
    big, (gax, gay) = build_arvore_grande()
    small, (sax, say) = build_arvore_pequena()
    big.save(OUT / "arvore_grande.png"); small.save(OUT / "arvore_pequena.png")
    big_l, smalls_l = (64, 104), [(22, 128), (106, 128)]
    build_pomar_floor(big_l, smalls_l).save(OUT / "pomar_floor.png")
    srt = [{"file": "arvore_grande.png", "size": list(big.size), "anchor": [gax, gay], "x": r[0] + big_l[0], "y": r[1] + big_l[1]}]
    for sx, sy in smalls_l:
        srt.append({"file": "arvore_pequena.png", "size": list(small.size), "anchor": [sax, say], "x": r[0] + sx, "y": r[1] + sy})
    objs["pomar"] = {"rect": r, "floor": "pomar_floor.png", "sorted": srt,
                     "objects": [{"kind": "arvore_grande", "x": r[0] + big_l[0], "y": r[1] + big_l[1], "layer": "sorted",
                                  "slots": [[-34, 4], [34, 4]], "slot_use": "sleep"}]}
    (LOCK / "conteudo.json").write_text(json.dumps({
        "note": "floor = camada do tamanho exato do rect (abaixo dos gatos, revelada ao desbloquear); sorted = sprites ordenados por y "
                "(x,y = centro-base absoluto, anchor dentro do sprite); objects = ancoras de slots no formato do pen.json (coordenadas "
                "absolutas). Desenhar so depois do desbloqueio. Tinta do periodo: mesmo BLEND_MULT do fundo.",
        "areas": objs}, indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
