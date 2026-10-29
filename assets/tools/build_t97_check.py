"""T9.7: valida quintal: grade, objetos na zona/sem sobreposicao/fora dos caminhos, slots em chao livre, paleta PEN, tamanhos."""
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
import build_t97_bg as BG  # noqa: E402
import build_t97_layout as L  # noqa: E402
from build_t97_lib import pal_check  # noqa: E402

pen = json.load(open(os.path.join(L.PEN, "pen.json")))
bad = 0


def err(*a):
    global bad
    bad += 1
    print("PROBLEMA", *a)


def inter(a, b, tol=0):
    return a[0] < b[2] - tol and a[2] > b[0] + tol and a[1] < b[3] - tol and a[3] > b[1] + tol


paths = [tuple(r) for r in BG.path_rects()]
allobjs = []
for zn, z in pen["zones"].items():
    zx, zy, zw, zh = z["rect"]
    if any(v % 16 for v in z["rect"]):
        err("rect fora da grade 16", zn, z["rect"])
    for o in z["objects"]:
        w, h = L.SIZE[o["kind"]]
        b = (o["x"] - w // 2, o["y"] - h, o["x"] - w // 2 + w, o["y"])
        if not (zx <= b[0] and b[2] <= zx + zw and zy <= b[1] and b[3] <= zy + zh):
            err("objeto fora da zona/cortado", zn, o["kind"], b)
        for p in paths:
            if inter(b, p):
                err("objeto sobre caminho", o["kind"], b)
        for ob in allobjs:
            if inter(b, ob[1], 2):
                err("sobreposicao", o["kind"], ob[0])
        allobjs.append((o["kind"], b))
for zn, z in pen["zones"].items():
    zx, zy, zw, zh = z["rect"]
    for o in z["objects"]:
        for dx, dy in o["slots"]:
            sx, sy = o["x"] + dx, o["y"] + dy
            if not (zx <= sx <= zx + zw and zy <= sy <= zy + zh):
                err("slot fora da zona", o["kind"], sx, sy)
            if o["kind"] in ("casinha", "banco_arvore") and dy < -16:
                continue                                   # em cima do proprio objeto (telhado/assento)
            for p in paths:
                if p[0] <= sx <= p[2] and p[1] <= sy <= p[3]:
                    err("slot em caminho", o["kind"], sx, sy)
            for k, bb in allobjs:
                if bb[0] <= sx <= bb[2] and bb[1] + 4 < sy < bb[3] - 2 and not (bb[0] <= o["x"] <= bb[2] and bb[3] == o["y"]):
                    err("slot sobre outro objeto", o["kind"], k, sx, sy)
# paleta
for f in ("objects.png", "ambient.png"):
    im = np.asarray(Image.open(os.path.join(L.PEN, f)).convert("RGBA"))
    out = pal_check(im)
    if out:
        err("cores fora da paleta em", f, out[:5])
bgd = np.asarray(Image.open(os.path.join(L.PEN, "pen_bg_dia.png")).convert("RGB"))
out = pal_check(bgd)
if out:
    err("bg dia fora da paleta", out[:5])
for p in L.PERIODS:
    im = Image.open(os.path.join(L.PEN, f"pen_bg_{p}.png"))
    if im.size != (960, 540):
        err("tamanho bg", p, im.size)
    n = len({tuple(x) for x in np.asarray(im.convert("RGB")).reshape(-1, 3)})
    if n > 40:
        err("muitas cores no bg", p, n)
# sprites nao esticados: bbox do idle <= SIZE
oj = json.load(open(os.path.join(L.PEN, "objects.json")))
sh = Image.open(os.path.join(L.PEN, "objects.png")).convert("RGBA")
for k, m in oj["objects"].items():
    a = m["anims"]["idle"]
    f = sh.crop((0, a["row"] * 96, 128, a["row"] * 96 + 96))
    bb = f.getchannel("A").point(lambda v: 255 if v == 255 else 0).getbbox()
    w, h = L.SIZE[k]
    if bb and (bb[2] - bb[0] > w or bb[3] - bb[1] > h):
        err("sprite maior que o tamanho nativo", k, bb)
print("problemas:", bad)
sys.exit(1 if bad else 0)
