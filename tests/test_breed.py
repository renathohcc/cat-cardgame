"""Breed e filhotes (Fase 5c): can_breed, start_breed, advance_after_run, ninhada, heranca,
dex, deck, doacao, cancel_breed, save e simulacao longa.

Fonte: regras do Renatho de 2026-10-28 e CONTRATOS 1.9 / 2.5 (so a API publica).
Todo sorteio usa Random com seed fixa.
"""
from __future__ import annotations

import copy
import json
from collections import Counter
from pathlib import Path
from random import Random

import pytest
from jsonschema import Draft202012Validator

from core import (Cat, SaveData, adopt, advance_after_run, autofill_deck, available_cats,
                  breeding_status, cancel_breed, can_breed, can_donate, create_adoption,
                  donate_cat, donation_value, get_cat, load_content, rename_cat,
                  save_deck_draft, save_from_dict, save_to_dict, set_deck, start_breed,
                  write_save, read_save)
from core.types import IllegalAction

DATA = Path(__file__).resolve().parent.parent / "data"
SCHEMA = json.loads((DATA / "schemas" / "save.schema.json").read_text("utf-8"))


@pytest.fixture(scope="module")
def content():
    return load_content(DATA)


# ------------------------------------------------------------------ helpers
def cid(n: int) -> str:
    return f"c-{n:06d}"


def build(content, n: int = 16) -> SaveData:
    """n adultos; impares = machos, pares = femeas; deck = os 12 primeiros.
    Casal padrao: c-000001 (M) e c-000002 (F), ambos no deck."""
    breeds, natures = list(content.breeds), list(content.natures)
    s = SaveData()
    for i in range(1, n + 1):
        s.cats.append(Cat(id=cid(i), breed=breeds[i % len(breeds)], sex="M" if i % 2 else "F",
                          nature=natures[i % len(natures)], iv_atk=3, iv_hp=3))
    s.next_cat_id = n + 1
    s.deck = [c.id for c in s.cats][:12]
    return s


M, F = cid(1), cid(2)


def couple_save(content, father_breed=None, mother_breed=None, father_iv=(3, 3),
                mother_iv=(3, 3), n: int = 16) -> SaveData:
    s = build(content, n)
    father, mother = get_cat(s, M), get_cat(s, F)
    if father_breed:
        father.breed = father_breed
    if mother_breed:
        mother.breed = mother_breed
    father.iv_atk, father.iv_hp = father_iv
    mother.iv_atk, mother.iv_hp = mother_iv
    return s


def run_breed(content, s: SaveData, rng: Random):
    """Inicia M+F e passa 2 runs validas. Devolve o RunAftermath da 2a."""
    start_breed(content, s, M, F)
    advance_after_run(content, s, rng, 1)
    return advance_after_run(content, s, rng, 1)


def litter(content, seed: int, **kw) -> list[Cat]:
    s = couple_save(content, **kw)
    return run_breed(content, s, Random(seed)).born


def adults_ids(s: SaveData) -> set[str]:
    return {c.id for c in s.cats if c.stage == "adult"}


# ------------------------------------------------------------------ can_breed
def test_can_breed_casal_valido(content):
    assert can_breed(content, build(content), M, F) == (True, "")


def test_can_breed_ordem_importa_macho_depois_femea(content):
    ok, motivo = can_breed(content, build(content), F, M)
    assert not ok and motivo


def test_can_breed_recusa_mesmo_sexo(content):
    s = build(content)
    for a, b in ((cid(1), cid(3)), (cid(2), cid(4))):
        ok, motivo = can_breed(content, s, a, b)
        assert not ok and isinstance(motivo, str) and motivo


def test_can_breed_recusa_mesmo_gato(content):
    ok, motivo = can_breed(content, build(content), M, M)
    assert not ok and motivo


def test_can_breed_recusa_filhote(content):
    s = build(content)
    get_cat(s, F).stage = "kitten"
    ok, motivo = can_breed(content, s, M, F)
    assert not ok and motivo


def test_can_breed_recusa_gato_em_descanso(content):
    s = build(content)
    get_cat(s, M).rest_runs_left = 1
    ok, motivo = can_breed(content, s, M, F)
    assert not ok and motivo


