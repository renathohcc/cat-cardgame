"""Desenho das areas bloqueadas do quintal: camada, placa com preco, animacao de desbloqueio e cesta.

Ordem (relatorio T13.3): fundo -> objetos/gatos -> camada de bloqueio -> placa -> preco -> icones.
Camada e placa levam a mesma tinta do periodo do dia que o fundo. Estado (livre/apagada) vem do
`ShopController` (core); aqui so desenho.
"""
from __future__ import annotations

from dataclasses import dataclass

import pygame

from ui import font, lock_art, pen_world, timing as timing_mod
from ui.lock_art import LockArt
from ui.pen_sprites import PenArt
from ui.render import mix_c, pulse, tint
from ui.theme import C
from ui.widgets import WHITE

PRICE_COLOR = (74, 44, 20)          # tinta escura sobre a madeira da placa
PRICE_COLOR_OFF = (118, 100, 84)
SIGN_GLOW = (255, 230, 140)


@dataclass
class UnlockFx:
    """Area recem-comprada: a camada some em `economy.unlock_fade` e a explosao ladrilha o retangulo."""
    area_id: str
    t: float = 0.0

    @property
    def duration(self) -> float:
        return timing_mod.current().economy.unlock_fade + timing_mod.current().economy.unlock_fx_hold

    @property
    def done(self) -> bool:
        return self.t >= self.duration


def update_fx(fx: list[UnlockFx], dt: float) -> list[UnlockFx]:
    for f in fx:
        f.t += dt
    return [f for f in fx if not f.done]


def sign_pos(la: LockArt, area_id: str) -> pygame.Rect | None:
    a = la.area(area_id)
    return pygame.Rect(pen_world.sign_rect(a, la.spec.sign_size)) if a else None


def _layer(surf: pygame.Surface, la: LockArt, area: pen_world.LockArea, tint_c, alpha: float = 1.0) -> None:
    img = la.tinted(la.layers[area.id], tint_c)
    if alpha < 0.999:
        img = img.copy()
        img.set_alpha(round(255 * max(0.0, alpha)))
    surf.blit(img, area.rect[:2])


