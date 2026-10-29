"""T9.7: fundo do quintal em grade de 16 px, pixel art chapada na paleta PEN. Uma arte base (dia) e os outros
periodos saem por tabela de cores (multiplica a paleta pelo tint do periodo; lanternas acesas ficam amarelas).
Uso: python assets/tools/build_t97_bg.py"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
import build_t97_layout as L  # noqa: E402
from build_t97_lib import (PAL, Canvas, bitmap, m_ell, m_rect, outline_of, pal_check, rgb, shaded)  # noqa: E402

T = L.T
rng = np.random.default_rng(97)
LAMP_GLASS = []        # retangulos (x0,y0,x1,y1) do vidro das lanternas


def noise_patches(w, h, cell=32, block=8, thr=0.70, seed=0):
    """mascara de manchas em blocos de `block` px (valor-ruido suavizado)."""
    r = np.random.default_rng(seed)
    gw, gh = w // cell + 4, h // cell + 4
    g = r.random((gh, gw))
    ys, xs = np.mgrid[0:-(-h // block), 0:-(-w // block)]
    fx, fy = xs * block / cell, ys * block / cell
    x0, y0 = fx.astype(int), fy.astype(int)
    tx, ty = fx - x0, fy - y0
    n = (g[y0, x0] * (1 - tx) * (1 - ty) + g[y0, x0 + 1] * tx * (1 - ty) + g[y0 + 1, x0] * (1 - tx) * ty
         + g[y0 + 1, x0 + 1] * tx * ty)
    m = n > thr
    return np.kron(m, np.ones((block, block), bool))[:h, :w]


def fill_zone(c, x, y, w, h, base, patch, seed):
    c.rect(x, y, x + w, y + h, base)
    pm = noise_patches(L.W, L.H, thr=2.0, seed=seed)
    reg = np.zeros((L.H, L.W), bool)
    reg[y:y + h, x:x + w] = True
    c.paint(pm & reg, patch)


TUFT = {"grass_dark": "grass", "grass": "grass_dark", "grass_light": "grass"}
TUFTS = [["X.X", ".X."], ["..X", "X.X", ".X."], ["X..X", ".XX."]]


def scatter(c, x, y, w, h, base, p_tuft=0.16, p_flower=0.035, keep=None):
    col = TUFT[base]
    for ty in range(y // T, (y + h) // T):
        for tx in range(x // T, (x + w) // T):
            if keep is not None and not keep[ty * T + 8, tx * T + 8]:
                continue
            r = rng.random()
            ox, oy = int(rng.integers(2, 10)), int(rng.integers(2, 11))
            if r < p_tuft:
                bitmap(c, tx * T + ox, ty * T + oy, TUFTS[int(rng.integers(0, 3))], {"X": col})
            elif r < p_tuft + p_flower:
                pc = ["cream_light", "flower_pink", "cream_light", "flower_red"][int(rng.integers(0, 4))]
                bitmap(c, tx * T + ox, ty * T + oy, [".X.", "XYX", ".X."], {"X": pc, "Y": "yellow"})


def dirt_speckle(c, x, y, w, h, keep=None):
    for ty in range(y // T, (y + h) // T):
        for tx in range(x // T, (x + w) // T):
            if keep is not None and not keep[ty * T + 8, tx * T + 8]:
                continue
            for _ in range(2):
                if rng.random() < 0.5:
                    ox, oy = int(rng.integers(1, 13)), int(rng.integers(1, 14))
                    kind = rng.random()
                    if kind < 0.5:
                        bitmap(c, tx * T + ox, ty * T + oy, ["XX"], {"X": "dirt_dark"})
                    elif kind < 0.85:
                        bitmap(c, tx * T + ox, ty * T + oy, ["X."], {"X": "dirt_light"})
                    else:
                        bitmap(c, tx * T + ox, ty * T + oy, ["XX", "XX"], {"X": "dirt_dark"})


# ------------------------------------------------------------------ caminhos
def path_rects():
    px0, px1 = L.PATH_V[0] * T, (L.PATH_V[1] + 1) * T
    py0, py1 = L.PATH_H[0] * T, (L.PATH_H[1] + 1) * T
    rects = [(px0, 0, px1, L.H),                           # vertical (entrada embaixo)
             (352, py0, L.PATH_H_END_X, py1)]              # horizontal, entra no cercado dos adultos
    gx = 36 * T
    rects.append((gx, 192, gx + 2 * T, py0))               # tronco para o gate dos casais
    rects.append((gx, py1, gx + 2 * T, 352))               # tronco para o gate dos filhotes
    return rects


def draw_paths(c):
    m = np.zeros((L.H, L.W), bool)
    for x0, y0, x1, y1 in path_rects():
        m[y0:y1, x0:x1] = True
    c.paint(m, "path")
    # manchas claras chatas em blocos de 8 px
    pm = noise_patches(L.W, L.H, cell=24, block=8, thr=0.8, seed=5)
    edge = m & ~(np.roll(m, 1, 0) & np.roll(m, -1, 0) & np.roll(m, 1, 1) & np.roll(m, -1, 1))
    c.paint(edge, "path_dark")
    # pedrinhas 2x2 (luz no canto superior esquerdo)
    for ty in range(L.H // T):
        for tx in range(L.W // T):
            if m[ty * T + 8, tx * T + 8] and rng.random() < 0.35:
                ox, oy = int(rng.integers(3, 11)), int(rng.integers(3, 11))
                if m[ty * T + oy - 2:ty * T + oy + 4, tx * T + ox - 2:tx * T + ox + 4].all():
                    bitmap(c, tx * T + ox, ty * T + oy, ["LP", "PD"], {"L": "path_light", "P": "pebble", "D": "path_dark"})
    return m


# ------------------------------------------------------------------ cercas
def rail_h(c, x0, x1, y):
    for dy, col in ((3, "outline"), (4, "wood_light"), (5, "wood"), (6, "wood_dark"), (7, "outline"),
                    (9, "outline"), (10, "wood_light"), (11, "wood"), (12, "wood_dark"), (13, "outline")):
        c.rect(x0, y + dy, x1, y + dy + 1, col)


def rail_v(c, x, y0, y1):
    for dx, col in ((6, "outline"), (7, "wood_light"), (8, "wood"), (9, "wood_dark"), (10, "outline")):
        c.rect(x + dx, y0, x + dx + 1, y1, col)


def post(c, cx, ybot, tall=False):
    """poste 8 px de largura centrado em cx, base em ybot; 14 px de altura (22 no portao)."""
    h = 22 if tall else 14
    y0 = ybot - h
    c.rect(cx - 4, y0, cx + 4, ybot, "outline")
    c.rect(cx - 3, y0 + 1, cx + 3, y0 + 4, "wood_light")
    c.rect(cx - 3, y0 + 4, cx + 3, y0 + 5, "wood_dark")
    c.rect(cx - 3, y0 + 5, cx + 3, ybot - 1, "wood")
    c.rect(cx - 3, y0 + 5, cx - 2, ybot - 1, "wood_light")
    c.rect(cx + 2, y0 + 5, cx + 3, ybot - 1, "wood_dark")


def zone_posts(zone):
    """(cx, ybot, tall) dos postes do anel de `zone` e retangulos de trilho."""
    c0, r0, c1, r1 = L.RINGS[zone]
    side, g0 = L.GATES[zone]
    posts, rails_h, rails_v = [], [], []

    def gap_h(row, edge):
        return edge == side and False

    # horizontais (N em r0, S em r1)
    for edge, row in (("N", r0), ("S", r1)):
        gap = (g0, g0 + 1) if side == edge else None
        cols = [c for c in range(c0, c1 + 1)]
        segs = [(c0, c1 + 1)] if not gap else [(c0, gap[0]), (gap[1] + 1, c1 + 1)]
        for a, b in segs:
            rails_h.append((a * T, b * T, row * T))
        pcols = set(range(c0, c1 + 1, 3)) | {c1}
        if gap:
            pcols = {c for c in pcols if abs(c - gap[0]) > 1 and abs(c - gap[1]) > 1 and c not in gap}
            pcols |= {gap[0] - 1, gap[1] + 1}
        pcols |= {c0, c1}
        for cc in sorted(pcols):
            tall = bool(gap) and cc in (gap[0] - 1, gap[1] + 1)
            posts.append((cc * T + 8, row * T + 15, tall))
    # verticais (W em c0, E em c1)
    for edge, col in (("W", c0), ("E", c1)):
        gap = (g0, g0 + 1) if side == edge else None
        segs = [(r0 + 1, r1)] if not gap else [(r0 + 1, gap[0]), (gap[1] + 1, r1)]
        for a, b in segs:
            rails_v.append((col * T, a * T, b * T))
        prow = set(range(r0, r1 + 1, 3)) | {r1}
        if gap:
            prow = {r for r in prow if abs(r - gap[0]) > 1 and abs(r - gap[1]) > 1 and r not in gap}
            prow |= {gap[0] - 1, gap[1] + 1}
        for rr in sorted(prow):
            if rr in (r0, r1):
                continue
            tall = bool(gap) and rr in (gap[0] - 1, gap[1] + 1)
            posts.append((col * T + 8, rr * T + 15, tall))
    return posts, rails_h, rails_v


def draw_fences(c):
    allposts = []
    for z in L.RINGS:
        posts, rh, rv = zone_posts(z)
        for x0, x1, y in rh:
            rail_h(c, x0, x1, y)
        for x, y0, y1 in rv:
            rail_v(c, x, y0, y1)
        allposts += posts
    for cx, yb, tall in sorted(allposts, key=lambda p: p[1]):
        post(c, cx, yb, tall)


# ------------------------------------------------------------------ vegetacao
def bush_sprite(w=28, h=18, flowers=True, seed=0):
    r = np.random.default_rng(seed)
    c = Canvas(w, h)
    m = m_ell(c, 0, 4, w * 6 // 10, h - 4) | m_ell(c, w * 4 // 10, 0, w * 6 // 10, h - 2) | m_ell(c, w // 5, 3, w * 3 // 5, h - 3)
    shaded(c, m, "bush", "bush_light", "bush_dark", depth=3)
    if flowers:
        for _ in range(4):
            x, y = int(r.integers(4, w - 5)), int(r.integers(4, h - 6))
            if m[y, x]:
                c.px(x, y, ["flower_pink", "cream_light", "yellow"][int(r.integers(0, 3))])
    return c


def tree_sprite(w=44, h=50, seed=0):
    r = np.random.default_rng(seed)
    c = Canvas(w, h)
    trunk = m_rect(c, w // 2 - 4, h - 16, 8, 16)
    shaded(c, trunk, "wood", "wood_light", "wood_dark", depth=2)
    can = (m_ell(c, 0, 12, w * 6 // 10, 26) | m_ell(c, w * 4 // 10, 12, w * 6 // 10, 26) | m_ell(c, w // 6, 0, w * 2 // 3, 30)
           | m_ell(c, w // 8, 14, w * 3 // 4, 26))
    shaded(c, can, "bush", "bush_light", "bush_dark", depth=3)
    for _ in range(5):                                             # tufos de folha
        x, y = int(r.integers(6, w - 8)), int(r.integers(5, 28))
        if can[y, x] and can[y + 1, x + 2]:
            bitmap(c, x, y, ["XX.", ".XX"], {"X": "bush_light"})
    return c


def rock_sprite(i=0):
    w, h = (14, 9) if i % 2 == 0 else (11, 8)
    c = Canvas(w, h)
    m = m_ell(c, 0, 1, w, h - 1)
    shaded(c, m, "stone", "stone_light", "stone_dark", depth=2)
    return c


def ground_shadow(c, x, y, w):
    from build_t97_lib import shadow
    shadow(c, x - w // 2, y - 3, w, 7, alpha=0) if False else None


def put(c, spr, cx, ybase):
    """cola o sprite com o centro-base em (cx, ybase) + sombra de contato opaca (grass escuro) nao usada (chapado)."""
    c.paste(spr, cx - spr.w // 2, ybase - spr.h)


def draw_vegetation(c):
    items = []     # (ybase, sprite, cx)
    # arvores nos cantos e na coluna esquerda
    left = [(14, 58), (12, 178), (14, 300), (12, 420), (14, 510)]
    for i, (cx, yb) in enumerate(left):
        items.append((yb, tree_sprite(36, 44, i), cx))
    for i, cx in enumerate((70, 150, 238, 330, 392)):
        items.append((42, bush_sprite(26, 16, True, i), cx))
    for i, cx in enumerate((76, 168, 262, 350, 400)):
        items.append((534, bush_sprite(28, 17, True, 10 + i), cx))
    for i, cx in enumerate((520, 590, 660, 704)):
        items.append((42, bush_sprite(26, 16, True, 20 + i), cx))
    for i, cx in enumerate((530, 610, 690)):
        items.append((534, bush_sprite(28, 17, True, 30 + i), cx))
    items.append((526, tree_sprite(36, 44, 40), 722))
    items.append((300, bush_sprite(16, 12, False, 41), 726))
    # cantos de dentro do cercado dos adultos
    items.append((128, bush_sprite(22, 14, False, 50), 417))
    items.append((476, bush_sprite(22, 14, False, 51), 417))
    items.append((476, bush_sprite(22, 14, False, 52), 63))
    # cantos do cercado dos casais / filhotes
    items.append((236, bush_sprite(22, 14, False, 53), 515))
    items.append((476, bush_sprite(22, 14, False, 54), 689))
    for i, (cx, yb) in enumerate([(70, 104), (414, 196), (62, 332), (420, 446), (250, 470), (690, 108), (520, 228),
                                  (700, 326), (508, 322), (600, 100)]):
        items.append((yb, rock_sprite(i), cx))
    for yb, spr, cx in sorted(items, key=lambda t: t[0]):
        put(c, spr, cx, yb)


def draw_forest(c):
    """x >= 736 (atras do painel da UI): copa densa escura."""
    c.rect(L.PANEL[0], 0, L.W, L.H, "bush_dark")
    items = []
    for j in range(0, 12):
        for i in range(0, 7):
            x = 736 + 8 + i * 36 + (18 if j % 2 else 0)
            items.append((j * 46 + 24, x, (i + j) % 5))
    for yb, x, s in sorted(items):
        put(c, tree_sprite(40, 48, s), x, yb)


def draw_lamps(c):
    for x, y in L.LAMPS:
        c.rect(x + 3, y - 22, x + 5, y, "wood_dark")
        c.rect(x + 2, y - 22, x + 3, y, "wood")
        base = m_rect(c, x, y - 3, 8, 4)
        shaded(c, base, "stone", "stone_light", "stone_dark", depth=1)
        c.rect(x - 1, y - 36, x + 9, y - 33, "outline")
        c.rect(x, y - 35, x + 8, y - 34, "wood_dark")
        c.rect(x, y - 33, x + 8, y - 23, "outline")
        c.rect(x + 1, y - 32, x + 7, y - 24, "yellow")
        c.rect(x + 1, y - 32, x + 3, y - 30, "cream_light")
        c.rect(x + 3, y - 33, x + 5, y - 32, "outline")
        LAMP_GLASS.append((x + 1, y - 32, x + 7, y - 24))


# ------------------------------------------------------------------ montagem
def build_dia():
    c = Canvas(L.W, L.H, "grass_dark")
    # fora: grama escura com manchas chapadas
    pm = noise_patches(L.W, L.H, thr=2.0, seed=11)
    c.paint(pm, "grass")
    # piso proprio de cada cercado
    ax, ay, aw, ah = L.RECTS["adultos"]
    fill_zone(c, ax - 0, ay, aw, ah, "grass", "grass_light", 21)
    bx, by, bw, bh = L.RECTS["breed"]
    fill_zone(c, bx, by, bw, bh, "dirt", "dirt_light", 22)
    fx, fy, fw, fh = L.RECTS["filhotes"]
    fill_zone(c, fx, fy, fw, fh, "grass_light", "grass", 23)
    pmask = draw_paths(c)
    keep = ~pmask
    # tufos e flores (fora dos caminhos)
    scatter(c, 0, 0, 736, L.H, "grass_dark", 0.16, 0.03, keep)
    scatter(c, ax, ay, aw, ah, "grass", 0.24, 0.05, keep)
    scatter(c, fx, fy, fw, fh, "grass_light", 0.22, 0.06, keep)
    dirt_speckle(c, bx, by, bw, bh, keep)
    # as manchas de fora so aparecem fora (os pisos acima ja cobrem); re-aplica piso nas bordas dos caminhos
    draw_fences(c)
    draw_vegetation(c)
    draw_forest(c)
    draw_lamps(c)
    return c


def tint_table(img, tint, lit):
    a = np.asarray(img.convert("RGB")).astype(np.float32)
    out = np.clip(a * (np.array(tint, np.float32) / 255.0), 0, 255).round().astype(np.uint8)
    if lit:
        for x0, y0, x1, y1 in LAMP_GLASS:
            out[y0:y1, x0:x1] = np.asarray(img.convert("RGB"))[y0:y1, x0:x1]
    return Image.fromarray(out, "RGB")


def main():
    dia = build_dia()
    base = Image.fromarray(dia.a[..., :3].copy(), "RGB")
    bad = pal_check(dia.a)
    assert not bad, bad
    base.save(os.path.join(L.PEN, "pen_bg_dia.png"))
    for p in ("amanhecer", "entardecer", "noite"):
        tint_table(base, L.TINT[p], p in ("entardecer", "noite")).save(os.path.join(L.PEN, f"pen_bg_{p}.png"))
    print("bg ok; cores:", len({tuple(x) for x in np.asarray(base).reshape(-1, 3)}))


if __name__ == "__main__":
    main()
