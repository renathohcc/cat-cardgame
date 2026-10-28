"""Mini-run (T4.4a): dados, new_run, fluxo, serializacao e propriedade.

Fonte: PLAN.md Fase 4 (decisoes do Renatho) e reports/T4.1/T4.2 (so a API publica).
"""
from __future__ import annotations

import copy
import json
import shutil
import sys
import time
from pathlib import Path
from random import Random

import pytest
from jsonschema import Draft202012Validator

from core import Run, load_content, new_run
from core.ai import choose_action
from core.duel import apply_action
from core.types import IllegalAction

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from data import validate_data as vd  # noqa: E402

DECK = 12
MAX_ACOES = 4000


def _json(name: str):
    return json.loads((DATA / name).read_text("utf-8"))


EFFECTS = {e["id"] for e in _json("effects.json")["effects"]}
SPECIALS = {e["id"] for e in _json("specials.json")["specials"]}
POOL = EFFECTS | SPECIALS
CAMINHO_ELITE = ["c1-batalha", "c2-batalha", "c3-batalha"]


@pytest.fixture(scope="module")
def content():
    return load_content(DATA)


def play_ai(duel, rng):
    for _ in range(MAX_ACOES):
        if duel.winner is not None:
            return
        apply_action(duel, choose_action(duel, duel.turn_side, rng))
    raise AssertionError("duelo nao terminou")


def forced(run, winner, seed=1):
    """Inicia o duelo e fixa o vencedor (atalho para testar so o fluxo da run)."""
    d = run.start_duel(Random(seed))
    d.winner = winner
    run.finish_duel(d)
    return d


def fresh(content, seed=1):
    return new_run(content, Random(seed))


def _ate_camada(r, nodes):
    for nid in nodes:
        r.choose_node(nid)
        if r.status == "duel":
            forced(r, "player")
        _pick_todos(r)


def _pick_todos(r):
    while r.status == "draft":
        r.pick_draft(0)


def _ate_chefe(r):
    _ate_camada(r, CAMINHO_ELITE + ["c4-batalha", "c5-descanso"])
    assert r.layer == 5


# ---------------------------------------------------------------- 1. dados
def test_run_json_valida_no_schema():
    schema = _json("schemas/run.schema.json")
    assert list(Draft202012Validator(schema).iter_errors(_json("run.json"))) == []


def test_mapa_tem_6_camadas_e_ultima_e_um_chefe():
    layers = _json("run.json")["map"]["layers"]
    assert len(layers) == 6
    assert len(layers[-1]["nodes"]) == 1 and layers[-1]["nodes"][0]["tipo"] == "chefe"


def test_ids_de_no_unicos_e_inimigos_existem_com_tipo_certo():
    enemies = {e["id"]: e["tipo"] for e in _json("enemies.json")["enemies"]}
    ids = []
    for layer in _json("run.json")["map"]["layers"]:
        for n in layer["nodes"]:
            ids.append(n["id"])
            if n["tipo"] == "descanso":
                assert n["inimigo"] is None
            else:
                assert enemies[n["inimigo"]] == n["tipo"]
    assert len(ids) == len(set(ids))


def test_start_deck_igual_ao_tamanho_do_deck_das_regras():
    assert _json("run.json")["start_deck"]["gatos"] == _json("rules.json")["duel"]["deck_size"]


def _docs():
    errs, docs = vd.check_schemas()
    assert errs == 0
    return copy.deepcopy(docs)


def test_validate_data_aceita_run_real(capsys):
    assert vd.check_run(_docs()) == 0


def test_validate_data_rejeita_inimigo_inexistente(capsys):
    docs = _docs()
    docs["run"]["map"]["layers"][0]["nodes"][0]["inimigo"] = "nao-existe"
    assert vd.check_run(docs) >= 1


def test_validate_data_rejeita_camada_final_com_dois_nos(capsys):
    docs = _docs()
    docs["run"]["map"]["layers"][-1]["nodes"].append(
        {"id": "extra-chefe", "tipo": "chefe", "inimigo": "madame-fifi-pelucia"})
    assert vd.check_run(docs) >= 1


