"""Desenho do Criatorio animado (hub): cercado vivo, painel lateral, ficha do gato.

So desenho; o estado vem de `HubController` / `PenController`. Gatos ordenados por y (fundo para a
frente). Arte do cercado via `ui.pen_sprites` (com fallback por codigo).
"""
from __future__ import annotations

import math

import pygame

from ui import font, layout_pen as LP, pen_sprites, widgets as Wd
from ui.daycycle import DayState, day_state
from ui.hub_controller import HubController
from ui.pen_controller import Heart, PenCat
from ui.render import UIState, border, mix_c, pulse, text_fit, tint
from ui.render_hub import draw_detail, draw_donate_confirm, draw_rename
from ui.theme import C, H, W
from ui.widgets import WHITE, button, panel

_HEART = ("..#.#..", ".#####.", ".#####.", "..###..", "...#...")
_heart_cache: dict[tuple, pygame.Surface] = {}
STATE_TAG = {"deck": "deck", "breed": "breed", "filhote": "filhote"}


def heart(color, scale: int = 2) -> pygame.Surface:
    k = (color, scale)
    s = _heart_cache.get(k)
    if s is None:
        s = pygame.Surface((7 * scale, 5 * scale), pygame.SRCALPHA)
        for yy, row in enumerate(_HEART):
            for xx, ch in enumerate(row):
                if ch == "#":
                    pygame.draw.rect(s, color, (xx * scale, yy * scale, scale, scale))
        _heart_cache[k] = s
    return s


# ------------------------------------------------------------------ cenario
FRONT_AMBIENT = ("vagalumes", "folhas")


def draw_floor(surf: pygame.Surface, art: pen_sprites.PenArt, day: DayState) -> None:
    """Fundo do periodo; no crossfade desenha o proximo fundo por cima com alpha."""
    base = art.background(day.period)
    if base is None:
        a = LP.area_rect(art.geo).inflate(16, 16)
        tint(surf, a, (10, 12, 24), 120)
        border(surf, a, C["panel_edge"], 2)
        return
    surf.blit(base, (0, 0))
    nxt = art.background(day.next)
    if day.mix > 0.004 and nxt is not None and nxt is not base:
        nxt.set_alpha(int(255 * day.mix))
        surf.blit(nxt, (0, 0))
        nxt.set_alpha(255)


_glow_cache: dict[tuple, pygame.Surface] = {}


def glow(radius: int, level: int) -> pygame.Surface:
    """Brilho radial quente para blit ADITIVO; `level` 1..8 (intensidade quantizada, com cache)."""
    k = (radius, level)
    g = _glow_cache.get(k)
    if g is None:
        g = pygame.Surface((radius * 2, radius * 2))
        for r in range(radius, 0, -2):
            f = (1 - r / radius) ** 2 * level / 8.0
            pygame.draw.circle(g, (int(120 * f), int(78 * f), int(26 * f)), (radius, radius), r)
        _glow_cache[k] = g
    return g


def draw_glow(surf: pygame.Surface, cx: int, cy: int, radius: int, strength: float) -> None:
    level = round(max(0.0, min(1.0, strength)) * 8)
    if level > 0:
        surf.blit(glow(radius, level), (cx - radius, cy - radius), special_flags=pygame.BLEND_RGB_ADD)


PHASE_DIV = 6.0          # a.phase (graus de defasagem do ambiente) -> segundos
AMBIENT_STAGGER = 0.37   # defasagem por indice quando o ambiente nao traz phase
FOOT_PAD = 3             # px transparentes sob os pes no quadro do gato


