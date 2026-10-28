"""Layout do Criatorio e das Novidades do Criatorio (480x270) e teste de clique."""
from __future__ import annotations

import pygame

from ui.theme import W

# ------------------------------------------------------------------ criatorio
ROWS = 8
ROW_H = 12
LIST_Y0 = 37
LIST_W = 176
LIST_X = {"M": 4, "F": 184}
PANEL_Y, PANEL_H = 139, 105
COUPLE_H = 24
COUPLES_VISIBLE = 3
KITTENS_VISIBLE = 8

# colunas (deslocamento x na linha)
COL_NAME, COL_NAT, COL_IV_ATK, COL_IV_HP, COL_STATS = 3, 49, 82, 114, 147
NAME_W, NAT_W = 44, 30


def list_header(side: str) -> pygame.Rect:
    return pygame.Rect(LIST_X[side], 22, LIST_W, 13)


def scroll_button(side: str, d: int) -> pygame.Rect:
    h = list_header(side)
    return pygame.Rect(h.right - 23 + (11 if d > 0 else 0), h.y + 1, 10, 11)


def row_rect(side: str, i: int) -> pygame.Rect:
    return pygame.Rect(LIST_X[side], LIST_Y0 + i * ROW_H, LIST_W, ROW_H - 1)


def breed_panel() -> pygame.Rect:
    return pygame.Rect(4, PANEL_Y, LIST_W, PANEL_H)


def kitten_panel() -> pygame.Rect:
    return pygame.Rect(184, PANEL_Y, LIST_W, PANEL_H)


def couple_rect(i: int) -> pygame.Rect:
    p = breed_panel()
    return pygame.Rect(p.x + 3, p.y + 14 + i * COUPLE_H, p.w - 6, COUPLE_H - 2)


def cancel_button(i: int) -> pygame.Rect:
    r = couple_rect(i)
    return pygame.Rect(r.right - 52, r.y + 11, 50, 10)


def side_panel() -> pygame.Rect:
    return pygame.Rect(364, 22, 112, 222)


def action_buttons() -> dict[str, pygame.Rect]:
    p = side_panel()
    return {"start": pygame.Rect(p.x + 4, p.bottom - 46, p.w - 8, 24),
            "back": pygame.Rect(p.x + 4, p.bottom - 19, p.w - 8, 16)}


def breed_hit(pos: tuple[int, int], male_ids: list[str], female_ids: list[str],
              cancel_pairs: list[tuple[str, str]]) -> tuple | None:
    for side, ids in (("M", male_ids), ("F", female_ids)):
        for i, cid in enumerate(ids):
            if row_rect(side, i).collidepoint(pos):
                return ("row", side, cid)
        for d in (-1, 1):
            if scroll_button(side, d).collidepoint(pos):
                return ("scroll", side, d)
    for i, (m, f) in enumerate(cancel_pairs):
        if cancel_button(i).collidepoint(pos):
            return ("cancel", m, f)
    for name, r in action_buttons().items():
        if r.collidepoint(pos):
            return (name,)
    return None


# ------------------------------------------------------------------ novidades
NEWS_ROWS_MAX = 8
NEWS_ROW_H = 13


def news_button() -> pygame.Rect:
    return pygame.Rect(W // 2 - 70, 244, 140, 20)


def news_hit(pos: tuple[int, int]) -> tuple | None:
    return ("news_continue",) if news_button().collidepoint(pos) else None