def test_validate_data_rejeita_start_deck_diferente_do_deck_size(capsys):
    docs = _docs()
    docs["run"]["start_deck"]["gatos"] = 11
    assert vd.check_run(docs) >= 1


def test_validate_data_rejeita_tipo_que_nao_bate_com_o_inimigo(capsys):
    docs = _docs()
    docs["run"]["map"]["layers"][0]["nodes"][0]["tipo"] = "elite"
    assert vd.check_run(docs) >= 1


def test_validate_data_rejeita_id_de_no_repetido(capsys):
    docs = _docs()
    docs["run"]["map"]["layers"][2]["nodes"][0]["id"] = "c1-batalha"
    assert vd.check_run(docs) >= 1


# ---------------------------------------------------------------- 2. new_run
def test_new_run_sorteia_12_gatos_adultos(content):
    r = fresh(content)
    assert len(r.cats) == DECK
    assert all(c.stage == "adult" for c in r.cats)
    assert len({c.id for c in r.cats}) == DECK
    assert r.cards == [] and r.status == "map" and r.result is None
    assert r.nodes_cleared == 0 and r.deck_size() == DECK


def test_new_run_e_deterministico_pela_seed(content):
    assert fresh(content, 7).cats == fresh(content, 7).cats


def test_new_run_seeds_diferentes_dao_decks_diferentes(content):
    assert fresh(content, 1).cats != fresh(content, 2).cats


def test_new_run_falha_se_deck_size_diferente_do_start_deck(tmp_path):
    d = tmp_path / "data"
    shutil.copytree(DATA, d)
    rules = json.loads((d / "rules.json").read_text("utf-8"))
    rules["duel"]["deck_size"] = 10
    (d / "rules.json").write_text(json.dumps(rules), "utf-8")
    with pytest.raises(ValueError):
        new_run(load_content(d), Random(1))


def test_new_run_sem_run_json_levanta_erro(tmp_path):
    d = tmp_path / "data"
    shutil.copytree(DATA, d)
    (d / "run.json").unlink()
    with pytest.raises(ValueError):
        new_run(load_content(d), Random(1))


# ---------------------------------------------------------------- 3. fluxo
def test_primeira_camada_so_tem_a_batalha_inicial(content):
    r = fresh(content)
    assert [n["id"] for n in r.available_nodes()] == ["c1-batalha"]


def test_choose_node_fora_da_camada_levanta_illegal(content):
    r = fresh(content)
    with pytest.raises(IllegalAction):
        r.choose_node("c4-elite")
    with pytest.raises(IllegalAction):
        r.choose_node("nao-existe")
    assert r.status == "map"


def test_acoes_fora_de_estado_levantam_illegal(content):
    r = fresh(content)
    with pytest.raises(IllegalAction):
        r.start_duel(Random(1))
    with pytest.raises(IllegalAction):
        r.pick_draft(0)


def test_camada_2_oferece_batalha_ou_descanso(content):
    r = fresh(content)
    _ate_camada(r, ["c1-batalha"])
    assert r.status == "map"
    assert {n["id"] for n in r.available_nodes()} == {"c2-batalha", "c2-descanso"}


def test_camada_4_oferece_elite_ou_batalha(content):
    r = fresh(content)
    _ate_camada(r, CAMINHO_ELITE)
    assert {n["id"] for n in r.available_nodes()} == {"c4-elite", "c4-batalha"}


def test_start_duel_usa_o_deck_da_run_com_cartas_escolhidas(content):
    r = fresh(content)
    r.choose_node("c1-batalha")
    forced(r, "player")
    escolhida = r.draft_options[0]
    r.pick_draft(0)
    r.choose_node("c2-batalha")
    d = r.start_duel(Random(3))
    assert len(d.sides["player"].initial_deck) == DECK + 1
    assert r.cards == [escolhida]


