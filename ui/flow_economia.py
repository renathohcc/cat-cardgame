"""Fluxo completo headless da economia (T13.4): `python -m ui.flow_economia`.

Comprar area, comprar racao, iniciar breed com racao, fechar uma run (close_run) com adocao e gatil
cheio. So usa o controlador do hub (cliques como o jogador) e desenha cada tela para provar que nada
levanta excecao. Sem disco (save so em memoria). Sai com codigo 0 se tudo passar.
"""
from __future__ import annotations

import os
import sys
from dataclasses import replace
from random import Random
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame  # noqa: E402

from core import kennel_slots, occupied  # noqa: E402
from core.save import format_cat_id  # noqa: E402
from ui import layout_adopt as LA, layout_breed as LB  # noqa: E402
from ui.controller import load_game_content  # noqa: E402
from ui.daycycle import fixed_clock  # noqa: E402
from ui.hub_controller import HubController  # noqa: E402
from ui.render import UIState  # noqa: E402
from ui.render_hub import draw_hub_frame  # noqa: E402
from ui.theme import H, W  # noqa: E402


def _draw(hub: HubController, canvas: pygame.Surface, ui: UIState) -> None:
    hub.update(0.05)
    draw_hub_frame(canvas, hub, ui)


def _add_adults(hub: HubController, n: int) -> None:
    save, base = hub.save, list(hub.save.cats)
    for k in range(n):
        save.cats.append(replace(base[k % len(base)], id=format_cat_id(save.next_cat_id), name=None,
                                 sex="M" if k % 2 == 0 else "F", rest_runs_left=0))
        save.next_cat_id += 1


def _fake_finished_run(hub: HubController):
    """Run de verdade (`new_run_from_save`) ja terminada em vitoria, embrulhada como o RunController."""
    run = hub.col.start_run(Random(5))
    run.status, run.result, run.nodes_cleared = "finished", "vitoria", 6
    run.wins = {"batalha": 3, "elite": 1, "chefe": 1}
    return SimpleNamespace(run=run, screen="finished", abandoned=False, end_line=None,
                           click=lambda e: None, update=lambda dt: None)


def main() -> int:
    pygame.init()
    canvas, ui = pygame.Surface((W, H)), UIState()
    content = load_game_content()
    hub = HubController(content, None, 3, ai_delay=0.0, clock=fixed_clock("12:00"))
    hub.click(("menu", "new_game"))
    assert hub.mode == "cercado", hub.mode
    save = hub.save
    _draw(hub, canvas, ui)

    # 1. comprar area pela loja -> atalho para a placa -> painel -> COMPRAR
    save.coins = 80
    hub.click(("pen_btn", "loja"))
    assert hub.mode == "loja"
    _draw(hub, canvas, ui)
    area = content.shop["areas"][0]["id"]
    hub.click(("shop_area", area))
    assert hub.mode == "cercado" and hub.area_open == area
    _draw(hub, canvas, ui)
    slots0 = kennel_slots(content, save)
    hub.click(("area_buy", area))
    assert area in save.areas_unlocked and hub.area_open is None and hub.unlock_fx
    assert kennel_slots(content, save) == slots0 + 2 and save.coins == 80 - content.shop["areas"][0]["price"]
    for _ in range(12):
        _draw(hub, canvas, ui)
    assert not hub.unlock_fx

    # 2. comprar racao e decoracao
    hub.click(("pen_btn", "loja"))
    hub.click(("shop_tab", "racoes"))
    hub.click(("shop_ration", "racao-fofa"))
    assert save.rations["racao-fofa"] == 1
    hub.click(("shop_tab", "decoracao"))
    hub.click(("shop_deco", "deco-novelo"))
    assert "deco-novelo" in save.decorations_owned
    _draw(hub, canvas, ui)
    hub.click(("shop_back",))
    assert hub.mode == "cercado"

    # 3. breed com racao
    _add_adults(hub, 4)
    hub.click(("pen_btn", "breed"))
    assert hub.mode == "criatorio"
    bc = hub.breed
    male = bc.rows("M")[0].cat
    female = next(r.cat for r in bc.rows("F") if r.cat.breed != male.breed)
    hub.click(("row", "M", male.id))
    hub.click(("row", "F", female.id))
    hub.click(("ration", "racao-fofa"))
    assert bc.ration == "racao-fofa" and bc.odds() is not None and bc.odds().mutation > 0.1
    _draw(hub, canvas, ui)
    hub.click(("start",))
    assert save.breeding and save.breeding[0]["ration"] == "racao-fofa", save.breeding
    assert save.rations["racao-fofa"] == 0
    _draw(hub, canvas, ui)
    hub.click(("back",))
    assert hub.mode == "cercado"

    # 4. fechar uma run (close_run) com adocao; gatil cheio pede para liberar vaga
    hub.click(("pen_btn", "colecao"))
    hub.col.complete()
    hub.rc, hub.mode = _fake_finished_run(hub), "run"
    coins0 = save.coins
    hub.click(None)
    assert hub.summary is not None and save.coins > coins0, (hub.mode, hub.summary)
    for _ in range(40):
        _draw(hub, canvas, ui)
        if hub.mode == "novidades":
            hub.click(("news_continue",))
        elif hub.mode == "adocao":
            ad = hub.adopt
            hub.click(("reveal_all",))
            while occupied(save) < kennel_slots(content, save):       # enche o gatil para provar o painel
                _add_adults(hub, 1)
            hub.click(("adopt", ad.visible_ids()[0]))
            assert ad.room_for, "gatil cheio deveria abrir o painel de vaga"
            _draw(hub, canvas, ui)
            n = len(save.cats)
            hub.click(("room_pick", ad.room_cats()[0].id))
            hub.click(("room_donate",))
            assert len(save.cats) == n, "doou 1 e adotou 1"
            ids = ad.visible_ids()
            while ids and hub.mode == "adocao":
                hub.click(("donate", ids[0]))
                ids = ad.visible_ids() if hub.mode == "adocao" else []
        elif hub.mode == "resultado":
            _draw(hub, canvas, ui)
            hub.click(("result_back",))
        elif hub.mode == "cercado":
            break
    assert hub.mode == "cercado", hub.mode
    _draw(hub, canvas, ui)
    print("fluxo da economia: OK "
          f"(moedas {save.coins}, vagas {occupied(save)}/{kennel_slots(content, save)}, "
          f"areas {len(save.areas_unlocked)}, prestigio {save.prestige})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
