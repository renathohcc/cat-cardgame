"""T13.2f: limites por padrao, doacao de gato de breed, legacy_capacity, liga da run e
consultas que nao gravam. Escrito a partir de reports/T13.1e e T13.1f e do GDD (so API publica)."""
from __future__ import annotations

import copy
import json
from random import Random

import pytest
from jsonschema import Draft202012Validator

from core import (Cat, SaveData, adopt, advance_after_run, area_status, areas_status,
                  available_cats, can_adopt, can_breed, can_donate, donate_cat, donation_value,
                  kennel_capacity, kennel_over_limit, kennel_slots, migrate_save_dict, new_run,
                  next_goal, occupied, rations_catalog, save_from_dict, save_to_dict, start_breed)
from core.runend import DEFAULT_LEAGUE, _league
from core.types import IllegalAction
from economia_helpers import DATA, SAVE_SCHEMA, build, cid, content as _content, fill_to, \
    new_cat, pending, set_strong_breeds

VALIDATOR = Draft202012Validator(SAVE_SCHEMA)


@pytest.fixture(scope="module")
def c():
    return _content()


def mult(c) -> float:
    return float(c.rules["adoption"]["donation_bred_multiplier"])


def bred(save: SaveData, **kw) -> Cat:
    base = dict(sex="F", iv_atk=5, iv_hp=5, generation=2, parents=[cid(1), cid(2)])
    return Cat(id=cid(save.next_cat_id), **{"breed": save.cats[0].breed, "nature": save.cats[0].nature,
                                             **base, **kw})


# ------------------------------------------------------------ doacao de gato de breed
def test_doacao_de_gato_de_breed_usa_o_multiplicador_do_json(c):
    s = build(c, 14)
    adotado = s.cats[0]
    adotado.iv_atk, adotado.iv_hp = 5, 5
    filho = bred(s)
    cheio = donation_value(c, adotado)
    assert cheio > 0
    assert donation_value(c, filho) == int(cheio * mult(c))


def test_doacao_de_breed_vale_zero_com_os_dados_atuais(c):
    assert mult(c) == 0
    s = build(c, 14)
    assert donation_value(c, bred(s)) == 0
    assert donation_value(c, bred(s, stage="kitten")) == 0
    antes = s.coins
    s.cats.append(bred(s))
    assert donate_cat(c, s, s.cats[-1].id) == 0 and s.coins == antes


def test_multiplicador_lido_do_json_nao_e_fixo_no_codigo(c):
    c2 = copy.deepcopy(c)
    c2.rules["adoption"]["donation_bred_multiplier"] = 0.5
    s = build(c2, 14)
    s.cats[0].iv_atk = s.cats[0].iv_hp = 5
    filho = bred(s)
    assert donation_value(c2, filho) == int(donation_value(c2, s.cats[0]) * 0.5)
    c2.rules["adoption"]["donation_bred_multiplier"] = 1
    assert donation_value(c2, filho) == donation_value(c2, s.cats[0])


def test_g1_adotado_paga_cheio_mesmo_com_multiplicador_zero(c):
    s = build(c, 14)
    g1 = s.cats[0]
    g1.iv_atk, g1.iv_hp = 5, 5
    assert donation_value(c, g1) > 0
    antes = s.coins
    assert donate_cat(c, s, g1.id) == donation_value(c, g1) and s.coins > antes


def test_filhote_g1_adotado_continua_valendo_metade(c):
    s = build(c, 14)
    a = s.cats[0]
    a.iv_atk = a.iv_hp = 5
    k = copy.deepcopy(a)
    k.stage = "kitten"
    fator = c.rules["adoption"]["kitten_donation_factor"]
    assert donation_value(c, k) == int(donation_value(c, a) * fator)


def test_filhote_de_breed_real_nasce_e_doa_zero(c):
    s = build(c, 16)
    start_breed(c, s, cid(1), cid(2))
    rng = Random(3)
    advance_after_run(c, s, rng, 1)
    out = advance_after_run(c, s, rng, 1)
    assert out.born
    for k in out.born:
        assert k.generation == 2 and k.parents == [cid(1), cid(2)]
        assert donation_value(c, k) == 0


# ------------------------------------------------------------ minimo de 12 adultos
def test_doar_com_12_adultos_disponiveis_e_recusado(c):
    s = build(c, 12)
    ok, motivo = can_donate(c, s, cid(1))
    assert not ok and "12" in motivo
    antes = save_to_dict(s)
    with pytest.raises(IllegalAction):
        donate_cat(c, s, cid(1))
    assert save_to_dict(s) == antes


