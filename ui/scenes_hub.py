"""Cenas de screenshot/demo do hub. Tudo em memoria (sem tocar em disco)."""
from __future__ import annotations

from random import Random

from core import create_adoption, new_game
from ui import layout_hub as LH
from ui.controller import load_game_content
from ui.hub_controller import HubController
from ui.render import UIState

HUB_SCENES = ("menu", "menu_confirmar", "menu_corrompido", "colecao", "colecao_deck",
              "renomear", "resultado", "adocao", "adocao_vazia", "doar_confirmar")


def make(seed: int, name: str) -> tuple[HubController, UIState]:
    if name not in HUB_SCENES:
        raise SystemExit(f"cena desconhecida: {name} (use: {', '.join(HUB_SCENES)})")
    content = load_game_content()
    hub = HubController(content, None, seed, ai_delay=0.0)
    ui = UIState(t=0.2)
    if name == "menu_corrompido":
        hub.load_error = "JSON invalido: Expecting value: line 1 column 1 (char 0)"
        hub.has_file = True
        return hub, ui
    hub.adopt_save(new_game(content, Random(seed)))
    hub.has_file = True
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
