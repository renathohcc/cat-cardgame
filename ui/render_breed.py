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


def _couple_boxes(surf: pygame.Surface, bc: BreedController, p: pygame.Rect) -> None:
    x, w = p.x + 12, p.w - 24
    font.draw(surf, "CASAL", x, p.y + 10, C["warn"], 1)
    font.draw(surf, f"{bc.couples_text()}  {bc.slots_text}", p.right - 12, p.y + 10, C["dim"], 1, "right")
    colw = (w - 8) // 2
    for k, side in enumerate(("M", "F")):
        cat = bc.selected(side)
        cx = x + k * (colw + 8)
        box = pygame.Rect(cx, p.y + 30, colw, 112)
        pygame.draw.rect(surf, C["slot"], box, border_radius=4)
        pygame.draw.rect(surf, sex_color(side), box, 1, border_radius=4)
        Wd.sex_badge(surf, box.x + 12, box.y + 12, side)
        if cat is None:
            font.draw(surf, "escolha", box.centerx, box.y + 50, C["dim"], 1, "center")
            continue
        Wd.cat_art(surf, cat.breed, pygame.Rect(box.centerx - 32, box.y + 4, 64, 64), bg=C["slot"])
        text_fit(surf, bc.label(cat), box.centerx, box.y + 72, C["text"], box.w - 8, "center")
        font.draw(surf, font.fit(bc.breed_name(cat), box.w - 8), box.centerx, box.y + 90, Wd.breed_color(cat.breed), 1, "center")


def _ration_chips(surf: pygame.Surface, bc: BreedController, p: pygame.Rect, ui: UIState) -> None:
    font.draw(surf, Wd.RATION_RULE.upper(), p.x + 12, p.y + 150, C["dim"], 1)
    for i, (rid, label, stock) in enumerate(bc.ration_options()):
        r = LB.ration_chip(i)
        on = bc.ration == rid
        usable = rid is None or stock > 0
        txt = label if rid is None else f"{label} x{stock}"
        button(surf, r, txt, ui.mouse, enabled=usable, base=(46, 120, 80) if on else C["card"],
               edge=WHITE if on else C["panel_edge"])
    if bc.needs_choice and bc.pair() is not None:
        font.draw(surf, "FIXAR QUAL IV?", p.x + 12, p.y + 226, C["dim"], 1)
        for i, (stat, parent) in enumerate(LB.CHOICES):
            on = bc.choice == (stat, parent)
            txt = f"{stat.upper()} DO PAI" if parent == "father" else f"{stat.upper()} DA MÃE"
            button(surf, LB.choice_chip(i), txt, ui.mouse, base=(46, 120, 80) if on else C["card"],
                   edge=WHITE if on else C["panel_edge"])


