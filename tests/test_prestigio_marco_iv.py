"""Marco de Prestigio `distinct_breeds_min_iv` (T13.2e) e o `distinct_breeds` antigo.

Escritos a partir de reports/T13.0e-marco-dados.md e do contrato do marco: progresso = racas com
ao menos um gato de soma IV ATK+HP >= min_iv_sum; alvo = count. Valores lidos de data/rules.json."""
from __future__ import annotations

import copy
import json

import pytest
from jsonschema import Draft202012Validator

from core import prestige_info, update_prestige
from economia_helpers import DATA, build, content as _content, min_iv_sum, set_strong_breeds

SCHEMA = json.loads((DATA / "schemas" / "rules.schema.json").read_text("utf-8"))
EX = DATA / "schemas" / "examples"


@pytest.fixture(scope="module")
def c():
    return _content()


@pytest.fixture
def save(c):
    s = build(c, 16, breeds_n=1)
    s.prestige = 2
    s.progress["leagues_cleared"] = 1
    return s


def test_regras_usam_o_marco_novo_no_prestigio_3(c):
    m = next(l["milestone"] for l in c.rules["prestige"]["levels"] if l["level"] == 3)
    assert m["type"] == "distinct_breeds_min_iv" and m["count"] >= 2 and m["min_iv_sum"] >= 2


def test_nao_conta_raca_sem_gato_forte(c, save):
    set_strong_breeds(c, save, soma=min_iv_sum(c) - 1)
    info = prestige_info(c, save)
    assert info.current == 0 and update_prestige(c, save) == 2


def test_conta_raca_com_exatamente_min_iv_sum(c, save):
    set_strong_breeds(c, save, soma=min_iv_sum(c))
    info = prestige_info(c, save)
    assert info.current == info.target and update_prestige(c, save) == 3


def test_quatro_racas_fortes_e_uma_fraca_nao_bastam(c, save):
    set_strong_breeds(c, save)
    fraca = save.cats[4]
    fraca.iv_atk, fraca.iv_hp = 1, min_iv_sum(c) - 2
    assert prestige_info(c, save).current == 4
    assert update_prestige(c, save) == 2


def test_dois_gatos_fortes_da_mesma_raca_contam_uma_raca_so(c, save):
    set_strong_breeds(c, save, 4)
    extra = save.cats[5]
    extra.breed = save.cats[0].breed
    extra.iv_atk, extra.iv_hp = 5, 5
    assert prestige_info(c, save).current == 4 and update_prestige(c, save) == 2


def test_raca_com_um_gato_fraco_e_um_forte_conta(c, save):
    set_strong_breeds(c, save, 4)
    b5 = list(c.breeds)[4]
    fraco, forte = save.cats[4], save.cats[5]
    fraco.breed = forte.breed = b5
    fraco.iv_atk = fraco.iv_hp = 1
    forte.iv_atk, forte.iv_hp = 5, min_iv_sum(c) - 5 if min_iv_sum(c) > 5 else 1
    assert update_prestige(c, save) == 3


def test_marco_novo_ainda_pede_a_liga_antes(c):
    s = build(c, 16, breeds_n=1)
    set_strong_breeds(c, s)
    assert update_prestige(c, s) == 1


def test_distinct_breeds_antigo_continua_funcionando(c, save):
    """Conteudo com o marco antigo no nivel 3: iv fraco nao importa."""
    c2 = copy.copy(c)
    c2.rules = copy.deepcopy(c.rules)
    for lv in c2.rules["prestige"]["levels"]:
        if lv["level"] == 3:
            lv["milestone"] = {"type": "distinct_breeds", "count": 5}
    for cat, breed in zip(save.cats, list(c.breeds)[:5]):
        cat.breed = breed
        cat.iv_atk = cat.iv_hp = 1
    assert update_prestige(c2, save) == 3


def test_schema_aceita_os_exemplos_validos():
    ex = json.loads((EX / "rules.example.json").read_text("utf-8"))
    assert list(Draft202012Validator(SCHEMA).iter_errors(ex)) == []
    tipos = [l["milestone"]["type"] for l in ex["prestige"]["levels"]]
    assert "distinct_breeds_min_iv" in tipos


def test_schema_rejeita_marco_sem_min_iv_sum():
    ex = json.loads((EX / "invalid" / "rules.invalid_min_iv_sem_soma.json").read_text("utf-8"))
    assert list(Draft202012Validator(SCHEMA).iter_errors(ex))


def test_schema_rejeita_min_iv_sum_zero_e_count_zero():
    ex = json.loads((EX / "rules.example.json").read_text("utf-8"))
    for campo in ("min_iv_sum", "count"):
        ruim = copy.deepcopy(ex)
        for lv in ruim["prestige"]["levels"]:
            if lv["milestone"]["type"] == "distinct_breeds_min_iv":
                lv["milestone"][campo] = 0
        assert list(Draft202012Validator(SCHEMA).iter_errors(ruim)), campo


def test_schema_aceita_distinct_breeds_antigo():
    ex = json.loads((EX / "rules.example.json").read_text("utf-8"))
    for lv in ex["prestige"]["levels"]:
        if lv["milestone"]["type"] == "distinct_breeds_min_iv":
            lv["milestone"] = {"type": "distinct_breeds", "count": 5}
    assert list(Draft202012Validator(SCHEMA).iter_errors(ex)) == []
