"""Layout do hub (menu, colecao, adocao, resultado da run) em coordenadas 960x540 e teste de clique."""
from __future__ import annotations

import pygame

from ui.theme import W

# ------------------------------------------------------------------ menu
MENU_ITEMS = ("continue", "new_game", "quit")


def menu_button(i: int) -> pygame.Rect:
    return pygame.Rect(W // 2 - 150, 250 + i * 66, 300, 54)


def menu_info_rect() -> pygame.Rect:
    return pygame.Rect(W // 2 - 300, 444, 600, 64)


def confirm_panel() -> pygame.Rect:
    return pygame.Rect(W // 2 - 270, 160, 540, 210)


def confirm_buttons() -> dict[str, pygame.Rect]:
    p = confirm_panel()
    return {"confirm_yes": pygame.Rect(p.x + 24, p.bottom - 66, 232, 46),
            "confirm_no": pygame.Rect(p.right - 256, p.bottom - 66, 232, 46)}


# ------------------------------------------------------------------ colecao
ROWS_VISIBLE = 10
ROW_Y0, ROW_H = 112, 38
LIST_X, ROW_W = 12, 610

# colunas: deslocamento x relativo ao inicio da linha
COL_CHECK, COL_SPRITE, COL_NAME, COL_SEX, COL_INFO = 6, 26, 62, 196, 222
COL_IV_ATK, COL_IV_HP, COL_STATS, COL_STATE = 328, 398, 462, 540
NAME_W, INFO_W, STATE_W = 130, 100, 64


def row_rect(i: int) -> pygame.Rect:
    return pygame.Rect(LIST_X, ROW_Y0 + i * ROW_H, ROW_W, ROW_H - 2)


def scroll_up_rect() -> pygame.Rect:
    return pygame.Rect(LIST_X + ROW_W + 6, ROW_Y0, 18, 22)


def scroll_down_rect() -> pygame.Rect:
    return pygame.Rect(LIST_X + ROW_W + 6, ROW_Y0 + ROWS_VISIBLE * ROW_H - 24, 18, 22)


def scroll_track() -> pygame.Rect:
    up, dn = scroll_up_rect(), scroll_down_rect()
    return pygame.Rect(up.x, up.bottom + 3, up.w, dn.y - up.bottom - 6)


SORT_KEYS = ("poder", "raca", "nome")


def sort_button(i: int) -> pygame.Rect:
    xs = (84, 174, 244)
    ws = (86, 66, 70)
    return pygame.Rect(xs[i], 62, ws[i], 28)


def filter_button() -> pygame.Rect:
    return pygame.Rect(332, 62, 290, 28)


def detail_panel() -> pygame.Rect:
    return pygame.Rect(662, 56, 286, 312)


def rename_button() -> pygame.Rect:
    d = detail_panel()
    return pygame.Rect(d.x + 8, d.bottom - 40, 128, 32)


def donate_button() -> pygame.Rect:
    d = detail_panel()
    return pygame.Rect(d.x + 142, d.bottom - 40, d.w - 150, 32)


def donate_panel() -> pygame.Rect:
    return pygame.Rect(W // 2 - 280, 150, 560, 240)


def donate_buttons() -> dict[str, pygame.Rect]:
    p = donate_panel()
    return {"donate_yes": pygame.Rect(p.x + 24, p.bottom - 66, 240, 46),
            "donate_no": pygame.Rect(p.right - 264, p.bottom - 66, 240, 46)}


def action_buttons() -> dict[str, pygame.Rect]:
    return {"complete": pygame.Rect(662, 376, 139, 32),
            "clear": pygame.Rect(809, 376, 139, 32),
            "start": pygame.Rect(662, 414, 286, 46),
            "back": pygame.Rect(662, 468, 139, 32),
            "breed": pygame.Rect(809, 468, 139, 32)}


# ------------------------------------------------------------------ renomear
def rename_panel() -> pygame.Rect:
    return pygame.Rect(W // 2 - 280, 130, 560, 280)


def rename_input() -> pygame.Rect:
    p = rename_panel()
    return pygame.Rect(p.x + 28, p.y + 76, p.w - 56, 48)


def rename_buttons() -> dict[str, pygame.Rect]:
    p = rename_panel()
    return {"rename_ok": pygame.Rect(p.x + 24, p.bottom - 66, 240, 46),
            "rename_cancel": pygame.Rect(p.right - 264, p.bottom - 66, 240, 46)}


# ------------------------------------------------------------------ resultado da run
def result_button() -> pygame.Rect:
    return pygame.Rect(W // 2 - 140, 372, 280, 48)


# ------------------------------------------------------------------ adocao
ADOPT_PER_PAGE = 4


def adopt_card(i: int) -> pygame.Rect:
    return pygame.Rect(16 + i * 232, 84, 220, 400)


def adopt_buttons(i: int) -> dict[str, pygame.Rect]:
    c = adopt_card(i)
    return {"adopt": pygame.Rect(c.x + 10, c.bottom - 84, c.w - 20, 34),
            "donate": pygame.Rect(c.x + 10, c.bottom - 44, c.w - 20, 34)}


def adopt_nav() -> dict[str, pygame.Rect]:
    return {"prev": pygame.Rect(16, 494, 110, 34), "reveal_all": pygame.Rect(W // 2 - 120, 494, 240, 34),
            "next": pygame.Rect(W - 126, 494, 110, 34)}


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
