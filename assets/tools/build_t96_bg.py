"""T9.6: fundo do quintal a partir de blocos gerados pelo Pixellab (assets/pen/_src96/*.png).
Monta 960x540 (esquerda adultos 448x540, casais 288x272, filhotes 288x272, floresta no painel),
troca os portoes por versoes maiores (objetos Pixellab) e gera os 4 periodos por color-grading.
Uso: python assets/tools/build_t96_bg.py"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
import build_t96_layout as L  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PEN = os.path.join(ROOT, "assets", "pen")
SRC = os.path.join(PEN, "_src96")
W, H = 960, 540


def load(name):
    return Image.open(os.path.join(SRC, name)).convert("RGBA")


def paste_obj(img, name, cx, base_y):
    """cola um objeto Pixellab (quadro com margem transparente) pelo centro-base da bbox."""
    o = load(name)
    o = o.crop(o.getbbox())
    img.alpha_composite(o, (cx - o.width // 2, base_y - o.height))


def compose():
    img = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    img.alpha_composite(load("left.png"), (0, 0))
    img.alpha_composite(load("casais.png"), (448, 0))
    img.alpha_composite(load("filh.png"), (448, 268))
    forest = load("forest.png")
    img.alpha_composite(forest.crop((0, 0, W - 736, H)), (736, 0))
    for name, (cx, by) in L.GATES.items():
        paste_obj(img, name, cx, by)
    return img.convert("RGB")


GRADE = {"dia": (1.0, 1.0, 1.0, (0, 0, 0)), "amanhecer": (0.85, 1.0, 1.05, (0.05, 0.02, 0.03)),
         "entardecer": (0.7, 0.95, 1.0, (0.06, 0.0, 0.05)), "noite": (0.5, 0.8, 1.25, (0.03, 0.045, 0.12))}


def glow(out, period):
    if period not in ("entardecer", "noite"):
        return out
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    k = 0.5 if period == "noite" else 0.3
    for (x, y) in L.LAMPS:
        d2 = ((xx - x) ** 2 + (yy - y) ** 2) / (46.0 ** 2)
        g = np.exp(-d2)[..., None] * k
        out = out + g * np.array([1.0, 0.72, 0.25], np.float32) * (1 - out * 0.5)
    return out


def grade(img, period):
    a = np.asarray(img.convert("RGB"), np.float32) / 255.0
    sat, gam, gain, lift = GRADE[period]
    lum = (a * np.array([0.3, 0.59, 0.11], np.float32)).sum(-1, keepdims=True)
    a = lum + (a - lum) * sat
    a = np.clip(a, 0, 1) ** gam * gain
    t = np.array(L.TINT[period], np.float32) / 255.0
    out = a * t + np.array(lift, np.float32) * (1 - a)
    yy = np.linspace(0, 1, H)[:, None, None]
    xx = np.linspace(0, 1, W)[None, :, None]
    if period == "amanhecer":
        out = out + np.array([0.08, 0.03, 0.0]) * (1 - yy) + np.array([0.06, 0.03, 0.0]) * xx
    elif period == "entardecer":
        out = out + np.array([0.08, 0.02, -0.02]) * (1 - xx) + np.array([0.0, 0.0, 0.04]) * yy
    out = glow(out, period)
    out = np.clip(out, 0, 1)
    f = np.clip((xx - 728 / W) / (24 / W), 0, 1)
    out = out * (1 - f * 0.5)          # painel de botoes (x>=736) escurecido
    return Image.fromarray((out * 255).astype(np.uint8), "RGB")


def main():
    base = compose()
    names = {"dia": "pen_bg_dia.png", "amanhecer": "pen_bg_amanhecer.png",
             "entardecer": "pen_bg_entardecer.png", "noite": "pen_bg_noite.png"}
    for per, fn in names.items():
        grade(base, per).save(os.path.join(PEN, fn))
    base.save(os.path.join(SRC, "_compose_raw.png"))
    print("bg ok")


if __name__ == "__main__":
    main()
