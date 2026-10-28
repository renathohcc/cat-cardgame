"""Desenho do Criatorio e das Novidades do Criatorio (retangulos e texto)."""
from __future__ import annotations

import pygame

from ui import font, layout_breed as LB
from ui.breed_controller import BreedController, BreedRow, NewsController
from ui.render import UIState, border, outlined, pulse, stars
from ui.render_hub import WHITE, button, draw_toast_obj, panel
from ui.render_run import mix
from ui.theme import BREED_COLOR, C, DEFAULT_BREED_COLOR, NATURE_COLOR, W

SIDE_NAME = {"M": "MACHOS", "F": "FÊMEAS"}


def _arrow(surf: pygame.Surface, r: pygame.Rect, up: bool, on: bool, mouse) -> None:
    pygame.draw.rect(surf, C["card"] if (on and r.collidepoint(mouse)) else C["slot"], r)
    border(surf, r, C["panel_edge"], 1)
    cx, cy = r.centerx, r.centery
    pts = [(cx - 3, cy + 2), (cx + 3, cy + 2), (cx, cy - 2)] if up else \
        [(cx - 3, cy - 2), (cx + 3, cy - 2), (cx, cy + 2)]
    pygame.draw.polygon(surf, C["text"] if on else C["panel_edge"], pts)


def _row(surf: pygame.Surface, bc: BreedController, row: BreedRow, side: str, i: int, ui: UIState) -> None:
    r = LB.row_rect(side, i)
    cat, st = row.cat, row.stats
    sel = bc.sel[side] == cat.id
    fill = (46, 62, 90) if sel else C["slot"]
    if r.collidepoint(ui.mouse):
        fill = mix(fill, WHITE, 0.12)
    pygame.draw.rect(surf, fill, r)
    border(surf, r, WHITE if sel else C["slot_edge"], 1)
    cy = r.y + 3
    font.draw(surf, font.fit(row.label, LB.NAME_W), r.x + LB.COL_NAME, cy,
              BREED_COLOR.get(cat.breed, DEFAULT_BREED_COLOR))
    font.draw(surf, font.fit(bc.nature_name(cat), LB.NAT_W), r.x + LB.COL_NAT, cy,
              NATURE_COLOR.get(cat.nature, C["text"]))
    stars(surf, r.x + LB.COL_IV_ATK, r.y + 3, cat.iv_atk)
    stars(surf, r.x + LB.COL_IV_HP, r.y + 3, cat.iv_hp)
    w = font.draw(surf, str(st.atk), r.x + LB.COL_STATS, cy, C["atk"])
    w2 = font.draw(surf, "/", r.x + LB.COL_STATS + w + 1, cy, C["dim"])
    font.draw(surf, str(st.hp), r.x + LB.COL_STATS + w + w2 + 2, cy, C["hp"])


def _list(surf: pygame.Surface, bc: BreedController, side: str, ui: UIState) -> None:
    h = LB.list_header(side)
    total = len(bc.rows(side))
    font.draw(surf, f"{SIDE_NAME[side]} ({total})", h.x, h.y + 3,
              C["male"] if side == "M" else C["female"])
    ms = bc.max_scroll(side)
    _arrow(surf, LB.scroll_button(side, -1), True, bc.scroll[side] > 0, ui.mouse)
    _arrow(surf, LB.scroll_button(side, 1), False, bc.scroll[side] < ms, ui.mouse)
    rows = bc.visible_rows(side)
    for i, row in enumerate(rows):
        _row(surf, bc, row, side, i, ui)
    if not rows:
        font.draw(surf, "Nenhum disponível.", LB.LIST_X[side] + LB.LIST_W // 2, LB.LIST_Y0 + 20,
                  C["dim"], 1, "center")


