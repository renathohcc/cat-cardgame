"""T13.3: confere paleta/grade e gera reports/arte/preview_10a_bloqueio.png."""
from __future__ import annotations
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT / "pen" / "lock"
REP = ROOT.parent / "reports" / "arte"
pal = {tuple(int(v.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)) for v in json.loads((ROOT / "pen" / "palette_pen.json").read_text()).values()}
areas = json.loads((LOCK / "areas.json").read_text(encoding="utf-8"))
A = areas["areas"]
pen = json.loads((ROOT / "pen" / "pen.json").read_text(encoding="utf-8"))
walk = pen["walk_area"]

bad = 0
for f in list(LOCK.glob("*.png")) + list((LOCK / "icons").glob("*.png")):
    im = Image.open(f).convert("RGBA")
    cols = {p[:3] for p in im.getdata() if p[3]}
    if any(p[3] not in (0, 255) for p in im.getdata()) or cols - pal:
        bad += 1; print("FORA DA PALETA/ALPHA:", f.name, cols - pal)
for a in A:
    x, y, w, h = a["rect"]
    assert all(v % 16 == 0 for v in a["rect"]), a
    assert walk[0] <= x and walk[1] <= y and x + w <= walk[0] + walk[2] and y + h <= walk[1] + walk[3], a
    assert Image.open(LOCK / a["file"]).size == (w, h)
print("ok, fora da paleta:", bad)

bg = Image.open(ROOT / "pen" / "pen_bg_dia.png").convert("RGBA")
sg_f, sg_l = Image.open(LOCK / "placa_livre.png"), Image.open(LOCK / "placa_bloqueada.png")


def scene(locked, bgim=bg):
    im = bgim.copy()
    for a in A:
        if a["id"] in locked:
            im.alpha_composite(Image.open(LOCK / a["file"]), tuple(a["rect"][:2]))
            s = sg_l if a["id"] != locked[0] else sg_f
            ax, ay = a["anchor_sign"]
            im.alpha_composite(s, (ax - 16, ay - 32))
    return im


ids = [a["id"] for a in A]
tint = tuple(pen["period_tint"]["noite"])
night = Image.new("RGBA", bg.size, tint + (255,))
nbg = Image.open(ROOT / "pen" / "pen_bg_noite.png").convert("RGBA")
W, H = 960, 540
sheet = Image.new("RGBA", (W * 2, H * 3 + 160), (30, 24, 34, 255))
sheet.paste(scene(ids), (0, 0))
sheet.paste(scene(ids, nbg), (W, 0))
sheet.paste(scene(ids[1:]), (0, H))            # 1 desbloqueada
sheet.paste(scene(ids[3:]), (W, H))            # 3 desbloqueadas
sheet.paste(scene([]), (0, H * 2))             # 6 desbloqueadas
# animacao em quadros + icones + placas
an = Image.open(LOCK / "unlock_anim.png")
jm = json.loads((LOCK / "unlock_anim.json").read_text())
fw, fh = jm["frame_size"]
sheet.paste(Image.new("RGBA", (W, H), (79, 130, 80, 255)), (W, H * 2 + 0))
for i in range(jm["frames"]):
    f = an.crop((i * fw, 0, (i + 1) * fw, fh)).resize((fw * 2, fh * 2), Image.NEAREST)
    sheet.alpha_composite(f, (W + (i % 4) * 240 + 24, H * 2 + 40 + (i // 4) * 240))
ico = Image.open(LOCK / "icons.png")
ico = ico.resize((ico.width * 4, ico.height * 4), Image.NEAREST)
d = ImageDraw.Draw(sheet)
ybase = H * 3 + 10
sheet.paste(Image.new("RGBA", (W * 2, 150), (79, 130, 80, 255)), (0, H * 3))
sheet.alpha_composite(ico, (10, ybase))
sheet.alpha_composite(sg_f.resize((96, 96), Image.NEAREST), (700, ybase))
sheet.alpha_composite(sg_l.resize((96, 96), Image.NEAREST), (820, ybase))
d.text((10, 5), "todas bloqueadas (dia)", fill=(255, 255, 255, 255)); d.text((W + 10, 5), "todas bloqueadas (noite, fundo noturno)", fill=(255, 255, 255, 255))
d.text((10, H + 5), "1 desbloqueada", fill=(255, 255, 255, 255)); d.text((W + 10, H + 5), "3 desbloqueadas", fill=(255, 255, 255, 255))
d.text((10, H * 2 + 5), "6 desbloqueadas", fill=(255, 255, 255, 255)); d.text((W + 10, H * 2 + 5), "animacao 8 quadros", fill=(255, 255, 255, 255))
REP.mkdir(parents=True, exist_ok=True)
sheet.convert("RGB").save(REP / "preview_10a_bloqueio.png")
