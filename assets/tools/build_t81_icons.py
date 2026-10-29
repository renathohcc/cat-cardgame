"""T8.1: icones 16x16 desenhados pixel a pixel (mascaras ASCII + sombreamento + contorno automatico #3b2a38).
Sem IA. Importado por build_t81.py."""
from PIL import Image

OUT = (0x3b, 0x2a, 0x38, 255)


def hx(s): s = s.lstrip("#"); return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), 255)


RAMPS = {  # (luz, base, sombra)
    "red": ("#ff8a8a", "#e5484d", "#a02838"), "grn": ("#a8f0a0", "#4cc85a", "#22803a"),
    "blu": ("#9ae0ff", "#3f8fe8", "#2450a8"), "cya": ("#e8ffff", "#5fe0ee", "#2a98b8"),
    "org": ("#ffd070", "#ff9a2e", "#c8561e"), "yel": ("#fff6a0", "#ffd84a", "#d89a1e"),
    "stl": ("#ffffff", "#c4cad8", "#6c7488"), "brn": ("#d09060", "#9a5a30", "#5e3420"),
    "pur": ("#e0b0ff", "#a060e0", "#603098"), "pnk": ("#ffd0dc", "#f09aa8", "#c05878"),
}


def parse(rows):
    return {(x, y): c for y, r in enumerate(rows) for x, c in enumerate(r) if c != "."}


def shade(pix, ramp):
    """pix: set de (x,y). Luz em cima/esquerda, sombra embaixo/direita."""
    lt, ba, dk = (hx(c) for c in RAMPS[ramp]); out = {}
    for (x, y) in pix:
        up = (x, y - 1) not in pix or (x - 1, y) not in pix
        dn = (x, y + 1) not in pix or (x + 1, y) not in pix
        out[(x, y)] = lt if up and not dn else dk if dn and not up else ba
    return out


def colorize(rows, ramps):
    """rows com chars; letras mapeadas por 'ramps' {char: ramp} usam shade; maiusculas fixas via FIX."""
    pix = parse(rows); out = {}
    for ch, rp in ramps.items():
        out.update(shade({p for p, c in pix.items() if c == ch}, rp))
    for p, c in pix.items():
        if c in FIX: out[p] = hx(FIX[c])
    return out


FIX = {"w": "#ffffff", "Y": "#ffe26a", "k": "#2a1c2a", "O": "#ff9a2e", "R": "#e5484d", "g": "#22803a", "n": "#8a5a30", "d": "#a02838"}


def place(pix, size=16):
    xs = [p[0] for p in pix]; ys = [p[1] for p in pix]
    w, h = max(xs) - min(xs) + 1, max(ys) - min(ys) + 1; assert w <= size - 2 and h <= size - 2, (w, h)
    ox, oy = (size - w) // 2 - min(xs), (size - h) // 2 - min(ys)
    return {(x + ox, y + oy): c for (x, y), c in pix.items()}


def outline(pix, size=16):
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); px = im.load()
    for (x, y) in pix:
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                q = (x + dx, y + dy)
                if 0 <= q[0] < size and 0 <= q[1] < size and q not in pix: px[q] = OUT
    for (x, y), c in pix.items(): px[x, y] = c
    return im


def shield():
    rows = ["KKKKKKKKKKKK", "KBBBBBBBBBBB", "KBBBBYYBBBBB", "KBBBBYYBBBBB", "KBBBYYYYBBBB", "KBBBBYYBBBBB", "KBBBBYYBBBBB",
            ".BBBBYYBBBB.", ".BBBBBBBBBB.", "..BBBBBBBB..", "...BBBBBB...", "....BBBB....", ".....BB....."]
    pix = parse(rows)
    out = shade({p for p, c in pix.items() if c == "B"}, "blu"); out.update(shade({p for p, c in pix.items() if c == "K"}, "stl"))
    out.update({p: hx("#ffd84a") for p, c in pix.items() if c == "Y"})
    return out


def charge():  # investida: seta para frente com linhas de velocidade
    rows = ["........Y.....", "........YY....", "........YYY...", "YYYYYYYYYYYY..", "YYYYYYYYYYYYY.", "YYYYYYYYYYYYYY", "YYYYYYYYYYYYY.", "YYYYYYYYYYYY..", "........YYY...", "........YY....", "........Y....."]
    pix = {p for p, c in parse(rows).items()}
    # linhas de velocidade: apaga trechos da cauda
    for p in [(0, 4), (1, 4), (2, 4), (0, 6), (1, 6), (2, 6), (0, 3), (0, 7), (1, 3), (1, 7)]: pix.discard(p)
    for p in [(3, 3), (4, 3), (3, 7), (4, 7)]: pix.discard(p)
    return shade(pix, "yel") | {p: hx("#ff9a2e") for p in []}


def claws():  # primeira-patada: pata com almofada e garras vermelhas
    rows = ["...XX..XX...", "...XX..XX...", "XX........XX", "XX..XXXX..XX", "....XXXX....", "..XXXXXXXX..", ".XXXXXXXXXX.", ".XXXXXXXXXX.", ".XXXXXXXXXX.", "..XXXXXXXX..", "...XXXXXX..."]
    pix = set(parse(rows)); out = shade(pix, "stl")
    for p in pix:
        if 5 <= p[1] <= 9 and 3 <= p[0] <= 8: out[p] = hx("#f09aa8") if p[0] < 6 and p[1] < 8 else hx("#c05878")
    for x in (3, 8): out[(x, 0)] = out[(x, 1)] = hx("#e5484d")
    for p in [(0, 2), (11, 2), (0, 3), (11, 3)]: out[p] = hx("#e5484d")
    return out


