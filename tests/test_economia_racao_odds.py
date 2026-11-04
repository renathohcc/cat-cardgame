"""Racoes e previa de odds do breed (Fase 10a, T13.2).

Fonte: especificacao 10a, secoes 4 (racao) e 5 (previa de odds).
Racao Fofa: mutacao 7% -> 15%. Veloz: breed termina 1 run antes (minimo 1).
Escolha: 1 IV (ATK ou HP) de um dos pais fixado na ninhada inteira, sem mutacao nele.

Estatistica: cada cenario sorteia N ninhadas com seed fixa e compara a frequencia de cada
resultado com `breed_odds` (que e exata). Tolerancia: 4,5 desvios-padrao binomiais
(erro de falso alarme ~7e-6 por comparacao) com piso de 0,004; as seeds sao fixas, entao o
resultado e deterministico. O teste de sensibilidade confirma que a tolerancia pega
a diferenca 7% x 15%."""
from __future__ import annotations

import copy
import math
import random as random_global
from collections import Counter
from functools import lru_cache
from random import Random

import pytest

from core import (Cat, IvChoice, SaveData, advance_after_run, breed_odds, breeding_status,
                  buy_ration, cancel_breed, can_start_breed, initial_runs, iv_distribution,
                  rations_catalog, save_to_dict, start_breed, update_prestige)
from core.types import IllegalAction
from economia_helpers import build, cid, content as _content, set_strong_breeds

M, F = cid(1), cid(2)
N_NINHADAS = 5000


@pytest.fixture(scope="module")
def c():
    return _content()


@pytest.fixture
def save(c):
    return build(c, 16, breeds_n=1)


def p_n(save, c, nivel: int):
    """Sobe o save para o Prestigio pedido (so pela API de marcos)."""
    if nivel >= 2:
        save.progress["leagues_cleared"] = 1
    if nivel >= 3:
        set_strong_breeds(c, save)
    return save


# ------------------------------------------------------------ compra de racao
def test_comprar_racao_fofa_custa_12_e_soma_1_ao_estoque(c, save):
    save.coins = 12
    assert buy_ration(c, save, "racao-fofa") == 1
    assert save.coins == 0 and save.rations["racao-fofa"] == 1


def test_comprar_duas_vezes_acumula_estoque_e_debita_duas_vezes(c, save):
    save.coins = 30
    buy_ration(c, save, "racao-fofa")
    assert buy_ration(c, save, "racao-fofa") == 2
    assert save.coins == 30 - 24


@pytest.mark.parametrize("ration, preco, nivel", [("racao-fofa", 12, 1), ("racao-veloz", 15, 2),
                                                  ("racao-escolha", 30, 3)])
def test_precos_e_prestigio_das_racoes_conforme_a_especificacao(c, save, ration, preco, nivel):
    item = next(r for r in c.shop["rations"] if r["id"] == ration)
    assert (item["price"], item["prestige_required"]) == (preco, nivel)


def test_racao_veloz_pede_prestigio_2_mesmo_com_moedas(c, save):
    save.coins = 500
    antes = save_to_dict(save)
    with pytest.raises(IllegalAction):
        buy_ration(c, save, "racao-veloz")
    assert save_to_dict(save) == antes


def test_racao_escolha_pede_prestigio_3_mesmo_com_moedas(c, save):
    save.coins = 500
    p_n(save, c, 2)
    update_prestige(c, save)
    antes = save_to_dict(save)
    with pytest.raises(IllegalAction):
        buy_ration(c, save, "racao-escolha")
    assert save_to_dict(save) == antes
    p_n(save, c, 3)
    assert buy_ration(c, save, "racao-escolha") == 1 and save.coins == 470


def test_comprar_racao_sem_moedas_falha_sem_alterar_o_save(c, save):
    save.coins = 11
    antes = save_to_dict(save)
    with pytest.raises(IllegalAction):
        buy_ration(c, save, "racao-fofa")
    assert save_to_dict(save) == antes