def test_can_breed_recusa_gato_que_ja_esta_em_casal(content):
    s = build(content)
    start_breed(content, s, M, F)
    # macho 1 repetido com outra femea; femea 2 repetida com outro macho
    assert not can_breed(content, s, M, cid(4))[0]
    assert not can_breed(content, s, cid(3), F)[0]
    assert can_breed(content, s, cid(3), cid(4))[0]


def test_can_breed_recusa_se_sobrar_menos_de_12_adultos_disponiveis(content):
    assert can_breed(content, build(content, 14), M, F)[0]      # 14 - 2 = 12
    ok, motivo = can_breed(content, build(content, 13), M, F)   # 13 - 2 = 11
    assert not ok and motivo
    ok, motivo = can_breed(content, build(content, 12), M, F)
    assert not ok and motivo


def test_can_breed_filhote_e_gato_em_descanso_nao_contam_como_disponiveis(content):
    s = build(content, 14)
    s.cats.append(Cat(id=cid(15), breed="siames", sex="F", nature="calmo",
                      iv_atk=1, iv_hp=1, stage="kitten"))
    s.cats[4].rest_runs_left = 1
    s.next_cat_id = 16
    assert not can_breed(content, s, M, F)[0]


def test_can_breed_recusa_gato_inexistente(content):
    s = build(content)
    for a, b in ((cid(99), F), (M, cid(98)), (cid(97), cid(98))):
        ok, motivo = can_breed(content, s, a, b)
        assert not ok and motivo


def test_can_breed_mensagens_diferentes_para_motivos_diferentes(content):
    s = build(content)
    msgs = {can_breed(content, s, cid(1), cid(3))[1], can_breed(content, s, M, M)[1],
            can_breed(content, s, M, cid(99))[1], can_breed(content, build(content, 13), M, F)[1]}
    assert len(msgs) >= 3 and all(isinstance(m, str) and m for m in msgs)


def test_can_breed_nao_altera_o_save(content):
    s = build(content)
    antes = save_to_dict(s)
    can_breed(content, s, M, F)
    can_breed(content, s, M, M)
    assert save_to_dict(s) == antes


# ------------------------------------------------------------------ start_breed
def test_start_breed_tira_os_pais_do_deck(content):
    s = build(content)
    assert M in s.deck and F in s.deck
    start_breed(content, s, M, F)
    assert M not in s.deck and F not in s.deck
    assert len(s.deck) == 10


def test_start_breed_registra_runs_left_2(content):
    s = build(content)
    start_breed(content, s, M, F)
    assert s.breeding == [{"male": M, "female": F, "runs_left": 2}]


def test_start_breed_atualiza_breeding_status(content):
    s = build(content)
    assert breeding_status(s) == []
    start_breed(content, s, M, F)
    st = breeding_status(s)
    assert len(st) == 1
    assert st[0]["male"].id == M and st[0]["female"].id == F and st[0]["runs_left"] == 2


def test_start_breed_pais_deixam_de_estar_disponiveis(content):
    s = build(content)
    start_breed(content, s, M, F)
    ids = {c.id for c in available_cats(s)}
    assert M not in ids and F not in ids and len(ids) == 14


def test_start_breed_invalido_levanta_e_nao_muda_o_save(content):
    s = build(content)
    antes = save_to_dict(s)
    for a, b in ((cid(1), cid(3)), (M, M), (M, cid(99)), (F, M)):
        with pytest.raises(IllegalAction):
            start_breed(content, s, a, b)
    assert save_to_dict(s) == antes


def test_start_breed_com_poucos_adultos_levanta_e_nao_muda_o_save(content):
    s = build(content, 13)
    antes = save_to_dict(s)
    with pytest.raises(IllegalAction):
        start_breed(content, s, M, F)
    assert save_to_dict(s) == antes


def test_dois_casais_simultaneos_com_16_adultos(content):
    s = build(content, 16)
    start_breed(content, s, M, F)
    start_breed(content, s, cid(3), cid(4))
    assert len(s.breeding) == 2
    assert not can_breed(content, s, cid(5), cid(6))[0]  # sobrariam 10


# ------------------------------------------------------------------ advance_after_run
def test_abandono_sem_no_vencido_nao_avanca_breed(content):
    s = build(content)
    start_breed(content, s, M, F)
    out = advance_after_run(content, s, Random(1), 0)
    assert s.breeding[0]["runs_left"] == 2
    assert out.born == [] and out.grown == [] and out.couples_done == []


