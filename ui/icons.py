"""Icones 16x16 do registro e da previa do duelo: ataque, dano, cura, morte (caveira), setas.

Usa os sprites de `assets/icons16` pelo modulo `sprites` quando existem; a caveira (que nao tem
sprite) e todos os demais caem num desenho simples por codigo, para a arte poder entrar depois
sem mexer nas telas. Sempre nearest, cache por (nome, escala).
"""
from __future__ import annotations

import pygame

from ui import sprites

SIZE = 16
OUT = (40, 28, 48)                 # contorno escuro dos icones pintados
BONE = (236, 232, 218)

_SPRITE = {"attack": "ataque", "damage": "acao-dano", "heal": "acao-cura", "shield": "provocar",
           "buff": "acao-buff_atk"}
_cache: dict[tuple[str, int], pygame.Surface] = {}


def _skull() -> pygame.Surface:
    s = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
    pygame.draw.circle(s, OUT, (8, 7), 7)
    pygame.draw.rect(s, OUT, (4, 9, 8, 7))
    pygame.draw.circle(s, BONE, (8, 7), 6)
    pygame.draw.rect(s, BONE, (5, 9, 6, 5))
    for x in (4, 9):                                    # olhos
        pygame.draw.rect(s, OUT, (x, 6, 3, 3))
    pygame.draw.rect(s, OUT, (7, 10, 2, 2))             # nariz
    for x in (6, 8, 10):                                # dentes
        pygame.draw.line(s, OUT, (x, 13), (x, 14))
    return s


def _sword() -> pygame.Surface:
    s = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
    pygame.draw.line(s, OUT, (4, 12), (13, 3), 5)
    pygame.draw.line(s, (200, 210, 225), (5, 11), (12, 4), 2)
    pygame.draw.line(s, (230, 190, 70), (3, 8), (8, 13), 3)
    return s


def _burst() -> pygame.Surface:
    s = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
    pts = [(8, 0), (10, 5), (15, 4), (11, 8), (15, 12), (10, 11), (8, 15), (6, 11), (1, 12),
           (5, 8), (1, 4), (6, 5)]
    pygame.draw.polygon(s, OUT, pts)
    pygame.draw.polygon(s, (240, 90, 60), [(8, 2), (9, 6), (13, 5), (10, 8), (13, 11), (9, 10),
                                           (8, 13), (7, 10), (3, 11), (6, 8), (3, 5), (7, 6)])
    return s


def _cross() -> pygame.Surface:
    s = pygame.Surface((SIZE, SIZE), pygame.SRCALPHA)
    pygame.draw.rect(s, OUT, (5, 1, 6, 14))
    pygame.draw.rect(s, OUT, (1, 5, 14, 6))
    pygame.draw.rect(s, (90, 210, 120), (6, 2, 4, 12))
    pygame.draw.rect(s, (90, 210, 120), (2, 6, 12, 4))
    return s


_CODED = {"skull": _skull, "attack": _sword, "damage": _burst, "heal": _cross}


def get(name: str, scale: int = 1) -> pygame.Surface | None:
    """Icone `name` (skull | attack | damage | heal | shield | buff) em `scale`x (inteiro)."""
    key = (name, scale)
    if key in _cache:
        return _cache[key]
    spr = sprites.get("icon", _SPRITE.get(name)) if name in _SPRITE else None
    if spr is None and name in _CODED:
        spr = _CODED[name]()
    if spr is not None and scale != 1:
        spr = pygame.transform.scale(spr, (spr.get_width() * scale, spr.get_height() * scale))
    if spr is not None:
        _cache[key] = spr
    return spr


def reset() -> None:
    _cache.clear()
