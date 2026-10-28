"""Colecao e deck: rename_cat, available_cats, set_deck, autofill_deck, new_run(cats)."""
from __future__ import annotations

import copy
from collections import Counter
from pathlib import Path
from random import Random

import pytest

from core import (Cat, autofill_deck, available_cats, cat_stats, load_content, new_game,
                  new_run, new_run_from_save, rename_cat, roll_cat, save_to_dict, set_deck)
from core.ai import choose_action
from core.duel import apply_action
from core.types import IllegalAction

DATA = Path(__file__).resolve().parent.parent / "data"


@pytest.fixture(scope="module")
def content():
    return load_content(DATA)


@pytest.fixture
def save(content):
    return new_game(content, Random(3))


def ids(s):
    return [c.id for c in s.cats]


def extra_cat(content, save, seed=99):
    """Adiciona um gato adulto extra a colecao."""
    c = roll_cat(content, Random(seed + save.next_cat_id))
    c.id = f"c-{save.next_cat_id:06d}"
    save.next_cat_id += 1
    save.cats.append(c)
    return c


# ------------------------------------------------------------ rename_cat
def test_renomear_aceita_16_caracteres_exatos(save):
    rename_cat(save, save.cats[0].id, "a" * 16)
    assert save.cats[0].name == "a" * 16


def test_renomear_17_caracteres_e_erro_e_nao_altera(save):
    with pytest.raises(IllegalAction):
        rename_cat(save, save.cats[0].id, "a" * 17)
    assert save.cats[0].name is None


def test_renomear_faz_strip(save):
    rename_cat(save, save.cats[0].id, "  Mingau  ")
    assert save.cats[0].name == "Mingau"


def test_strip_vale_antes_do_limite(save):
    rename_cat(save, save.cats[0].id, "  " + "a" * 16 + "  ")
    assert save.cats[0].name == "a" * 16


@pytest.mark.parametrize("valor", ["", "   ", None])
def test_renomear_vazio_ou_none_volta_ao_padrao(save, valor):
    cid = save.cats[0].id
    rename_cat(save, cid, "Mingau")
    rename_cat(save, cid, valor)
    assert save.cats[0].name is None
    assert "name" not in save_to_dict(save)["cats"][0]


def test_renomear_com_acentos(save):
    rename_cat(save, save.cats[0].id, "Pãozinho Ç")
    assert save.cats[0].name == "Pãozinho Ç"


@pytest.mark.parametrize("valor", [123, 1.5, ["a"], b"abc", True])
def test_renomear_nao_string_e_erro(save, valor):
    with pytest.raises(IllegalAction):
        rename_cat(save, save.cats[0].id, valor)


def test_renomear_id_inexistente_e_erro(save):
    with pytest.raises(IllegalAction):
        rename_cat(save, "c-999999", "X")


def test_nome_nao_precisa_ser_unico(save):
    rename_cat(save, save.cats[0].id, "Igual")
    rename_cat(save, save.cats[1].id, "Igual")
    assert save.cats[0].name == save.cats[1].name == "Igual"


def test_renomear_nao_muda_status_nem_ids(content, save):
    antes = [(c.id, cat_stats(content, c)) for c in save.cats]
    rename_cat(save, save.cats[0].id, "Novo", content)
    assert [(c.id, cat_stats(content, c)) for c in save.cats] == antes


def test_renomear_le_limite_de_rules_meta(content, save):
    assert content.rules["meta"]["name_max_length"] == 16
    c2 = copy.copy(content)
    c2.rules = {**content.rules, "meta": {"name_max_length": 5}}
    rename_cat(save, save.cats[0].id, "12345", c2)
    with pytest.raises(IllegalAction):
        rename_cat(save, save.cats[0].id, "123456", c2)


# ------------------------------------------------------------ available_cats
def test_disponiveis_exclui_filhote_e_descanso(save):
    save.cats[0].stage = "kitten"
    save.cats[1].rest_runs_left = 2
    disp = [c.id for c in available_cats(save)]
    assert save.cats[0].id not in disp and save.cats[1].id not in disp
    assert len(disp) == 10


def test_disponiveis_inclui_quem_acabou_o_descanso(save):
    save.cats[1].rest_runs_left = 1
    assert len(available_cats(save)) == 11
    save.cats[1].rest_runs_left = 0
    assert len(available_cats(save)) == 12


