"""T8.4: tabuleiro final 960x540 (2 temas), pecas de UI e previews. Pillow, sem IA.
Uso: python assets/tools/build_t84_board.py
"""
import json
import os
import random
from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
BOARD = os.path.join(ROOT, "assets", "board", "final")
UI = os.path.join(ROOT, "assets", "ui")
PREV = os.path.join(ROOT, "reports", "arte")
for d in (BOARD, UI, PREV):
    os.makedirs(d, exist_ok=True)


def h(c):
    return tuple(int(c[i:i + 2], 16) for i in (1, 3, 5)) + (255,)


THEMES = {
    # A: taverna (feltro verde-petroleo escuro + madeira + ouro velho)
    "taverna": dict(
        felt=h("#1f3a34"), felt_hi=h("#244338"), felt_lo=h("#1a312c"),
        side=h("#17261f"), band=h("#201714"),
        frame_dk=h("#1a1114"), frame=h("#4a3022"), frame_hi=h("#6b4a31"),
        frame_lo=h("#2b1d1a"), gold=h("#c9a24a"), gold_dk=h("#8a6a2c"),
        plate=h("#2b1d1a"), plate_in=h("#15231d"), glow=h("#e8d28a"),
    ),
    # B: jardim noturno (pedra azul + prata/ouro palido)
    "noturno": dict(
        felt=h("#232a3f"), felt_hi=h("#2a3350"), felt_lo=h("#1d2335"),
        side=h("#141a2b"), band=h("#101526"),
        frame_dk=h("#0b0f1c"), frame=h("#3d4a6e"), frame_hi=h("#5d6c96"),
        frame_lo=h("#252d47"), gold=h("#d9b65c"), gold_dk=h("#8d7a46"),
        plate=h("#1a2036"), plate_in=h("#0f1424"), glow=h("#9fd8c4"), orn=True,
    ),
}


def rect(d, r, fill=None, outline=None):
    x, y, w, hh = r
    d.rectangle([x, y, x + w - 1, y + hh - 1], fill=fill, outline=outline)


def bevel_plate(d, r, t, inset=True):
    """Lugar rebaixado (inset) ou elevado: preenchimento + borda 1px clara/escura."""
    x, y, w, hh = r
    fill = t["plate_in"] if inset else t["plate"]
    d.rectangle([x, y, x + w - 1, y + hh - 1], fill=fill, outline=t["frame_dk"])
    d.line([x + 1, y + hh - 2, x + w - 2, y + hh - 2], fill=t["frame_lo"] if inset else t["frame"])
    d.line([x + w - 2, y + 1, x + w - 2, y + hh - 2], fill=t["frame_lo"] if inset else t["frame"])
    d.line([x + 1, y + 1, x + w - 2, y + 1], fill=t["frame_dk"] if inset else t["frame_hi"])
    # cantos cortados
    for cx, cy in ((x, y), (x + w - 1, y), (x, y + hh - 1), (x + w - 1, y + hh - 1)):
        d.point((cx, cy), fill=(0, 0, 0, 0))


def diamond(d, cx, cy, r, fill, outline=None):
    pts = [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)]
    d.polygon(pts, fill=fill, outline=outline)


def ornament(d, cx, cy, t):
    """Pequeno losango dourado com miolo."""
    diamond(d, cx, cy, 5, t["gold_dk"], t["frame_dk"])
    diamond(d, cx, cy, 3, t["gold"])
    d.point((cx, cy), fill=t["glow"])


def texture(img, t, region, seed):
    rng = random.Random(seed)
    x0, y0, x1, y1 = region
    px = img.load()
    for y in range(y0, y1):
        for x in range(x0, x1):
            # trama discreta de feltro: pontos claros em grade 8 + ruido raro
            if (x % 8 == 0 and y % 8 == 0) or (x % 8 == 4 and y % 8 == 4):
                px[x, y] = t["felt_hi"]
            else:
                r = rng.random()
                if r < 0.025:
                    px[x, y] = t["felt_hi"]
                elif r < 0.05:
                    px[x, y] = t["felt_lo"]


