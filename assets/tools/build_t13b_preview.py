"""T13.3b: confere paleta/alpha/tamanhos e gera reports/arte/preview_10a_areas.png (cena completa + detalhes + animacao)."""
from __future__ import annotations
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
LOCK = ROOT / "pen" / "lock"
CON = LOCK / "conteudo"
REP = ROOT.parent / "reports" / "arte"
pal = {tuple(int(v.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)) for v in json.loads((ROOT / "pen" / "palette_pen.json").read_text()).values()}
data = json.loads((LOCK / "conteudo.json").read_text(encoding="utf-8"))["areas"]
areas = {a["id"]: a for a in json.loads((LOCK / "areas.json").read_text(encoding="utf-8"))["areas"]}

bad = 0
for f in list(CON.glob("*.png")) + [LOCK / "unlock_anim.png"]:
    im = Image.open(f).convert("RGBA")
    cols = {p[:3] for p in im.getdata() if p[3]}
    if any(p[3] not in (0, 255) for p in im.getdata()) or cols - pal:
        bad += 1; print("FORA:", f.name, cols - pal)
for aid, d in data.items():
    assert d["rect"] == areas[aid]["rect"], aid
    assert Image.open(CON / d["floor"]).size == tuple(d["rect"][2:]), aid
assert Image.open(LOCK / "unlock_anim.png").size == (768, 96)
print("ok, fora da paleta:", bad)


def scene(unlocked, locked_ids=(), bgname="pen_bg_dia.png"):
    im = Image.open(ROOT / "pen" / bgname).convert("RGBA")
    for aid in unlocked:
        d = data[aid]
        im.alpha_composite(Image.open(CON / d["floor"]).convert("RGBA"), tuple(d["rect"][:2]))
    for aid in unlocked:
        for s in sorted(data[aid]["sorted"], key=lambda s: s["y"]):
            sp = Image.open(CON / s["file"]).convert("RGBA")
            im.alpha_composite(sp, (s["x"] - s["anchor"][0], s["y"] - s["anchor"][1]))
    for aid in locked_ids:
        a = areas[aid]
        im.alpha_composite(Image.open(LOCK / a["file"]).convert("RGBA"), tuple(a["rect"][:2]))
    return im


ids = ["jardim-lagoa", "patio-casais-nobre", "pomar"]
full = scene(ids)
night = scene(ids, bgname="pen_bg_noite.png")
tint = json.loads((ROOT / "pen" / "pen.json").read_text())["period_tint"]["noite"]
tn = Image.new("RGB", night.size, tuple(tint))
from PIL import ImageChops
night = Image.merge("RGBA", (*ImageChops.multiply(night.convert("RGB"), Image.new("RGB", night.size, (255, 255, 255))).split(), night.split()[3]))
tinted = scene(ids)
tinted = Image.merge("RGBA", (*ImageChops.multiply(tinted.convert("RGB"), tn).split(), tinted.split()[3]))

W = 960 * 2
canvas = Image.new("RGBA", (W, 540 + 540 * 0 + 3 * 288 + 20), (59, 42, 56, 255))
canvas.paste(full, (0, 0)); canvas.paste(tinted, (960, 0))
d = ImageDraw.Draw(canvas)
d.text((6, 4), "areas 4-6 abertas (dia)", fill=(255, 255, 255)); d.text((966, 4), "idem com tinta da noite (BLEND_MULT)", fill=(255, 255, 255))
y0 = 548
for i, aid in enumerate(ids):
    x, y, w, h = data[aid]["rect"]
    crop = full.crop((x, y, x + w, y + h)).resize((w * 2, h * 2), Image.NEAREST)
    canvas.paste(crop, (i * 400 + 8, y0))
sheet = Image.open(LOCK / "unlock_anim.png").convert("RGBA")
bgc = Image.new("RGBA", sheet.size, (121, 180, 90, 255)); bgc.alpha_composite(sheet)
canvas.paste(bgc.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST).crop((0, 0, 1536, 192)), (0, y0 + 300))
canvas.paste(bgc.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST).crop((0, 0, 0 + 1536, 192)), (0, y0 + 300))
canvas = canvas.crop((0, 0, W, y0 + 300 + 196))
REP.mkdir(parents=True, exist_ok=True)
canvas.convert("RGB").save(REP / "preview_10a_areas.png")
# lagoa animada: 4 quadros lado a lado
la = Image.open(CON / "jardim-lagoa_floor_anim.png").convert("RGBA")
bgl = Image.open(ROOT / "pen" / "pen_bg_dia.png").convert("RGBA").crop((48, 336, 240, 480))
strip = Image.new("RGBA", (192 * 4, 144))
for i in range(4):
    t = bgl.copy(); t.alpha_composite(la.crop((i * 192, 0, i * 192 + 192, 144))); strip.paste(t, (i * 192, 0))
strip.resize((192 * 4 * 2, 288), Image.NEAREST).convert("RGB").save(REP / "preview_10a_lagoa_anim.png")
print("previa salva")
