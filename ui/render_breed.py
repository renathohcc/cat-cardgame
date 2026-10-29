"""Desenho do Criatorio e das Novidades do Criatorio em 960x540 nativo."""
from __future__ import annotations

import pygame

from ui import font, layout_breed as LB, sprites, widgets as Wd
from ui.breed_controller import BreedController, BreedRow, NewsController
from ui.render import UIState, mix_c, pulse, text_fit
from ui.render_hub import SEX_NAME, sex_color
from ui.theme import C, H, NATURE_COLOR, W
from ui.widgets import WHITE, button, panel

SIDE_NAME = {"M": "MACHOS", "F": "FÊMEAS"}


def _small_cat(surf: pygame.Surface, breed: str, cx: int, cy: int, kitten: bool = False) -> None:
    """Sprite do adulto reduzido (nearest): 32 px; filhote 24 px, ate haver arte propria."""
    spr = sprites.get("cat", breed, 24 if kitten else 32)
    if spr is not None:
        surf.blit(spr, spr.get_rect(center=(cx, cy)))


def _row(surf: pygame.Surface, bc: BreedController, row: BreedRow, side: str, i: int, ui: UIState) -> None:
    r = LB.row_rect(side, i)
    cat, st = row.cat, row.stats
    sel = bc.sel[side] == cat.id
    fill = (46, 62, 90) if sel else C["slot"]
    if r.collidepoint(ui.mouse):
        fill = mix_c(fill, WHITE, 0.12)
    pygame.draw.rect(surf, fill, r, border_radius=4)
    pygame.draw.rect(surf, WHITE if sel else C["slot_edge"], r, 2 if sel else 1, border_radius=4)
    _small_cat(surf, cat.breed, r.x + 22, r.centery)
    x = r.x + 44
    ax = r.right - 8
    stats = f"{st.atk}/{st.hp}"
    font.draw(surf, font.fit(row.label, ax - font.width(stats) - 12 - x), x, r.y + 4, C["text"], 1)
    font.draw(surf, f"{st.atk}", ax - font.advance(f"/{st.hp}"), r.y + 4, C["atk"], 1, "right")
    font.draw(surf, f"/{st.hp}", ax, r.y + 4, C["hp"], 1, "right")
    y2 = r.y + 22
    font.draw(surf, font.fit(row.breed, 100), x, y2, Wd.breed_color(cat.breed))
    font.draw(surf, font.fit(bc.nature_name(cat), 70), x + 104, y2, NATURE_COLOR.get(cat.nature, C["text"]))
    Wd.stars(surf, r.x + 228, y2 + 2, cat.iv_atk, 1)
    Wd.stars(surf, r.x + 264, y2 + 2, cat.iv_hp, 1)


