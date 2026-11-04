"""T9.2: objetos interativos animados (objects.png/json) e ambiente (ambient.png/json). Pillow, sem IA.
Uso: python assets/tools/build_t92_objects.py
"""
import json
import math
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
from build_t92_layout import LAYER  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PEN = os.path.join(ROOT, "assets", "pen")


def h(c, a=255):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) + (a,)


OUT = h("#3b2a38")
SH = h("#0a0f1c", 110)
W, H, CX, BY = 96, 64, 48, 60
D = [None]


def E(d, cx, cy, rx, ry, fill, out=None):
    if out:
        d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=out)
        rx, ry = rx - 1, ry - 1
    d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=fill)


def shadow(d, cx, rx, ry=4, cy=BY - 1):
    d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=SH)


def sn(t, k=1, ph=0.0):
    return math.sin(2 * math.pi * (t * k + ph))


def sparkle(d, x, y, c="#fff0d8"):
    for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
        d.point((x + dx, y + dy), fill=h(c))


# ---------------- camas ----------------
def cama_almofada(t, use):
    d = D[0]
    s = sn(t)
    cy = BY - 12
    rx, ry = (31, 13) if not use else (31 + round(1.2 * s), 13 - round(1.4 * s))
    shadow(d, CX, 33, 5)
    E(d, CX, cy + 2, rx, ry, h("#8a3a52"), OUT)
    E(d, CX, cy, rx - 2, ry - 2, h("#a84a66"))
    E(d, CX - 3, cy - 2, rx - 9, ry - 5, h("#c26a82"))
    E(d, CX - 7, cy - 4, 8, 2, h("#e08aa2"))
    d.point((CX, cy), fill=h("#5c2338"))
    d.point((CX + 1, cy), fill=h("#5c2338"))
    for sx in (-1, 1):
        d.rectangle((CX + sx * (rx - 1) - 1, cy + 2, CX + sx * (rx - 1) + 1, cy + 4), fill=h("#e8c46a"), outline=OUT)
    if (not use and int(t * 6) in (2, 3)) or (use and int(t * 8) % 4 == 1):
        sparkle(d, CX - 12, cy - 5)


