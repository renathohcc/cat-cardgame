"""Layout da tela de opcoes e do menu de pausa (960x540) e testes de clique."""
from __future__ import annotations

import pygame

from ui.theme import W

ROWS = ("musica", "efeitos", "mudo", "tela", "velocidade", "tremor", "voltar")
LABELS = {"musica": "MÚSICA", "efeitos": "EFEITOS", "mudo": "SOM", "tela": "TELA",
          "velocidade": "VEL. DO INIMIGO", "tremor": "TREMOR DE TELA", "voltar": ""}
VOL_ROWS = ("musica", "efeitos")
BTN_H = 34
CTRL_X_OFF = 230            # inicio dos controles, relativo ao painel
ROW_STEP = 48


def panel() -> pygame.Rect:
    return pygame.Rect(W // 2 - 280, 60, 560, 432)


def row_y(i: int) -> int:
    return panel().y + 64 + i * ROW_STEP


LABEL_X = panel().x + 24


def row_rect(i: int) -> pygame.Rect:
    p = panel()
    return pygame.Rect(p.x + 12, row_y(i) - 5, p.w - 24, BTN_H + 10)


def _cx() -> int:
    return panel().x + CTRL_X_OFF


def vol_minus(i: int) -> pygame.Rect:
    return pygame.Rect(_cx(), row_y(i), 30, BTN_H)


def vol_bar(i: int) -> pygame.Rect:
    return pygame.Rect(_cx() + 36, row_y(i), 160, BTN_H)


def vol_plus(i: int) -> pygame.Rect:
    return pygame.Rect(_cx() + 202, row_y(i), 30, BTN_H)


def toggle_rect(i: int) -> pygame.Rect:
    return pygame.Rect(_cx(), row_y(i), 200, BTN_H)


def speed_rect(k: int, n: int) -> pygame.Rect:
    w = (300 - 6 * (n - 1)) // max(1, n)
    return pygame.Rect(_cx() + k * (w + 6), row_y(4), w, BTN_H)


def back_rect() -> pygame.Rect:
    return pygame.Rect(W // 2 - 110, row_y(6), 220, 40)


_TOGGLE_ELEM = {2: ("opt_mute",), 3: ("opt_full",), 5: ("opt_shake",)}


def hit_test(pos: tuple[int, int], speeds: list[str]) -> tuple | None:
    for i, which in enumerate(VOL_ROWS):
        if vol_minus(i).collidepoint(pos):
            return ("opt_vol", which, -1)
        if vol_plus(i).collidepoint(pos):
            return ("opt_vol", which, 1)
        bar = vol_bar(i)
        if bar.collidepoint(pos):
            return ("opt_vol_set", which, round(10 * (pos[0] - bar.x) / (bar.w - 1)) / 10)
    for i, elem in _TOGGLE_ELEM.items():
        if toggle_rect(i).collidepoint(pos):
            return elem
    for k, key in enumerate(speeds):
        if speed_rect(k, len(speeds)).collidepoint(pos):
            return ("opt_speed", key)
    return ("opt_back",) if back_rect().collidepoint(pos) else None


def row_of(elem: tuple) -> int:
    kind = elem[0]
    if kind in ("opt_vol", "opt_vol_set"):
        return ROWS.index(elem[1])
    return {"opt_mute": 2, "opt_full": 3, "opt_speed": 4, "opt_shake": 5, "opt_back": 6}.get(kind, 0)


# ------------------------------------------------------------------ pausa
PAUSE_W, PAUSE_BTN_H, PAUSE_STEP = 440, 48, 58


def pause_panel(n: int) -> pygame.Rect:
    h = 76 + n * PAUSE_STEP + 18
    return pygame.Rect(W // 2 - PAUSE_W // 2, (540 - h) // 2, PAUSE_W, h)


def pause_button(i: int, n: int) -> pygame.Rect:
    p = pause_panel(n)
    return pygame.Rect(p.x + 30, p.y + 64 + i * PAUSE_STEP, p.w - 60, PAUSE_BTN_H)


def pause_hit(pos: tuple[int, int], items: list[str]) -> tuple | None:
    for i, name in enumerate(items):
        if pause_button(i, len(items)).collidepoint(pos):
            return ("pause", name)
    return None


def ask_panel() -> pygame.Rect:
    return pygame.Rect(W // 2 - 270, 160, 540, 210)


def ask_buttons() -> dict[str, pygame.Rect]:
    p = ask_panel()
    return {"ask_yes": pygame.Rect(p.x + 24, p.bottom - 66, 232, 46),
            "ask_no": pygame.Rect(p.right - 256, p.bottom - 66, 232, 46)}


def ask_hit(pos: tuple[int, int]) -> tuple | None:
    for name, r in ask_buttons().items():
        if r.collidepoint(pos):
            return (name,)
    return None
