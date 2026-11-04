"""T9.6: objects.png/json + ambient.png/json a partir de sprites gerados pelo Pixellab (assets/pen/_src96/obj_*.png).
Quadro 128x96, ancora (64,86). Animacoes por transformacao de script (squash/stretch/deslocamento).
Uso: python assets/tools/build_t96_objects.py"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
import build_t96_layout as L  # noqa: E402

ROOT = L.ROOT
PEN = os.path.join(ROOT, "assets", "pen")
W, H, CX, BY = 128, 96, 64, 86
SH = (42, 32, 48, 52)
BYOFF = {"casinha_filhote": 6}   # sprite alto: base 6 px abaixo da ancora para caber no quadro


def put_shadow(im, cx, base, w, ry=None):
    ry = ry or max(3, min(7, w // 9))
    d = ImageDraw.Draw(im)
    d.ellipse((cx - w // 2 - 1, base - ry - 1, cx + w // 2 + 1, base + ry - 1), fill=SH)


def place(kind, dx=0, dy=0, sx=1.0, sy=1.0, shadow=True, shadow_only=False, extra=None):
    """quadro com o sprite de `kind` assentado em (CX,BY); sx/sy esticam ancorando o centro-base."""
    s = L.sprite(kind)
    w, h = s.size
    nw, nh = max(1, round(w * sx)), max(1, round(h * sy))
    s2 = s if (nw, nh) == (w, h) else s.resize((nw, nh), Image.NEAREST)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    by = BY + BYOFF.get(kind, 0)
    if shadow:
        put_shadow(im, CX, by - 1, int(w * 0.92))
    if not shadow_only:
        im.alpha_composite(s2, (CX - nw // 2 + dx, by - nh + dy))
    if extra:
        extra(ImageDraw.Draw(im))
    return im


def blank():
    return Image.new("RGBA", (W, H), (0, 0, 0, 0))


# ---- camas
ENTER = [0.45, 0.95, 1.0, 0.85]
EXIT = [0.35, -0.2, 0.1, 0.0]


def bed(kind, p):
    return place(kind, sx=1 + 0.03 * p, sy=1 - 0.075 * p)


def bed_anims(kind):
    return [("idle", 1, 1, False, lambda i: bed(kind, 0.0)),
            ("enter", 4, 8, False, lambda i: bed(kind, ENTER[i])),
            ("exit", 4, 8, False, lambda i: bed(kind, EXIT[i]))]


# ---- brinquedos
def sn(t, k=1, ph=0.0):
    return math.sin(2 * math.pi * (t * k + ph))


def novelo(t, use):
    if not use:
        return place("novelo", dy=-round(max(0, sn(t)) * 1))
    return place("novelo", dx=round(5 * sn(t)), dy=-round(abs(sn(t, 2)) * 3), sx=1 + 0.08 * sn(t, 2), sy=1 - 0.08 * sn(t, 2))


def ratinho(t, use):
    if not use:
        return place("ratinho", dx=round(sn(t)), dy=0)
    return place("ratinho", dx=round(3 * sn(t)), dy=-round(abs(sn(t, 2)) * 5))


def arranhador(t, use):
    if not use:
        return place("arranhador")

    def chips(d):
        for k in range(3):
            ph = (t * 1.0 + k / 3) % 1.0
            x = CX + 12 + int(ph * 16) * (1 if k % 2 else -1) * 0 + (k - 1) * 7
            y = BY - 28 + int(ph * 26)
            if t < 0.9:
                d.point((x, y), fill=(222, 196, 140, int(255 * (1 - ph))))
                d.point((x + 1, y), fill=(190, 150, 100, int(255 * (1 - ph))))
    return place("arranhador", dx=round(1.4 * sn(t, 3)), extra=chips)


def bola(t, use):
    if not use:
        return place("bola_filhote")
    hgt = abs(sn(t / 2.0)) * 14
    sq = 1.0 - 0.18 * max(0, 1 - hgt / 2.0)
    im = place("bola_filhote", dy=-round(hgt), sx=1 + (1 - sq), sy=sq, shadow=False)
    sh = blank()
    put_shadow(sh, CX, BY - 1, int(L.sprite("bola_filhote").width * (0.95 - hgt / 40.0)), 2)
    sh.alpha_composite(im)
    return sh


def tunel(t, use):
    base = place("tunel_filhote")
    if not use:
        return base
    out = blank()
    src, dst = base.load(), out.load()
    s = L.sprite("tunel_filhote")
    x0 = CX - s.width // 2
    for x in range(W):
        u = (x - x0) / max(1.0, s.width)
        amp = max(0.0, math.sin(2 * math.pi * (u - t))) ** 2
        dy = -round(amp * 3)
        for y in range(H):
            p = src[x, y]
            if p[3]:
                ny = y + dy
                if 0 <= ny < H:
                    dst[x, ny] = p
    return out


def static(kind):
    return [("idle", 1, 1, True, lambda i: place(kind))]


def empty(kind):
    return [("idle", 1, 1, True, lambda i: blank())]


KINDS = {}
for k in ("cama_almofada", "cama_cesto", "cama_pedra", "cama_casal", "viveiro_cesto"):
    KINDS[k] = bed_anims(k)
KINDS["banco_arvore"] = empty("banco_arvore")
KINDS["casinha"] = empty("casinha")
KINDS["novelo"] = [("idle", 6, 6, True, lambda i: novelo(i / 6, False)), ("use", 8, 8, True, lambda i: novelo(i / 8, True))]
KINDS["ratinho"] = [("idle", 6, 6, True, lambda i: ratinho(i / 6, False)), ("use", 8, 8, True, lambda i: ratinho(i / 8, True))]
KINDS["arranhador"] = [("idle", 1, 1, True, lambda i: arranhador(0, False)), ("use", 6, 10, True, lambda i: arranhador(i / 6, True))]
KINDS["bola_filhote"] = [("idle", 1, 1, True, lambda i: bola(0, False)), ("use", 8, 10, True, lambda i: bola(i / 8, True))]
KINDS["tunel_filhote"] = [("idle", 1, 1, True, lambda i: tunel(0, False)), ("use", 6, 8, True, lambda i: tunel(i / 6, True))]
for k in ("tigela", "tigela_racao", "casinha_filhote"):
    KINDS[k] = static(k)
ORDER = ["cama_almofada", "cama_cesto", "cama_pedra", "cama_casal", "viveiro_cesto", "banco_arvore", "casinha",
         "novelo", "ratinho", "arranhador", "bola_filhote", "tunel_filhote", "tigela", "tigela_racao", "casinha_filhote"]


def build_objects():
    nrows = sum(len(KINDS[k]) for k in ORDER)
    sheet = Image.new("RGBA", (8 * W, nrows * H), (0, 0, 0, 0))
    meta, r = {}, 0
    for name in ORDER:
        anims = {}
        for an, n, fps, loop, fn in KINDS[name]:
            if an in ("enter", "exit"):
                loop = False
            for i in range(n):
                sheet.paste(fn(i), (i * W, r * H))
            anims[an] = {"row": r, "frames": n, "fps": fps, "loop": bool(loop) if an not in ("enter", "exit") else False}
            if an == "idle":
                anims[an]["loop"] = True
            r += 1
        meta[name] = {"frame": [W, H], "anchor": [CX, BY], "layer": L.LAYER[name], "anims": anims}
    sheet.save(os.path.join(PEN, "objects.png"))
    with open(os.path.join(PEN, "objects.json"), "w") as f:
        json.dump({"image": "objects.png", "size": list(sheet.size), "objects": meta}, f, indent=1)


# ---------------------------------------------------------------- ambiente (96x64, ancora 48,60)
AW, AH, ACX, ABY = 96, 64, 48, 60


def hx(c, a=255):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) + (a,)


def water_mask():
    bg = np.asarray(Image.open(os.path.join(PEN, "pen_bg_dia.png")).convert("RGB")).astype(int)
    r, g, b = bg[..., 0], bg[..., 1], bg[..., 2]
    m = (b > g + 6) & (b > r + 30)
    m[:340, :] = False
    m[470:, :] = False
    m[:, :190] = False
    m[:, 340:] = False
    ys, xs = np.nonzero(m)
    return m, (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))


def lagoa_frames(m, bb):
    cx, cy = (bb[0] + bb[2]) // 2, (bb[1] + bb[3]) // 2
    ox, oy = cx - ACX, cy - 34            # origem do quadro no mundo
    bg = Image.open(os.path.join(PEN, "pen_bg_dia.png")).convert("RGB")
    frames = []
    for f in range(8):
        t = f / 8
        im = Image.new("RGBA", (AW, AH), (0, 0, 0, 0))
        px = im.load()
        for y in range(AH):
            for x in range(AW):
                wx, wy = ox + x, oy + y
                if not (0 <= wx < 960 and 0 <= wy < 540) or not m[wy, wx]:
                    continue
                v = (x + 2 * y - t * 16) % 16
                if v < 2:
                    px[x, y] = (214, 238, 255, 95)
                elif v < 3:
                    px[x, y] = (255, 255, 255, 60)
        # anel que expande dentro da agua
        for k in range(2):
            ph = (t + k / 2) % 1.0
            rx, ry = 4 + ph * 22, 2 + ph * 10
            a = int(170 * (1 - ph))
            for ang in range(0, 360, 6):
                x = int(ACX - 8 + rx * math.cos(math.radians(ang)))
                y = int(34 + 3 + ry * math.sin(math.radians(ang)))
                wx, wy = ox + x, oy + y
                if 0 <= x < AW and 0 <= y < AH and m[wy, wx]:
                    px[x, y] = (230, 246, 255, a)
        frames.append(im)
    return frames, (cx, cy)


def lanterna_on(t):
    im = Image.new("RGBA", (AW, AH), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    fl = [0, 1, 0, -1][int(t * 4) % 4]
    d.ellipse((ACX - 9, ABY - 9 + fl, ACX + 9, ABY + 9 - fl), fill=(255, 200, 80, 40))
    d.ellipse((ACX - 5, ABY - 5, ACX + 5, ABY + 5), fill=(255, 220, 110, 80))
    d.rectangle((ACX - 1, ABY - 2, ACX, ABY - 1), fill=(255, 250, 200, 255))
    return im


def build_ambient():
    sys.path.insert(0, os.path.dirname(__file__))
    import build_t94_objects as t94
    m, bb = water_mask()
    lag, (wcx, wcy) = lagoa_frames(m, bb)
    rows = [("lagoa", "idle", 6, True, lag),
            ("borboleta", "idle", 8, True, [t94.amb(t94.a_borboleta, i / 8) for i in range(8)]),
            ("vagalumes", "idle", 6, True, [t94.amb(t94.a_vagalumes, i / 8) for i in range(8)]),
            ("folhas", "idle", 6, True, [t94.amb(t94.a_folhas, i / 8) for i in range(8)]),
            ("lanterna", "off", 1, True, [Image.new("RGBA", (AW, AH), (0, 0, 0, 0))]),
            ("lanterna", "on", 6, True, [lanterna_on(i / 4) for i in range(4)])]
    sheet = Image.new("RGBA", (8 * AW, len(rows) * AH), (0, 0, 0, 0))
    meta = {}
    for r, (name, an, fps, loop, frs) in enumerate(rows):
        for i, fr in enumerate(frs):
            sheet.paste(fr, (i * AW, r * AH))
        meta.setdefault(name, {"frame": [AW, AH], "anchor": [ACX, ABY], "anims": {}})["anims"][an] = {
            "row": r, "frames": len(frs), "fps": fps, "loop": loop}
    sheet.save(os.path.join(PEN, "ambient.png"))
    with open(os.path.join(PEN, "ambient.json"), "w") as f:
        json.dump({"image": "ambient.png", "size": list(sheet.size), "objects": meta, "ambient": meta}, f, indent=1)
    return (wcx, wcy + 26), bb


if __name__ == "__main__":
    build_objects()
    pos, bb = build_ambient()
    print("lagoa ambient", pos, "agua bbox", bb)
