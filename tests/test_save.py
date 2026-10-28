"""Save (CONTRATOS 1.9): new_game, serializacao, arquivo, schema, validacao."""
from __future__ import annotations

import json
import re
from pathlib import Path
from random import Random

import pytest
from jsonschema import Draft202012Validator

from core import (load_content, new_game, new_run_from_save, read_save, rename_cat,
                  save_from_dict, save_to_dict, write_save)

DATA = Path(__file__).resolve().parent.parent / "data"
SCHEMA = json.loads((DATA / "schemas" / "save.schema.json").read_text("utf-8"))


@pytest.fixture(scope="module")
def content():
    return load_content(DATA)


def novo(content, seed=1):
    return new_game(content, Random(seed))


def erros_schema(d):
    return list(Draft202012Validator(SCHEMA).iter_errors(d))


# ------------------------------------------------------------ new_game
def test_novo_jogo_tem_12_adultos(content):
    s = novo(content)
    assert len(s.cats) == 12
    assert all(c.stage == "adult" and c.rest_runs_left == 0 for c in s.cats)


def test_novo_jogo_ids_unicos_sequenciais_e_next_cat_id(content):
    s = novo(content)
    assert [c.id for c in s.cats] == [f"c-{i:06d}" for i in range(1, 13)]
    assert s.next_cat_id == 13


def test_novo_jogo_deck_tem_12_gatos_da_colecao(content):
    s = novo(content)
    assert len(s.deck) == 12 and len(set(s.deck)) == 12
    assert set(s.deck) <= {c.id for c in s.cats}


def test_novo_jogo_mesma_seed_mesmo_save(content):
    assert save_to_dict(novo(content, 7)) == save_to_dict(novo(content, 7))


def test_novo_jogo_seeds_diferentes_dao_colecoes_diferentes(content):
    assert save_to_dict(novo(content, 1)) != save_to_dict(novo(content, 2))


@pytest.mark.parametrize("seed", range(15))
def test_novo_jogo_racas_naturezas_e_ivs_validos(content, seed):
    for c in novo(content, seed).cats:
        assert c.breed in content.breeds
        assert c.nature in content.natures
        assert 1 <= c.iv_atk <= 5 and 1 <= c.iv_hp <= 5
        assert c.sex in ("M", "F")
        assert c.name is None


# ------------------------------------------------------------ round-trip
def test_roundtrip_dict(content):
    s = novo(content)
    rename_cat(s, s.cats[0].id, "Mingau")
    d = save_to_dict(s)
    assert save_to_dict(save_from_dict(d, content)) == d


def test_to_dict_nao_compartilha_estado_com_o_save(content):
    s = novo(content)
    d = save_to_dict(s)
    d["deck"].clear()
    d["settings"]["x"] = 1
    assert len(s.deck) == 12 and "x" not in s.settings


def test_nome_ausente_nao_vai_ao_json(content):
    d = save_to_dict(novo(content))
    assert all("name" not in c for c in d["cats"])


def test_roundtrip_arquivo_com_acentos(content, tmp_path):
    s = novo(content)
    rename_cat(s, s.cats[0].id, "Açaí Ñandú")
    p = tmp_path / "save.json"
    write_save(s, p)
    assert "Açaí Ñandú" in p.read_bytes().decode("utf-8")
    s2 = read_save(p, content)
    assert save_to_dict(s2) == save_to_dict(s)
    assert s2.cats[0].name == "Açaí Ñandú"


def test_escrita_atomica_sem_sobras_tmp(content, tmp_path):
    p = tmp_path / "save.json"
    s = novo(content)
    write_save(s, p)
    write_save(s, p)
    assert [f.name for f in tmp_path.iterdir()] == ["save.json"]


def test_escrita_sobrescreve_save_anterior(content, tmp_path):
    p = tmp_path / "sub" / "save.json"
    write_save(novo(content, 1), p)
    write_save(novo(content, 2), p)
    assert save_to_dict(read_save(p)) == save_to_dict(novo(content, 2))


def test_ler_save_ausente_e_valueerror(tmp_path):
    with pytest.raises(ValueError):
        read_save(tmp_path / "nao_existe.json")


