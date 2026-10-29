"""T9.8: objects.png/json, ambient e pen.json do quintal com sprites do Pixellab (paleta PEN48, 1:1, sem resize).
Cada sprite limpo e posto no quadro 128x96 (ancora 64,86) com sombra de contato; animacoes por script (afundar 1 px,
respiro, saltinhos, tremor). Uso: python assets/tools/build_t98_objects.py"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
import build_t98_layout as L  # noqa: E402
import build_t98_lib as B  # noqa: E402
import build_t97_objects as O97  # noqa: E402  (ambiente: borboleta, vagalumes, folhas, lanterna)

FW, FH, CX, BY = 128, 96, 64, 86
SPR = {k: B.clean_sprite(s) for k, s in L.SRC.items()}


def shake_top(a, dx, split=0.55):
    """arranhador: parte de cima desliza dx px (tremor)."""
    out = a.copy()
    cut = int(a.shape[0] * split)
    top = np.roll(a[:cut], dx, axis=1)
    if dx > 0:
        top[:, :dx] = 0
    elif dx < 0:
        top[:, dx:] = 0
    out[:cut] = top
    return out


def squash(a, n):
    """afunda n px (remove n linhas na parte de cima do corpo; a base fica no chao). Sem resize."""
    if n <= 0:
        return a
    cut = int(a.shape[0] * 0.45)
    return np.concatenate([a[:cut - n], a[cut:]], 0)


def canvas():
    return np.zeros((FH, FW, 4), np.uint8)


def paste(dst, src, x, y):
    h, w = src.shape[:2]
    for yy in range(h):
        ty = y + yy
        if not 0 <= ty < dst.shape[0]:
            continue
        for xx in np.nonzero(src[yy, :, 3])[0]:
            tx = x + int(xx)
            if 0 <= tx < dst.shape[1]:
                dst[ty, tx] = src[yy, xx]


def contact_shadow(dst, w, dx=0):
    """elipse achatada (cor do contorno, alpha) sob a base, deslocada 1 px p/ baixo: o objeto 'senta' no chao."""
    sw = w + (8 if w > 24 else 2)
    sh = 8 if w > 24 else 5
    yy, xx = np.mgrid[0:FH, 0:FW]
    cy = BY - sh // 2 + 2
    m = ((xx + 0.5 - (CX + dx)) / (sw / 2.0)) ** 2 + ((yy + 0.5 - cy) / (sh / 2.0)) ** 2 <= 1.0
    dst[m] = (*B.OUTLINE, 110)
    if w > 24:
        m2 = ((xx + 0.5 - (CX + dx)) / ((sw + 6) / 2.0)) ** 2 + ((yy + 0.5 - cy) / ((sh + 3) / 2.0)) ** 2 <= 1.0
        dst[m2 & ~m] = (*B.OUTLINE, 52)


def frame(spr, dx=0, dy=0):
    f = canvas()
    h, w = spr.shape[:2]
    contact_shadow(f, w, dx // 2)
    paste(f, spr, CX - w // 2 + dx, BY - h + dy)
    return f


def sn(t, k=1):
    return math.sin(2 * math.pi * t * k)


def build_kinds():
    K = {}
    for k in ("cama_almofada", "cama_cesto", "cama_pedra", "cama_casal", "viveiro_cesto"):
        s = SPR[k]
        K[k] = [("idle", 1, 1, lambda i, s=s: frame(s)),
                ("enter", 4, 8, lambda i, s=s: frame(squash(s, [0, 1, 1, 1][i]))),
                ("exit", 4, 8, lambda i, s=s: frame(squash(s, [1, 0, 0, 0][i])))]
    for k in ("banco_arvore", "casinha", "casinha_filhote", "tigela", "tigela_racao"):
        K[k] = [("idle", 1, 1, lambda i, k=k: frame(SPR[k]))]
    K["novelo"] = [("idle", 6, 6, lambda i: frame(SPR["novelo"], dy=[0, 0, -1, -1, 0, 0][i])),
                   ("use", 8, 8, lambda i: frame(SPR["novelo"], dx=round(5 * sn(i / 8)),
                                                  dy=-round(abs(sn(i / 8, 2)) * 3)))]
    K["ratinho"] = [("idle", 6, 6, lambda i: frame(SPR["ratinho"], dy=[0, 0, -1, -1, 0, 0][i])),
                    ("use", 8, 8, lambda i: frame(SPR["ratinho"], dx=round(4 * sn(i / 8)),
                                                   dy=-round(abs(sn(i / 8, 2)) * 5)))]
    K["arranhador"] = [("idle", 1, 1, lambda i: frame(SPR["arranhador"])),
                       ("use", 6, 10, lambda i: frame(shake_top(SPR["arranhador"], [0, 1, 0, -1, 0, 1][i])))]
    K["bola_filhote"] = [("idle", 1, 1, lambda i: frame(SPR["bola_filhote"])),
                         ("use", 8, 10, lambda i: frame(SPR["bola_filhote"], dx=round(4 * sn(i / 8)),
                                                         dy=-round(abs(sn(i / 16)) * 12)))]
    K["tunel_filhote"] = [("idle", 1, 1, lambda i: frame(SPR["tunel_filhote"])),
                          ("use", 8, 8, lambda i: frame(SPR["tunel_filhote"], dx=[0, 1, 1, 0, 0, -1, -1, 0][i]))]
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
                sheet.paste(Image.fromarray(fn(i), "RGBA"), (i * FW, r * FH))
            loop = an not in ("enter", "exit")
            anims[an] = {"row": r, "frames": n, "fps": fps, "loop": loop}
            r += 1
        meta[name] = {"frame": [FW, FH], "anchor": [CX, BY], "layer": L.LAYER[name], "anims": anims}
    sheet.save(os.path.join(B.OUT, "objects.png"))
    with open(os.path.join(B.OUT, "objects.json"), "w") as f:
        json.dump({"image": "objects.png", "size": list(sheet.size), "objects": meta}, f, indent=1)


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
    with open(os.path.join(B.OUT, "pen.json"), "w") as f:
        json.dump(pen, f, indent=1)


if __name__ == "__main__":
    os.makedirs(B.OUT, exist_ok=True)
    O97.L.PEN = B.OUT
    build_objects()
    O97.build_ambient()
    write_pen()
    print("objetos ok")
