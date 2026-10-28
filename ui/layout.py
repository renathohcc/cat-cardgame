"""Layout em coordenadas internas 480x270 e teste de clique (hit test)."""
from __future__ import annotations

import pygame

from ui.theme import H, W

CARD_W, CARD_H = 62, 62
PITCH = 64                       # distancia entre cartas
SLOTS = 5
FIELD_X = 4
MAIN_W = (SLOTS - 1) * PITCH + CARD_W      # 318
PANEL_X = FIELD_X + MAIN_W + 6              # 328
PANEL_W = W - PANEL_X - 4                   # 148

ENEMY_LEADER_Y = 2
ENEMY_FIELD_Y = 27
PLAYER_FIELD_Y = 93
PLAYER_LEADER_Y = 158
LEADER_H = 22
HAND_Y = 184
BAR_Y = 250


def slot_rect(side: str, n: int) -> pygame.Rect:
    y = ENEMY_FIELD_Y if side == "enemy" else PLAYER_FIELD_Y
    return pygame.Rect(FIELD_X + n * PITCH, y, CARD_W, CARD_H)


def leader_rect(side: str) -> pygame.Rect:
    y = ENEMY_LEADER_Y if side == "enemy" else PLAYER_LEADER_Y
    return pygame.Rect(FIELD_X, y, MAIN_W, LEADER_H)


def hand_rect(i: int, n: int) -> pygame.Rect:
    total = (n - 1) * PITCH + CARD_W
    x0 = (W - total) // 2
    return pygame.Rect(x0 + i * PITCH, HAND_Y, CARD_W, CARD_H)


def pass_rect() -> pygame.Rect:
    return pygame.Rect(PANEL_X, 156, PANEL_W, 26)


def pass_yes_rect() -> pygame.Rect:
    r = pass_rect()
    return pygame.Rect(r.x, r.y, r.w * 3 // 5 - 1, r.h)


def pass_no_rect() -> pygame.Rect:
    r = pass_rect()
    y = pass_yes_rect()
    return pygame.Rect(y.right + 2, r.y, r.right - y.right - 2, r.h)


def turn_rect() -> pygame.Rect:
    return pygame.Rect(PANEL_X, 2, PANEL_W, 22)


def info_rect() -> pygame.Rect:
    return pygame.Rect(PANEL_X, 27, PANEL_W, 34)


def log_rect() -> pygame.Rect:
    return pygame.Rect(PANEL_X, 64, PANEL_W, 90)


def energy_rect() -> pygame.Rect:
    return pygame.Rect(4, BAR_Y, 150, 18)


def message_rect() -> pygame.Rect:
    return pygame.Rect(160, BAR_Y, W - 164, 18)


def final_panel() -> pygame.Rect:
    return pygame.Rect(80, 36, 320, 198)


def final_buttons() -> dict[str, pygame.Rect]:
    p = final_panel()
    return {"again": pygame.Rect(p.x + 12, p.bottom - 34, 132, 24),
            "repeat": pygame.Rect(p.right - 144, p.bottom - 34, 132, 24)}


def hit_test(pos: tuple[int, int], n_hand: int, *, final: bool = False,
             confirm: bool = False) -> tuple | None:
    """Elemento sob `pos` (coordenadas internas) ou None."""
    if final:
        for name, r in final_buttons().items():
            if r.collidepoint(pos):
                return (name,)
        return None
    if confirm:
        if pass_yes_rect().collidepoint(pos):
            return ("pass_yes",)
        if pass_no_rect().collidepoint(pos):
            return ("pass_no",)
    if pass_rect().collidepoint(pos):
        return ("pass",)
    for side in ("enemy", "player"):
        if leader_rect(side).collidepoint(pos):
            return ("leader", side)
        for n in range(SLOTS):
            if slot_rect(side, n).collidepoint(pos):
                return ("slot", side, n)
    for i in range(n_hand - 1, -1, -1):
        if hand_rect(i, n_hand).collidepoint(pos):
            return ("hand", i)
    return None


def rect_of(elem: tuple, n_hand: int = 0) -> pygame.Rect | None:
    if elem[0] == "slot":
        return slot_rect(elem[1], elem[2])
    if elem[0] == "leader":
        return leader_rect(elem[1])
    if elem[0] == "hand":
        return hand_rect(elem[1], n_hand)
    if elem[0] == "pass":
        return pass_rect()
    if elem[0] == "pass_yes":
        return pass_yes_rect()
    if elem[0] == "pass_no":
        return pass_no_rect()
    return None


def to_internal(pos: tuple[int, int], win_size: tuple[int, int]) -> tuple[int, int]:
    """Posicao do mouse na janela -> coordenadas internas (pode sair do intervalo)."""
    scale, ox, oy = view_transform(win_size)
    return ((pos[0] - ox) // scale, (pos[1] - oy) // scale)


def view_transform(win_size: tuple[int, int]) -> tuple[int, int, int]:
    """(escala inteira, offset x, offset y): a maior escala inteira que cabe, centralizada."""
    scale = max(1, min(win_size[0] // W, win_size[1] // H))
    return scale, (win_size[0] - W * scale) // 2, (win_size[1] - H * scale) // 2
