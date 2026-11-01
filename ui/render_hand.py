"""Mao do jogador animada: compra desliza do baralho, carta em foco sobe/cresce e afasta as
vizinhas. Intensidades de `ctrl.timing.hand`; posicoes sempre inteiras."""
from __future__ import annotations

import pygame

from ui import anim, font, layout as L
from ui.render import DARK, border, draw_card, pill, tint
from ui.theme import C, H


def _focus(ui, hov_i: int | None) -> float:
    """Progresso (0..1) do foco do mouse; reinicia quando a carta em hover muda."""
    if ui.hover_hand != hov_i:
        ui.hover_hand, ui.hover_since = hov_i, ui.t
    return 1.0 if hov_i is None else anim.hand_hover_factor(ui.t, ui.hover_since)


def _draw_slide(ctrl, card) -> float | None:
    """Progresso (0..1) da compra desta carta, ou None se nao esta deslizando."""
    for f in ctrl.fx:
        if f.kind == "draw" and f.card is card:
            return anim.ease_out(f.age / f.life)
    return None


def _card_rect(ctrl, i: int, n: int, card) -> pygame.Rect:
    base = L.hand_rect(i, n)
    k = _draw_slide(ctrl, card)
    if k is None:
        return base
    sx, sy = L.pile_rect().center
    r = base.copy()
    r.center = (round(sx + (base.centerx - sx) * k), round(sy + (base.centery - sy) * k))
    return r


def _lifted(r: pygame.Rect, tm, k: float) -> pygame.Rect:
    """Carta em foco: sobe `hover_lift` e cresce ate `hover_scale` (inteiros)."""
    w = round(r.w * (1 + (tm.hover_scale - 1) * k))
    h = round(r.h * (1 + (tm.hover_scale - 1) * k))
    out = pygame.Rect(0, 0, w, h)
    out.center = (r.centerx, r.centery - round(tm.hover_lift * k))
    return keep_clear(out)


def keep_clear(r: pygame.Rect) -> pygame.Rect:
    """A carta ampliada nunca cobre o Lider (sobe so ate a faixa da mao), a tela nem a coluna
    direita (energia/baralho)."""
    r = r.copy()
    r.top = max(r.top, L.HAND_STRIP_Y)
    r.bottom = min(r.bottom, H)
    r.left = max(r.left, 4)
    r.right = min(r.right, L.HAND_X1 + 4)
    return r


def draw_hand(surf: pygame.Surface, ctrl, ui, hover: tuple | None = None) -> int | None:
    """Desenha a mao em leque; devolve o indice da carta arrastada (para nao duplicar)."""
    hand = ctrl.shown.me.hand
    n = len(hand)
    tm = ctrl.timing.hand
    dragging = ui.drag[0][1] if ui.drag and ui.drag[0][0] == "hand" else None
    hov_i = hover[1] if hover and hover[0] == "hand" and hover[1] < n else None
    sel_i = ctrl.sel[1] if ctrl.sel and ctrl.sel[0] == "hand" else None
    focus_i = hov_i if hov_i is not None else (sel_i if sel_i is not None and sel_i < n else None)
    fk = _focus(ui, focus_i) if dragging is None else 0.0
    order = [i for i in range(n) if i not in (hov_i, sel_i)]
    for i in (hov_i, sel_i):                      # foco/selecionada por cima das outras
        if i is not None and i < n and i not in order:
            order.append(i)
    for i in order:
        if i == dragging:
            continue
        card = hand[i]
        r = _card_rect(ctrl, i, n, card)
        sel = ctrl.sel == ("hand", i)
        ok, why = ctrl.hand_state(i)
        if (sel or i == hov_i) and _draw_slide(ctrl, card) is None:
            r = _lifted(r, tm, 1.0 if sel and i != hov_i else fk)
        elif focus_i is not None and fk > 0:
            r = keep_clear(r.move(round(anim.spread_dx(i, focus_i, tm.hover_spread) * fk), 0))
        draw_card(surf, r, card, card.atk, card.hp, card.hp, card.keywords)
        if not ok:
            tint(surf, r, DARK, 140)   # so escurece; o motivo aparece no toast ao clicar
        elif ctrl.can_act():
            border(surf, r, C["ready"], 2)
        if sel:
            border(surf, r.inflate(6, 6), C["select"], 3)
            if ctrl.needs_confirm():
                pr = pygame.Rect(r.x + 6, r.y + 32, r.w - 12, 38)
                pill(surf, pr, 235)
                font.draw(surf, "CLIQUE DE", r.centerx, pr.y + 5, (255, 255, 255), 1, "center")
                font.draw(surf, "NOVO", r.centerx, pr.y + 22, C["warn"], 1, "center")
    return dragging
