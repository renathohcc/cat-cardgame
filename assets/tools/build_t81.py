"""T8.1: sheets 96x96 de espiritos e efeitos (fontes Pixellab em _src), icones 16x16 (build_t81_icons) e previews.
Uso: python assets/tools/build_t81.py"""
import json
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from build_t81_icons import build_icons  # noqa: E402

A = ROOT / "assets"; PREV = ROOT / "reports/arte"
BG = (236, 222, 196, 255)


def ids(f, key): return [e["id"] for e in json.loads((ROOT / "data" / f).read_text("utf-8"))[key]]


def binarize(im):
    im = im.convert("RGBA"); px = im.load()
    for x in range(im.width):
        for y in range(im.height):
            r, g, b, a = px[x, y]; px[x, y] = (r, g, b, 255) if a >= 128 else (0, 0, 0, 0)
    return im


def write_sheet(folder, items, cell, cols, scale=1):
    c = cell * scale; rows = -(-len(items) // cols); s = Image.new("RGBA", (cols * c, rows * c), (0, 0, 0, 0)); meta = {}
    for i, (n, im) in enumerate(items):
        if scale > 1: im = im.resize((c, c), Image.NEAREST)
        x, y = (i % cols) * c, (i // cols) * c; s.paste(im, (x, y)); meta[n] = {"x": x, "y": y, "w": c, "h": c}
    suf = "" if scale == 1 else f"_x{scale}"
    s.save(folder / f"spritesheet{suf}.png")
    (folder / f"spritesheet{suf}.json").write_text(json.dumps({"image": f"spritesheet{suf}.png", "size": list(s.size), "sprites": meta}, indent=2), "utf-8")
    return s


def from_src(folder, names):
    out = []
    for n in names:
        im = binarize(Image.open(A / folder / "_src" / f"{n}.png")); assert im.size == (96, 96), n
        im.save(A / folder / f"{n}.png"); out.append((n, im))
    return out


def contact(items, scale, cols, path, label=True, cell=None):
    cell = cell or items[0][1].width * scale; pad = 6; lh = 14 if label else 0
    rows = -(-len(items) // cols); W = cols * (cell + pad) + pad; H = rows * (cell + lh + pad) + pad
    s = Image.new("RGBA", (W, H), BG); d = ImageDraw.Draw(s)
    try: f = ImageFont.truetype("arial.ttf", 11)
    except OSError: f = ImageFont.load_default()
    for i, (n, im) in enumerate(items):
        x, y = pad + (i % cols) * (cell + pad), pad + (i // cols) * (cell + lh + pad)
        big = im.resize((im.width * scale, im.height * scale), Image.NEAREST); s.alpha_composite(big, (x + (cell - big.width) // 2, y))
        if label: d.text((x + cell // 2, y + cell + 1), n, fill=(59, 42, 56, 255), font=f, anchor="mt")
    PREV.mkdir(parents=True, exist_ok=True); s.convert("RGB").save(path)


def main():
    sp = from_src("specials96", ids("specials.json", "specials")); ef = from_src("effects96", ids("effects.json", "effects"))
    write_sheet(A / "specials96", sp, 96, 4); write_sheet(A / "effects96", ef, 96, 4)
    icons = list(build_icons().items())
    for n, im in icons: im.save(A / "icons16" / f"{n}.png")
    write_sheet(A / "icons16", icons, 16, 6); write_sheet(A / "icons16", icons, 16, 6, scale=2)
    contact(sp, 4, 4, PREV / "preview_especiais96_4x.png"); contact(ef, 4, 4, PREV / "preview_efeitos96_4x.png")
    contact(icons, 8, 6, PREV / "preview_icones16_8x.png", cell=140)
    # teste de legibilidade: icones 16x16 em tamanho real 1x/2x sobre fundos claro, escuro e colorido
    s = Image.new("RGBA", (len(icons) * 40 + 8, 3 * 40 + 8), (0, 0, 0, 0)); d = ImageDraw.Draw(s)
    for r, col in enumerate([(236, 222, 196), (30, 24, 40), (70, 120, 70)]):
        d.rectangle([0, r * 40, s.width, r * 40 + 39], fill=col + (255,))
        for i, (n, im) in enumerate(icons): s.alpha_composite(im, (8 + i * 40, r * 40 + 12)); s.alpha_composite(im.resize((32, 32), Image.NEAREST), (8 + i * 40, r * 40 + 4)) if False else None
    s.resize((s.width * 3, s.height * 3), Image.NEAREST).convert("RGB").save(PREV / "preview_icones16_fundos.png")


if __name__ == "__main__":
    main()
