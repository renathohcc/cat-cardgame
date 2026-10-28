"""Validacao dos dados da Fase 3 (efeitos, Espiritos, inimigos) e do validador cruzado.

Fonte: CONTRATOS 1.6, 1.7, 1.8. Os JSON invalidos sao feitos em memoria (ou em copia
em tmp_path); nada em data/ e alterado.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import shutil
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from core import load_content

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"


def _carrega_validador():
    spec = importlib.util.spec_from_file_location("validate_data_mod", DATA / "validate_data.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


vd = _carrega_validador()


@pytest.fixture()
def docs(capsys):
    erros, d = vd.check_schemas()
    capsys.readouterr()
    assert erros == 0
    return copy.deepcopy(d)


def schema_erros(nome: str, doc: dict) -> list:
    schema = json.loads((DATA / "schemas" / f"{nome}.schema.json").read_text(encoding="utf-8"))
    return list(Draft202012Validator(schema).iter_errors(doc))


def inimigo(docs, eid: str) -> dict:
    return next(e for e in docs["enemies"]["enemies"] if e["id"] == eid)


# ---------------------------------------------------------------- dados reais
def test_dados_reais_passam_nos_schemas_e_nas_referencias_cruzadas(docs, capsys):
    assert vd.check_cross_refs(docs) == 0
    capsys.readouterr()


@pytest.mark.parametrize("nome", ["effects", "specials", "enemies"])
def test_arquivos_da_fase3_validam_contra_o_schema(nome):
    doc = json.loads((DATA / f"{nome}.json").read_text(encoding="utf-8"))
    assert schema_erros(nome, doc) == []


def test_load_content_carrega_efeitos_especiais_e_inimigos():
    c = load_content(DATA)
    assert len(c.effects) == 8 and len(c.specials) == 8 and len(c.enemies) == 4


def test_dados_batem_com_a_proposta_aprovada():
    ef = {e["id"]: e for e in json.loads((DATA / "effects.json").read_text("utf-8"))["effects"]}
    assert ef["rugido-de-guerra"]["acoes"][0]["duracao"] == "turno"
    assert all(e["custo"] >= 1 for e in ef.values())
    inim = {e["id"]: e for e in json.loads((DATA / "enemies.json").read_text("utf-8"))["enemies"]}
    assert inim["berenice-da-matilha"]["lider_hp"] == 22
    assert inim["madame-fifi-pelucia"]["lider_hp"] == 25
    assert inim["madame-fifi-pelucia"]["regra_propria"] == {
        "id": "banho-de-espuma", "nome": "Banho de Espuma",
        "texto": "No início do turno dela, o Líder se cura em 1 HP.",
        "gatilho": "inicio_turno_proprio",
        "acao": {"tipo": "cura", "alvo": "lider_proprio", "valor": 1}}
    assert all(e["regra_propria"] is None for k, e in inim.items() if k != "madame-fifi-pelucia")


# ---------------------------------------------------------------- referencias cruzadas
def test_carta_inexistente_no_deck_e_rejeitada(docs, capsys):
    inimigo(docs, "tonho-sem-sorte")["deck"][-1]["carta"] = "gato-fantasma"
    assert vd.check_cross_refs(docs) > 0
    assert "gato-fantasma" in capsys.readouterr().out


def test_deck_que_nao_soma_12_e_rejeitado(docs, capsys):
    inimigo(docs, "irmaos-pimenta")["deck"][0]["qtd"] += 1
    assert vd.check_cross_refs(docs) > 0
    assert "13" in capsys.readouterr().out


def test_deck_com_menos_de_12_e_rejeitado(docs):
    inimigo(docs, "irmaos-pimenta")["deck"].pop()
    assert vd.check_cross_refs(docs) > 0


def test_raca_sem_iv_e_rejeitada(docs):
    entrada = next(e for e in inimigo(docs, "tonho-sem-sorte")["deck"] if e["carta"] == "persa")
    del entrada["iv_atk"]
    assert vd.check_cross_refs(docs) > 0


def test_espirito_com_iv_e_rejeitado(docs):
    entrada = next(e for e in inimigo(docs, "tonho-sem-sorte")["deck"]
                   if e["carta"] == "sombra-miuda")
    entrada.update(iv_atk=3, iv_hp=3, nature="calmo")
    assert vd.check_cross_refs(docs) > 0


def test_natureza_inexistente_e_rejeitada(docs):
    inimigo(docs, "tonho-sem-sorte")["deck"][0]["nature"] = "dorminhoco"
    assert vd.check_cross_refs(docs) > 0


def test_iv_fora_de_1_a_5_e_rejeitado(docs):
    inimigo(docs, "tonho-sem-sorte")["deck"][0]["iv_atk"] = 6
    assert vd.check_cross_refs(docs) > 0 or schema_erros("enemies", docs["enemies"])


def test_keyword_inexistente_em_espirito_e_rejeitada(docs):
    docs["specials"]["specials"][0]["keywords"] = ["voar"]
    assert vd.check_cross_refs(docs) > 0


def test_id_repetido_entre_raca_e_efeito_e_rejeitado(docs):
    docs["effects"]["effects"][0]["id"] = "persa"
    assert vd.check_cross_refs(docs) > 0


def test_inimigo_repetido_e_rejeitado(docs):
    docs["enemies"]["enemies"].append(copy.deepcopy(docs["enemies"]["enemies"][0]))
    assert vd.check_cross_refs(docs) > 0


def test_arquivo_ausente_nas_referencias_e_erro(docs):
    del docs["enemies"]
    assert vd.check_cross_refs(docs) > 0


# ---------------------------------------------------------------- schema de regra_propria
def test_regra_propria_com_gatilho_desconhecido_e_rejeitada_pelo_schema(docs):
    inimigo(docs, "madame-fifi-pelucia")["regra_propria"]["gatilho"] = "fim_de_turno_inimigo"
    assert schema_erros("enemies", docs["enemies"])


def test_regra_propria_com_campo_extra_e_rejeitada(docs):
    inimigo(docs, "madame-fifi-pelucia")["regra_propria"]["bonus"] = 3
    assert schema_erros("enemies", docs["enemies"])


def test_regra_propria_sem_acao_e_rejeitada(docs):
    del inimigo(docs, "madame-fifi-pelucia")["regra_propria"]["acao"]
    assert schema_erros("enemies", docs["enemies"])


def test_regra_propria_com_acao_de_tipo_desconhecido_e_rejeitada(docs):
    inimigo(docs, "madame-fifi-pelucia")["regra_propria"]["acao"]["tipo"] = "teleporte"
    assert schema_erros("enemies", docs["enemies"])


def test_batalha_comum_nao_pode_ter_regra_propria(docs):
    inimigo(docs, "tonho-sem-sorte")["regra_propria"] = copy.deepcopy(
        inimigo(docs, "madame-fifi-pelucia")["regra_propria"])
    assert schema_erros("enemies", docs["enemies"])


def test_ia_desconhecida_e_rejeitada(docs):
    inimigo(docs, "tonho-sem-sorte")["ia"] = "genio"
    assert schema_erros("enemies", docs["enemies"])


def test_efeito_com_custo_zero_e_rejeitado(docs):
    docs["effects"]["effects"][0]["custo"] = 0
    assert schema_erros("effects", docs["effects"])


def test_efeito_com_tipo_de_acao_desconhecido_e_rejeitado(docs):
    docs["effects"]["effects"][0]["acoes"][0]["tipo"] = "ressuscitar"
    assert schema_erros("effects", docs["effects"])


# ---------------------------------------------------------------- load_content rejeita
def copia_dados(tmp_path: Path) -> Path:
    destino = tmp_path / "data"
    shutil.copytree(DATA, destino, ignore=shutil.ignore_patterns("__pycache__"))
    return destino


def altera(destino: Path, nome: str, fn) -> None:
    caminho = destino / nome
    doc = json.loads(caminho.read_text(encoding="utf-8"))
    fn(doc)
    caminho.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")


def test_load_content_aceita_a_copia_intacta(tmp_path):
    assert len(load_content(copia_dados(tmp_path)).enemies) == 4


def test_load_content_rejeita_carta_inexistente_no_deck(tmp_path):
    d = copia_dados(tmp_path)
    altera(d, "enemies.json", lambda doc: doc["enemies"][0]["deck"][-1].update(carta="fantasma"))
    with pytest.raises(Exception):
        load_content(d)


def test_load_content_rejeita_gatilho_desconhecido(tmp_path):
    d = copia_dados(tmp_path)

    def quebra(doc):
        next(e for e in doc["enemies"] if e["tipo"] == "chefe")["regra_propria"]["gatilho"] = "x"

    altera(d, "enemies.json", quebra)
    with pytest.raises(Exception):
        load_content(d)
