"""Layout do Criatorio animado (cercado + painel lateral + ficha) em 960x540 e teste de clique."""
from __future__ import annotations

import pygame

from ui import layout_hub as LH
from ui.pen_geometry import PenGeometry

BUTTONS = ("start", "colecao", "adocao", "breed", "menu")      # ordem do painel


def panel_rect(geo: PenGeometry | None = None) -> pygame.Rect:
    return pygame.Rect(geo.panel if geo else (736, 16, 208, 508))


def area_rect(geo: PenGeometry | None = None) -> pygame.Rect:
    return pygame.Rect(geo.walk_area if geo else (48, 96, 664, 372))


def button_rect(name: str, geo: PenGeometry | None = None) -> pygame.Rect:
    p = panel_rect(geo)
    x, w = p.x + 12, p.w - 24
    ys = {"start": 196, "colecao": 262, "adocao": 312, "breed": 362, "menu": p.h - 56}
    hs = {"start": 52, "colecao": 40, "adocao": 40, "breed": 40, "menu": 40}
    return pygame.Rect(x, p.y + ys[name], w, hs[name])


def stats_rect(geo: PenGeometry | None = None) -> pygame.Rect:
    p = panel_rect(geo)
    return pygame.Rect(p.x + 12, p.y + 56, p.w - 24, 120)


def hint_rect(geo: PenGeometry | None = None) -> pygame.Rect:
    p = panel_rect(geo)
    return pygame.Rect(p.x + 12, p.y + 410, p.w - 24, 42)


FICHA_W, FICHA_H = 286, 312


def ficha_rect(cat_x: float, geo: PenGeometry | None = None) -> pygame.Rect:
    """Ficha do gato: do lado do cercado oposto ao gato, para nao cobri-lo."""
    a = area_rect(geo)
    x = a.x + 12 if cat_x > a.centerx else a.right - FICHA_W - 12
    return pygame.Rect(x, a.y + 4, FICHA_W, FICHA_H)


def ficha_close(ficha: pygame.Rect) -> pygame.Rect:
    return pygame.Rect(ficha.right - 32, ficha.y + 8, 24, 24)


def ficha_hit(pos: tuple[int, int], ficha: pygame.Rect) -> tuple | None:
    """Clique dentro da ficha: botoes ou ("ficha",) (absorve o clique)."""
    if not ficha.collidepoint(pos):
        return None
    if ficha_close(ficha).collidepoint(pos):
        return ("ficha_close",)
    if LH.rename_button(ficha).collidepoint(pos):
        return ("ficha_rename",)
    if LH.donate_button(ficha).collidepoint(pos):
        return ("ficha_donate",)
    return ("ficha",)


def panel_hit(pos: tuple[int, int], buttons: tuple[str, ...], geo: PenGeometry | None = None) -> tuple | None:
    for name in buttons:
        if button_rect(name, geo).collidepoint(pos):
            return ("pen_btn", name)
    return None
