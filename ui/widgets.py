"""Pecas visuais compartilhadas pelas telas nativas 960x540 (hub, mapa, draft, criatorio...).

So desenho: nenhuma regra de jogo. Texto sempre por `ui.font`; cores sempre de `ui.theme`.
Tamanhos de texto: escala 2 para o que importa (10x14 px nas maiusculas), escala 1 so para
apoio (dicas, rotulos). Tudo foi pensado para o ESPACO de 960x540 e para trocar a fonte depois.
"""
from __future__ import annotations

import pygame

from ui import audio, font, skin, sprites
from ui.render import mix_c, outlined, text_fit, tint
from ui.theme import BREED_COLOR, C, DEFAULT_BREED_COLOR, H, KEYWORD_COLOR, W

WHITE = (255, 255, 255)
DARK = C["dark"]
EDGE = C["panel_edge"]

_bg: pygame.Surface | None = None


def background() -> pygame.Surface:
    """Fundo das telas fora do duelo: trama noturna do tabuleiro com a moldura (skin.screen_background);
    sem a arte, gradiente suave + vinheta."""
    global _bg
    if _bg is None:
        art = skin.screen_background((W, H))
        if art is not None:
            _bg = art
            return _bg
        b = pygame.Surface((W, H))
        top, bot = (30, 36, 62), (14, 16, 28)
        for y in range(H):
            k = y / (H - 1)
            pygame.draw.line(b, tuple(int(top[i] + (bot[i] - top[i]) * k) for i in range(3)), (0, y), (W, y))
        edge = pygame.Surface((W, H), pygame.SRCALPHA)
        for i in range(24):
            a = int(70 * (1 - i / 24) ** 2)
            pygame.draw.rect(edge, (0, 0, 0, a), pygame.Rect(i, i, W - 2 * i, H - 2 * i), 1)
        b.blit(edge, (0, 0))
        _bg = b
    return _bg


def fill_background(surf: pygame.Surface) -> None:
    surf.blit(background(), (0, 0))


# ------------------------------------------------------------------ paineis e botoes
def panel(surf: pygame.Surface, r: pygame.Rect, edge=None, alpha: int = 215) -> None:
    tint(surf, r, (12, 14, 26), alpha)
    pygame.draw.rect(surf, edge or EDGE, r, 2, border_radius=6)


def title(surf: pygame.Surface, txt: str, x: int, y: int, color=None, scale: int = 2,
          align: str = "left") -> None:
    outlined(surf, txt, x, y, color or C["text"], scale, align)


def button(surf: pygame.Surface, r: pygame.Rect, label: str, mouse, enabled: bool = True,
           base=None, scale: int = 1, edge=WHITE) -> None:
    hot = enabled and r.collidepoint(mouse)
    base = base or C["button"]
    fill = mix_c(base, WHITE, 0.25) if hot else (base if enabled else C["button_off"])
    pygame.draw.rect(surf, DARK, r.inflate(2, 2), border_radius=7)
    pygame.draw.rect(surf, fill, r, border_radius=6)
    tint(surf, pygame.Rect(r.x + 3, r.y + 2, r.w - 6, 3), WHITE, 40 if enabled else 12)   # brilho
    pygame.draw.rect(surf, edge if enabled else EDGE, r, 2, border_radius=6)
    sc = scale
    while sc > 1 and font.width(label, sc) > r.w - 12:
        sc -= 1
    ty = r.y + (r.h - font.CAP_H * sc) // 2
    col = WHITE if enabled else C["dim"]
    font.draw(surf, font.fit(label, r.w - 8, sc), r.centerx, ty, col, sc, "center")