def test_abandono_sem_no_vencido_nao_envelhece_filhote(content):
    s = build(content)
    s.cats.append(Cat(id=cid(17), breed="siames", sex="M", nature="calmo", iv_atk=2,
                      iv_hp=2, stage="kitten", runs_as_kitten=1))
    s.next_cat_id = 18
    out = advance_after_run(content, s, Random(1), 0)
    assert get_cat(s, cid(17)).stage == "kitten" and get_cat(s, cid(17)).runs_as_kitten == 1
    assert out.grown == []


def test_um_no_vencido_ja_conta_a_run(content):
    s = build(content)
    start_breed(content, s, M, F)
    out = advance_after_run(content, s, Random(1), 1)
    assert s.breeding[0]["runs_left"] == 1
    assert out.born == []


def test_duas_runs_validas_fazem_nascer_a_ninhada(content):
    s = build(content)
    n0 = len(s.cats)
    out = run_breed(content, s, Random(5))
    assert 1 <= len(out.born) <= 3
    assert len(s.cats) == n0 + len(out.born)
    assert out.couples_done == [(M, F)]
    assert s.breeding == []
    assert all(k.stage == "kitten" and k.runs_as_kitten == 0 for k in out.born)
    assert all(get_cat(s, k.id) is k for k in out.born)


def test_run_com_0_nos_entre_duas_validas_nao_conta(content):
    s = build(content)
    start_breed(content, s, M, F)
    rng = Random(2)
    advance_after_run(content, s, rng, 1)
    assert advance_after_run(content, s, rng, 0).born == []
    assert s.breeding[0]["runs_left"] == 1
    assert len(advance_after_run(content, s, rng, 3).born) >= 1


def test_recem_nascidos_nao_envelhecem_na_mesma_chamada(content):
    s = build(content)
    out = run_breed(content, s, Random(7))
    assert out.grown == []
    assert all(k.runs_as_kitten == 0 and k.stage == "kitten" for k in out.born)


def test_filhote_vira_adulto_na_segunda_run_apos_nascer(content):
    s = build(content)
    rng = Random(8)
    born = run_breed(content, s, rng).born
    r1 = advance_after_run(content, s, rng, 1)
    assert r1.grown == [] and all(k.stage == "kitten" and k.runs_as_kitten == 1 for k in born)
    r2 = advance_after_run(content, s, rng, 1)
    assert {k.id for k in r2.grown} == {k.id for k in born}
    assert all(k.stage == "adult" for k in born)


def test_filhote_crescido_vira_disponivel_e_pode_ir_ao_deck(content):
    s = build(content)
    rng = Random(9)
    born = run_breed(content, s, rng).born
    advance_after_run(content, s, rng, 1)
    advance_after_run(content, s, rng, 1)
    assert {k.id for k in born} <= {c.id for c in available_cats(s)}
    set_deck(content, s, [c.id for c in available_cats(s)][-12:])


def test_runs_zero_nos_nao_fazem_filhote_crescer_apos_nascer(content):
    s = build(content)
    rng = Random(10)
    born = run_breed(content, s, rng).born
    for _ in range(5):
        advance_after_run(content, s, rng, 0)
    assert all(k.stage == "kitten" for k in born)


def test_couples_done_com_dois_casais_na_mesma_run(content):
    s = build(content, 16)
    start_breed(content, s, M, F)
    start_breed(content, s, cid(3), cid(4))
    rng = Random(11)
    advance_after_run(content, s, rng, 2)
    out = advance_after_run(content, s, rng, 2)
    assert sorted(out.couples_done) == [(M, F), (cid(3), cid(4))]
    assert len(out.born) >= 2 and s.breeding == []


def test_casais_com_inicios_diferentes_nascem_em_runs_diferentes(content):
    s = build(content, 16)
    rng = Random(12)
    start_breed(content, s, M, F)
    advance_after_run(content, s, rng, 1)
    start_breed(content, s, cid(3), cid(4))
    out = advance_after_run(content, s, rng, 1)
    assert out.couples_done == [(M, F)]
    assert len(s.breeding) == 1 and s.breeding[0]["runs_left"] == 1
    out2 = advance_after_run(content, s, rng, 1)
    assert out2.couples_done == [(cid(3), cid(4))]


