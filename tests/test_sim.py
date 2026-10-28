"""Simulador: determinismo por seed, sem excecoes e sem duelos no teto."""
from __future__ import annotations

import re

import pytest

from sim.run import build_report
from duel_helpers import load


def _rodar(seed: int, n: int = 20):
    return build_report(load(), seed, n)


def test_mesma_seed_gera_saida_identica():
    a, ea = _rodar(1)
    b, eb = _rodar(1)
    assert a == b and ea == eb == 0


def test_seeds_diferentes_geram_saidas_diferentes():
    assert _rodar(1)[0] != _rodar(2)[0]


def test_zero_excecoes_e_zero_duelos_no_teto():
    texto, erros = _rodar(1)
    assert erros == 0
    assert re.search(r"Duelos com exce\w+: 0\b", texto)
    assert re.search(r"teto de seguran\w+: 0 ", texto)


def test_relatorio_tem_taxas_por_raca_iv_e_natureza_e_duracao():
    texto, _ = _rodar(1)
    for trecho in ("Taxa de vitoria por raca", "Efeito do IV", "Efeito da natureza",
                   "Turnos: media"):
        assert trecho in texto


@pytest.mark.slow  # ~30 s (1000 duelos); roda por padrao
def test_vantagem_do_primeiro_jogador_entre_50_e_58_por_cento_com_pacote_b():
    """Pacote B (decisao 2026-10-27): 1000 duelos seed 1 -> quem comeca vence entre 50% e 58%."""
    texto, erros = _rodar_n(1, 1000)
    assert erros == 0
    linha = next(l for l in texto.splitlines() if l.startswith("| Misto vs misto (dado)"))
    pct = float(linha.split("|")[5].strip().rstrip("%").replace(",", "."))
    assert 50.0 <= pct <= 58.0, pct


def _rodar_n(seed: int, n: int):
    return build_report(load(), seed, n)
