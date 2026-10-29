"""Pecas de UI do tema (assets/ui/<tema>/ui.json) e o fundo do tabuleiro (assets/board/final).

Tudo com fallback: se um arquivo faltar (ou nao houver display em teste headless), `piece`/`nine`/
`board` devolvem None/False e quem desenha usa o retangulo de paleta de sempre.
`nine(surf, nome, rect)` desenha uma peca 9-slice [esq, topo, dir, base] esticada ate `rect`.
"""
from __future__ import annotations

import json
from pathlib import Path

import pygame

THEME = "noturno"
_ASSETS = Path(__file__).resolve().parent.parent / "assets"

_meta: dict | None = None
_pieces: dict[str, pygame.Surface | None] = {}
_nine_cache: dict[tuple, pygame.Surface] = {}
_board: pygame.Surface | None = None
_board_tried = False
_bg: pygame.Surface | None = None


def reset() -> None:
    global _meta, _board, _board_tried, _bg
    _meta, _board, _board_tried, _bg = None, None, False, None
    _pieces.clear()
    _nine_cache.clear()


def _load_meta() -> dict:
    global _meta
    if _meta is None:
        try:
            _meta = json.loads((_ASSETS / "ui" / THEME / "ui.json").read_text(encoding="utf-8"))["pieces"]
        except Exception:
            _meta = {}
    return _meta


def piece(name: str) -> pygame.Surface | None:
    """Surface da peca (tamanho nativo) ou None."""
    if name not in _pieces:
        surf = None
        info = _load_meta().get(name)
        if info:
            try:
                img = pygame.image.load(str(_ASSETS / "ui" / info["file"]))
                surf = img.convert_alpha() if pygame.display.get_surface() else img
            except Exception:
                surf = None
        _pieces[name] = surf
    return _pieces[name]


def blit(surf: pygame.Surface, name: str, pos: tuple[int, int], center: bool = False) -> bool:
    p = piece(name)
    if p is None:
        return False
    surf.blit(p, p.get_rect(center=pos) if center else pos)
    return True


def nine(surf: pygame.Surface, name: str, rect: pygame.Rect) -> bool:
    """Desenha a peca 9-slice em `rect`. False se faltar (use o fallback)."""
    p = piece(name)
    info = _load_meta().get(name)
    if p is None or info is None or "nine_slice" not in info:
        return False
    key = (name, rect.w, rect.h)
    img = _nine_cache.get(key)
    if img is None:
        img = _build_nine(p, info["nine_slice"], rect.w, rect.h)
        if len(_nine_cache) > 64:
            _nine_cache.clear()
        _nine_cache[key] = img
    surf.blit(img, rect.topleft)
    return True


def _build_nine(p: pygame.Surface, ns: list[int], w: int, h: int) -> pygame.Surface:
    l, t, r, b = ns
    sw, sh = p.get_size()
    w, h = max(w, l + r), max(h, t + b)
    out = pygame.Surface((w, h), pygame.SRCALPHA)
    xs = [(0, l, 0, l), (l, w - r, l, sw - r), (w - r, w, sw - r, sw)]
    ys = [(0, t, 0, t), (t, h - b, t, sh - b), (h - b, h, sh - b, sh)]
    for dy0, dy1, sy0, sy1 in ys:
        for dx0, dx1, sx0, sx1 in xs:
            src = pygame.Rect(sx0, sy0, sx1 - sx0, sy1 - sy0)
            if src.w <= 0 or src.h <= 0 or dx1 - dx0 <= 0 or dy1 - dy0 <= 0:
                continue
            piece_img = p.subsurface(src)
            if (dx1 - dx0, dy1 - dy0) != src.size:
                piece_img = pygame.transform.scale(piece_img, (dx1 - dx0, dy1 - dy0))
            out.blit(piece_img, (dx0, dy0))
    return out


# ------------------------------------------------------------------ fundos
def board() -> pygame.Surface | None:
    """Tabuleiro pintado do duelo (960x540) ou None."""
    global _board, _board_tried
    if not _board_tried:
        _board_tried = True
        try:
            img = pygame.image.load(str(_ASSETS / "board" / "final" / f"board_{THEME}.png"))
            _board = img.convert() if pygame.display.get_surface() else img
        except Exception:
            _board = None
    return _board


def screen_background(size: tuple[int, int]) -> pygame.Surface | None:
    """Fundo das telas do hub/run: o centro do tabuleiro noturno (trama + estrelas) esticado,
    escurecido, com a moldura externa do tabuleiro. None se a arte faltar."""
    global _bg
    if _bg is not None and _bg.get_size() == size:
        return _bg
    b = board()
    if b is None:
        return None
    w, h = size
    out = pygame.Surface(size)
    # miolo liso do campo (sem placas/slots): repete uma faixa de 160x120 pela tela inteira
    tile = b.subsurface(pygame.Rect(200, 70, 160, 110)).copy()
    for y in range(0, h, tile.get_height()):
        for x in range(0, w, tile.get_width()):
            out.blit(tile, (x, y))
    shade = pygame.Surface(size, pygame.SRCALPHA)
    for y in range(h):                      # mais escuro embaixo (texto legivel)
        a = int(40 + 90 * y / (h - 1))
        pygame.draw.line(shade, (8, 10, 22, a), (0, y), (w, y))
    out.blit(shade, (0, 0))
    # moldura: bordas externas do tabuleiro (6 px) recortadas e coladas
    if (w, h) == b.get_size():
        for r in (pygame.Rect(0, 0, w, 8), pygame.Rect(0, h - 8, w, 8),
                  pygame.Rect(0, 0, 8, h), pygame.Rect(w - 8, 0, 8, h)):
            out.blit(b, r.topleft, r)
        for cx, cy in ((0, 0), (w - 16, 0), (0, h - 16), (w - 16, h - 16)):     # cantos
            out.blit(b, (cx, cy), pygame.Rect(cx, cy, 16, 16))
    _bg = out
    return out
