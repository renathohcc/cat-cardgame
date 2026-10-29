"""T9.0: gatos do criatorio (forma pacato + filhotes). Pillow.

Origem (Pixellab, 2026-10-29; ver reports/T9.0-arte-criatorio.md):
  1. bases 64x64 de perfil: create_image_pro_flash (style_image = gato96 reduzido) -> _src/base_<id>.png
  2. animacoes: animate_image (64x64, 4/8/16 frames) a partir da base -> frames baixados com
     `fetch` (download?index=i) em _src/<id>/<anim>_<i>.png
  3. este script monta cats_pen.png + cats_pen.json e os previews.

Uso:
  python assets/tools/build_t90.py fetch <id> <anim> <job_id> <n_frames>   # baixa frames de um job
  python assets/tools/build_t90.py build                                   # monta sheet/json/previews
"""
import json
import os
import sys
import urllib.request

from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PEN = os.path.join(ROOT, "assets", "pen")
SRC = os.path.join(PEN, "_src")
PREV = os.path.join(ROOT, "reports", "arte")
BREEDS = ["vira-lata", "siames", "persa", "sphynx", "maine-coon"]
IDS = BREEDS + [b + "_filhote" for b in BREEDS]
ANIMS = ["idle", "walk", "sleep", "play"]
FPS = {"idle": 5, "walk": 10, "sleep": 3, "play": 8}
FRAME = 64
# quadros do sleep a usar (o job gera 17 quadros: o gato deita e depois respira); (inicio, fim) por id
SLEEP_RANGE = {}
API = "https://api.pixellab.ai/mcp/images/%s/download"


def fetch(cid, anim, job, n):
    d = os.path.join(SRC, cid)
    os.makedirs(d, exist_ok=True)
    for i in range(n):
        data = urllib.request.urlopen(API % job + "?index=%d" % i).read()
        with open(os.path.join(d, "%s_%02d.png" % (anim, i)), "wb") as f:
            f.write(data)
    print(cid, anim, n, "frames")


def load_frames(cid, anim):
    d = os.path.join(SRC, cid)
    fs = []
    i = 0
    while os.path.exists(os.path.join(d, "%s_%02d.png" % (anim, i))):
        fs.append(Image.open(os.path.join(d, "%s_%02d.png" % (anim, i))).convert("RGBA"))
        i += 1
    return fs


def binarize(im):
    """alfa binario (pixel art sem semitransparencia)."""
    px = im.load()
    for y in range(im.height):
        for x in range(im.width):
            r, g, b, a = px[x, y]
            px[x, y] = (r, g, b, 255) if a >= 128 else (0, 0, 0, 0)
    return im


def drop_islands(im, min_area=40):
    """remove ilhas soltas pequenas (artefatos da geracao: pontinhos/marcas fora do corpo)."""
    px = im.load()
    w, h = im.size
    seen = set()
    for y in range(h):
        for x in range(w):
            if px[x, y][3] == 0 or (x, y) in seen:
                continue
            comp, st = [], [(x, y)]
            seen.add((x, y))
            while st:
                cx, cy = st.pop()
                comp.append((cx, cy))
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        q = (cx + dx, cy + dy)
                        if 0 <= q[0] < w and 0 <= q[1] < h and q not in seen and px[q][3]:
                            seen.add(q)
                            st.append(q)
            if len(comp) < min_area:
                for c in comp:
                    px[c] = (0, 0, 0, 0)
    return im


def pick(cid, anim, frames):
    if anim == "sleep":
        # fase "deitando" descartada; trecho dormindo em vai-e-volta (ping-pong) para loop suave
        a, b = SLEEP_RANGE.get(cid, (10, len(frames)))
        seg = frames[a:b]
        return seg + seg[-2:0:-1]
    if anim == "walk":
        return frames[1:]          # quadro 0 e a pose-base parada
    return frames


def baseline_shift(cid):
    """desloca vertical por id: pes (base do idle/walk) na linha 62 -> 1 px de margem e linha de chao igual para todos."""
    bottoms, tops = [], []
    for an in ANIMS:
        for f in load_frames(cid, an):
            b = drop_islands(binarize(f.copy())).getbbox()
            if b:
                tops.append(b[1])
                if an in ("idle", "walk"):
                    bottoms.append(b[3] - 1)
    return max(61 - max(bottoms), -min(tops))   # nunca corta o topo


def shift_img(im, dy):
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.alpha_composite(im, (0, dy))
    return out


def build():
    rows = []
    meta = {}
    for cid in IDS:
        meta[cid] = {}
        for anim in ANIMS:
            fr = load_frames(cid, anim)
            if not fr:
                continue
            dy = baseline_shift(cid)
            fr = [shift_img(drop_islands(binarize(f.copy())), dy) for f in pick(cid, anim, fr)]
            meta[cid][anim] = {"row": len(rows), "frames": len(fr), "fps": FPS[anim]}
            rows.append(fr)
    if not rows:
        print("nada para montar")
        return
    cols = max(len(r) for r in rows)
    sheet = Image.new("RGBA", (cols * FRAME, len(rows) * FRAME), (0, 0, 0, 0))
    for r, fr in enumerate(rows):
        for c, f in enumerate(fr):
            sheet.alpha_composite(f, (c * FRAME, r * FRAME))
    sheet.save(os.path.join(PEN, "cats_pen.png"))
    with open(os.path.join(PEN, "cats_pen.json"), "w", encoding="utf-8") as f:
        json.dump({"image": "cats_pen.png", "size": list(sheet.size), "frame": [FRAME, FRAME], "anims": meta}, f, indent=1)
    print("sheet", sheet.size, "rows", len(rows))
    previews(sheet, meta)


