"""Layout das telas da mini-run (mapa, draft, fim, confirmacao) em 960x540 e teste de clique."""
from __future__ import annotations

import pygame

from ui.theme import H, W

# ------------------------------------------------------------------ mapa
NODE_W, NODE_H = 132, 88
MAP_X0, MAP_X1 = 96, 864            # centros da primeira e da ultima camada
MAP_Y0, MAP_Y1 = 132, 410           # faixa vertical dos nos


def node_rect(layer: int, idx: int, n_in_layer: int, n_layers: int) -> pygame.Rect:
    cx = (MAP_X0 + MAP_X1) // 2 if n_layers < 2 else         MAP_X0 + (MAP_X1 - MAP_X0) * layer // (n_layers - 1)
    cy = MAP_Y0 + (MAP_Y1 - MAP_Y0) * (2 * idx + 1) // (2 * n_in_layer)
    r = pygame.Rect(0, 0, NODE_W, NODE_H)
    r.center = (cx, cy)
    return r


def map_info_rect() -> pygame.Rect:
    return pygame.Rect(12, 440, 730, 88)


def abandon_rect() -> pygame.Rect:
    return pygame.Rect(W - 200, 462, 188, 48)


def title_rect() -> pygame.Rect:
    return pygame.Rect(12, 8, W - 24, 44)


# ------------------------------------------------------------------ draft
DRAFT_W, DRAFT_H, DRAFT_PITCH = 272, 318, 288
DRAFT_Y = 76


def draft_card_rect(i: int, n: int) -> pygame.Rect:
    total = (n - 1) * DRAFT_PITCH + DRAFT_W
    return pygame.Rect((W - total) // 2 + i * DRAFT_PITCH, DRAFT_Y, DRAFT_W, DRAFT_H)


def draft_pick_rect(i: int, n: int) -> pygame.Rect:
    r = draft_card_rect(i, n)
    return pygame.Rect(r.x, r.bottom + 6, r.w, 38)


def draft_deck_rect() -> pygame.Rect:
    return pygame.Rect(12, 448, W - 24, 82)


# ------------------------------------------------------------------ fim da run
def end_buttons() -> dict[str, pygame.Rect]:
    return {"new_run": pygame.Rect(W // 2 - 280, 474, 270, 48),
            "quit": pygame.Rect(W // 2 + 10, 474, 270, 48)}


# ------------------------------------------------------------------ confirmar abandono
def quit_panel() -> pygame.Rect:
    return pygame.Rect(W // 2 - 260, 170, 520, 200)


def quit_buttons() -> dict[str, pygame.Rect]:
    p = quit_panel()
    return {"quit_yes": pygame.Rect(p.x + 24, p.bottom - 66, 232, 46),
            "quit_no": pygame.Rect(p.right - 256, p.bottom - 66, 232, 46)}


def hit_test(pos: tuple[int, int], screen: str, *, nodes: list[tuple[str, pygame.Rect]] | None = None,
             n_draft: int = 0, selected: int | None = None, confirm: bool = False,
             finished: bool = False) -> tuple | None:
    """Elemento sob `pos` nas telas da run (o duelo usa `layout.hit_test`)."""
    if confirm:
        for name, r in quit_buttons().items():
            if r.collidepoint(pos):
                return (name,)
        return None
    if screen == "map":
        for node_id, r in nodes or []:
            if r.collidepoint(pos):
                return ("node", node_id)
        if abandon_rect().collidepoint(pos):
            return ("abandon",)
    elif screen == "draft":
        if selected is not None and 0 <= selected < n_draft and \
                draft_pick_rect(selected, n_draft).collidepoint(pos):
            return ("draft_pick", selected)
        for i in range(n_draft):
            if draft_card_rect(i, n_draft).collidepoint(pos):
                return ("draft_card", i)
    elif screen == "finished" or finished:
        for name, r in end_buttons().items():
            if r.collidepoint(pos):
                return (name,)
    return None
