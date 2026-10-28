"""Desenho do hub: menu, colecao, resultado (retangulos e texto; paleta em theme.py)."""
from __future__ import annotations

import pygame

from ui import font, layout_hub as LH
from ui.adoption_controller import AdoptionController
from ui.collection_controller import CollectionController
from ui.hub_controller import SHORT_RUN_TEXT, HubController
from ui.render import UIState, border, outlined, pulse, stars, tint
from ui.render_run import draw_run_frame, mix
from ui.theme import BREED_COLOR, C, DEFAULT_BREED_COLOR, H, KEYWORD_COLOR, NATURE_COLOR, W

WHITE = (255, 255, 255)
STATE_COLOR = {"deck": C["good"], "livre": C["dim"], "filhote": C["female"], "descanso": C["warn"],
               "breed": C["warn"]}


def button(surf: pygame.Surface, r: pygame.Rect, label: str, mouse, enabled: bool = True,
           base=None, edge=WHITE) -> None:
    hot = enabled and r.collidepoint(mouse)
    base = base or C["button"]
    fill = mix(base, WHITE, 0.25) if hot else (base if enabled else C["button_off"])
    pygame.draw.rect(surf, fill, r)
    border(surf, r, edge if enabled else C["panel_edge"], 1)
    font.draw(surf, label, r.centerx, r.y + (r.h - font.CAP_H) // 2, WHITE if enabled else C["dim"],
              1, "center")


def panel(surf: pygame.Surface, r: pygame.Rect, edge=None) -> None:
    pygame.draw.rect(surf, C["panel"], r)
    border(surf, r, edge or C["panel_edge"], 1)