def test_apos_nascer_pais_voltam_disponiveis_mas_nao_ao_deck(content):
    s = build(content)
    run_breed(content, s, Random(13))
    ids = {c.id for c in available_cats(s)}
    assert M in ids and F in ids
    assert M not in s.deck and F not in s.deck
    assert len(available_cats(s)) == 16


def test_pais_podem_formar_novo_casal_apos_nascer(content):
    s = build(content)
    run_breed(content, s, Random(14))
    assert can_breed(content, s, M, F)[0]


def test_advance_sem_breed_nem_filhote_nao_faz_nada(content):
    s = build(content)
    antes = save_to_dict(s)
    out = advance_after_run(content, s, Random(1), 4)
    assert (out.born, out.grown, out.couples_done) == ([], [], [])
    assert save_to_dict(s) == antes


# ------------------------------------------------------------------ ninhada
def test_ninhada_distribuicao_1_2_3_aproximadamente_uniforme(content):
    cnt = Counter()
    for seed in range(3000):
        cnt[len(litter(content, seed))] += 1
    assert set(cnt) == {1, 2, 3}
    for n in (1, 2, 3):
        assert abs(cnt[n] - 1000) <= 120, cnt


# ------------------------------------------------------------------ raca
def test_raca_do_filhote_60_mae_40_pai(content):
    breeds = list(content.breeds)
    mae, pai = breeds[0], breeds[1]
    cnt = Counter()
    for seed in range(1500):
        for k in litter(content, seed, father_breed=pai, mother_breed=mae):
            cnt[k.breed] += 1
    total = sum(cnt.values())
    assert set(cnt) == {mae, pai}
    assert abs(cnt[mae] / total - 0.6) < 0.03, cnt


def test_pais_da_mesma_raca_geram_so_essa_raca(content):
    raca = list(content.breeds)[2]
    for seed in range(200):
        assert {k.breed for k in litter(content, seed, father_breed=raca,
                                        mother_breed=raca)} == {raca}


# ------------------------------------------------------------------ sexo e natureza
def test_sexo_do_filhote_50_50(content):
    cnt = Counter()
    for seed in range(1500):
        for k in litter(content, seed):
            cnt[k.sex] += 1
    total = sum(cnt.values())
    assert set(cnt) == {"M", "F"}
    assert abs(cnt["M"] / total - 0.5) < 0.03, cnt


def test_natureza_sempre_valida_e_todas_aparecem(content):
    cnt = Counter()
    for seed in range(600):
        for k in litter(content, seed):
            cnt[k.nature] += 1
    assert set(cnt) == set(content.natures)


# ------------------------------------------------------------------ IV
def sem_mutacao(content):
    c = copy.deepcopy(content)
    c.rules["breed"]["mutation_chance"] = 0
    return c


def test_iv_herdado_so_dos_pais_sem_mutacao(content):
    c0 = sem_mutacao(content)
    vistos_atk, vistos_hp = Counter(), Counter()
    for seed in range(600):
        s = couple_save(c0, father_iv=(1, 2), mother_iv=(4, 5))
        for k in run_breed(c0, s, Random(seed)).born:
            vistos_atk[k.iv_atk] += 1
            vistos_hp[k.iv_hp] += 1
    assert set(vistos_atk) == {1, 4}
    assert set(vistos_hp) == {2, 5}
    total = sum(vistos_atk.values())
    assert abs(vistos_atk[1] / total - 0.5) < 0.05


def test_iv_atk_e_hp_herdam_de_forma_independente(content):
    c0 = sem_mutacao(content)
    combos = set()
    for seed in range(400):
        s = couple_save(c0, father_iv=(1, 2), mother_iv=(4, 5))
        for k in run_breed(c0, s, Random(seed)).born:
            combos.add((k.iv_atk, k.iv_hp))
    assert combos == {(1, 2), (1, 5), (4, 2), (4, 5)}


def test_pais_com_iv_igual_sem_mutacao_geram_filhote_com_o_mesmo_iv(content):
    c0 = sem_mutacao(content)
    for seed in range(100):
        s = couple_save(c0, father_iv=(2, 3), mother_iv=(2, 3))
        for k in run_breed(c0, s, Random(seed)).born:
            assert (k.iv_atk, k.iv_hp) == (2, 3)


