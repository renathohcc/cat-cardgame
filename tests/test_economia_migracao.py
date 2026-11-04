"""Migracao do save v1 -> v2 (Fase 10a, T13.2). Fonte: especificacao 10a e T13.0b/T13.1.

Nenhum teste altera `saves/save.json` real: ele so e COPIADO para pasta temporaria."""
from __future__ import annotations

import copy
import json
import shutil
from random import Random

import pytest
from jsonschema import Draft202012Validator

from core import (SaveData, migrate_save_dict, new_game, read_save, save_from_dict,
                  save_to_dict, write_save)
from economia_helpers import ROOT, SAVE_SCHEMA, build, content as _content

REAL = ROOT / "saves" / "save.json"
VALIDATOR = Draft202012Validator(SAVE_SCHEMA)


@pytest.fixture(scope="module")
def c():
    return _content()


def _v1_de(save: SaveData) -> dict:
    """Converte um save atual no formato v1 antigo (remove tudo que a v2 acrescentou)."""
    d = save_to_dict(save)
    d["schema_version"] = 1
    for k in ("prestige", "areas_unlocked", "rations", "decorations_owned",
              "first_league_win_claimed", "lifetime"):
        d.pop(k)
    for cat in d["cats"] + d.get("pending_adoption", {}).get("cats", []):
        for k in ("generation", "parents", "history"):
            cat.pop(k)
    for b in d["breeding"]:
        b.pop("ration")
        b.pop("ration_choice")
    return d


@pytest.fixture
def v1(c):
    """v1 sintetico: 14 gatos, um casal em breed, dex e progresso preenchidos, oferta pendente."""
    s = new_game(c, Random(5))
    extra = build(c, 16, breeds_n=3)
    s.cats = extra.cats
    s.deck = extra.deck
    s.next_cat_id = 17
    s.coins = 7
    s.breeding = [{"male": "c-000013", "female": "c-000014", "runs_left": 1,
                   "ration": None, "ration_choice": None}]
    s.deck = [i for i in s.deck if i not in ("c-000013", "c-000014")]
    s.cats[2].name = "Mingau"
    s.pity = {"runs_without_high_iv": 3}
    s.progress = {"leagues_cleared": 0, "best_distance": 5, "records": {"x": 1}}
    s.dex = {"breeds_seen": ["siames"], "perfect_cats": []}
    s.settings = {"vol": 3}
    return _v1_de(s)


# ------------------------------------------------------------ v1 sintetico
def test_migrar_v1_sintetico_gera_save_v2_que_valida_no_schema(c, v1):
    save = save_from_dict(v1, c)
    assert save.migrated_from == 1
    assert list(VALIDATOR.iter_errors(save_to_dict(save))) == []
    assert save_to_dict(save)["schema_version"] == 2


def test_migrar_v1_preserva_todos_os_campos_antigos(c, v1):
    out = save_to_dict(save_from_dict(copy.deepcopy(v1), c))
    for k in ("coins", "deck", "next_cat_id", "pity", "progress", "dex", "items", "settings"):
        assert out[k] == v1[k], k
    assert len(out["cats"]) == len(v1["cats"])
    for novo, velho in zip(out["cats"], v1["cats"]):
        assert {k: novo[k] for k in velho} == velho
    antigo = v1["breeding"][0]
    novo = out["breeding"][0]
    assert {k: novo[k] for k in antigo} == antigo


def test_migrar_v1_acrescenta_campos_novos_com_valores_neutros(c, v1):
    out = save_to_dict(save_from_dict(copy.deepcopy(v1), c))
    assert out["prestige"] == 1
    assert out["areas_unlocked"] == [] and out["decorations_owned"] == []
    assert out["first_league_win_claimed"] is False
    assert out["lifetime"] == {"runs_completed": 0, "duels_won": 0}
    assert set(out["rations"]) == {r["id"] for r in c.shop["rations"]}
    assert set(out["rations"].values()) == {0}
    for cat in out["cats"]:
        assert cat["generation"] == 1 and cat["parents"] == []
        assert cat["history"] == {"runs": 0, "duels_won": 0, "bosses_defeated": 0}
    assert out["breeding"][0]["ration"] is None
    assert out["breeding"][0]["ration_choice"] is None


def test_migrar_v1_com_adocao_pendente_tambem_migra_os_gatos_da_oferta(c, v1):
    v1["pending_adoption"] = {"cats": [{
        "id": "c-000100", "breed": next(iter(c.breeds)), "sex": "F",
        "nature": next(iter(c.natures)), "iv_atk": 4, "iv_hp": 2, "stage": "adult",
        "rest_runs_left": 0, "runs_as_kitten": 0}], "result": "vitoria", "nodes_cleared": 4}
    v1["next_cat_id"] = 101
    save = save_from_dict(v1, c)
    oferta = save.pending_adoption["cats"][0]
    assert (oferta.generation, oferta.parents) == (1, [])
    assert list(VALIDATOR.iter_errors(save_to_dict(save))) == []


def test_migrate_save_dict_nao_altera_o_dicionario_de_entrada(c, v1):
    antes = copy.deepcopy(v1)
    out = migrate_save_dict(v1, c)
    assert v1 == antes
    assert out["schema_version"] == 2 and out is not v1


def test_migrate_save_dict_sem_content_deixa_estoque_de_racao_vazio(v1):
    assert migrate_save_dict(v1)["rations"] == {}


def test_save_v2_relido_nao_marca_migrated_from(c, v1, tmp_path):
    p = tmp_path / "save.json"
    write_save(save_from_dict(v1, c), p)
    lido = read_save(p, c)
    assert lido.migrated_from is None
    assert json.loads(p.read_text("utf-8"))["schema_version"] == 2