def _breeding_panel(surf: pygame.Surface, bc: BreedController, ui: UIState) -> None:
    p = LB.breed_panel()
    panel(surf, p)
    couples = bc.couples()
    font.draw(surf, f"EM BREED ({len(couples)})", p.x + 4, p.y + 3, C["warn"])
    if not couples:
        font.draw(surf, "Nenhum casal.", p.centerx, p.y + 40, C["dim"], 1, "center")
    for i, cp in enumerate(couples[:LB.COUPLES_VISIBLE]):
        r = LB.couple_rect(i)
        pygame.draw.rect(surf, C["slot"], r)
        border(surf, r, C["slot_edge"], 1)
        names = f"{bc.label(cp.male)} + {bc.label(cp.female)}"
        font.draw(surf, font.fit(names, r.w - 6), r.x + 3, r.y + 2, C["text"])
        n = cp.runs_left
        font.draw(surf, f"faltam {n} run{'s' if n != 1 else ''}", r.x + 3, r.y + 13, C["good"])
        button(surf, LB.cancel_button(i), "CANCELAR", ui.mouse, enabled=cp.can_cancel,
               base=(110, 44, 52))
    if len(couples) > LB.COUPLES_VISIBLE:
        font.draw(surf, f"+{len(couples) - LB.COUPLES_VISIBLE} casal(is)", p.right - 4, p.y + 3,
                  C["dim"], 1, "right")


def _kitten_panel(surf: pygame.Surface, bc: BreedController) -> None:
    p = LB.kitten_panel()
    panel(surf, p)
    ks = bc.kittens()
    font.draw(surf, f"FILHOTES ({len(ks)})", p.x + 4, p.y + 3, C["female"])
    if not ks:
        font.draw(surf, "Nenhum filhote.", p.centerx, p.y + 40, C["dim"], 1, "center")
    for i, (cat, left) in enumerate(ks[:LB.KITTENS_VISIBLE]):
        y = p.y + 14 + i * 11
        font.draw(surf, font.fit(bc.label(cat), 62), p.x + 4, y, BREED_COLOR.get(cat.breed, DEFAULT_BREED_COLOR))
        font.draw(surf, cat.sex, p.x + 68, y, C["male"] if cat.sex == "M" else C["female"])
        stars(surf, p.x + 78, y, cat.iv_atk, 4)
        stars(surf, p.x + 102, y, cat.iv_hp, 4)
        font.draw(surf, f"{left} run{'s' if left != 1 else ''}", p.right - 4, y, C["good"], 1, "right")
    if len(ks) > LB.KITTENS_VISIBLE:
        font.draw(surf, f"+{len(ks) - LB.KITTENS_VISIBLE}", p.right - 4, p.y + 3, C["dim"], 1, "right")


def _side_panel(surf: pygame.Surface, bc: BreedController, ui: UIState) -> None:
    p = LB.side_panel()
    panel(surf, p)
    x, y, w = p.x + 5, p.y + 4, p.w - 10
    font.draw(surf, "CASAL", x, y, C["warn"])
    y += 11
    for side, tag in (("M", "M"), ("F", "F")):
        cat = bc.selected(side)
        col = C["male"] if side == "M" else C["female"]
        font.draw(surf, tag, x, y, col)
        font.draw(surf, font.fit(bc.label(cat), w - 10) if cat else "-", x + 9, y,
                  C["text"] if cat else C["dim"])
        y += 10
    y += 4
    odds = bc.breed_odds()
    if odds:
        for ln in font.wrap("Provável raça do filhote:", w):
            font.draw(surf, ln, x, y, C["dim"])
            y += 10
        for pct, name in odds:
            font.draw(surf, font.fit(f"{pct}% {name}", w), x, y, C["text"])
            y += 10
    else:
        for ln in font.wrap("Raça do filhote: escolha o casal.", w):
            font.draw(surf, ln, x, y, C["dim"])
            y += 10
    y += 4
    font.draw(surf, bc.litter_text(), x, y, C["text"])
    y += 10
    font.draw(surf, bc.time_text(), x, y, C["text"])
    y += 14
    ok, motivo = bc.verdict()
    if not ok:
        for ln in font.wrap(motivo, w)[:5]:
            font.draw(surf, ln, x, y, C["warn"] if bc.pair() else C["dim"])
            y += 10
    else:
        font.draw(surf, "Casal válido.", x, y, C["good"])
    b = LB.action_buttons()
    button(surf, b["start"], "INICIAR BREED", ui.mouse, enabled=ok, base=(46, 120, 80))
    button(surf, b["back"], "VOLTAR (ESC)", ui.mouse, base=C["card"])


