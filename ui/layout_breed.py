"""Layout do Criatorio e das Novidades do Criatorio em 960x540 e teste de clique."""
from __future__ import annotations

import pygame

from ui.theme import W

# ------------------------------------------------------------------ criatorio
ROWS = 5
ROW_H = 44
LIST_Y0 = 92
LIST_W = 302
LIST_X = {"M": 12, "F": 326}
PANEL_Y, PANEL_H = 322, 206
COUPLE_H = 56
COUPLES_VISIBLE = 3
KITTENS_VISIBLE = 4
KITTEN_H = 36


def list_header(side: str) -> pygame.Rect:
    return pygame.Rect(LIST_X[side], 60, LIST_W, 28)


def scroll_button(side: str, d: int) -> pygame.Rect:
    h = list_header(side)
    return pygame.Rect(h.right - 50 + (26 if d > 0 else 0), h.y + 3, 24, 22)


def row_rect(side: str, i: int) -> pygame.Rect:
    return pygame.Rect(LIST_X[side], LIST_Y0 + i * ROW_H, LIST_W, ROW_H - 2)


def breed_panel() -> pygame.Rect:
    return pygame.Rect(LIST_X["M"], PANEL_Y, LIST_W, PANEL_H)


def kitten_panel() -> pygame.Rect:
    return pygame.Rect(LIST_X["F"], PANEL_Y, LIST_W, PANEL_H)


def couple_rect(i: int) -> pygame.Rect:
    p = breed_panel()
    return pygame.Rect(p.x + 6, p.y + 32 + i * COUPLE_H, p.w - 12, COUPLE_H - 4)


def cancel_button(i: int) -> pygame.Rect:
    r = couple_rect(i)
    return pygame.Rect(r.right - 122, r.y + r.h - 28, 116, 24)


def side_panel() -> pygame.Rect:
    return pygame.Rect(640, 56, 308, 472)


def action_buttons() -> dict[str, pygame.Rect]:
    p = side_panel()
    return {"start": pygame.Rect(p.x + 10, p.bottom - 108, p.w - 20, 48),
            "back": pygame.Rect(p.x + 10, p.bottom - 52, p.w - 20, 40)}


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
NEWS_ROWS_MAX = 3
NEWS_ROW_H = 58


def news_button() -> pygame.Rect:
    return pygame.Rect(W // 2 - 140, 480, 280, 46)


def news_hit(pos: tuple[int, int]) -> tuple | None:
    return ("news_continue",) if news_button().collidepoint(pos) else None
