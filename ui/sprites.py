"""Sprites (gatos, Espiritos, efeitos, icones, lideres) com cache e fallback gracioso.

Tudo passa por AQUI: as telas pedem `get(kind, name, size)`/`draw(...)` e a arte entra sem
mexer nelas. Cada `kind` tem uma lista de FONTES em ordem de preferencia (tabela `SOURCES`):
a primeira que tiver o sprite vence; sheets antigos (48x48 / 9x9) sao ampliados em escala
inteira (nearest) ate chegarem os novos (96x96 / 16x16). Formato do sheet:
`{"image": "x.png", "size": [w, h], "sprites": {nome: {x, y, w, h}}}`.

Caminhos relativos ao projeto (via __file__). Se arquivo/sprite faltar, `get` devolve None e
quem desenha usa o placeholder. Sempre nearest (sem suavizacao).
"""
from __future__ import annotations

import json
from pathlib import Path

import pygame

_ROOT = Path(__file__).resolve().parent.parent / "assets"
SPRITE = 96                    # tamanho nativo da arte de gato/Espirito/efeito na carta
ICON = 16                      # tamanho nativo dos icones (badges)

# kind -> [(pasta, nome do json, ampliacao inteira)] em ordem de preferencia (novo primeiro,
# antigo depois). Sheets antigos (48x48, 9x9) entram ampliados 2x ate a arte nova chegar.
SOURCES: dict[str, list[tuple[str, str, int]]] = {
    "cat": [("cats96", "spritesheet.json", 1), ("cats", "spritesheet.json", 2)],
    "special": [("specials96", "spritesheet.json", 1), ("specials", "spritesheet.json", 2)],
    "effect": [("effects96", "spritesheet.json", 1), ("effects", "spritesheet.json", 2)],
    "icon": [("icons16", "spritesheet.json", 1), ("icons", "spritesheet.json", 2)],
    "leader": [("leaders", "spritesheet.json", 1)],
    # lideres em 128 (menu, fim de run, resultado); sem o sheet 128 cai para o 96 ampliado
    "leader128": [("leaders", "spritesheet128.json", 1), ("leaders", "spritesheet.json", 1)],
}


class _Sheet:
    def __init__(self, folder: str, json_name: str) -> None:
        self.rects: dict[str, pygame.Rect] = {}
        self.image: pygame.Surface | None = None
        try:
            base = _ROOT / folder
            data = json.loads((base / json_name).read_text(encoding="utf-8"))
            img = pygame.image.load(str(base / data["image"]))
            self.image = img.convert_alpha() if pygame.display.get_surface() else img
            self.rects = {k: pygame.Rect(v["x"], v["y"], v["w"], v["h"])
                          for k, v in data["sprites"].items()}
        except Exception:                  # ausente/corrompido: usa placeholders
            self.image, self.rects = None, {}


_sheets: dict[tuple[str, str], _Sheet] = {}
_cache: dict[tuple[str, str, int], pygame.Surface | None] = {}


def reset() -> None:
    """Esvazia os caches (testes / troca de display / arte nova)."""
    _sheets.clear()
    _cache.clear()


def _sheet(folder: str, json_name: str) -> _Sheet:
    key = (folder, json_name)
    if key not in _sheets:
        _sheets[key] = _Sheet(folder, json_name)
    return _sheets[key]


def get(kind: str, name: str | None, size: int | None = None) -> pygame.Surface | None:
    """Sprite `name` do `kind` ou None. `size` None = tamanho nativo da fonte (sheet novo, ou
    antigo ampliado em escala inteira); com `size`, redimensiona a altura (nearest)."""
    if not name or kind not in SOURCES:
        return None
    key = (kind, name, size or 0)
    if key in _cache:
        return _cache[key]
    surf = None
    for folder, json_name, up in SOURCES[kind]:
        sh = _sheet(folder, json_name)
        r = sh.rects.get(name)
        if r is None or sh.image is None:
            continue
        try:
            surf = sh.image.subsurface(r).copy()
        except (ValueError, pygame.error):
            surf = None
            continue
        h = size or surf.get_height() * up
        if surf.get_height() != h:
            surf = pygame.transform.scale(surf, (round(surf.get_width() * h / surf.get_height()), h))
        break
    _cache[key] = surf
    return surf


def get_cat(breed: str | None, size: int | None = None) -> pygame.Surface | None:
    return get("cat", breed, size)


def draw(surf: pygame.Surface, breed: str | None, x: int, y: int, size: int | None = None,
         clip: pygame.Rect | None = None, src_dy: int = 0, kind: str = "cat") -> bool:
    """Desenha o sprite em (x, y). `clip` recorta na tela; `src_dy` sobe o sprite (corte).
    Devolve False se nao ha sprite (o chamador desenha o placeholder)."""
    spr = get(kind, breed, size)
    if spr is None:
        return False
    old = surf.get_clip()
    if clip is not None:
        surf.set_clip(clip.clip(old) if old else clip)
    surf.blit(spr, (x, y - src_dy))
    surf.set_clip(old)
    return True