# ------------------------------------------------------------ set_deck
def test_set_deck_ok(content, save):
    extra = extra_cat(content, save)
    novo = ids(save)[1:12] + [extra.id]
    set_deck(content, save, novo)
    assert save.deck == novo


@pytest.mark.parametrize("n", [0, 11, 13])
def test_set_deck_tamanho_errado_e_erro(content, save, n):
    extra_cat(content, save)
    antes = list(save.deck)
    with pytest.raises(IllegalAction):
        set_deck(content, save, ids(save)[:n])
    assert save.deck == antes


def test_set_deck_repetido_e_erro(content, save):
    with pytest.raises(IllegalAction):
        set_deck(content, save, ids(save)[:11] + [ids(save)[0]])


def test_set_deck_filhote_e_erro(content, save):
    extra = extra_cat(content, save)
    extra.stage = "kitten"
    with pytest.raises(IllegalAction):
        set_deck(content, save, ids(save)[1:12] + [extra.id])


def test_set_deck_em_descanso_e_erro(content, save):
    extra = extra_cat(content, save)
    extra.rest_runs_left = 1
    with pytest.raises(IllegalAction):
        set_deck(content, save, ids(save)[1:12] + [extra.id])


def test_set_deck_inexistente_e_erro(content, save):
    with pytest.raises(IllegalAction):
        set_deck(content, save, ids(save)[:11] + ["c-999999"])


# ------------------------------------------------------------ autofill_deck
def test_autofill_completa_ate_12_mantendo_escolhidos(content, save):
    for _ in range(4):
        extra_cat(content, save)
    pick = [ids(save)[0], ids(save)[5]]
    r = autofill_deck(content, save, pick)
    assert len(r) == 12 and len(set(r)) == 12
    assert r[:2] == pick


def test_autofill_escolhe_os_maiores_atk_vezes_hp(content, save):
    # 3 gatos por raca no maximo (15), IVs variados: o limite por raca nao interfere
    especs = ["vira-lata", "siames", "persa", "sphynx", "maine-coon"] * 3
    cats = colecao(content, save, especs)
    for i, c in enumerate(cats):
        c.iv_atk, c.iv_hp = 1 + i % 5, 1 + (i * 2) % 5
    r = autofill_deck(content, save, [cats[0].id])

    def prod(c):
        s = cat_stats(content, c)
        return s.atk * s.hp

    escolhidos = [c for c in cats if c.id in r[1:]]
    fora = [c for c in cats if c.id not in r]
    assert r[0] == cats[0].id and len(r) == 12
    assert min(prod(c) for c in escolhidos) >= max(prod(c) for c in fora)


def test_autofill_desempate_por_id_e_deterministico(content, save):
    for _ in range(4):
        extra_cat(content, save)
    base = save.cats[0]
    for c in save.cats:
        c.breed, c.nature, c.iv_atk, c.iv_hp = base.breed, base.nature, 3, 3
    r1 = autofill_deck(content, save, [])
    r2 = autofill_deck(content, save, [])
    assert r1 == r2 == sorted(ids(save))[:12]


def test_autofill_nao_altera_o_save(content, save):
    for _ in range(3):
        extra_cat(content, save)
    antes = copy.deepcopy(save_to_dict(save))
    autofill_deck(content, save, [ids(save)[2]])
    assert save_to_dict(save) == antes


def test_autofill_sem_gatos_suficientes_e_erro(content, save):
    save.cats[0].stage = "kitten"
    with pytest.raises(IllegalAction):
        autofill_deck(content, save, [])


def test_autofill_com_escolhido_indisponivel_e_erro(content, save):
    save.cats[0].rest_runs_left = 1
    with pytest.raises(IllegalAction):
        autofill_deck(content, save, [save.cats[0].id])


def test_autofill_com_mais_de_12_e_erro(content, save):
    for _ in range(2):
        extra_cat(content, save)
    with pytest.raises(IllegalAction):
        autofill_deck(content, save, ids(save)[:13])


# ------------------------------------------------------------ cat_stats
def test_cat_stats_positivos_e_nome_nao_interfere(content, save):
    c = save.cats[0]
    antes = cat_stats(content, c)
    assert antes.atk > 0 and antes.hp > 0
    rename_cat(save, c.id, "Bola")
    assert cat_stats(content, c) == antes


# ------------------------------------------------------------ new_run
def test_new_run_from_save_usa_mesmos_ids_e_nomes(content, save):
    rename_cat(save, save.cats[0].id, "Mingau")
    r = new_run_from_save(content, save, Random(1))
    assert [c.id for c in r.cats] == save.deck
    assert r.cats[0].name == "Mingau"