def _unlock_burst(surf: pygame.Surface, la: LockArt, area: pen_world.LockArea, progress: float) -> None:
    fr = la.frame_at(progress)
    if fr is None:
        return
    x, y, w, h = area.rect
    fw, fh = fr.get_size()
    prev = surf.get_clip()
    surf.set_clip(pygame.Rect(x - fw // 2, y - fh // 2, w + fw, h + fh).clip(prev))
    cols, rows = max(1, -(-w // fw)), max(1, -(-h // fh))
    for r in range(rows):
        for c in range(cols):
            cx = x + min(w - fw // 2, c * fw + fw // 2)
            cy = y + min(h - fh // 2, r * fh + fh // 2)
            surf.blit(fr, (cx - fw // 2, cy - fh // 2))
    surf.set_clip(prev)


def draw_price(surf: pygame.Surface, la: LockArt, sign: pygame.Rect, price: int, off: bool) -> None:
    tx, ty, tw, th = la.spec.text_rect
    r = pygame.Rect(sign.x + tx, sign.y + ty, tw, th)
    txt = str(price)
    font.draw(surf, txt, r.centerx, r.centery - font.CAP_H // 2, PRICE_COLOR_OFF if off else PRICE_COLOR, 1, "center")


def draw_requirements(surf: pygame.Surface, la: LockArt, sign: pygame.Rect, state: str, row) -> None:
    """Mini-selo sob a placa: cadeado + Prestigio exigido, ou moeda + quanto falta."""
    if state == "blocked_prestige":
        items = [("cadeado", ""), ("prestigio", str(row.prestige))]
    elif state == "blocked_coins":
        items = [("moeda", f"faltam {row.missing_coins}")]
    elif state == "queued":
        items = [("cadeado", "")]
    else:
        return
    w = sum(19 + (font.width(t, 1) + 2 if t else 0) for _, t in items) + 6
    r = pygame.Rect(sign.centerx - w // 2, sign.bottom + 2, w, 20)
    tint(surf, r, (10, 12, 24), 200)
    x = r.x + 4
    for name, text in items:
        surf.blit(la.icon(name), (x, r.y + 2))
        x += 19
        if text:
            font.draw(surf, text, x, r.centery - font.CAP_H // 2, WHITE, 1)
            x += font.width(text, 1) + 2


def draw_locks(surf: pygame.Surface, la: LockArt, art: PenArt, day, shop, fx: list[UnlockFx], t: float,
               hover: str | None = None) -> None:
    """Camadas das areas ainda bloqueadas + animacao das recem-compradas, depois as placas."""
    tint_c = art.tint_for(day)
    states = {r.id: r for r in shop.areas()}
    for area in la.spec.areas:
        row = states.get(area.id)
        if row is not None and not row.done:
            _layer(surf, la, area, tint_c)
    cfg = timing_mod.current().economy
    for f in fx:
        area = la.area(f.area_id)
        if area is None:
            continue
        k = min(1.0, f.t / max(1e-6, cfg.unlock_fade))
        _layer(surf, la, area, tint_c, 1.0 - k)
        _unlock_burst(surf, la, area, k)
    per = max(0.1, cfg.sign_pulse_period)
    for area in la.spec.areas:
        row = states.get(area.id)
        if row is None or row.done:
            continue
        sign = pygame.Rect(pen_world.sign_rect(area, la.spec.sign_size))
        free = row.can_buy
        img = la.tinted(la.sign(free), tint_c)
        bob = -round(pulse(t, 6.283 / per) * 2) if free else 0
        surf.blit(img, (sign.x, sign.y + bob))
        draw_price(surf, la, sign.move(0, bob), row.price, not free)
        if free:
            glow = pygame.Rect(sign.x - 2, sign.y + bob - 2, sign.w + 4, sign.h + 4)
            pygame.draw.rect(surf, mix_c(SIGN_GLOW, WHITE, pulse(t, 6.283 / per)), glow, 1, border_radius=3)
        if hover == area.id:
            pygame.draw.rect(surf, WHITE, sign.inflate(4, 4), 1, border_radius=3)
        draw_requirements(surf, la, sign, row.state, row)


def draw_hover_label(surf: pygame.Surface, sign: pygame.Rect, name: str, price: int) -> None:
    txt = f"{name}: {price}"
    w = font.width(txt, 1) + 14
    r = pygame.Rect(sign.centerx - w // 2, sign.y - 22, w, font.CAP_H + 10)
    r.clamp_ip(pygame.Rect(4, 4, 700, 400))
    pygame.draw.rect(surf, C["dark"], r, border_radius=4)
    pygame.draw.rect(surf, C["warn"], r, 1, border_radius=4)
    font.draw(surf, txt, r.centerx, r.y + 5, C["text"], 1, "center")


def draw_basket(surf: pygame.Surface, la: LockArt, art: PenArt, day, n: int, rect: tuple[int, int, int, int]) -> None:
    """Cesta dos filhotes (antes do cercadinho): o objeto do viveiro sobre a camada, com a contagem."""
    x = rect[0] + 54
    y = rect[1] + 78
    img = art.object_frame("viveiro_cesto", "idle", 0.0)
    if img is not None:
        ax, ay = art.anchor("viveiro_cesto")
        surf.blit(art.tinted(img, art.tint_for(day)), (x - ax, y - ay))
    else:
        pygame.draw.ellipse(surf, (176, 128, 70), pygame.Rect(x - 26, y - 14, 52, 16))
    if n > 0:
        label = f"CESTA: {n} filhote{'s' if n != 1 else ''}"
        w = font.width(label, 1) + 14
        r = pygame.Rect(x - 20, y - 66, w, 20)
        pygame.draw.rect(surf, C["dark"], r, border_radius=4)
        pygame.draw.rect(surf, C["female"], r, 1, border_radius=4)
        font.draw(surf, label, r.centerx, r.centery - font.CAP_H // 2, C["text"], 1, "center")