def test_comprar_racao_inexistente_falha(c, save):
    save.coins = 100
    with pytest.raises(IllegalAction):
        buy_ration(c, save, "racao-quantica")


def test_catalogo_de_racoes_mostra_estoque_prestigio_e_se_da_para_comprar(c, save):
    save.coins = 20
    save.rations["racao-fofa"] = 2
    cat = {r["id"]: r for r in rations_catalog(c, save)}
    assert cat["racao-fofa"]["stock"] == 2 and cat["racao-fofa"]["can_buy"]
    assert cat["racao-veloz"]["prestige_ok"] is False and cat["racao-veloz"]["can_buy"] is False
    assert cat["racao-escolha"]["can_buy"] is False


# ------------------------------------------------------------ uma racao por casal
def test_iniciar_breed_com_racao_gasta_uma_do_estoque_e_grava_no_casal(c, save):
    save.rations["racao-fofa"] = 2
    start_breed(c, save, M, F, ration="racao-fofa")
    assert save.rations["racao-fofa"] == 1
    assert save.breeding == [{"male": M, "female": F, "runs_left": 2, "ration": "racao-fofa",
                              "ration_choice": None}]
    st = breeding_status(save, c)[0]
    assert st["ration"] == "racao-fofa" and st["choice"] is None


def test_iniciar_breed_sem_estoque_da_racao_falha_sem_alterar_o_save(c, save):
    antes = save_to_dict(save)
    ok, motivo = can_start_breed(c, save, M, F, ration="racao-fofa")
    assert not ok and motivo
    with pytest.raises(IllegalAction):
        start_breed(c, save, M, F, ration="racao-fofa")
    assert save_to_dict(save) == antes


def test_cada_casal_usa_a_sua_propria_racao_do_estoque(c, save):
    save.areas_unlocked = ["cercado-adultos-ampliado", "cercadinho-filhotes",
                           "patio-casais-ampliado"]
    save.rations["racao-fofa"] = 1
    start_breed(c, save, M, F, ration="racao-fofa", enforce_limits=True)
    with pytest.raises(IllegalAction):             # estoque acabou: segundo casal sem racao
        start_breed(c, save, cid(3), cid(4), ration="racao-fofa", enforce_limits=True)
    start_breed(c, save, cid(3), cid(4), enforce_limits=True)
    assert [b["ration"] for b in save.breeding] == ["racao-fofa", None]


def test_racao_inexistente_no_breed_falha(c, save):
    save.rations["racao-quantica"] = 1
    with pytest.raises(IllegalAction):
        start_breed(c, save, M, F, ration="racao-quantica")


def test_cancelar_breed_que_nao_andou_devolve_a_racao(c, save):
    save.rations["racao-veloz"] = 1
    start_breed(c, save, M, F, ration="racao-veloz")
    assert save.rations["racao-veloz"] == 0
    cancel_breed(c, save, M, F)
    assert save.rations["racao-veloz"] == 1 and save.breeding == []


def test_cancelar_breed_em_andamento_com_racao_falha_e_nao_devolve(c, save):
    save.rations["racao-fofa"] = 1
    start_breed(c, save, M, F, ration="racao-fofa")
    advance_after_run(c, save, Random(1), 3)
    with pytest.raises(IllegalAction):
        cancel_breed(c, save, M, F)
    assert save.rations["racao-fofa"] == 0


def test_cancelar_breed_veloz_apos_uma_run_ja_nasceu_e_nada_a_cancelar(c, save):
    save.rations["racao-veloz"] = 1
    start_breed(c, save, M, F, ration="racao-veloz")
    out = advance_after_run(c, save, Random(1), 3)
    assert out.born and save.breeding == []
    with pytest.raises(IllegalAction):
        cancel_breed(c, save, M, F)