def test_vitoria_abre_draft_com_3_opcoes_distintas_do_pool(content):
    r = fresh(content)
    r.choose_node("c1-batalha")
    forced(r, "player")
    assert r.status == "draft"
    assert len(r.draft_options) == 3 and len(set(r.draft_options)) == 3
    assert set(r.draft_options) <= POOL


def test_draft_sorteia_efeitos_e_espiritos_ao_longo_de_varias_telas(content):
    vistos = set()
    for seed in range(40):
        r = fresh(content, seed)
        r.choose_node("c1-batalha")
        forced(r, "player")
        vistos |= set(r.draft_options)
    assert vistos & EFFECTS and vistos & SPECIALS


def test_derrota_encerra_a_run(content):
    r = fresh(content)
    r.choose_node("c1-batalha")
    forced(r, "enemy")
    assert r.status == "finished" and r.result == "derrota"
    assert r.draft_options == [] and r.available_nodes() == []
    assert r.nodes_cleared == 0


def test_pick_draft_adiciona_carta_e_deck_cresce_alem_de_12(content):
    r = fresh(content)
    gatos = [c.id for c in r.cats]
    r.choose_node("c1-batalha")
    forced(r, "player")
    op = r.draft_options[1]
    assert r.pick_draft(1) == op
    assert r.cards == [op] and r.deck_size() == DECK + 1
    assert [c.id for c in r.cats] == gatos
    assert r.status == "map" and r.layer == 1


def test_os_12_gatos_nunca_saem_do_deck_ao_longo_da_run(content):
    r = fresh(content)
    gatos = [c.id for c in r.cats]
    _ate_chefe(r)
    assert [c.id for c in r.cats] == gatos
    assert len(r.cards) == 5 and r.deck_size() == DECK + 5


def test_pick_draft_indice_invalido_levanta_illegal(content):
    r = fresh(content)
    r.choose_node("c1-batalha")
    forced(r, "player")
    for i in (3, -1, 99):
        with pytest.raises(IllegalAction):
            r.pick_draft(i)
    assert r.status == "draft" and r.cards == []


def test_descanso_abre_draft_extra_sem_batalha(content):
    r = fresh(content)
    _ate_camada(r, ["c1-batalha"])
    r.choose_node("c2-descanso")
    assert r.status == "draft" and r.duel is None
    assert len(r.draft_options) == 2 and len(set(r.draft_options)) == 2
    r.pick_draft(0)
    assert len(r.cards) == 2 and r.layer == 2 and r.nodes_cleared == 2


def test_nodes_cleared_conta_a_distancia(content):
    r = fresh(content)
    assert r.nodes_cleared == 0
    _ate_camada(r, ["c1-batalha"])
    assert r.nodes_cleared == 1
    _ate_camada(r, ["c2-batalha"])
    assert r.nodes_cleared == 2


def test_derrota_mantem_nodes_cleared_ja_conquistado(content):
    r = fresh(content)
    _ate_camada(r, ["c1-batalha"])
    r.choose_node("c2-batalha")
    forced(r, "enemy")
    assert r.nodes_cleared == 1 and r.result == "derrota"


def test_elite_usa_draft_options_elite(content):
    c2 = copy.deepcopy(content)
    c2.run["draft_options_elite"] = 5
    r = new_run(c2, Random(1))
    _ate_camada(r, CAMINHO_ELITE)
    r.choose_node("c4-elite")
    forced(r, "player")
    assert len(r.draft_options) == 5 and len(set(r.draft_options)) == 5


def test_batalha_comum_nao_usa_draft_options_elite(content):
    c2 = copy.deepcopy(content)
    c2.run["draft_options_elite"] = 5
    r = new_run(c2, Random(1))
    _ate_camada(r, CAMINHO_ELITE)
    r.choose_node("c4-batalha")
    forced(r, "player")
    assert len(r.draft_options) == 3


