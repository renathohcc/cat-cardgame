"""T9.4: objetos do quintal (objects.png/json) e ambiente (ambient.png/json). Pillow, sem IA.
Quadro uniforme 128x96, ancora (64,86) = centro-base. Uso: python assets/tools/build_t94_objects.py
"""
import json
import math
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
import build_t92_objects as old  # noqa: E402  (novelo e ratinho mantidos)
from build_t94_layout import LAYER  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PEN = os.path.join(ROOT, "assets", "pen")
W, H, CX, BY = 128, 96, 64, 86


def h(c, a=255):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) + (a,)


OUT = h("#3b2a38")
SH = h("#2a2030", 85)
WOOD = [h(x) for x in ("#4e2f22", "#7a4c2e", "#9a6638", "#bc8650", "#d6a468")]
D = [None]


def E(cx, cy, rx, ry, fill, out=None):
    d = D[0]
    if out:
        d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=out)
        rx, ry = rx - 1, ry - 1
    d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=fill)


def shadow(cx, rx, ry=5, cy=BY - 2):
    D[0].ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=SH)


def R(x0, y0, x1, y1, fill, out=None):
    d = D[0]
    if out:
        d.rectangle((x0 - 1, y0 - 1, x1 + 1, y1 + 1), fill=out)
    d.rectangle((x0, y0, x1, y1), fill=fill)


def heart(x, y, col, s=1):
    d = D[0]
    pts = [(-2, -1), (-1, -2), (0, -1), (1, -2), (2, -1), (2, 0), (1, 1), (0, 2), (-1, 1), (-2, 0)]
    d.polygon([(x + px * s, y + py * s) for px, py in pts], fill=col)


def sn(t, k=1, ph=0.0):
    return math.sin(2 * math.pi * (t * k + ph))


# --------------------------------------------------------------- camas (press: 0 normal .. 1 amassada)
def cama_almofada(p):
    cy = BY - 15 + round(p * 1.2)
    rx, ry = 33 + round(p * 2), 14 - round(p * 2.5)
    shadow(CX, 37, 6)
    E(CX, cy + 2, rx, ry, h("#8a3a52"), OUT)
    E(CX, cy, rx - 2, ry - 2, h("#b04e6c"))
    E(CX - 4, cy - 2, rx - 10, ry - 6, h("#cc6c88"))
    E(CX - 9, cy - 4, 9, 2, h("#e69ab0"))
    if p > 0:
        k = min(p, 1.0)
        E(CX, cy + 1, round(rx * .62 * (.5 + .5 * k)), round(ry * .55 * (.5 + .5 * k)), h("#8f3f58"))
        E(CX, cy + 1, round(rx * .5 * (.5 + .5 * k)), round(ry * .4 * (.5 + .5 * k)), h("#a24862"))
    for sx in (-1, 1):
        R(CX + sx * (rx - 2) - 2, cy + 3, CX + sx * (rx - 2) + 1, cy + 7, h("#e8c46a"), OUT)
    D[0].rectangle((CX - 1, cy - 1, CX + 1, cy + 1), fill=h("#5c2338"))


