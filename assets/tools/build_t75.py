"""T7.5: spritesheets de specials/effects, icones de badge e conceitos de tabuleiro.
Fontes: assets/specials/_src, assets/effects/_src (Pixellab), icones desenhados aqui, assets/board/_proposta/*_raw.png (Pixellab 400x224).
Uso: python assets/tools/build_t75.py"""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
ROOT = Path(__file__).resolve().parents[2]
A = ROOT / "assets"; PREV = ROOT / "reports/arte"; BOARD = A / "board/_proposta"


def ids(f, key): return [e["id"] for e in json.loads((ROOT / "data" / f).read_text("utf-8"))[key]]


def binarize(im):
    im = im.convert("RGBA"); px = im.load()
    for x in range(im.width):
        for y in range(im.height):
            r, g, b, a = px[x, y]; px[x, y] = (r, g, b, 255) if a >= 128 else (0, 0, 0, 0)
    return im


def sheet(folder, names, cell, cols=4):
    rows = -(-len(names) // cols); s = Image.new("RGBA", (cols * cell, rows * cell), (0, 0, 0, 0)); meta = {}
    for i, n in enumerate(names):
        im = binarize(Image.open(A / folder / "_src" / f"{n}.png")); assert im.size == (cell, cell), n
        x, y = (i % cols) * cell, (i // cols) * cell; s.paste(im, (x, y)); meta[n] = {"x": x, "y": y, "w": cell, "h": cell}
        im.save(A / folder / f"{n}.png")
    s.save(A / folder / "spritesheet.png")
    (A / folder / "spritesheet.json").write_text(json.dumps({"image": "spritesheet.png", "size": list(s.size), "sprites": meta}, indent=2), "utf-8")
    return s


PAL = {"o": "#3b2a38", "w": "#ffffff", "R": "#e5484d", "r": "#a02838", "B": "#4a8fe0", "b": "#2a5aa8", "G": "#5ccb5f", "g": "#2f8f3a",
       "O": "#ff9a2e", "Y": "#ffd84a", "C": "#6fe0e8", "c": "#2fa0b8", "P": "#f09aa8", "K": "#8a8fa0", "k": "#5a5f70"}
ICONS = {  # 9x9: forma + cor distintas
    "provocar": ["ooooooooo", "oKwKKKkko", "oKwKBBkko", "oKKBBBkko", ".oKBBkko.", ".oKKBkko.", "..oKkko..", "...oko...", "....o...."],
    "investida": ["....o....", "....oo...", "ooooOoo..", "oYOOOOOo.", "oOOOOOOOo", "oYOOOOOo.", "ooooOoo..", "....oo...", "....o...."],
    "primeira-patada": ["oo.oo.oo.", "oRooRooRo", "oRRoRRoRR", ".oRRoRRoR", ".oRRoRRoR", "..oRRoRRo", "..oRoorRo", "...oo.oo.", "........."],
    "robusto": ["...ooo...", ".ooGoGoo.", "oGwGoGGGo", "oGGGGGGgo", "oGGGGGggo", ".oGGGggo.", "..oGGgo..", "...ogo...", "....o...."],
    "acao-dano": ["....o....", "o...o...o", ".oo.R.oo.", "..oRRRo..", "ooRRYRRoo", "..oRRRo..", ".oo.R.oo.", "o...o...o", "....o...."],
    "acao-cura": ["..ooooo..", "..oGwGo..", "..oGGGo..", "oooGGGooo", "oGwGGGGGo", "oGGGGGgGo", "oooGGGooo", "..ogGgo..", "..ooooo.."],
    "acao-buff_atk": ["....o....", "...oYo...", "..oYwYo..", ".oYYYYOo.", "oooOYOooo", "..oOYOo..", "..oOYOo..", "..oOOOo..", "..ooooo.."],
    "acao-comprar": ["..ooooo..", ".oCwwCCbo", ".oCwCCCbo", ".oCCCoCbo", ".oCCoCCbo", ".oCCCoCbo", ".oCCCCCbo", ".oCCCCCbo", "..ooooo.."],
    "acao-energia": ["..ooooo..", ".oCwBBBo.", "oCwBBBBbo", "oCBBBBBbo", ".oBBBBbo.", "..oBBbo..", "...oBo...", "....o....", "........."],
}


def claws():
    """Tres arranhoes diagonais vermelhos com contorno automatico."""
    im = Image.new("RGBA", (9, 9), (0, 0, 0, 0)); red = set()
    for x0, ln in ((8, 7), (5, 7), (2, 6)):   # cada risco desce 1 px para a esquerda a cada 2 linhas de altura
        for j in range(ln):
            red.add((x0 - j // 2, j + 1))
    for x, y in red:
        for dx, dy in ((-1, 0), (0, 1), (0, -1)):
            if True:
                q = (x + dx, y + dy)
                if 0 <= q[0] < 9 and 0 <= q[1] < 9 and q not in red: im.putpixel(q, (0x3b, 0x2a, 0x38, 255))
    for x, y in red: im.putpixel((x, y), (0xe5, 0x48, 0x4d, 255) if (x + y) % 3 else (0xff, 0x9a, 0x9a, 255))
    return im


def icon_img(rows):
    im = Image.new("RGBA", (9, 9), (0, 0, 0, 0))
    for y, r in enumerate(rows):
        assert len(r) == 9, (r, len(r))
        for x, ch in enumerate(r):
            if ch != ".": im.putpixel((x, y), tuple(int(PAL[ch][i:i + 2], 16) for i in (1, 3, 5)) + (255,))
    return im


def build_icons():
    (A / "icons").mkdir(exist_ok=True)
    names = list(ICONS); s = Image.new("RGBA", (9 * len(names), 9), (0, 0, 0, 0)); meta = {}
    s2 = Image.new("RGBA", (18 * len(names), 18), (0, 0, 0, 0)); meta2 = {}
    for i, n in enumerate(names):
        im = claws() if n == "primeira-patada" else icon_img(ICONS[n]); s.paste(im, (9 * i, 0)); meta[n] = {"x": 9 * i, "y": 0, "w": 9, "h": 9}
        s2.paste(im.resize((18, 18), Image.NEAREST), (18 * i, 0)); meta2[n] = {"x": 18 * i, "y": 0, "w": 18, "h": 18}
        im.save(A / "icons" / f"{n}.png")
    s.save(A / "icons/spritesheet.png"); s2.save(A / "icons/spritesheet_x2.png")
    (A / "icons/spritesheet.json").write_text(json.dumps({"image": "spritesheet.png", "size": list(s.size), "sprites": meta}, indent=2), "utf-8")
    (A / "icons/spritesheet_x2.json").write_text(json.dumps({"image": "spritesheet_x2.png", "size": list(s2.size), "sprites": meta2}, indent=2), "utf-8")
    return s


def contact(sheets, path, scale=4, bg=(243, 233, 214, 255)):
    w = max(s.width for s in sheets) * scale + 16; h = sum(s.height * scale + 8 for s in sheets) + 8
    c = Image.new("RGBA", (w, h), bg); y = 8
    for s in sheets:
        c.alpha_composite(s.resize((s.width * scale, s.height * scale), Image.NEAREST), (8, y)); y += s.height * scale + 8
    c.save(path)


def extend(raw, name):
    """400x224 -> 480x270 por espelhamento das bordas (mesma densidade de pixel dos sprites)."""
    a = np.array(Image.open(raw).convert("RGB")); a = np.pad(a, ((23, 23), (40, 40), (0, 0)), mode="edge")
    im = Image.fromarray(a); dk = Image.new("RGB", im.size, (12, 8, 16)); m = Image.new("L", im.size, 150)
    ImageDraw.Draw(m).rectangle((40, 23, 439, 246), fill=0); im = Image.composite(dk, im, m); im.save(BOARD / f"{name}_480x270.png"); return im


def plate(d, box, fill=(20, 14, 28, 110), line="#e8c25a"):
    d.rectangle(box, fill=fill, outline=line)


def mock(bg, name, accent):
    im = bg.convert("RGBA"); lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    f = ImageFont.load_default()
    d.rectangle((0, 0, 479, 269), outline=accent); d.rectangle((1, 1, 478, 268), outline="#3b2a38"); d.rectangle((2, 2, 477, 267), outline="#e8c25a")
    for cx, cy in ((4, 4), (475, 4), (4, 265), (475, 265)): d.ellipse((cx - 3, cy - 3, cx + 3, cy + 3), fill="#e8c25a", outline="#3b2a38")
    for row_y in (40, 106):
        for n in range(5): plate(d, (81 + n * 64, row_y, 81 + n * 64 + 61, row_y + 61))
    im.alpha_composite(lay); lay = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    sp = [binarize(Image.open(A / "specials" / f"{n}.png")) for n in ("trovao-amarelo", "pelo-de-aco", "velha-dos-novelos")]
    cats = [Image.open(A / "cats" / f"{n}.png").convert("RGBA") for n in ("persa", "vira-lata")]
    im.alpha_composite(sp[0], (81 + 7, 106 + 8)); im.alpha_composite(sp[1], (81 + 2 * 64 + 7, 106 + 8))
    im.alpha_composite(sp[2], (81 + 64 + 7, 40 + 8)); im.alpha_composite(cats[0], (81 + 3 * 64 + 7, 40 + 8))
    for (cy, cat) in ((2, cats[0]), (172, cats[1])):
        cx = 222
        d.ellipse((cx - 1, cy - 1, cx + 36, cy + 36), fill=(40, 28, 48, 255), outline="#e8c25a"); d.ellipse((cx, cy, cx + 35, cy + 35), outline="#3b2a38")
        small = cat.crop((6, 4, 42, 40)); lay.paste(small, (cx, cy), small)
        d.ellipse((cx - 17, cy + 10, cx - 1, cy + 26), fill="#6fe0e8", outline="#3b2a38"); d.text((cx - 12, cy + 14), "2", fill="#3b2a38", font=f)
        d.polygon([(cx + 40, cy + 14), (cx + 49, cy + 25), (cx + 40, cy + 36), (cx + 31, cy + 25)], fill="#e5484d", outline="#3b2a38"); d.text((cx + 36, cy + 20), "20", fill="white", font=f)
        d.rectangle((cx - 68, cy + 12, cx - 20, cy + 24), fill="#2a1c2a", outline="#e8c25a"); d.text((cx - 66, cy + 14), "Fifi" if cy < 100 else "Jogador", fill="white", font=f)
    for k in range(3): d.rectangle((14 + k, 132 - k, 46 + k, 150 - k), fill="#5a3a5a", outline="#e8c25a")
    d.text((22, 160), "12", fill="white", font=f)
    d.rectangle((14, 60, 40, 74), fill="#2a1c2a", outline="#e8c25a"); d.text((18, 62), "E:8", fill="white", font=f)
    d.rounded_rectangle((420, 100, 472, 140), radius=6, fill="#e8c25a", outline="#3b2a38"); d.rounded_rectangle((423, 103, 469, 137), radius=4, outline="#a06a20")
    d.text((430, 112), "FIM DE\n TURNO", fill="#3b2a38", font=f)
    d.rounded_rectangle((372, 244, 474, 264), radius=4, fill=(20, 14, 28, 200), outline="#e8c25a")
    for i in range(7):
        x = 378 + i * 14; on = i < 5
        d.polygon([(x + 5, 248), (x + 10, 254), (x + 5, 260), (x, 254)], fill="#6fe0e8" if on else "#3a3a50", outline="#3b2a38")
    d.text((378, 232), "ENERGIA 5/7", fill="white", font=f)
    for i in range(7):
        x = 50 + i * 38; d.rectangle((x, 214, x + 61, 276), fill="#f3e9d6", outline="#3b2a38"); d.rectangle((x + 3, 217, x + 58, 250), fill="#c9b48a")
    
    d.text((8, 8), "[proposta de layout]", fill="white", font=f)
    im.alpha_composite(lay); im.save(BOARD / f"mock_{name}.png"); im.save(PREV / f"preview_tabuleiro_{name}_mock.png")
    im.resize((960, 540), Image.NEAREST).save(PREV / f"preview_tabuleiro_{name}_mock_2x.png")


def main():
    PREV.mkdir(parents=True, exist_ok=True)
    s1 = sheet("specials", ids("specials.json", "specials"), 48)
    s2 = sheet("effects", ids("effects.json", "effects"), 48)
    s3 = build_icons()
    contact([s1], PREV / "preview_especiais_4x.png"); contact([s2], PREV / "preview_efeitos_4x.png")
    contact([s3], PREV / "preview_icones_8x.png", scale=8)
    for k, acc in (("jardim", "#2f5a3a"), ("taverna", "#6a3a20")):
        mock(extend(BOARD / f"{k}_raw.png", k), k, acc)
        Image.open(BOARD / f"{k}_raw.png").convert("RGB").resize((800, 448), Image.NEAREST).save(PREV / f"preview_tabuleiro_{k}_fundo.png")
    Image.open(BOARD / "circo_raw.png").convert("RGB").resize((800, 448), Image.NEAREST).save(PREV / "preview_tabuleiro_circo_fundo.png")


if __name__ == "__main__": main()