def test_doar_com_13_adultos_e_permitido_e_filhote_nao_conta_como_adulto(c):
    assert can_donate(c, build(c, 13), cid(1))[0]
    s = build(c, 12)
    fill_to(s, 14)                      # 2 filhotes nao contam como adultos
    assert not can_donate(c, s, cid(1))[0]
    assert can_donate(c, s, s.cats[-1].id)[0]


# ------------------------------------------------------------ legacy_capacity
def legado(c, n: int = 20) -> SaveData:
    assert n > kennel_slots(c, build(c, 12))
    s = build(c, n)
    s.legacy_capacity = n
    return s


def test_legacy_capacity_encolhe_ao_doar_e_nao_volta(c):
    s = legado(c, 20)
    slots = kennel_slots(c, s)
    assert kennel_capacity(c, s) == 20
    donate_cat(c, s, cid(19))
    assert s.legacy_capacity == 19 and kennel_capacity(c, s) == 19
    while occupied(s) > slots - 2:
        donate_cat(c, s, s.cats[-1].id)
    assert kennel_capacity(c, s) == slots           # voltou as vagas das areas
    fill_to(s, slots + 2)                           # gatos novos nao ressuscitam o legado
    assert s.legacy_capacity <= slots - 2
    assert kennel_capacity(c, s) == slots
    assert kennel_over_limit(c, s)


def test_legacy_capacity_nunca_passa_do_total_de_gatos(c):
    s = legado(c, 20)
    for i in range(20, 14, -1):
        donate_cat(c, s, cid(i))
        assert s.legacy_capacity <= occupied(s)


def test_save_sem_o_campo_legacy_capacity_le_como_zero(c):
    d = save_to_dict(build(c, 14))
    d.pop("legacy_capacity", None)
    assert save_from_dict(d, c).legacy_capacity == 0
    assert list(VALIDATOR.iter_errors(d)) == []


def test_legacy_capacity_zero_nao_e_serializado_e_positivo_faz_round_trip(c):
    s = build(c, 14)
    assert "legacy_capacity" not in save_to_dict(s)
    s2 = legado(c, 20)
    d = save_to_dict(s2)
    assert d["legacy_capacity"] == 20
    assert list(VALIDATOR.iter_errors(d)) == []
    assert save_to_dict(save_from_dict(json.loads(json.dumps(d)), c)) == d


def test_adocao_bloqueada_quando_total_atinge_a_capacidade_efetiva(c):
    s = legado(c, 20)
    assert not can_adopt(c, s)[0]
    novo = new_cat(s)
    pending(s, [novo])
    antes = save_to_dict(s)
    with pytest.raises(IllegalAction):
        adopt(c, s, novo.id)
    assert save_to_dict(s) == antes
    donate_cat(c, s, cid(20))
    assert not can_adopt(c, s)[0]                   # 19 de 19: ainda cheio
    while occupied(s) > kennel_slots(c, s) - 1:
        donate_cat(c, s, s.cats[-1].id)
    assert can_adopt(c, s)[0]
    adopt(c, s, novo.id)
    assert any(x.id == novo.id for x in s.cats)


def test_gatil_cheio_sem_legado_bloqueia_adocao(c):
    s = build(c, 12)
    fill_to(s, kennel_slots(c, s))
    novo = new_cat(s)
    pending(s, [novo])
    with pytest.raises(IllegalAction):
        adopt(c, s, novo.id)


def test_breed_nao_trava_por_causa_do_legado(c):
    s = legado(c, 20)
    assert not kennel_over_limit(c, s)
    assert can_breed(c, s, cid(1), cid(2))[0]
    start_breed(c, s, cid(1), cid(2))
    assert len(s.breeding) == 1


def test_breed_trava_quando_gatil_esta_acima_do_limite(c):
    s = build(c, 16)
    assert can_breed(c, s, cid(1), cid(2))[0]
    fill_to(s, kennel_slots(c, s) + 1)
    assert kennel_over_limit(c, s)
    with pytest.raises(IllegalAction):
        start_breed(c, s, cid(1), cid(2))
    start_breed(c, s, cid(1), cid(2), enforce_limits=False)     # a flag explicita desliga
    assert len(s.breeding) == 1


def test_adopt_com_flag_false_ignora_a_capacidade(c):
    s = build(c, 12)
    fill_to(s, kennel_slots(c, s))
    novo = new_cat(s)
    pending(s, [novo])
    adopt(c, s, novo.id, enforce_capacity=False)
    assert occupied(s) == kennel_slots(c, s) + 1