def draw_breed(surf: pygame.Surface, bc: BreedController, ui: UIState) -> None:
    outlined(surf, "CRIATÓRIO", 4, 3, C["text"], 2, "left")
    font.draw(surf, f"Adultos livres {bc.free_adults()}  (mín. {bc.cfg['min_adults_after_breed']} fora do casal)",
              476, 8, C["dim"], 1, "right")
    for side in ("M", "F"):
        _list(surf, bc, side, ui)
    _breeding_panel(surf, bc, ui)
    _kitten_panel(surf, bc)
    _side_panel(surf, bc, ui)
    draw_toast_obj(surf, bc.toast)


# ------------------------------------------------------------------ novidades
def draw_news(surf: pygame.Surface, nc: NewsController, ui: UIState) -> None:
    outlined(surf, "NOVIDADES DO CRIATÓRIO", W // 2, 6, C["warn"], 2, "center")
    y = 28
    if nc.born:
        font.draw(surf, nc.born_title(), 8, y, C["female"])
        y += 11
        for i, cat in enumerate(nc.born[:LB.NEWS_ROWS_MAX]):
            _news_row(surf, nc, cat, y, ui)
            y += LB.NEWS_ROW_H
        if len(nc.born) > LB.NEWS_ROWS_MAX:
            font.draw(surf, f"+{len(nc.born) - LB.NEWS_ROWS_MAX} filhote(s) na Coleção", 8, y, C["dim"])
            y += 10
        y += 4
    if nc.grown:
        font.draw(surf, nc.grown_title(), 8, y, C["good"])
        y += 11
        for ln in font.wrap(", ".join(nc.grown_labels()), W - 24)[:3]:
            font.draw(surf, ln, 12, y, C["text"])
            y += 10
        y += 4
    labels = nc.couple_labels()
    if labels:
        font.draw(surf, "Casal disponível de novo:" if len(labels) == 1 else "Casais disponíveis de novo:",
                  8, y, C["warn"])
        y += 11
        for ln in font.wrap("; ".join(labels), W - 24)[:3]:
            font.draw(surf, ln, 12, y, C["text"])
            y += 10
    button(surf, LB.news_button(), "CONTINUAR", ui.mouse)
    draw_toast_obj(surf, nc.toast)


def _news_row(surf: pygame.Surface, nc: NewsController, cat, y: int, ui: UIState) -> None:
    tier = nc.tier(cat)
    r = pygame.Rect(8, y, W - 16, LB.NEWS_ROW_H - 1)
    pygame.draw.rect(surf, mix(C["panel"], C["warn"], 0.14) if tier else C["slot"], r)
    if tier == "perfeito":
        edge = mix(C["warn"], WHITE, pulse(ui.t, 5.0))
    elif tier == "alto":
        edge = C["warn"]
    else:
        edge = C["slot_edge"]
    border(surf, r, edge, 1)
    cy = r.y + 3
    font.draw(surf, font.fit(nc.breed_name(cat), 90), r.x + 5, cy, BREED_COLOR.get(cat.breed, DEFAULT_BREED_COLOR))
    font.draw(surf, "Macho" if cat.sex == "M" else "Fêmea", r.x + 100, cy,
              C["male"] if cat.sex == "M" else C["female"])
    font.draw(surf, font.fit(nc.nature_name(cat), 50), r.x + 140, cy, NATURE_COLOR.get(cat.nature, C["text"]))
    font.draw(surf, "ATK", r.x + 198, cy, C["atk"])
    stars(surf, r.x + 220, r.y + 3, cat.iv_atk)
    font.draw(surf, "HP", r.x + 258, cy, C["hp"])
    stars(surf, r.x + 272, r.y + 3, cat.iv_hp)
    if tier:
        label = "IV 5/5!" if tier == "perfeito" else "IV ALTO!"
        pygame.draw.rect(surf, C["warn"], (r.right - 62, r.y + 1, 60, r.h - 2))
        font.draw(surf, label, r.right - 32, cy, C["dark"], 1, "center")
