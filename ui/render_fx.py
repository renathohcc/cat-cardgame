"""Efeitos visuais do duelo: investida, numeros de dano, poof, cartas em voo, faixa de turno,
entrada do chefe e tremor de tela. So desenha; o tempo/estado vem do Controller (Fx) e as
intensidades de ui_timing.json (via `ctrl.timing`). Coordenadas sempre inteiras."""
from __future__ import annotations

import pygame

from ui import anim, font, layout as L, sprites
from ui.render import (
    DARK, border, draw_card, mix_c, outlined, pill, tint,
)
from ui.theme import BREED_COLOR, C, DEFAULT_BREED_COLOR, H, W

SMOKE = (200, 200, 214)
_FX_COLOR = {"bad": "bad", "good": "good", "buff": "buff", "dim": "dim", "energy": "energy"}


def fx_rect(side: str, slot: int | None) -> pygame.Rect:
    return L.leader_rect(side) if slot is None else L.slot_rect(side, slot)


def _of(ctrl, kind: str) -> list:
    return [f for f in ctrl.fx if f.kind == kind]


# ------------------------------------------------------------------ campo: investida e respiracao
def lunge_offset(f, tm) -> tuple[int, int]:
    src = fx_rect(f.side, f.slot).center
    dst = fx_rect(f.to_side, f.to_slot).center
    dx, dy = anim.lunge_offset(src, dst, f.age, f.life, f.data if f.data is not None else tm.lunge.reach)
    top = fx_rect(f.side, f.slot).y + dy                    # a carta nunca sai pela borda da tela
    return dx, dy + max(0, -top) - max(0, top + L.CARD_H - H)


def field_offsets(ctrl, ui) -> dict[tuple[str, int], tuple[int, int]]:
    """Deslocamento (dx, dy) de cada gato em campo: respiracao + investida."""
    tm = ctrl.timing
    out: dict[tuple[str, int], tuple[int, int]] = {}
    for side in ("enemy", "player"):
        for n, fc in enumerate(ctrl.shown.me.field if side == "player" else ctrl.shown.opponent.field):
            if fc is not None:
                out[(side, n)] = (0, anim.breath_offset(ui.t, side, n, tm.breathing.amplitude,
                                                        tm.breathing.period))
    for f in _of(ctrl, "lunge"):
        if (f.side, f.slot) in out:
            out[(f.side, f.slot)] = lunge_offset(f, tm)
    return out


def lunging(ctrl) -> set[tuple[str, int]]:
    return {(f.side, f.slot) for f in _of(ctrl, "lunge")}


def hidden_slots(ctrl) -> set[tuple[str, int]]:
    """Slots cujo gato ainda esta 'em voo' (a carta jogada desenha o arco por cima)."""
    return {(f.side, f.slot) for f in _of(ctrl, "play")}


# ------------------------------------------------------------------ efeitos por tipo
def draw_tag_fx(surf: pygame.Surface, f, k: float) -> None:
    r = L.energy_rect() if (f.card == "energy" and f.side == "player") else L.info_rect()
    outlined(surf, f.text, r.centerx, r.y - 10 - int(24 * k), C[_FX_COLOR.get(f.color, "good")], 1)