def _list(surf: pygame.Surface, bc: BreedController, side: str, ui: UIState) -> None:
    h = LB.list_header(side)
    total = len(bc.rows(side))
    font.draw(surf, f"{SIDE_NAME[side]} ({total})", h.x + 4, h.centery - font.CAP_H // 2, sex_color(side), 1)
    ms = bc.max_scroll(side)
    Wd.arrow(surf, LB.scroll_button(side, -1), True, bc.scroll[side] > 0, ui.mouse)
    Wd.arrow(surf, LB.scroll_button(side, 1), False, bc.scroll[side] < ms, ui.mouse)
    rows = bc.visible_rows(side)
    for i, row in enumerate(rows):
        _row(surf, bc, row, side, i, ui)
    if not rows:
        font.draw(surf, "Nenhum disponível.", LB.LIST_X[side] + LB.LIST_W // 2, LB.LIST_Y0 + 40,
                  C["dim"], 1, "center")


def _breeding_panel(surf: pygame.Surface, bc: BreedController, ui: UIState) -> None:
    p = LB.breed_panel()
    panel(surf, p)
    couples = bc.couples()
    font.draw(surf, f"EM BREED ({len(couples)})", p.x + 10, p.y + 10, C["warn"], 1)
    if not couples:
        font.draw(surf, "Nenhum casal.", p.centerx, p.y + 90, C["dim"], 1, "center")
    for i, cp in enumerate(couples[:LB.COUPLES_VISIBLE]):
        r = LB.couple_rect(i)
        pygame.draw.rect(surf, C["slot"], r, border_radius=4)
        pygame.draw.rect(surf, C["slot_edge"], r, 1, border_radius=4)
        text_fit(surf, f"{bc.label(cp.male)} + {bc.label(cp.female)}", r.x + 8, r.y + 6, C["text"],
                 r.w - 16, "left")
        n = cp.runs_left
        font.draw(surf, f"faltam {n} run{'s' if n != 1 else ''}", r.x + 8, r.y + 31, C["good"], 1)
        button(surf, LB.cancel_button(i), "CANCELAR", ui.mouse, enabled=cp.can_cancel, base=(110, 44, 52))
    if len(couples) > LB.COUPLES_VISIBLE:
        font.draw(surf, f"+{len(couples) - LB.COUPLES_VISIBLE} casal(is)", p.right - 10, p.y + 10, C["dim"], 1, "right")


def _kitten_panel(surf: pygame.Surface, bc: BreedController) -> None:
    p = LB.kitten_panel()
    panel(surf, p)
    ks = bc.kittens()
    font.draw(surf, f"FILHOTES ({len(ks)})", p.x + 10, p.y + 10, C["female"], 1)
    if not ks:
        font.draw(surf, "Nenhum filhote.", p.centerx, p.y + 90, C["dim"], 1, "center")
    for i, (cat, left) in enumerate(ks[:LB.KITTENS_VISIBLE]):
        y = p.y + 34 + i * LB.KITTEN_H
        _small_cat(surf, cat.breed, p.x + 24, y + 16, kitten=True)
        font.draw(surf, font.fit(bc.label(cat), 120), p.x + 44, y, Wd.breed_color(cat.breed), 1)
        Wd.sex_badge(surf, p.x + 184, y + 5, cat.sex, 8)
        font.draw(surf, f"{left} run{'s' if left != 1 else ''}", p.right - 10, y, C["good"], 1, "right")
        font.draw(surf, "ATK", p.x + 44, y + 16, C["atk"], 1)
        Wd.stars(surf, p.x + 82, y + 18, cat.iv_atk, 1)
        font.draw(surf, "HP", p.x + 124, y + 16, C["hp"], 1)
        Wd.stars(surf, p.x + 150, y + 18, cat.iv_hp, 1)
    if len(ks) > LB.KITTENS_VISIBLE:
        font.draw(surf, f"+{len(ks) - LB.KITTENS_VISIBLE}", p.right - 10, p.y + 10, C["dim"], 1, "right")


def _side_panel(surf: pygame.Surface, bc: BreedController, ui: UIState) -> None:
    p = LB.side_panel()
    panel(surf, p)
    x, w = p.x + 12, p.w - 24
    font.draw(surf, "CASAL", x, p.y + 12, C["warn"], 1)
    colw = (w - 8) // 2
    for k, side in enumerate(("M", "F")):
        cat = bc.selected(side)
        cx = x + k * (colw + 8)
        box = pygame.Rect(cx, p.y + 36, colw, 138)
        pygame.draw.rect(surf, C["slot"], box, border_radius=4)
        pygame.draw.rect(surf, sex_color(side), box, 1, border_radius=4)
        Wd.sex_badge(surf, box.x + 12, box.y + 12, side)
        if cat is None:
            font.draw(surf, "escolha", box.centerx, box.y + 62, C["dim"], 1, "center")
            continue
        Wd.cat_art(surf, cat.breed, pygame.Rect(box.centerx - 48, box.y + 4, 96, 96), bg=C["slot"])
        text_fit(surf, bc.label(cat), box.centerx, box.y + 104, C["text"], box.w - 8, "center")
        font.draw(surf, font.fit(bc.breed_name(cat), box.w - 8), box.centerx, box.y + 122, Wd.breed_color(cat.breed), 1, "center")
    y = p.y + 188
    odds = bc.breed_odds()
    if odds:
        font.draw(surf, font.fit("Raça provável do filhote:", w), x, y, C["dim"], 1)
        y += 15
        for pct, name in odds[:3]:
            text_fit(surf, f"{pct}% {name}", x, y, C["text"], w, "left")
            y += 15
    else:
        y = Wd.wrap_lines(surf, "Raça do filhote: escolha o casal.", x, y, w, C["dim"], 1, 2, 14)
    y += 4
    y = Wd.wrap_lines(surf, bc.litter_text(), x, y, w, C["text"], 1, 1, 15)
    y = Wd.wrap_lines(surf, bc.time_text(), x, y, w, C["text"], 1, 1, 15)
    y += 4
    ok, motivo = bc.verdict()
    if not ok:
        Wd.wrap_lines(surf, motivo, x, y, w, C["warn"] if bc.pair() else C["dim"], 1, 4, 14)
    else:
        font.draw(surf, "Casal válido.", x, y, C["good"], 1)
    b = LB.action_buttons()
    button(surf, b["start"], "INICIAR BREED", ui.mouse, enabled=ok, base=(46, 120, 80))
    button(surf, b["back"], "VOLTAR (ESC)", ui.mouse, base=C["card"])


def draw_breed(surf: pygame.Surface, bc: BreedController, ui: UIState) -> None:
    Wd.title(surf, "CRIATÓRIO", 22, 14, C["text"], 2)
    font.draw(surf, font.fit(f"Adultos livres {bc.free_adults()} (mín. {bc.cfg['min_adults_after_breed']} fora do casal)", 560),
              W - 24, 22, C["dim"], 1, "right")
    for side in ("M", "F"):
        _list(surf, bc, side, ui)
    _breeding_panel(surf, bc, ui)
    _kitten_panel(surf, bc)
    _side_panel(surf, bc, ui)
    Wd.toast(surf, bc.toast, H - 40)


# ------------------------------------------------------------------ novidades
def draw_news(surf: pygame.Surface, nc: NewsController, ui: UIState) -> None:
    Wd.title(surf, "NOVIDADES DO CRIATÓRIO", W // 2, 20, C["warn"], 2, "center")
    y = 70
    if nc.born:
        font.draw(surf, nc.born_title(), 24, y, C["female"], 1)
        y += 22
        for cat in nc.born[:LB.NEWS_ROWS_MAX]:
            _news_row(surf, nc, cat, y, ui)
            y += LB.NEWS_ROW_H
        if len(nc.born) > LB.NEWS_ROWS_MAX:
            font.draw(surf, f"+{len(nc.born) - LB.NEWS_ROWS_MAX} filhote(s) na Coleção", 24, y + 2, C["dim"], 1)
            y += 22
        y += 8
    if nc.grown:
        font.draw(surf, nc.grown_title(), 24, y, C["good"], 1)
        y += 20
        y = Wd.wrap_lines(surf, ", ".join(nc.grown_labels()), 40, y, W - 80, C["text"], 1, 2, 16) + 8
    labels = nc.couple_labels()
    if labels:
        font.draw(surf, "Casal disponível de novo:" if len(labels) == 1 else "Casais disponíveis de novo:",
                  24, y, C["warn"], 1)
        y += 20
        Wd.wrap_lines(surf, "; ".join(labels), 40, y, W - 80, C["text"], 1, 2, 16)
    button(surf, LB.news_button(), "CONTINUAR", ui.mouse)
    Wd.toast(surf, nc.toast, H - 40)


def _news_row(surf: pygame.Surface, nc: NewsController, cat, y: int, ui: UIState) -> None:
    tier = nc.tier(cat)
    r = pygame.Rect(24, y, W - 48, LB.NEWS_ROW_H - 4)
    pygame.draw.rect(surf, mix_c(C["panel"], C["warn"], 0.14) if tier else C["slot"], r, border_radius=6)
    if tier == "perfeito":
        edge = mix_c(C["warn"], WHITE, pulse(ui.t, 5.0))
    elif tier == "alto":
        edge = C["warn"]
    else:
        edge = C["slot_edge"]
    pygame.draw.rect(surf, edge, r, 2, border_radius=6)
    spr = sprites.get("cat", cat.breed, 48)
    if spr is not None:
        surf.blit(spr, spr.get_rect(center=(r.x + 34, r.centery)))
    cy = r.centery - font.CAP_H // 2
    font.draw(surf, font.fit(nc.breed_name(cat), 190), r.x + 72, cy, Wd.breed_color(cat.breed), 1)
    Wd.sex_badge(surf, r.x + 292, r.centery, cat.sex)
    font.draw(surf, SEX_NAME[cat.sex], r.x + 308, cy, sex_color(cat.sex), 1)
    font.draw(surf, font.fit(nc.nature_name(cat), 110), r.x + 400, cy, NATURE_COLOR.get(cat.nature, C["text"]), 1)
    font.draw(surf, "ATK", r.x + 510, cy, C["atk"], 1)
    Wd.stars(surf, r.x + 550, r.centery - 5, cat.iv_atk, 2)
    font.draw(surf, "HP", r.x + 630, cy, C["hp"], 1)
    Wd.stars(surf, r.x + 658, r.centery - 5, cat.iv_hp, 2)
    if tier:
        label = "IV 5/5!" if tier == "perfeito" else "IV ALTO!"
        tag = pygame.Rect(r.right - 108, r.y + 8, 100, r.h - 16)
        pygame.draw.rect(surf, C["warn"], tag, border_radius=4)
        font.draw(surf, label, tag.centerx, tag.centery - font.CAP_H // 2, C["dark"], 1, "center")
