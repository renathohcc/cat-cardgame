"""Historico, linhagem, ordem ao fechar a run e determinismo (Fase 10a, T13.2).

Fonte: especificacao 10a, secao 5 (geracao G1 para adotados, pais + 1; contadores de runs,
duelos vencidos e chefes) e T13.1 item 7 (ordem na UI ao fechar a run)."""
from __future__ import annotations

from random import Random

import pytest
from jsonschema import Draft202012Validator

from core import (adopt, advance_after_run, can_adopt, close_run, create_adoption, donate_offer,
                  get_cat, new_game, new_run_from_save, read_save, save_to_dict, start_breed,
                  write_save, available_cats, set_deck)
from economia_helpers import SAVE_SCHEMA, build, cid, content as _content, finished_run
from sim import balanceamento as B

M, F = cid(1), cid(2)
VALIDATOR = Draft202012Validator(SAVE_SCHEMA)


@pytest.fixture(scope="module")
def c():
    return _content()


@pytest.fixture
def save(c):
    return build(c, 16, breeds_n=1)


def nasce(c, save, seed=3):
    start_breed(c, save, M, F)
    save.breeding[0]["runs_left"] = 1
    return advance_after_run(c, save, Random(seed), 3).born


# ------------------------------------------------------------ geracao e pais
def test_jogo_novo_comeca_todo_mundo_na_geracao_1_sem_pais(c):
    s = new_game(c, Random(1))
    assert all(x.generation == 1 and x.parents == [] for x in s.cats)
    assert all(x.history == {"runs": 0, "duels_won": 0, "bosses_defeated": 0} for x in s.cats)


def test_gato_adotado_e_geracao_1_sem_pais(c, save):
    s = new_game(c, Random(2))
    create_adoption(c, s, Random(2), "vitoria", 4)
    for g in list(s.pending_adoption["cats"]):
        adopted = adopt(c, s, g.id)
        assert adopted.generation == 1 and adopted.parents == []


def test_filhote_de_pais_geracao_1_e_geracao_2_com_os_ids_dos_pais(c, save):
    filhotes = nasce(c, save)
    assert filhotes
    for k in filhotes:
        assert k.generation == 2 and k.parents == [M, F]
        assert k.stage == "kitten"
        assert k.history == {"runs": 0, "duels_won": 0, "bosses_defeated": 0}


@pytest.mark.parametrize("gen_pai, gen_mae", [(1, 3), (3, 1), (2, 2), (5, 4), (4, 7)])
def test_filhote_e_o_maior_geracao_dos_pais_mais_um(c, save, gen_pai, gen_mae):
    get_cat(save, M).generation = gen_pai
    get_cat(save, F).generation = gen_mae
    for k in nasce(c, save):
        assert k.generation == max(gen_pai, gen_mae) + 1


def test_ordem_dos_pais_e_sempre_pai_depois_mae(c, save):
    for k in nasce(c, save, seed=9):
        assert get_cat(save, k.parents[0]).sex == "M" and get_cat(save, k.parents[1]).sex == "F"


def test_neto_e_geracao_3_e_a_geracao_se_mantem_ao_virar_adulto(c, save):
    filhotes = nasce(c, save, seed=4)
    for _ in range(c.rules["breed"]["growth_runs"]):
        advance_after_run(c, save, Random(1), 3)
    crescido = get_cat(save, filhotes[0].id)
    assert crescido.stage == "adult" and crescido.generation == 2
    par = next((x for x in save.cats if x.sex != crescido.sex and x.stage == "adult"
                and x.id not in (crescido.id,) and x.generation == 1), None)
    macho, femea = (crescido, par) if crescido.sex == "M" else (par, crescido)
    set_deck(c, save, [x.id for x in available_cats(save)
                       if x.id not in (macho.id, femea.id)][:12])
    start_breed(c, save, macho.id, femea.id)
    save.breeding[-1]["runs_left"] = 1
    neto = advance_after_run(c, save, Random(5), 3).born
    assert neto and all(k.generation == 3 and k.parents == [macho.id, femea.id] for k in neto)


def test_geracao_e_pais_sobrevivem_a_gravar_e_reler(c, save, tmp_path):
    nasce(c, save)
    p = tmp_path / "s.json"
    write_save(save, p)
    lido = read_save(p, c)
    assert [(k.id, k.generation, k.parents) for k in lido.cats] == \
        [(k.id, k.generation, k.parents) for k in save.cats]


