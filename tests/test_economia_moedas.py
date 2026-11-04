"""Carteira, fontes de moeda e Prestigio (Fase 10a, T13.2).

Fonte: especificacao 10a, secoes 1 (Prestigio) e 2 (economia) e `data/rules.json`.
Valores esperados lidos de `data/rules.json` (economy): batalha, elite, chefe e bonus da liga 1."""
from __future__ import annotations

from random import Random

import pytest

from core import (adopt, close_run, new_game, new_run_from_save, prestige_info,
                  prestige_level, run_earnings, save_to_dict, update_prestige)
from core.types import IllegalAction
from economia_helpers import (build, content as _content, finished_run, min_iv_sum, new_cat,
                              pending, set_strong_breeds)
from sim import balanceamento as B

_ECO = _content().rules["economy"]
BAT, ELI, CHE = _ECO["coins_battle_node"], _ECO["coins_elite_node"], _ECO["coins_boss_node"]
LIGA = _ECO["league1_first_win_bonus"]


@pytest.fixture(scope="module")
def c():
    return _content()


@pytest.fixture
def save(c):
    return build(c, 16, breeds_n=1)


def ganhos(settlement) -> dict[str, int]:
    return dict(settlement.earnings)


# ------------------------------------------------------------ fontes de moeda
def test_no_de_batalha_vencido_paga_o_valor_da_regra(c, save):
    r = close_run(c, save, finished_run(c, save, {"batalha": 1}))
    assert save.coins == BAT and r.coins == BAT


def test_no_de_elite_vencido_paga_o_valor_da_regra(c, save):
    close_run(c, save, finished_run(c, save, {"elite": 1}))
    assert save.coins == ELI


def test_no_de_chefe_vencido_paga_o_valor_da_regra(c, save):
    close_run(c, save, finished_run(c, save, {"chefe": 1}))
    assert save.coins == CHE


def test_varios_nos_somam_cada_fonte(c, save):
    r = close_run(c, save, finished_run(c, save, {"batalha": 3, "elite": 2, "chefe": 1}))
    assert save.coins == 3 * BAT + 2 * ELI + 1 * CHE
    assert r.coins == save.coins


def test_no_de_descanso_nao_paga(c, save):
    r = close_run(c, save, finished_run(c, save, {"descanso": 2}, nodes=2))
    assert save.coins == 0 and r.earnings == []


def test_moedas_somam_ao_saldo_que_ja_existia(c, save):
    save.coins = 10
    close_run(c, save, finished_run(c, save, {"elite": 1}))
    assert save.coins == 10 + ELI


def test_primeira_vitoria_da_liga_1_paga_20_extra_uma_unica_vez(c, save):
    r1 = close_run(c, save, finished_run(c, save, {"batalha": 3, "chefe": 1}, "vitoria"))
    assert r1.first_league_win and save.first_league_win_claimed
    assert save.coins == BAT * 3 + CHE + LIGA
    antes = save.coins
    r2 = close_run(c, save, finished_run(c, save, {"batalha": 3, "chefe": 1}, "vitoria"))
    assert not r2.first_league_win
    assert save.coins - antes == BAT * 3 + CHE
    assert save.first_league_win_claimed is True


def test_derrota_nao_reclama_o_bonus_da_liga(c, save):
    r = close_run(c, save, finished_run(c, save, {"batalha": 2}, "derrota"))
    assert not r.first_league_win and not save.first_league_win_claimed
    assert save.coins == 2 * BAT


def test_bonus_da_liga_1_ainda_vale_depois_de_derrotas(c, save):
    close_run(c, save, finished_run(c, save, {"batalha": 1}, "derrota"))
    close_run(c, save, finished_run(c, save, {"chefe": 1}, "vitoria"))
    assert save.coins == BAT + CHE + LIGA


def test_vitoria_em_save_migrado_sem_flag_ainda_recebe_o_bonus(c, save):
    """Save migrado do v1 tem first_league_win_claimed False: o bonus e pago na 1a vitoria."""
    assert save.first_league_win_claimed is False
    close_run(c, save, finished_run(c, save, {"chefe": 1}, "vitoria"))
    assert save.first_league_win_claimed is True


def test_vitoria_em_liga_2_nao_paga_o_bonus_da_liga_1(c, save):
    r = close_run(c, save, finished_run(c, save, {"chefe": 1}, "vitoria", league=2))
    assert not r.first_league_win and save.coins == CHE


# ------------------------------------------------------------ abandono
def test_run_abandonada_antes_de_qualquer_no_nao_paga_nada(c, save):
    run = new_run_from_save(c, save, Random(1))
    run.abandon()
    r = close_run(c, save, run)
    assert save.coins == 0 and r.earnings == [] and not r.counted


def test_run_abandonada_paga_so_o_que_ja_ganhou(c, save):
    run = finished_run(c, save, {"batalha": 2, "elite": 1}, "derrota")
    r = close_run(c, save, run)
    assert save.coins == 2 * BAT + ELI and not r.first_league_win and not r.league_cleared


# ------------------------------------------------------------ resumo de ganhos
def test_resumo_lista_fonte_e_valor_e_a_soma_bate_com_o_saldo(c, save):
    save.coins = 4
    r = close_run(c, save, finished_run(c, save, {"batalha": 2, "elite": 1, "chefe": 1},
                                        "vitoria"))
    g = ganhos(r)
    assert g == {"batalha": 2 * BAT, "elite": ELI, "chefe": CHE, "primeira-vitoria-liga": LIGA}
    assert sum(v for _, v in r.earnings) == r.coins == save.coins - 4


def test_resumo_nao_lista_fontes_zeradas(c, save):
    r = close_run(c, save, finished_run(c, save, {"elite": 1}))
    assert [s for s, _ in r.earnings] == ["elite"]


