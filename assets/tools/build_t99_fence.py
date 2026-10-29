"""T9.9: cerca nova (postes, trilhos continuos, postes de portao) desenhada por script na paleta PEN. Sem Pixellab.
Uso: importado por build_t99_bg.py; `python build_t99_fence.py` salva preview 6x em reports/arte/preview_pen_v7_postes_novo.png"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
import build_t98_lib as B  # noqa: E402

PAL = dict(B.palette_rgb())
COL = {"o": PAL["outline"], "L": PAL["wood_light"], "M": PAL["wood"], "D": PAL["wood_dark"], "E": PAL["x9"],
       "r": PAL["stone_light"], "s": PAL["stone"], "S": PAL["stone_dark"], "t": PAL["stone_light"],
       "R": PAL["rose"], "l": PAL["rose_light"], "d": PAL["rose_dark"], "y": PAL["cream_light"]}
T = 16


def from_art(rows):
    h, w = len(rows), max(len(r) for r in rows)
    a = np.zeros((h, w, 4), np.uint8)
    for y, r in enumerate(rows):
        for x, ch in enumerate(r):
            if ch in COL:
                a[y, x] = (*COL[ch], 255)
    return a


# poste da cerca 7x22: capuz abaulado com colar, fuste com veios e pregos, pe com base mais escura
POST = from_art([
    "..ooo..",
    ".oLLMo.",
    "oLLMMDo",
    "oLMMMDo",
    "ooooooo",
    "oLLMMDo",
    "oLMMMDo",
    "oLMDMDo",
    "oLMrMDo",
    "oLMMMDo",
    "oLMMDDo",
    "oLDMMDo",
    "oLMMMDo",
    "oLMMMDo",
    "oLMrMDo",
    "oLMMMDo",
    "oLMMDDo",
    "oLMMMDo",
    "oLMDMDo",
    "oLMMMDo",
    "oMMDDDo",
    "ooooooo",
])
POST_RAILS = (8, 14)        # linhas (no poste) onde ficam os trilhos: pregos ficam em 8 e 14
RAIL_ROWS = ["o", "L", "M", "D", "o"]      # trilho 5 px, com realce em cima e sombra embaixo

# poste de portao 9x32 + braco e coracao pendurado (sprite 21x32; poste nas colunas 6..14, centro 10)
_G = ["...ooo...", ".ooLLMoo.", ".oLLMMDo.", ".oLMMDDo.", "..ooooo..", "oooooooo" + "o", "oLLMMMDDo", "ooooooooo",
      "oLMMMMMDo", "oLMMDMMDo", "oLMMMMMDo", "oLMMMMMDo", "oLMMMMDDo", "oLMMMMMDo", "oLMDMMMDo", "ossssssso",
      "oSSSSSSSo", "oLMMMMMDo", "oLMMMMMDo", "oLMMDMMDo", "oLMMMMMDo", "oLMMMMMDo", "oLMMMMDDo", "oLMDMMMDo",
      "ossssssso", "oSSSSSSSo", "oLMMMMMDo", "oLMMMMMDo", "oLMMMMDDo", "oLLMMMMDo", "oMMMDDDDo", "ooooooooo"]
_ARM = {9: "ooooooo", 10: "oLLLLLo", 11: "oMMMMMo", 12: "ooooooo", 13: "...o...", 14: ".oo.oo.", 15: "olRoRRo",
        16: "oRRRRDo", 17: ".oRRDo.", 18: "..odo..", 19: "...o..."}
GATE = from_art(["......" + r + _ARM.get(i, "") for i, r in enumerate(_G)])
GATE_CX = 10

# grama/terra/caminho: um passo mais escuro (sombra de contato simples, so cores da paleta)
_DARKEN = {"grass": "grass_dark", "grass_light": "grass", "dirt": "dirt_dark", "dirt_light": "dirt",
           "path": "path_dark", "path_light": "path", "dirt_dark": "dirt_dark", "grass_dark": "grass_dark",
           "path_dark": "path_dark"}
DARK = {PAL[k]: PAL[v] for k, v in _DARKEN.items()}


def shade(c, x0, x1, y):
    """escurece um passo os pixels do chao (so os da paleta de terreno) em [x0,x1) na linha y."""
    if not 0 <= y < c.shape[0]:
        return
    for x in range(max(0, x0), min(c.shape[1], x1)):
        t = tuple(int(v) for v in c[y, x, :3])
        if t in DARK:
            c[y, x, :3] = DARK[t]


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


def post_shadow(c, cx, yfoot, w):
    shade(c, cx - w // 2 - 2, cx + w // 2 + 3, yfoot + 1)
    shade(c, cx - w // 2, cx + w // 2 + 2, yfoot + 2)


def rails_h(c, x0, x1, yfoot):
    """dois trilhos continuos [x0,x1), alinhados aos pregos do poste; sombra de contato 1 px corrida embaixo."""
    top = yfoot - POST.shape[0] + 1
    for r0 in POST_RAILS:
        for k, ch in enumerate(RAIL_ROWS):
            y = top + r0 - 2 + k
            c[y, x0:x1] = (*COL[ch], 255)
    shade(c, x0, x1, yfoot + 1)


def hpost(c, cx, yfoot):
    post_shadow(c, cx, yfoot, POST.shape[1])
    paste(c, POST, cx - POST.shape[1] // 2, yfoot - POST.shape[0] + 1)


def hrun(c, xa, xb, yfoot):
    """trilhos continuos entre os centros de poste xa..xb; um poste a cada ~32 px (as pontas ficam sob poste de canto/portao)."""
    rails_h(c, xa, xb + 1, yfoot)
    n = max(1, round((xb - xa) / 32))
    for i in range(n + 1):
        hpost(c, xa + round(i * (xb - xa) / n), yfoot)


# vertical: tabua continua (visao quase de cima) + postes curtos (capuz e fuste) a cada ~40 px
VPOST = from_art([
    "..ooo..",
    ".oLLMo.",
    "oLLMMDo",
    "oLMMMDo",
    "ooooooo",
    "oLMrMDo",
    "oLMMMDo",
    "oMMDDDo",
    "ooooooo",
])
PLANK = ["oLMDo"] * 1


def vrun(c, cx, y0, y1):
    n = y1 - y0
    if n <= 0:
        return
    for y in range(y0, y1):
        for k, ch in enumerate("oLMDo"):
            c[y, cx - 2 + k] = (*COL[ch], 255)
    # veio da tabua a cada 9 px
    for y in range(y0 + 4, y1, 9):
        c[y, cx] = (*COL["D"], 255)
    k = max(1, round(n / 40))
    for i in range(k + 1):
        yb = y0 + VPOST.shape[0] + round(i * (n - VPOST.shape[0] - 1) / k)
        post_shadow(c, cx, yb, 7)
        paste(c, VPOST, cx - 3, yb - VPOST.shape[0] + 1)


def gate_post(c, cx, yfoot, flip=False):
    g = GATE[:, ::-1] if flip else GATE
    post_shadow(c, cx, yfoot, 11)
    paste(c, g, cx - (g.shape[1] - 1 - GATE_CX if flip else GATE_CX), yfoot - g.shape[0] + 1)


def draw_fences(c, L):
    gates = []
    for zone, (c0, r0, c1, r1) in L.RINGS.items():
        side, g0 = L.GATES[zone]
        gl, gr = g0 * T - 12, (g0 + 2) * T + 12
        for edge, row in (("N", r0), ("S", r1)):
            yb = row * T + 15
            xa, xb = c0 * T + 8, c1 * T + 8
            if side == edge:
                hrun(c, xa, gl, yb)
                hrun(c, gr, xb, yb)
                gates.append((gl, yb, False))
                gates.append((gr, yb, True))
            else:
                hrun(c, xa, xb, yb)
        for edge, col in (("W", c0), ("E", c1)):
            cx = col * T + 8
            ya, yb2 = r0 * T + 10, r1 * T + 14
            if side == edge:
                vrun(c, cx, ya, gl + 10)
                vrun(c, cx, gr - 8, yb2)
                gates.append((cx, gl + 8, edge == "E"))
                gates.append((cx, gr + 8, edge == "E"))
            else:
                vrun(c, cx, ya, yb2)
    for zone, (c0, r0, c1, r1) in L.RINGS.items():
        for col in (c0, c1):
            for row in (r0, r1):
                hpost(c, col * T + 8, row * T + 15)
    for cx, yb, flip in sorted(gates, key=lambda g: g[1]):
        gate_post(c, cx, yb, flip)


