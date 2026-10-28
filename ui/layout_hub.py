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
    return pygame.Rect(d.x + 6, d.bottom - 22, 68, 16)


def donate_button() -> pygame.Rect:
    d = detail_panel()
    return pygame.Rect(d.x + 78, d.bottom - 22, d.w - 84, 16)


def donate_panel() -> pygame.Rect:
    return pygame.Rect(90, 80, 300, 100)


def donate_buttons() -> dict[str, pygame.Rect]:
    p = donate_panel()
    return {"donate_yes": pygame.Rect(p.x + 14, p.bottom - 30, 128, 22),
            "donate_no": pygame.Rect(p.right - 142, p.bottom - 30, 128, 22)}


def action_buttons() -> dict[str, pygame.Rect]:
    return {"complete": pygame.Rect(326, 176, 73, 18),
            "clear": pygame.Rect(403, 176, 73, 18),
            "start": pygame.Rect(326, 198, 150, 24),
            "back": pygame.Rect(326, 228, 72, 16),
            "breed": pygame.Rect(402, 228, 74, 16)}


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


# ------------------------------------------------------------------ adocao
ADOPT_PER_PAGE = 4


def adopt_card(i: int) -> pygame.Rect:
    return pygame.Rect(6 + i * 118, 40, 114, 176)


def adopt_buttons(i: int) -> dict[str, pygame.Rect]:
    c = adopt_card(i)
    return {"adopt": pygame.Rect(c.x + 5, c.bottom - 42, c.w - 10, 18),
            "donate": pygame.Rect(c.x + 5, c.bottom - 22, c.w - 10, 18)}


def adopt_nav() -> dict[str, pygame.Rect]:
    return {"prev": pygame.Rect(6, 222, 50, 16), "reveal_all": pygame.Rect(150, 222, 180, 16),
            "next": pygame.Rect(424, 222, 50, 16)}


def adopt_hit(pos: tuple[int, int], ids: list[str], revealed: set[str], paged: bool) -> tuple | None:
    for i, cid in enumerate(ids):
        if cid in revealed:
            for name, r in adopt_buttons(i).items():
                if r.collidepoint(pos):
                    return (name, cid)
        elif adopt_card(i).collidepoint(pos):
            return ("reveal", cid)
    nav = adopt_nav()
    if nav["reveal_all"].collidepoint(pos):
        return ("reveal_all",)
    if paged:
        if nav["prev"].collidepoint(pos):
            return ("page", -1)
        if nav["next"].collidepoint(pos):
            return ("page", 1)
    return None


# ------------------------------------------------------------------ cliques
def hit_test(pos: tuple[int, int], mode: str, *, rows: list[str] | None = None,
             confirm: bool = False, rename: bool = False, donate: bool = False,
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
        if donate:
            for name, r in donate_buttons().items():
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
        if donate_button().collidepoint(pos):
            return ("donate",)
        for name, r in action_buttons().items():
            if r.collidepoint(pos):
                return (name,)
    elif mode == "resultado":
        if result_button().collidepoint(pos):
            return ("result_back",)
    return None