def cama_cesto(t, use):
    d = D[0]
    s = sn(t)
    ox = round(s) if use else 0
    cy = BY - 17
    shadow(d, CX, 33, 5)
    E(d, CX + ox, cy + 4, 30, 14, h("#6b4a31"), OUT)
    for i in range(-24, 25, 6):
        d.line((CX + ox + i, cy + 9, CX + ox + i + 1, cy + 16), fill=h("#4a3022"))
    E(d, CX + ox, cy, 31, 14, h("#8a6240"), OUT)
    E(d, CX + ox, cy, 25, 10 - (1 if use and s > 0 else 0), h("#c9a98a"), h("#5a3d28"))
    E(d, CX + ox - 3, cy - 2, 16, 5, h("#e0c4a6"))
    k = round(1.5 * sn(t, 1, 0.2))
    d.polygon([(CX + 14 + ox, cy - 6), (CX + 24 + ox, cy - 4 + k), (CX + 16 + ox, cy + 2)], fill=h("#e8a0b0"), outline=OUT)
    for i in range(-22, 23, 4):
        d.point((CX + ox + i, cy - 12 + (i // 4) % 2), fill=h("#a88458"))


def cama_pedra(t, use):
    d = D[0]
    cy = BY - 11
    pul = 0.5 + 0.5 * sn(t)
    gl = h("#e8884a") if pul > 0.5 or use else h("#b8683a")
    shadow(d, CX, 33, 5)
    E(d, CX, cy + 3, 32, 14, gl)
    E(d, CX, cy + 2, 30, 13, h("#241c34"))
    E(d, CX, cy + 1, 29, 13, h("#5d6c96"), OUT)
    E(d, CX - 1, cy - 1, 24, 9, h("#7384ae"))
    E(d, CX - 5, cy - 3, 14, 4, h("#93a3c8"))
    for px, py, c in ((CX + 10, cy + 2, "#5d6c96"), (CX - 14, cy + 1, "#5d6c96"), (CX + 4, cy - 4, "#8fa0c6")):
        d.point((px, py), fill=h(c))
    nw = 4 if use else 3
    for k in range(nw):
        ph = (t * 2 + k / nw) % 1.0
        y = cy - 6 - int(ph * 22)
        x = CX - 14 + k * (28 // max(nw - 1, 1)) + round(2 * math.sin(2 * math.pi * (ph * 2 + k * 0.3)))
        c = h("#f2b27a") if ph < 0.6 else h("#b8a0a8")
        d.point((x, y), fill=c)
        d.point((x, y + 1), fill=c)


# ---------------- brinquedos ----------------
def novelo(t, use):
    d = D[0]
    r = 8
    if use:
        bx = CX + round(12 * sn(t))
        dirn = 1 if sn(t, 1, 0.25) > 0 else -1
        ang = dirn * 2 * math.pi * t * 2
        cy = BY - r - 1 - round(abs(sn(t, 2)) * 2)
    else:
        bx = CX
        ang = 0.15 * sn(t)
        cy = BY - r - 1
    shadow(d, bx + 1, 10, 3)
    ox, oy = CX - 20, BY - 3
    n = 14
    for i in range(n):
        u = i / n
        x = ox + (bx - r - ox) * u
        wob = 3 * math.sin(math.pi * u * 2 + (t * 2 * math.pi if use else 0.3)) if use else 2 * math.sin(math.pi * u)
        y = oy + (cy + r - 2 - oy) * u + wob
        d.point((round(x), round(y)), fill=h("#e0507a"))
    if not use:
        e1 = bx + r + 8 + round(sn(t))
        d.line((bx + r, cy + 5, e1, cy + 7), fill=h("#e0507a"))
        d.line((e1, cy + 7, bx + r + 12, cy + 5), fill=h("#e0507a"))
    E(d, bx, cy, r, r, h("#e0507a"), OUT)
    E(d, bx - 2, cy - 2, 4, 4, h("#f58aa8"))
    for k in range(3):
        a = ang + k * math.pi / 3
        d.line((bx + 6 * math.cos(a), cy + 6 * math.sin(a), bx + 6 * math.cos(a + 2.2), cy + 6 * math.sin(a + 2.2)),
               fill=h("#b0305a"))
    d.point((bx - 4, cy - 4), fill=h("#ffd0dc"))


def ratinho(t, use):
    d = D[0]
    if use:
        bx = CX + round(12 * sn(t))
        up = round(abs(sn(t, 2)) * 9)
        dirn = 1 if sn(t, 1, 0.25) > 0 else -1
    else:
        bx, up, dirn = CX, 0, 1
    by = BY - 7 - up
    shadow(d, bx, max(4, 10 - up // 2), 3)
    ph = 2 * math.pi * t * (2 if use else 1)
    for i in range(16):
        x = bx - dirn * (10 + i)
        y = by + 2 + round(3 * math.sin(i * 0.55 - ph))
        d.point((x, y), fill=h("#f09aa8"))
        d.point((x, y + 1), fill=h("#c06a7c"))
    E(d, bx, by, 11, 7, h("#9aa0b4"), OUT)
    E(d, bx - dirn, by - 1, 7, 3, h("#c4c9d8"))
    E(d, bx + dirn * 6, by - 6, 3, 3, h("#f09aa8"), OUT)
    E(d, bx, by - 7, 3, 3, h("#f09aa8"), OUT)
    d.point((bx + dirn * 9, by - 1), fill=h("#f09aa8"))
    d.point((bx + dirn * 6, by - 2), fill=h("#2a1c2a"))
    if use:
        k = 1 + int(t * 8) % 2 * 3
        d.line((bx - 4, by + 7, bx - 4 + dirn * k, by + 8), fill=OUT)
        d.line((bx + 4, by + 7, bx + 4 - dirn * k, by + 8), fill=OUT)
    elif int(t * 6) == 3:
        d.point((bx + 3, by - 4), fill=h("#ffffff"))
        d.point((bx + 2, by - 4), fill=h("#ffffff"))


def pena(t, use):
    d = D[0]
    th = math.radians(24 * sn(t, 2) if use else 7 * sn(t))
    shadow(d, CX, 9, 3)
    E(d, CX, BY - 3, 7, 3, h("#6b4a31"), OUT)
    bx, by = CX, BY - 4
    u = (math.sin(th), -math.cos(th))
    v = (-u[1], u[0])
    tip = (bx + u[0] * 30, by + u[1] * 30)
    d.line((bx, by, tip[0], tip[1]), fill=h("#8a6a2c"), width=2)
    pts = [tip, (tip[0] + u[0] * 8 + v[0] * 6, tip[1] + u[1] * 8 + v[1] * 6),
           (tip[0] + u[0] * 17, tip[1] + u[1] * 17),
           (tip[0] + u[0] * 8 - v[0] * 6, tip[1] + u[1] * 8 - v[1] * 6)]
    d.polygon(pts, fill=h("#9fd8c4"), outline=OUT)
    d.line((tip[0] + u[0] * 2, tip[1] + u[1] * 2, tip[0] + u[0] * 14, tip[1] + u[1] * 14), fill=h("#d9f3e8"))
    d.point((round(tip[0]), round(tip[1])), fill=h("#e8c46a"))


def arranhador(t, use):
    d = D[0]
    o = round(1.5 * sn(t)) if use else 0
    shadow(d, CX, 24, 4)
    d.rectangle((CX - 19, BY - 9, CX + 19, BY - 1), fill=OUT)
    d.rectangle((CX - 18, BY - 8, CX + 18, BY - 2), fill=h("#7a5a40"))
    d.line((CX - 18, BY - 8, CX + 18, BY - 8), fill=h("#9a7a58"))
    top = BY - 46
    d.polygon([(CX - 8, BY - 9), (CX + 8, BY - 9), (CX + 8 + o, top), (CX - 8 + o, top)], fill=OUT)
    d.polygon([(CX - 7, BY - 9), (CX + 7, BY - 9), (CX + 7 + o, top), (CX - 7 + o, top)], fill=h("#c9a470"))
    for i in range(0, 36, 3):
        y = BY - 10 - i
        oo = round(o * (BY - 9 - y) / 37)
        d.line((CX - 7 + oo, y, CX + 7 + oo, y), fill=h("#a88450"))
    d.line((CX - 6 + o, BY - 12, CX - 6 + o, top + 2), fill=h("#e0c08a"))
    d.rectangle((CX - 15 + o, top - 6, CX + 15 + o, top), fill=OUT)
    d.rectangle((CX - 14 + o, top - 5, CX + 14 + o, top - 1), fill=h("#7a5a40"))
    d.line((CX - 14 + o, top - 5, CX + 14 + o, top - 5), fill=h("#9a7a58"))
    a = math.radians(18 * sn(t, 1, 0.4 if use else 0.1))
    px, py = CX + 12 + o, top
    ex, ey = px + 11 * math.sin(a), py + 11 * math.cos(a)
    d.line((px, py, ex, ey), fill=h("#e8c46a"))
    E(d, round(ex), round(ey) + 2, 3, 3, h("#e0507a"), OUT)
    if use:
        k = int(t * 8)
        for j in range(3):
            fx = CX - 9 - ((k + j * 3) % 8) * 1.5 + o
            fy = BY - 28 + j * 6 + ((k + j * 3) % 8) * 1.2
            if (k + j) % 4 != 3:
                d.point((round(fx), round(fy)), fill=h("#e0c08a"))
                d.point((round(fx) + 1, round(fy)), fill=h("#a88450"))


# ---------------- breed e filhotes ----------------
HEART = ["01101100", "11111110", "11111110", "01111100", "00111000", "00010000"]


def heart(d, x, y, c):
    for j, row in enumerate(HEART):
        for i, v in enumerate(row):
            if v == "1":
                d.point((x + i, y + j), fill=c)
    d.point((x + 1, y + 1), fill=h("#ffd0dc"))


def cama_casal(t, use):
    d = D[0]
    br = round(1.3 * sn(t)) if use else 0
    cy = BY - 15
    shadow(d, CX, 45, 6)
    E(d, CX, cy + 3, 45, 19 + br, h("#8a3a52"), OUT)
    E(d, CX, cy + 1, 42, 17 + br, h("#a84a66"))
    E(d, CX, cy + 1 - br, 35, 12, h("#f0c8a0"), h("#c98a6a"))
    E(d, CX - 2, cy - 1 - br, 28, 8, h("#f8dcb8"))
    E(d, CX - 19, cy - 5 - br, 12, 6, h("#f6e3c8"), OUT)
    E(d, CX + 19, cy - 5 - br, 12, 6, h("#e8a0b0"), OUT)
    E(d, CX - 21, cy - 7 - br, 6, 2, h("#ffffff"))
    E(d, CX + 17, cy - 7 - br, 6, 2, h("#f8c4cc"))
    for x in range(-14, 15, 7):
        d.point((CX + x, cy + 4 - br), fill=h("#e08aa2"))
        d.point((CX + x + 3, cy + 6 - br), fill=h("#e08aa2"))
    for sx in (-1, 1):
        d.rectangle((CX + sx * 44 - 1, cy + 4, CX + sx * 44 + 1, cy + 6), fill=h("#e8c46a"), outline=OUT)
    n = 2 if use else 1
    for k in range(n):
        ph = (t + k / n) % 1.0
        y = cy - 12 - int(ph * 26)
        x = CX - 3 + round(3 * math.sin(2 * math.pi * (ph + k * 0.4)))
        if ph < 0.85:
            heart(d, x, y, h("#f09aa8") if ph < 0.6 else h("#c8808e"))
    if not use and int(t * 6) in (2, 3):
        sparkle(d, CX - 34, cy - 12)


def viveiro_cesto(t, use):
    d = D[0]
    ox = round(1.2 * sn(t)) if use else 0
    cy = BY - 11
    shadow(d, CX, 40, 5)
    E(d, CX + ox, cy + 4, 38, 13, h("#d8b890"), OUT)
    for i in range(-32, 33, 6):
        d.line((CX + ox + i, cy + 8, CX + ox + i + 1, cy + 15), fill=h("#a88458"))
    E(d, CX + ox, cy, 39, 13, h("#e8cba4"), OUT)
    E(d, CX + ox, cy, 33, 9, h("#9fb8e0"), h("#7a96c8"))
    E(d, CX + ox - 3, cy - 2, 24, 5, h("#bcd0f0"))
    for sx in (-20, -2, 16):
        d.point((CX + ox + sx, cy), fill=h("#fff0b0"))
        d.point((CX + ox + sx + 1, cy + 2), fill=h("#fff0b0"))
    px = CX + ox + (-20, -2, 16)[int(t * 6) % 3]
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        d.point((px + dx, cy + dy - 1), fill=h("#ffffff"))
    d.rectangle((CX + ox + 28, cy - 9, CX + ox + 30, cy - 7), fill=h("#f8c4cc"), outline=OUT)


def bola_filhote(t, use):
    d = D[0]
    r = 8
    sq = False
    if use:
        up = round(math.sin(math.pi * ((t * 2) % 1.0)) * 20)
        sq = up < 2
    else:
        up = round(abs(sn(t)))
    rx, ry = (10, 6) if sq else (r, r)
    cy = BY - ry - 1 - (0 if sq else up)
    shadow(d, CX, max(4, 10 - up // 3), 3)
    E(d, CX, cy, rx, ry, h("#f58aa8"), OUT)
    d.rectangle((CX - rx + 1, cy - 1, CX + rx - 1, cy + 1), fill=h("#f5e07a"))
    d.rectangle((CX - rx + 2, cy + 2, CX + rx - 2, cy + ry - 2), fill=h("#9fd8c4"))
    d.point((CX - 3, cy - ry + 2), fill=h("#ffd0dc"))
    d.point((CX - 2, cy - ry + 2), fill=h("#ffd0dc"))
    if use and not sq and up > 12:
        d.point((CX + 12, cy - 4), fill=h("#fff0b0"))
        d.point((CX - 12, cy - 4), fill=h("#fff0b0"))


def casinha(t, use):
    d = D[0]
    shadow(d, CX, 34, 5)
    d.rectangle((CX - 29, BY - 34, CX + 29, BY - 1), fill=OUT)
    d.rectangle((CX - 28, BY - 33, CX + 28, BY - 2), fill=h("#8a78b8"))
    d.rectangle((CX - 28, BY - 33, CX - 22, BY - 2), fill=h("#a090d0"))
    for y in range(BY - 31, BY - 3, 6):
        d.line((CX - 28, y, CX + 28, y), fill=h("#7a68a8"))
    d.polygon([(CX - 34, BY - 32), (CX + 34, BY - 32), (CX + 22, BY - 52), (CX - 22, BY - 52)], fill=OUT)
    d.polygon([(CX - 32, BY - 33), (CX + 32, BY - 33), (CX + 21, BY - 50), (CX - 21, BY - 50)], fill=h("#b84a5a"))
    d.polygon([(CX - 32, BY - 33), (CX - 24, BY - 33), (CX - 17, BY - 50), (CX - 21, BY - 50)], fill=h("#d86a78"))
    for x in range(-28, 29, 8):
        d.line((CX + x, BY - 33, CX + x + 3, BY - 48 + abs(x) // 4), fill=h("#9a3a4a"))
    d.rectangle((CX - 11, BY - 24, CX + 11, BY - 2), fill=OUT)
    d.ellipse((CX - 11, BY - 32, CX + 11, BY - 16), fill=OUT)
    d.rectangle((CX - 10, BY - 23, CX + 10, BY - 2), fill=h("#241830"))
    d.ellipse((CX - 10, BY - 31, CX + 10, BY - 15), fill=h("#241830"))
    sw = (3 if use else 1.5) * sn(t)
    for sx in (-1, 1):
        x0 = CX + sx * 10
        pts = [(CX, BY - 30), (x0, BY - 26), (x0 + round(sw * -sx * 0.5), BY - 6), (CX + round(sw) + sx * 2, BY - 8)]
        d.polygon(pts, fill=h("#e8a0b0"), outline=OUT)
        d.line((CX + sx * 4, BY - 26, CX + sx * 6 + round(sw * 0.5), BY - 9), fill=h("#f8c4cc"))
    d.rectangle((CX - 8, BY - 36, CX + 8, BY - 34), fill=h("#e8c46a"), outline=OUT)
    if use and int(t * 8) in (1, 2, 5, 6):
        heart(d, CX + 20, BY - 40 - (int(t * 8) % 4) * 2, h("#f09aa8"))
    d.point((CX + 22, BY - 20), fill=h("#e8c46a"))


KINDS_OBJ = {
    "cama_almofada": cama_almofada, "cama_cesto": cama_cesto, "cama_pedra": cama_pedra,
    "novelo": novelo, "ratinho": ratinho, "pena": pena, "arranhador": arranhador,
    "cama_casal": cama_casal, "viveiro_cesto": viveiro_cesto, "bola_filhote": bola_filhote, "casinha": casinha,
}
NIDLE, NUSE = 6, 8


def frame(fn, t, use, w=W, hh=H):
    im = Image.new("RGBA", (w, hh), (0, 0, 0, 0))
    D[0] = ImageDraw.Draw(im)
    fn(t, use)
    return im


# ---------------- ambiente (64x64) ----------------
AW = 64


def lanterna(t, use):
    d = D[0]
    cx = 32
    f = [0, 1, 0, -1, 1, 0, -1, 0][int(t * 8) % 8]
    r = 22 + f
    for rr, a in ((r, 20), (r * 2 // 3, 26), (r // 3, 40)):
        d.ellipse((cx - rr, 14 - rr * 3 // 4, cx + rr, 14 + rr * 3 // 4), fill=(255, 190, 90, a))
    d.rectangle((cx - 2, 22, cx + 1, 60), fill=OUT)
    d.rectangle((cx - 1, 22, cx, 60), fill=h("#4a4868"))
    d.rectangle((cx - 4, 56, cx + 3, 60), fill=OUT)
    d.rectangle((cx - 3, 57, cx + 2, 59), fill=h("#4a4868"))
    d.rectangle((cx - 6, 8, cx + 5, 22), fill=OUT)
    d.rectangle((cx - 5, 10, cx + 4, 21), fill=h("#2a2438"))
    d.rectangle((cx - 4, 11, cx + 3, 20), fill=h("#ffb84a"))
    fh = 6 + f
    d.polygon([(cx - 1, 20), (cx + 1, 20), (cx + 2, 20 - fh // 2), (cx, 20 - fh), (cx - 2, 20 - fh // 2)], fill=h("#fff2a8"))
    d.rectangle((cx - 1, 17, cx, 20), fill=h("#ffffff"))
    d.polygon([(cx - 8, 8), (cx + 7, 8), (cx + 1, 2), (cx - 2, 2)], fill=OUT)
    d.polygon([(cx - 6, 7), (cx + 5, 7), (cx + 1, 3), (cx - 2, 3)], fill=h("#4a4868"))


def vagalumes(t, use):
    d = D[0]
    for k in range(5):
        a, b = 8 + k * 3, 6 + (k * 5) % 9
        x = 32 + a * math.sin(2 * math.pi * (t + k * 0.2)) * (1 if k % 2 else -1)
        y = 32 + b * math.sin(2 * math.pi * (2 * t + k * 0.13))
        inten = 0.5 + 0.5 * math.sin(2 * math.pi * (t * (1 + k % 2) + k * 0.37))
        x, y = round(x), round(y)
        if inten > 0.25:
            d.point((x, y), fill=h("#e8ff8a"))
        if inten > 0.6:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                d.point((x + dx, y + dy), fill=(200, 240, 106, 120))


def grama(t, use):
    d = D[0]
    cols = [h("#2a5a4a"), h("#3f8a62"), h("#2f6a52"), h("#4a9a70"), h("#3f8a62")]
    for i, (bx, hgt) in enumerate(((-6, 9), (-3, 13), (0, 16), (3, 12), (6, 8))):
        sw = 2.2 * math.sin(2 * math.pi * (t + i * 0.1)) * (hgt / 16)
        for j in range(hgt):
            u = j / hgt
            c = cols[i] if j < hgt - 2 else h("#7ac090")
            d.point((32 + bx + round(sw * u * u * 1.5) + round(bx * u * 0.4), 60 - j), fill=c)


def arbusto(t, use):
    d = D[0]
    dk, md, lt = h("#12302c"), h("#1f4a40"), h("#2f6a52")
    blobs = [(-14, -8, 9), (0, -12, 11), (14, -8, 9), (-6, -4, 10), (8, -4, 10)]
    for stage in (0, 1):
        for i, (bx, by_, r) in enumerate(blobs):
            ox = round(1.5 * math.sin(2 * math.pi * (t + i * 0.13))) if by_ < -5 else 0
            x, y = 32 + bx + ox, 56 + by_
            if stage == 0:
                d.ellipse((x - r, y - r, x + r, y + r), fill=dk)
            else:
                d.ellipse((x - r + 1, y - r + 1, x + r - 1, y + r - 1), fill=md)
                d.ellipse((x - r + 3, y - r + 2, x + 1, y - 1), fill=lt)
    for i, (fx, fy) in enumerate(((-10, -12), (4, -18), (12, -8), (-2, -6))):
        ox = round(1.5 * math.sin(2 * math.pi * (t + i * 0.2)))
        d.point((32 + fx + ox, 56 + fy), fill=h("#f09aa8"))
        d.point((32 + fx + ox + 1, 56 + fy), fill=h("#ffd0dc"))


def folhas(t, use):
    d = D[0]
    for k in range(2):
        f = (int(t * 8) + k * 4) % 8
        if f == 7:
            continue
        y = 6 + f * 7
        x = 32 + round(7 * math.sin(2 * math.pi * (f / 8 + k * 0.5))) + (k * 8 - 4)
        c1, c2 = (h("#d98f4e"), h("#b86a3a")) if k == 0 else (h("#c0a050"), h("#8a7030"))
        if f % 2:
            d.rectangle((x, y, x + 2, y + 1), fill=c1)
            d.point((x + 1, y + 2), fill=c2)
        else:
            d.rectangle((x, y, x + 1, y + 2), fill=c1)
            d.point((x + 2, y + 1), fill=c2)


def estrela(t, use):
    d = D[0]
    pos = [(8, 24), (20, 10), (34, 30), (46, 14), (56, 34), (14, 40)]
    for k, (x, y) in enumerate(pos):
        lvl = 0.5 + 0.5 * math.sin(2 * math.pi * (t * (1 + k % 2) + k * 0.31))
        if lvl > 0.8:
            d.point((x, y), fill=h("#ffffff"))
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                d.point((x + dx, y + dy), fill=h("#aab8e0"))
        elif lvl > 0.4:
            d.point((x, y), fill=h("#e8efff"))
        else:
            d.point((x, y), fill=h("#5a6a98"))


def fonte(t, use):
    d = D[0]
    cx, by = 32, 58
    shadow(d, cx, 26, 5, by)
    E(d, cx, by - 8, 26, 10, h("#5d6c96"), OUT)
    E(d, cx, by - 9, 22, 7, h("#3a7aa8"), h("#7384ae"))
    E(d, cx - 2, by - 10, 14, 3, h("#5a9ac8"))
    for k in range(2):
        ph = (t + k * 0.5) % 1.0
        rr = int(4 + ph * 16)
        if ph < 0.9:
            d.arc((cx - rr, by - 9 - rr // 3, cx + rr, by - 9 + rr // 3), 0, 360, fill=h("#9ad0f0"))
    d.rectangle((cx - 3, by - 28, cx + 2, by - 12), fill=OUT)
    d.rectangle((cx - 2, by - 27, cx + 1, by - 13), fill=h("#7384ae"))
    E(d, cx, by - 28, 8, 3, h("#5d6c96"), OUT)
    E(d, cx, by - 29, 6, 2, h("#5a9ac8"))
    for k in range(4):
        ph = (t + k / 4) % 1.0
        for sx in (-1, 1):
            x = cx + sx * ph * 12
            y = by - 30 - (1 - (2 * ph - 1) ** 2) * 9 + ph * ph * 12
            d.point((round(x), round(y)), fill=h("#bfe4f8") if ph < 0.7 else h("#7ab4d8"))
    d.point((cx, by - 33 - int(sn(t, 2) + 1)), fill=h("#d8f0ff"))


KINDS_AMB = {"lanterna": (lanterna, 8, 8), "vagalumes": (vagalumes, 8, 6), "grama": (grama, 6, 6),
             "arbusto": (arbusto, 8, 6), "folhas": (folhas, 8, 6), "estrela": (estrela, 8, 4), "fonte": (fonte, 8, 8)}


def build():
    rows = len(KINDS_OBJ) * 2
    sheet = Image.new("RGBA", (8 * W, rows * H), (0, 0, 0, 0))
    meta = {}
    r = 0
    for name, fn in KINDS_OBJ.items():
        anims = {}
        for an, n, fps, use in (("idle", NIDLE, 6, False), ("use", NUSE, 8, True)):
            for i in range(n):
                sheet.paste(frame(fn, i / n, use), (i * W, r * H))
            anims[an] = {"row": r, "frames": n, "fps": fps}
            r += 1
        meta[name] = {"frame": [W, H], "anchor": [CX, BY], "layer": LAYER[name], "anims": anims}
    sheet.save(os.path.join(PEN, "objects.png"))
    with open(os.path.join(PEN, "objects.json"), "w") as f:
        json.dump({"image": "objects.png", "size": list(sheet.size), "objects": meta}, f, indent=1)
    sheet = Image.new("RGBA", (8 * AW, len(KINDS_AMB) * AW), (0, 0, 0, 0))
    meta = {}
    for r, (name, (fn, n, fps)) in enumerate(KINDS_AMB.items()):
        for i in range(n):
            sheet.paste(frame(fn, i / n, False, AW, AW), (i * AW, r * AW))
        meta[name] = {"frame": [AW, AW], "anchor": [32, 60], "anims": {"idle": {"row": r, "frames": n, "fps": fps}}}
    sheet.save(os.path.join(PEN, "ambient.png"))
    with open(os.path.join(PEN, "ambient.json"), "w") as f:
        json.dump({"image": "ambient.png", "size": list(sheet.size), "objects": meta, "ambient": meta}, f, indent=1)


if __name__ == "__main__":
    build()
    print("ok")