def test_migrar_ida_e_volta_e_idempotente(c, v1):
    primeira = save_to_dict(save_from_dict(copy.deepcopy(v1), c))
    segunda = save_to_dict(save_from_dict(copy.deepcopy(primeira), c))
    assert primeira == segunda


# ------------------------------------------------------------ id de racao antigo
@pytest.mark.parametrize("antigo, stat, parent", [
    ("racao-escolha-hp-mae", "hp", "mother"),
    ("racao-escolha-atk-pai", "atk", "father"),
    ("racao-escolha-hp-pai", "hp", "father"),
    ("racao-escolha-atk-mae", "atk", "mother"),
])
def test_racao_antiga_codificada_vira_racao_escolha_com_ration_choice(c, v1, antigo, stat, parent):
    v1["breeding"][0]["ration"] = antigo
    save = save_from_dict(v1, c)
    b = save.breeding[0]
    assert b["ration"] == "racao-escolha"
    assert b["ration_choice"] == {"stat": stat, "parent": parent}
    assert list(VALIDATOR.iter_errors(save_to_dict(save))) == []


def test_racao_antiga_comum_passa_intacta_sem_escolha(c, v1):
    v1["breeding"][0]["ration"] = "racao-fofa"
    b = save_from_dict(v1, c).breeding[0]
    assert b["ration"] == "racao-fofa" and b["ration_choice"] is None


# ------------------------------------------------------------ falhas
@pytest.mark.parametrize("mutar", [
    lambda d: d.__setitem__("cats", "nao-e-lista"),
    lambda d: d.__setitem__("deck", ["c-999999"]),
    lambda d: d.__setitem__("coins", -1),
    lambda d: d.__setitem__("campo_extra", 1),
    lambda d: d["cats"][0].__setitem__("iv_atk", 9),
    lambda d: d["cats"][0].__setitem__("sex", "X"),
    lambda d: d.pop("coins"),
    lambda d: d.__setitem__("next_cat_id", 3),
    lambda d: d["cats"].append(copy.deepcopy(d["cats"][0])),
], ids=["cats-nao-lista", "deck-inexistente", "moedas-negativas", "campo-extra",
        "iv-fora-da-faixa", "sexo-invalido", "campo-obrigatorio-faltando",
        "next_cat_id-baixo", "id-repetido"])
def test_v1_corrompido_continua_falhando(c, v1, mutar):
    mutar(v1)
    with pytest.raises(ValueError):
        save_from_dict(v1, c)


@pytest.mark.parametrize("versao", [0, 3, 4, -1, None, "1", "2", True, 1.5])
def test_versao_desconhecida_falha(c, v1, versao):
    v1["schema_version"] = versao
    with pytest.raises(ValueError):
        save_from_dict(v1, c)


def test_arquivo_com_json_quebrado_falha(c, tmp_path):
    p = tmp_path / "save.json"
    p.write_text("{ isto nao e json", encoding="utf-8")
    with pytest.raises(ValueError):
        read_save(p, c)


def test_arquivo_ausente_falha(c, tmp_path):
    with pytest.raises(ValueError):
        read_save(tmp_path / "nao-existe.json", c)


# ------------------------------------------------------------ save real e backup
def _copia_do_real(tmp_path):
    if not REAL.exists():
        pytest.skip("saves/save.json nao existe nesta maquina")
    raw = json.loads(REAL.read_text("utf-8"))
    if raw.get("schema_version") != 1:
        pytest.skip("saves/save.json ja esta na v2: nao ha mais v1 real para migrar")
    p = tmp_path / "save.json"
    shutil.copyfile(REAL, p)
    return p


def test_save_real_v1_migra_valida_e_preserva_os_campos_antigos(c, tmp_path):
    p = _copia_do_real(tmp_path)
    antigo = json.loads(p.read_text("utf-8"))
    save = read_save(p, c)
    novo = save_to_dict(save)
    assert save.migrated_from == 1
    assert list(VALIDATOR.iter_errors(novo)) == []
    for k, v in antigo.items():
        if k in ("schema_version", "cats", "breeding"):
            continue
        assert novo[k] == v, k
    assert [{k: x[k] for k in o} for x, o in zip(novo["cats"], antigo["cats"])] == antigo["cats"]


def test_ler_save_real_v1_nao_altera_o_arquivo(c, tmp_path):
    p = _copia_do_real(tmp_path)
    antes = p.read_bytes()
    read_save(p, c)
    assert p.read_bytes() == antes


def test_original_em_saves_nao_e_tocado_pelos_testes(c, tmp_path):
    if not REAL.exists():
        pytest.skip("sem save real")
    antes = REAL.read_bytes()
    p = tmp_path / "save.json"
    shutil.copyfile(REAL, p)
    write_save(read_save(p, c), p)
    assert REAL.read_bytes() == antes


def test_protocolo_do_backup_bak_antes_de_regravar_v2(c, v1, tmp_path):
    """O `.bak` e responsabilidade de quem chama (UI): usa `migrated_from` para copiar o v1
    antes de regravar. Aqui valida o protocolo que o core permite."""
    p = tmp_path / "save.json"
    p.write_text(json.dumps(v1), encoding="utf-8")
    bruto = p.read_bytes()
    save = read_save(p, c)
    assert save.migrated_from == 1
    bak = p.with_name(p.name + ".bak")
    shutil.copyfile(p, bak)
    write_save(save, p)
    assert bak.read_bytes() == bruto
    assert json.loads(bak.read_text("utf-8"))["schema_version"] == 1
    assert json.loads(p.read_text("utf-8"))["schema_version"] == 2
    assert read_save(p, c).migrated_from is None
