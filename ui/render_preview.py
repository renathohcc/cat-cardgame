"""Desenho da previa de ataque/carta (resultado ANTES de confirmar) e dos alvos apagados por
Provocar. So desenha: os numeros vem de `core` (via ui.preview) e nada aqui decide regra."""
from __future__ import annotations

import pygame

from core.types import CatPreview, LeaderPreview, Preview
from ui import font, icons, layout as L, preview
from ui.render import DARK, border, pill, tint
from ui.theme import C

Line = tuple  # (texto, cor, "down" | "up" | None)
ROW = 13


def arrow(surf: pygame.Surface, x: int, y: int, up: bool, color) -> None:
    """Seta 7x5 com contorno escuro; (x, y) = canto superior esquerdo."""
    if up:
        pts, edge = [(x + 3, y), (x + 6, y + 4), (x, y + 4)], [(x + 3, y - 2), (x + 8, y + 5), (x - 2, y + 5)]
    else:
        pts, edge = [(x, y), (x + 6, y), (x + 3, y + 4)], [(x - 2, y - 1), (x + 8, y - 1), (x + 3, y + 6)]
    pygame.draw.polygon(surf, DARK, edge)
    pygame.draw.polygon(surf, color, pts)


def pill_lines(surf: pygame.Surface, cx: int, cy: int, lines: list[Line], edge=None) -> pygame.Rect:
    """Etiqueta escura com `lines` centrada em (cx, cy); seta (opcional) antes do texto."""
    w = max(font.width(t) + (12 if a else 0) for t, _, a in lines) + 10
    r = pygame.Rect(0, 0, w, ROW * len(lines) + 5)
    r.center = (cx, cy)
    pill(surf, r, 240)
    if edge:
        border(surf, r, edge, 1)
    for k, (txt, col, arr) in enumerate(lines):
        y = r.y + 3 + k * ROW
        tw = font.width(txt) + (12 if arr else 0)
        x = r.centerx - tw // 2
        if arr:
            arrow(surf, x + 2, y + 3, arr == "up", col)
            x += 12
        font.draw(surf, txt, x, y, col, 1, "left")
    return r


def cat_lines(cp: CatPreview) -> list[Line]:
    out: list[Line] = []
    if cp.damage:
        out.append((f"-{cp.damage}", C["bad"], "down"))
    if cp.heal:
        out.append((f"+{cp.heal}", C["good"], "up"))
    if cp.hp_after != cp.hp_before and not cp.dies:
        out.append((f"HP {cp.hp_before}>{cp.hp_after}", (255, 255, 255), None))
    if cp.atk_after != cp.atk_before:
        up = cp.atk_after > cp.atk_before
        out.append((f"ATK {cp.atk_before}>{cp.atk_after}", C["buff"], "up" if up else "down"))
    return out


def leader_lines(lp: LeaderPreview) -> list[Line]:
    out: list[Line] = []
    if lp.damage:
        out.append((f"-{lp.damage}", C["bad"], "down"))
    if lp.heal:
        out.append((f"+{lp.heal}", C["good"], "up"))
    if lp.hp_after != lp.hp_before:
        out.append((f"HP {lp.hp_before}>{lp.hp_after}", (255, 255, 255), None))
    return out


def skull(surf: pygame.Surface, center: tuple[int, int], scale: int) -> None:
    ico = icons.get("skull", scale)
    if ico is not None:
        surf.blit(ico, ico.get_rect(center=center))


def draw_cat(surf: pygame.Surface, cp: CatPreview) -> None:
    r = L.slot_rect(cp.side, cp.slot)
    if cp.dies:
        tint(surf, r, C["bad"], 90)
        border(surf, r.inflate(6, 6), C["bad"], 3)
        skull(surf, (r.centerx, r.y + 34), 3)
    lines = cat_lines(cp)
    if lines:
        pill_lines(surf, r.centerx, r.y + (82 if cp.dies else 72), lines)


def draw_leader(surf: pygame.Surface, lp: LeaderPreview) -> None:
    r = L.leader_rect(lp.side)
    if lp.hp_after <= 0:
        tint(surf, r, C["bad"], 110)
        skull(surf, r.center, 2)
    lines = leader_lines(lp)
    if lines:
        hp = L.leader_hp_rect(lp.side)
        w = max(font.width(t) + (12 if a else 0) for t, _, a in lines) + 10
        pill_lines(surf, hp.right + 44 + w // 2, hp.centery, lines)


def draw_verdict(surf: pygame.Surface, pv: Preview) -> None:
    """Aviso quando a jogada encerra o duelo ou dispara o Impasse (resultado sorteado)."""
    if pv.winner == "player":
        txt, col = "ESTA JOGADA VENCE O DUELO", C["good"]
    elif pv.winner == "enemy":
        txt, col = "ESTA JOGADA FAZ VOCÊ PERDER", C["bad"]
    elif pv.deadlock:
        txt, col = "ESTA JOGADA DISPARA O IMPASSE", C["warn"]
    else:
        return
    r = L.toast_rect(font.width(txt) + 32)
    pill(surf, r, 235)
    border(surf, r, col, 2)
    font.draw(surf, txt, r.centerx, r.centery - font.CAP_H // 2, col, 1, "center")


def draw_preview(surf: pygame.Surface, ctrl, ui) -> bool:
    """Desenha a previa do alvo sob o mouse; devolve True se havia previa (some o tooltip)."""
    pv = preview.current(ctrl, ui.mouse)
    if pv is None:
        return False
    for cp in pv.cats:
        draw_cat(surf, cp)
    for lp in pv.leaders:
        draw_leader(surf, lp)
    if ctrl.toast is None:
        draw_verdict(surf, pv)
    return True


# ------------------------------------------------------------------ alvos apagados
def draw_blocked_cat(surf: pygame.Surface, ctrl, side: str, n: int, kind: str) -> None:
    """Gato inimigo que nao e alvo valido: apagado; com Provocar na frente mostra o escudo."""
    r = L.slot_rect(side, n)
    tint(surf, r, DARK, 150)
    if kind == "taunt":
        shield(surf, r.center, 3)


def shield(surf: pygame.Surface, center: tuple[int, int], scale: int) -> None:
    ico = icons.get("shield", scale)
    if ico is not None:
        surf.blit(ico, ico.get_rect(center=center))
    else:                                               # sem sprite: escudo simples por codigo
        pts = [(-12, -12), (12, -12), (12, 2), (0, 14), (-12, 2)]
        pygame.draw.polygon(surf, C["taunt"], [(center[0] + x, center[1] + y) for x, y in pts])
        pygame.draw.polygon(surf, DARK, [(center[0] + x, center[1] + y) for x, y in pts], 2)


def draw_blocked_leader(surf: pygame.Surface, side: str) -> None:
    r = L.leader_rect(side)
    tint(surf, r, DARK, 150)
    shield(surf, r.center, 2)

