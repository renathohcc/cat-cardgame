"""T9.9: previews antes/depois (postes, camas->tapetes, cena). Uso: python assets/tools/build_t99_preview.py"""
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
import json  # noqa: E402
import build_t98_lib as B  # noqa: E402

PEN, V6, REP = B.PEN, os.path.join(B.PEN, "_v6"), os.path.join(B.ROOT, "reports", "arte")


def pair(a, b, scale, name, la="antes (T9.8)", lb="depois (T9.9)"):
    w = max(a.width, b.width)
    im = Image.new("RGB", (w * scale * 2 + 30, max(a.height, b.height) * scale + 20), (30, 26, 38))
    im.paste(a.resize((a.width * scale, a.height * scale), Image.NEAREST), (10, 16))
    im.paste(b.resize((b.width * scale, b.height * scale), Image.NEAREST), (w * scale + 20, 16))
    d = ImageDraw.Draw(im)
    d.text((10, 2), la, fill=(255, 255, 255))
    d.text((w * scale + 20, 2), lb, fill=(255, 255, 255))
    im.save(os.path.join(REP, name))


def beds(root):
    oj = json.load(open(os.path.join(root, "objects.json")))
    sh = Image.open(os.path.join(root, "objects.png")).convert("RGBA")
    out = Image.new("RGBA", (5 * 100, 70), (121, 180, 90, 255))
    for i, k in enumerate(("cama_almofada", "cama_cesto", "cama_pedra", "cama_casal", "viveiro_cesto")):
        r = oj["objects"][k]["anims"]["idle"]["row"]
        f = sh.crop((0, r * 96, 128, r * 96 + 96)).crop((14, 26, 114, 96))
        out.paste(f, (i * 100 - (14 if i == 3 else 0) * 0, 0), f)
    return out.convert("RGB")


a = Image.open(os.path.join(V6, "pen_bg_dia.png")).convert("RGB")
b = Image.open(os.path.join(PEN, "pen_bg_dia.png")).convert("RGB")
box = (420, 200, 640, 320)
pair(a.crop(box), b.crop(box), 3, "preview_pen_v7_postes.png")
box2 = (0, 380, 300, 520)
pair(a.crop(box2), b.crop(box2), 2, "preview_pen_v7_cerca.png")
pair(beds(V6), beds(PEN), 3, "preview_pen_v7_camas.png", "camas T9.8", "tapetes T9.9")
