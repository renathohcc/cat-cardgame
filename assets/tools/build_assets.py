"""Organiza a arte definitiva: assets/cats/<raca>.png, camadas, pelagens, spritesheet + json e preview 4x.
Fontes: _proposta/A_48_capa.png (vira-lata) e _proposta2/ (escolhas, ver CHOSEN). Versoes antigas em _v1/.
Uso: python assets/tools/build_assets.py"""
import json
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parents[2]
CATS = ROOT / "assets/cats"; SRC = CATS / "_src"; LAY = CATS / "layers"; PREV = ROOT / "reports/arte"
BREEDS = [b["id"] for b in json.loads((ROOT / "data/breeds.json").read_text("utf-8"))["breeds"]]
OUTLINE = {(0x3b, 0x2a, 0x38), (0x2a, 0x1c, 0x2a)}
COATS = {  # so o vira-lata tem paleta conhecida (sombra, base, luz, padrao, peito)
    "cinza": ["#5f6878", "#8c95a6", "#b9c1cf", "#454c5c", "#e8ecf2"],
    "preto": ["#26222e", "#3c3646", "#585066", "#1a1720", "#6a6278"],
    "creme": ["#c9a77a", "#e6c99a", "#f6e3c2", "#a9835a", "#fff6e6"]}
VL = ["#b86a3a", "#d98f4e", "#f0b878", "#8f4a2c", "#f6e3c8"]
# Escolhas aprovadas (T7.1c): arquivo em _proposta2/ de cada raca. Sem quantizacao (reduce() fica disponivel, nao usada).
CHOSEN = {"siames": "siames_op2.png", "persa": "persa_op1.png", "sphynx": "sphynx_op1.png", "maine-coon": "maine-coon_op1.png"}
def h(s): return tuple(int(s[i:i + 2], 16) for i in (1, 3, 5))

def layers_generic(im):
    """Camadas por papel de cor: contorno / olhos(claros-amarelos-azuis) / resto = corpo."""
    out = {n: Image.new("RGBA", im.size, (0, 0, 0, 0)) for n in ("contorno", "corpo", "olhos")}
    for x in range(im.width):
        for y in range(im.height):
            p = im.getpixel((x, y))
            if not p[3]: continue
            c = p[:3]
            k = "contorno" if c in OUTLINE else "olhos" if (c == (255, 255, 255) or (c[2] > 200 and c[2] > c[0] + 40) or (c[0] > 240 and c[1] > 200 and c[2] < 120)) else "corpo"
            out[k].putpixel((x, y), p)
    return out

def layers_vl(im):
    spec = {"contorno": ["#3b2a38", "#2a1c2a"], "pelagem": VL[:3], "padrao": [VL[3]], "peito_focinho": [VL[4]],
            "nariz_orelha": ["#f09aa8"], "olhos": ["#ffd84a", "#ffffff"]}
    out = {}
    for n, cols in spec.items():
        s = {h(c) for c in cols}; l = Image.new("RGBA", im.size, (0, 0, 0, 0))
        for x in range(im.width):
            for y in range(im.height):
                p = im.getpixel((x, y))
                if p[3] and p[:3] in s: l.putpixel((x, y), p)
        out[n] = l
    return out

def recolor(im, coat):
    m = dict(zip([h(c) for c in VL], [h(c) for c in COATS[coat]])); o = im.copy()
    for x in range(im.width):
        for y in range(im.height):
            p = im.getpixel((x, y))
            if p[3] and p[:3] in m: o.putpixel((x, y), m[p[:3]] + (255,))
    return o

def reduce(im, n=14):
    """Limita a n cores (quantizacao local) mantendo alfa binario."""
    if len({q[:3] for q in im.getdata() if q[3]}) <= n: return im
    a = im.getchannel("A").point(lambda v: 255 if v > 127 else 0)
    q = im.convert("RGB").quantize(n, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert("RGB")
    o = q.convert("RGBA"); o.putalpha(a); return o

def main():
    LAY.mkdir(exist_ok=True); PREV.mkdir(parents=True, exist_ok=True)
    sprites = {}
    for b in BREEDS:
        src = CATS / "_proposta/A_48_capa.png" if b == "vira-lata" else CATS / "_proposta2" / CHOSEN[b]
        im = Image.open(src).convert("RGBA"); assert im.size == (48, 48), (b, im.size)
        im.save(CATS / f"{b}.png"); sprites[b] = im
        for n, l in (layers_vl(im) if b == "vira-lata" else layers_generic(im)).items(): l.save(LAY / f"{b}_{n}.png")
    cells = {b: sprites[b] for b in BREEDS}
    for c in COATS: cells[f"vira-lata_{c}"] = recolor(sprites["vira-lata"], c)
    for n, im in cells.items():
        if "_" in n and n.startswith("vira-lata_"): im.save(CATS / f"{n}.png")
    cols = 4; rows = -(-len(cells) // cols)
    sheet = Image.new("RGBA", (cols * 48, rows * 48), (0, 0, 0, 0)); meta = {}
    for i, (n, im) in enumerate(cells.items()):
        x, y = (i % cols) * 48, (i // cols) * 48; sheet.paste(im, (x, y)); meta[n] = {"x": x, "y": y, "w": 48, "h": 48}
    sheet.save(CATS / "spritesheet.png")
    (CATS / "spritesheet.json").write_text(json.dumps({"image": "spritesheet.png", "size": [sheet.width, sheet.height], "sprites": meta}, indent=2), "utf-8")
    S = 4; prev = Image.new("RGBA", (len(BREEDS) * 52 * S + 4 * S, 56 * S), (243, 233, 214, 255))
    for i, b in enumerate(BREEDS): prev.alpha_composite(sprites[b].resize((48 * S, 48 * S), Image.NEAREST), (4 * S + i * 52 * S, 4 * S))
    prev.save(PREV / "preview_racas_4x.png")

if __name__ == "__main__": main()
