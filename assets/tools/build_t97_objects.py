"""T9.7: objects.png/json, ambient.png/json e pen.json do quintal no estilo do jogo (paleta PEN, pixel 1:1, sem resize).
Cada objeto e desenhado por script no tamanho final (SIZE em build_t97_layout) e colocado no quadro 128x96 (ancora 64,86).
Uso: python assets/tools/build_t97_objects.py"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
import build_t97_layout as L  # noqa: E402
from build_t97_lib import (Canvas, bitmap, flat, m_ell, m_poly, m_rect, m_rrect, outline_of, shadow, shaded,  # noqa: E402
                           shift)

FW, FH, CX, BY = 128, 96, 64, 86


# ------------------------------------------------------------------ camas
def bed_oval(w, h, rim, inner, pillow, depth=4, weave=False, p=0.0, heart=False):
    """cama oval vista de cima-3/4. rim/inner/pillow = (base, luz, sombra)."""
    c = Canvas(w, h)
    th = h - depth
    top = m_ell(c, 0, 0, w, th)
    side = m_ell(c, 0, depth, w, th) & ~top
    full = m_ell(c, 0, depth, w, th) | top
    c.paint(full, rim[2])
    if weave:                                                # trama de cesto na parede lateral
        yy, xx = np.mgrid[0:h, 0:w]
        c.paint(side & (((xx // 3) + (yy // 2)) % 2 == 0), rim[0])
    c.paint(outline_of(full), "outline")
    shaded(c, top, rim[0], rim[1], rim[2], depth=2)
    ix, iy = 6, 4
    inn = m_ell(c, ix, iy, w - 2 * ix, th - 2 * iy + 1)
    shaded(c, inn, inner[0], inner[1], inner[2], depth=2, outline=None, flip=True)
    c.paint(outline_of(inn), rim[2])
    # almofada (afunda um pouco quando `p` > 0)
    pw = max(10, round((w - 2 * ix) * 0.42))
    ph = max(5, round((th - 2 * iy) * 0.42)) - (1 if p > 0.4 else 0)
    px_, py_ = ix + 4, iy + 3 + (1 if p > 0.9 else 0)
    if heart:
        pillow_heart(c, w // 2 - 6, iy + 3 + (1 if p > 0.9 else 0), pillow)
        pm = m_ell(c, ix + 5, iy + 5, 11, 6)
        shaded(c, pm, "cream", "cream_light", "cream_dark", depth=1)
        pm = m_ell(c, w - ix - 16, iy + 5, 11, 6)
        shaded(c, pm, "cream", "cream_light", "cream_dark", depth=1)
    else:
        pm = m_ell(c, px_, py_, pw, ph)
        shaded(c, pm, pillow[0], pillow[1], pillow[2], depth=1)
    return c


def pillow_heart(c, x, y, pillow):
    rows = [".XX.XX.",
            "XXXXXXX",
            "XXXXXXX",
            ".XXXXX.",
            "..XXX..",
            "...X..."]
    m = c.blank()
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch == "X":
                m[y + j, x + i] = True
    c.paint(outline_of(m), "outline")
    c.paint(m, pillow[0])
    c.paint(m & ~shift(m, 2, 2), pillow[1])
    c.paint(m & ~shift(m, -1, -1), pillow[2])


ROSE = ("rose", "rose_light", "rose_dark")
TEAL = ("teal", "teal_light", "teal_dark")
WOOD = ("wood", "wood_light", "wood_dark")
CREAM = ("cream", "cream_light", "cream_dark")


def spr_cama_almofada(p=0.0):
    return bed_oval(64, 40, ROSE, CREAM, ("rose_light", "cream_light", "rose"), p=p)


def spr_cama_cesto(p=0.0):
    return bed_oval(56, 36, WOOD, CREAM, TEAL, depth=6, weave=True, p=p)


def spr_cama_pedra(p=0.0):
    return bed_oval(48, 32, TEAL, ("cream_light", "cream_light", "cream"), ROSE, p=p)


def spr_cama_casal(p=0.0):
    return bed_oval(88, 44, ROSE, ("cream_light", "cream_light", "cream"), ("rose_light", "cream_light", "rose"),
                    depth=5, p=p, heart=True)


def spr_viveiro_cesto(p=0.0):
    return bed_oval(56, 36, WOOD, ("rose_light", "cream_light", "rose"), CREAM, depth=6, weave=True, p=p)


# ------------------------------------------------------------------ mobilia
def spr_banco():
    c = Canvas(72, 40)
    for lx in (4, 62):                                     # pernas
        r = m_rect(c, lx, 30, 6, 9)
        shaded(c, r, "wood_dark", "wood", "wood_dark", depth=1)
    for lx in (7, 59):                                     # apoio do encosto
        r = m_rect(c, lx, 8, 5, 6)
        shaded(c, r, "wood", "wood_light", "wood_dark", depth=1)
    back = m_rect(c, 1, 0, 70, 10)
    shaded(c, back, "wood", "wood_light", "wood_dark", depth=2)
    c.rect(2, 5, 70, 6, "wood_dark")                         # frestas do encosto
    seat = m_rect(c, 0, 12, 72, 14)
    shaded(c, seat, "wood_light", "cream", "wood", depth=2)
    for x in (23, 47):
        c.rect(x, 13, x + 1, 25, "wood")                      # tabuas
    front = m_rect(c, 0, 26, 72, 5)
    shaded(c, front, "wood", "wood_light", "wood_dark", depth=1)
    return c


def spr_casinha():
    c = Canvas(64, 64)
    body = m_rect(c, 5, 27, 54, 34)
    shaded(c, body, "wood", "wood_light", "wood_dark", depth=2)
    for x in (14, 23, 41, 50):                             # tabuas verticais
        c.rect(x, 28, x + 1, 60, "wood_dark")
    door = m_rect(c, 24, 42, 16, 19) | m_ell(c, 24, 34, 16, 16)
    c.paint(door, "outline")
    c.paint(outline_of(door), "wood_dark")
    cush = m_ell(c, 26, 53, 12, 7)
    shaded(c, cush, "rose", "rose_light", "rose_dark", depth=1, outline=None)
    lip = m_rect(c, 1, 20, 62, 8)
    shaded(c, lip, "teal_dark", "teal", "teal_dark", depth=1)
    roof = m_poly(c, [(8, 3), (55, 3), (62, 19), (1, 19)])
    shaded(c, roof, "teal", "teal_light", "teal_dark", depth=2)
    yy, xx = np.mgrid[0:64, 0:64]
    inner = roof & ~outline_of(~roof)
    c.paint(inner & ((yy == 9) | (yy == 14)), "teal_dark")      # telhas
    return c


def spr_casinha_filhote():
    c = Canvas(64, 64)
    body = m_rect(c, 7, 28, 50, 34)
    shaded(c, body, "cream", "cream_light", "cream_dark", depth=2)
    door = m_rect(c, 24, 44, 16, 17) | m_ell(c, 24, 36, 16, 16)
    c.paint(door, "outline")
    c.paint(outline_of(door), "wood")
    roof = m_poly(c, [(32, 0), (63, 28), (1, 28)])
    shaded(c, roof, "rose", "rose_light", "rose_dark", depth=2)
    yy, xx = np.mgrid[0:64, 0:64]
    inner = roof & ~outline_of(~roof)
    c.paint(inner & ((yy == 12) | (yy == 18) | (yy == 24)) & (xx % 8 != 0), "rose_dark")
    bitmap(c, 29, 14, [".X.X.", "XXXXX", ".XXX.", "..X.."], {"X": "cream_light"})
    return c


def spr_arranhador(shake=0):
    c = Canvas(40, 72)
    disc_side = m_ell(c, 2, 60, 36, 12)
    c.paint(disc_side, "wood_dark")
    c.paint(outline_of(disc_side), "outline")
    disc = m_ell(c, 2, 56, 36, 12)
    shaded(c, disc, "wood", "wood_light", "wood_dark", depth=2)
    post = m_rect(c, 14, 14, 12, 46)
    shaded(c, post, "cream", "cream_light", "cream_dark", depth=2)
    yy, xx = np.mgrid[0:72, 0:40]
    c.paint(post & ~outline_of(~post) & (yy % 4 == 0) & (yy > 18) & (xx > 15) & (xx < 24), "cream_dark")
    pf_side = m_ell(c, 2, 4, 36, 14)
    top = m_ell(c, 2, 0, 36, 14)
    c.paint(pf_side | top, "teal_dark")
    c.paint(outline_of(pf_side | top), "outline")
    shaded(c, top, "teal", "teal_light", "teal_dark", depth=2)
    if shake:
        c2 = Canvas(40, 72)
        c2.a[:, :] = shift_arr(c.a, shake)
        return c2
    return c


def shift_arr(a, dx):
    out = np.zeros_like(a)
    if dx > 0:
        out[:, dx:] = a[:, :-dx]
    elif dx < 0:
        out[:, :dx] = a[:, -dx:]
    else:
        out = a.copy()
    return out


def spr_tunel(phase=0):
    c = Canvas(80, 40)
    body = m_rrect(c, 8, 4, 68, 32, 14)
    lit = body & ~shift(body, 0, 4)
    shd = body & ~shift(body, 0, -5)
    yy, xx = np.mgrid[0:40, 0:80]
    stripe = ((xx + phase) // 8) % 2 == 0
    for sel, (b, l, d) in ((stripe, ("teal", "teal_light", "teal_dark")), (~stripe, ("cream", "cream_light", "cream_dark"))):
        c.paint(body & sel, b)
        c.paint(lit & sel & ~shd, l)
        c.paint(shd & sel, d)
    c.paint(outline_of(body), "outline")
    ring = m_ell(c, 0, 6, 20, 28)
    c.paint(ring, "teal_dark")
    c.paint(outline_of(ring), "outline")
    c.paint(m_ell(c, 4, 10, 12, 20), "outline")
    c.paint(m_ell(c, 4, 10, 12, 20) & ~shift(m_ell(c, 4, 10, 12, 20), 2, 2), "wood_dark")
    return c


# ------------------------------------------------------------------ brinquedos
def spr_novelo(ang=0.0):
    c = Canvas(16, 16)
    m = m_ell(c, 1, 1, 14, 14)
    shaded(c, m, "rose", "rose_light", "rose_dark", depth=2)
    core = m & ~outline_of(~m)
    for k in (-4, 0, 4):
        for t in np.linspace(-8, 8, 40):
            x = int(round(7.5 - k * math.sin(ang) + t * math.cos(ang)))
            y = int(round(7.5 + k * math.cos(ang) + t * math.sin(ang)))
            if 0 <= x < 16 and 0 <= y < 16 and core[y, x]:
                c.px(x, y, "rose_dark")
    c.px(14, 12, "outline")
    c.px(15, 13, "outline")
    return c


def spr_bola(ang=0.0):
    c = Canvas(16, 16)
    m = m_ell(c, 1, 1, 14, 14)
    shaded(c, m, "yellow", "cream_light", "wood_light", depth=2)
    core = m & ~outline_of(~m)
    for t in np.linspace(-8, 8, 40):
        x = int(round(7.5 + t * math.cos(ang)))
        y = int(round(7.5 + t * math.sin(ang) + 2 * math.sin(t * 0.4)))
        if 0 <= x < 16 and 0 <= y < 16 and core[y, x]:
            c.px(x, y, "rose")
    return c


def spr_ratinho(wig=0):
    c = Canvas(20, 12)
    body = m_ell(c, 3, 3, 13, 8)
    shaded(c, body, "stone", "stone_light", "stone_dark", depth=2)
    head = m_ell(c, 11, 4, 8, 6)
    shaded(c, head, "stone_light", "stone_light", "stone", depth=2)
    ear = m_ell(c, 10, 1, 4, 4)
    flat(c, ear, "rose_light")
    c.px(16, 6, "outline")
    c.px(18, 7, "rose")
    for i, (x, y) in enumerate([(2, 8), (1, 9), (0, 9), (0, 8)]):       # rabo
        c.px(x, y - (wig if i >= 2 else 0), "stone_dark")
    return c


def spr_tigela(food=False):
    c = Canvas(20, 12)
    top = m_ell(c, 0, 0, 20, 9)
    side = m_ell(c, 0, 3, 20, 9)
    both = top | side
    c.paint(side, "rose_dark" if food else "teal_dark")
    c.paint(outline_of(both), "outline")
    shaded(c, top, "rose" if food else "teal", "rose_light" if food else "teal_light",
           "rose_dark" if food else "teal_dark", depth=2)
    inn = m_ell(c, 3, 1, 14, 5)
    if food:
        c.paint(inn, "wood")
        for x, y in ((6, 3), (9, 2), (12, 3), (8, 4), (13, 4), (10, 3)):
            c.px(x, y, "wood_light" if (x + y) % 2 else "wood_dark")
    else:
        c.paint(inn, "teal_light")
        c.px(6, 2, "cream_light")
        c.px(7, 2, "cream_light")
    return c


SPR = {"cama_almofada": spr_cama_almofada, "cama_cesto": spr_cama_cesto, "cama_pedra": spr_cama_pedra,
       "cama_casal": spr_cama_casal, "viveiro_cesto": spr_viveiro_cesto}


def frame(img, dx=0, dy=0, shadow_w=None, shadow_dy=0, shade=True):
    f = Canvas(FW, FH)
    w, h = img.w, img.h
    if shade:
        sw = shadow_w or int(w * 0.94)
        shadow(f, CX - sw // 2, BY - 3 + shadow_dy, sw, 7)
    f.paste(img, CX - w // 2 + dx, BY - h + dy)
    return f


def sn(t, k=1):
    return math.sin(2 * math.pi * t * k)


ENTER = [0.5, 1.0, 1.0, 1.0]
EXIT = [0.5, 0.0, 0.0, 0.0]


def build_kinds():
    K = {}
    for k, fn in SPR.items():
        K[k] = [("idle", 1, 1, lambda i, fn=fn: frame(fn(0.0))),
                ("enter", 4, 8, lambda i, fn=fn: frame(fn(ENTER[i]))),
                ("exit", 4, 8, lambda i, fn=fn: frame(fn(EXIT[i])))]
    K["banco_arvore"] = [("idle", 1, 1, lambda i: frame(spr_banco()))]
    K["casinha"] = [("idle", 1, 1, lambda i: frame(spr_casinha()))]
    K["novelo"] = [("idle", 6, 6, lambda i: frame(spr_novelo(0.15 * sn(i / 6)))),
                   ("use", 8, 8, lambda i: frame(spr_novelo(-2 * math.pi * i / 8), dx=round(5 * sn(i / 8)),
                                                  dy=-round(abs(sn(i / 8, 2)) * 3), shadow_w=13))]
    K["ratinho"] = [("idle", 6, 6, lambda i: frame(spr_ratinho(round(sn(i / 6))))),
                    ("use", 8, 8, lambda i: frame(spr_ratinho(round(sn(i / 8, 2))), dx=round(3 * sn(i / 8)),
                                                   dy=-round(abs(sn(i / 8, 2)) * 5)))]
    K["arranhador"] = [("idle", 1, 1, lambda i: frame(spr_arranhador())),
                       ("use", 6, 10, lambda i: frame(spr_arranhador([0, 1, 0, -1, 0, 1][i]), shadow_w=36))]
    K["bola_filhote"] = [("idle", 1, 1, lambda i: frame(spr_bola(0.3))),
                         ("use", 8, 10, lambda i: frame(spr_bola(2 * math.pi * i / 8),
                                                         dy=-round(abs(sn(i / 16)) * 12), shadow_w=12))]
    K["tunel_filhote"] = [("idle", 1, 1, lambda i: frame(spr_tunel())),
                          ("use", 8, 8, lambda i: frame(spr_tunel(2 * i)))]
    K["tigela"] = [("idle", 1, 1, lambda i: frame(spr_tigela(False)))]
    K["tigela_racao"] = [("idle", 1, 1, lambda i: frame(spr_tigela(True)))]
    K["casinha_filhote"] = [("idle", 1, 1, lambda i: frame(spr_casinha_filhote()))]
    return K


def build_objects():
    K = build_kinds()
    nrows = sum(len(K[k]) for k in L.ORDER)
    sheet = Image.new("RGBA", (8 * FW, nrows * FH), (0, 0, 0, 0))
    meta, r = {}, 0
    for name in L.ORDER:
        anims = {}
        for an, n, fps, fn in K[name]:
            for i in range(n):
                sheet.paste(fn(i).image(), (i * FW, r * FH))
            loop = an not in ("enter", "exit")
            anims[an] = {"row": r, "frames": n, "fps": fps, "loop": loop}
            r += 1
        meta[name] = {"frame": [FW, FH], "anchor": [CX, BY], "layer": L.LAYER[name], "anims": anims}
    sheet.save(os.path.join(L.PEN, "objects.png"))
    with open(os.path.join(L.PEN, "objects.json"), "w") as f:
        json.dump({"image": "objects.png", "size": list(sheet.size), "objects": meta}, f, indent=1)


# ------------------------------------------------------------------ ambiente (96x64, ancora 48,60)
AW, AH, ACX, ABY = 96, 64, 48, 60


def a_borboleta(i):
    c = Canvas(AW, AH)
    t = i / 8
    x = int(ACX + 26 * math.sin(2 * math.pi * t))
    y = int(30 + 10 * math.sin(4 * math.pi * t))
    op = [".AA.A.AA.", "AAAAbAAAA", "AAAAbAAAA", ".AA.b.AA."]
    cl = ["...A.A...", "...AbA...", "...AbA...", "....b...."]
    bitmap(c, x - 4, y - 2, op if i % 2 == 0 else cl, {"A": "rose_light", "b": "outline"})
    return c


def a_vagalumes(i):
    c = Canvas(AW, AH)
    for k in range(5):
        ph = i / 8 + k * 0.21
        x = int(ACX + 34 * math.sin(2 * math.pi * (ph + k * 0.13)))
        y = int(30 + 18 * math.cos(2 * math.pi * (ph * 0.7 + k * 0.3)))
        if math.sin(2 * math.pi * (i / 8 + k * 0.4)) > -0.3:
            c.rect(x - 1, y - 1, x + 2, y + 2, "yellow", 60)
            c.px(x, y, "yellow")
    return c


def a_folhas(i):
    c = Canvas(AW, AH)
    for k in range(3):
        x = (14 + k * 30 + int(5 * math.sin(2 * math.pi * (i / 8 + k / 3)))) % AW
        y = (6 + k * 18 + i * 7) % AH
        col = "bush_light" if k != 1 else "yellow"
        c.rect(x, y, x + 3, y + 1, col)
        c.rect(x + 1, y + 1, x + 3, y + 2, "bush" if k != 1 else "wood_light")
    return c


def a_lanterna_on(i):
    c = Canvas(AW, AH)
    fl = [0, 1, 0, -1][i % 4]
    cx, cy = ACX + 4, ABY - 28
    c.paint(m_ell(c, cx - 9 - fl, cy - 9 - fl, 18 + 2 * fl, 18 + 2 * fl), "yellow", 30)
    c.paint(m_ell(c, cx - 5, cy - 5, 10, 10), "yellow", 55)
    return c


def build_ambient():
    rows = [("borboleta", "idle", 8, [a_borboleta(i) for i in range(8)]),
            ("vagalumes", "idle", 6, [a_vagalumes(i) for i in range(8)]),
            ("folhas", "idle", 6, [a_folhas(i) for i in range(8)]),
            ("lanterna", "off", 1, [Canvas(AW, AH)]),
            ("lanterna", "on", 6, [a_lanterna_on(i) for i in range(4)])]
    sheet = Image.new("RGBA", (8 * AW, len(rows) * AH), (0, 0, 0, 0))
    meta = {}
    for r, (name, an, fps, frs) in enumerate(rows):
        for i, fr in enumerate(frs):
            sheet.paste(fr.image(), (i * AW, r * AH))
        meta.setdefault(name, {"frame": [AW, AH], "anchor": [ACX, ABY], "anims": {}})["anims"][an] = {
            "row": r, "frames": len(frs), "fps": fps, "loop": True}
    sheet.save(os.path.join(L.PEN, "ambient.png"))
    with open(os.path.join(L.PEN, "ambient.json"), "w") as f:
        json.dump({"image": "ambient.png", "size": list(sheet.size), "objects": meta, "ambient": meta}, f, indent=1)


def write_pen():
    pen = {
        "bg": "pen_bg_dia.png",
        "bg_periods": {"amanhecer": "pen_bg_amanhecer.png", "dia": "pen_bg_dia.png",
                       "entardecer": "pen_bg_entardecer.png", "noite": "pen_bg_noite.png"},
        "period_tint": L.TINT,
        "lantern_on_periods": ["entardecer", "noite"],
        "walk_area": [48, 64, 656, 416],
        "panel": L.PANEL,
        "anchors": "x,y = centro-base do objeto (ancora no json do sheet); slots = offsets (dx,dy) do centro-base do gato; "
                   "layer floor = abaixo de todos os gatos, sorted = ordenar por y; gato em slot e desenhado SEMPRE depois do objeto. "
                   "zones.*.rect = [x,y,w,h]",
        "zones": L.ZONES,
        "ambient": L.AMBIENT,
    }
    with open(os.path.join(L.PEN, "pen.json"), "w") as f:
        json.dump(pen, f, indent=1)


if __name__ == "__main__":
    build_objects()
    build_ambient()
    write_pen()
    print("ok")