def draw_ambient(surf: pygame.Surface, art: pen_sprites.PenArt, t: float, back: bool,
                 day: DayState | None = None) -> None:
    day = day or day_state()
    lit = day.weight_of(art.geo.lantern_on)
    tint_c = art.tint_for(day)
    for i, a in enumerate(art.geo.ambient):
        if (a.kind not in FRONT_AMBIENT) != back or a.x >= LP.panel_rect(art.geo).x:
            continue
        w = day.weight_of(a.periods)
        if w <= 0.01:
            continue
        lamp = a.kind == "lanterna"
        anim = "idle"
        if lamp:
            want = "on" if lit >= 0.5 else "off"
            anim = want if art.has_anim(a.kind, want, True) else "idle"
        img = art.ambient_frame(a.kind, t + a.phase / PHASE_DIV + (0 if a.phase else i * AMBIENT_STAGGER), anim)
        if img is not None:
            ax, ay = art.anchor(a.kind, True)
            if a.kind not in ("vagalumes",) and not (lamp and anim == "on"):
                img = art.tinted(img, tint_c)
            if w < 0.99:
                img = img.copy()
                img.set_alpha(int(255 * w))
            surf.blit(img, (int(a.x) - ax, int(a.y) - ay))
            if lamp:
                fw, fh = img.get_size()
                flick = 0.92 + 0.08 * math.sin(t * 5 + i)       # cabeca da lanterna ~ (54%, 50%) do quadro
                draw_glow(surf, int(a.x) - ax + int(fw * 0.54), int(a.y) - ay + fh // 2, 34, lit * w * flick)
        elif w >= 0.5:
            _ambient_shape(surf, a.kind, a.x, a.y, t + i * 1.7, lit)


def _ambient_shape(surf: pygame.Surface, kind: str, x: float, y: float, t: float, lit: float = 1.0) -> None:
    if kind == "lanterna":
        pygame.draw.rect(surf, (70, 56, 48), (int(x) - 1, int(y) - 22, 3, 22))
        pygame.draw.rect(surf, mix_c((90, 84, 80), (255, 214, 120), lit), (int(x) - 3, int(y) - 28, 6, 6))
        draw_glow(surf, int(x), int(y) - 25, 30, lit * (0.9 + 0.1 * math.sin(t * 7)))
    elif kind == "vagalumes":
        for k in range(5):
            ph = t * 0.5 + k * 1.3
            fx, fy = x + math.sin(ph * 1.3 + k) * 38, y + math.cos(ph + k * 2) * 22
            if math.sin(t * 2 + k * 2.4) > -0.2:
                pygame.draw.rect(surf, (230, 255, 130), (int(fx), int(fy), 2, 2))


def bed_frame(art: pen_sprites.PenArt, o) -> pygame.Surface | None:
    """Cama: `idle` estatico; `enter`/`exit` tocam UMA vez (quando o gato deita / levanta)."""
    if o.sleepers > 0 and art.has_anim(o.kind, "enter"):        # ocupada: segura o ultimo quadro do enter
        return art.object_frame(o.kind, "enter", o.oneshot_t if o.oneshot == "enter" else 1e6, once=True)
    if o.oneshot == "exit" and art.has_anim(o.kind, "exit") and o.oneshot_t < art.anim_duration(o.kind, "exit"):
        return art.object_frame(o.kind, "exit", o.oneshot_t, once=True)
    return art.object_frame(o.kind, "idle", 0.0)


def draw_object(surf: pygame.Surface, art: pen_sprites.PenArt, o, hovered: bool, day: DayState | None = None) -> None:
    x, y = int(o.spec.x + o.ox), int(o.spec.y + o.oy)
    if hovered and o.spec.slots:
        pygame.draw.ellipse(surf, C["warn"], pygame.Rect(x - 20, y - 6, 40, 11), 1)
    img = bed_frame(art, o) if o.is_bed else art.object_frame(o.kind, "use" if o.using else "idle", o.t)
    if img is not None:
        ax, ay = art.anchor(o.kind)
        surf.blit(art.tinted(img, art.tint_for(day)), (x - ax, y - ay))
    else:
        _object_shape(surf, o.kind, x, y, o.using and not o.is_bed, o.t)


def _ell(surf, col, cx, cy, w, h) -> None:
    pygame.draw.ellipse(surf, col, pygame.Rect(cx - w // 2, cy - h // 2, w, h))


def _object_shape(surf: pygame.Surface, kind: str, x: int, y: int, using: bool, t: float) -> None:
    """Forma simples de reserva (sem arte), animada por codigo."""
    breathe = 0
    if kind in ("cama_almofada", "cama_cesto", "cama_pedra", "viveiro_cesto"):
        base = {"cama_almofada": (150, 80, 110), "cama_cesto": (150, 112, 62), "cama_pedra": (96, 100, 118),
                "viveiro_cesto": (176, 128, 70)}[kind]
        _ell(surf, mix_c(base, (0, 0, 0), 0.4), x, y - 5, 50 + breathe, 16)
        _ell(surf, base, x, y - 8, 44 + breathe, 13)
        _ell(surf, mix_c(base, WHITE, 0.25), x, y - 9, 28, 7)
    elif kind == "cama_casal":
        _ell(surf, (90, 40, 70), x, y - 5, 74 + breathe, 20)
        _ell(surf, (178, 84, 120), x, y - 9, 66 + breathe, 16)
        _ell(surf, (214, 128, 160), x, y - 10, 44, 8)
    elif kind in ("novelo", "bola_filhote"):
        r = 5 if kind == "bola_filhote" else 6
        hop = -round(abs(math.sin(t * 6)) * 5) if using else 0
        col = (240, 200, 70) if kind == "bola_filhote" else (210, 70, 80)
        _ell(surf, (0, 0, 0), x, y - 1, 12, 4)
        pygame.draw.circle(surf, col, (x, y - r + hop), r)
        pygame.draw.line(surf, mix_c(col, WHITE, 0.4), (x - r + 2, y - r + hop), (x + r - 2, y - r + hop - 2))
    elif kind == "ratinho":
        wig = round(math.sin(t * 10)) if using else 0
        _ell(surf, (150, 150, 160), x, y - 5, 16, 9)
        pygame.draw.circle(surf, (190, 150, 160), (x + 7, y - 9), 2)
        pygame.draw.line(surf, (200, 150, 160), (x - 8, y - 5), (x - 15, y - 7 + wig))
    elif kind in ("casinha", "casinha_filhote"):
        w, h = (46, 30) if kind == "casinha_filhote" else (64, 44)
        pygame.draw.rect(surf, (140, 100, 70), (x - w // 2, y - h + 10, w, h - 10))
        pygame.draw.polygon(surf, (170, 70, 60), [(x - w // 2 - 4, y - h + 12), (x, y - h - 6), (x + w // 2 + 4, y - h + 12)])
        pygame.draw.rect(surf, (40, 28, 24), (x - 7, y - 16, 14, 16))
    elif kind == "banco_arvore":
        pygame.draw.rect(surf, (96, 70, 46), (x - 4, y - 22, 8, 22))
        _ell(surf, (120, 90, 60), x, y - 24, 44, 12)
        _ell(surf, (150, 116, 78), x, y - 25, 36, 8)
    elif kind == "tunel_filhote":
        _ell(surf, (70, 100, 150), x, y - 9, 50, 22)
        _ell(surf, (24, 30, 46), x + 18, y - 9, 10, 16)
    elif kind == "tigela":
        _ell(surf, (190, 70, 60), x, y - 3, 18, 7)
        _ell(surf, (120, 70, 50), x, y - 5, 12, 4)
    elif kind == "arranhador":
        pygame.draw.rect(surf, (96, 70, 46), (x - 10, y - 4, 20, 4))
        pygame.draw.rect(surf, (190, 150, 90), (x - 4, y - 28, 8, 24))
        if using:
            pygame.draw.line(surf, (230, 200, 140), (x - 4, y - 14 + round(math.sin(t * 9) * 4)), (x + 3, y - 12))
    else:
        pygame.draw.rect(surf, (140, 140, 160), (x - 6, y - 10, 12, 10))


# ------------------------------------------------------------------ gatos
def _shadow(surf: pygame.Surface, c: PenCat) -> None:
    w, h = (22, 7) if c.kitten else (32, 9)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (0, 0, 0, int(90 * c.fade)), s.get_rect())
    surf.blit(s, (int(c.x) - w // 2, int(c.y) - h // 2 - 1))


def draw_cat(surf: pygame.Surface, c: PenCat, art: pen_sprites.PenArt, ui: UIState, hovered: bool,
             selected: bool, day: DayState | None = None) -> None:
    _shadow(surf, c)
    if selected:
        pygame.draw.ellipse(surf, WHITE, pygame.Rect(int(c.x) - 20, int(c.y) - 7, 40, 12), 1)
    elif hovered:
        pygame.draw.ellipse(surf, C["warn"], pygame.Rect(int(c.x) - 18, int(c.y) - 6, 36, 10), 1)
    img = art.tinted(art.frame(c.breed, c.kitten, c.anim, c.t, flip=c.facing < 0), art.tint_for(day))
    bob = -round(abs(math.sin(c.t * 9)) * 2) if c.state == "react" else 0
    if c.fade < 1.0:
        img = img.copy()
        img.set_alpha(int(255 * c.fade))
    surf.blit(img, (int(c.x) - img.get_width() // 2, int(c.y) - (art.frame_size[1] - FOOT_PAD) + bob))
    top = int(c.y) - img.get_height() + 8
    if c.state == "sleep":
        zi = art.fx("z")
        for k in range(2):
            ph = (c.t * 0.6 + k * 0.5) % 1.0
            zx, zy = int(c.x) + 8 + k * 8 + int(ph * 4), top + 10 - int(ph * 16) - k * 6
            if zi is not None:
                zi = zi.copy()
                zi.set_alpha(int(255 * (1 - ph)))
                surf.blit(zi, (zx, zy))
            else:
                font.draw(surf, "Z", zx, zy, mix_c(C["dim"], C["bg"], ph), 1)
    elif c.state == "play" and art.fx("note") is not None:
        n = art.fx("note")
        surf.blit(n, (int(c.x) + 10, top + 4 - round(abs(math.sin(c.t * 4)) * 4)))
    if c.tag == "breed" and c.state != "sleep":
        h = art.fx("heart") or heart(C["female"], 2)
        surf.blit(h, (int(c.x) - h.get_width() // 2, top - 6 + round(math.sin(c.t * 3))))


def draw_hearts(surf: pygame.Surface, hearts: list[Heart], art: pen_sprites.PenArt) -> None:
    for h in hearts:
        k = h.age / h.ttl
        img = (art.fx("heart", 2) or heart((255, 96, 140), 2)).copy()
        img.set_alpha(int(255 * (1 - k * k)))
        surf.blit(img, (int(h.x) - img.get_width() // 2, int(h.y)))


def hover_text(hub: HubController, cat_id: str) -> str:
    cat = next((c for c in hub.save.cats if c.id == cat_id), None)
    if cat is None:
        return ""
    st = STATE_TAG.get(hub.col.state_of(cat), "")
    return hub.pen_label(cat_id) + (f" ({st})" if st else "")


def draw_hover(surf: pygame.Surface, hub: HubController, c: PenCat, sprite_h: int) -> None:
    txt = hover_text(hub, c.cat_id)
    w = font.width(txt, 1) + 14
    r = pygame.Rect(int(c.x) - w // 2, int(c.y) - sprite_h - 6, w, font.CAP_H + 10)
    r.clamp_ip(pygame.Rect(4, 4, W - 8, H - 8))
    pygame.draw.rect(surf, C["dark"], r, border_radius=4)
    pygame.draw.rect(surf, C["warn"], r, 1, border_radius=4)
    font.draw(surf, txt, r.centerx, r.y + 5, C["text"], 1, "center")


# ------------------------------------------------------------------ painel lateral
def draw_side(surf: pygame.Surface, hub: HubController, ui: UIState) -> None:
    geo = hub.pen_geo()
    p = LP.panel_rect(geo)
    panel(surf, p)
    text_fit(surf, "CRIATÓRIO", p.centerx, p.y + 18, C["warn"], p.w - 24, "center", top=2)
    col, save = hub.col, hub.save
    sr = LP.stats_rect(geo)
    shown = len([c for c in hub.pen.cats if not c.leaving]) if hub.pen else 0
    full = col.can_start
    rows = (("MOEDAS", str(save.coins), C["warn"]), ("GATOS", str(len(save.cats)), C["text"]),
            ("DECK", f"{col.deck_count}/{col.deck_size}", C["good"] if full else C["warn"]),
            ("NO CERCADO", str(shown), C["dim"]))
    for i, (lab, val, colr) in enumerate(rows):
        y = sr.y + i * 24
        font.draw(surf, lab, sr.x, y, C["dim"], 1)
        font.draw(surf, val, sr.right, y, colr, 1, "right")
        pygame.draw.line(surf, C["slot_edge"], (sr.x, y + 17), (sr.right, y + 17))
    quiet = hub._modal_open()
    m = (-100, -100) if quiet else ui.mouse
    b = lambda n: LP.button_rect(n, geo)           # noqa: E731
    button(surf, b("start"), "INICIAR RUN", m, enabled=full, scale=2)
    button(surf, b("colecao"), "COLEÇÃO", m, base=C["card"])
    if hub.adoption_pending:
        r = b("adocao")
        glow = pulse(ui.t, 5.0)
        pygame.draw.rect(surf, mix_c(C["warn"], WHITE, glow), r.inflate(8, 8), 3, border_radius=9)
        button(surf, r, "ADOÇÃO!", m, base=(150, 108, 24), scale=2)
    button(surf, b("breed"), "BREED", m, base=(104, 76, 132))
    button(surf, b("menu"), "MENU (ESC)", m, base=C["card"])
    hint = ("Deck pronto: INICIAR RUN." if full
            else f"Faltam {col.deck_size - col.deck_count} gato(s) no deck. Veja a COLEÇÃO.")
    hr = LP.hint_rect(geo)
    Wd.wrap_lines(surf, hint, hr.x, hr.y, hr.w, C["dim"], 1, 3, 13)


# ------------------------------------------------------------------ ficha
def draw_ficha(surf: pygame.Surface, hub: HubController, ui: UIState) -> None:
    cat = next((c for c in hub.save.cats if c.id == hub.ficha), None)
    if cat is None:
        return
    r = hub.ficha_rect()
    pygame.draw.rect(surf, (12, 14, 26), r, border_radius=6)
    draw_detail(surf, hub.col, ui, r, cat, close=True)
    x = LP.ficha_close(r)
    m = (-100, -100) if hub._modal_open() else ui.mouse
    button(surf, x, "X", m, base=C["card"])


# ------------------------------------------------------------------ quadro
def draw_pen(surf: pygame.Surface, hub: HubController, ui: UIState) -> None:
    art = pen_sprites.art()
    pen = hub.pen
    day = pen.day
    draw_floor(surf, art, day)
    clock = pen.time
    draw_ambient(surf, art, clock, True, day)
    quiet = hub._modal_open()
    hovered = None if quiet else pen.hit(ui.mouse)
    over_panel = LP.panel_rect(art.geo).collidepoint(ui.mouse)
    hov_obj = None if (quiet or hovered or over_panel) else pen.hit_object(ui.mouse)
    for o in pen.objects:                                   # camas e brinquedos "floor": abaixo de todos os gatos
        if o.spec.layer == "floor":
            draw_object(surf, art, o, o.index == hov_obj, day)
    layer: list[tuple[float, int, str, object]] = [(o.spec.y + o.oy, 0, "", o) for o in pen.objects
                                                   if o.spec.layer != "floor"]
    layer += [(pen.sort_y(c), 1, c.cat_id, c) for c in pen.cats]
    layer.sort(key=lambda it: it[:3])
    for _, kind, _, it in layer:
        if kind == 0:
            draw_object(surf, art, it, it.index == hov_obj, day)
        else:
            draw_cat(surf, it, art, ui, it.cat_id == hovered, it.cat_id == hub.ficha, day)
    draw_hearts(surf, pen.hearts, art)
    draw_ambient(surf, art, clock, False, day)
    if hovered and hovered != hub.ficha:
        c = pen.cat(hovered)
        if c is not None:
            draw_hover(surf, hub, c, art.frame_size[1] - 10)
    draw_side(surf, hub, ui)
    if hub.ficha:
        draw_ficha(surf, hub, ui)
    if hub.col.editing:
        draw_rename(surf, hub.col, ui)
    if hub.col.confirm_donate:
        draw_donate_confirm(surf, hub.col, ui)
    Wd.toast(surf, hub.toast or hub.col.toast)