# ------------------------------------------------------------ Escolha: validacao
def test_racao_escolha_exige_a_escolha_do_iv(c, save):
    save.rations["racao-escolha"] = 1
    ok, motivo = can_start_breed(c, save, M, F, ration="racao-escolha")
    assert not ok and motivo
    with pytest.raises(IllegalAction):
        start_breed(c, save, M, F, ration="racao-escolha")
    assert save.rations["racao-escolha"] == 1 and save.breeding == []


def test_escolha_de_iv_com_outra_racao_ou_sem_racao_e_recusada(c, save):
    save.rations["racao-fofa"] = 1
    for r in ("racao-fofa", None):
        ok, _ = can_start_breed(c, save, M, F, ration=r, choice=IvChoice("atk", "father"))
        assert not ok


@pytest.mark.parametrize("stat, parent", [("def", "father"), ("atk", "avo"), ("", "mother")])
def test_iv_choice_invalida_e_recusada(stat, parent):
    with pytest.raises(IllegalAction):
        IvChoice(stat, parent)


def test_racao_escolha_grava_a_escolha_no_casal(c, save):
    save.rations["racao-escolha"] = 1
    start_breed(c, save, M, F, ration="racao-escolha", choice=IvChoice("hp", "mother"))
    assert save.breeding[0]["ration"] == "racao-escolha"
    assert save.breeding[0]["ration_choice"] == {"stat": "hp", "parent": "mother"}
    assert breeding_status(save, c)[0]["choice"] == IvChoice("hp", "mother")


# ------------------------------------------------------------ Veloz
def test_veloz_encurta_o_breed_de_2_para_1_run(c):
    assert initial_runs(c) == 2
    assert initial_runs(c, "racao-veloz") == 1
    assert initial_runs(c, "racao-fofa") == 2 and initial_runs(c, "racao-escolha") == 2


def test_veloz_nunca_leva_o_breed_abaixo_de_1_run(c):
    curto = copy.deepcopy(c)
    curto.rules["breed"]["base_runs"] = 1
    assert initial_runs(curto, "racao-veloz") == 1
    longo = copy.deepcopy(c)
    longo.rules["breed"]["base_runs"] = 5
    assert initial_runs(longo, "racao-veloz") == 4      # reduz exatamente 1


def test_breed_com_veloz_nasce_apos_1_run_e_sem_racao_so_apos_2(c, save):
    save.rations["racao-veloz"] = 1
    start_breed(c, save, M, F, ration="racao-veloz")
    assert save.breeding[0]["runs_left"] == 1
    assert advance_after_run(c, save, Random(2), 1).born
    s2 = build(c, 16)
    start_breed(c, s2, M, F)
    assert advance_after_run(c, s2, Random(2), 1).born == []
    assert advance_after_run(c, s2, Random(2), 1).born


def test_veloz_nao_conta_run_sem_no_vencido(c, save):
    save.rations["racao-veloz"] = 1
    start_breed(c, save, M, F, ration="racao-veloz")
    assert advance_after_run(c, save, Random(2), 0).born == []
    assert save.breeding[0]["runs_left"] == 1


# ------------------------------------------------------------ amostragem
def _pais(c, pai_iv=(2, 5), mae_iv=(4, 1)):
    b = list(c.breeds)
    pai = Cat(id=M, breed=b[0], sex="M", nature="calmo", iv_atk=pai_iv[0], iv_hp=pai_iv[1])
    mae = Cat(id=F, breed=b[1], sex="F", nature="bravo", iv_atk=mae_iv[0], iv_hp=mae_iv[1])
    return pai, mae


def _save_pais(pai, mae) -> SaveData:
    s = SaveData(cats=[copy.copy(pai), copy.copy(mae)])
    s.next_cat_id = 3
    return s


