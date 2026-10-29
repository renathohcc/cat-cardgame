"""Desenho do hub em 960x540 nativo: menu, colecao, adocao, resultado, renomear, doar.

Retangulos e texto, paleta em theme.py, pecas em widgets.py. Sem regra de jogo."""
from __future__ import annotations

import pygame

from ui import font, layout_hub as LH, sprites, widgets as Wd
from ui.adoption_controller import AdoptionController
from ui.collection_controller import CollectionController
from ui.hub_controller import SHORT_RUN_TEXT, HubController
from ui.render import UIState, border, mix_c, pulse, text_fit, tint
from ui.render_run import draw_run_frame
from ui.theme import C, H, NATURE_COLOR, W
from ui.widgets import WHITE, button, panel

STATE_COLOR = {"deck": C["good"], "livre": C["dim"], "filhote": C["female"], "descanso": C["warn"],
               "breed": C["warn"]}
DANGER = (150, 60, 60)
SOFT = (196, 202, 222)               # nome padrao (sem apelido)
SEX_NAME = {"M": "Macho", "F": "Fêmea"}


def sex_color(sex: str):
    return C["male"] if sex == "M" else C["female"]


def sex_line(surf: pygame.Surface, x: int, y: int, sex: str, scale: int = 1) -> int:
    """Selo do sexo + nome por extenso. Devolve o x do fim."""
    Wd.sex_badge(surf, x + 10, y + font.CAP_H * scale // 2, sex)
    w = font.draw(surf, SEX_NAME[sex], x + 26, y, sex_color(sex), scale)
    return x + 26 + w


# ------------------------------------------------------------------ menu
def draw_menu(surf: pygame.Surface, hub: HubController, ui: UIState) -> None:
    Wd.title(surf, "CHAOSCATS", W // 2, 56, C["warn"], 4, "center")
    font.draw(surf, "card game roguelike de gatos", W // 2, 150, C["dim"], 1, "center")
    Wd.leader_art(surf, "heroi", pygame.Rect(96, 236, 160, 160), C["player"])
    Wd.leader_art(surf, "madame-fifi-pelucia", pygame.Rect(W - 256, 236, 160, 160), C["enemy"])
    for i, (key, label, enabled) in enumerate(hub.menu_labels()):
        r = LH.menu_button(i)
        hot_ok = enabled and not hub.confirm_new
        button(surf, r, label, ui.mouse if hot_ok else (-100, -100), enabled, scale=2,
               base=DANGER if key == "quit" else None)
    info = LH.menu_info_rect()
    if hub.load_error:
        Wd.panel(surf, info, C["bad"])
        font.draw(surf, "SAVE CORROMPIDO", info.centerx, info.y + 6, C["bad"], 1, "center")
        font.draw(surf, "Comece um novo jogo para recriar o save.", info.centerx, info.y + 26, C["text"], 1, "center")
        font.draw(surf, font.fit(hub.load_error, info.w - 20), info.centerx, info.y + 46, C["dim"], 1, "center")
    else:
        font.draw(surf, font.fit(hub.save_summary(), info.w - 20), W // 2, info.centery - font.CAP_H // 2,
                  C["dim"], 1, "center")
    if hub.save_path is not None:
        font.draw(surf, font.fit(str(hub.save_path), W - 40), W // 2, H - 28, C["slot_edge"], 1, "center")
    font.draw(surf, "F11: tela cheia", W - 20, 18, C["slot_edge"], 1, "right")
    if hub.confirm_new:
        draw_confirm(surf, ui)
    Wd.toast(surf, hub.toast)


def draw_confirm(surf: pygame.Surface, ui: UIState) -> None:
    p = LH.confirm_panel()
    Wd.modal(surf, p, "SOBRESCREVER O SAVE?")
    font.draw(surf, "Os gatos e o deck atuais", p.centerx, p.y + 72, C["text"], 1, "center")
    font.draw(surf, "serão perdidos.", p.centerx, p.y + 96, C["text"], 1, "center")
    for name, r in LH.confirm_buttons().items():
        yes = name == "confirm_yes"
        button(surf, r, "SIM, NOVO JOGO" if yes else "CANCELAR", ui.mouse,
               base=DANGER if yes else C["card"])


# ------------------------------------------------------------------ colecao
def draw_header(surf: pygame.Surface, col: CollectionController, ui: UIState) -> None:
    Wd.title(surf, "COLEÇÃO", 20, 14, C["text"], 2)
    full = col.can_start
    Wd.title(surf, col.deck_text, 620, 14, C["good"] if full else C["warn"], 2, "right")
    font.draw(surf, f"MOEDAS {col.coins}", W - 24, 20, C["warn"], 1, "right")
    font.draw(surf, "ORDEM", 20, 70, C["dim"], 1)
    for i, key in enumerate(LH.SORT_KEYS):
        r = LH.sort_button(i)
        on = col.sort == key
        pygame.draw.rect(surf, C["button"] if on else (C["card"] if r.collidepoint(ui.mouse) else C["slot"]),
                         r, border_radius=4)
        pygame.draw.rect(surf, WHITE if on else C["panel_edge"], r, 2, border_radius=4)
        font.draw(surf, {"poder": "PODER", "raca": "RAÇA", "nome": "NOME"}[key], r.centerx,
                  r.centery - font.CAP_H // 2, WHITE if on else C["dim"], 1, "center")
    r = LH.filter_button()
    pygame.draw.rect(surf, C["card"] if r.collidepoint(ui.mouse) else C["slot"], r, border_radius=4)
    pygame.draw.rect(surf, C["warn"] if col.filter_breed else C["panel_edge"], r, 2, border_radius=4)
    text_fit(surf, col.filter_label(), r.centerx, r.centery - font.CAP_H // 2, C["warn"] if col.filter_breed else C["dim"],
             r.w - 12, "center")


def draw_column_labels(surf: pygame.Surface) -> None:
    x0, y = LH.LIST_X, 98
    for off, txt in ((LH.COL_NAME, "NOME"), (LH.COL_INFO, "RAÇA"),
                     (LH.COL_IV_ATK, "IV ATK"), (LH.COL_IV_HP, "IV HP"), (LH.COL_STATS, "ATK/HP"),
                     (LH.COL_STATE, "ESTADO")):
        font.draw(surf, txt, x0 + off, y, C["dim"])


def draw_row(surf: pygame.Surface, col: CollectionController, row, i: int, ui: UIState) -> None:
    r = LH.row_rect(i)
    cat, st = row.cat, row.stats
    in_deck = row.state == "deck"
    sel = col.selected == cat.id
    usable = row.state in ("deck", "livre")
    fill = (40, 72, 60) if in_deck else C["slot"]
    if r.collidepoint(ui.mouse) and not col.editing:
        fill = mix_c(fill, WHITE, 0.12)
    pygame.draw.rect(surf, fill, r, border_radius=4)
    pygame.draw.rect(surf, WHITE if sel else (C["good"] if in_deck else C["slot_edge"]), r,
                     2 if sel else 1, border_radius=4)
    cy = r.centery
    box = pygame.Rect(r.x + LH.COL_CHECK, cy - 8, 16, 16)
    pygame.draw.rect(surf, C["dark"], box, border_radius=3)
    pygame.draw.rect(surf, C["good"] if in_deck else C["panel_edge"], box, 2, border_radius=3)
    if in_deck:
        pygame.draw.lines(surf, C["good"], False, [(box.x + 3, cy), (box.x + 7, cy + 4), (box.x + 13, cy - 4)], 3)
    kit = cat.stage == "kitten"
    spr = sprites.get("cat", cat.breed, 24 if kit else 32)
    if spr is not None:
        surf.blit(spr, spr.get_rect(center=(r.x + LH.COL_SPRITE + 16, cy)))
    dim = not usable
    font.draw(surf, font.fit(row.label, LH.NAME_W), r.x + LH.COL_NAME, cy - font.CAP_H // 2,
              C["dim"] if dim else (C["text"] if cat.name else SOFT), 1)
    Wd.sex_badge(surf, r.x + LH.COL_SEX + 8, cy, cat.sex)
    bcol = Wd.breed_color(cat.breed)
    font.draw(surf, font.fit(row.breed, LH.INFO_W), r.x + LH.COL_INFO, cy - 16,
              mix_c(bcol, C["bg"], 0.4) if dim else bcol)
    font.draw(surf, font.fit(col.nature_name(cat), LH.INFO_W), r.x + LH.COL_INFO, cy + 3,
              NATURE_COLOR.get(cat.nature, C["text"]))
    Wd.stars(surf, r.x + LH.COL_IV_ATK, cy - 5, cat.iv_atk, 2)
    Wd.stars(surf, r.x + LH.COL_IV_HP, cy - 5, cat.iv_hp, 2)
    x = r.x + LH.COL_STATS
    font.draw(surf, str(st.atk), x, cy - 16, C["atk"], 1)
    font.draw(surf, str(st.hp), x, cy + 3, C["hp"], 1)
    font.draw(surf, font.fit(col.state_text(row), LH.STATE_W), r.x + LH.COL_STATE, cy - font.CAP_H // 2,
              STATE_COLOR[row.state])


def draw_detail(surf: pygame.Surface, col: CollectionController, ui: UIState,
                d: pygame.Rect | None = None, cat=None, close: bool = False) -> None:
    """Painel de detalhe do gato. `d`/`cat`/`close` servem a ficha do cercado."""
    d = d or LH.detail_panel()
    panel(surf, d)
    cat = cat or col.selected_cat()
    if cat is None:
        font.draw(surf, "Selecione um gato", d.centerx, d.y + 40, C["dim"], 1, "center")
        return
    row = col.row_of(cat)
    x, y = d.x + 12, d.y + 10
    text_fit(surf, row.label, x, y, C["warn"] if cat.name else C["text"], d.w - 24 - (30 if close else 0), "left", top=2)
    y += 28
    art = pygame.Rect(x, y, 96, 96)
    Wd.cat_art(surf, cat.breed, art, kitten=cat.stage == "kitten")
    pygame.draw.rect(surf, Wd.breed_color(cat.breed), art, 2)
    tx, tw = art.right + 10, d.right - 12 - (art.right + 10)
    ty = y
    text_fit(surf, row.breed, tx, ty, Wd.breed_color(cat.breed), tw, "left")
    ty += 18
    Wd.sex_badge(surf, tx + 10, ty + 5, cat.sex)
    font.draw(surf, SEX_NAME[cat.sex], tx + 26, ty, sex_color(cat.sex), 1)
    ty += 18
    text_fit(surf, col.nature_name(cat), tx, ty, NATURE_COLOR.get(cat.nature, C["text"]), tw, "left")
    ty += 16
    Wd.wrap_lines(surf, col.nature_effect(cat), tx, ty, tw, C["dim"], 1, 1, 13)
    ty += 18
    Wd.wrap_lines(surf, col.state_long_text(row), tx, ty, tw, STATE_COLOR[row.state], 1, 2, 13)
    y = art.bottom + 10
    font.draw(surf, "IV ATK", x, y, C["atk"], 1)
    Wd.stars(surf, x + 82, y, cat.iv_atk, 2)
    font.draw(surf, f"{cat.iv_atk}/5", d.right - 12, y, C["dim"], 1, "right")
    y += 18
    font.draw(surf, "IV HP", x, y, C["hp"], 1)
    Wd.stars(surf, x + 82, y, cat.iv_hp, 2)
    font.draw(surf, f"{cat.iv_hp}/5", d.right - 12, y, C["dim"], 1, "right")
    y += 22
    st = row.stats
    cx = x
    for lab, fill, val in (("ATK", C["atk"], st.atk), ("HP", C["hp"], st.hp), ("CUSTO", C["cost"], st.cost)):
        cx = Wd.stat_pill(surf, cx, y, fill, lab, str(val), 82).right + 6
    Wd.keyword_row(surf, x, y + 28, d.right - 12, col.keyword_names(cat), 1)
    quiet = col.editing or col.confirm_donate
    m = (-100, -100) if quiet else ui.mouse
    button(surf, LH.rename_button(d), "RENOMEAR", m)
    button(surf, LH.donate_button(d), f"DOAR +{col.donate_value(cat)}", m, base=(120, 86, 28))


def draw_collection(surf: pygame.Surface, col: CollectionController, ui: UIState) -> None:
    draw_header(surf, col, ui)
    draw_column_labels(surf)
    rows = col.visible_rows()
    for i, row in enumerate(rows):
        draw_row(surf, col, row, i, ui)
    if not rows:
        font.draw(surf, "Nenhum gato com esse filtro.", LH.LIST_X + LH.ROW_W // 2, LH.ROW_Y0 + 40,
                  C["dim"], 1, "center")
    draw_scrollbar(surf, col, ui)
    draw_detail(surf, col, ui)
    m = ui.mouse if not (col.editing or col.confirm_donate) else (-100, -100)
    b = LH.action_buttons()
    button(surf, b["complete"], "COMPLETAR", m)
    button(surf, b["clear"], "LIMPAR", m, base=(110, 50, 60))
    button(surf, b["start"], "INICIAR RUN", m, enabled=col.can_start, scale=2)
    button(surf, b["back"], "VOLTAR (ESC)", m, base=C["card"])
    button(surf, b["breed"], "BREED", m, base=(104, 76, 132))
    text_fit(surf, col.hint(), LH.LIST_X + 4, 500, C["dim"], LH.ROW_W, "left")
    if col.editing:
        draw_rename(surf, col, ui)
    if col.confirm_donate:
        draw_donate_confirm(surf, col, ui)
    Wd.toast(surf, col.toast)


def draw_scrollbar(surf: pygame.Surface, col: CollectionController, ui: UIState) -> None:
    up, dn = LH.scroll_up_rect(), LH.scroll_down_rect()
    Wd.arrow(surf, up, True, col.scroll > 0, ui.mouse)
    Wd.arrow(surf, dn, False, col.scroll < col.max_scroll(), ui.mouse)
    Wd.scrollbar(surf, LH.scroll_track(), len(col.rows()), LH.ROWS_VISIBLE, col.scroll, col.max_scroll())


def draw_rename(surf: pygame.Surface, col: CollectionController, ui: UIState) -> None:
    p = LH.rename_panel()
    cat = col.selected_cat()
    Wd.modal(surf, p, f"RENOMEAR: {col.breed_name(cat)}")
    inp = LH.rename_input()
    pygame.draw.rect(surf, C["dark"], inp, border_radius=4)
    pygame.draw.rect(surf, WHITE, inp, 2, border_radius=4)
    txt = col.edit or ""
    w = font.draw(surf, txt, inp.x + 10, inp.centery - font.CAP_H // 2, C["text"], 1)
    if int(ui.t * 2) % 2 == 0:
        pygame.draw.rect(surf, C["text"], (inp.x + 12 + w, inp.y + 10, 3, inp.h - 20))
    full = len(txt) >= col.name_max
    font.draw(surf, col.edit_counter(), inp.right, inp.bottom + 8, C["warn"] if full else C["dim"], 1, "right")
    font.draw(surf, "Vazio volta ao nome padrão.", inp.x, inp.bottom + 8, C["dim"], 1)
    font.draw(surf, "Enter confirma   ESC cancela", p.centerx, inp.bottom + 34, C["dim"], 1, "center")
    for name, r in LH.rename_buttons().items():
        ok = name == "rename_ok"
        button(surf, r, "CONFIRMAR" if ok else "CANCELAR", ui.mouse, base=None if ok else C["card"])


def draw_donate_confirm(surf: pygame.Surface, col: CollectionController, ui: UIState) -> None:
    p = LH.donate_panel()
    Wd.modal(surf, p, "DOAR GATO?")
    y = Wd.wrap_lines(surf, col.donate_question(), p.x + 24, p.y + 70, p.w - 48, C["text"], 1, 3, 16, "center")
    font.draw(surf, "O gato sai da coleção para sempre.", p.centerx, y + 10, C["dim"], 1, "center")
    for name, r in LH.donate_buttons().items():
        yes = name == "donate_yes"
        button(surf, r, "SIM, DOAR" if yes else "CANCELAR", ui.mouse, base=DANGER if yes else C["card"])


# ------------------------------------------------------------------ adocao
def draw_adoption(surf: pygame.Surface, ad: AdoptionController, ui: UIState) -> None:
    Wd.title(surf, "ADOÇÃO", 24, 16, C["warn"], 2)
    font.draw(surf, f"MOEDAS {ad.coins}", W - 24, 22, C["warn"], 1, "right")
    n = len(ad.cats())
    font.draw(surf, font.fit(f"{ad.summary()}. Adotar ou doar cada gato.", W - 200), 24, 56, C["dim"], 1)
    font.draw(surf, f"Restam {n}", W - 24, 56, C["text"], 1, "right")
    if ad.note:
        font.draw(surf, font.fit(ad.note, 420), W - 24, 38, C["warn"], 1, "right")
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
        font.draw(surf, f"Pág. {ad.page + 1}/{ad.pages}", nav["prev"].right + 16, nav["prev"].centery - font.CAP_H // 2, C["dim"], 1)
    font.draw(surf, "ESC volta ao criatório", W // 2, 20, C["slot_edge"], 1, "center")
    Wd.toast(surf, ad.toast, H - 90)


def draw_hidden_card(surf: pygame.Surface, i: int, ui: UIState) -> None:
    r = LH.adopt_card(i)
    hot = r.collidepoint(ui.mouse)
    pygame.draw.rect(surf, mix_c(C["slot"], WHITE, 0.12) if hot else C["slot"], r, border_radius=8)
    pygame.draw.rect(surf, WHITE if hot else C["panel_edge"], r, 2, border_radius=8)
    font.draw(surf, "?", r.centerx, r.centery - 60, C["slot_edge"], 6, "center")
    font.draw(surf, "CLIQUE PARA", r.centerx, r.bottom - 64, C["dim"], 1, "center")
    font.draw(surf, "REVELAR", r.centerx, r.bottom - 44, C["dim"], 1, "center")


def draw_offer_card(surf: pygame.Surface, ad: AdoptionController, cat, i: int, ui: UIState) -> None:
    r = LH.adopt_card(i)
    tier = ad.tier(cat)
    pygame.draw.rect(surf, mix_c(C["panel"], C["warn"], 0.12) if tier else C["panel"], r, border_radius=8)
    if tier == "perfeito":
        edge = mix_c(C["warn"], WHITE, pulse(ui.t, 5.0))
    elif tier == "alto":
        edge = mix_c(C["warn"], C["panel_edge"], 0.5 * pulse(ui.t, 4.0))
    else:
        edge = C["panel_edge"]
    pygame.draw.rect(surf, edge, r, 3 if tier else 2, border_radius=8)
    x, iw = r.x + 10, r.w - 20
    art = pygame.Rect(x, r.y + 8, iw, 100)
    Wd.cat_art(surf, cat.breed, art)
    if tier:
        label = "IV PERFEITO 5/5!" if tier == "perfeito" else "IV ALTO!"
        strip = pygame.Rect(art.x, art.bottom - 20, art.w, 20)
        pygame.draw.rect(surf, C["warn"], strip)
        font.draw(surf, font.fit(label, strip.w - 8), strip.centerx, strip.centery - font.CAP_H // 2, C["dark"], 1, "center")
    y = art.bottom + 8
    text_fit(surf, ad.breed_name(cat), x, y, Wd.breed_color(cat.breed), iw, "left")
    y += 18
    sex_line(surf, x, y, cat.sex)
    font.draw(surf, font.fit(ad.nature_name(cat), 100), r.right - 10, y,
              NATURE_COLOR.get(cat.nature, C["text"]), 1, "right")
    y += 17
    y = Wd.wrap_lines(surf, ad.nature_effect(cat), x, y, iw, C["dim"], 1, 1, 13) + 2
    st = ad.stats_of(cat)
    for lab, col_, iv in (("ATK", C["atk"], cat.iv_atk), ("HP", C["hp"], cat.iv_hp)):
        font.draw(surf, f"IV {lab}", x, y, col_, 1)
        Wd.stars(surf, x + 82, y, iv, 2)
        y += 17
    y += 4
    cx = x
    for lab, fill, val in (("ATK", C["atk"], st.atk), ("HP", C["hp"], st.hp), ("CUSTO", C["cost"], st.cost)):
        cx = Wd.stat_pill(surf, cx, y, fill, lab, str(val), 62).right + 6
    Wd.keyword_row(surf, x, y + 28, r.right - 8, ad.keyword_names(cat), 1)
    b = LH.adopt_buttons(i)
    button(surf, b["adopt"], "ADOTAR", ui.mouse, base=(46, 120, 80))
    button(surf, b["donate"], f"DOAR +{ad.value_of(cat)}", ui.mouse, base=(120, 86, 28))


# ------------------------------------------------------------------ resultado
def draw_result(surf: pygame.Surface, hub: HubController, ui: UIState) -> None:
    col = C["good"] if hub.result_win else C["bad"]
    Wd.title(surf, "RUN ENCERRADA", W // 2, 40, col, 3, "center")
    if hub.short_run:
        Wd.wrap_lines(surf, SHORT_RUN_TEXT, 120, 100, W - 240, C["warn"], 1, 2, 16, "center")
    p = pygame.Rect(150, 150, W - 300, 200)
    panel(surf, p, col)
    Wd.leader_art(surf, "heroi", pygame.Rect(p.x - 120, p.y + 40, 96, 96), C["player"], 96)
    y = Wd.wrap_lines(surf, hub.result_text, p.x + 20, p.y + 22, p.w - 40, C["text"], 1, 3, 18, "center")
    y += 10
    for line in hub.result_detail:
        y = Wd.wrap_lines(surf, line, p.x + 20, y, p.w - 40, C["dim"], 1, 3, 16, "center") + 4
    button(surf, LH.result_button(), "VOLTAR AO CRIATÓRIO", ui.mouse)
    font.draw(surf, "Enter ou ESC volta", W // 2, LH.result_button().bottom + 16, C["dim"], 1, "center")
    Wd.toast(surf, hub.toast)


# ------------------------------------------------------------------ quadro completo
def draw_hub_frame(surf: pygame.Surface, hub: HubController, ui: UIState) -> None:
    """Quadro 960x540 nativo de qualquer tela do hub (ou da run, que e delegada)."""
    if hub.mode == "run" and hub.rc is not None:
        draw_run_frame(surf, hub.rc, ui)
        return
    Wd.fill_background(surf)
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
    elif hub.mode == "cercado":
        from ui.render_pen import draw_pen
        draw_pen(surf, hub, ui)
    else:
        draw_result(surf, hub, ui)
