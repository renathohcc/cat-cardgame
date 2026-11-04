"""T13.3: camadas de bloqueio, placas, animacao de desbloqueio e icones 16x16 (Pillow, 100% script proprio).
Usa so a paleta PEN (assets/pen/palette_pen.json). Saida: assets/pen/lock/."""
from __future__ import annotations
import json, math, random
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "pen" / "lock"
_raw = json.loads((ROOT / "pen" / "palette_pen.json").read_text(encoding="utf-8"))
C = {k: tuple(int(v.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)) + (255,) for k, v in _raw.items() if isinstance(v, str)}
O = C["outline"]
CLEAR = (0, 0, 0, 0)

AREAS = [  # id, rect (grade 16, dentro das zonas do pen.json)
    ("cercado-adultos-ampliado", (48, 64, 384, 128)),
    ("cercadinho-filhotes", (496, 304, 208, 176)),
    ("patio-casais-ampliado", (496, 160, 208, 80)),
    ("jardim-lagoa", (48, 336, 192, 144)),
    ("patio-casais-nobre", (240, 336, 192, 144)),
    ("pomar", (304, 192, 128, 144)),
]


def px(im, x, y, c):
    if 0 <= x < im.width and 0 <= y < im.height:
        im.putpixel((x, y), c)


def rect(im, x, y, w, h, c):
    ImageDraw.Draw(im).rectangle([x, y, x + w - 1, y + h - 1], fill=c)


