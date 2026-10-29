"""T8.4: fonte bitmap Chaoscats a partir do atlas Pixellab (create_font, 16px, Bold).
Adiciona acentos pt-BR, espaco e alguns simbolos desenhados por script.
Saidas: assets/fonts/chaoscats_16.png|json, chaoscats_32.png|json (2x), preview.
Uso: python assets/tools/build_t84_font.py
"""
import json
import os
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FONTS = os.path.join(ROOT, "assets", "fonts")
PREV = os.path.join(ROOT, "reports", "arte")
ORDER = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz.,!?:;'\"-+()0123456789/%*=_$"
CELL, BASE = 16, 14  # altura da celula; ultima linha da linha de base
GAP = 2  # espaco entre glifos
SPACE = 6


def load_atlas():
    im = Image.open(os.path.join(FONTS, "_src", "atlas.png")).convert("RGBA")
    g = {}
    for i, c in enumerate(ORDER):
        cell = im.crop(((i % 8) * 16, (i // 8) * 16, (i % 8) * 16 + 16, (i // 8) * 16 + 16))
        a = cell.getchannel("A")
        w = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        w.paste((255, 255, 255, 255), mask=a.point(lambda v: 255 if v > 127 else 0))
        g[c] = w
    return g


def bbox_x(img):
    b = img.getchannel("A").getbbox()
    return b[0], b[2]


def put(img, pts):
    px = img.load()
    for x, y in pts:
        if 0 <= x < 16 and 0 <= y < 16:
            px[x, y] = (255, 255, 255, 255)


def accent_pts(kind, c0, y0):
    """Pontos do acento; c0 = coluna do centro (par c0,c0+1); y0 = linha do topo."""
    c1 = c0 + 1
    if kind == "acute":
        rows = [(c1 + 1, c1 + 2), (c0, c1), (c0 - 1, c0)]
    elif kind == "grave":
        rows = [(c0 - 1, c0), (c0, c1), (c1 + 1, c1 + 2)][::-1]
        rows = [(c0 - 1, c0), (c0, c1), (c1, c1 + 1)]
        rows = [(c0 - 1, c0), (c0, c1), (c1 + 1, c1 + 2)]
        rows = [(c0 - 1, c0), (c0, c1), (c1, c1 + 1)]
    elif kind == "circ":
        rows = [(c0, c1), (c0 - 1, c1 + 1)]
        rows = [(c0, c1), (c0 - 1, c0 - 1, c1 + 1, c1 + 1)]
    elif kind == "tilde":
        rows = [(c0 - 2, c0 - 1, c1 + 2), (c0, c1)]
        rows = [(c0, c1), (c0 - 2, c0 - 1, c1 + 1, c1 + 2)]
    elif kind == "uml":
        rows = [(c0 - 1, c0 - 1 + 0, c1 + 1, c1 + 2), (c0 - 1, c0, c1 + 1, c1 + 2)]
        rows = [(c0 - 1, c0, c1 + 1, c1 + 2)] * 2
    else:
        rows = []
    return [(x, y0 + r) for r, xs in enumerate(rows) for x in xs]


def tilde_pts(c0, y0):
    c1 = c0 + 1
    return [(c0 - 2, y0 + 1), (c0 - 1, y0), (c0, y0), (c1, y0 + 1), (c1 + 1, y0 + 1),
            (c0 - 2, y0 + 2 - 1), (c1 + 2, y0)]


def compose(base, kind, top_row, glyph):
    """Cola acento sobre o glifo base. top_row = linha do topo do acento."""
    img = base.copy()
    x0, x1 = bbox_x(base)
    c0 = (x0 + x1) // 2 - 1
    if kind == "tilde":
        pts = [(c0 - 2, top_row + 1), (c0 - 1, top_row), (c0, top_row), (c0 + 1, top_row + 1),
               (c0 + 2, top_row + 1), (c0 - 2, top_row + 2), (c0 + 3, top_row)]
        pts = [(c0 - 2, top_row + 1), (c0 - 2, top_row + 2), (c0 - 1, top_row), (c0, top_row),
               (c0 + 1, top_row + 1), (c0 + 2, top_row + 1), (c0 + 2, top_row)]
        pts = [(c0 - 2, top_row + 1), (c0 - 1, top_row), (c0, top_row), (c0 + 1, top_row + 1),
               (c0 + 2, top_row + 1), (c0 - 2, top_row), (c0 + 3, top_row)]
        pts = [(c0 - 2, top_row + 1), (c0 - 1, top_row), (c0, top_row), (c0 + 1, top_row + 1),
               (c0 + 2, top_row + 1), (c0 - 1, top_row + 1), (c0 + 1, top_row), (c0 + 2, top_row)]
    elif kind == "cedilla":
        pts = [(c0, 14), (c0 + 1, 14), (c0 + 1, 15), (c0 - 1, 15), (c0, 15)]
    else:
        pts = accent_pts(kind, c0, top_row)
    put(img, pts)
    return img


def dotless_i(base):
    img = base.copy()
    px = img.load()
    for y in range(0, 6):
        for x in range(16):
            px[x, y] = (0, 0, 0, 0)
    return img


def extra_symbols():
    s = {}

    def mk(rows, ox=0):
        im = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
        px = im.load()
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch == "#":
                    px[x + ox, y] = (255, 255, 255, 255)
        return im

    s["["] = mk(["", "", "", "  ####", "  ##", "  ##", "  ##", "  ##", "  ##", "  ##", "  ##", "  ##", "  ##", "  ##", "  ####"][0:15], 4)
    s["]"] = mk(["", "", "", "####", "  ##", "  ##", "  ##", "  ##", "  ##", "  ##", "  ##", "  ##", "  ##", "  ##", "####"], 4)
    s["<"] = mk(["", "", "", "", "", "      ##", "    ##", "  ##", "##", "  ##", "    ##", "      ##"], 3)
    s[">"] = mk(["", "", "", "", "", "##", "  ##", "    ##", "      ##", "    ##", "  ##", "##"], 3)
    s["|"] = mk(["", "", "", "##", "##", "##", "##", "##", "##", "##", "##", "##", "##", "##", "##"], 6)
    s["×"] = mk(["", "", "", "", "", "##  ##", "####", "##", "####", "##  ##"][:5] + ["  ##", "  ##", "####", "##  ##"][0:0], 4)
    s["×"] = mk(["", "", "", "", "", "", "##    ##", "  ####", "  ##", "  ####", "##    ##"], 3)
    s["→"] = mk(["", "", "", "", "", "", "      ##", "        ##", "##########", "        ##", "      ##"], 2)
    s["·"] = mk(["", "", "", "", "", "", "", "##", "##"], 6)
    s["•"] = mk(["", "", "", "", "", "", "  ####", "######", "######", "  ####"], 4)
    return s


def build_glyphs():
    g = load_atlas()
    out = dict(g)
    caps_acc = {"Á": ("A", "acute"), "À": ("A", "grave"), "Â": ("A", "circ"),
                "Ã": ("A", "tilde"), "É": ("E", "acute"), "Ê": ("E", "circ"),
                "Í": ("I", "acute"), "Ó": ("O", "acute"), "Ô": ("O", "circ"),
                "Õ": ("O", "tilde"), "Ú": ("U", "acute"), "Ü": ("U", "uml"),
                "Ç": ("C", "cedilla"), "Ñ": ("N", "tilde"),
                "Ï": ("I", "uml"), "È": ("E", "grave")}
    low_acc = {"á": ("a", "acute"), "à": ("a", "grave"), "â": ("a", "circ"),
               "ã": ("a", "tilde"), "é": ("e", "acute"), "ê": ("e", "circ"),
               "í": ("i", "acute"), "ó": ("o", "acute"), "ô": ("o", "circ"),
               "õ": ("o", "tilde"), "ú": ("u", "acute"), "ü": ("u", "uml"),
               "ç": ("c", "cedilla"), "ñ": ("n", "tilde"),
               "ï": ("i", "uml"), "è": ("e", "grave")}
    for ch, (b, k) in caps_acc.items():
        out[ch] = compose(g[b], k, 0, ch)
    for ch, (b, k) in low_acc.items():
        base = dotless_i(g["i"]) if b == "i" else g[b]
        out[ch] = compose(base, k, 2, ch)
    out.update(extra_symbols())
    return out


def pack(glyphs):
    W = 512
    x = y = 0
    sheet = Image.new("RGBA", (W, 16 * 8), (0, 0, 0, 0))
    meta = {}
    for ch, im in glyphs.items():
        x0, x1 = bbox_x(im)
        w = x1 - x0
        if x + w + 1 > W:
            x = 0
            y += 16
        sheet.alpha_composite(im.crop((x0, 0, x1, 16)), (x, y))
        meta[ch] = {"x": x, "y": y, "w": w, "h": 16, "adv": w + GAP}
        x += w + 1
    sheet = sheet.crop((0, 0, W, y + 16))
    return sheet, meta


def write(sheet, meta, scale, name):
    if scale != 1:
        sheet = sheet.resize((sheet.width * scale, sheet.height * scale), Image.NEAREST)
        meta = {c: {k: v * scale for k, v in m.items()} for c, m in meta.items()}
    sheet.save(os.path.join(FONTS, name + ".png"))
    data = {"image": name + ".png", "cell_height": CELL * scale, "baseline": (BASE + 1) * scale,
            "space": SPACE * scale, "scale": scale, "color": "branco (use BLEND_RGBA_MULT para tingir)",
            "glyphs": meta}
    with open(os.path.join(FONTS, name + ".json"), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    return sheet, data


def render(sheet, data, text, color=(255, 255, 255)):
    sp = data["space"]
    w = sum(data["glyphs"][c]["adv"] if c in data["glyphs"] else sp for c in text)
    out = Image.new("RGBA", (max(w, 1), data["cell_height"]), (0, 0, 0, 0))
    x = 0
    tint = Image.new("RGBA", sheet.size, color + (255,))
    colored = Image.composite(tint, Image.new("RGBA", sheet.size, (0, 0, 0, 0)), sheet.getchannel("A"))
    for c in text:
        m = data["glyphs"].get(c)
        if not m:
            x += sp
            continue
        out.alpha_composite(colored.crop((m["x"], m["y"], m["x"] + m["w"], m["y"] + m["h"])), (x, 0))
        x += m["adv"]
    return out


def preview(s16, d16, s32, d32):
    lines = [
        (d16, s16, "ABCDEFGHIJKLMNOPQRSTUVWXYZ abcdefghijklmnopqrstuvwxyz", (255, 255, 255)),
        (d16, s16, "ÁÀÂÃÉÊÍÓÔÕÚÜÇÑÏÈ áàâãéêíóôõúüçñïè 0123456789 .,!?:;'\"-+()/%*=_$ [ ] < > | × → · •", (255, 255, 255)),
        (d16, s16, "Vira-lata (inimigo) leva 8 de dano e foi derrotado.", (255, 120, 120)),
        (d16, s16, "Seu Líder leva 4 de dano (13 HP). Você compra Maine Coon.", (140, 200, 255)),
        (d16, s16, "Adoção: escolha um gatinho. Criação, evolução, número, ação, mão, pé", (230, 210, 140)),
        (d16, s16, "Trovão Amarelo: Provocar. Ao jogar, cause 3 de dano ao Espírito inimigo.", (255, 255, 255)),
        (d32, s32, "FIM DE TURNO  SEU TURNO", (120, 230, 130)),
        (d32, s32, "ATACAR LÍDER  Criação É ÑÏÈ ñïè", (255, 255, 255)),
        (d32, s32, "Adoção de gatos 0123456789", (230, 210, 140)),
    ]
    rows = [render(s, d, t, c) for d, s, t, c in lines]
    H = sum(r.height + 8 for r in rows) + 8
    W = max(r.width for r in rows) + 16
    bg = Image.new("RGBA", (W, H), (31, 58, 52, 255))
    y = 8
    for r in rows:
        bg.alpha_composite(r, (8, y))
        y += r.height + 8
    bg.convert("RGB").save(os.path.join(PREV, "preview_fonte.png"))


if __name__ == "__main__":
    os.makedirs(PREV, exist_ok=True)
    sheet, meta = pack(build_glyphs())
    s16, d16 = write(sheet, meta, 1, "chaoscats_16")
    s32, d32 = write(sheet, meta, 2, "chaoscats_32")
    preview(s16, d16, s32, d32)
    print(len(meta), "glifos")