def sortear(c, pai_iv, mae_iv, ration, choice, seed, n=N_NINHADAS):
    """n ninhadas reais (advance_after_run) com seed fixa. Casal pronto: runs_left = 1."""
    pai, mae = _pais(c, pai_iv, mae_iv)
    rng = Random(seed)
    filhotes: list[Cat] = []
    tamanhos: Counter = Counter()
    for _ in range(n):
        s = _save_pais(pai, mae)
        s.breeding = [{"male": M, "female": F, "runs_left": 1, "ration": ration,
                       "ration_choice": None if choice is None
                       else {"stat": choice.stat, "parent": choice.parent}}]
        nascidos = advance_after_run(c, s, rng, 1).born
        tamanhos[len(nascidos)] += 1
        filhotes += nascidos
    return filhotes, tamanhos


CENARIOS = {
    "sem-racao": dict(pai_iv=(2, 5), mae_iv=(4, 1), ration=None, choice=None),
    "fofa": dict(pai_iv=(2, 5), mae_iv=(4, 1), ration="racao-fofa", choice=None),
    "veloz": dict(pai_iv=(2, 5), mae_iv=(4, 1), ration="racao-veloz", choice=None),
    "escolha-atk-pai": dict(pai_iv=(2, 5), mae_iv=(4, 1), ration="racao-escolha",
                            choice=IvChoice("atk", "father")),
    "escolha-hp-mae": dict(pai_iv=(2, 5), mae_iv=(4, 1), ration="racao-escolha",
                           choice=IvChoice("hp", "mother")),
    "teto-5-fofa": dict(pai_iv=(5, 4), mae_iv=(4, 5), ration="racao-fofa", choice=None),
    "teto-5-sem-racao": dict(pai_iv=(5, 5), mae_iv=(5, 4), ration=None, choice=None),
    "pais-iguais": dict(pai_iv=(3, 3), mae_iv=(3, 3), ration=None, choice=None),
}


@lru_cache(maxsize=None)
def amostra(nome: str):
    cfg = CENARIOS[nome]
    c = _content()
    filhotes, tamanhos = sortear(c, cfg["pai_iv"], cfg["mae_iv"], cfg["ration"], cfg["choice"],
                                 seed=hash_estavel(nome))
    return filhotes, tamanhos


def hash_estavel(nome: str) -> int:
    return sum((i + 1) * ord(ch) for i, ch in enumerate(nome))   # nao usa hash() (varia por processo)


def odds_do(c, nome: str):
    cfg = CENARIOS[nome]
    pai, mae = _pais(c, cfg["pai_iv"], cfg["mae_iv"])
    return breed_odds(c, _save_pais(pai, mae), M, F, cfg["ration"], cfg["choice"])


def max_desvio(freq: Counter, probs: dict, n: int) -> tuple[float, float]:
    """(maior desvio |freq - p|, maior tolerancia usada) sobre todo o suporte."""
    pior, tol_pior = 0.0, 0.0
    for chave in set(freq) | set(probs):
        p = probs.get(chave, 0.0)
        obs = freq.get(chave, 0) / n
        tol = max(0.004, 4.5 * math.sqrt(p * (1 - p) / n))
        assert chave in probs or obs == 0, f"resultado {chave!r} fora do suporte das odds"
        if abs(obs - p) > tol:
            return abs(obs - p), tol
        pior = max(pior, abs(obs - p))
        tol_pior = max(tol_pior, tol)
    return pior, tol_pior


def confere(freq: Counter, probs: dict, n: int) -> None:
    desvio, tol = max_desvio(freq, probs, n)
    assert desvio <= tol, f"desvio {desvio:.4f} > tolerancia {tol:.4f}"


ATRIBUTOS = [("breed", "breed"), ("iv_atk", "iv_atk"), ("iv_hp", "iv_hp"), ("sex", "sex"),
             ("nature", "nature")]