def test_mutacao_acontece_cerca_de_7_por_cento(content):
    mut = n = 0
    for seed in range(2500):
        for k in litter(content, seed, father_iv=(1, 1), mother_iv=(1, 1)):
            for iv in (k.iv_atk, k.iv_hp):
                n += 1
                assert iv in (1, 2)           # so +1
                mut += iv == 2
    assert abs(mut / n - 0.07) < 0.012, (mut, n)


def test_mutacao_nunca_passa_de_5(content):
    for seed in range(800):
        for k in litter(content, seed, father_iv=(5, 5), mother_iv=(5, 5)):
            assert (k.iv_atk, k.iv_hp) == (5, 5)
    for seed in range(800):
        for k in litter(content, seed, father_iv=(4, 5), mother_iv=(5, 4)):
            assert 1 <= k.iv_atk <= 5 and 1 <= k.iv_hp <= 5


def test_mutacao_total_100_por_cento_soma_1_com_teto(content):
    c1 = copy.deepcopy(content)
    c1.rules["breed"]["mutation_chance"] = 1
    for seed in range(50):
        s = couple_save(c1, father_iv=(2, 5), mother_iv=(2, 5))
        for k in run_breed(c1, s, Random(seed)).born:
            assert (k.iv_atk, k.iv_hp) == (3, 5)


# ------------------------------------------------------------------ ids
def test_ids_novos_unicos_e_next_cat_id_avanca(content):
    s = build(content, 16)
    antes = {c.id for c in s.cats}
    nid = s.next_cat_id
    start_breed(content, s, M, F)
    start_breed(content, s, cid(3), cid(4))
    rng = Random(21)
    advance_after_run(content, s, rng, 1)
    out = advance_after_run(content, s, rng, 1)
    novos = [k.id for k in out.born]
    assert len(set(novos)) == len(novos) and not (set(novos) & antes)
    assert s.next_cat_id == nid + len(novos)
    assert novos == [cid(nid + i) for i in range(len(novos))]
    assert len({c.id for c in s.cats}) == len(s.cats)


def test_dois_nascimentos_seguidos_nao_repetem_id(content):
    s = build(content, 16)
    rng = Random(22)
    run_breed(content, s, rng)
    run_breed(content, s, rng)
    assert len({c.id for c in s.cats}) == len(s.cats)


# ------------------------------------------------------------------ dex
def test_dex_registra_raca_do_filhote(content):
    s = couple_save(content, father_breed="persa", mother_breed="persa")
    s.dex = {"breeds_seen": [], "perfect_cats": []}
    run_breed(content, s, Random(31))
    assert s.dex["breeds_seen"] == ["persa"]


def test_dex_registra_gato_perfeito_5_5(content):
    s = couple_save(content, father_iv=(5, 5), mother_iv=(5, 5))
    s.dex = {"breeds_seen": [], "perfect_cats": []}
    born = run_breed(content, s, Random(32)).born
    assert sorted(s.dex["perfect_cats"]) == sorted(k.id for k in born)


def test_dex_nao_registra_perfeito_para_filhote_imperfeito(content):
    c0 = sem_mutacao(content)
    s = couple_save(c0, father_iv=(5, 4), mother_iv=(4, 4))
    s.dex = {"breeds_seen": [], "perfect_cats": []}
    run_breed(c0, s, Random(33))
    assert s.dex["perfect_cats"] == []


def test_dex_sem_duplicatas_apos_varias_ninhadas(content):
    s = couple_save(content, father_breed="persa", mother_breed="persa",
                    father_iv=(5, 5), mother_iv=(5, 5))
    s.dex = {"breeds_seen": [], "perfect_cats": []}
    rng = Random(34)
    for _ in range(3):
        run_breed(content, s, rng)
    assert s.dex["breeds_seen"] == ["persa"]
    assert len(s.dex["perfect_cats"]) == len(set(s.dex["perfect_cats"]))


# ------------------------------------------------------------------ determinismo
def test_mesma_seed_gera_mesma_ninhada(content):
    a = [save_to_dict(couple_save(content)) for _ in range(1)][0]
    sa, sb = save_from_dict(a), save_from_dict(a)
    ra = run_breed(content, sa, Random(40))
    rb = run_breed(content, sb, Random(40))
    assert ra.born == rb.born
    assert save_to_dict(sa) == save_to_dict(sb)


