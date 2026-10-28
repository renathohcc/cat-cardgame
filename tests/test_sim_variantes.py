"""Variantes do simulador: em memoria, deterministicas e sem tocar em data/."""
from __future__ import annotations

import hashlib
from pathlib import Path
from random import Random

import pytest

from duel_helpers import load
from sim import run as R
from sim.variantes import VARIANTES, Variante, aplicar, medir

DATA = Path(__file__).resolve().parent.parent / "data"


def _hash_data() -> dict[str, str]:
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(DATA.rglob("*.json"))}


def test_variante_altera_custo_so_na_copia():
    content = load()
    novo = aplicar(content, Variante("t", "", custos={"maine-coon": 4}))
    assert novo.breeds["maine-coon"]["custo"] == 4
    assert content.breeds["maine-coon"]["custo"] == 3  # pacote B (CONTRATOS 1.2)


def test_variante_altera_regra_so_na_copia():
    content = load()
    novo = aplicar(content, Variante("t", "", regras={"energy_start": 3}))
    assert novo.rules["duel"]["energy_start"] == 3
    assert content.rules["duel"]["energy_start"] == 2


def test_raca_ou_regra_desconhecida_da_erro():
    with pytest.raises(KeyError):
        aplicar(load(), Variante("t", "", custos={"naoexiste": 1}))
    with pytest.raises(KeyError):
        aplicar(load(), Variante("t", "", regras={"naoexiste": 1}))


def test_medir_nao_altera_arquivos_de_data():
    antes = _hash_data()
    medir(load(), VARIANTES["pacote-A"], 1, 10)
    assert _hash_data() == antes


def test_medir_e_deterministico_por_seed():
    a = medir(load(), VARIANTES["mc4"], 1, 10)
    b = medir(load(), VARIANTES["mc4"], 1, 10)
    assert a == b and a["errors"] == 0
    assert medir(load(), VARIANTES["mc4"], 2, 10) != a


def test_handicap_de_energia_do_segundo_jogador():
    content = aplicar(load(), VARIANTES["a-seg-e3"])
    rng = Random(1)
    from core.duel import new_duel
    from core.types import DeckSpec
    duel = new_duel(content, rng, DeckSpec(R.deck_of(content, rng)), DeckSpec(R.deck_of(content, rng)), True)
    hc = content.extras["sim_handicap"]
    second = R._second(duel)
    assert second == "enemy"
    duel.turn_side = second
    duel.sides[second].turns_taken = 1
    duel.sides[second].energy = 2
    R.apply_handicap_turn(duel, hc, content.rules["duel"]["energy_cap"])
    assert duel.sides[second].energy == 3


def test_handicap_de_carta_extra_para_o_segundo():
    content = aplicar(load(), VARIANTES["b-seg-mao5"])
    rng = Random(1)
    from core.duel import new_duel
    from core.types import DeckSpec
    duel = new_duel(content, rng, DeckSpec(R.deck_of(content, rng)), DeckSpec(R.deck_of(content, rng)), True)
    n_first, n_second = len(duel.sides["player"].hand), len(duel.sides["enemy"].hand)
    R.apply_handicap_start(duel, content.extras["sim_handicap"])
    assert len(duel.sides["enemy"].hand) == n_second + 1
    assert len(duel.sides["player"].hand) == n_first
