"""Cenas de screenshot/demo da economia do hub (T13.4). Tudo em memoria (sem tocar em disco).

Cada cena monta um save so com a API do core e abre a tela pelo controlador do hub.
"""
from __future__ import annotations

from dataclasses import replace
from random import Random

from core import RunSettlement, create_adoption
from core.save import format_cat_id
from ui import layout_adopt as LA, layout_breed as LB, layout_pen as LP, layout_shop as LS
from ui.hub_controller import HubController, RunSummary
from ui.render import UIState

AREAS = ("cercado-adultos-ampliado", "cercadinho-filhotes", "patio-casais-ampliado", "jardim-lagoa",
         "patio-casais-nobre", "pomar")
QUINTAL = ("quintal_0", "quintal_0_noite", "quintal_2", "quintal_2_noite", "quintal_4", "quintal_4_noite",
           "quintal_3", "quintal_6", "quintal_6_noite")
ECON_SCENES = QUINTAL + ("quintal_painel", "quintal_desbloqueio", "loja_areas", "loja_racoes", "loja_decoracao",
                         "adocao_cheio", "breed_racao", "ficha_historico", "fim_run_meta", "prestigio_selo")
NIGHT_HOUR = "22:00"
PEN_SIM_SECONDS = 25.0


def default_hour(name: str) -> str:
    return NIGHT_HOUR if name.endswith("_noite") else "12:00"


def _more_cats(hub: HubController, adults: int = 0, kittens: int = 0) -> None:
    """Acrescenta copias (ids novos) de gatos da colecao: adultos e filhotes."""
    save = hub.save
    base = list(save.cats)
    for k in range(adults):
        save.cats.append(replace(base[k % len(base)], id=format_cat_id(save.next_cat_id), name=None,
                                 sex="M" if k % 2 == 0 else "F", rest_runs_left=0))
        save.next_cat_id += 1
    for k in range(kittens):
        save.cats.append(replace(base[k % len(base)], id=format_cat_id(save.next_cat_id), name=None,
                                 stage="kitten", runs_as_kitten=k % 2, iv_atk=5 - k, iv_hp=3 + k % 3))
        save.next_cat_id += 1


def _state(hub: HubController, areas: int, coins: int, prestige: int) -> None:
    hub.save.areas_unlocked = list(AREAS[:areas])
    hub.save.coins = coins
    hub.save.prestige = prestige


def _pen(hub: HubController, ui: UIState, areas: int, coins: int, prestige: int, kittens: int = 2) -> None:
    _more_cats(hub, adults=2, kittens=kittens)
    _state(hub, areas, coins, prestige)
    hub.col.refresh_deck()
    hub.col.complete()
    hub.col.toast = None
    hub.save.cats[3].name = "Mingau"
    hub.enter_pen()
    hub.pen.advance(PEN_SIM_SECONDS)
    ui.mouse = (-100, -100)


def _quintal(hub: HubController, ui: UIState, name: str) -> None:
    n = name.removesuffix("_noite")
    if n == "quintal_0":
        _pen(hub, ui, 0, 12, 1)
    elif n == "quintal_2":
        _pen(hub, ui, 2, 40, 2, kittens=3)
        hub.save.decorations_owned = ["deco-novelo"]
        hub.refresh_world()
        hub.pen.advance(3.0)
    elif n in ("quintal_3", "quintal_6"):               # 3 = areas 4 a 6 fechadas; 6 = tudo aberto
        _pen(hub, ui, 3 if n == "quintal_3" else 6, 80, 4, kittens=3)
        hub.save.decorations_owned = ["deco-novelo", "deco-ratinho"]
        hub.refresh_world()
        hub.pen.advance(3.0)
    else:
        _pen(hub, ui, 4, 80, 3, kittens=3)
        hub.save.decorations_owned = ["deco-novelo", "deco-ratinho", "deco-banco-arvore"]
        hub.refresh_world()
        hub.pen.advance(3.0)


def _quintal_painel(hub: HubController, ui: UIState) -> None:
    _pen(hub, ui, 0, 20, 1)
    hub.area_open = AREAS[0]
    ui.mouse = LS.area_panel_buttons()["area_buy"].center


def _desbloqueio(hub: HubController, ui: UIState) -> None:
    """Meio da animacao do desbloqueio: area recem-comprada, camada sumindo."""
    _pen(hub, ui, 0, 20, 1)
    hub.shop.buy_area(AREAS[0])
    hub.update(0.2)
    hub.pen.advance(0.4)