def test_seeds_diferentes_geram_ninhadas_diferentes(content):
    resultados = {tuple((k.breed, k.sex, k.nature, k.iv_atk, k.iv_hp)
                        for k in litter(content, seed)) for seed in range(30)}
    assert len(resultados) > 5


# ------------------------------------------------------------------ deck e colecao
def com_filhote(content):
    s = build(content)
    rng = Random(50)
    born = run_breed(content, s, rng).born
    return s, born[0]


def test_set_deck_recusa_filhote(content):
    s, kit = com_filhote(content)
    ids = [c.id for c in available_cats(s)][:11] + [kit.id]
    with pytest.raises(IllegalAction):
        set_deck(content, s, ids)


def test_save_deck_draft_recusa_filhote(content):
    s, kit = com_filhote(content)
    with pytest.raises(IllegalAction):
        save_deck_draft(s, [kit.id], content)


def test_autofill_recusa_filhote_escolhido_e_nunca_o_inclui(content):
    s, kit = com_filhote(content)
    with pytest.raises(IllegalAction):
        autofill_deck(content, s, [kit.id])
    deck = autofill_deck(content, s, [])
    assert len(deck) == 12 and kit.id not in deck


def test_set_deck_e_autofill_recusam_gato_em_breed(content):
    s = build(content)
    start_breed(content, s, M, F)
    ids = [c.id for c in available_cats(s)][:11] + [M]
    with pytest.raises(IllegalAction):
        set_deck(content, s, ids)
    with pytest.raises(IllegalAction):
        save_deck_draft(s, [F], content)
    with pytest.raises(IllegalAction):
        autofill_deck(content, s, [M])
    assert not ({M, F} & set(autofill_deck(content, s, [])))


# ------------------------------------------------------------------ doacao e nome
def test_doar_filhote_rende_metade(content):
    s = build(content)
    kit = Cat(id=cid(17), breed="siames", sex="F", nature="calmo", iv_atk=4, iv_hp=4,
              stage="kitten")
    adulto = Cat(id=cid(18), breed="siames", sex="F", nature="calmo", iv_atk=4, iv_hp=4)
    s.cats += [kit, adulto]
    s.next_cat_id = 19
    valor_adulto = donation_value(content, adulto)
    assert valor_adulto > 0
    assert donation_value(content, kit) == int(valor_adulto * 0.5)
    assert can_donate(content, s, kit.id)[0]
    coins = s.coins
    assert donate_cat(content, s, kit.id) == int(valor_adulto * 0.5)
    assert s.coins == coins + int(valor_adulto * 0.5)
    assert all(c.id != kit.id for c in s.cats)


def test_nao_doa_gato_em_breed(content):
    s = build(content)
    start_breed(content, s, M, F)
    ok, motivo = can_donate(content, s, M)
    assert not ok and motivo
    with pytest.raises(IllegalAction):
        donate_cat(content, s, F)


def test_renomear_filhote(content):
    s, kit = com_filhote(content)
    rename_cat(s, kit.id, "Mingau", content)
    assert get_cat(s, kit.id).name == "Mingau"
    s2 = save_from_dict(save_to_dict(s), content)
    assert get_cat(s2, kit.id).name == "Mingau" and get_cat(s2, kit.id).stage == "kitten"


# ------------------------------------------------------------------ cancel_breed
def test_cancel_breed_ok_antes_de_qualquer_run(content):
    s = build(content)
    start_breed(content, s, M, F)
    cancel_breed(content, s, M, F)
    assert s.breeding == [] and breeding_status(s) == []
    assert M not in s.deck and F not in s.deck           # nao volta ao deck
    assert {M, F} <= {c.id for c in available_cats(s)}


def test_cancel_breed_ok_apos_run_sem_nos_vencidos(content):
    s = build(content)
    start_breed(content, s, M, F)
    advance_after_run(content, s, Random(1), 0)
    cancel_breed(content, s, M, F)
    assert s.breeding == []


def test_cancel_breed_recusado_depois_de_uma_run_valida(content):
    s = build(content)
    start_breed(content, s, M, F)
    advance_after_run(content, s, Random(1), 2)
    antes = save_to_dict(s)
    with pytest.raises(IllegalAction):
        cancel_breed(content, s, M, F)
    assert save_to_dict(s) == antes


def test_cancel_breed_casal_inexistente(content):
    with pytest.raises(IllegalAction):
        cancel_breed(content, build(content), M, F)