def test_run_earnings_e_puro_e_igual_ao_resumo_do_close_run(c, save):
    run = finished_run(c, save, {"batalha": 2, "chefe": 1}, "vitoria")
    antes = save_to_dict(save)
    previa = run_earnings(c, run, first_league_win=True)
    assert save_to_dict(save) == antes and run.settled is False
    assert previa == close_run(c, save, run).earnings


def test_close_run_so_uma_vez_por_run(c, save):
    run = finished_run(c, save, {"batalha": 1})
    close_run(c, save, run)
    with pytest.raises(IllegalAction):
        close_run(c, save, run)
    assert save.coins == BAT


def test_close_run_exige_run_terminada(c, save):
    run = new_run_from_save(c, save, Random(2))
    with pytest.raises(IllegalAction):
        close_run(c, save, run)
    assert save.coins == 0


@pytest.mark.parametrize("seed", range(6))
def test_runs_reais_da_ia_pagam_exatamente_o_que_venceram(c, seed):
    """Joga a run inteira com a IA e confere o pagamento contra a tabela da regra."""
    s = new_game(c, Random(seed))
    rng = Random(100 + seed)
    run = new_run_from_save(c, s, rng)
    B.jogar_run(c, rng, run)
    esperado = run.wins.get("batalha", 0) * BAT + run.wins.get("elite", 0) * ELI \
        + run.wins.get("chefe", 0) * CHE + (LIGA if run.result == "vitoria" else 0)
    r = close_run(c, s, run)
    assert s.coins == esperado == r.coins


# ------------------------------------------------------------ Prestigio
def test_prestigio_comeca_em_1(c):
    s = new_game(c, Random(1))
    assert s.prestige == 1 and prestige_level(c, s) == 1


def test_vencer_a_liga_1_leva_ao_prestigio_2(c, save):
    r = close_run(c, save, finished_run(c, save, {"chefe": 1}, "vitoria"))
    assert (r.prestige_before, r.prestige_after) == (1, 2)
    assert r.prestige_up and save.prestige == 2 and save.progress["leagues_cleared"] >= 1


def test_derrota_nao_sobe_o_prestigio(c, save):
    r = close_run(c, save, finished_run(c, save, {"batalha": 2, "elite": 1}, "derrota"))
    assert r.prestige_after == 1 and save.prestige == 1


def test_cinco_racas_distintas_sozinhas_nao_pulam_o_marco_da_liga(c, save):
    """Decisao do core (T13.1 item 3): Prestigio e sequencial, o nivel 3 pede o 2."""
    set_strong_breeds(c, save)
    assert len({x.breed for x in save.cats}) == 5
    assert update_prestige(c, save) == 1


def test_cinco_racas_distintas_levam_ao_prestigio_3_depois_da_liga(c, save):
    set_strong_breeds(c, save)
    close_run(c, save, finished_run(c, save, {"chefe": 1}, "vitoria"))
    assert save.prestige == 3


def test_quatro_racas_nao_bastam_para_o_prestigio_3(c, save):
    save.prestige = 2
    for cat, breed in zip(save.cats, list(c.breeds)[:4]):
        cat.breed = breed
    assert len({x.breed for x in save.cats}) == 4
    assert update_prestige(c, save) == 2


def test_adotar_a_quinta_raca_sobe_o_prestigio_para_3(c, save):
    save.prestige = 2
    save.progress["leagues_cleared"] = 1
    breeds = list(c.breeds)
    set_strong_breeds(c, save, 4)
    novo = new_cat(save, breed=breeds[4], iv_atk=min_iv_sum(c) - 3, iv_hp=3)
    pending(save, [novo])
    adopt(c, save, novo.id)
    assert save.prestige == 3


@pytest.mark.parametrize("liga", [1, 3, 99])
def test_niveis_4_e_5_nao_sobem_na_10a_mesmo_com_todos_os_marcos_possiveis(c, save, liga):
    set_strong_breeds(c, save)
    save.progress["leagues_cleared"] = liga
    assert update_prestige(c, save) == 3
    info = prestige_info(c, save)
    assert info.level == 3 and info.next_level == 4 and info.locked is True
    assert info.missing is None


def test_prestigio_nunca_desce_mesmo_perdendo_a_colecao_que_o_deu(c, save):
    save.prestige = 3
    assert update_prestige(c, save) == 3          # colecao de 1 raca so
    save.cats = save.cats[:12]
    assert prestige_level(c, save) == 3 and update_prestige(c, save) == 3


def test_prestigio_guardado_maior_que_os_marcos_prevalece(c, save):
    save.prestige = 2
    assert prestige_level(c, save) == 2


def test_prestige_level_e_puro(c, save):
    save.progress["leagues_cleared"] = 1
    antes = save_to_dict(save)
    assert prestige_level(c, save) == 2
    assert save_to_dict(save) == antes


def test_info_no_nivel_1_mostra_o_marco_da_liga_e_o_que_falta(c, save):
    info = prestige_info(c, save)
    assert (info.level, info.next_level, info.locked) == (1, 2, False)
    assert info.milestone["type"] == "win_league"
    assert (info.current, info.target, info.missing) == (0, 1, 1)


def test_info_no_nivel_2_conta_racas_distintas(c, save):
    save.prestige = 2
    set_strong_breeds(c, save, 3)
    info = prestige_info(c, save)
    assert (info.next_level, info.current, info.target, info.missing) == (3, 3, 5, 2)
    assert info.milestone["type"] == "distinct_breeds_min_iv"


def test_info_no_ultimo_nivel_aberto_aponta_o_4_travado(c, save):
    save.prestige = 3
    info = prestige_info(c, save)
    assert info.level == 3 and info.next_level == 4 and info.locked
    assert info.current is None and info.target is None
