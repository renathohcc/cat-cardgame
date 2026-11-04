"""Layout do painel "gatil cheio" da Adocao (960x540) e teste de clique."""
from __future__ import annotations

import pygame

from ui.theme import W

ROOM_ROWS = 5
ROOM_ROW_H = 44


def room_panel() -> pygame.Rect:
    return pygame.Rect((W - 740) // 2, 62, 740, 410)


def room_row(i: int) -> pygame.Rect:
    p = room_panel()
    return pygame.Rect(p.x + 44, p.y + 132 + i * ROOM_ROW_H, 436, ROOM_ROW_H - 3)


def room_scroll_button(d: int) -> pygame.Rect:
    p = room_panel()
    return pygame.Rect(p.x + 14, p.y + 132 + (0 if d < 0 else ROOM_ROWS * ROOM_ROW_H - 28), 26, 28)


def room_buttons() -> dict[str, pygame.Rect]:
    p = room_panel()
    x, w = p.x + 504, p.w - 504 - 20
    return {"room_donate": pygame.Rect(x, p.y + 220, w, 44),
            "room_donate_new": pygame.Rect(x, p.y + 276, w, 44),
            "room_cancel": pygame.Rect(x, p.y + 332, w, 44)}


def room_hit(pos: tuple[int, int], ids: list[str]) -> tuple | None:
    for i, cid in enumerate(ids):
        if room_row(i).collidepoint(pos):
            return ("room_pick", cid)
    for d in (-1, 1):
        if room_scroll_button(d).collidepoint(pos):
            return ("room_scroll", d)
    for name, r in room_buttons().items():
        if r.collidepoint(pos):
            return (name,)
    return ("room_panel",) if room_panel().collidepoint(pos) else None