# ------------------------------------------------------------ migracao v1 -> v2
def v1_de(save: SaveData) -> dict:
    d = save_to_dict(save)
    d.pop("legacy_capacity", None)
    d["schema_version"] = 1
    for k in ("prestige", "areas_unlocked", "rations", "decorations_owned",
              "first_league_win_claimed", "lifetime"):
        d.pop(k)
    for cat in d["cats"]:
        for k in ("generation", "parents", "history"):
            cat.pop(k)
    for b in d["breeding"]:
        b.pop("ration")
        b.pop("ration_choice")
    return d


def test_migracao_v1_com_mais_gatos_que_as_vagas_iniciais_grava_o_campo(c):
    n = c.shop["start"]["slots"] + 3
    s = save_from_dict(v1_de(build(c, n)), c)
    assert s.migrated_from == 1 and s.legacy_capacity == n
    assert kennel_capacity(c, s) == n
    d = save_to_dict(s)
    assert d["legacy_capacity"] == n and list(VALIDATOR.iter_errors(d)) == []


@pytest.mark.parametrize("delta", [0, -1, -6])
def test_migracao_v1_com_gatos_ate_as_vagas_iniciais_nao_grava_o_campo(c, delta):
    n = c.shop["start"]["slots"] + delta
    s = save_from_dict(v1_de(build(c, n)), c)
    assert s.legacy_capacity == 0
    assert "legacy_capacity" not in save_to_dict(s)


def test_migracao_v1_com_12_gatos_nao_gera_legado(c):
    assert save_from_dict(v1_de(build(c, 12)), c).legacy_capacity == 0


def test_migracao_e_idempotente_com_legado(c):
    v1 = v1_de(build(c, c.shop["start"]["slots"] + 4))
    primeira = migrate_save_dict(copy.deepcopy(v1), c)
    segunda = migrate_save_dict(copy.deepcopy(primeira), c)
    assert primeira == segunda
    assert primeira["legacy_capacity"] == c.shop["start"]["slots"] + 4
    de_volta = save_to_dict(save_from_dict(copy.deepcopy(primeira), c))
    assert de_volta == save_to_dict(save_from_dict(copy.deepcopy(de_volta), c))
    assert de_volta["legacy_capacity"] == primeira["legacy_capacity"]


def test_migrar_save_v2_nao_inventa_legado(c):
    d = save_to_dict(build(c, 14))
    out = migrate_save_dict(copy.deepcopy(d), c)
    assert "legacy_capacity" not in out


# ------------------------------------------------------------ liga da run
def uma_run(c):
    return new_run(c, Random(0), available_cats(build(c, 14))[:12])


def test_run_json_tem_league_1():
    d = json.loads((DATA / "run.json").read_text("utf-8"))
    assert d["league"] == 1


def test_run_nova_carrega_league_do_json(c):
    assert _league(uma_run(c)) == 1


def test_league_ausente_vale_1(c):
    run = uma_run(c)
    run.cfg = {k: v for k, v in run.cfg.items() if k != "league"}
    assert _league(run) == DEFAULT_LEAGUE == 1


def test_league_valida_e_respeitada(c):
    run = uma_run(c)
    run.cfg = {**run.cfg, "league": 3}
    assert _league(run) == 3


@pytest.mark.parametrize("valor", [0, -1, "1", 1.0, 1.5, None, True, [1]])
def test_league_invalida_levanta_value_error(c, valor):
    run = uma_run(c)
    run.cfg = {**run.cfg, "league": valor}
    with pytest.raises(ValueError):
        _league(run)


# ------------------------------------------------------------ consultar nao grava
def forte(c) -> SaveData:
    s = set_strong_breeds(c, build(c, 14, breeds_n=6))
    s.prestige = 1                      # marcos ja atingidos, mas o campo guardado e antigo
    s.coins = 500
    return s


def test_area_status_nao_grava_no_save(c):
    s = forte(c)
    antes = save_to_dict(s)
    for a in c.shop["areas"]:
        area_status(c, s, a["id"])
    areas_status(c, s)
    assert save_to_dict(s) == antes and s.prestige == 1


def test_rations_catalog_nao_grava_no_save(c):
    s = forte(c)
    antes = save_to_dict(s)
    rations_catalog(c, s)
    assert save_to_dict(s) == antes and s.prestige == 1


def test_next_goal_nao_grava_no_save(c):
    s = forte(c)
    antes = save_to_dict(s)
    next_goal(c, s)
    assert save_to_dict(s) == antes and s.prestige == 1