def heart(ramp, cross=False):
    rows = ["..XXX...XXX..", ".XXXXX.XXXXX.", "XXXXXXXXXXXXX", "XXXXXXXXXXXXX", "XXXXXXXXXXXXX", ".XXXXXXXXXXX.", "..XXXXXXXXX..",
            "...XXXXXXX...", "....XXXXX....", ".....XXX.....", "......X......"]
    pix = {p for p in parse(rows)}; out = shade(pix, ramp)
    out[(3, 2)] = out[(2, 3)] = hx("#ffffff")
    if cross:
        for p in [(6, 3), (6, 4), (6, 5), (5, 4), (7, 4), (6, 6)]: out[p] = hx("#ffffff")
    return out


def cross():
    pix = {(x, y) for x in range(12) for y in range(12) if (4 <= x <= 7) or (4 <= y <= 7)}
    return shade(pix, "grn")


def buff():  # seta para cima, laranja
    rows = ["......XX......", ".....XXXX.....", "....XXXXXX....", "...XXXXXXXX...", "..XXXXXXXXXX..", ".XXXXXXXXXXXX.", "....XXXXXX....", "....XXXXXX....", "....XXXXXX....", "....XXXXXX....", "....XXXXXX...."]
    return shade(set(parse(rows)), "org")


def burst():
    pix = {}
    for dy in range(-6, 7):
        for dx in range(-6, 7):
            d2 = dx * dx + dy * dy
            inn = (abs(dx) <= 1 and abs(dy) <= 6 and (abs(dx) == 0 or abs(dy) <= 4)) or (abs(dy) <= 1 and abs(dx) <= 6 and (abs(dy) == 0 or abs(dx) <= 4))
            inn = inn or (abs(dx) == abs(dy) and abs(dx) <= 5) or d2 <= 13 or (abs(abs(dx) - abs(dy)) == 1 and d2 <= 30 and min(abs(dx), abs(dy)) >= 2)
            if inn: pix[(dx + 6, dy + 6)] = hx("#ffffff") if d2 <= 2 else hx("#ffe26a") if d2 <= 7 else hx("#ff9a2e") if d2 <= 19 else hx("#e5484d")
    return pix


def card():
    pix = {}
    for x in range(5, 13):
        for y in range(0, 11): pix[(x, y)] = hx("#2450a8") if x > 5 and y > 0 else hx("#3f8fe8")
    for x in range(-1, 11):
        for y in range(1, 14):
            if x in (-1, 10) or y in (1, 13): pix[(x, y)] = OUT
    for x in range(0, 10):
        for y in range(2, 13):
            edge = x in (0, 9) or y in (2, 12)
            pix[(x, y)] = hx("#e8ffff") if edge else hx("#5fe0ee") if (x + y) % 2 == 0 or True else hx("#2a98b8")
    for p in [(4, 5), (5, 5), (3, 6), (4, 6), (5, 6), (6, 6), (4, 7), (5, 7), (4, 8), (5, 8), (4, 9), (5, 9)]: pix[p] = hx("#ffffff") if p[1] < 8 else hx("#2a98b8")
    for p in [(4, 4), (5, 4)]: pix[p] = hx("#ffffff")
    for y in range(3, 12): pix[(8, y)] = hx("#2a98b8")
    return pix


def bolt():
    rows = ["......XXXX", ".....XXXX.", "....XXXX..", "...XXXXXXX", "..XXXXXXX.", ".....XXX..", "....XXX...", "...XXX....", "..XXX.....", "..XX......", ".X........"]
    return shade(set(parse(rows)), "cya")


def gem():
    rows = ["..XXXXXX..", ".XXXXXXXX.", "XXXXXXXXXX", "XXXXXXXXXX", ".XXXXXXXX.", "..XXXXXX..", "...XXXX...", "....XX...."]
    out = shade(set(parse(rows)), "blu")
    for p in [(2, 1), (3, 1), (2, 2), (3, 3)]: out[p] = hx("#e8ffff")
    for p in [(5, 1), (6, 1), (4, 2), (5, 2), (6, 2), (7, 2)]: out[p] = hx("#7ac8ff")
    return out


def sword():
    pix = {}
    for i in range(9):
        x, y = 12 - i, i; pix[(x, y)] = "stl_l" if i else "w"; pix[(x - 1, y)] = "stl_d"
        if i == 0: pix.pop((x - 1, y))
    for p in [(2, 6), (3, 7), (4, 8), (5, 9), (6, 10), (3, 6), (4, 7), (5, 8), (6, 9)]: pix[p] = "gold"
    for p in [(3, 9), (2, 10), (1, 11)]: pix[p] = "brn"
    pix[(0, 12)] = "gold"; pix[(1, 12)] = "gold"; pix[(0, 11)] = "gold"
    cm = {"stl_l": "#ffffff", "stl_d": "#8a92a8", "w": "#ffffff", "gold": "#ffd84a", "brn": "#9a5a30"}
    out = {p: hx(cm[c]) for p, c in pix.items()}
    for x, y in [(11, 1), (10, 2), (9, 3), (8, 4), (7, 5), (6, 6), (5, 7)]: out[(x, y)] = hx("#d8deea")
    return out


ICONS = {
    "provocar": shield, "investida": charge, "primeira-patada": claws, "robusto": lambda: heart("grn", True),
    "acao-dano": burst, "acao-cura": cross, "acao-buff_atk": buff, "acao-comprar": card, "acao-energia": bolt,
    "custo": gem, "ataque": sword, "hp": lambda: heart("red"),
}


def build_icons():
    return {n: outline(place(f())) for n, f in ICONS.items()}