@pytest.mark.parametrize("nome", list(CENARIOS))
@pytest.mark.parametrize("campo, atributo", ATRIBUTOS)
def test_odds_batem_com_o_sorteio_real(c, nome, campo, atributo):
    filhotes, _ = amostra(nome)
    odds = odds_do(c, nome)
    freq = Counter(getattr(k, atributo) for k in filhotes)
    confere(freq, getattr(odds, campo), len(filhotes))


@pytest.mark.parametrize("nome", list(CENARIOS))
def test_odds_do_tamanho_da_ninhada_batem_com_o_sorteio_real(c, nome):
    _, tamanhos = amostra(nome)
    odds = odds_do(c, nome)
    confere(tamanhos, odds.litter, N_NINHADAS)
    media = sum(k * v for k, v in tamanhos.items()) / N_NINHADAS
    assert abs(media - odds.litter_expected) < 0.06


def test_sensibilidade_a_tolerancia_distingue_mutacao_de_7_e_15_por_cento(c):
    """Garante que os testes acima pegariam uma previa errada (poder estatistico)."""
    filhotes, _ = amostra("fofa")
    previa_sem_racao = odds_do(c, "sem-racao")
    freq = Counter(k.iv_atk for k in filhotes)
    desvio, tol = max_desvio(freq, previa_sem_racao.iv_atk, len(filhotes))
    assert desvio > tol


# ------------------------------------------------------------ valores exatos (calculados da regra)
def test_odds_sem_racao_valores_exatos(c):
    o = odds_do(c, "sem-racao")                       # ATK pai 2, mae 4; mutacao 7%
    assert o.mutation == pytest.approx(0.07)
    assert o.iv_atk == pytest.approx({2: 0.465, 3: 0.035, 4: 0.465, 5: 0.035})
    b = list(c.breeds)
    assert o.breed == pytest.approx({b[1]: 0.6, b[0]: 0.4})
    assert o.litter == pytest.approx({1: 1 / 3, 2: 1 / 3, 3: 1 / 3})
    assert (o.litter_min, o.litter_max, o.litter_expected) == (1, 3, pytest.approx(2.0))
    assert o.sex == {"M": 0.5, "F": 0.5}
    assert (o.runs, o.runs_without_ration, o.runs_left) == (2, 2, 2)


def test_odds_com_fofa_usam_15_por_cento(c):
    o = odds_do(c, "fofa")
    assert o.mutation == pytest.approx(0.15)
    assert o.iv_atk == pytest.approx({2: 0.425, 3: 0.075, 4: 0.425, 5: 0.075})
    assert o.iv_hp == pytest.approx({1: 0.425, 2: 0.075, 5: 0.5})   # pai 5 (teto), mae 1


def test_odds_com_veloz_mostram_1_run_e_mantem_mutacao_de_7(c):
    o = odds_do(c, "veloz")
    assert (o.runs, o.runs_without_ration) == (1, 2)
    assert o.mutation == pytest.approx(0.07)


def test_odds_com_escolha_fixam_o_iv_com_100_por_cento_e_o_outro_segue_normal(c):
    o = odds_do(c, "escolha-atk-pai")
    assert o.iv_atk == {2: 1.0} and o.fixed == {"atk": 2, "hp": None}
    assert o.iv_hp == pytest.approx({1: 0.465, 2: 0.035, 5: 0.5})
    o2 = odds_do(c, "escolha-hp-mae")
    assert o2.iv_hp == {1: 1.0} and o2.fixed == {"atk": None, "hp": 1}


def test_odds_no_teto_5_a_mutacao_nao_passa_de_5(c):
    o = odds_do(c, "teto-5-fofa")
    assert max(o.iv_atk) == 5 and max(o.iv_hp) == 5
    assert o.iv_atk == pytest.approx({4: 0.425, 5: 0.575})
    o2 = odds_do(c, "teto-5-sem-racao")                   # ATK 5 e 5
    assert o2.iv_atk == pytest.approx({5: 1.0})