def draw_cast_fx(surf: pygame.Surface, f, k: float) -> None:
    w = font.width(f.text, 1) + 28
    pr = pygame.Rect(0, 0, w, 28)
    pr.center = (W // 2, L.CENTER_Y)
    col = C["player"] if f.side == "player" else C["enemy"]
    pill(surf, pr, int(235 * min(1.0, (1 - k) * 3)))
    border(surf, pr, col, 2)
    if k < 0.8:
        font.draw(surf, f.text, pr.centerx, pr.y + 9, (255, 255, 255), 1, "center")


def draw_number(surf: pygame.Surface, ctrl, f, r: pygame.Rect) -> None:
    """Numero flutuante: surge grande, encolhe (pop) e sobe; dano alto fica maior e mais quente."""
    damage = f.color == "bad"
    scale, rise, hot = anim.damage_style(f.amount, f.age, f.life, ctrl.timing, damage)
    col = C[_FX_COLOR.get(f.color, "good")]
    if hot:
        col = mix_c(col, anim.BIG_HOT, 0.7)
    if f.age / f.life > 0.85 and int(f.age * 30) % 2:        # pisca ao sumir (sem alpha)
        return
    if f.slot is None:                      # Lider: o numero nasce dentro da tela (o inimigo fica no topo)
        base = r.bottom + 12 if f.side == "enemy" else r.centery
    else:
        base = r.centery - 10
    y = base - rise
    outlined(surf, f.text, r.centerx, y - font.CAP_H * scale // 2, col, scale)


def draw_poof(surf: pygame.Surface, ctrl, f, r: pygame.Rect) -> None:
    fur = BREED_COLOR.get(getattr(f.card, "breed", None) or "", DEFAULT_BREED_COLOR)
    cx, cy = r.center
    for dx, dy, size, kind in anim.poof_particles(f.slot * 5 + (0 if f.side == "player" else 3),
                                                  f.age, ctrl.timing):
        col = fur if kind == 0 else SMOKE
        pygame.draw.rect(surf, DARK, (cx + dx - 1, cy + dy - 1, size + 2, size + 2))
        pygame.draw.rect(surf, col, (cx + dx, cy + dy, size, size))


def _lerp_pt(a: tuple[int, int], b: tuple[int, int], k: float) -> tuple[int, int]:
    return round(a[0] + (b[0] - a[0]) * k), round(a[1] + (b[1] - a[1]) * k)


def draw_play_arc(surf: pygame.Surface, f) -> None:
    """Carta jogada voa em arco da mao (ou do baralho inimigo) ate o slot."""
    k = anim.ease_out(f.age / f.life)
    dst = L.slot_rect(f.side, f.slot)
    if f.data is not None:
        src = L.hand_rect(*f.data).center
    else:
        src = L.pile_rect().center if f.side == "player" else L.enemy_pile_rect().center
    cx, cy = _lerp_pt(src, dst.center, k)
    cy -= round(4 * 36 * k * (1 - k))                       # arco
    r = pygame.Rect(0, 0, L.CARD_W, L.CARD_H)
    r.center = (cx, cy)
    c = f.card
    draw_card(surf, r, c, c.atk, c.hp, c.hp, c.keywords, enemy=f.side == "enemy")


def draw_fx(surf: pygame.Surface, ctrl) -> None:
    for f in ctrl.fx:
        k = f.age / f.life
        if f.kind == "tag":
            draw_tag_fx(surf, f, k)
            continue
        if f.kind == "cast":
            draw_cast_fx(surf, f, k)
            continue
        if f.kind == "play":
            draw_play_arc(surf, f)
            continue
        if f.kind in ("lunge", "draw", "gems"):             # desenhados no campo/mao/barra
            continue
        r = fx_rect(f.side, f.slot)
        if f.kind == "flash":
            col = (255, 255, 255) if f.color == "bad" else C["buff" if f.color == "buff" else "good"]
            tint(surf, r, col, int(200 * (1 - k)))
        elif f.kind == "float":
            draw_number(surf, ctrl, f, r)
        elif f.kind == "poof":
            draw_poof(surf, ctrl, f, r)
        elif f.kind == "die":
            ghost = pygame.Surface(r.size, pygame.SRCALPHA)
            c = f.card
            draw_card(ghost, ghost.get_rect(), c, c.atk, 0, c.hp, c.keywords, enemy=f.side == "enemy")
            ghost.set_alpha(int(255 * (1 - k)))
            surf.blit(ghost, r.topleft)
            tint(surf, r, C["bad"], int(120 * (1 - k)))
        elif f.kind == "enter":
            grow = int(16 * (1 - k))
            border(surf, r.inflate(grow, grow), (255, 255, 255), 3)


# ------------------------------------------------------------------ faixas e telas
def draw_banner(surf: pygame.Surface, ctrl) -> None:
    """Faixa de turno (uma linha) entra pela esquerda e sai pela direita; o Impasse usa a caixa."""
    if not ctrl.banner:
        return
    lines, left = ctrl.banner
    if len(lines) > 1:
        _draw_box_banner(surf, lines)
        return
    total = ctrl.banner_total or left
    p = anim.clamp01(1 - left / total) if total > 0 else 1.0
    edge = 0.22
    if p < edge:
        off = -round((1 - anim.ease_out(p / edge)) * W)
    elif p > 1 - edge:
        off = round(anim.ease_in_out((p - (1 - edge)) / edge) * W)
    else:
        off = 0
    r = pygame.Rect(off, 0, W, 44)
    r.centery = L.CENTER_Y
    mine = "SEU" in lines[0]
    pill(surf, r, 215)
    pygame.draw.rect(surf, C["player"] if mine else C["enemy"], (r.x, r.y, r.w, 2))
    pygame.draw.rect(surf, C["player"] if mine else C["enemy"], (r.x, r.bottom - 2, r.w, 2))
    font.draw(surf, lines[0], r.centerx, r.centery - font.CAP_H, (255, 255, 255), 2, "center")


def _draw_box_banner(surf: pygame.Surface, lines: list[str]) -> None:
    scale = 3
    w = max(font.width(lines[0], scale), *(font.width(s, 1) for s in lines[1:]), 0) + 48
    cap = font.CAP_H * scale
    h = 16 + cap + (24 * (len(lines) - 1) + 8) + 16
    r = pygame.Rect(0, 0, w, h)
    r.center = (W // 2, L.CENTER_Y)
    pill(surf, r, 225)
    border(surf, r, C["warn"], 3)
    font.draw(surf, lines[0], r.centerx, r.y + 16, C["warn"], scale, "center")
    for k, ln in enumerate(lines[1:]):
        font.draw(surf, ln, r.centerx, r.y + 24 + cap + k * 24, C["text"], 1, "center")


def draw_boss_intro(surf: pygame.Surface, ctrl) -> None:
    """Retrato e nome do chefe antes do duelo (clique/tecla pula). Sem falas."""
    t = ctrl.intro_t or 0.0
    fade = anim.ease_out(t / 0.3)
    tint(surf, pygame.Rect(0, 0, W, H), (6, 8, 16), int(235 * fade))
    slide = round((1 - anim.ease_out(t / 0.45)) * 48)
    enemy = ctrl.enemy or {}
    spr = sprites.get("leader128", ctrl.enemy_id or "inimigo")
    cx = W // 2
    if spr is not None:
        big = pygame.transform.scale(spr, (spr.get_width() * 2, spr.get_height() * 2))
        surf.blit(big, (cx - big.get_width() // 2, 50 + slide))
    else:
        r = pygame.Rect(0, 0, 200, 200)
        r.center = (cx, 150 + slide)
        pygame.draw.rect(surf, mix_c(C["enemy"], DARK, 0.6), r)
        border(surf, r, C["enemy"], 3)
        font.draw(surf, enemy.get("nome", "?")[:1].upper(), r.centerx, r.centery - font.CAP_H * 2,
                  (255, 255, 255), 4, "center")
    if fade >= 0.6:
        chip = pygame.Rect(0, 0, font.width("CHEFE", 2) + 24, font.CAP_H * 2 + 10)
        chip.center = (cx, 330 + slide // 2)
        pygame.draw.rect(surf, C["warn"], chip, border_radius=4)
        font.draw(surf, "CHEFE", chip.centerx, chip.y + 5, DARK, 2, "center")
        outlined(surf, ctrl.enemy_name().upper(), cx, 362 + slide // 2, (255, 255, 255), 3)
        if t > 0.6 and int(t * 2) % 2 == 0:
            font.draw(surf, "Clique ou ESPAÇO para continuar", cx, H - 36, C["dim"], 1, "center")


# ------------------------------------------------------------------ tremor
_buf: pygame.Surface | None = None


def shaken(surf: pygame.Surface, ctrl, enabled: bool, draw) -> None:
    """Desenha a cena com `draw(alvo)`; com tremor ativo, desenha num buffer e o desloca em px
    inteiros (as bordas mostram o tabuleiro)."""
    global _buf
    off = ctrl.shake_offset() if enabled else (0, 0)
    if off == (0, 0):
        draw(surf)
        return
    if _buf is None or _buf.get_size() != surf.get_size():
        _buf = pygame.Surface(surf.get_size())
    draw(_buf)
    from ui.render import board_surface
    surf.blit(board_surface(), (0, 0))
    surf.blit(_buf, off)