# ------------------------------------------------------------ historico dos gatos do deck
def test_fechar_run_soma_duelos_e_chefes_a_todos_os_gatos_do_deck(c, save):
    close_run(c, save, finished_run(c, save, {"batalha": 2, "elite": 1, "chefe": 1}, "vitoria"))
    for gid in save.deck:
        h = get_cat(save, gid).history
        assert h == {"runs": 1, "duels_won": 4, "bosses_defeated": 1}


def test_gatos_fora_do_deck_nao_recebem_historico(c, save):
    close_run(c, save, finished_run(c, save, {"batalha": 2}, "derrota"))
    fora = [x for x in save.cats if x.id not in save.deck]
    assert fora and all(x.history == {"runs": 0, "duels_won": 0, "bosses_defeated": 0}
                        for x in fora)


def test_historico_acumula_em_varias_runs(c, save):
    close_run(c, save, finished_run(c, save, {"batalha": 1}, "derrota"))
    close_run(c, save, finished_run(c, save, {"batalha": 3, "chefe": 1}, "vitoria"))
    h = get_cat(save, save.deck[0]).history
    assert h == {"runs": 2, "duels_won": 5, "bosses_defeated": 1}
    assert save.lifetime == {"runs_completed": 2, "duels_won": 5}


def test_lifetime_soma_runs_e_duelos_vencidos(c, save):
    close_run(c, save, finished_run(c, save, {"batalha": 2, "elite": 1}, "derrota"))
    assert save.lifetime == {"runs_completed": 1, "duels_won": 3}


def test_anti_farm_run_sem_no_vencido_nao_conta(c, save):
    run = new_run_from_save(c, save, Random(1))
    run.abandon()
    r = close_run(c, save, run)
    assert not r.counted
    assert save.lifetime == {"runs_completed": 0, "duels_won": 0}
    assert all(get_cat(save, g).history["runs"] == 0 for g in save.deck)


def test_anti_farm_run_sem_no_vencido_nao_avanca_breed_nem_crescimento(c, save):
    start_breed(c, save, M, F)
    close_run(c, save, finished_run(c, save, {}, "derrota", nodes=0))
    out = advance_after_run(c, save, Random(1), 0)
    assert out.born == [] and out.grown == [] and save.breeding[0]["runs_left"] == 2


def test_run_so_com_descanso_conta_como_run_mas_nao_paga_nem_soma_duelo(c, save):
    """Descanso vencido e um no concluido (min_nodes_for_run_count = 1): a run conta."""
    r = close_run(c, save, finished_run(c, save, {}, "derrota", nodes=1))
    assert r.counted and save.coins == 0
    assert save.lifetime == {"runs_completed": 1, "duels_won": 0}


def test_historico_e_lifetime_persistem_no_arquivo(c, save, tmp_path):
    close_run(c, save, finished_run(c, save, {"batalha": 2, "chefe": 1}, "vitoria"))
    p = tmp_path / "s.json"
    write_save(save, p)
    lido = read_save(p, c)
    assert lido.lifetime == save.lifetime and lido.coins == save.coins
    assert get_cat(lido, save.deck[0]).history == get_cat(save, save.deck[0]).history
    assert lido.first_league_win_claimed is True


@pytest.mark.parametrize("seed", range(4))
def test_run_real_da_ia_credita_exatamente_os_duelos_que_venceu(c, seed):
    s = new_game(c, Random(seed))
    rng = Random(50 + seed)
    run = new_run_from_save(c, s, rng)
    B.jogar_run(c, rng, run)
    close_run(c, s, run)
    total = sum(run.wins.values())
    assert s.lifetime["duels_won"] == total
    for gid in s.deck:
        assert get_cat(s, gid).history["duels_won"] == total
        assert get_cat(s, gid).history["bosses_defeated"] == run.wins.get("chefe", 0)


# ------------------------------------------------------------ ordem ao fechar a run
def fechar(c, s, run, rng, caminho):
    """Fluxo documentado da UI: close_run -> advance_after_run -> create_adoption -> 1 write."""
    r = close_run(c, s, run)
    aft = advance_after_run(c, s, rng, run.nodes_cleared)
    create_adoption(c, s, rng, run.result, run.nodes_cleared)
    write_save(s, caminho)
    return r, aft