def _loja(hub: HubController, ui: UIState, tab: str) -> None:
    _more_cats(hub, kittens=0)
    _state(hub, 1, 28, 2)
    hub.save.rations["racao-fofa"] = 1
    hub.save.decorations_owned = ["deco-novelo"]
    hub.enter_pen()
    hub.shop.tab = tab
    hub.mode = "loja"
    pos = {"areas": LS.area_button(1), "racoes": LS.ration_button(0), "decoracao": LS.deco_button(1)}[tab]
    ui.mouse = pos.center


def _adocao_cheio(hub: HubController, ui: UIState, seed: int) -> None:
    _more_cats(hub, adults=6)            # 12 + 6 = 18 = vagas: gatil cheio
    hub.save.coins = 12
    create_adoption(hub.content, hub.save, Random(seed), "vitoria", 6)
    cats = hub.save.pending_adoption["cats"]
    hub.open_pending_adoption()
    hub.adopt.revealed.update(c.id for c in cats[:3])
    hub.adopt.click(("adopt", cats[0].id))              # gatil cheio: abre o painel de liberar vaga
    hub.adopt.room_sel = hub.adopt.room_cats()[1].id
    ui.mouse = LA.room_buttons()["room_donate"].center


def _breed_racao(hub: HubController, ui: UIState) -> None:
    _more_cats(hub, adults=4)
    _state(hub, 2, 20, 3)
    hub.save.rations.update({"racao-fofa": 2, "racao-veloz": 1, "racao-escolha": 1})
    adults = [c for c in hub.save.cats if c.stage == "adult"]
    male = next(c for c in adults if c.sex == "M")
    female = next(c for c in adults if c.sex == "F" and c.breed != male.breed)
    male.iv_atk, female.iv_atk, male.iv_hp, female.iv_hp = 4, 2, 3, 5
    hub.open_breed()
    bc = hub.breed
    bc.sel = {"M": male.id, "F": female.id}
    bc.ration, bc.choice = "racao-escolha", ("atk", "father")
    ui.mouse = LB.action_buttons()["start"].center


def _ficha(hub: HubController, ui: UIState) -> None:
    _pen(hub, ui, 2, 12, 2)
    cats = hub.save.cats
    cats[0].name = "Pipoca"
    kid = cats[2]
    kid.generation, kid.parents = 2, [cats[0].id, cats[1].id]
    kid.history = {"runs": 6, "duels_won": 14, "bosses_defeated": 2}
    hub.sync_pen()
    hub.open_ficha(kid.id)
    hub.pen.advance(0.3)
    ui.mouse = LP.ficha_close(hub.ficha_rect()).center


def _fim_run(hub: HubController, ui: UIState, seal: bool) -> None:
    _more_cats(hub)
    _state(hub, 1, 7, 2 if seal else 1)
    st = RunSettlement(earnings=[("batalha", 4), ("elite", 3)], coins=7, counted=True,
                       prestige_before=1, prestige_after=2 if seal else 1)
    hub.enter_pen()
    hub.mode = "resultado"
    hub.result_win, hub.short_run = False, False
    hub.result_text = "Run encerrada: derrota, nós vencidos 5"
    hub.result_detail = ["Você foi derrotado."]
    hub.summary = RunSummary(st, False, 5, age=5.0)
    if seal:
        st.earnings.append(("primeira-vitoria-liga", 20))
        st.coins = 27
        hub.save.coins = 27
        hub.result_win = True
        hub.result_text = "Run encerrada: vitória, nós vencidos 8"
        hub.result_detail = ["Primeira vitória da liga 1!"]
        hub.seal = [2, 0.6]
    ui.mouse = (-100, -100)


def make_scene(hub: HubController, ui: UIState, name: str, seed: int) -> None:
    if name in QUINTAL:
        _quintal(hub, ui, name)
    elif name == "quintal_painel":
        _quintal_painel(hub, ui)
    elif name == "quintal_desbloqueio":
        _desbloqueio(hub, ui)
    elif name.startswith("loja_"):
        _loja(hub, ui, {"loja_areas": "areas", "loja_racoes": "racoes", "loja_decoracao": "decoracao"}[name])
    elif name == "adocao_cheio":
        _adocao_cheio(hub, ui, seed)
    elif name == "breed_racao":
        _breed_racao(hub, ui)
    elif name == "ficha_historico":
        _ficha(hub, ui)
    elif name in ("fim_run_meta", "prestigio_selo"):
        _fim_run(hub, ui, name == "prestigio_selo")