def test_vitoria_no_chefe_termina_sem_draft(content):
    r = fresh(content)
    _ate_chefe(r)
    r.choose_node("c6-chefe")
    forced(r, "player")
    assert r.status == "finished" and r.result == "vitoria"
    assert r.draft_options == []
    assert r.nodes_cleared == 6


def test_derrota_no_chefe_e_derrota(content):
    r = fresh(content)
    _ate_chefe(r)
    r.choose_node("c6-chefe")
    forced(r, "enemy")
    assert r.status == "finished" and r.result == "derrota"


def test_finish_duel_sem_vencedor_levanta_illegal(content):
    r = fresh(content)
    r.choose_node("c1-batalha")
    d = r.start_duel(Random(1))
    with pytest.raises(IllegalAction):
        r.finish_duel(d)


def test_start_duel_duas_vezes_levanta_illegal(content):
    r = fresh(content)
    r.choose_node("c1-batalha")
    r.start_duel(Random(1))
    with pytest.raises(IllegalAction):
        r.start_duel(Random(2))


def test_duelo_seguinte_recomeca_do_zero_apos_duelo_jogado_pela_ia(content):
    r = fresh(content, 2)
    r.choose_node("c1-batalha")
    d1 = r.start_duel(Random(5))
    play_ai(d1, Random(6))
    d1.winner = "player"  # garante o fluxo de vitoria; o duelo ja foi disputado de verdade
    r.finish_duel(d1)
    r.pick_draft(0)
    r.choose_node("c2-batalha")
    d2 = r.start_duel(Random(9))
    p, e = d2.sides["player"], d2.sides["enemy"]
    assert p.leader_hp == p.leader_hp_max == _json("rules.json")["duel"]["leader_hp"]
    assert e.leader_hp == e.leader_hp_max
    assert d2.winner is None
    assert len(p.initial_deck) == DECK + 1
    assert len(p.deck) + len(p.hand) + sum(1 for s in p.field if s) == DECK + 1


def test_lider_do_chefe_tem_25_de_hp(content):
    r = fresh(content)
    _ate_chefe(r)
    r.choose_node("c6-chefe")
    d = r.start_duel(Random(1))
    assert d.sides["enemy"].leader_hp == 25


# ---------------------------------------------------------------- 4. serializacao
def _roundtrip(content, r):
    return Run.from_dict(content, json.loads(json.dumps(r.to_dict())))


def _estado(r):
    return (r.status, r.result, r.layer, r.nodes_cleared, list(r.cards), list(r.draft_options),
            [c.id for c in r.cats], r.node["id"] if r.node else None, r.deck_size())


def test_to_dict_e_json_puro(content):
    json.dumps(fresh(content).to_dict())


def test_roundtrip_no_mapa_reproduz_estado(content):
    r = fresh(content)
    _ate_camada(r, ["c1-batalha"])
    r2 = _roundtrip(content, r)
    assert _estado(r2) == _estado(r)
    assert r2.cats == r.cats


def test_roundtrip_no_draft_reproduz_opcoes(content):
    r = fresh(content)
    r.choose_node("c1-batalha")
    forced(r, "player")
    r2 = _roundtrip(content, r)
    assert r2.status == "draft" and r2.draft_options == r.draft_options
    assert r2.pick_draft(2) == r.pick_draft(2)


def test_roundtrip_mantem_a_mesma_sequencia_de_drafts(content):
    a = fresh(content, 11)
    _ate_camada(a, ["c1-batalha"])
    b = _roundtrip(content, a)
    ra, rb = [], []
    for nid in ["c2-batalha", "c3-batalha"]:
        for r, acc in ((a, ra), (b, rb)):
            r.choose_node(nid)
            forced(r, "player")
            acc.append(tuple(r.draft_options))
            r.pick_draft(1)
    assert ra == rb and a.cards == b.cards


def test_roundtrip_run_finalizada(content):
    r = fresh(content)
    r.choose_node("c1-batalha")
    forced(r, "enemy")
    r2 = _roundtrip(content, r)
    assert r2.status == "finished" and r2.result == "derrota"