# ------------------------------------------------------------------ menu
def draw_menu(surf: pygame.Surface, hub: HubController, ui: UIState) -> None:
    outlined(surf, "GATOS", W // 2, 38, C["warn"], 5, "center")
    font.draw(surf, "card game roguelike", W // 2, 84, C["dim"], 1, "center")
    for i, (key, label, enabled) in enumerate(hub.menu_labels()):
        r = LH.menu_button(i)
        hot_ok = enabled and not hub.confirm_new
        button(surf, r, label, ui.mouse if hot_ok else (-100, -100), enabled,
               base=(150, 60, 60) if key == "quit" else None)
    info = LH.menu_info_rect()
    if hub.load_error:
        panel(surf, info, C["bad"])
        font.draw(surf, "SAVE CORROMPIDO", info.centerx, info.y + 5, C["bad"], 1, "center")
        lines = font.wrap("Comece um novo jogo para recriar o save.", info.w - 12)
        for k, ln in enumerate(lines[:1]):
            font.draw(surf, ln, info.centerx, info.y + 17, C["text"], 1, "center")
        font.draw(surf, font.fit(hub.load_error, info.w - 12), info.centerx, info.y + 29, C["dim"],
                  1, "center")
    else:
        font.draw(surf, hub.save_summary(), W // 2, info.y + 10, C["dim"], 1, "center")
    if hub.save_path is not None:
        font.draw(surf, font.fit(str(hub.save_path), W - 12), W // 2, 256, C["slot_edge"], 1, "center")
    if hub.confirm_new:
        draw_confirm(surf, ui)
    draw_toast(surf, hub)


def draw_confirm(surf: pygame.Surface, ui: UIState) -> None:
    tint(surf, pygame.Rect(0, 0, W, H), (6, 8, 16), 190)
    p = LH.confirm_panel()
    pygame.draw.rect(surf, C["panel"], p)
    border(surf, p, C["warn"], 2)
    font.draw(surf, "SOBRESCREVER O SAVE?", p.centerx, p.y + 10, C["warn"], 1, "center")
    font.draw(surf, "Os gatos e o deck atuais", p.centerx, p.y + 28, C["text"], 1, "center")
    font.draw(surf, "serão perdidos.", p.centerx, p.y + 38, C["text"], 1, "center")
    for name, r in LH.confirm_buttons().items():
        yes = name == "confirm_yes"
        button(surf, r, "SIM, NOVO JOGO" if yes else "CANCELAR", ui.mouse,
               base=(150, 60, 60) if yes else None)


# ------------------------------------------------------------------ colecao
def draw_header(surf: pygame.Surface, col: CollectionController, ui: UIState) -> None:
    outlined(surf, "COLEÇÃO", 4, 3, C["text"], 2, "left")
    full = col.can_start
    outlined(surf, col.deck_text, LH.LIST_X + LH.ROW_W + 16, 6, C["good"] if full else C["warn"], 2, "right")
    font.draw(surf, f"MOEDAS {col.coins}", 476, 8, C["warn"], 1, "right")
    font.draw(surf, "ORDEM", 4, 26, C["dim"])
    for i, key in enumerate(LH.SORT_KEYS):
        r = LH.sort_button(i)
        on = col.sort == key
        pygame.draw.rect(surf, C["button"] if on else (r.collidepoint(ui.mouse) and C["card"] or C["slot"]), r)
        border(surf, r, WHITE if on else C["panel_edge"], 1)
        font.draw(surf, {"poder": "PODER", "raca": "RAÇA", "nome": "NOME"}[key], r.centerx, r.y + 4,
                  WHITE if on else C["dim"], 1, "center")
    r = LH.filter_button()
    pygame.draw.rect(surf, C["card"] if r.collidepoint(ui.mouse) else C["slot"], r)
    border(surf, r, C["warn"] if col.filter_breed else C["panel_edge"], 1)
    font.draw(surf, font.fit(col.filter_label(), r.w - 8), r.centerx, r.y + 4,
              C["warn"] if col.filter_breed else C["dim"], 1, "center")


def draw_column_labels(surf: pygame.Surface) -> None:
    x0, y = LH.LIST_X, 40
    for off, txt in ((LH.COL_NAME, "NOME"), (LH.COL_BREED, "RAÇA"), (LH.COL_SEX, "S"),
                     (LH.COL_NATURE, "NATUR."), (LH.COL_IV_ATK, "IV ATK"), (LH.COL_IV_HP, "IV HP"),
                     (LH.COL_STATS, "A/H"), (LH.COL_STATE, "EST.")):
        font.draw(surf, txt, x0 + off, y, C["slot_edge"])


def draw_row(surf: pygame.Surface, col: CollectionController, row, i: int, ui: UIState) -> None:
    r = LH.row_rect(i)
    cat, st = row.cat, row.stats
    in_deck = row.state == "deck"
    sel = col.selected == cat.id
    usable = row.state in ("deck", "livre")
    fill = (46, 74, 62) if in_deck else C["slot"]
    if r.collidepoint(ui.mouse) and not col.editing:
        fill = mix(fill, WHITE, 0.12)
    pygame.draw.rect(surf, fill, r)
    border(surf, r, WHITE if sel else (C["good"] if in_deck else C["slot_edge"]), 1)
    cy = r.y + 3
    box = pygame.Rect(r.x + LH.COL_CHECK, r.y + 3, 7, 7)
    border(surf, box, C["good"] if in_deck else C["panel_edge"], 1)
    if in_deck:
        pygame.draw.rect(surf, C["good"], box.inflate(-2, -2))
    dim = not usable
    name_col = C["dim"] if (dim or not cat.name) else C["text"]
    font.draw(surf, font.fit(row.label, LH.NAME_W), r.x + LH.COL_NAME, cy, name_col)
    bcol = BREED_COLOR.get(cat.breed, DEFAULT_BREED_COLOR)
    font.draw(surf, font.fit(row.breed, LH.BREED_W), r.x + LH.COL_BREED, cy, mix(bcol, C["bg"], 0.4) if dim else bcol)
    font.draw(surf, cat.sex, r.x + LH.COL_SEX, cy, C["male"] if cat.sex == "M" else C["female"])
    font.draw(surf, font.fit(col.nature_name(cat), LH.NATURE_W), r.x + LH.COL_NATURE, cy,
              NATURE_COLOR.get(cat.nature, C["text"]))
    stars(surf, r.x + LH.COL_IV_ATK, r.y + 4, cat.iv_atk)
    stars(surf, r.x + LH.COL_IV_HP, r.y + 4, cat.iv_hp)
    w = font.draw(surf, str(st.atk), r.x + LH.COL_STATS, cy, C["atk"])
    w2 = font.draw(surf, "/", r.x + LH.COL_STATS + w + 1, cy, C["dim"])
    font.draw(surf, str(st.hp), r.x + LH.COL_STATS + w + w2 + 2, cy, C["hp"])
    font.draw(surf, col.state_text(row), r.x + LH.COL_STATE, cy, STATE_COLOR[row.state])


def draw_scrollbar(surf: pygame.Surface, col: CollectionController, ui: UIState) -> None:
    total = len(col.rows())
    for r, up in ((LH.scroll_up_rect(), True), (LH.scroll_down_rect(), False)):
        pygame.draw.rect(surf, C["card"] if r.collidepoint(ui.mouse) else C["slot"], r)
        border(surf, r, C["panel_edge"], 1)
        cx, cy = r.centerx, r.centery
        pts = [(cx - 3, cy + 2), (cx + 3, cy + 2), (cx, cy - 2)] if up else \
            [(cx - 3, cy - 2), (cx + 3, cy - 2), (cx, cy + 2)]
        pygame.draw.polygon(surf, C["text"], pts)
    tr = LH.scroll_track()
    pygame.draw.rect(surf, C["slot"], tr)
    if total > LH.ROWS_VISIBLE:
        th = max(8, tr.h * LH.ROWS_VISIBLE // total)
        ty = tr.y + (tr.h - th) * col.scroll // max(1, col.max_scroll())
        pygame.draw.rect(surf, C["panel_edge"], (tr.x, ty, tr.w, th))


def chip(surf: pygame.Surface, x: int, y: int, w: int, fill, txt: str, color=WHITE) -> None:
    pygame.draw.rect(surf, fill, (x, y, w, 11))
    font.draw(surf, txt, x + w // 2, y + 2, color, 1, "center")


def draw_detail(surf: pygame.Surface, col: CollectionController, ui: UIState) -> None:
    d = LH.detail_panel()
    panel(surf, d)
    cat = col.selected_cat()
    if cat is None:
        font.draw(surf, "Selecione um gato", d.centerx, d.y + 20, C["dim"], 1, "center")
        return
    row = col.row_of(cat)
    x, y = d.x + 6, d.y + 6
    font.draw(surf, font.fit(row.label, d.w - 12), x, y, C["warn"] if cat.name else C["text"])
    y += 11
    bcol = BREED_COLOR.get(cat.breed, DEFAULT_BREED_COLOR)
    font.draw(surf, font.fit(row.breed, 80), x, y, bcol)
    font.draw(surf, "Macho" if cat.sex == "M" else "Fêmea", d.right - 6, y,
              C["male"] if cat.sex == "M" else C["female"], 1, "right")
    y += 11
    font.draw(surf, col.nature_name(cat), x, y, NATURE_COLOR.get(cat.nature, C["text"]))
    font.draw(surf, col.nature_effect(cat), d.right - 6, y, C["dim"], 1, "right")
    y += 12
    font.draw(surf, "IV ATK", x, y + 1, C["atk"])
    stars(surf, x + 44, y, cat.iv_atk, 7)
    y += 10
    font.draw(surf, "IV HP", x, y + 1, C["hp"])
    stars(surf, x + 44, y, cat.iv_hp, 7)
    y += 13
    st = row.stats
    chip(surf, x, y, 44, C["atk"], f"ATK {st.atk}")
    chip(surf, x + 47, y, 40, C["hp"], f"HP {st.hp}")
    chip(surf, x + 90, y, 52, C["cost"], f"CUSTO {st.cost}")
    y += 14
    cx = x
    for kid, nome in col.keyword_names(cat):
        w = font.width(nome.upper()) + 4
        if cx + w > d.right - 6:
            break
        chip(surf, cx, y, w, KEYWORD_COLOR.get(kid, C["dim"]), nome.upper(), C["dark"])
        cx += w + 2
    y += 14
    font.draw(surf, font.fit(col.state_long_text(row), d.w - 12), x, y, STATE_COLOR[row.state])
    rb = LH.rename_button()
    quiet = col.editing or col.confirm_donate
    button(surf, rb, "RENOMEAR", (-100, -100) if quiet else ui.mouse)
    button(surf, LH.donate_button(), f"DOAR +{col.donate_value(cat)}",
           (-100, -100) if quiet else ui.mouse, base=(110, 80, 30))


def draw_collection(surf: pygame.Surface, col: CollectionController, ui: UIState) -> None:
    draw_header(surf, col, ui)
    draw_column_labels(surf)
    rows = col.visible_rows()
    for i, row in enumerate(rows):
        draw_row(surf, col, row, i, ui)
    if not rows:
        font.draw(surf, "Nenhum gato com esse filtro.", LH.LIST_X + LH.ROW_W // 2, LH.ROW_Y0 + 20,
                  C["dim"], 1, "center")
    draw_scrollbar(surf, col, ui)
    draw_detail(surf, col, ui)
    m = ui.mouse if not col.editing else (-100, -100)
    b = LH.action_buttons()
    button(surf, b["complete"], "COMPLETAR", m)
    button(surf, b["clear"], "LIMPAR", m, base=(96, 44, 52))
    button(surf, b["start"], "INICIAR RUN", m, enabled=col.can_start)
    button(surf, b["back"], "MENU (ESC)", m, base=C["card"])
    button(surf, b["breed"], "CRIATÓRIO", m, base=(96, 70, 120))
    font.draw(surf, font.fit(col.hint(), 318), LH.LIST_X, 252, C["dim"])
    if col.editing:
        draw_rename(surf, col, ui)
    if col.confirm_donate:
        draw_donate_confirm(surf, col, ui)
    draw_toast_obj(surf, col.toast)


def draw_rename(surf: pygame.Surface, col: CollectionController, ui: UIState) -> None:
    tint(surf, pygame.Rect(0, 0, W, H), (6, 8, 16), 190)
    p = LH.rename_panel()
    pygame.draw.rect(surf, C["panel"], p)
    border(surf, p, C["warn"], 2)
    cat = col.selected_cat()
    font.draw(surf, font.fit(f"RENOMEAR: {col.breed_name(cat)}", p.w - 20), p.centerx, p.y + 10,
              C["warn"], 1, "center")
    inp = LH.rename_input()
    pygame.draw.rect(surf, C["dark"], inp)
    border(surf, inp, WHITE, 1)
    txt = col.edit or ""
    w = font.draw(surf, txt, inp.x + 4, inp.y + 6, C["text"])
    if int(ui.t * 2) % 2 == 0:
        pygame.draw.rect(surf, C["text"], (inp.x + 5 + w, inp.y + 4, 1, 10))
    full = len(txt) >= col.name_max
    font.draw(surf, col.edit_counter(), inp.right, inp.bottom + 4, C["warn"] if full else C["dim"], 1, "right")
    font.draw(surf, "Vazio volta ao nome padrão.", inp.x, inp.bottom + 4, C["dim"])
    font.draw(surf, "Enter confirma   ESC cancela", p.centerx, p.y + 76, C["dim"], 1, "center")
    for name, r in LH.rename_buttons().items():
        ok = name == "rename_ok"
        button(surf, r, "CONFIRMAR" if ok else "CANCELAR", ui.mouse, base=None if ok else C["card"])


def draw_donate_confirm(surf: pygame.Surface, col: CollectionController, ui: UIState) -> None:
    tint(surf, pygame.Rect(0, 0, W, H), (6, 8, 16), 190)
    p = LH.donate_panel()
    pygame.draw.rect(surf, C["panel"], p)
    border(surf, p, C["warn"], 2)
    font.draw(surf, "DOAR GATO?", p.centerx, p.y + 10, C["warn"], 1, "center")
    for k, ln in enumerate(font.wrap(col.donate_question(), p.w - 24)[:2]):
        font.draw(surf, ln, p.centerx, p.y + 28 + k * 11, C["text"], 1, "center")
    font.draw(surf, "O gato sai da coleção para sempre.", p.centerx, p.y + 54, C["dim"], 1, "center")
    for name, r in LH.donate_buttons().items():
        yes = name == "donate_yes"
        button(surf, r, "SIM, DOAR" if yes else "CANCELAR", ui.mouse,
               base=(150, 60, 60) if yes else C["card"])


# ------------------------------------------------------------------ adocao
def draw_adoption(surf: pygame.Surface, ad: AdoptionController, ui: UIState) -> None:
    outlined(surf, "ADOÇÃO", 4, 3, C["warn"], 2, "left")
    font.draw(surf, f"MOEDAS {ad.coins}", 476, 8, C["warn"], 1, "right")
    n = len(ad.cats())
    font.draw(surf, f"{ad.summary()}. Adotar ou doar cada gato.", 4, 26, C["dim"])
    font.draw(surf, f"Restam {n}", 476, 26, C["text"], 1, "right")
    if ad.note:
        font.draw(surf, ad.note, 476, 17, C["warn"], 1, "right")
    for i, cat in enumerate(ad.visible()):
        if cat.id in ad.revealed:
            draw_offer_card(surf, ad, cat, i, ui)
        else:
            draw_hidden_card(surf, i, ui)
    nav = LH.adopt_nav()
    button(surf, nav["reveal_all"], "REVELAR TODOS", ui.mouse, enabled=not ad.all_revealed())
    if ad.paged:
        button(surf, nav["prev"], "< ANT", ui.mouse, enabled=ad.page > 0, base=C["card"])
        button(surf, nav["next"], "PRÓX >", ui.mouse, enabled=ad.page < ad.pages - 1, base=C["card"])
        font.draw(surf, f"Pág. {ad.page + 1}/{ad.pages}", 62, 226, C["dim"])
    font.draw(surf, "ESC volta ao menu (a oferta fica guardada)", W // 2, 240, C["slot_edge"], 1, "center")
    draw_toast_obj(surf, ad.toast)


def draw_hidden_card(surf: pygame.Surface, i: int, ui: UIState) -> None:
    r = LH.adopt_card(i)
    hot = r.collidepoint(ui.mouse)
    pygame.draw.rect(surf, mix(C["slot"], WHITE, 0.12) if hot else C["slot"], r)
    border(surf, r, WHITE if hot else C["panel_edge"], 1)
    font.draw(surf, "?", r.centerx, r.centery - 14, C["slot_edge"], 4, "center")
    font.draw(surf, "CLIQUE PARA REVELAR", r.centerx, r.bottom - 14, C["dim"], 1, "center")


def draw_offer_card(surf: pygame.Surface, ad: AdoptionController, cat, i: int, ui: UIState) -> None:
    r = LH.adopt_card(i)
    tier = ad.tier(cat)
    pygame.draw.rect(surf, mix(C["panel"], C["warn"], 0.12) if tier else C["panel"], r)
    if tier == "perfeito":
        edge = mix(C["warn"], WHITE, pulse(ui.t, 5.0))
    elif tier == "alto":
        edge = mix(C["warn"], C["panel_edge"], 0.5 * pulse(ui.t, 4.0))
    else:
        edge = C["panel_edge"]
    border(surf, r, edge, 2 if tier else 1)
    x, y, iw = r.x + 6, r.y + 6, r.w - 12
    bcol = BREED_COLOR.get(cat.breed, DEFAULT_BREED_COLOR)
    font.draw(surf, font.fit(ad.breed_name(cat), iw - 40), x, y, bcol)
    font.draw(surf, "Macho" if cat.sex == "M" else "Fêmea", r.right - 6, y,
              C["male"] if cat.sex == "M" else C["female"], 1, "right")
    y += 11
    font.draw(surf, font.fit(ad.nature_name(cat), iw), x, y, NATURE_COLOR.get(cat.nature, C["text"]))
    y += 10
    font.draw(surf, ad.nature_effect(cat), x, y, C["dim"])
    y += 14
    font.draw(surf, "IV ATK", x, y + 1, C["atk"])
    stars(surf, x + 38, y, cat.iv_atk, 7)
    y += 10
    font.draw(surf, "IV HP", x, y + 1, C["hp"])
    stars(surf, x + 38, y, cat.iv_hp, 7)
    y += 14
    st = ad.stats_of(cat)
    cx = x
    for txt, fill in ((f"ATK {st.atk}", C["atk"]), (f"HP {st.hp}", C["hp"]), (f"C{st.cost}", C["cost"])):
        w = font.width(txt) + 6
        chip(surf, cx, y, w, fill, txt)
        cx += w + 2
    y += 14
    cx = x
    for kid, nome in ad.keyword_names(cat):
        w = font.width(nome.upper()) + 4
        if cx + w > r.right - 6:
            break
        chip(surf, cx, y, w, KEYWORD_COLOR.get(kid, C["dim"]), nome.upper(), C["dark"])
        cx += w + 2
    y += 15
    if tier:
        label = "IV PERFEITO 5/5!" if tier == "perfeito" else "IV ALTO!"
        pygame.draw.rect(surf, C["warn"], (x, y, iw, 11))
        font.draw(surf, label, r.centerx, y + 2, C["dark"], 1, "center")
    b = LH.adopt_buttons(i)
    button(surf, b["adopt"], "ADOTAR", ui.mouse, base=(46, 120, 80))
    button(surf, b["donate"], f"DOAR +{ad.value_of(cat)}", ui.mouse, base=(110, 80, 30))


# ------------------------------------------------------------------ resultado
def draw_result(surf: pygame.Surface, hub: HubController, ui: UIState) -> None:
    col = C["good"] if hub.result_win else C["bad"]
    outlined(surf, "RUN ENCERRADA", W // 2, 36, col, 3, "center")
    if hub.short_run:
        font.draw(surf, SHORT_RUN_TEXT, W // 2, 66, C["warn"], 1, "center")
    p = pygame.Rect(40, 84, W - 80, 100)
    panel(surf, p)
    for k, ln in enumerate(font.wrap(hub.result_text, p.w - 16)):
        font.draw(surf, ln, p.centerx, p.y + 12 + k * 11, C["text"], 1, "center")
    y = p.y + 40
    for line in hub.result_detail:
        for ln in font.wrap(line, p.w - 16)[:4]:
            font.draw(surf, ln, p.centerx, y, C["dim"], 1, "center")
            y += 10
    button(surf, LH.result_button(), "VOLTAR À COLEÇÃO", ui.mouse)
    font.draw(surf, "Enter ou ESC volta", W // 2, 246, C["dim"], 1, "center")
    draw_toast(surf, hub)


# ------------------------------------------------------------------ avisos
def draw_toast_obj(surf: pygame.Surface, t) -> None:
    if t is None:
        return
    fill, col = {"error": ((100, 36, 40), (255, 190, 190)), "warn": ((110, 84, 20), (255, 230, 150)),
                 "info": ((36, 64, 100), (200, 225, 255))}[t.kind]
    m = pygame.Rect(60, 246, W - 120, 18)
    pygame.draw.rect(surf, fill, m)
    border(surf, m, col, 1)
    font.draw(surf, font.fit(t.text, m.w - 10), m.centerx, m.y + 6, col, 1, "center")


def draw_toast(surf: pygame.Surface, hub: HubController) -> None:
    draw_toast_obj(surf, hub.toast)


# ------------------------------------------------------------------ quadro completo
def draw_hub_frame(surf: pygame.Surface, hub: HubController, ui: UIState) -> None:
    if hub.mode == "run" and hub.rc is not None:
        draw_run_frame(surf, hub.rc, ui)
        return
    surf.fill(C["bg"])
    if hub.mode == "menu":
        draw_menu(surf, hub, ui)
    elif hub.mode == "colecao":
        draw_collection(surf, hub.col, ui)
    elif hub.mode == "adocao":
        draw_adoption(surf, hub.adopt, ui)
    elif hub.mode == "criatorio":
        from ui.render_breed import draw_breed
        draw_breed(surf, hub.breed, ui)
    elif hub.mode == "novidades":
        from ui.render_breed import draw_news
        draw_news(surf, hub.news, ui)
    else:
        draw_result(surf, hub, ui)