def chip(surf: pygame.Surface, x: int, y: int, fill, txt: str, color=WHITE, scale: int = 1,
         min_w: int = 0, h: int | None = None) -> pygame.Rect:
    """Etiqueta colorida (ATK 7, nome de keyword...). Devolve o retangulo."""
    w = max(min_w, font.width(txt, scale) + 12)
    hh = h or font.CAP_H * scale + 8
    r = pygame.Rect(x, y, w, hh)
    pygame.draw.rect(surf, DARK, r.inflate(2, 2), border_radius=5)
    pygame.draw.rect(surf, fill, r, border_radius=4)
    font.draw(surf, txt, r.centerx, r.y + (hh - font.CAP_H * scale) // 2, color, scale, "center")
    return r


def keyword_chip(surf: pygame.Surface, x: int, y: int, kid: str, name: str, scale: int = 1) -> pygame.Rect:
    """Chip de keyword com o icone 16x16 (se existir) e o nome."""
    ico = sprites.get("icon", kid)
    iw = ico.get_width() + 4 if ico else 0
    txt = name.upper()
    w = font.width(txt, scale) + 12 + iw
    hh = max(20, font.CAP_H * scale + 8)
    r = pygame.Rect(x, y, w, hh)
    col = KEYWORD_COLOR.get(kid, C["dim"])
    pygame.draw.rect(surf, DARK, r.inflate(2, 2), border_radius=5)
    pygame.draw.rect(surf, mix_c(col, DARK, 0.55), r, border_radius=4)
    pygame.draw.rect(surf, col, r, 1, border_radius=4)
    if ico:
        surf.blit(ico, (r.x + 5, r.centery - ico.get_height() // 2))
    font.draw(surf, txt, r.x + 6 + iw, r.y + (hh - font.CAP_H * scale) // 2, WHITE, scale)
    return r


def keyword_row(surf: pygame.Surface, x: int, y: int, max_x: int, items: list[tuple[str, str]],
                scale: int = 1) -> int:
    """Chips de keyword em linha, quebrando para a proxima se faltar espaco. Devolve o y final."""
    cx, line_h = x, 0
    for kid, name in items:
        ico = sprites.get("icon", kid)
        w = font.width(name.upper(), scale) + 12 + (ico.get_width() + 4 if ico else 0)
        if cx + w > max_x and cx > x:
            cx, y = x, y + line_h + 4
        r = keyword_chip(surf, cx, y, kid, name, scale)
        line_h = r.h
        cx = r.right + 6
    return y + line_h


def stat_pill(surf: pygame.Surface, x: int, y: int, fill, label: str, value: str, w: int = 78,
              scale: int = 1) -> pygame.Rect:
    """'ATK 12' com o icone pequeno do tipo (ataque/hp/custo) quando existir."""
    icon = {"ATK": "ataque", "HP": "hp", "CUSTO": "custo"}.get(label)
    ico = sprites.get("icon", icon) if icon else None
    hh = font.CAP_H * scale + 10
    r = pygame.Rect(x, y, w, hh)
    pygame.draw.rect(surf, DARK, r.inflate(2, 2), border_radius=6)
    pygame.draw.rect(surf, fill, r, border_radius=5)
    tx = r.x + 8
    if ico:
        surf.blit(ico, (r.x + 5, r.centery - ico.get_height() // 2))
        tx += ico.get_width() + 2
        txt = value
    else:
        txt = f"{label} {value}"
    font.draw(surf, txt, tx + (r.right - 6 - tx - font.width(txt, scale)) // 2, r.y + (hh - font.CAP_H * scale) // 2,
              WHITE, scale)
    return r


# ------------------------------------------------------------------ estrelas de IV
_star_cache: dict[tuple, pygame.Surface] = {}
_STAR = ("..#..", ".###.", "#####", ".###.", ".#.#.")


def star(color, scale: int) -> pygame.Surface:
    k = (color, scale)
    s = _star_cache.get(k)
    if s is None:
        s = pygame.Surface((5 * scale, 5 * scale), pygame.SRCALPHA)
        for yy, row in enumerate(_STAR):
            for xx, c in enumerate(row):
                if c == "#":
                    pygame.draw.rect(s, color, (xx * scale, yy * scale, scale, scale))
        _star_cache[k] = s
    return s


def star_width(scale: int) -> int:
    return 5 * (5 * scale + scale)


def stars(surf: pygame.Surface, x: int, y: int, n: int | None, scale: int = 2) -> int:
    """5 estrelas (IV n/5). Devolve a largura."""
    step = 6 * scale
    for i in range(5):
        on = n is not None and i < n
        surf.blit(star(C["star_on"] if on else C["star_off"], scale), (x + i * step, y))
    return 5 * step - scale


# ------------------------------------------------------------------ gatos
def breed_color(breed: str | None):
    return BREED_COLOR.get(breed or "", DEFAULT_BREED_COLOR)


def sex_badge(surf: pygame.Surface, cx: int, cy: int, sex: str, r: int = 10) -> None:
    col = C["male"] if sex == "M" else C["female"]
    pygame.draw.circle(surf, DARK, (cx, cy), r + 1)
    pygame.draw.circle(surf, col, (cx, cy), r)
    font.draw(surf, sex, cx, cy - font.CAP_H // 2, DARK, 1, "center")


def cat_art(surf: pygame.Surface, breed: str | None, rect: pygame.Rect, kitten: bool = False,
            bg=None) -> None:
    """Janela com o sprite do gato centrado em `rect` (96 nativo; menor = reducao nearest).
    Sem sprite: silhueta placeholder na cor da raca. `kitten` usa o adulto menor (ate haver arte)."""
    pygame.draw.rect(surf, bg or C["card"], rect)
    side = min(rect.w, rect.h)
    size = side * 2 // 3 if kitten else side
    spr = sprites.get("cat", breed, size)
    if spr is not None:
        surf.blit(spr, spr.get_rect(center=rect.center))
        return
    col = breed_color(breed)
    cx, cy, k = rect.centerx, rect.centery + side // 10, side // 4
    pygame.draw.circle(surf, col, (cx, cy), k)
    pygame.draw.polygon(surf, col, [(cx - k, cy - k // 3), (cx - k + 2, cy - k - k // 2), (cx - k // 4, cy - k + 2)])
    pygame.draw.polygon(surf, col, [(cx + k, cy - k // 3), (cx + k - 2, cy - k - k // 2), (cx + k // 4, cy - k + 2)])
    e = max(2, k // 5)
    pygame.draw.rect(surf, DARK, (cx - k // 2, cy - e, e * 2, e * 2))
    pygame.draw.rect(surf, DARK, (cx + k // 2 - e, cy - e, e * 2, e * 2))


def leader_art(surf: pygame.Surface, leader_id: str | None, rect: pygame.Rect, side_col, size: int = 128,
               fallback_text: str = "?") -> None:
    """Retrato de Lider (sheet 128; 96 se faltar), centrado em `rect`, sempre o mesmo desenho."""
    pygame.draw.rect(surf, mix_c(side_col, DARK, 0.7), rect, border_radius=8)
    spr = sprites.get("leader128", leader_id, size)
    if spr is not None:
        surf.blit(spr, spr.get_rect(center=rect.center))
    else:
        font.draw(surf, fallback_text[:1].upper(), rect.centerx, rect.centery - font.CAP_H * 3 // 2, WHITE, 3, "center")
    pygame.draw.rect(surf, side_col, rect, 2, border_radius=8)


def toast(surf: pygame.Surface, t, y: int = H - 44) -> None:
    if t is None:
        return
    fill, col = {"error": ((100, 36, 40), (255, 190, 190)), "warn": ((110, 84, 20), (255, 230, 150)),
                 "info": ((36, 64, 100), (200, 225, 255))}[t.kind]
    w = min(W - 120, max(360, font.width(t.text, 1) + 40))
    m = pygame.Rect((W - w) // 2, y, w, 34)
    pygame.draw.rect(surf, fill, m, border_radius=6)
    pygame.draw.rect(surf, col, m, 2, border_radius=6)
    font.draw(surf, font.fit(t.text, m.w - 16), m.centerx, m.y + (m.h - font.CAP_H) // 2, col, 1, "center")


def dim_screen(surf: pygame.Surface, alpha: int = 190) -> None:
    tint(surf, pygame.Rect(0, 0, W, H), (6, 8, 16), alpha)


def modal(surf: pygame.Surface, r: pygame.Rect, heading: str, edge=None) -> None:
    """Escurece a tela e desenha um painel com titulo (scale 2) centralizado."""
    dim_screen(surf)
    pygame.draw.rect(surf, C["panel"], r, border_radius=8)
    pygame.draw.rect(surf, edge or C["warn"], r, 3, border_radius=8)
    text_fit(surf, heading, r.centerx, r.y + 18, edge or C["warn"], r.w - 24, "center", top=2)


def wrap_lines(surf: pygame.Surface, txt: str, x: int, y: int, w: int, color, scale: int = 1,
               max_lines: int = 99, step: int | None = None, align: str = "left") -> int:
    """Texto com quebra de linha. Devolve o y logo apos a ultima linha."""
    step = step or (font.CAP_H * scale + 4 * scale)
    lines = font.wrap(txt, w, scale)
    for k, ln in enumerate(lines[:max_lines]):
        if k == max_lines - 1 and len(lines) > max_lines:
            ln = font.fit(ln + " ...", w, scale)
        cx = x + (w // 2 if align == "center" else 0)
        font.draw(surf, ln, cx, y, color, scale, align)
        y += step
    return y


def arrow(surf: pygame.Surface, r: pygame.Rect, up: bool, on: bool, mouse) -> None:
    pygame.draw.rect(surf, C["card"] if (on and r.collidepoint(mouse)) else C["slot"], r, border_radius=3)
    pygame.draw.rect(surf, EDGE, r, 1, border_radius=3)
    cx, cy = r.centerx, r.centery
    pts = [(cx - 5, cy + 3), (cx + 5, cy + 3), (cx, cy - 4)] if up else \
        [(cx - 5, cy - 3), (cx + 5, cy - 3), (cx, cy + 4)]
    pygame.draw.polygon(surf, C["text"] if on else EDGE, pts)


def scrollbar(surf: pygame.Surface, track: pygame.Rect, total: int, visible: int, pos: int,
              max_pos: int) -> None:
    pygame.draw.rect(surf, C["slot"], track, border_radius=3)
    if total > visible:
        th = max(16, track.h * visible // total)
        ty = track.y + (track.h - th) * pos // max(1, max_pos)
        pygame.draw.rect(surf, EDGE, (track.x, ty, track.w, th), border_radius=3)



# ------------------------------------------------------------------ audio
def volume_bar(surf: pygame.Surface, r: pygame.Rect, value: float, on: bool = True) -> None:
    """Barra de volume (0..1) no estilo dos widgets nativos."""
    pygame.draw.rect(surf, C["slot"], r, border_radius=4)
    fill = pygame.Rect(r.x + 2, r.y + 2, int((r.w - 4) * max(0.0, min(1.0, value))), r.h - 4)
    if fill.w > 0:
        pygame.draw.rect(surf, C["good"] if on else C["dim"], fill, border_radius=3)
    pygame.draw.rect(surf, EDGE, r, 2, border_radius=4)


def volume_panel(surf: pygame.Surface, mouse) -> None:
    """Controles de volume do menu: Musica e Efeitos (-/+ em passos de 10%) e botao de mudo."""
    from ui import layout_hub as LH
    mgr = audio.manager()
    panel(surf, LH.volume_panel(), alpha=170)
    for i, which in enumerate(LH.VOL_ROWS):
        y = LH.vol_row_y(i)
        v = mgr.volume_of(which)
        font.draw(surf, which.upper(), LH.volume_panel().x + 12, y + (26 - font.CAP_H) // 2, C["text"], 1)
        button(surf, LH.vol_minus(i), "-", mouse, v > 0, scale=2)
        volume_bar(surf, LH.vol_bar(i), v, not mgr.muted)
        button(surf, LH.vol_plus(i), "+", mouse, v < 1, scale=2)
        font.draw(surf, f"{round(v * 100)}%", LH.vol_plus(i).right + 10, y + (26 - font.CAP_H) // 2,
                  C["dim"] if mgr.muted else C["text"], 1)
    r = LH.mute_button()
    button(surf, r, "MUDO (M)" if mgr.muted else "SOM (M)", mouse, True, base=(150, 60, 60) if mgr.muted else None)


def mute_badge(surf: pygame.Surface) -> None:
    """Aviso discreto 'MUDO (M)' no canto quando o som esta desligado."""
    if audio.manager().muted:
        font.draw(surf, "MUDO (M)", 10, H - font.CAP_H - 8, C["warn"], 1)