def _side_panel(surf: pygame.Surface, bc: BreedController, ui: UIState) -> None:
    p = LB.side_panel()
    panel(surf, p)
    _couple_boxes(surf, bc, p)
    _ration_chips(surf, bc, p, ui)
    ok, motivo = bc.verdict()
    vr = LB.verdict_rect(bc.needs_choice and bc.pair() is not None)
    if not ok:
        Wd.wrap_lines(surf, motivo, vr.x, vr.y, vr.w, C["warn"] if bc.pair() else C["dim"], 1,
                      max(1, vr.h // 14), 14)
    else:
        font.draw(surf, "Casal válido.", vr.x, vr.y, C["good"], 1)
        if bc.basket:
            Wd.wrap_lines(surf, "Filhotes vão para a cesta até abrir o cercadinho.", vr.x, vr.y + 16, vr.w,
                          C["dim"], 1, 2, 14)
    b = LB.action_buttons()
    button(surf, b["start"], "INICIAR BREED", ui.mouse, enabled=ok, base=(46, 120, 80))
    button(surf, b["back"], "VOLTAR (ESC)", ui.mouse, base=C["card"])


def _pct(p: float) -> int:
    return round(p * 100)


def _iv_chart(surf: pygame.Surface, x: int, y: int, label: str, color, dist: dict[int, float], fixed) -> None:
    font.draw(surf, label, x + 12, y + 9, color, 1)
    top = max(dist.values()) if dist else 1.0
    for k, iv in enumerate(sorted(dist)):
        cx = x + 58 + k * 44
        h = max(2, round(18 * dist[iv] / top)) if dist[iv] > 0 else 0
        pygame.draw.rect(surf, C["slot"], (cx, y, 34, 18))
        if h:
            pygame.draw.rect(surf, color if dist[iv] == top else mix_c(color, C["slot"], 0.45), (cx, y + 18 - h, 34, h))
        font.draw(surf, str(iv), cx + 17, y + 4, WHITE if dist[iv] else C["slot_edge"], 1, "center")
        font.draw(surf, f"{_pct(dist[iv])}%", cx + 17, y + 19, C["text"] if dist[iv] else C["slot_edge"], 1, "center")


def _odds_panel(surf: pygame.Surface, bc: BreedController, od) -> None:
    """Previa de chances (core: breed_odds): raca, cada IV, ninhada, efeito da racao e tempo."""
    p = LB.odds_panel()
    panel(surf, p)
    x, w = p.x + 12, p.w - 24
    font.draw(surf, "PRÉVIA DE CHANCES", x, p.y + 8, C["warn"], 1)
    items = sorted(od.breed.items(), key=lambda kv: -kv[1])
    bar = pygame.Rect(x, p.y + 24, w, 10)
    cx = bar.x
    for k, (bid, pr) in enumerate(items):
        seg = bar.w - (cx - bar.x) if k == len(items) - 1 else round(bar.w * pr)
        pygame.draw.rect(surf, Wd.breed_color(bid), (cx, bar.y, seg, bar.h))
        cx += seg
    pygame.draw.rect(surf, C["panel_edge"], bar, 1)
    for k, (bid, pr) in enumerate(items[:2]):
        txt = font.fit(f"{_pct(pr)}% {bc.breed_name_of(bid)}", w // 2 - 4)
        font.draw(surf, txt, x if k == 0 else p.right - 12, p.y + 37, Wd.breed_color(bid), 1, "left" if k == 0 else "right")
    _iv_chart(surf, p.x, p.y + 60, "ATK", C["atk"], od.iv_atk, od.fixed.get("atk"))
    _iv_chart(surf, p.x, p.y + 100, "HP", C["hp"], od.iv_hp, od.fixed.get("hp"))
    y = p.y + 142
    avg = f"{od.litter_expected:.1f}".replace(".", ",")
    lines = [(f"Ninhada: {od.litter_min} a {od.litter_max} (média {avg})", C["text"]),
             (f"Mutação por IV: {_pct(od.mutation)}%", C["good"] if bc.ration and od.mutation > 0.1 else C["text"]),
             (f"Tempo: {od.runs} run{'s' if od.runs != 1 else ''}"
              + (f" (sem ração: {od.runs_without_ration})" if od.runs != od.runs_without_ration else ""),
              C["good"] if od.runs != od.runs_without_ration else C["text"])]
    fx = [f"{k.upper()} fixado em {v}" for k, v in od.fixed.items() if v is not None]
    if fx:
        lines.append((" · ".join(fx) + ", ninhada toda", C["good"]))
    elif bc.basket:
        lines.append(("Filhotes vão para a cesta.", C["dim"]))
    for ln, colr in lines[:4]:
        font.draw(surf, font.fit(ln, w), x, y, colr, 1)
        y += 14


def draw_breed(surf: pygame.Surface, bc: BreedController, ui: UIState) -> None:
    Wd.title(surf, "BREED", 22, 14, C["text"], 2)
    font.draw(surf, font.fit(f"Adultos livres {bc.free_adults()} (mín. {bc.cfg['min_adults_after_breed']} fora do casal)", 560),
              W - 24, 22, C["dim"], 1, "right")
    for side in ("M", "F"):
        _list(surf, bc, side, ui)
    _breeding_panel(surf, bc, ui)
    od = bc.odds()
    if od is not None:
        _odds_panel(surf, bc, od)
    else:
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
