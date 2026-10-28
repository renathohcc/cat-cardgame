"""Layout do hub (menu, colecao, resultado da run) em coordenadas internas 480x270, e teste de clique."""
from __future__ import annotations

import pygame

from ui.theme import W

# ------------------------------------------------------------------ menu
MENU_ITEMS = ("continue", "new_game", "quit")


def menu_button(i: int) -> pygame.Rect:
    return pygame.Rect(W // 2 - 70, 104 + i * 30, 140, 24)


def menu_info_rect() -> pygame.Rect:
    return pygame.Rect(40, 204, W - 80, 40)


def confirm_panel() -> pygame.Rect:
    return pygame.Rect(100, 84, 280, 92)


def confirm_buttons() -> dict[str, pygame.Rect]:
    p = confirm_panel()
    return {"confirm_yes": pygame.Rect(p.x + 14, p.bottom - 30, 124, 22),
            "confirm_no": pygame.Rect(p.right - 138, p.bottom - 30, 124, 22)}


# ------------------------------------------------------------------ colecao
ROWS_VISIBLE = 14
ROW_Y0, ROW_H = 50, 14
LIST_X, ROW_W = 4, 304

# colunas: deslocamento x relativo ao inicio da linha
COL_CHECK, COL_NAME, COL_BREED, COL_SEX, COL_NATURE = 3, 14, 78, 134, 144
COL_IV_ATK, COL_IV_HP, COL_STATS, COL_STATE = 184, 220, 252, 279
NAME_W, BREED_W, NATURE_W, STATE_W = 62, 54, 38, 24


def row_rect(i: int) -> pygame.Rect:
    return pygame.Rect(LIST_X, ROW_Y0 + i * ROW_H, ROW_W, ROW_H - 1)


def scroll_up_rect() -> pygame.Rect:
    return pygame.Rect(LIST_X + ROW_W + 3, ROW_Y0, 9, 12)


def scroll_down_rect() -> pygame.Rect:
    return pygame.Rect(LIST_X + ROW_W + 3, ROW_Y0 + ROWS_VISIBLE * ROW_H - 13, 9, 12)


def scroll_track() -> pygame.Rect:
    up, dn = scroll_up_rect(), scroll_down_rect()
    return pygame.Rect(up.x, up.bottom + 2, up.w, dn.y - up.bottom - 4)


SORT_KEYS = ("poder", "raca", "nome")


def sort_button(i: int) -> pygame.Rect:
    xs = (36, 82, 120)
    ws = (44, 36, 38)
    return pygame.Rect(xs[i], 22, ws[i], 14)


def filter_button() -> pygame.Rect:
    return pygame.Rect(170, 22, 150, 14)


def detail_panel() -> pygame.Rect:
    return pygame.Rect(326, 22, 150, 150)


def rename_button() -> pygame.Rect:
    d = detail_panel()
    return pygame.Rect(d.x + 6, d.bottom - 22, d.w - 12, 16)


def action_buttons() -> dict[str, pygame.Rect]:
    return {"complete": pygame.Rect(326, 176, 73, 18),
            "clear": pygame.Rect(403, 176, 73, 18),
            "start": pygame.Rect(326, 198, 150, 24),
            "back": pygame.Rect(326, 228, 150, 16)}


# ------------------------------------------------------------------ renomear
def rename_panel() -> pygame.Rect:
    return pygame.Rect(100, 64, 280, 124)


def rename_input() -> pygame.Rect:
    p = rename_panel()
    return pygame.Rect(p.x + 14, p.y + 32, p.w - 28, 18)


def rename_buttons() -> dict[str, pygame.Rect]:
    p = rename_panel()
    return {"rename_ok": pygame.Rect(p.x + 14, p.bottom - 28, 120, 20),
            "rename_cancel": pygame.Rect(p.right - 134, p.bottom - 28, 120, 20)}


# ------------------------------------------------------------------ resultado da run
def result_button() -> pygame.Rect:
    return pygame.Rect(W // 2 - 80, 214, 160, 24)


# ------------------------------------------------------------------ cliques
def hit_test(pos: tuple[int, int], mode: str, *, rows: list[str] | None = None,
             confirm: bool = False, rename: bool = False,
             menu_enabled: dict[str, bool] | None = None) -> tuple | None:
    if mode == "menu":
        if confirm:
            for name, r in confirm_buttons().items():
                if r.collidepoint(pos):
                    return (name,)
            return None
        for i, item in enumerate(MENU_ITEMS):
            if menu_button(i).collidepoint(pos):
                return ("menu", item)
    elif mode == "colecao":
        if rename:
            for name, r in rename_buttons().items():
                if r.collidepoint(pos):
                    return (name,)
            return None
        for i, cid in enumerate(rows or []):
            if row_rect(i).collidepoint(pos):
                return ("row", cid)
        if scroll_up_rect().collidepoint(pos):
            return ("scroll", -1)
        if scroll_down_rect().collidepoint(pos):
            return ("scroll", 1)
        for i, key in enumerate(SORT_KEYS):
            if sort_button(i).collidepoint(pos):
                return ("sort", key)
        if filter_button().collidepoint(pos):
            return ("filter",)
        if rename_button().collidepoint(pos):
            return ("rename",)
        for name, r in action_buttons().items():
            if r.collidepoint(pos):
                return (name,)
    elif mode == "resultado":
        if result_button().collidepoint(pos):
            return ("result_back",)
    return None
