"""Testes da IA (core.ai.choose_action). Fonte: CONTRATOS 2.3/2.4."""
from __future__ import annotations

from random import Random

import pytest

from core.ai import choose_action
from core.duel import apply_action, is_over, legal_actions, new_duel
from core.types import IllegalAction
from duel_helpers import deck_spec, load

MAX_ACOES = 3000


@pytest.fixture(scope="module")
def content():
    return load()


def novo(content, seed: int, first: bool | None = None):
    return new_duel(content, Random(seed), deck_spec(content, seed * 2 + 1),
                    deck_spec(content, seed * 2 + 2), player_first=first)


def test_acao_da_ia_esta_sempre_em_legal_actions_nos_dois_lados(content):
    for seed in range(30):
        d = novo(content, seed)
        rng = Random(seed)
        passos = 0
        while is_over(d) is None and passos < MAX_ACOES:
            lado = d.turn_side
            acao = choose_action(d, lado, rng)
            assert acao in legal_actions(d), (seed, passos, acao)
            apply_action(d, acao)
            passos += 1
        assert is_over(d) is not None


def test_ia_levanta_valueerror_fora_da_vez(content):
    d = novo(content, 1, first=True)
    outro = "enemy" if d.turn_side == "player" else "player"
    with pytest.raises(ValueError):
        choose_action(d, outro, Random(1))


def test_ia_levanta_valueerror_com_duelo_acabado(content):
    d = novo(content, 2)
    rng = Random(2)
    for _ in range(MAX_ACOES):
        if is_over(d) is not None:
            break
        apply_action(d, choose_action(d, d.turn_side, rng))
    assert is_over(d) is not None
    for lado in ("player", "enemy"):
        with pytest.raises(ValueError):
            choose_action(d, lado, Random(3))


def test_mesma_seed_gera_a_mesma_acao(content):
    for seed in range(10):
        d1 = novo(content, seed, first=True)
        d2 = novo(content, seed, first=True)
        a1 = choose_action(d1, d1.turn_side, Random(99))
        a2 = choose_action(d2, d2.turn_side, Random(99))
        assert a1 == a2


def test_mesma_seed_gera_a_mesma_partida_inteira(content):
    def joga(seed):
        d = novo(content, seed, first=True)
        rng = Random(seed)
        acoes = []
        while is_over(d) is None and len(acoes) < MAX_ACOES:
            a = choose_action(d, d.turn_side, rng)
            acoes.append(a)
            apply_action(d, a)
        return acoes, is_over(d)

    assert joga(7) == joga(7)


def test_ia_vs_ia_em_100_seeds_sempre_termina_com_vencedor_sem_ilegal(content):
    for seed in range(100):
        d = novo(content, seed)
        rng = Random(seed)
        passos = 0
        try:
            while is_over(d) is None:
                apply_action(d, choose_action(d, d.turn_side, rng))
                passos += 1
                assert passos < MAX_ACOES, f"seed {seed} nao terminou"
        except IllegalAction as e:  # pragma: no cover
            pytest.fail(f"seed {seed}: IllegalAction {e}")
        assert is_over(d) in ("player", "enemy")