def test_escolha_no_pai_com_iv_5_continua_5(c):
    pai, mae = _pais(c, (5, 5), (1, 1))
    o = breed_odds(c, _save_pais(pai, mae), M, F, "racao-escolha", IvChoice("atk", "father"))
    assert o.iv_atk == {5: 1.0}


def test_nenhum_filhote_passa_do_teto_5_em_nenhum_cenario(c):
    for nome in CENARIOS:
        assert all(1 <= k.iv_atk <= 5 and 1 <= k.iv_hp <= 5 for k in amostra(nome)[0])


# ------------------------------------------------------------ probabilidades somam 1
@pytest.mark.parametrize("nome", list(CENARIOS))
def test_todas_as_distribuicoes_das_odds_somam_1(c, nome):
    o = odds_do(c, nome)
    for dist in (o.breed, o.iv_atk, o.iv_hp, o.sex, o.nature, o.litter):
        assert sum(dist.values()) == pytest.approx(1.0, abs=1e-12)
        assert all(0 < p <= 1 for p in dist.values())


@pytest.mark.parametrize("a, b, mut", [(1, 1, 0.07), (1, 5, 0.15), (5, 5, 0.15), (3, 4, 0.0)])
def test_iv_distribution_soma_1_para_qualquer_par(a, b, mut):
    assert sum(iv_distribution(a, b, mut, 5).values()) == pytest.approx(1.0)


def test_pais_com_a_mesma_raca_dao_100_por_cento_dessa_raca(c):
    pai, mae = _pais(c)
    mae.breed = pai.breed
    o = breed_odds(c, _save_pais(pai, mae), M, F)
    assert o.breed == pytest.approx({pai.breed: 1.0})


# ------------------------------------------------------------ pureza
def test_breed_odds_nao_consome_rng_nem_altera_o_save(c, save):
    save.rations["racao-fofa"] = 1
    antes = save_to_dict(save)
    estado = random_global.getstate()
    a = breed_odds(c, save, M, F, "racao-fofa")
    b = breed_odds(c, save, M, F, "racao-fofa")
    assert a == b
    assert random_global.getstate() == estado
    assert save_to_dict(save) == antes             # nem gasta racao, nem abre breed


def test_breed_odds_exige_macho_e_femea(c, save):
    with pytest.raises(IllegalAction):
        breed_odds(c, save, M, cid(3))
    with pytest.raises(IllegalAction):
        breed_odds(c, save, F, M)


def test_breed_odds_valida_a_escolha_como_o_start_breed(c, save):
    with pytest.raises(IllegalAction):
        breed_odds(c, save, M, F, "racao-escolha")
    with pytest.raises(IllegalAction):
        breed_odds(c, save, M, F, "racao-fofa", IvChoice("atk", "father"))


def test_runs_left_da_previa_acompanha_o_casal_ja_aberto(c, save):
    antes = breed_odds(c, save, M, F)
    assert antes.runs_left == antes.runs == 2
    start_breed(c, save, M, F)
    advance_after_run(c, save, Random(4), 1)
    assert breed_odds(c, save, M, F).runs_left == 1


# ------------------------------------------------------------ Escolha: heranca na ninhada toda
@pytest.mark.parametrize("nome, atributo, esperado", [("escolha-atk-pai", "iv_atk", 2),
                                                       ("escolha-hp-mae", "iv_hp", 1)])
def test_escolha_fixa_o_iv_em_toda_a_ninhada_sem_nenhuma_mutacao(nome, atributo, esperado):
    filhotes, _ = amostra(nome)
    assert len(filhotes) > 8000
    assert {getattr(k, atributo) for k in filhotes} == {esperado}


def test_escolha_nao_afeta_o_outro_iv(c):
    filhotes, _ = amostra("escolha-atk-pai")
    freq = Counter(k.iv_hp for k in filhotes)
    confere(freq, {1: 0.465, 2: 0.035, 5: 0.5}, len(filhotes))
