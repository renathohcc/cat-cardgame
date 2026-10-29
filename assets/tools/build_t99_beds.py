"""T9.9: tapetes/almofadas planos (substituem as camas-tigela) desenhados por script na paleta PEN. Elipse simetrica,
perspectiva dos gatos de pen (3/4 alto), espessura pequena, brilho em cima-esquerda. Salva em assets/pen/_src99/.
Uso: python assets/tools/build_t99_beds.py"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
import build_t98_lib as B  # noqa: E402

PAL = dict(B.palette_rgb())
OUT_DIR = os.path.join(B.PEN, "_src99")
O = B.OUTLINE


def c(n):
    return PAL[n]


def rug(rx, ry, thick, rim, field, weave=False, puffs=0, extra=None, inner=0.76):
    """rim=(claro,medio,escuro); field=(claro,medio,escuro). Retorna RGBA (h,w,4) com contorno de 1 px."""
    pad = 2
    w, h = 2 * rx + 2 * pad, 2 * ry + thick + 2 * pad
    cx, cy = w / 2.0, pad + ry
    yy, xx = np.mgrid[0:h, 0:w]
    u, v = (xx + 0.5 - cx) / rx, (yy + 0.5 - cy) / ry
    r = np.hypot(u, v)
    r2 = np.hypot(u, (yy + 0.5 - cy - thick) / ry)
    face = r <= 1.0
    body = face | ((r2 <= 1.0) & (yy + 0.5 > cy))
    img = np.zeros((h, w, 4), np.uint8)
    side = body & ~face
    img[side] = (*rim[2], 255)
    rimm = face & (r > inner)
    light = -v                                      # luz so por altura: simetrico no eixo vertical
    tone = np.where(light > 0.38, 0, np.where(light < -0.42, 2, 1))
    for t in range(3):
        img[rimm & (tone == t)] = (*rim[t], 255)
    if weave:                                       # vime: tracos alternados
        wv = rimm & (((xx // 2 + (yy % 2) * 1 + yy // 2) % 2) == 0) & (tone == 1)
        img[wv] = (*rim[0], 255)
        wd = rimm & (((xx // 2 + yy // 2) % 2) == 1) & (tone == 2)
        img[wd] = (*rim[1], 255)
    if puffs:                                       # gomos da almofada: divisorias radiais escuras na borda
        ang = np.arctan2(v, u)
        k = (ang / (2 * np.pi) * puffs) % 1.0
        sep = rimm & (k < 0.5 / puffs * 2 * 0.08 + 0.03) & (r > inner + 0.05)
        img[sep] = (*rim[2], 255)
    fld = face & ~rimm
    img[fld] = (*field[1], 255)
    sh = fld & (light > 0.35) & (r > inner - 0.18)  # parede interna iluminada/sombreada
    img[fld & (v > 0.30) & (r > inner - 0.30)] = (*field[0], 255)     # fundo do forro iluminado
    img[fld & (v < -0.22) & (r > inner - 0.20)] = (*field[2], 255)    # parede interna em sombra
    for k in range(-2, 3):                                            # tufos simetricos no forro
        tx, ty = int(cx + k * rx * 0.2), int(cy + ry * 0.12 + (abs(k) % 2) * ry * 0.18)
        if fld[min(ty, h - 1), min(tx, w - 1)]:
            img[ty, tx] = (*field[2], 255)
    if extra:
        extra(img, cx, cy, rx, ry)
    # contorno externo
    al = img[..., 3] > 0
    p = np.pad(al, 1)
    nb = p[:-2, 1:-1] & p[2:, 1:-1] & p[1:-1, :-2] & p[1:-1, 2:]
    ring = np.pad(al, 1)
    out = np.zeros_like(al)
    for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (1, 1), (-1, 1), (1, -1)):
        out |= np.roll(np.roll(ring, dy, 0), dx, 1)[1:-1, 1:-1]
    edge = out & ~al
    img[edge] = (*O, 255)
    # linha de contorno entre a face e a lateral (ajuda a ler a espessura)
    img[(~face) & body & (np.roll(face, 1, 0)) ] = (*O, 255)
    ys, xs = np.nonzero(img[..., 3])
    return img[ys.min():ys.max() + 1, xs.min():xs.max() + 1].copy()


def ell(img, cx, cy, rx, ry, col, outline=True):
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot((xx + 0.5 - cx) / rx, (yy + 0.5 - cy) / ry)
    if outline:
        img[r <= 1.0] = (*O, 255)
        r = np.hypot((xx + 0.5 - cx) / (rx - 1), (yy + 0.5 - cy) / (ry - 1))
    img[r <= 1.0] = (*col, 255)


def heart(img, cx, cy):
    art = [".ooo...ooo.", "oLLRRoRRRRo", "oLRRRRRRRDo", "oRRRRRRRRDo", ".oRRRRRRDo.", "..oRRRRDo..", "...oRRDo...",
           "....oDo....", ".....o....."]
    cm = {"o": c("x3"), "L": c("x8"), "R": c("flower_red"), "D": c("x3")}
    for y, row in enumerate(art):
        for x, ch in enumerate(row):
            if ch in cm:
                img[int(cy) - 5 + y, int(cx) - 5 + x] = (*cm[ch], 255)


def pillow(img, cx, cy):
    ell(img, cx, cy, 8, 5, c("cream_light"))
    ell(img, cx, cy + 2, 5, 1.8, c("cream"), outline=False)


def casal_extra(img, cx, cy, rx, ry):
    pillow(img, cx - 24, cy - 2)
    pillow(img, cx + 24, cy - 2)
    heart(img, cx, cy - 2)


def viveiro_extra(img, cx, cy, rx, ry):
    ell(img, cx + 9, cy - 2, 6, 3.5, c("rose_light"))
    img[int(cy) - 3, int(cx) + 6:int(cx) + 11] = (*c("rose"), 255)


CREAM = (c("cream_light"), c("cream"), c("cream_dark"))
SPECS = {
    "tapete_teal": dict(rx=29, ry=15, thick=4, inner=0.76, rim=(c("teal_light"), c("teal"), c("teal_dark")), field=CREAM, puffs=10),
    "tapete_cesto": dict(rx=29, ry=15, thick=4, inner=0.76, rim=(c("wood_light"), c("x9"), c("wood")), field=CREAM, weave=True),
    "tapete_cinza": dict(rx=27, ry=14, thick=4, inner=0.76, rim=(c("stone_light"), c("stone"), c("stone_dark")), field=CREAM, puffs=9),
    "tapete_casal": dict(rx=42, ry=20, thick=5, rim=(c("x8"), c("rose"), c("rose_dark")), field=CREAM, puffs=16,
                         extra=casal_extra, inner=0.74),
    "tapete_viveiro": dict(rx=28, ry=13, thick=3, rim=(c("wood_light"), c("x9"), c("wood")),
                           field=(c("stone_light"), c("teal_light"), c("teal")), weave=True, extra=viveiro_extra),
}


def build():
    os.makedirs(OUT_DIR, exist_ok=True)
    out = {}
    for n, sp in SPECS.items():
        a = rug(**sp)
        Image.fromarray(a, "RGBA").save(os.path.join(OUT_DIR, n + ".png"))
        out[n] = a
    return out


if __name__ == "__main__":
    for n, a in build().items():
        print(n, a.shape[1], "x", a.shape[0])