def leader_plate(d, t, top):
    """Faixa do Lider: placa ornamentada centralizada (x 372..628)."""
    x0, x1 = 372, 588 + 40
    if top:
        y0, y1 = 0, 66
    else:
        y0, y1 = 316, 382
    d.rectangle([x0, y0, x1, y1], fill=t["band"], outline=t["frame_dk"])
    d.rectangle([x0 + 2, y0 + 2, x1 - 2, y1 - 2], outline=t["frame"])
    d.rectangle([x0 + 3, y0 + 3, x1 - 3, y1 - 3], outline=t["gold_dk"])
    # tampa a borda externa (topo encosta na moldura da tela; base encosta no campo)
    if top:
        d.rectangle([x0 - 1, y0, x1 + 1, y0 + 1], fill=t["frame_dk"])
    for ox in (x0 + 2, x1 - 2):
        ornament(d, ox, (y0 + y1) // 2, t)
    # retrato: medalhao (450,2,60,56) / (450,322,60,56)
    py = 2 if top else 322
    bevel_plate(d, (448, py - 1, 64, 58), t, inset=True)
    # lugar da gema de HP e poder (placas pequenas)
    gy = 44 if top else 364
    bevel_plate(d, (540, 10 if top else 330, 40, 40), t, inset=True)


def frame_screen(d, t):
    W, H = 960, 540
    # moldura externa 6px
    d.rectangle([0, 0, W - 1, H - 1], outline=t["frame_dk"])
    d.rectangle([1, 1, W - 2, H - 2], outline=t["frame_hi"])
    d.rectangle([2, 2, W - 3, H - 3], outline=t["frame"])
    d.rectangle([3, 3, W - 4, H - 4], outline=t["frame_lo"])
    d.rectangle([4, 4, W - 5, H - 5], outline=t["gold_dk"])
    d.rectangle([5, 5, W - 6, H - 6], outline=t["frame_dk"])
    for cx, cy in ((10, 10), (W - 11, 10), (10, H - 11), (W - 11, H - 11)):
        ornament(d, cx, cy, t)
    for cx in (480,):
        ornament(d, cx, 3, t)
        ornament(d, cx, H - 4, t)


PAW = ["..#...#..", ".###.###.", ".###.###.", "..#...#..", "....#....", "..#####..", ".#######.", ".#######.", "..#.#.#.."]
PAW = ["...#..#...", "..##..##..", "#..#..#..#", "##......##", "..........", "....##....", "..######..", ".########.", ".###..###.", "..##..##.."]


def star(d, x, y, t, big=False):
    if big:
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            d.point((x + dx, y + dy), fill=t["glow"] if (dx, dy) == (0, 0) else t["frame_hi"])
    else:
        d.point((x, y), fill=t["frame_hi"])


def constel(d, pts, t, big=(0,)):
    for a, b in zip(pts, pts[1:]):
        d.line([a, b], fill=t["frame"])
    for i, (x, y) in enumerate(pts):
        star(d, x, y, t, i in big)


def paw(d, cx, cy, col):
    for y, row in enumerate(PAW):
        for x, ch in enumerate(row):
            if ch == "#":
                d.point((cx - 5 + x, cy - 5 + y), fill=col)


def corner_filigree(d, t, fx, fy):
    """Filigrana no canto interno da moldura; fx/fy = +1 ou -1 (espelho)."""
    ox = 12 if fx > 0 else 947
    oy = 12 if fy > 0 else 527
    P = lambda x, y: (ox + fx * x, oy + fy * y)
    for k in range(4, 34):
        d.point(P(k, 0), fill=t["frame"])
        d.point(P(0, k), fill=t["frame"])
    for k in range(6, 24, 4):
        d.point(P(k, 2), fill=t["frame_hi"])
        d.point(P(2, k), fill=t["frame_hi"])
    d.point(P(34, 0), fill=t["gold_dk"])
    d.point(P(0, 34), fill=t["gold_dk"])
    for x, y in ((3, 3), (4, 3), (3, 4), (5, 5)):
        d.point(P(x, y), fill=t["gold"])
    star(d, *P(40, 0), t)
    star(d, *P(0, 40), t)


def ornament_noturno(img, t):
    d = ImageDraw.Draw(img)
    for fx in (1, -1):
        for fy in (1, -1):
            corner_filigree(d, t, fx, fy)
    # constelacoes nos cantos livres das faixas dos Lideres (x 164..372 e 628..796)
    constel(d, [(176, 14), (196, 26), (214, 18), (236, 34), (262, 28)], t, (0, 3))
    constel(d, [(300, 10), (322, 22), (346, 12)], t, (1,))
    constel(d, [(786, 48), (764, 36), (742, 46), (716, 30)], t, (0, 2))
    constel(d, [(680, 12), (660, 24), (638, 14)], t, (1,))
    constel(d, [(176, 366), (198, 352), (220, 362), (244, 346)], t, (0, 2))
    constel(d, [(300, 372), (324, 358), (348, 368)], t, (1,))
    constel(d, [(784, 336), (762, 350), (738, 340), (712, 356)], t, (0, 2))
    constel(d, [(676, 370), (656, 358), (634, 368)], t, (1,))
    # patas sutis no centro de cada slot (so aparecem em slot vazio)
    col = t["felt_hi"]
    for n in range(5):
        for y0 in (62, 194):
            paw(d, 164 + 128 * n + 60, y0 + 62, col)
    # faixa da mao: fieira de losangos e constelacoes laterais
    for x in range(30, 930, 24):
        d.point((x, 388), fill=t["frame"])
        d.point((x + 12, 388), fill=t["gold_dk"])
    for x in (12, 947):
        diamond(d, x, 388, 3, t["gold_dk"], t["frame_dk"])
    constel(d, [(18, 470), (30, 452), (22, 432), (36, 416)], t, (0, 2))
    constel(d, [(724, 520), (744, 506), (762, 516)], t, (1,))
    # placas dos Lideres: asas de filigrana + estrelas
    for top in (True, False):
        yc = 33 if top else 349
        for sgn, xe in ((-1, 372), (1, 628)):
            for k in range(1, 22):
                d.point((xe + sgn * k, yc), fill=t["frame"] if k % 3 else t["gold_dk"])
            star(d, xe + sgn * 24, yc, t, True)
        for ox in (392, 608):
            star(d, ox, yc - 16, t)
            star(d, ox, yc + 16, t)
            d.point((ox - 1, yc - 16), fill=t["frame"])
            d.point((ox + 1, yc - 16), fill=t["frame"])
        d.line([380, 6 if top else 322, 620, 6 if top else 322], fill=t["frame"])


def build_board(name):
    t = THEMES[name]
    img = Image.new("RGBA", (960, 540), t["felt"])
    d = ImageDraw.Draw(img)
    # laterais e mao: mais escuras e lisas (nao competem com as cartas)
    rect(d, (0, 0, 160, 540), fill=t["side"])
    rect(d, (800, 0, 160, 540), fill=t["side"])
    rect(d, (0, 382, 960, 158), fill=t["band"])
    # campo central
    texture(img, t, (164, 62, 796, 318), 1)
    texture(img, t, (160, 318, 800, 382), 2)
    texture(img, t, (160, 0, 800, 62), 3)
    d = ImageDraw.Draw(img)
    # bordas suaves do campo (sombra 1px, sem caixa por slot)
    d.line([164, 61, 795, 61], fill=t["frame_dk"])
    d.line([164, 318, 795, 318], fill=t["frame_dk"])
    d.line([164, 62, 795, 62], fill=t["felt_lo"])
    d.line([164, 317, 795, 317], fill=t["felt_lo"])
    # linha central discreta + losango
    d.line([164, 190, 460, 190], fill=t["felt_lo"])
    d.line([500, 190, 795, 190], fill=t["felt_lo"])
    diamond(d, 480, 190, 4, t["gold_dk"], t["frame_dk"])
    # divisorias verticais entre laterais e campo
    for x in (160, 799):
        d.line([x, 6, x, 381], fill=t["frame_dk"])
        d.line([x + (1 if x == 160 else -1), 6, x + (1 if x == 160 else -1), 381], fill=t["frame"])
    # topo da mao
    d.line([6, 381, 953, 381], fill=t["frame_dk"])
    d.line([6, 382, 953, 382], fill=t["gold_dk"])
    d.line([6, 383, 953, 383], fill=t["frame"])
    # lideres
    leader_plate(d, t, True)
    leader_plate(d, t, False)
    # lugares (paineis esquerdos, baralhos, fim de turno, energia)
    for r in ((6, 6, 150, 40), (6, 50, 150, 50), (6, 104, 150, 228), (6, 336, 150, 42)):
        bevel_plate(d, r, t, inset=True)
    bevel_plate(d, (802, 6, 156, 80), t, inset=True)       # baralho inimigo
    bevel_plate(d, (802, 390, 156, 88), t, inset=True)     # baralho jogador
    bevel_plate(d, (802, 154, 156, 72), t, inset=False)    # fim de turno
    bevel_plate(d, (778, 486, 180, 50), t, inset=True)     # energia
    frame_screen(d, t)
    if t.get("orn"):
        ornament_noturno(img, t)
    img.save(os.path.join(BOARD, f"board_{name}.png"))
    return img


# ------------------------------------------------------------------ pecas de UI
def piece(size, fn):
    im = Image.new("RGBA", size, (0, 0, 0, 0))
    fn(ImageDraw.Draw(im), im)
    return im


def gem(d, r, fill, lt, dk, ol, glint=True):
    cx = cy = r
    diamond(d, cx, cy, r - 1, ol)
    diamond(d, cx, cy, r - 2, dk)
    diamond(d, cx, cy, r - 4, fill)
    if glint:
        d.line([cx - r // 3, cy - r // 3, cx, cy - r // 2 - 1], fill=lt)
        d.point((cx - r // 3, cy - r // 3), fill=(255, 255, 255, 255))


def button(t, state):
    W, H = 152, 64
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if state == "desabilitado":
        top, base, low = h("#4a4f4c"), h("#3b403d"), h("#2c302e")
        edge = h("#202422")
    elif state == "hover":
        top, base, low = h("#6fd078"), h("#4cb85a"), h("#2f8a3e")
        edge = h("#16381c")
    else:
        top, base, low = h("#4cb85a"), h("#38a048"), h("#26762f")
        edge = h("#16381c")
    d.rounded_rectangle([0, 0, W - 1, H - 1], 6, fill=edge)
    d.rounded_rectangle([2, 2, W - 3, H - 3], 5, fill=low)
    d.rounded_rectangle([2, 2, W - 3, H - 8], 5, fill=base)
    d.line([6, 3, W - 7, 3], fill=top)
    d.line([4, 4, 4, H - 10], fill=top)
    # parafusos dourados
    for p in ((8, 8), (W - 9, 8), (8, H - 9), (W - 9, H - 9)):
        d.point(p, fill=t["gold"] if state != "desabilitado" else h("#707573"))
    return im


def tooltip_panel(t):
    S = 48
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, S - 1, S - 1], 5, fill=t["frame_dk"])
    d.rounded_rectangle([1, 1, S - 2, S - 2], 4, outline=t["gold_dk"], fill=h("#14101a"))
    d.rounded_rectangle([3, 3, S - 4, S - 4], 3, fill=h("#1c1724"))
    for p in ((2, 2), (S - 3, 2), (2, S - 3), (S - 3, S - 3)):
        d.point(p, fill=t["gold"])
        if t.get("orn"):
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                d.point((p[0] + dx, p[1] + dy), fill=t["gold_dk"])
    return im


def deck_frame(t):
    W, H = 152, 76
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, W - 1, H - 1], 5, fill=t["frame_dk"])
    d.rounded_rectangle([1, 1, W - 2, H - 2], 4, outline=t["frame_hi"], fill=t["plate"])
    d.rounded_rectangle([3, 3, W - 4, H - 4], 3, outline=t["gold_dk"], fill=t["plate_in"])
    for p in ((6, 6), (W - 7, 6), (6, H - 7), (W - 7, H - 7)):
        d.point(p, fill=t["gold"])
        if t.get("orn"):
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                d.point((p[0] + dx, p[1] + dy), fill=t["gold_dk"])
    if t.get("orn"):
        for x in range(20, W - 20, 6):
            d.point((x, 2), fill=t["frame_hi"])
            d.point((x, H - 3), fill=t["frame_hi"])
    return im


def build_ui(name):
    t = THEMES[name]
    out = os.path.join(UI, name)
    os.makedirs(out, exist_ok=True)
    pieces = {}

    def save(key, im, nine=None):
        im.save(os.path.join(out, key + ".png"))
        e = {"file": f"{name}/{key}.png", "w": im.width, "h": im.height}
        if nine:
            e["nine_slice"] = nine
        pieces[key] = e

    g = lambda fill, lt, dk, ol: piece((24, 24), lambda d, im: gem(d, 12, fill, lt, dk, ol))
    save("energia_cheia", g(h("#5fb8ff"), h("#c4e8ff"), h("#2e73c4"), h("#10224a")))
    save("energia_vazia", g(h("#1b2540"), h("#34456e"), h("#141c33"), h("#0a0f1c")))
    hp = piece((40, 40), lambda d, im: gem(d, 20, h("#e04a4a"), h("#ff9a9a"), h("#a02828"), h("#3a0f14"), glint=False))
    save("hp_lider", hp)
    for st in ("normal", "hover", "desabilitado"):
        save(f"botao_fim_turno_{st}", button(t, st), nine=[8, 8, 8, 12])
    save("tooltip", tooltip_panel(t), nine=[8, 8, 8, 8])
    save("baralho_moldura", deck_frame(t), nine=[8, 8, 8, 8])
    with open(os.path.join(out, "ui.json"), "w", encoding="utf-8") as f:
        json.dump({"tema": name, "pieces": pieces,
                   "nota": "nine_slice = [esq, topo, dir, base] em px; botoes sem texto"}, f, indent=2)
    return out


# ------------------------------------------------------------------ preview
def card(face, sprite, tint):
    c = Image.new("RGBA", (120, 124), (0, 0, 0, 0))
    d = ImageDraw.Draw(c)
    d.rectangle([0, 0, 119, 123], fill=h("#2a2030"), outline=h("#0d0a12"))
    c.alpha_composite(Image.open(sprite).convert("RGBA"), (12, 1))
    d.rectangle([2, 100, 117, 121], fill=tint)
    return c


def preview(name):
    t = THEMES[name]
    img = Image.open(os.path.join(BOARD, f"board_{name}.png")).convert("RGBA")
    A = os.path.join(ROOT, "assets")
    cats = [f"{A}/cats96/{n}.png" for n in ("siames", "persa", "sphynx", "maine-coon", "vira-lata")]
    sps = [f"{A}/specials96/{n}.png" for n in ("trovao-amarelo", "pelo-de-aco", "gata-das-brasas", "sombra-miuda", "velha-dos-novelos")]
    for n in range(5):
        img.alpha_composite(card(None, sps[n], h("#d9a060")), (164 + 128 * n, 62))
        if n != 3:
            img.alpha_composite(card(None, cats[n], h("#c9b890")), (164 + 128 * n, 194))
    hand = [cats[1], cats[0], cats[2], cats[3], cats[4]]
    for i, p in enumerate(hand):
        img.alpha_composite(card(None, p, h("#c9b890")), (30 + i * 140, 398))
    for top, nm in ((True, "irmaos-pimenta"), (False, "heroi")):
        L = Image.open(f"{A}/leaders/{nm}.png").convert("RGBA").resize((56, 56), Image.NEAREST)
        img.alpha_composite(L, (452, 2 if top else 322))
    ui = os.path.join(UI, name)
    hpg = Image.open(f"{ui}/hp_lider.png")
    img.alpha_composite(hpg.resize((38, 38), Image.NEAREST), (493, 25))
    img.alpha_composite(hpg.resize((38, 38), Image.NEAREST), (493, 345))
    img.alpha_composite(Image.open(f"{ui}/botao_fim_turno_normal.png"), (804, 158))
    for i in range(7):
        k = "energia_cheia" if i < 3 else "energia_vazia"
        img.alpha_composite(Image.open(f"{ui}/{k}.png"), (784 + 24 * i, 500))
    # tooltip 9-slice de amostra 200x80
    tp = Image.open(f"{ui}/tooltip.png")
    tw, th = 120, 80
    box = Image.new("RGBA", (tw, th), (0, 0, 0, 0))
    S, m = 48, 8
    xs = [(0, m, 0, m), (m, S - m, m, tw - m), (S - m, S, tw - m, tw)]
    ys = [(0, m, 0, m), (m, S - m, m, th - m), (S - m, S, th - m, th)]
    for sx0, sx1, dx0, dx1 in xs:
        for sy0, sy1, dy0, dy1 in ys:
            part = tp.crop((sx0, sy0, sx1, sy1)).resize((dx1 - dx0, dy1 - dy0), Image.NEAREST)
            box.alpha_composite(part, (dx0, dy0))
    img.alpha_composite(box, (548, 222))
    img.convert("RGB").save(os.path.join(PREV, f"preview_tabuleiro_final_{name}.png"))


if __name__ == "__main__":
    for n in THEMES:
        build_board(n)
        build_ui(n)
        preview(n)
    print("ok")