def test_ler_json_corrompido_e_valueerror(tmp_path):
    p = tmp_path / "save.json"
    p.write_text("{nao e json", encoding="utf-8")
    with pytest.raises(ValueError):
        read_save(p)


# ------------------------------------------------------------ schema
def test_novo_jogo_valida_no_schema(content):
    assert erros_schema(save_to_dict(novo(content))) == []


def test_save_com_nomes_valida_no_schema(content):
    s = novo(content)
    for i, c in enumerate(s.cats[:5]):
        rename_cat(s, c.id, f"Gato {i} é ótimo")
    assert erros_schema(save_to_dict(s)) == []


def test_schema_rejeita_nome_longo(content):
    d = save_to_dict(novo(content))
    d["cats"][0]["name"] = "x" * 17
    assert erros_schema(d) != []


def test_schema_rejeita_iv_fora_da_faixa(content):
    d = save_to_dict(novo(content))
    d["cats"][0]["iv_atk"] = 6
    assert erros_schema(d) != []


# ------------------------------------------------------------ invalidos
def _mut(content, fn):
    d = save_to_dict(novo(content))
    fn(d)
    return d


def test_save_sem_campo_obrigatorio_e_erro(content):
    d = _mut(content, lambda d: d.pop("coins"))
    with pytest.raises(ValueError):
        save_from_dict(d, content)


def test_gato_sem_campo_obrigatorio_e_erro(content):
    d = _mut(content, lambda d: d["cats"][0].pop("nature"))
    with pytest.raises(ValueError):
        save_from_dict(d, content)


def test_id_de_gato_duplicado_e_erro(content):
    def f(d):
        d["cats"][1]["id"] = d["cats"][0]["id"]
    with pytest.raises(ValueError):
        save_from_dict(_mut(content, f), content)


def test_deck_com_id_inexistente_e_erro(content):
    d = _mut(content, lambda d: d["deck"].__setitem__(0, "c-999999"))
    with pytest.raises(ValueError):
        save_from_dict(d, content)


def test_deck_com_id_repetido_e_erro(content):
    d = _mut(content, lambda d: d["deck"].__setitem__(1, d["deck"][0]))
    with pytest.raises(ValueError):
        save_from_dict(d, content)


def test_next_cat_id_baixo_e_erro(content):
    d = _mut(content, lambda d: d.__setitem__("next_cat_id", 12))
    with pytest.raises(ValueError):
        save_from_dict(d, content)


@pytest.mark.parametrize("versao", [0, 2, 99, None, "1"])
def test_versao_errada_e_erro(content, versao):
    d = _mut(content, lambda d: d.__setitem__("schema_version", versao))
    with pytest.raises(ValueError):
        save_from_dict(d, content)


def test_raiz_nao_objeto_e_erro():
    with pytest.raises(ValueError):
        save_from_dict([])


def test_raca_inexistente_com_content_e_erro(content):
    d = _mut(content, lambda d: d["cats"][0].__setitem__("breed", "raca-fantasma"))
    with pytest.raises(ValueError):
        save_from_dict(d, content)


def test_iv_fora_da_faixa_e_erro(content):
    d = _mut(content, lambda d: d["cats"][0].__setitem__("iv_hp", 0))
    with pytest.raises(ValueError):
        save_from_dict(d, content)


def test_deck_com_filhote_e_erro(content):
    def f(d):
        d["cats"][0]["stage"] = "kitten"
    with pytest.raises(ValueError):
        save_from_dict(_mut(content, f), content)


# ------------------------------------------------------------ conteudo do save
def test_save_nunca_tem_gatos_de_run_nem_cartas_de_efeito(content):
    s = novo(content)
    r = new_run_from_save(content, s, Random(1))
    r.cards.append("algum-efeito")
    r.cats[0].iv_atk = 1
    d = save_to_dict(s)
    texto = json.dumps(d)
    assert not re.search(r"run-\d+", texto)
    assert all(re.fullmatch(r"c-\d{6}", c["id"]) for c in d["cats"])
    assert "cards" not in d and "run" not in d
    assert "algum-efeito" not in texto