def test_new_run_usa_copias_da_colecao(content, save):
    r = new_run_from_save(content, save, Random(1))
    r.cats[0].name = "Alterado"
    r.cats[0].iv_atk = 5 if save.cats[0].iv_atk != 5 else 1
    assert r.cats[0] is not save.cats[0]
    assert save.cats[0].name is None
    assert r.cats[0].iv_atk != save.cats[0].iv_atk


def test_new_run_com_cats_nao_consome_rng(content, save):
    rng = Random(5)
    estado = rng.getstate()
    new_run(content, rng, cats=list(save.cats))
    assert rng.getstate() == estado


def test_new_run_sem_cats_mantem_comportamento_antigo(content):
    r1 = new_run(content, Random(4))
    r2 = new_run(content, Random(4))
    assert [c.id for c in r1.cats] == [f"run-{i}" for i in range(1, 13)]
    assert [(c.breed, c.iv_atk) for c in r1.cats] == [(c.breed, c.iv_atk) for c in r2.cats]


def test_new_run_deck_com_tamanho_errado_e_erro(content, save):
    with pytest.raises(IllegalAction):
        new_run(content, Random(1), cats=save.cats[:11])


def test_new_run_deck_repetido_e_erro(content, save):
    with pytest.raises(IllegalAction):
        new_run(content, Random(1), cats=save.cats[:11] + [save.cats[0]])


def test_new_run_deck_com_filhote_ou_descanso_e_erro(content, save):
    save.cats[0].stage = "kitten"
    with pytest.raises(IllegalAction):
        new_run(content, Random(1), cats=list(save.cats))
    save.cats[0].stage = "adult"
    save.cats[0].rest_runs_left = 1
    with pytest.raises(IllegalAction):
        new_run(content, Random(1), cats=list(save.cats))


def test_new_run_from_save_com_deck_invalido_e_erro(content, save):
    save.deck = save.deck[:11]
    with pytest.raises(IllegalAction):
        new_run_from_save(content, save, Random(1))
    save.deck = save.deck + ["c-999999"]
    with pytest.raises(IllegalAction):
        new_run_from_save(content, save, Random(1))


def test_run_nao_altera_o_save(content, save):
    antes = copy.deepcopy(save_to_dict(save))
    r = new_run_from_save(content, save, Random(1))
    r.cats.clear()
    assert save_to_dict(save) == antes


def _terminar_run(r, seed):
    rng = Random(seed)
    for _ in range(100):
        if r.status == "finished":
            return
        if r.status == "map":
            r.choose_node(rng.choice(r.available_nodes())["id"])
        elif r.status == "duel":
            d = r.start_duel(Random(rng.randrange(2**31)))
            for _ in range(4000):
                if d.winner is not None:
                    break
                apply_action(d, choose_action(d, d.turn_side, Random(rng.randrange(2**31))))
            else:
                raise AssertionError("duelo nao terminou")
            r.finish_duel(d)
        else:
            r.pick_draft(rng.randrange(len(r.draft_options)))
    raise AssertionError("run nao terminou")


@pytest.mark.parametrize("seed", range(5))
def test_run_completa_com_deck_da_colecao_e_ia(content, seed):
    s = new_game(content, Random(seed))
    antes = copy.deepcopy(save_to_dict(s))
    r = new_run_from_save(content, s, Random(seed))
    _terminar_run(r, seed)
    assert r.status == "finished" and r.result in ("vitoria", "derrota")
    assert save_to_dict(s) == antes


# ------------------------------------------------------------ autofill: limite por raca
def colecao(content, save, specs, ids_reversos=False):
    """Troca a colecao por gatos adultos IV 3/3, natureza bravo. specs: lista de racas."""
    n = len(specs)
    cats = []
    for i, breed in enumerate(specs):
        k = n - i if ids_reversos else i + 1
        cats.append(Cat(id=f"c-{k:06d}", breed=breed, sex="M", nature="bravo",
                        iv_atk=3, iv_hp=3))
    save.cats = cats
    save.deck = []
    save.next_cat_id = n + 1
    return cats


def racas(save, deck):
    por_id = {c.id: c.breed for c in save.cats}
    return Counter(por_id[i] for i in deck)


ESPEC_MC = (["maine-coon"] * 8 + ["vira-lata"] * 3 + ["persa"] * 3
            + ["sphynx"] * 3 + ["siames"] * 3)


