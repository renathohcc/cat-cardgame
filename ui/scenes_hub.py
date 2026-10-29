"""Cenas de screenshot/demo do hub. Tudo em memoria (sem tocar em disco)."""
from __future__ import annotations

from dataclasses import replace
from random import Random

from core import RunAftermath, available_cats, create_adoption, new_game
from core.save import format_cat_id
from ui import layout_breed as LB, layout_hub as LH, layout_pen as LP
from ui.breed_controller import NewsController
from ui.controller import load_game_content
from ui.daycycle import fixed_clock
from ui.hub_controller import HubController
from ui.render import UIState

HUB_SCENES = ("menu", "menu_confirmar", "menu_corrompido", "colecao", "colecao_deck",
              "renomear", "resultado", "adocao", "adocao_vazia", "doar_confirmar")
BREED_SCENES = ("criatorio", "criatorio_casal", "criatorio_recusado", "novidades")
PEN_SCENES = ("criatorio_hub", "criatorio_hub_ficha", "criatorio_hub_adocao")
ALL_SCENES = HUB_SCENES + BREED_SCENES + PEN_SCENES
PEN_SIM_SECONDS = 25.0          # tempo simulado antes do screenshot (deterministico por seed)


def _big_save(hub: HubController) -> tuple[list, list]:
    """Save com 18 adultos (sobra para o breed), dois casais em breed e 2 filhotes (20 gatos...)."""
    content, save = hub.content, hub.save
    base = list(save.cats)
    for k in range(6):
        c = replace(base[k], id=format_cat_id(save.next_cat_id), name=None,
                    sex="M" if k % 2 == 0 else "F", rest_runs_left=0)
        save.next_cat_id += 1
        save.cats.append(c)
    adults = [c for c in save.cats if c.stage == "adult"]
    males = [c for c in adults if c.sex == "M"]
    females = [c for c in adults if c.sex == "F"]
    males[0].name, females[0].name = "Mingau", "Pipoca"
    save.breeding = [{"male": males[1].id, "female": females[1].id, "runs_left": 2},
                     {"male": males[2].id, "female": females[2].id, "runs_left": 1}]
    save.deck = []
    for i in range(4):
        k = replace(base[i], id=format_cat_id(save.next_cat_id), name=None, stage="kitten",
                    runs_as_kitten=i % 3, iv_atk=5 - i, iv_hp=4)
        save.next_cat_id += 1
        save.cats.append(k)
    return males, females


def _breed_scene(hub: HubController, ui: UIState, name: str, seed: int) -> None:
    content, save = hub.content, hub.save
    males, females = _big_save(hub)
    base = list(save.cats)
    if name == "novidades":
        born = [replace(base[0], id=format_cat_id(save.next_cat_id + i), name=None, stage="kitten",
                        sex="MF"[i % 2], iv_atk=a, iv_hp=h)
                for i, (a, h) in enumerate(((5, 5), (4, 4), (2, 3)))]
        save.next_cat_id += 3
        save.cats.extend(born)
        grown = [c for c in save.cats if c.stage == "kitten"][:2]
        hub.news = NewsController(content, save, RunAftermath(
            born=born, grown=grown, couples_done=[(males[2].id, females[2].id)]))
        hub.mode = "novidades"
        ui.mouse = LB.news_button().center
        return
    hub.open_breed()
    bc = hub.breed
    if name == "criatorio_casal":
        bc.sel = {"M": males[0].id, "F": females[0].id}
        ui.mouse = LB.action_buttons()["start"].center
    elif name == "criatorio_recusado":
        keep = {males[0].id, females[0].id}
        extra = [c for c in available_cats(save) if c.id not in keep]
        drop = {c.id for c in extra[11 - 0:]}      # sobram 13 livres: o core recusa
        save.cats[:] = [c for c in save.cats if c.id not in drop]
        bc.sel = {"M": males[0].id, "F": females[0].id}
        ui.mouse = LB.action_buttons()["start"].center
    else:
        ui.mouse = LB.row_rect("M", 1).center


