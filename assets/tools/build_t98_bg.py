"""T9.8: fundo do quintal montado a partir de TILESETS do Pixellab (Wang 16x16: grama/terra, grama/caminho,
grama/piso dos filhotes) + sprites do Pixellab (cerca, arvores, moitas). Quantizado na paleta PEN48 (palette_pen.json).
Grade dual: o terreno vive nas celulas de 16 px do layout; os tiles de transicao sao desenhados deslocados meio tile,
entao as bordas caem exatamente nas linhas da grade (cercas/portoes alinhados). Periodos por tabela de cores.
Uso: python assets/tools/build_t98_bg.py   (T98_OUT=dir para staging)"""
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
import build_t98_layout as L  # noqa: E402
import build_t98_lib as B  # noqa: E402
import build_t97_bg as BG97  # noqa: E402  (path_rects, draw_lamps, LAMP_GLASS)
import build_t97_lib as L97  # noqa: E402

T, W, H = L.T, L.W, L.H
rng = np.random.default_rng(98)
PAL = B.palette_rgb()
PALMAP = dict(PAL)
PALMAP_RGB = dict(PAL)
PALSET = {c for _, c in PAL}


# ------------------------------------------------------------------ tilesets
RAMPS = {"grass": ("grass_dark", "grass", "grass_light"), "mint": ("grass", "grass_light", "grass_light"),
         "dirt": ("dirt_dark", "dirt", "dirt_light"), "path": ("path_dark", "path", "path_light")}


def luma(a):
    return a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114


def tone_map(img, classes, k_lo=0.45, k_hi=0.9):
    """classes: mapa (H,W) de nomes de rampa ('' = nao mexe). Cada classe: 3 tons por luma relativa a mediana."""
    out = img.copy()
    lu = luma(img[..., :3].astype(np.float32))
    for cname in set(classes.ravel()) - {""}:
        m = classes == cname
        med, sd = np.median(lu[m]), lu[m].std() + 1e-6
        dk, md, lt = (np.array(PALMAP_RGB[n], np.uint8) for n in RAMPS[cname])
        tone = np.where(lu < med - k_lo * sd, 0, np.where(lu > med + k_hi * sd, 2, 1))
        for t, col in enumerate((dk, md, lt)):
            out[m & (tone == t), :3] = col
    return out


def load_ts(name, other="dirt", floor=False):
    raw = B.load_rgba(os.path.join(B.SRC, name + ".png"))
    rgb = raw[..., :3].astype(int)
    green = (rgb[..., 1] > rgb[..., 2] + 14) & (rgb[..., 1] >= rgb[..., 0] - 8)
    cls = np.full(green.shape, "", dtype=object)
    cls = np.where(green, "grass", other)
    if floor:                                   # grama x pasto claro: separa pela luma (limiar = meio das duas medias)
        lu = luma(raw[..., :3].astype(np.float32))
        thr = None
        meta0 = json.load(open(os.path.join(B.SRC, name + ".json")))["tileset_data"]["tiles"]
        vals = {}
        for t in meta0:
            c = t["corners"]
            for k in ("lower", "upper"):
                if all(c[q] == k for q in ("NW", "NE", "SW", "SE")):
                    bb = t["bounding_box"]
                    vals[k] = lu[bb["y"]:bb["y"] + T, bb["x"]:bb["x"] + T].mean()
        thr = sum(vals.values()) / 2
        cls = np.where(lu > thr, "mint", "grass")
    img = tone_map(raw, cls)
    img = B.quantize(img, pal=PAL[:32], outline_luma=0)
    meta = json.load(open(os.path.join(B.SRC, name + ".json")))["tileset_data"]["tiles"]
    d = {}
    for t in meta:
        c = t["corners"]
        key = tuple(c[k] == "lower" for k in ("NW", "NE", "SW", "SE"))
        bb = t["bounding_box"]
        d[key] = img[bb["y"]:bb["y"] + T, bb["x"]:bb["x"] + T].copy()
    return d


def variants(tile):
    """8 variantes dihedrais de um tile cheio (quebra a repeticao)."""
    out = []
    for k in range(4):
        r = np.rot90(tile, k)
        out += [r, r[:, ::-1]]
    return out


def is_green(px):
    r, g, b = int(px[0]), int(px[1]), int(px[2])
    return g > b + 20 and g >= r - 6


def cells_array():
    return H // T + 2, W // T + 2          # linhas, colunas de celulas de mundo (com folga)