def test_fluxo_de_fim_de_run_deixa_um_unico_arquivo_coerente(c, tmp_path):
    s = new_game(c, Random(7))
    s.breeding = []
    extra = build(c, 16)
    s.cats, s.deck, s.next_cat_id = extra.cats, extra.deck, 17
    start_breed(c, s, M, F)
    s.breeding[0]["runs_left"] = 1
    run = finished_run(c, s, {"batalha": 3, "elite": 1, "chefe": 1}, "vitoria")
    eco = c.rules["economy"]
    p = tmp_path / "save.json"
    r, aft = fechar(c, s, run, Random(8), p)
    lido = read_save(p, c)
    assert save_to_dict(lido) == save_to_dict(s)
    assert list(VALIDATOR.iter_errors(save_to_dict(lido))) == []
    assert lido.coins == r.coins == 3 * eco["coins_battle_node"] + eco["coins_elite_node"] + eco["coins_boss_node"] + eco["league1_first_win_bonus"]
    assert aft.born and lido.pending_adoption is not None
    assert lido.prestige == 2


def test_filhotes_recebem_id_antes_do_gato_da_oferta_de_adocao(c, tmp_path):
    """Ordem importa: nascimento (advance) antes de create_adoption => ids dos filhotes menores."""
    s = build(c, 16)
    start_breed(c, s, M, F)
    s.breeding[0]["runs_left"] = 1
    run = finished_run(c, s, {"batalha": 3, "chefe": 1}, "vitoria")
    _, aft = fechar(c, s, run, Random(3), tmp_path / "s.json")
    ids_filhotes = [int(k.id[2:]) for k in aft.born]
    ids_oferta = [int(g.id[2:]) for g in s.pending_adoption["cats"]]
    assert ids_filhotes and ids_oferta and max(ids_filhotes) < min(ids_oferta)


def test_fluxo_de_run_sem_no_vencido_nao_gera_oferta_nem_moedas(c, tmp_path):
    s = build(c, 16)
    run = finished_run(c, s, {}, "derrota", nodes=0)
    r, aft = fechar(c, s, run, Random(3), tmp_path / "s.json")
    assert r.coins == 0 and not r.counted
    assert s.pending_adoption is None and aft.born == []


def test_pais_em_breed_nao_recebem_historico_da_run_que_nao_jogaram(c, save):
    """Os pais saem do deck ao abrir o breed: nao jogaram a run, nao ganham historico."""
    start_breed(c, save, M, F)
    assert M not in save.deck
    save.breeding[0]["runs_left"] = 1
    close_run(c, save, finished_run(c, save, {"batalha": 1}, "derrota"))
    assert get_cat(save, M).history["runs"] == 0          # nao estava no deck
    assert all(get_cat(save, g).history["runs"] == 1 for g in save.deck)


# ------------------------------------------------------------ carreira e determinismo
def carreira(c, seed: int, n_runs: int = 6) -> dict:
    """n runs com IA e o fluxo completo (breed, adocao com gatil cheio doando o novo)."""
    rng = Random(seed)
    s = new_game(c, rng)
    for _ in range(n_runs):
        if not s.breeding:
            m = next((x for x in available_cats(s) if x.sex == "M"), None)
            f = next((x for x in available_cats(s) if x.sex == "F"), None)
            if m and f and len(available_cats(s)) - 2 >= 12:
                start_breed(c, s, m.id, f.id)
        set_deck(c, s, [x.id for x in available_cats(s)][:12])
        run = new_run_from_save(c, s, rng)
        B.jogar_run(c, rng, run)
        close_run(c, s, run)
        advance_after_run(c, s, rng, run.nodes_cleared)
        create_adoption(c, s, rng, run.result, run.nodes_cleared)
        for g in list(s.pending_adoption["cats"] if s.pending_adoption else []):
            if can_adopt(c, s)[0]:
                adopt(c, s, g.id, enforce_capacity=True)
            else:
                donate_offer(c, s, g.id)
        assert list(VALIDATOR.iter_errors(save_to_dict(s))) == []
        assert s.coins >= 0
    return save_to_dict(s)


def test_mesma_seed_gera_exatamente_o_mesmo_save_apos_varias_runs(c):
    assert carreira(c, 21) == carreira(c, 21)


def test_seeds_diferentes_geram_saves_diferentes(c):
    assert carreira(c, 21) != carreira(c, 22)


def test_carreira_mantem_os_invariantes_do_save_v2(c):
    d = carreira(c, 5, n_runs=8)
    assert d["schema_version"] == 2
    ids = [x["id"] for x in d["cats"]]
    assert len(ids) == len(set(ids))
    assert d["lifetime"]["runs_completed"] <= 8
    assert all(x["generation"] >= 1 for x in d["cats"])
    assert all(len(x["parents"]) in (0, 2) for x in d["cats"])
