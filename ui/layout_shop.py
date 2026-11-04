"""Layout da loja do hub e do painel de compra de area (960x540) e teste de clique."""
from __future__ import annotations

import pygame

from ui.theme import H, W

TABS = ("areas", "racoes", "decoracao")
TAB_Y, TAB_H, TAB_W = 62, 34, 190
BODY_Y = 108


def tab_rect(i: int) -> pygame.Rect:
    return pygame.Rect(24 + i * (TAB_W + 8), TAB_Y, TAB_W, TAB_H)


def back_button() -> pygame.Rect:
    return pygame.Rect(24, H - 52, 220, 38)


def header_stats() -> pygame.Rect:
    return pygame.Rect(W - 330, 14, 306, 70)


# ------------------------------------------------------------------ areas
AREA_ROW_H = 56


def area_row(i: int) -> pygame.Rect:
    return pygame.Rect(24, BODY_Y + i * AREA_ROW_H, W - 48, AREA_ROW_H - 4)


def area_button(i: int) -> pygame.Rect:
    r = area_row(i)
    return pygame.Rect(r.right - 168, r.y + 10, 158, r.h - 20)


# ------------------------------------------------------------------ racoes
CARD_W, CARD_H = 296, 330


def ration_card(i: int) -> pygame.Rect:
    return pygame.Rect(24 + i * (CARD_W + 12), BODY_Y + 4, CARD_W, CARD_H)


def ration_button(i: int) -> pygame.Rect:
    c = ration_card(i)
    return pygame.Rect(c.x + 14, c.bottom - 52, c.w - 28, 40)


# ------------------------------------------------------------------ decoracao
DECO_W, DECO_H = 456, 64


def deco_card(i: int) -> pygame.Rect:
    return pygame.Rect(24 + (i % 2) * (DECO_W + 12), BODY_Y + (i // 2) * (DECO_H + 6), DECO_W, DECO_H)


def deco_button(i: int) -> pygame.Rect:
    c = deco_card(i)
    return pygame.Rect(c.right - 134, c.y + (c.h - 28) // 2, 124, 28)


def shop_hit(pos: tuple[int, int], tab: str, area_ids: list[str], ration_ids: list[str],
             deco_ids: list[str]) -> tuple | None:
    if back_button().collidepoint(pos):
        return ("shop_back",)
    for i, t in enumerate(TABS):
        if tab_rect(i).collidepoint(pos):
            return ("shop_tab", t)
    if tab == "areas":
        for i, aid in enumerate(area_ids):
            if area_row(i).collidepoint(pos):
                return ("shop_area", aid)
    elif tab == "racoes":
        for i, rid in enumerate(ration_ids):
            if ration_button(i).collidepoint(pos):
                return ("shop_ration", rid)
    else:
        for i, did in enumerate(deco_ids):
            if deco_button(i).collidepoint(pos):
                return ("shop_deco", did)
    return None


# ------------------------------------------------------------------ painel da area (no cercado)
def area_panel() -> pygame.Rect:
    return pygame.Rect((W - 520) // 2, 110, 520, 300)


def area_panel_buttons() -> dict[str, pygame.Rect]:
    p = area_panel()
    return {"area_buy": pygame.Rect(p.x + 24, p.bottom - 60, 300, 44),
            "area_close": pygame.Rect(p.right - 164, p.bottom - 60, 140, 44)}


def area_panel_hit(pos: tuple[int, int], area_id: str) -> tuple | None:
    b = area_panel_buttons()
    if b["area_buy"].collidepoint(pos):
        return ("area_buy", area_id)
    if b["area_close"].collidepoint(pos):
        return ("area_close",)
    return ("area_panel",) if area_panel().collidepoint(pos) else None