def rect_mask(rects):
    m = np.zeros(cells_array(), bool)
    for x0, y0, x1, y1 in rects:
        m[y0 // T:-(-y1 // T), x0 // T:-(-x1 // T)] = True
    return m


def render(ts, mask, canvas, only_mixed_over=None, lower_from_canvas=False, salt=0):
    """desenha em `canvas` (H,W,4) os tiles de `ts` conforme `mask` (celulas de mundo). Display cell (i,j) cobre
    [16i-8,16i+8) x [16j-8,16j+8). Sem mascara True nos 4 cantos -> nao toca (a menos que only_mixed_over None e lower)."""
    rows, cols = mask.shape
    pad = np.pad(mask, 1, mode="edge")
    r2 = np.random.default_rng(1000 + salt)
    full = {k: variants(v) for k, v in ts.items() if k in ((False,) * 4, (True,) * 4)}
    ext = np.zeros((H + 2 * T, W + 2 * T, 4), np.uint8)
    ext[T // 2 + 0:T // 2 + H, T // 2:T // 2 + W] = 0
    ox = oy = T // 2                                   # (16i-8)+8 -> deslocamento p/ ext
    for j in range(H // T + 2):
        for i in range(W // T + 2):
            nw, ne = pad[j, i], pad[j, i + 1]
            sw, se = pad[j + 1, i], pad[j + 1, i + 1]
            key = (bool(nw), bool(ne), bool(sw), bool(se))
            if not any(key) and only_mixed_over is not None:
                continue
            if key in full:
                tile = full[key][int(r2.integers(0, 8))]
            else:
                tile = ts[key]
            px, py = 16 * i - 8, 16 * j - 8
            if lower_from_canvas:
                tile = tile.copy()
                for yy in range(T):
                    for xx in range(T):
                        X, Y = px + xx, py + yy
                        if 0 <= X < W and 0 <= Y < H and is_green(tile[yy, xx]):
                            tile[yy, xx] = canvas[Y, X]
            for yy in range(T):
                Y = py + yy
                if not 0 <= Y < H:
                    continue
                for xx in range(T):
                    X = px + xx
                    if 0 <= X < W:
                        canvas[Y, X] = tile[yy, xx]


# ------------------------------------------------------------------ sprites
SP = {}


def spr(name):
    if name not in SP:
        SP[name] = B.clean_sprite(name, PAL[:32] if name.startswith(("cerca", "poste")) else None)
    return SP[name]


def paste(dst, src, x, y):
    h, w = src.shape[:2]
    for yy in range(h):
        ty = y + yy
        if not 0 <= ty < dst.shape[0]:
            continue
        xs = np.nonzero(src[yy, :, 3])[0]
        for xx in xs:
            tx = x + int(xx)
            if 0 <= tx < dst.shape[1]:
                dst[ty, tx] = src[yy, xx]


def ground_shadow(c, cx, yb, w):
    """sombra chapada (grass_dark) sob arvore/moita: so sobre pixels de grama."""
    sh = max(4, w // 5)
    yy, xx = np.mgrid[0:H, 0:W]
    m = ((xx + 0.5 - cx) / ((w + 4) / 2.0)) ** 2 + ((yy + 0.5 - (yb - 1)) / (sh / 2.0)) ** 2 <= 1.0
    gd = np.array(PALMAP_RGB["grass_dark"])
    R, G, Bc = (c[..., k].astype(int) for k in range(3))
    ok = (G > Bc + 20) & (G >= R - 6) & (c[..., 3] > 0)
    c[m & ok, :3] = gd




def put(c, name, cx, yb, shadow=True, flip=False):
    s = spr(name)
    if flip:
        s = s[:, ::-1]
    if shadow:
        ground_shadow(c, cx, yb, s.shape[1])
    paste(c, s, cx - s.shape[1] // 2, yb - s.shape[0])


# ------------------------------------------------------------------ cercas
FH_ = spr("cerca_h")           # 40x19, postes em x 0..6, 16..22, 33..39
FV_ = spr("cerca_v")           # 41x8
GP_ = spr("poste_portao")      # 36x19
POST_W = 7
GAP_COLS = FH_[:, 7:16]


def unit_h():
    """unidade periodica de 32 px: poste (7 col) + trilho liso 25 col."""
    u = np.zeros((FH_.shape[0], 32, 4), np.uint8)
    u[:, :7] = FH_[:, :7]
    g = np.concatenate([GAP_COLS, GAP_COLS, GAP_COLS], 1)
    u[:, 7:32] = g[:, :25]
    return u


UH = unit_h()


def hrun(c, x0, x1, ybase):
    """trilho horizontal [x0,x1) com poste a cada 32 px; base (pe dos postes) em ybase (inclusivo)."""
    top = ybase - FH_.shape[0] + 1
    n = x1 - x0
    strip = np.zeros((FH_.shape[0], n, 4), np.uint8)
    for x in range(n):
        strip[:, x] = UH[:, (x + 32 - 5) % 32]
    paste(c, strip, x0, top)
    for px in (x0 + 1, x1 - POST_W - 1):
        paste(c, FH_[:, :POST_W], px, top)


def vrun(c, cx, y0, y1):
    n = y1 - y0
    if n <= 0:
        return
    strip = np.zeros((n, FV_.shape[1], 4), np.uint8)
    for y in range(n):
        if y < 15:
            r = y
        elif y >= n - 12:
            r = 29 + (y - (n - 12))
        else:
            r = 15 + ((y - 15) % 14)
        strip[y] = FV_[min(r, FV_.shape[0] - 1)]
    paste(c, strip, cx - FV_.shape[1] // 2, y0)


def draw_fences(c):
    gates = []
    for zone, (c0, r0, c1, r1) in L.RINGS.items():
        side, g0 = L.GATES[zone]
        gl, gr = g0 * T - 12, (g0 + 2) * T + 12            # extremos do vao (centros dos postes de portao)
        # horizontais
        for edge, row in (("N", r0), ("S", r1)):
            yb = row * T + 15
            xa, xb = c0 * T, (c1 + 1) * T
            if side == edge:
                hrun(c, xa, gl + 5, yb)
                hrun(c, gr - 5, xb, yb)
                gates.append(("h", gl, yb, False))
                gates.append(("h", gr, yb, True))
            else:
                hrun(c, xa, xb, yb)
        # verticais
        for edge, col in (("W", c0), ("E", c1)):
            cx = col * T + 8
            ya, yb2 = r0 * T + 10, r1 * T + 14
            if side == edge:
                vrun(c, cx, ya, gl + 10)
                vrun(c, cx, gr - 8, yb2)
                gates.append(("v", cx, gl + 8, False))
                gates.append(("v", cx, gr + 8, False))
            else:
                vrun(c, cx, ya, yb2)
    # postes de canto (do trilho horizontal) por cima
    for zone, (c0, r0, c1, r1) in L.RINGS.items():
        for col in (c0, c1):
            for row in (r0, r1):
                top = row * T + 15 - FH_.shape[0] + 1
                paste(c, FH_[:, :POST_W], col * T + 8 - POST_W // 2, top)
    for kind, a, b, flip in sorted(gates, key=lambda g: (g[2] if g[0] == "h" else g[2])):
        s = GP_[:, ::-1] if flip else GP_
        if kind == "h":
            paste(c, s, a - s.shape[1] // 2, b - s.shape[0] + 1)
        else:
            paste(c, s, a - s.shape[1] // 2, b - s.shape[0] + 1)


# ------------------------------------------------------------------ vegetacao
def vegetation(c):
    items = []
    for i, (cx, yb) in enumerate([(6, 76), (4, 190), (8, 312), (4, 426), (8, 520)]):
        items.append((yb, "arvore_peq1" if i % 2 == 0 else "arvore_peq2", cx, i % 3 == 2))
    for i, cx in enumerate((70, 150, 238, 330, 392)):
        items.append((44, ("moita_flor", "moita_b", "moita_c")[i % 3], cx, i % 2 == 1))
    for i, cx in enumerate((76, 168, 262, 350, 404)):
        items.append((536, ("moita_b", "moita_flor", "moita_c")[i % 3], cx, i % 2 == 0))
    for i, cx in enumerate((520, 590, 660, 706)):
        items.append((44, ("moita_c", "moita_flor", "moita_b")[i % 3], cx, i % 2 == 1))
    for i, cx in enumerate((530, 610, 690)):
        items.append((536, ("moita_flor", "moita_c", "moita_b")[i % 3], cx, False))
    items.append((528, "arvore_peq2", 724, False))
    items.append((300, "moita_c", 728, False))
    for cx, yb, nm in [(414, 134, "moita_b"), (414, 476, "moita_c"), (62, 476, "moita_b"), (514, 238, "moita_c"),
                       (692, 476, "moita_b")]:
        items.append((yb, nm, cx, False))
    for yb, nm, cx, fl in sorted(items, key=lambda t: t[0]):
        put(c, nm, cx, yb, flip=fl)


def forest(c):
    x0 = L.PANEL[0]
    gd = np.array(PALMAP_RGB["bush_dark"] if "bush_dark" in PALMAP_RGB else (47, 106, 70))
    c[:, x0:, :3] = gd
    c[:, x0:, 3] = 255
    names = ["arvore_a", "arvore_b", "arvore_peq1", "arvore_peq2"]
    items = []
    for j in range(0, 22):
        for i in range(0, 7):
            x = x0 + 4 + i * 34 + (17 if j % 2 else 0) + int(rng.integers(-3, 4))
            yb = 12 + j * 26 + int(rng.integers(-3, 4))
            items.append((yb, names[(i * 3 + j * 5 + (i * j)) % 4], x, (i + j) % 2 == 0))
    for yb, nm, x, fl in sorted(items, key=lambda t: t[0]):
        s = spr(nm)
        s = s[:, ::-1] if fl else s
        paste(c, s, x - s.shape[1] // 2, yb - s.shape[0])
    # a mata nao vaza sobre a grama: corta em x0 (restaura pela esquerda)


def lamps(c):
    cv = L97.Canvas(W, H)
    cv.a = c
    BG97.LAMP_GLASS.clear()
    BG97.draw_lamps(cv)


def decor(c):
    """tufos e florzinhas (paleta PEN) sobre a grama, fora de caminhos."""
    cv = L97.Canvas(W, H)
    cv.a = c
    R, G, Bc = (c[..., k].astype(int) for k in range(3))
    green = (G > Bc + 20) & (G >= R - 6)
    keep = green
    gcol = np.array(PALMAP_RGB["grass"], np.uint8)
    pm = BG97.noise_patches(W, H, cell=28, block=4, thr=0.74, seed=17)
    base = (c[..., :3] == gcol).all(-1)
    c[pm & base, :3] = np.array(PALMAP_RGB["grass_light"], np.uint8)
    BG97.rng = np.random.default_rng(98)
    BG97.scatter(cv, 0, 0, 736, H, "grass", 0.26, 0.05, keep)


# ------------------------------------------------------------------ montagem
def path_cell_rects():
    r = []
    for x0, y0, x1, y1 in BG97.path_rects():
        r.append((x0, y0, min(x1, W + 16), y1))
    return r


def build_dia():
    c = np.zeros((H, W, 4), np.uint8)
    gd, gp, gf = load_ts("ts_grass_dirt", "dirt"), load_ts("ts_grass_path", "path"), load_ts("ts_floor3", floor=True)
    # 1) grama em tudo (tile cheio 'lower' do conjunto grama/terra, 8 variantes)
    none = np.zeros(cells_array(), bool)
    render(gd, none, c, salt=1)
    # 2) pisos dos cercados (celulas do anel inteiro: a borda do piso cai no limite externo da cerca)
    def ring_rect(z):
        c0, r0, c1, r1 = L.RINGS[z]
        return (c0 * T, r0 * T, (c1 + 1) * T, (r1 + 1) * T)
    render(gd, rect_mask([ring_rect("breed")]), c, only_mixed_over=True, salt=2)
    render(gf, rect_mask([ring_rect("filhotes")]), c, only_mixed_over=True, salt=3)
    # 3) caminho: tiles do conjunto grama/caminho; o 'lower' (verde) vira o que ja estava embaixo (grama/terra/piso)
    render(gp, rect_mask(path_cell_rects()), c, only_mixed_over=True, lower_from_canvas=True, salt=4)
    decor(c)
    draw_fences(c)
    vegetation(c)
    forest(c)
    lamps(c)
    c[..., 3] = 255
    return c


def tint_table(rgb, tint, lit):
    a = rgb.astype(np.float32)
    out = np.clip(a * (np.array(tint, np.float32) / 255.0), 0, 255).round().astype(np.uint8)
    if lit:
        for x0, y0, x1, y1 in BG97.LAMP_GLASS:
            out[y0:y1, x0:x1] = rgb[y0:y1, x0:x1]
    return Image.fromarray(out, "RGB")


def main():
    os.makedirs(B.OUT, exist_ok=True)
    c = build_dia()
    rgb = c[..., :3].copy()
    out = {tuple(int(v) for v in t) for t in np.unique(rgb.reshape(-1, 3), axis=0)} - PALSET
    assert not out, sorted(out)[:6]
    Image.fromarray(rgb, "RGB").save(os.path.join(B.OUT, "pen_bg_dia.png"))
    for p in ("amanhecer", "entardecer", "noite"):
        tint_table(rgb, L.TINT[p], p in ("entardecer", "noite")).save(os.path.join(B.OUT, f"pen_bg_{p}.png"))
    print("bg ok; cores:", len({tuple(x) for x in rgb.reshape(-1, 3)}))


if __name__ == "__main__":
    main()