def test_to_dict_durante_duelo_levanta_illegal(content):
    r = fresh(content)
    r.choose_node("c1-batalha")
    r.start_duel(Random(1))
    with pytest.raises(IllegalAction):
        r.to_dict()


def test_to_dict_logo_apos_finish_duel_funciona(content):
    r = fresh(content)
    r.choose_node("c1-batalha")
    forced(r, "player")
    assert _roundtrip(content, r).status == "draft"


def test_abandon_conta_como_derrota(content):
    r = fresh(content)
    _ate_camada(r, ["c1-batalha"])
    r.abandon()
    assert r.status == "finished" and r.result == "derrota"
    assert r.nodes_cleared == 1


def test_abandon_no_mapa_inicial(content):
    r = fresh(content)
    r.abandon()
    assert r.status == "finished" and r.result == "derrota"


def test_from_dict_rejeita_versao_desconhecida(content):
    d = fresh(content).to_dict()
    d["version"] = 99
    with pytest.raises(ValueError):
        Run.from_dict(content, d)


# ---------------------------------------------------------------- 5. propriedade
def _run_completa(content, seed):
    rng = Random(seed)
    r = new_run(content, rng)
    for _ in range(100):
        if r.status == "finished":
            return r
        if r.status == "map":
            r.choose_node(rng.choice(r.available_nodes())["id"])
        elif r.status == "duel":
            d = r.start_duel(Random(rng.randrange(2**31)))
            play_ai(d, Random(rng.randrange(2**31)))
            r.finish_duel(d)
        else:
            r.pick_draft(rng.randrange(len(r.draft_options)))
    raise AssertionError("run nao terminou")


def test_cem_runs_com_ia_terminam_sem_excecao(content):
    t0 = time.time()
    resultados = []
    for seed in range(100):
        r = _run_completa(content, seed)
        assert r.status == "finished" and r.result in ("vitoria", "derrota")
        assert r.deck_size() >= DECK
        resultados.append(r.result)
    print(f"100 runs em {time.time() - t0:.1f}s; vitorias={resultados.count('vitoria')}")


def test_run_completa_e_deterministica_pela_seed(content):
    assert _estado(_run_completa(content, 3)) == _estado(_run_completa(content, 3))


# ---------------------------------------------------------------- 6. recompensas (T4.7)
def _ate_elite(content, seed=1):
    r = fresh(content, seed)
    _ate_camada(r, CAMINHO_ELITE)
    r.choose_node("c4-elite")
    forced(r, "player")
    return r


def test_elite_abre_dois_drafts_em_sequencia(content):
    r = _ate_elite(content)
    assert r.status == "draft" and r.draft_step == 1 and r.draft_total == 2
    assert len(r.draft_options) == 3
    antes = r.deck_size()
    primeira = r.draft_options[0]
    opcoes1 = list(r.draft_options)
    r.pick_draft(0)
    assert r.status == "draft" and r.draft_step == 2 and r.draft_total == 2
    assert len(r.draft_options) == 3 and r.draft_options != opcoes1
    assert primeira not in r.draft_options
    assert r.layer == 3  # ainda nao voltou ao mapa
    r.pick_draft(1)
    assert r.status == "map" and r.draft_step == 0
    assert r.deck_size() == antes + 2


def test_elite_segundo_draft_nunca_repete_a_escolhida_em_varias_seeds(content):
    for seed in range(30):
        r = _ate_elite(content, seed)
        escolhida = r.draft_options[seed % 3]
        r.pick_draft(seed % 3)
        assert escolhida not in r.draft_options, seed


def test_batalha_comum_abre_um_draft_de_3(content):
    r = fresh(content)
    r.choose_node("c1-batalha")
    forced(r, "player")
    assert r.draft_step == 1 and r.draft_total == 1 and len(r.draft_options) == 3
    r.pick_draft(0)
    assert r.status == "map" and r.draft_step == 0 and len(r.cards) == 1


