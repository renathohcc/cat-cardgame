"""Apoio dos testes de UI e de fluxo da Fase 10a (T13.5). Headless (SDL dummy).

So usa os controladores da UI como o jogador (cliques) e a API publica do `core` para conferir
o estado final. O texto na tela e capturado interceptando `ui.font.draw` durante o desenho."""
from __future__ import annotations

import copy
import os
from contextlib import contextmanager
from pathlib import Path
from random import Random

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from core import Cat, SaveData, kennel_slots, new_game, occupied, save_to_dict, write_save
from ui import font
from ui.controller import load_game_content
from ui.daycycle import fixed_clock
from ui.hub_controller import HubController
from ui.render import UIState
from ui.render_hub import draw_hub_frame
from ui.theme import H, W

SEED = 7
_CONTENT = None


def game_content():
    global _CONTENT
    if _CONTENT is None:
        _CONTENT = load_game_content()
    return _CONTENT


def new_hub(save_path: Path | None = None, seed: int = SEED) -> HubController:
    pygame.init()
    return HubController(game_content(), save_path, seed, ai_delay=0.0, clock=fixed_clock("12:00"))


def hub_no_cercado(save: SaveData | None = None, save_path: Path | None = None) -> HubController:
    """Hub no cercado com um jogo novo em memoria (ou o `save` dado)."""
    h = new_hub(save_path)
    if save is None:
        h.click(("menu", "new_game"))
    else:
        h.adopt_save(save)
        h.enter_pen()
    assert h.mode == "cercado"
    return h


def add_cats(save: SaveData, adults: int = 0, kittens: int = 0) -> None:
    """Acrescenta adultos (M/F alternados) e filhotes; copia gatos existentes com ids novos."""
    base = [c for c in save.cats if c.stage == "adult"]
    for k in range(adults + kittens):
        src = base[k % len(base)]
        kitten = k >= adults
        save.cats.append(Cat(id=f"c-{save.next_cat_id:06d}", breed=src.breed,
                             sex="M" if k % 2 == 0 else "F", nature=src.nature, iv_atk=3, iv_hp=3,
                             stage="kitten" if kitten else "adult"))
        save.next_cat_id += 1


def fill_kennel(content, save: SaveData, with_kittens: int = 0) -> None:
    """Enche o gatil ate o limite (sobra de adultos, depois `with_kittens` filhotes no meio)."""
    add_cats(save, kittens=with_kittens)
    add_cats(save, adults=max(0, kennel_slots(content, save) - occupied(save)))
    assert occupied(save) == kennel_slots(content, save)


def draw_texts(h: HubController, ui: UIState | None = None, frames: int = 1) -> list[str]:
    """Desenha o hub `frames` quadros e devolve todo texto desenhado (via `font.draw`)."""
    canvas, ui = pygame.Surface((W, H)), ui or UIState()
    seen: list[str] = []
    real = font.draw

    def spy(surf, text, *a, **k):
        seen.append(str(text))
        return real(surf, text, *a, **k)

    font.draw = spy
    try:
        for _ in range(frames):
            h.update(0.05)
            draw_hub_frame(canvas, h, ui)
    finally:
        font.draw = real
    return seen


def has_text(texts: list[str], *parts: str) -> bool:
    """Algum texto desenhado contem todos os trechos (sem diferenciar maiusculas)."""
    low = [t.lower() for t in texts]
    return any(all(p.lower() in t for p in parts) for t in low)


def v1_dict(save: SaveData) -> dict:
    """Converte um save atual no formato v1 antigo (remove tudo que a v2 acrescentou)."""
    d = copy.deepcopy(save_to_dict(save))
    d["schema_version"] = 1
    for k in ("prestige", "areas_unlocked", "rations", "decorations_owned",
              "first_league_win_claimed", "lifetime"):
        d.pop(k, None)
    for cat in d["cats"] + (d.get("pending_adoption") or {}).get("cats", []):
        for k in ("generation", "parents", "history"):
            cat.pop(k, None)
    for b in d["breeding"]:
        b.pop("ration", None)
        b.pop("ration_choice", None)
    return d


def write_v1(path: Path, content, seed: int = SEED, coins: int = 0) -> bytes:
    """Grava no disco um save v1 de verdade (jogo novo convertido). Devolve os bytes."""
    import json
    s = new_game(content, Random(seed))
    s.coins = coins
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(v1_dict(s), ensure_ascii=False, indent=2), encoding="utf-8")
    return path.read_bytes()


# ------------------------------------------------------------------ cenarios comuns
def area_def(c, i: int) -> dict:
    """Definicao da i-esima area (por `order`) de data/shop.json."""
    return sorted(c.shop["areas"], key=lambda a: a["order"])[i]


def area_ids(c) -> list[str]:
    return [a["id"] for a in sorted(c.shop["areas"], key=lambda a: a["order"])]


def open_shop(h: HubController) -> None:
    h.click(("pen_btn", "loja"))
    assert h.mode == "loja"


def buy_area_at_yard(h: HubController, area_id: str) -> None:
    """Loja > linha da area > placa no quintal > COMPRAR (como o jogador)."""
    open_shop(h)
    h.click(("shop_area", area_id))
    assert h.mode == "cercado" and h.area_open == area_id
    h.click(("area_buy", area_id))


def offer(c, h: HubController, seed: int = 3) -> list[Cat]:
    """Cria uma oferta de adocao, abre a tela e revela todos os gatos."""
    from core import create_adoption
    create_adoption(c, h.save, Random(seed), "vitoria", 6)
    assert h.open_pending_adoption()
    h.adopt.click(("reveal_all",))
    return h.adopt.cats()


def couple(save: SaveData) -> tuple[Cat, Cat]:
    """Macho e femea livres de racas diferentes."""
    from core import available_cats
    ad = available_cats(save)
    m = next(x for x in ad if x.sex == "M")
    return m, next(x for x in ad if x.sex == "F" and x.breed != m.breed)


def finish_run(c, h: HubController, wins: dict, result: str = "derrota", league: int | None = None):
    """Faz o hub fechar uma `Run` real ja terminada com os contadores dados (como o RunController)."""
    from types import SimpleNamespace
    from economia_helpers import finished_run
    run = finished_run(c, h.save, wins=wins, result=result, league=league)
    h.rc = SimpleNamespace(run=run, screen="finished", abandoned=False, end_line=None,
                           click=lambda e: None, update=lambda dt: None)
    h.mode = "run"
    h.click(None)
    return run


def to_result(h: HubController) -> None:
    """Passa por novidades e adocao (doando as ofertas) ate chegar ao resumo/cercado."""
    for _ in range(20):
        if h.mode == "novidades":
            h.click(("news_continue",))
        elif h.mode == "adocao":
            h.click(("reveal_all",))
            ids = h.adopt.visible_ids()
            if not ids:
                break
            h.click(("donate", ids[0]))
        else:
            break