def previews(sheet, meta):
    os.makedirs(PREV, exist_ok=True)
    Z = 4
    lines = [(cid, an, a) for cid, m in meta.items() for an, a in m.items()]
    cols = max(a["frames"] for _, _, a in lines)
    LW = 190
    W, H = LW + cols * FRAME * Z + 8, len(lines) * (FRAME * Z + 6) + 6
    # um preview por grupo para manter a imagem de tamanho razoavel
    for part, sel in (("adultos", [l for l in lines if "filhote" not in l[0]]), ("filhotes", [l for l in lines if "filhote" in l[0]])):
        H = len(sel) * (FRAME * Z + 6) + 6
        im = Image.new("RGBA", (W, H), (44, 53, 83, 255))
        d = ImageDraw.Draw(im)
        for k, (cid, an, a) in enumerate(sel):
            y = 6 + k * (FRAME * Z + 6)
            d.text((6, y + 8), "%s / %s" % (cid, an), fill=(230, 230, 240, 255))
            d.text((6, y + 24), "%d frames @ %d fps" % (a["frames"], a["fps"]), fill=(160, 170, 200, 255))
            for c in range(a["frames"]):
                cell = sheet.crop((c * FRAME, a["row"] * FRAME, (c + 1) * FRAME, (a["row"] + 1) * FRAME))
                x = LW + c * FRAME * Z
                d.rectangle((x, y, x + FRAME * Z - 1, y + FRAME * Z - 1), fill=(35, 42, 63, 255))
                im.alpha_composite(cell.resize((FRAME * Z, FRAME * Z), Image.NEAREST), (x, y))
        im.save(os.path.join(PREV, "preview_pen_anims_%s.png" % part))
    print("previews ok")


def scene():
    """cena montada: ~8 gatos no cercado (preview do que a UI vai fazer)."""
    meta = json.load(open(os.path.join(PEN, "cats_pen.json"), encoding="utf-8"))
    pen = json.load(open(os.path.join(PEN, "pen.json"), encoding="utf-8"))
    fx = json.load(open(os.path.join(PEN, "fx.json"), encoding="utf-8"))
    sheet = Image.open(os.path.join(PEN, "cats_pen.png")).convert("RGBA")
    fxs = Image.open(os.path.join(PEN, "fx.png")).convert("RGBA")
    bg = Image.open(os.path.join(PEN, pen["bg"])).convert("RGBA")

    def cell(cid, anim, i, flip=False):
        a = meta["anims"][cid][anim]
        c = sheet.crop((i % a["frames"] * 64, a["row"] * 64, i % a["frames"] * 64 + 64, a["row"] * 64 + 64))
        return c.transpose(Image.FLIP_LEFT_RIGHT) if flip else c

    def put(cid, anim, i, x, y, flip=False):  # x,y = pes (centro-base)
        bg.alpha_composite(cell(cid, anim, i, flip), (x - 32, y - 60))

    def sprite(name, x, y):
        s = fx["sprites"][name]
        bg.alpha_composite(fxs.crop((s["x"], s["y"], s["x"] + 16, s["y"] + 16)), (x, y))

    S, P = pen["sleep_spots"], pen["play_spots"]
    put("maine-coon", "sleep", 3, S[0][0], S[0][1] + 8)
    sprite("z", S[0][0] + 14, S[0][1] - 40)
    put("persa", "sleep", 2, S[1][0], S[1][1] + 8)
    sprite("z", S[1][0] + 16, S[1][1] - 38)
    put("sphynx_filhote", "sleep", 4, S[3][0], S[3][1] + 8)
    sprite("z", S[3][0] + 10, S[3][1] - 34)
    put("vira-lata", "walk", 2, 200, 260)
    put("siames", "walk", 5, 560, 250, True)
    put("vira-lata_filhote", "idle", 1, 560, 350)
    sprite("heart", 568, 296)
    put("siames_filhote", "walk", 3, 150, 330)
    put("persa_filhote", "play", 2, P[0][0] + 6, P[0][1] + 14)
    sprite("sparkle", P[0][0] + 20, P[0][1] - 40)
    put("sphynx", "idle", 0, 640, 300, True)
    put("maine-coon_filhote", "walk", 4, 300, 390, True)
    put("persa", "play", 3, P[1][0] - 30, P[1][1] + 18)
    sprite("note", 650, 250)
    os.makedirs(PREV, exist_ok=True)
    bg.save(os.path.join(PREV, "preview_pen_cena.png"))
    print("cena ok")


if __name__ == "__main__":
    if sys.argv[1] == "scene":
        scene()
    elif sys.argv[1] == "fetch":
        fetch(sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]))
    else:
        build()