# ------------------------------------------------------------------ save
def save_com_breed_e_filhotes(content) -> SaveData:
    s = build(content, 18)
    rng = Random(60)
    run_breed(content, s, rng)                      # filhotes nascidos
    start_breed(content, s, cid(3), cid(4))        # casal em andamento
    advance_after_run(content, s, rng, 1)
    return s


def test_round_trip_do_save_com_breeding_e_filhotes(content, tmp_path):
    s = save_com_breed_e_filhotes(content)
    assert s.breeding and any(c.stage == "kitten" for c in s.cats)
    d = save_to_dict(s)
    assert save_to_dict(save_from_dict(json.loads(json.dumps(d)), content)) == d
    p = tmp_path / "save.json"
    write_save(s, p)
    assert save_to_dict(read_save(p, content)) == d


def test_save_com_breeding_e_filhotes_valida_no_schema(content):
    d = save_to_dict(save_com_breed_e_filhotes(content))
    erros = list(Draft202012Validator(SCHEMA).iter_errors(d))
    assert erros == [], [e.message for e in erros]


def test_save_com_filhote_na_oferta_e_rejeitado_pelo_schema(content):
    s = build(content)
    kit = Cat(id=cid(17), breed="siames", sex="F", nature="calmo", iv_atk=2, iv_hp=2,
              stage="kitten", runs_as_kitten=1)
    s.next_cat_id = 18
    s.pending_adoption = {"cats": [kit], "result": "derrota", "nodes_cleared": 1}
    d = save_to_dict(s)
    assert list(Draft202012Validator(SCHEMA).iter_errors(d)) != []


def test_save_com_filhote_na_oferta_round_trip(content):
    s = build(content)
    s.next_cat_id = 18
    s.pending_adoption = {"cats": [Cat(id=cid(17), breed="siames", sex="F", nature="calmo",
                                        iv_atk=2, iv_hp=2, stage="kitten")],
                          "result": "derrota", "nodes_cleared": 1}
    d = save_to_dict(s)
    with pytest.raises(ValueError):
        save_from_dict(d, content)


def _dict_base(content) -> dict:
    s = build(content)
    start_breed(content, s, M, F)
    return save_to_dict(s)


def test_save_base_com_casal_e_valido(content):
    save_from_dict(_dict_base(content), content)


def _invalida(content, mutacao):
    d = _dict_base(content)
    mutacao(d)
    with pytest.raises(ValueError):
        save_from_dict(d, content)


def test_save_invalido_casal_com_sexos_iguais(content):
    _invalida(content, lambda d: d["breeding"][0].update(female=cid(3)))   # M + M
    _invalida(content, lambda d: d["breeding"][0].update(male=cid(4)))     # F + F


def test_save_invalido_casal_com_sexos_trocados(content):
    _invalida(content, lambda d: d["breeding"][0].update(male=F, female=M))


def test_save_invalido_gato_em_dois_casais(content):
    _invalida(content, lambda d: d["breeding"].append(
        {"male": M, "female": cid(4), "runs_left": 2}))
    _invalida(content, lambda d: d["breeding"].append(
        {"male": cid(3), "female": F, "runs_left": 2}))


def test_save_invalido_filhote_no_casal(content):
    def f(d):
        for c in d["cats"]:
            if c["id"] == F:
                c["stage"] = "kitten"
    _invalida(content, f)


def test_save_invalido_id_inexistente_no_casal(content):
    _invalida(content, lambda d: d["breeding"][0].update(male=cid(99)))
    _invalida(content, lambda d: d["breeding"][0].update(female=cid(99)))


def test_save_invalido_runs_left_negativo(content):
    _invalida(content, lambda d: d["breeding"][0].update(runs_left=-1))


def test_save_invalido_casal_malformado(content):
    _invalida(content, lambda d: d["breeding"][0].pop("runs_left"))


def test_save_invalido_filhote_no_deck(content):
    def f(d):
        d["cats"][-1]["stage"] = "kitten"
        d["deck"][-1] = d["cats"][-1]["id"]
    d = build(content)
    d.cats[-1].id  # garante que existe
    dd = save_to_dict(d)
    f(dd)
    with pytest.raises(ValueError):
        save_from_dict(dd, content)