# ---------- camada de bloqueio ----------
def tall_grass(im, rng):
    w, h = im.size
    for y in range(h):
        for x in range(w):
            im.putpixel((x, y), C["bush"] if rng.random() < 0.2 else C["bush_dark"])
    for _ in range(w * h // 70):          # tufos de laminas
        x, y = rng.randrange(w), rng.randrange(h)
        n = rng.randint(2, 4)
        for i in range(n):
            bx = x + i * 2 - n
            ln = rng.randint(4, 8)
            for k in range(ln):
                col = C["bush"] if k < ln - 2 else rng.choice([C["x5"], C["grass_dark"], C["bush"]])
                px(im, bx, y - k, col)
                if k > ln - 3 and rng.random() < .5:
                    px(im, bx + rng.choice((-1, 1)), y - k, C["x5"])
    for _ in range(w * h // 600):          # flores murchas, so uma pitada
        px(im, rng.randrange(w), rng.randrange(h), C["x2"])


def board(im, x, y, w, h, rng):
    """tabua vertical de ponta cortada, contorno, madeira desbotada."""
    d = ImageDraw.Draw(im)
    d.rectangle([x, y, x + w - 1, y + h - 1], fill=C["x10"], outline=O)
    d.line([x + 1, y + 1, x + 1, y + h - 2], fill=C["wood"])
    d.line([x + w - 2, y + 2, x + w - 2, y + h - 2], fill=C["wood_dark"])
    px(im, x, y, CLEAR); px(im, x + w - 1, y, CLEAR)
    px(im, x + 1, y, O); px(im, x + w - 2, y, O)
    px(im, x + w // 2 - 1, y + 3, C["pebble"])
    px(im, x + w // 2 - 1, y + h - 4, C["pebble"])
    if rng.random() < .5:
        px(im, x + 2, y + h // 2, C["wood_dark"])


def tapume(im, rng):
    w, h = im.size
    y0 = h - 20
    x = 2
    while x + 8 <= w - 2:
        board(im, x, y0 + rng.randint(-2, 1), 8, 18, rng)
        x += 8
    d = ImageDraw.Draw(im)
    for ry in (y0 + 5, y0 + 13):
        d.rectangle([0, ry, w - 1, ry + 2], fill=C["wood_dark"], outline=O)
        d.line([1, ry + 1, w - 2, ry + 1], fill=C["wood"])
    for sx in (0, w - 8):                  # estacas nos cantos, mais altas
        board(im, sx, max(0, y0 - 14), 8, min(34, h - max(0, y0 - 14)), rng)
    for a, b in (((6, 8), (w - 8, y0 - 6)), ((w - 8, 8), (6, y0 - 6))):   # X de tabuas
        d.line([a[0], a[1] - 2, b[0], b[1] - 2], fill=O)
        d.line([a[0], a[1] + 2, b[0], b[1] + 2], fill=O)
        for off in (-1, 0, 1):
            d.line([a[0], a[1] + off, b[0], b[1] + off], fill=C["x10"])
        d.line([a[0], a[1] - 1, b[0], b[1] - 1], fill=C["wood"])


def ragged(im, rng):
    w, h = im.size

    def walk(n):
        v, out = 2, []
        for _ in range(n):
            v = max(0, min(5, v + rng.choice((-1, 0, 0, 1))))
            out.append(v)
        return out
    for edge in ("t", "l", "r"):            # base reta (tapume); topo e laterais irregulares
        n = w if edge == "t" else h
        prof = walk(n)
        for i in range(n):
            for k in range(prof[i]):
                if edge == "t": px(im, i, k, CLEAR)
                if edge == "l": px(im, k, i, CLEAR)
                if edge == "r": px(im, w - 1 - k, i, CLEAR)
    src = im.copy()
    for y in range(h):
        for x in range(w):
            if src.getpixel((x, y))[3] and any(
                    0 <= x + dx < w and 0 <= y + dy < h and src.getpixel((x + dx, y + dy))[3] == 0
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                im.putpixel((x, y), O)


def build_layer(r, seed):
    rng = random.Random(seed)
    im = Image.new("RGBA", (r[2], r[3]), CLEAR)
    tall_grass(im, rng)
    tapume(im, rng)
    ragged(im, rng)
    return im


# ---------- placas ----------
def build_sign(free: bool):
    im = Image.new("RGBA", (32, 32), CLEAR)
    d = ImageDraw.Draw(im)
    face, edge = (C["wood_light"], C["wood"]) if free else (C["x10"], C["wood_dark"])
    d.rectangle([14, 20, 17, 31], fill=C["wood_dark"], outline=O)
    d.line([15, 21, 15, 30], fill=C["wood"] if free else C["x10"])
    d.rectangle([1, 3, 30, 22], fill=face, outline=O)
    d.rectangle([2, 4, 29, 21], outline=edge)
    d.rectangle([4, 6, 27, 19], fill=C["cream"] if free else C["pebble"], outline=edge if free else C["x2"])
    for p in ((2, 4), (29, 4), (2, 21), (29, 21)):
        px(im, *p, C["cream_light"] if free else C["pebble"])
    if free:
        for x, y in ((0, 1), (31, 2), (30, 25), (1, 24)):   # brilho
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                px(im, x + dx, y + dy, C["yellow"])
            px(im, x, y, C["cream_light"])
        d.line([5, 7, 12, 7], fill=C["cream_light"])
    else:
        d.line([5, 7, 26, 7], fill=C["x2"])
    return im


# ---------- animacao ----------
FW = FH = 96
NF = 8


def rot_piece(w, h, ang, col_a, col_b):
    p = Image.new("RGBA", (w, h), O)
    ImageDraw.Draw(p).rectangle([1, 1, w - 2, h - 2], fill=col_a)
    ImageDraw.Draw(p).line([1, 1, 1, h - 2], fill=col_b)
    return p.rotate(ang, expand=True, resample=Image.NEAREST)


def build_anim():
    rng = random.Random(1303)
    sheet = Image.new("RGBA", (FW * NF, FH), CLEAR)
    cx, cy = FW // 2, FH // 2 + 8
    planks = [(-30, 8), (-14, -6), (2, 10), (18, -4), (34, 6)]
    clump = [(rng.randint(-26, 26), rng.randint(-26, 8)) for _ in range(26)]
    leaves = [(rng.uniform(0, 6.28), rng.uniform(10, 24),
               rng.choice([C["x5"], C["bush_light"], C["grass"], C["bush"]])) for _ in range(14)]
    dust = [(rng.uniform(0, 6.28), rng.uniform(14, 30)) for _ in range(9)]
    for f in range(NF):
        im = Image.new("RGBA", (FW, FH), CLEAR)
        shake = [1, -1, 2, -2][f] if f < 4 else 0
        for i, (dx, dy) in enumerate(clump):          # mato: balanca (0-2), depois se dispersa
            if f < 3:
                x, y = cx + dx + shake, cy + dy
            else:
                k = (f - 2) / 5
                x = cx + dx * (1 + 1.4 * k)
                y = cy + dy + 66 * k * k - 14 * k
            if f <= 5:
                col = [C["bush_dark"], C["bush"], C["x5"]][i % 3]
                rect(im, int(x), int(y), 3, 3, O)
                px(im, int(x) + 1, int(y) + 1, col); px(im, int(x) + 1, int(y), col)
        for dx, ph in planks:                          # tabuas: balancam, abrem e caem
            side = -1 if dx < 0 else 1
            if f < 3:
                x, y, ang = cx + dx + shake, cy - 6, shake * 2
            else:
                k = (f - 2) / 5
                x = cx + dx + side * 18 * k * (1 + abs(dx) / 30)
                y = cy - 6 + 40 * k * k - 8 * k
                ang = side * 80 * k + ph
            if f <= 6:
                p = rot_piece(6, 22, ang, C["x10"], C["wood"])
                im.alpha_composite(p, (int(x) - p.width // 2, int(y) - p.height // 2))
        if f >= 2:
            k = (f - 2) / 5
            for a, dist, col in leaves:               # folhas
                x = cx + math.cos(a) * dist * (1 + 2.2 * k)
                y = cy - 8 + math.sin(a) * dist * .6 * (1 + k) + 18 * k * k - 10 * k
                if f <= 6:
                    px(im, int(x), int(y), O); px(im, int(x) + 1, int(y), col)
                    px(im, int(x) + 1, int(y) - 1, col); px(im, int(x), int(y) + 1, col)
            for n, (a, dist) in enumerate(dust):      # poeira em dither (alpha 0/255)
                x = cx + math.cos(a) * dist * (.5 + 1.3 * k)
                y = cy + 8 + math.sin(a) * dist * .35 * (.6 + k) - 6 * k
                r = int(3 + 6 * k)
                col = C["path_light"] if f < 5 else C["path"]
                if f == 7 and n % 2:
                    continue
                for yy in range(-r, r + 1):
                    for xx in range(-r, r + 1):
                        if xx * xx + yy * yy <= r * r and ((xx + yy) % 2 == 0 or f < 4):
                            if f >= 6 and (xx * 7 + yy * 3) % 3:
                                continue
                            px(im, int(x) + xx, int(y) + yy, col)
        sheet.paste(im, (f * FW, 0))
    return sheet


# ---------- icones 16x16 ----------
def icon():
    return Image.new("RGBA", (16, 16), CLEAR)


def ic_coin():
    im = icon(); d = ImageDraw.Draw(im)
    d.ellipse([2, 2, 13, 13], fill=C["yellow"], outline=O)
    d.ellipse([4, 4, 11, 11], outline=C["cream_dark"])
    d.line([7, 6, 7, 9], fill=C["cream_dark"]); d.line([8, 6, 8, 9], fill=C["cream_dark"])
    for p in ((4, 5), (5, 4)):
        px(im, *p, C["cream_light"])
    return im


def star_pts(cx, cy, R, r, n=5):
    return [(cx + (R if i % 2 == 0 else r) * math.sin(math.pi * i / n),
             cy - (R if i % 2 == 0 else r) * math.cos(math.pi * i / n)) for i in range(2 * n)]


def ic_prestige():
    im = icon(); d = ImageDraw.Draw(im)
    d.polygon(star_pts(7.5, 8.5, 7.3, 3.2), fill=O)
    d.polygon(star_pts(7.5, 8.5, 5.6, 2.4), fill=C["rose"])
    d.polygon(star_pts(7.5, 8.2, 3.4, 1.4), fill=C["rose_light"])
    px(im, 7, 7, C["cream_light"]); px(im, 7, 8, C["cream_light"])
    return im


def ic_lock():
    im = icon(); d = ImageDraw.Draw(im)
    d.arc([4, 1, 11, 9], 180, 360, fill=O); d.line([4, 5, 4, 8], fill=O); d.line([11, 5, 11, 8], fill=O)
    d.line([5, 2, 10, 2], fill=C["stone"]); d.line([5, 3, 5, 8], fill=C["stone"]); d.line([10, 3, 10, 8], fill=C["stone"])
    d.rectangle([2, 7, 13, 14], fill=C["yellow"], outline=O)
    d.line([3, 8, 12, 8], fill=C["cream_light"]); d.line([3, 13, 12, 13], fill=C["dirt"])
    d.rectangle([7, 9, 8, 11], fill=O)
    return im


def ic_ration(emblem):
    im = icon(); d = ImageDraw.Draw(im)
    body = {"fofa": C["rose"], "veloz": C["teal"], "escolha": C["wood_light"]}[emblem]
    shade = {"fofa": C["rose_dark"], "veloz": C["teal_dark"], "escolha": C["wood"]}[emblem]
    d.rectangle([3, 3, 12, 14], fill=body, outline=O)
    d.line([4, 13, 11, 13], fill=shade); d.line([11, 4, 11, 12], fill=shade)
    d.rectangle([3, 1, 12, 3], fill=C["cream"], outline=O)
    d.line([4, 2, 11, 2], fill=C["cream_light"])
    ex, ey = 7, 8
    shapes = {
        "fofa": ([(-2, -1), (-1, -1), (1, -1), (2, -1), (-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0),
                  (-1, 1), (0, 1), (1, 1), (0, 2)], C["cream_light"]),
        "veloz": ([(1, -2), (1, -1), (0, -1), (-1, 0), (0, 0), (1, 0), (0, 1), (-1, 2)], C["yellow"]),
        "escolha": ([(0, -2), (0, -1), (-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0), (-1, 1), (1, 1), (-1, 2), (1, 2)],
                    C["cream_light"]),
    }
    pts, col = shapes[emblem]
    for p in pts:
        px(im, ex + p[0], ey + p[1], col)
    return im


def ic_vase():
    im = icon(); d = ImageDraw.Draw(im)
    d.polygon([(5, 6), (10, 6), (12, 10), (11, 14), (4, 14), (3, 10)], fill=C["wood_light"], outline=O)
    d.rectangle([5, 4, 10, 5], fill=C["wood"], outline=O)
    d.line([5, 11, 10, 11], fill=C["rose"]); d.line([4, 9, 11, 9], fill=C["wood"])
    px(im, 5, 8, C["cream_light"])
    for x in (5, 7, 9):
        px(im, x, 3, C["bush"]); px(im, x, 2, C["bush_light"])
    for x, y, c in ((7, 1, C["flower_red"]), (4, 1, C["flower_pink"]), (10, 1, C["yellow"])):
        px(im, x, y, c); px(im, x, y - 1, c)
    return im


def ic_brush():
    im = icon(); d = ImageDraw.Draw(im)
    d.line([12, 1, 6, 8], fill=O, width=3)
    d.line([12, 1, 6, 8], fill=C["wood_light"], width=1)
    d.polygon([(6, 7), (8, 9), (5, 13), (2, 14), (3, 11)], fill=C["rose"], outline=O)
    px(im, 4, 12, C["rose_light"]); px(im, 3, 13, C["rose_dark"])
    return im


def build_icons():
    icons = {"moeda": ic_coin(), "prestigio": ic_prestige(), "cadeado": ic_lock(), "racao_fofa": ic_ration("fofa"),
             "racao_veloz": ic_ration("veloz"), "racao_escolha": ic_ration("escolha"),
             "decoracao_vaso": ic_vase(), "decoracao_pincel": ic_brush()}
    (OUT / "icons").mkdir(exist_ok=True)
    sheet = Image.new("RGBA", (16 * len(icons), 16), CLEAR)
    meta = {}
    for i, (k, im) in enumerate(icons.items()):
        im.save(OUT / "icons" / f"{k}.png")
        sheet.paste(im, (i * 16, 0))
        meta[k] = {"x": i * 16, "y": 0, "w": 16, "h": 16}
    sheet.save(OUT / "icons.png")
    (OUT / "icons.json").write_text(json.dumps({"image": "icons.png", "size": list(sheet.size), "sprites": meta}, indent=2),
                                    encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    areas = []
    for i, (aid, r) in enumerate(AREAS):
        build_layer(r, 1300 + i).save(OUT / f"bloqueio_{aid}.png")
        areas.append({"id": aid, "file": f"bloqueio_{aid}.png", "rect": list(r),
                      "anchor_sign": [r[0] + r[2] // 2, r[1] + r[3] // 2 + 16]})
    build_sign(True).save(OUT / "placa_livre.png")
    build_sign(False).save(OUT / "placa_bloqueada.png")
    build_anim().save(OUT / "unlock_anim.png")
    (OUT / "unlock_anim.json").write_text(json.dumps({
        "image": "unlock_anim.png", "frame_size": [FW, FH], "frames": NF, "fps": 20, "duration_ms": NF * 1000 // 20,
        "loop": False, "origin": "centro do quadro",
        "note": "1 explosao por 96x96; ladrilhar sobre a area em passos de 96 e desvanecer a camada em sincronia"},
        indent=2), encoding="utf-8")
    (OUT / "areas.json").write_text(json.dumps({
        "grid": 16, "sign": {"free": "placa_livre.png", "locked": "placa_bloqueada.png", "size": [32, 32],
                             "anchor": "centro-base [16,32]", "text_rect": [4, 6, 24, 14]},
        "areas": areas}, indent=2, ensure_ascii=False), encoding="utf-8")
    build_icons()


if __name__ == "__main__":
    main()