def _pen_scene(hub: HubController, ui: UIState, name: str, seed: int) -> None:
    """Cercado cheio (16 gatos em cena, de 20 na colecao), tempo simulado por seed."""
    _big_save(hub)
    hub.col.refresh_deck()
    hub.col.complete()
    hub.col.toast = None
    hub.save.cats[3].name = "Mingau"
    hub.save.coins = 12
    if name == "criatorio_hub_adocao":
        create_adoption(hub.content, hub.save, Random(seed), "vitoria", 6)
    hub.enter_pen()
    hub.pen.advance(PEN_SIM_SECONDS)
    ui.mouse = (-100, -100)
    if name == "criatorio_hub_ficha":
        c = hub.pen.cats[0]
        hub.open_ficha(c.cat_id)
        hub.pen.advance(0.3)
        ui.mouse = LP.ficha_close(hub.ficha_rect()).center
    elif name == "criatorio_hub_adocao":
        ui.mouse = LP.button_rect("adocao").center


def make(seed: int, name: str, hora: str | None = None) -> tuple[HubController, UIState]:
    """`hora` ("HH:MM") fixa o relogio do cercado; padrao 12:00 (deterministico)."""
    if name not in ALL_SCENES:
        raise SystemExit(f"cena desconhecida: {name} (use: {', '.join(ALL_SCENES)})")
    content = load_game_content()
    hub = HubController(content, None, seed, ai_delay=0.0, clock=fixed_clock(hora or "12:00"))
    ui = UIState(t=0.2)
    if name == "menu_corrompido":
        hub.load_error = "JSON invalido: Expecting value: line 1 column 1 (char 0)"
        hub.has_file = True
        return hub, ui
    hub.adopt_save(new_game(content, Random(seed)))
    hub.has_file = True
    if name in PEN_SCENES:
        _pen_scene(hub, ui, name, seed)
        return hub, ui
    if name in BREED_SCENES:
        _breed_scene(hub, ui, name, seed)
        return hub, ui
    if name == "menu":
        ui.mouse = LH.menu_button(0).center
    elif name == "menu_confirmar":
        hub.confirm_new = True
        ui.mouse = LH.confirm_buttons()["confirm_yes"].center
    elif name == "adocao":
        create_adoption(content, hub.save, Random(seed), "vitoria", 6)
        cats = hub.save.pending_adoption["cats"]
        cats[0].iv_atk = cats[0].iv_hp = 5
        cats[1].iv_atk, cats[1].iv_hp = 4, 4
        cats[2].iv_atk, cats[2].iv_hp = 2, 1
        hub.save.coins = 12
        hub.open_pending_adoption()
        hub.adopt.revealed.update(c.id for c in cats[:3])
        ui.mouse = LH.adopt_buttons(2)["donate"].center
    elif name == "adocao_vazia":
        hub.mode = "resultado"
        hub.result_text = "Run encerrada: derrota, nós vencidos 1"
        hub.result_detail = ["Você foi derrotado.", "Nenhum gato para adotar desta vez"]
    elif name == "doar_confirmar":
        hub.mode = "colecao"
        hub.save.coins = 12
        hub.col.selected = hub.col.rows()[2].cat.id
        hub.col.confirm_donate = True
        ui.mouse = LH.donate_buttons()["donate_yes"].center
    elif name == "resultado":
        hub.mode = "resultado"
        hub.result_text = "Run encerrada: derrota, nós vencidos 2"
        hub.result_detail = ["Você foi derrotado."]
    else:
        hub.mode = "colecao"
        col = hub.col
        if name in ("colecao_deck", "renomear"):
            cats = col.save.cats
            cats[2].name = "Mingau"
            cats[5].name = "Sr. Bigodes"
            cats[8].stage = "kitten"
            cats[9].rest_runs_left = 2
            col.picked = []
            for r in col.rows()[:7]:
                if r.state in ("livre", "deck"):
                    col.picked.append(r.cat.id)
            col.sort = "poder"
            col.selected = col.rows()[1].cat.id
            ui.mouse = LH.row_rect(3).center
        if name == "renomear":
            col.begin_rename()
            col.type_text("Pelúcia Çã")
    return hub, ui