def test_autofill_limita_a_3_por_raca_mesmo_com_raca_dominante(content, save):
    colecao(content, save, ESPEC_MC)
    r = autofill_deck(content, save, [])
    assert len(r) == 12 and len(set(r)) == 12
    assert racas(save, r)["maine-coon"] == 3
    assert max(racas(save, r).values()) <= 3


def test_autofill_conta_os_escolhidos_no_limite(content, save):
    colecao(content, save, ESPEC_MC)
    mcs = [c.id for c in save.cats if c.breed == "maine-coon"]
    r = autofill_deck(content, save, mcs[:2])
    assert r[:2] == mcs[:2]
    assert racas(save, r)["maine-coon"] == 3      # 2 escolhidos + 1


def test_autofill_escolhidos_acima_do_limite_sao_mantidos_sem_somar_mais(content, save):
    colecao(content, save, ESPEC_MC)
    mcs = [c.id for c in save.cats if c.breed == "maine-coon"]
    r = autofill_deck(content, save, mcs[:5])
    assert r[:5] == mcs[:5]
    assert racas(save, r)["maine-coon"] == 5


def test_autofill_so_ultrapassa_o_limite_se_faltarem_gatos(content, save):
    colecao(content, save, ["maine-coon"] * 7 + ["vira-lata"] * 3 + ["persa"] * 2)
    r = autofill_deck(content, save, [])
    assert sorted(r) == sorted(ids(save))
    assert racas(save, r)["maine-coon"] == 7


def test_autofill_excedente_segue_atk_vezes_hp_e_depois_id(content, save):
    colecao(content, save, ["maine-coon"] * 6 + ["vira-lata"] * 6 + ["persa"] * 2)
    r = autofill_deck(content, save, [])
    assert len(r) == 12
    c = racas(save, r)
    assert c["persa"] == 2 and c["maine-coon"] + c["vira-lata"] == 10
    # primeiros 8: 3 de cada uma das tres racas dentro do limite (2 persa)
    dentro = set(r[:8])
    assert racas(save, list(dentro)) == Counter({"maine-coon": 3, "vira-lata": 3, "persa": 2})
    # os 4 do excedente sao os de maior ATK*HP (maine-coon) e depois menor id
    extra = r[8:]
    mc_fora = sorted(i.id for i in save.cats if i.breed == "maine-coon" and i.id not in dentro)
    assert extra[:3] == mc_fora
    assert extra[3] == min(i.id for i in save.cats
                           if i.breed == "vira-lata" and i.id not in dentro)


def test_autofill_limite_desempata_por_menor_id_dentro_da_raca(content, save):
    colecao(content, save, ["maine-coon"] * 6 + ["vira-lata"] * 6 + ["persa"] * 4,
            ids_reversos=True)
    r = autofill_deck(content, save, [])
    mc = sorted(c.id for c in save.cats if c.breed == "maine-coon")
    assert [i for i in r if i in mc][:3] == mc[:3]
    assert r == autofill_deck(content, save, [])


def test_autofill_sem_chave_no_content_usa_limite_3(content, save):
    colecao(content, save, ESPEC_MC)
    esperado = autofill_deck(content, save, [])
    c2 = copy.deepcopy(content)
    c2.rules["meta"].pop("max_per_breed_autofill", None)
    assert autofill_deck(c2, save, []) == esperado


@pytest.mark.parametrize("limite", [2, 4])
def test_autofill_respeita_limite_configurado_no_content(content, save, limite):
    colecao(content, save, ESPEC_MC)
    c2 = copy.deepcopy(content)
    c2.rules["meta"]["max_per_breed_autofill"] = limite
    r = autofill_deck(c2, save, [])
    assert len(r) == 12
    if limite == 4:
        assert racas(save, r)["maine-coon"] == 4 and max(racas(save, r).values()) <= 4
    else:
        # 5 racas x 2 = 10 < 12: ultrapassa so o necessario, dando preferencia a maior ATK*HP
        assert racas(save, r)["maine-coon"] == 4
        assert all(racas(save, r)[b] >= 2 for b in set(ESPEC_MC))


def test_autofill_com_limite_nao_altera_o_save(content, save):
    colecao(content, save, ESPEC_MC)
    antes = copy.deepcopy(save_to_dict(save))
    autofill_deck(content, save, [])
    assert save_to_dict(save) == antes
