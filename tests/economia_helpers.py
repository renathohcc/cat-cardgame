"""Apoio dos testes da Fase 10a (economia, gatil, racao, odds, historico).

So usa a API publica do `core`. Escritos a partir da especificacao
`docs/propostas/2026-11-03-especificacao-10a.md`, nao do codigo."""
from __future__ import annotations

import json
from pathlib import Path
from random import Random

from core import Cat, SaveData, available_cats, load_content, new_run, new_run_from_save

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SAVE_SCHEMA = json.loads((DATA / "schemas" / "save.schema.json").read_text("utf-8"))

_CONTENT = None


def content():
    global _CONTENT
    if _CONTENT is None:
        _CONTENT = load_content(DATA)
    return _CONTENT


def cid(n: int) -> str:
    return f"c-{n:06d}"


def build(c, n: int = 16, breeds_n: int = 1, ivs: tuple[int, int] = (3, 3)) -> SaveData:
    """n adultos: impares = machos, pares = femeas. Deck = os 12 primeiros.
    `breeds_n` limita quantas racas distintas aparecem (1 = todos da mesma raca)."""
    breeds = list(c.breeds)[:breeds_n]
    natures = list(c.natures)
    s = SaveData()
    for i in range(1, n + 1):
        s.cats.append(Cat(id=cid(i), breed=breeds[i % len(breeds)],
                          sex="M" if i % 2 else "F", nature=natures[i % len(natures)],
                          iv_atk=ivs[0], iv_hp=ivs[1]))
    s.next_cat_id = n + 1
    s.deck = [x.id for x in s.cats][:12]
    return s


def finished_run(c, save: SaveData, wins: dict[str, int] | None = None,
                 result: str = "derrota", nodes: int | None = None, league: int | None = None):
    """Run no estado `finished` com os contadores pedidos (so atributos publicos)."""
    if len(save.deck) == c.rules["duel"]["deck_size"]:
        run = new_run_from_save(c, save, Random(0))
    else:   # deck incompleto (pais em breed): joga com os 12 primeiros disponiveis
        run = new_run(c, Random(0), available_cats(save)[:c.rules["duel"]["deck_size"]])
    run.wins = dict(wins or {})
    run.nodes_cleared = sum(run.wins.values()) if nodes is None else nodes
    run.status, run.result = "finished", result
    if league is not None:
        run.cfg = {**run.cfg, "league": league}
    return run


def pending(save: SaveData, cats: list[Cat], result: str = "vitoria") -> None:
    save.pending_adoption = {"cats": list(cats), "result": result, "nodes_cleared": 4}


def new_cat(save: SaveData, **kw) -> Cat:
    """Gato novo com id reservado (nao entra em save.cats)."""
    cat = Cat(id=cid(save.next_cat_id), **{"breed": next(iter(content().breeds)),
              "sex": "M", "nature": next(iter(content().natures)), "iv_atk": 3,
              "iv_hp": 3, **kw})
    save.next_cat_id += 1
    return cat


def fill_to(save: SaveData, n: int) -> None:
    """Acrescenta filhotes ate `len(cats) == n` (ocupam vaga, nao entram no deck)."""
    c = content()
    while len(save.cats) < n:
        save.cats.append(new_cat(save, breed=next(iter(c.breeds)), stage="kitten"))


def unlock_all_possible(c, save: SaveData) -> None:
    """Desbloqueia por API publica todas as areas liberadas (de graca, via moedas)."""
    from core import available_areas, unlock_area
    while True:
        avail = available_areas(c, save)
        if not avail:
            return
        save.coins = max(save.coins, avail[0].price)
        unlock_area(c, save, avail[0].id)


def p3_milestone(c) -> dict:
    """Marco do Prestigio 3 lido de data/rules.json."""
    return next(l["milestone"] for l in c.rules["prestige"]["levels"] if l["level"] == 3)


def min_iv_sum(c) -> int:
    return p3_milestone(c)["min_iv_sum"]


def set_strong_breeds(c, save: SaveData, n: int | None = None, soma: int | None = None) -> SaveData:
    """Os n primeiros gatos viram n racas distintas, cada um com soma de IV = `soma`
    (padrao: min_iv_sum de rules.json; ATK e HP entre 1 e 5)."""
    soma = min_iv_sum(c) if soma is None else soma
    n = p3_milestone(c)["count"] if n is None else n
    atk = min(5, soma - 1)
    for cat, breed in zip(save.cats[:n], list(c.breeds)[:n]):
        cat.breed = breed
        cat.iv_atk, cat.iv_hp = atk, soma - atk
    return save