# ------------------------------------------------------------------ simulacao longa
def _invariantes(content, s: SaveData) -> None:
    ids = [c.id for c in s.cats]
    assert len(ids) == len(set(ids))
    emcasal = [i for b in s.breeding for i in (b["male"], b["female"])]
    assert len(emcasal) == len(set(emcasal))
    por_id = {c.id: c for c in s.cats}
    for b in s.breeding:
        assert por_id[b["male"]].sex == "M" and por_id[b["female"]].sex == "F"
        assert b["runs_left"] >= 0
    disp = {c.id for c in available_cats(s)}
    assert set(s.deck) <= disp
    assert len(s.deck) == len(set(s.deck)) and len(s.deck) <= 12
    assert len(disp) >= 12           # o jogador sempre consegue montar 12 e iniciar run
    assert all(por_id[i].stage == "adult" for i in s.deck)
    assert not (set(emcasal) & set(s.deck))
    assert all(int(n[2:]) < s.next_cat_id for n in ids)
    assert save_to_dict(save_from_dict(save_to_dict(s), content)) == save_to_dict(s)


def test_simulacao_de_50_runs_com_adocao_e_breed_mantem_invariantes(content):
    rng = Random(2024)
    s = SaveData()
    from core import new_game
    s = new_game(content, rng)
    nascidos = crescidos = 0
    for run in range(50):
        _invariantes(content, s)
        s.deck = autofill_deck(content, s, [])       # monta e "inicia" a run
        assert len(s.deck) == 12
        nos = rng.choice([0, 0, 1, 2, 3, 4, 5])
        resultado = "vitoria" if nos >= 4 else "derrota"
        out = advance_after_run(content, s, rng, nos)
        nascidos += len(out.born)
        crescidos += len(out.grown)
        create_adoption(content, s, rng, resultado, nos)
        while s.pending_adoption:
            pend = s.pending_adoption["cats"][0]
            adopt(content, s, pend.id)
        _invariantes(content, s)
        # doa filhotes/adultos excedentes de vez em quando
        for c in list(s.cats):
            if rng.random() < 0.15 and can_donate(content, s, c.id)[0] \
                    and c.id not in s.deck:
                donate_cat(content, s, c.id)
        _invariantes(content, s)
        # tenta iniciar breed com um casal valido
        machos = [c for c in available_cats(s) if c.sex == "M"]
        femeas = [c for c in available_cats(s) if c.sex == "F"]
        rng.shuffle(machos)
        rng.shuffle(femeas)
        for m in machos[:2]:
            for f in femeas[:2]:
                if can_breed(content, s, m.id, f.id)[0]:
                    start_breed(content, s, m.id, f.id)
                    break
        _invariantes(content, s)
    assert nascidos > 0 and crescidos > 0, (nascidos, crescidos)


# ------------------------------------------------------------------ deck x casal (T5.23)
def _deck_e_casal(content, gato_no_deck: str) -> dict:
    """Casal valido M+F (fora do deck) e depois forca `gato_no_deck` de volta ao deck."""
    s = build(content)
    start_breed(content, s, M, F)
    d = save_to_dict(s)
    d["deck"] = [gato_no_deck] + [i for i in d["deck"] if i != gato_no_deck][:11]
    return d


@pytest.mark.parametrize("gato", [M, F], ids=["macho", "femea"])
def test_save_com_gato_do_casal_no_deck_e_rejeitado_citando_criatorio(content, gato):
    d = _deck_e_casal(content, gato)
    with pytest.raises(ValueError, match="criatorio"):
        save_from_dict(d, content)


def test_save_valido_com_pais_fora_do_deck_carrega(content):
    s = build(content)
    start_breed(content, s, M, F)
    assert M not in s.deck and F not in s.deck
    carregado = save_from_dict(save_to_dict(s), content)
    assert carregado.breeding and M not in carregado.deck and F not in carregado.deck


def test_start_breed_real_seguido_de_write_read_nunca_gera_deck_com_casal(content, tmp_path):
    s = build(content)
    start_breed(content, s, M, F)
    p = tmp_path / "save.json"
    write_save(s, p)
    lido = read_save(p, content)
    emcasal = {i for b in lido.breeding for i in (b["male"], b["female"])}
    assert emcasal == {M, F}
    assert not (emcasal & set(lido.deck))


def test_breed_cfg_importavel_de_core():
    from core import breed_cfg
    assert callable(breed_cfg) or breed_cfg is not None