def test_descanso_abre_um_draft_de_2(content):
    r = fresh(content)
    _ate_camada(r, ["c1-batalha"])
    r.choose_node("c2-descanso")
    assert r.draft_step == 1 and r.draft_total == 1 and len(r.draft_options) == 2
    r.pick_draft(1)
    assert r.status == "map" and len(r.cards) == 2


def test_elite_respeita_drafts_elite_configurado(content):
    c2 = copy.deepcopy(content)
    c2.run["drafts_elite"] = 3
    r = new_run(c2, Random(1))
    _ate_camada(r, CAMINHO_ELITE)
    r.choose_node("c4-elite")
    forced(r, "player")
    assert r.draft_total == 3
    _pick_todos(r)
    assert len(r.cards) == 3 + 3


def test_elite_como_ultimo_no_antes_do_chefe(content):
    c2 = copy.deepcopy(content)
    inimigo = next(n["inimigo"] for l in c2.run["map"]["layers"] for n in l["nodes"]
                   if n["id"] == "c4-elite")
    no = c2.run["map"]["layers"][4]["nodes"][0]
    no["tipo"], no["inimigo"] = "elite", inimigo
    r = new_run(c2, Random(1))
    _ate_camada(r, CAMINHO_ELITE + ["c4-batalha"])
    r.choose_node(no["id"])
    forced(r, "player")
    assert r.status == "draft" and r.draft_total == 2
    r.pick_draft(0)
    assert r.status == "draft" and r.draft_step == 2
    r.pick_draft(0)
    assert r.status == "map" and r.layer == 5
    assert [n["id"] for n in r.available_nodes()] == ["c6-chefe"]


def test_roundtrip_no_meio_da_sequencia_de_drafts_mantem_o_passo(content):
    r = _ate_elite(content)
    r.pick_draft(0)
    r2 = _roundtrip(content, r)
    assert r2.status == "draft" and r2.draft_step == 2 and r2.draft_total == 2
    assert r2.draft_options == r.draft_options and r2.cards == r.cards
    assert r2.pick_draft(1) == r.pick_draft(1)
    assert r2.status == r.status == "map" and r2.cards == r.cards


def test_roundtrip_no_primeiro_draft_da_elite_ainda_tem_dois_passos(content):
    r = _ate_elite(content)
    r2 = _roundtrip(content, r)
    assert (r2.draft_step, r2.draft_total) == (1, 2)
    r2.pick_draft(0)
    assert r2.draft_step == 2


def test_from_dict_de_save_antigo_sem_campos_novos(content):
    r = fresh(content)
    r.choose_node("c1-batalha")
    forced(r, "player")
    d = json.loads(json.dumps(r.to_dict()))
    for k in ("drafts_left", "draft_total", "draft_taken", "draft_key"):
        d.pop(k, None)
    r2 = Run.from_dict(content, d)
    assert r2.status == "draft" and r2.draft_options == r.draft_options
    assert r2.draft_total == 1
    r2.pick_draft(0)
    assert r2.status == "map"


def test_abandon_no_meio_dos_drafts_da_elite_e_derrota(content):
    r = _ate_elite(content)
    r.pick_draft(0)
    r.abandon()
    assert r.status == "finished" and r.result == "derrota"
    assert r.draft_options == [] and r.draft_step == 0


def test_start_duel_em_no_sem_inimigo_levanta_illegal(content):
    r = fresh(content)
    _ate_camada(r, ["c1-batalha"])
    r.choose_node("c2-descanso")
    with pytest.raises(IllegalAction):
        r.start_duel(Random(1))


def test_drafts_da_elite_sao_deterministicos_pela_seed(content):
    def seq(seed):
        r = _ate_elite(content, seed)
        a = list(r.draft_options)
        r.pick_draft(0)
        return a, list(r.draft_options)
    assert seq(5) == seq(5)
    assert seq(5) != seq(6)
