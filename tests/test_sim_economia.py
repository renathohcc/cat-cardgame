"""Simulador de economia (sim/economia.py): determinismo, politicas e invariantes."""
from __future__ import annotations

import pytest

from economia_helpers import content as _content
from sim import economia as E


@pytest.fixture(scope="module")
def c():
    return _content()


def texto(c, seed=1, runs=14, carreiras=2, pols=("area", "barato"), mapa="aleatorio"):
    return E.render(c, E.rodar(c, seed, carreiras, runs, list(pols), mapa), seed, runs, mapa)


def test_mesma_seed_gera_relatorio_identico(c):
    assert texto(c, 3) == texto(c, 3)


def test_seeds_diferentes_geram_relatorios_diferentes(c):
    assert texto(c, 3) != texto(c, 4)


def test_relatorio_traz_as_secoes_pedidas(c):
    t = texto(c)
    for trecho in ("Moedas por run", "Area 1", "Area 6", "Prestigio 2", "Prestigio 3",
                   "Ritmo de desbloqueios", "Custo das racoes", "`area`", "`barato`"):
        assert trecho in t


@pytest.mark.parametrize("politica", E.POLITICAS)
def test_carreira_respeita_regras_do_core(c, politica):
    car = E.jogar_carreira(c, 5, 0, 25, politica, "aleatorio")
    assert len(car.logs) == 25
    for lg in car.logs:
        assert lg.coins_after >= 0 and 18 <= lg.slots <= 30
        assert lg.prestige <= 3                      # niveis 4 e 5 travados na 10a
    areas = [e for lg in car.logs for e in lg.events if e.startswith("area:")]
    assert areas == [f"area:{k}" for k in range(1, len(areas) + 1)]      # sempre em ordem
    assert len(areas) == len(set(areas)) and "area:5" not in areas


def test_politica_area_compra_a_area_antes_de_decoracao_quando_ela_esta_liberada(c):
    car = E.jogar_carreira(c, 7, 1, 30, "area", "aleatorio")
    primeira_deco = next((lg.idx for lg in car.logs
                          if any(e.startswith("deco:") for e in lg.events)), None)
    area1 = E.primeira_run(car, "area:1")
    assert area1 is not None
    assert primeira_deco is None or primeira_deco >= area1


def test_percentil_interpola():
    assert E.percentil([1, 2, 3, 4, 5], 50) == 3
    assert E.percentil([0, 10], 10) == 1