def cama_cesto(p):
    cy = BY - 19
    k = max(p, 0)
    shadow(CX, 37, 6)
    E(CX, cy + 7, 33, 14, h("#6b4a31"), OUT)
    for i in range(-27, 28, 6):
        D[0].line((CX + i, cy + 11, CX + i, cy + 19), fill=h("#4a3022"))
    E(CX, cy + 1, 35, 15 - round(p * .5), h("#9a7048"), OUT)
    E(CX, cy + 1, 31, 12, h("#6b4a31"))
    E(CX, cy + 3, 28, 10 - round(k * 1.5), h("#e0c4a6"), h("#5a3d28"))
    E(CX - 3, cy + 1, 20, 6 - round(k * 1.5), h("#f0d8bc"))
    if p > 0:
        E(CX, cy + 4, round(18 * (.5 + .5 * k)), round(6 * (.5 + .5 * k)), h("#cfae8c"))
    for i in range(-30, 31, 5):
        D[0].point((CX + i, cy - 13 + abs(i) // 8 + (i // 5) % 2), fill=h("#c09a62"))


def cama_pedra(p):
    cy = BY - 15
    k = max(p, 0)
    shadow(CX, 37, 6)
    E(CX, cy + 6, 34, 14, h("#4e5878"), OUT)
    E(CX, cy + 2, 34, 14, h("#7a88aa"), OUT)
    E(CX - 2, cy, 28, 10, h("#93a0c0"))
    E(CX - 8, cy - 3, 14, 3, h("#b3bfd8"))
    for px, py in ((12, 5), (-18, 3), (20, -4), (-6, 8)):
        D[0].point((CX + px, cy + py), fill=h("#68759a"))
    # manta verde-agua dobrada sobre a pedra
    E(CX, cy + 2 + round(k), 23 + round(k * 2), 9 - round(k * 2), h("#3e8a82"), OUT)
    E(CX - 2, cy + 1 + round(k), 19, 6 - round(k * 1.5), h("#58aaa0"))
    if p > 0:
        E(CX, cy + 2, round(11 * (.5 + .5 * k)), round(4 * (.5 + .5 * k)), h("#3e8a82"))
    D[0].line((CX - 14, cy + 6, CX + 14, cy + 6), fill=h("#2f6a64"))


def cama_casal(p):
    cy = BY - 18
    k = max(p, 0)
    shadow(CX, 46, 7)
    # almofada de apoio atras
    E(CX, cy - 6, 40, 13, h("#c88aa0"), OUT)
    E(CX, cy - 7, 36, 10, h("#e0a8bc"))
    # tapete / cama redonda
    E(CX, cy + 4, 44, 17, h("#8a3a52"), OUT)
    E(CX, cy + 2, 41, 15 - round(p * 1.5), h("#f2d8c0"))
    E(CX, cy + 2, 37, 12 - round(p * 1.5), h("#d86a8a"))
    E(CX - 3, cy, 31, 8 - round(p), h("#ee8aa6"))
    if p > 0:
        E(CX, cy + 3, round(28 * (.55 + .45 * k)), round(8 * (.55 + .45 * k)), h("#c85c7c"))
    heart(CX, cy + 2 + round(k), h("#fff0f4"), 2)
    heart(CX, cy + 2 + round(k), h("#e04a72"), 1)


def viveiro_cesto(p):
    cy = BY - 17
    k = max(p, 0)
    shadow(CX, 42, 6)
    E(CX, cy + 7, 38, 14, h("#7a5538"), OUT)
    for i in range(-30, 31, 6):
        D[0].line((CX + i, cy + 11, CX + i, cy + 19), fill=h("#4a3022"))
    E(CX, cy + 1, 40, 15, h("#a67c52"), OUT)
    E(CX, cy + 2, 35, 12, h("#e8b8c8"), h("#7a4a5c"))
    E(CX - 3, cy, 28, 7 - round(k), h("#f6d4de"))
    if p > 0:
        E(CX, cy + 3, round(26 * (.5 + .5 * k)), round(7 * (.5 + .5 * k)), h("#dca0b4"))
    heart(CX, cy + 2, h("#e04a72"), 1)
    for i in range(-36, 37, 5):
        D[0].point((CX + i, cy - 14 + abs(i) // 10 + (i // 5) % 2), fill=h("#c9a070"))


BEDS = {"cama_almofada": cama_almofada, "cama_cesto": cama_cesto, "cama_pedra": cama_pedra,
        "cama_casal": cama_casal, "viveiro_cesto": viveiro_cesto}
ENTER = [0.45, 0.95, 1.0, 0.85]
EXIT = [0.35, -0.2, 0.1, 0.0]


# --------------------------------------------------------------- brinquedos e mobilia
def arranhador(t, use):
    ox = [0, 1, -1, 1, -1, 0][int(t * 6) % 6] if use else 0
    shadow(CX, 26, 5)
    R(CX - 22, BY - 11, CX + 22, BY - 3, WOOD[2], OUT)
    R(CX - 22, BY - 11, CX + 22, BY - 9, WOOD[3])
    R(CX - 22, BY - 5, CX + 22, BY - 3, WOOD[1])
    top = BY - 56
    R(CX - 9 + ox, top, CX + 9 + ox, BY - 12, h("#d8b878"), OUT)
    for i, y in enumerate(range(top + 2, BY - 12, 4)):
        D[0].line((CX - 9 + ox, y + (i % 2), CX + 9 + ox, y + 1 - (i % 2)), fill=h("#a8844c"))
        D[0].line((CX - 9 + ox, y + 2 - (i % 2), CX - 5 + ox, y + 2 - (i % 2)), fill=h("#ecd49a"))
    R(CX + 6 + ox, top, CX + 9 + ox, BY - 12, h("#b08c52"))
    E(CX + ox, top - 1, 12, 4, WOOD[3], OUT)
    E(CX - 2 + ox, top - 2, 7, 2, WOOD[4])
    if use:
        n = int(t * 6) % 6
        for j in range(3):
            px = CX + 12 + j * 4 + n * 2
            py = BY - 34 - j * 3 + (n * 2 if n > 2 else 0)
            D[0].point((px, py), fill=h("#ecd49a"))
            D[0].point((px + 1, py), fill=h("#c0a068"))


def casinha(t, use):
    d = D[0]
    shadow(CX - 4, 56, 7)
    # pernas
    for lx in (32, 84):
        R(lx, 80, lx + 5, BY, WOOD[0], OUT)
    # rampa
    d.polygon([(92, 70), (92, 80), (121, BY), (121, BY - 8)], fill=OUT)
    d.polygon([(93, 72), (93, 79), (119, BY - 1), (119, BY - 7)], fill=WOOD[2])
    for i in range(4):
        x = 97 + i * 6
        d.line((x, 74 + i * 3, x, 80 + i * 3), fill=WOOD[1])
    # corpo
    R(28, 46, 91, 80, WOOD[2], OUT)
    for x in range(32, 91, 6):
        d.line((x, 47, x, 79), fill=WOOD[1])
        d.line((x + 1, 47, x + 1, 79), fill=WOOD[3])
    d.line((28, 79, 91, 79), fill=WOOD[1])
    # porta em arco
    d.rectangle((44, 56, 71, 80), fill=OUT)
    d.pieslice((44, 48, 71, 66), 180, 360, fill=OUT)
    d.rectangle((46, 58, 69, 80), fill=h("#2a1c22"))
    d.pieslice((46, 50, 69, 66), 180, 360, fill=h("#2a1c22"))
    d.rectangle((47, 72, 68, 79), fill=h("#c88aa0"))
    d.rectangle((47, 72, 68, 73), fill=h("#e0a8bc"))
    # lanterna na parede
    R(78, 56, 82, 62, h("#f4d46a"), OUT)
    D[0].point((79, 57), fill=h("#fff6c8"))
    # telhado (superficie superior + borda frontal)
    d.polygon([(24, 47), (96, 47), (88, 26), (32, 26)], fill=OUT)
    d.polygon([(26, 46), (94, 46), (87, 28), (33, 28)], fill=WOOD[3])
    for y in (33, 39):
        xo = (46 - y) * 0.36
        d.line((33 - (y - 28) * 0.0 + (y - 28) * -0.35, y, 87 + (y - 28) * 0.35, y), fill=WOOD[2])
    d.line((34, 29, 86, 29), fill=WOOD[4])
    R(24, 46, 96, 50, WOOD[1], OUT)
    d.line((25, 47, 95, 47), fill=WOOD[3])


def banco_arvore(t, use):
    d = D[0]
    shadow(CX, 44, 6)
    for lx in (CX - 36, CX + 29):
        R(lx, BY - 14, lx + 6, BY - 1, WOOD[1], OUT)
        R(lx, BY - 14, lx + 2, BY - 1, WOOD[2])
    R(CX - 40, BY - 21, CX + 40, BY - 14, WOOD[1], OUT)       # frente do assento
    R(CX - 40, BY - 21, CX + 40, BY - 20, WOOD[2])
    d.polygon([(CX - 42, BY - 21), (CX + 42, BY - 21), (CX + 38, BY - 38), (CX - 38, BY - 38)], fill=OUT)
    d.polygon([(CX - 40, BY - 22), (CX + 40, BY - 22), (CX + 36, BY - 37), (CX - 36, BY - 37)], fill=WOOD[3])
    for y in (-27, -32):
        d.line((CX - 39 + (y + 22) * -.2, BY + y, CX + 39 - (y + 22) * -.2, BY + y), fill=WOOD[2])
    d.line((CX - 36, BY - 37, CX + 36, BY - 37), fill=WOOD[4])
    for x in (-18, 6, 24):
        d.point((CX + x, BY - 30), fill=WOOD[1])


def tunel_filhote(t, use):
    base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    saved = D[0]
    D[0] = ImageDraw.Draw(base)
    d = D[0]
    shadow(CX + 2, 48, 7)
    # corpo
    d.rectangle((CX - 38, BY - 34, CX + 34, BY - 4), fill=OUT)
    d.ellipse((CX + 22, BY - 34, CX + 46, BY - 4), fill=OUT)
    d.rectangle((CX - 37, BY - 33, CX + 34, BY - 5), fill=h("#4a78c8"))
    d.ellipse((CX + 23, BY - 33, CX + 45, BY - 5), fill=h("#3a62ac"))
    d.rectangle((CX - 37, BY - 33, CX + 34, BY - 27), fill=h("#7aa4e8"))
    d.rectangle((CX - 37, BY - 12, CX + 34, BY - 5), fill=h("#3a62ac"))
    for x in range(CX - 28, CX + 34, 12):
        d.rectangle((x, BY - 33, x + 3, BY - 5), fill=h("#e8f0ff"))
        d.rectangle((x + 3, BY - 33, x + 3, BY - 5), fill=h("#b0c4ec"))
    # boca de entrada (esquerda)
    d.ellipse((CX - 50, BY - 34, CX - 26, BY - 4), fill=OUT)
    d.ellipse((CX - 49, BY - 33, CX - 27, BY - 5), fill=h("#7aa4e8"))
    d.ellipse((CX - 46, BY - 30, CX - 29, BY - 8), fill=h("#241c34"))
    d.ellipse((CX - 44, BY - 26, CX - 32, BY - 12), fill=h("#14101c"))
    D[0] = saved
    return base


def tigela(t, use):
    shadow(CX, 17, 4, BY - 1)
    E(CX, BY - 6, 14, 7, h("#4a78c8"), OUT)
    E(CX, BY - 8, 12, 5, h("#7aa4e8"))
    E(CX, BY - 8, 9, 3, h("#5aaedc"))
    D[0].line((CX - 5, BY - 9, CX - 1, BY - 9), fill=h("#c8ecff"))
    R(CX - 6, BY - 3, CX + 6, BY - 1, h("#3a62ac"))


def tigela_racao(t, use):
    shadow(CX, 17, 4, BY - 1)
    E(CX, BY - 6, 14, 7, h("#c0485a"), OUT)
    E(CX, BY - 8, 12, 5, h("#e0788a"))
    E(CX, BY - 9, 9, 3, h("#8a5a38"))
    for px, py in ((-5, -10), (-1, -11), (3, -10), (6, -9), (-3, -8), (1, -8)):
        D[0].point((CX + px, BY + py), fill=h("#b88458"))
        D[0].point((CX + px + 1, BY + py), fill=h("#6a4228"))
    R(CX - 6, BY - 3, CX + 6, BY - 1, h("#90303f"))


def casinha_filhote(t, use):
    d = D[0]
    shadow(CX, 34, 6)
    R(CX - 24, BY - 28, CX + 24, BY - 1, WOOD[2], OUT)
    for x in range(CX - 22, CX + 24, 5):
        d.line((x, BY - 27, x, BY - 2), fill=WOOD[1])
    d.polygon([(CX - 32, BY - 26), (CX + 32, BY - 26), (CX, BY - 54)], fill=OUT)
    d.polygon([(CX - 29, BY - 27), (CX + 29, BY - 27), (CX, BY - 51)], fill=h("#c0584a"))
    for i, y in enumerate(range(BY - 31, BY - 50, -5)):
        w = (y - (BY - 54)) * 1.0
        d.line((CX - w, y, CX + w, y), fill=h("#9a3e38"))
    d.line((CX - 20, BY - 36, CX - 2, BY - 49), fill=h("#e0786a"))
    d.rectangle((CX - 9, BY - 20, CX + 9, BY - 1), fill=OUT)
    d.pieslice((CX - 9, BY - 28, CX + 9, BY - 12), 180, 360, fill=OUT)
    d.rectangle((CX - 7, BY - 18, CX + 7, BY - 1), fill=h("#2a1c22"))
    d.pieslice((CX - 7, BY - 26, CX + 7, BY - 12), 180, 360, fill=h("#2a1c22"))
    d.rectangle((CX - 7, BY - 5, CX + 7, BY - 1), fill=h("#a0b8e8"))
    R(CX + 12, BY - 16, CX + 19, BY - 10, h("#f4d46a"), OUT)
    d.line((CX + 15, BY - 16, CX + 15, BY - 10), fill=WOOD[1])


def bola_filhote(t, use):
    r = 8
    if use:
        ph = (t * 1.0) % 1.0
        up = round(abs(math.sin(math.pi * ph)) * 22)
        sq = 3 if up < 2 else 0
        cy = BY - r - 1 - up + sq // 2
        rx, ry = r + sq, r - sq
        shadow(CX, max(5, 11 - up // 3), 3, BY - 1)
    else:
        cy, rx, ry = BY - r - 1, r, r
        shadow(CX, 11, 3, BY - 1)
    E(CX, cy, rx, ry, h("#e0546a"), OUT)
    E(CX - 1, cy - 1, rx - 3, ry - 3, h("#f27a8a"))
    D[0].line((CX - rx + 2, cy, CX + rx - 2, cy), fill=h("#fff0f4"))
    D[0].point((CX - 3, cy - ry + 2), fill=h("#ffffff"))


def render(fn, t, use):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    D[0] = ImageDraw.Draw(im)
    r = fn(t, use)
    if isinstance(r, Image.Image):
        return r
    return im


def render_old(fn_old, t, use):
    old_im = old.frame(fn_old, t, use)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    im.alpha_composite(old_im, (16, 26))
    return im


def render_bed(bed, p):
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    D[0] = ImageDraw.Draw(im)
    bed(p)
    return im


def tunnel_frame(t, use):
    im = tunel_filhote(0, False)
    if not use:
        return im
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    src = im.load()
    dst = out.load()
    for x in range(W):
        u = (x - (CX - 50)) / 96.0
        amp = max(0.0, math.sin(2 * math.pi * (u - t))) ** 2
        dy = -round(amp * 4)
        for y in range(H):
            p = src[x, y]
            if p[3]:
                ny = y + dy
                if 0 <= ny < H:
                    dst[x, ny] = p
    return out


STATIC = {"arranhador": arranhador, "casinha": casinha, "banco_arvore": banco_arvore, "tigela": tigela,
          "tigela_racao": tigela_racao, "casinha_filhote": casinha_filhote, "bola_filhote": bola_filhote}


def build_objects():
    kinds = {}
    for name, bed in BEDS.items():
        kinds[name] = [("idle", 1, 1, True, lambda i, b=bed: render_bed(b, 0.0)),
                       ("enter", 4, 8, False, lambda i, b=bed: render_bed(b, ENTER[i])),
                       ("exit", 4, 8, False, lambda i, b=bed: render_bed(b, EXIT[i]))]
    kinds["novelo"] = [("idle", 6, 6, True, lambda i: render_old(old.novelo, i / 6, False)),
                       ("use", 8, 8, True, lambda i: render_old(old.novelo, i / 8, True))]
    kinds["ratinho"] = [("idle", 6, 6, True, lambda i: render_old(old.ratinho, i / 6, False)),
                        ("use", 8, 8, True, lambda i: render_old(old.ratinho, i / 8, True))]
    kinds["arranhador"] = [("idle", 1, 1, True, lambda i: render(arranhador, 0, False)),
                           ("use", 6, 10, True, lambda i: render(arranhador, i / 6, True))]
    kinds["bola_filhote"] = [("idle", 1, 1, True, lambda i: render(bola_filhote, 0, False)),
                             ("use", 8, 10, True, lambda i: render(bola_filhote, i / 8, True))]
    kinds["tunel_filhote"] = [("idle", 1, 1, True, lambda i: tunnel_frame(0, False)),
                              ("use", 6, 8, True, lambda i: tunnel_frame(i / 6, True))]
    for name in ("casinha", "banco_arvore", "tigela", "tigela_racao", "casinha_filhote"):
        fn = STATIC[name]
        kinds[name] = [("idle", 1, 1, True, lambda i, f=fn: render(f, 0, False))]
    order = ["cama_almofada", "cama_cesto", "cama_pedra", "cama_casal", "viveiro_cesto", "banco_arvore", "casinha",
             "novelo", "ratinho", "arranhador", "bola_filhote", "tunel_filhote", "tigela", "tigela_racao", "casinha_filhote"]
    nrows = sum(len(kinds[k]) for k in order)
    sheet = Image.new("RGBA", (8 * W, nrows * H), (0, 0, 0, 0))
    meta = {}
    r = 0
    for name in order:
        anims = {}
        for an, n, fps, loop, fn in kinds[name]:
            for i in range(n):
                sheet.paste(fn(i), (i * W, r * H))
            anims[an] = {"row": r, "frames": n, "fps": fps, "loop": loop}
            r += 1
        meta[name] = {"frame": [W, H], "anchor": [CX, BY], "layer": LAYER[name], "anims": anims}
    sheet.save(os.path.join(PEN, "objects.png"))
    with open(os.path.join(PEN, "objects.json"), "w") as f:
        json.dump({"image": "objects.png", "size": list(sheet.size), "objects": meta}, f, indent=1)


# ------------------------------------------------------------------ ambiente (96x64, ancora 48,60)
AW, AH, ACX, ABY = 96, 64, 48, 60


def amb(fn, t):
    im = Image.new("RGBA", (AW, AH), (0, 0, 0, 0))
    D[0] = ImageDraw.Draw(im)
    fn(t)
    return im


def a_lagoa(t):
    d = D[0]
    # cobre a agua da lagoa (centro do quadro = centro da agua em (48,34)); so ondas claras e brilhos
    cx, cy = 48, 34
    for k in range(3):
        ph = (t + k / 3) % 1.0
        rx, ry = int(6 + ph * 30), int(2 + ph * 13)
        a = int(180 * (1 - ph))
        d.ellipse((cx - 14 - rx // 2, cy - 2 - ry // 2, cx - 14 + rx // 2, cy - 2 + ry // 2), outline=h("#d8f0ff", a))
    for i, (x, y) in enumerate(((30, 24), (58, 38), (40, 44), (62, 26), (24, 36))):
        if int(t * 8 + i * 2) % 8 in (0, 1):
            d.point((x, y), fill=h("#ffffff"))
            d.point((x + 1, y), fill=h("#d8f0ff"))
            d.point((x - 1, y), fill=h("#d8f0ff"))
    # vitoria-regia balancando
    ox = round(sn(t))
    d.ellipse((cx + 12 + ox, cy + 1, cx + 24 + ox, cy + 7), fill=h("#243628"))
    d.ellipse((cx + 13 + ox, cy + 2, cx + 23 + ox, cy + 6), fill=h("#6aa850"))
    d.line((cx + 18 + ox, cy + 4, cx + 23 + ox, cy + 3), fill=h("#4f95c4"))
    d.point((cx + 17 + ox, cy + 2), fill=h("#f4a0b4"))


def a_borboleta(t):
    d = D[0]
    for k, col in enumerate((("#f4a0b4", "#fff0f4"), ("#f2d460", "#fff6c8"))):
        ph = t + k * 0.5
        x = 48 + 30 * math.sin(2 * math.pi * ph) * (1 if k == 0 else -1)
        y = 30 + 12 * math.sin(2 * math.pi * ph * 2 + k) - 6 * k
        flap = int(t * 16 + k) % 2
        w = 3 if flap else 1
        d.ellipse((x - w - 1, y - 3, x - 1, y + 1), fill=h(col[0]), outline=OUT if w == 3 else None)
        d.ellipse((x + 1, y - 3, x + w + 1, y + 1), fill=h(col[0]), outline=OUT if w == 3 else None)
        d.point((x, y - 1), fill=OUT)
        d.point((x, y), fill=OUT)
        d.point((x - 1, y - 2), fill=h(col[1]))


def a_vagalumes(t):
    d = D[0]
    for k in range(6):
        ph = t + k / 6
        x = 48 + 34 * math.sin(2 * math.pi * (ph + k * 0.17)) * (0.6 + 0.4 * (k % 2))
        y = 30 + 20 * math.sin(2 * math.pi * (ph * 2 + k * 0.3))
        g = 0.5 + 0.5 * math.sin(2 * math.pi * (t * 2 + k * 0.37))
        a = int(70 + 130 * g)
        d.ellipse((x - 3, y - 3, x + 3, y + 3), fill=h("#f4f08a", int(a * .25)))
        d.point((x, y), fill=h("#fffbc8", min(255, a + 60)))
        d.point((x + 1, y), fill=h("#f4f08a", a))


def a_folhas(t):
    d = D[0]
    for k in range(2):
        f = (int(t * 8) + k * 4) % 8
        if f == 7:
            continue
        y = 4 + f * 7
        x = 48 + round(8 * math.sin(2 * math.pi * (f / 8 + k * 0.5))) + (k * 14 - 7)
        c1, c2 = (h("#d98f4e"), h("#b86a3a")) if k == 0 else (h("#8ec462"), h("#4a8a44"))
        if f % 2:
            d.rectangle((x, y, x + 2, y + 1), fill=c1)
            d.point((x + 1, y + 2), fill=c2)
        else:
            d.rectangle((x, y, x + 1, y + 2), fill=c1)
            d.point((x + 2, y + 1), fill=c2)


def a_lanterna(t, on=False):
    d = D[0]
    cx = ACX
    d.ellipse((cx - 8, ABY - 4, cx + 8, ABY), fill=SH)
    R(cx - 2, ABY - 36, cx + 2, ABY - 2, WOOD[2], OUT)
    R(cx - 2, ABY - 36, cx - 1, ABY - 2, WOOD[3])
    R(cx - 4, ABY - 6, cx + 4, ABY - 2, WOOD[1], OUT)
    # gancho + lanterna
    d.line((cx + 2, ABY - 34, cx + 7, ABY - 34), fill=OUT)
    d.line((cx + 7, ABY - 34, cx + 7, ABY - 31), fill=OUT)
    fl = 0
    if on:
        fl = [0, 1, 0, -1][int(t * 4) % 4]
    R(cx + 3, ABY - 31, cx + 11, ABY - 21, h("#fff2b0") if on else h("#9aa6a0"), OUT)
    if on:
        R(cx + 5, ABY - 29, cx + 9, ABY - 23, h("#ffd24a"))
        d.point((cx + 7, ABY - 27 + fl), fill=h("#ffffff"))
        d.point((cx + 7, ABY - 25), fill=h("#ffb030"))
    else:
        R(cx + 5, ABY - 29, cx + 9, ABY - 23, h("#b8c4bc"))
        d.point((cx + 6, ABY - 28), fill=h("#e8f0ec"))
    d.rectangle((cx + 3, ABY - 33, cx + 11, ABY - 32), fill=OUT)
    d.polygon([(cx + 2, ABY - 32), (cx + 12, ABY - 32), (cx + 7, ABY - 38)], fill=OUT)
    d.polygon([(cx + 4, ABY - 33), (cx + 10, ABY - 33), (cx + 7, ABY - 36)], fill=WOOD[1])


AMB = {"lagoa": [("idle", 8, 6, True, a_lagoa)], "borboleta": [("idle", 8, 8, True, a_borboleta)],
       "vagalumes": [("idle", 8, 6, True, a_vagalumes)], "folhas": [("idle", 8, 6, True, a_folhas)],
       "lanterna": [("off", 1, 1, True, lambda t: a_lanterna(t, False)), ("on", 4, 6, True, lambda t: a_lanterna(t, True))]}


def build_ambient():
    nrows = sum(len(v) for v in AMB.values())
    sheet = Image.new("RGBA", (8 * AW, nrows * AH), (0, 0, 0, 0))
    meta = {}
    r = 0
    for name, anims_l in AMB.items():
        anims = {}
        for an, n, fps, loop, fn in anims_l:
            for i in range(n):
                sheet.paste(amb(fn, i / n), (i * AW, r * AH))
            anims[an] = {"row": r, "frames": n, "fps": fps, "loop": loop}
            r += 1
        meta[name] = {"frame": [AW, AH], "anchor": [ACX, ABY], "anims": anims}
    sheet.save(os.path.join(PEN, "ambient.png"))
    with open(os.path.join(PEN, "ambient.json"), "w") as f:
        json.dump({"image": "ambient.png", "size": list(sheet.size), "objects": meta, "ambient": meta}, f, indent=1)


if __name__ == "__main__":
    build_objects()
    build_ambient()
    print("ok")
