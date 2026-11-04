"""Areas, vagas, gatil cheio e decoracoes (Fase 10a, T13.2).

Fonte: especificacao 10a, secoes 1 (areas), 3 (limite do gatil) e 6 (decoracao).
Vagas: 18 no inicio, +2 por area, maximo 30. Casais: 1/2/3 (areas 3 e 5)."""
from __future__ import annotations

import json
import shutil
from random import Random

import pytest

from core import (advance_after_run, available_areas, available_cats,
                  areas_blocked_by_coins, areas_blocked_by_prestige, areas_status, adopt,
                  area_status, buy_decoration, can_adopt, can_donate, can_start_breed,
                  couples_allowed, decoration_catalog, donate_cat, donate_offer,
                  donation_value, kennel_over_limit, kennel_slots, kittens_in_basket,
                  load_content, next_area, next_goal, occupied, room_candidates,
                  save_to_dict, start_breed, unlock_area)
from core.types import IllegalAction
from economia_helpers import (DATA, build, cid, content as _content, fill_to, new_cat, set_strong_breeds,
                              pending, unlock_all_possible)

M, F = cid(1), cid(2)


@pytest.fixture(scope="module")
def c():
    return _content()


@pytest.fixture
def save(c):
    return build(c, 16, breeds_n=1)


def ids_areas(c) -> list[str]:
    return [a["id"] for a in sorted(c.shop["areas"], key=lambda a: a["order"])]


def preco(c, n: int) -> int:
    """Preco (moedas) da area de ordem n (1-based), lido de data/shop.json."""
    return sorted(c.shop["areas"], key=lambda a: a["order"])[n - 1]["price"]


def p3(c, s):
    """Prestigio 3: liga 1 vencida + 5 racas na colecao."""
    s.progress["leagues_cleared"] = 1
    set_strong_breeds(c, s)
    return s


# ------------------------------------------------------------ vagas
def test_gatil_comeca_com_18_vagas(c, save):
    assert kennel_slots(c, save) == 18


@pytest.mark.parametrize("n, esperado", [(0, 18), (1, 20), (2, 22), (3, 24), (4, 26),
                                         (5, 28), (6, 30)])
def test_cada_area_comprada_da_mais_2_vagas_ate_30(c, save, n, esperado):
    save.areas_unlocked = ids_areas(c)[:n]
    assert kennel_slots(c, save) == esperado


def test_vagas_nunca_passam_de_30(c, save):
    save.areas_unlocked = ids_areas(c)
    assert kennel_slots(c, save) == 30 == c.shop["max_slots"]


def test_comprar_area_pela_api_soma_2_vagas_e_devolve_o_resumo(c, save):
    p1 = preco(c, 1)
    save.coins = p1 + 5
    r = unlock_area(c, save, ids_areas(c)[0])
    assert (r.price, r.slots_bonus, r.slots_after, r.coins_left) == (p1, 2, 20, 5)
    assert save.coins == 5 and kennel_slots(c, save) == 20
    assert save.areas_unlocked == [ids_areas(c)[0]]


def test_areas_na_ordem_com_precos_da_especificacao(c):
    precos = [a["price"] for a in sorted(c.shop["areas"], key=lambda a: a["order"])]
    prest = [a["prestige_required"] for a in sorted(c.shop["areas"], key=lambda a: a["order"])]
    assert precos == [8, 25, 40, 60, 85, 115]
    assert prest == [1, 1, 1, 3, 4, 5]


# ------------------------------------------------------------ unlock_area: validacoes
def test_unlock_area_inexistente_falha_sem_alterar_o_save(c, save):
    save.coins = 500
    antes = save_to_dict(save)
    with pytest.raises(IllegalAction):
        unlock_area(c, save, "area-que-nao-existe")
    assert save_to_dict(save) == antes


def test_unlock_area_duplicada_falha_sem_alterar_o_save(c, save):
    save.coins = 500
    unlock_area(c, save, ids_areas(c)[0])
    antes = save_to_dict(save)
    with pytest.raises(IllegalAction):
        unlock_area(c, save, ids_areas(c)[0])
    assert save_to_dict(save) == antes


def test_unlock_area_fora_de_ordem_falha_sem_alterar_o_save(c, save):
    save.coins = 500
    antes = save_to_dict(save)
    with pytest.raises(IllegalAction):
        unlock_area(c, save, ids_areas(c)[1])
    assert save_to_dict(save) == antes


def test_unlock_area_sem_prestigio_falha_mesmo_com_moedas(c, save):
    """Area 4 pede Prestigio 3; o save e de Prestigio 1."""
    save.coins = 1000
    for a in ids_areas(c)[:3]:
        unlock_area(c, save, a)
    antes = save_to_dict(save)
    with pytest.raises(IllegalAction):
        unlock_area(c, save, ids_areas(c)[3])
    assert save_to_dict(save) == antes


def test_unlock_area_sem_moedas_suficientes_falha_sem_debitar(c, save):
    save.coins = preco(c, 1) - 1
    antes = save_to_dict(save)
    with pytest.raises(IllegalAction):
        unlock_area(c, save, ids_areas(c)[0])
    assert save_to_dict(save) == antes and save.coins == preco(c, 1) - 1


def test_unlock_area_com_exatamente_o_preco_zera_o_saldo(c, save):
    save.coins = preco(c, 1)
    assert unlock_area(c, save, ids_areas(c)[0]).coins_left == 0
    assert save.coins == 0


@pytest.mark.parametrize("n", [4, 5])
def test_areas_5_e_6_ficam_travadas_na_10a_mesmo_rico_e_com_prestigio_3(c, save, n):
    p3(c, save)
    save.coins = 100000
    save.areas_unlocked = ids_areas(c)[:n]
    save.prestige = 3
    with pytest.raises(IllegalAction):
        unlock_area(c, save, ids_areas(c)[n])
    assert save.prestige == 3 and len(save.areas_unlocked) == n


def test_com_prestigio_3_e_dinheiro_as_quatro_primeiras_abrem_e_vagas_vao_a_26(c, save):
    p3(c, save)
    save.coins = sum(preco(c, n) for n in (1, 2, 3, 4))
    for a in ids_areas(c)[:4]:
        unlock_area(c, save, a)
    assert save.coins == 0 and kennel_slots(c, save) == 26
    assert next_area(c, save)["id"] == ids_areas(c)[4]
    assert areas_blocked_by_prestige(c, save)[0].id == ids_areas(c)[4]


# ------------------------------------------------------------ consultas de area
def test_status_das_areas_no_comeco(c, save):
    st = areas_status(c, save)
    assert [s.state for s in st] == ["blocked_coins"] + ["queued"] * 5
    assert st[0].missing_coins == preco(c, 1) and st[0].missing_prestige == 0


def test_status_vira_available_com_moedas_e_unlocked_depois_de_comprar(c, save):
    save.coins = preco(c, 1)
    assert [a.id for a in available_areas(c, save)] == [ids_areas(c)[0]]
    unlock_area(c, save, ids_areas(c)[0])
    assert area_status(c, save, ids_areas(c)[0]).state == "unlocked"


def test_status_de_area_inexistente_levanta(c, save):
    with pytest.raises(IllegalAction):
        area_status(c, save, "xyz")


def test_bloqueada_por_prestigio_aparece_na_lista_certa(c, save):
    save.coins = 1000
    save.areas_unlocked = ids_areas(c)[:3]
    assert [a.id for a in areas_blocked_by_prestige(c, save)] == [ids_areas(c)[3]]
    assert areas_blocked_by_prestige(c, save)[0].missing_prestige == 2
    assert areas_blocked_by_coins(c, save) == []


# ------------------------------------------------------------ casais e filhotes
@pytest.mark.parametrize("areas, casais", [(0, 1), (1, 1), (2, 1), (3, 2), (4, 2),
                                           (5, 3), (6, 3)])
def test_casais_permitidos_1_2_3_conforme_as_areas(c, save, areas, casais):
    save.areas_unlocked = ids_areas(c)[:areas]
    assert couples_allowed(c, save) == casais


def test_segundo_casal_so_abre_com_a_area_3(c, save):
    start_breed(c, save, M, F, enforce_limits=True)
    ok, motivo = can_start_breed(c, save, cid(3), cid(4))
    assert not ok and motivo
    with pytest.raises(IllegalAction):
        start_breed(c, save, cid(3), cid(4), enforce_limits=True)
    save.areas_unlocked = ids_areas(c)[:3]
    assert can_start_breed(c, save, cid(3), cid(4))[0]
    start_breed(c, save, cid(3), cid(4), enforce_limits=True)
    assert len(save.breeding) == 2


def test_filhotes_ficam_na_cesta_ate_a_area_2(c, save):
    assert kittens_in_basket(c, save) is True
    save.areas_unlocked = ids_areas(c)[:1]
    assert kittens_in_basket(c, save) is True
    save.areas_unlocked = ids_areas(c)[:2]
    assert kittens_in_basket(c, save) is False


# ------------------------------------------------------------ gatil cheio: consultas
def test_occupied_conta_adultos_filhotes_e_gatos_em_breed(c, save):
    fill_to(save, 18)
    start_breed(c, save, M, F)
    assert occupied(save) == 18 == len(save.cats)


def test_oferta_pendente_nao_ocupa_vaga(c, save):
    pending(save, [new_cat(save)])
    assert occupied(save) == 16


def test_can_adopt_livre_com_vaga_cheio_ou_acima_recusa(c, save):
    assert can_adopt(c, save)[0]                    # 16/18
    fill_to(save, 17)
    assert can_adopt(c, save)[0]                    # 17/18
    fill_to(save, 18)
    ok, motivo = can_adopt(c, save)                 # 18/18
    assert not ok and motivo
    fill_to(save, 19)
    ok, motivo = can_adopt(c, save)                 # 19/18
    assert not ok and motivo
    assert kennel_over_limit(c, save)


def test_can_start_breed_acima_do_limite_recusa_e_no_limite_exato_permite(c, save):
    """Spec: abertura de novo breed fica bloqueada ate o gatil VOLTAR ao limite."""
    fill_to(save, 18)
    assert not kennel_over_limit(c, save)
    assert can_start_breed(c, save, M, F)[0]
    fill_to(save, 19)
    ok, motivo = can_start_breed(c, save, M, F)
    assert not ok and motivo


# ------------------------------------------------------------ gatil cheio: adocao
def _gatil_cheio_com_oferta(c, n_oferta=2):
    s = build(c, 14)
    fill_to(s, 18)                                  # 14 adultos + 4 filhotes
    ofertas = [new_cat(s, iv_atk=5, iv_hp=5) for _ in range(n_oferta)]
    pending(s, ofertas)
    return s, ofertas


def test_adocao_com_gatil_cheio_recusa_e_a_oferta_continua_intacta(c):
    s, oferta = _gatil_cheio_com_oferta(c)
    antes = save_to_dict(s)
    with pytest.raises(IllegalAction):
        adopt(c, s, oferta[0].id, enforce_capacity=True)
    assert save_to_dict(s) == antes
    assert [x.id for x in s.pending_adoption["cats"]] == [o.id for o in oferta]


def test_doar_um_gato_da_colecao_abre_espaco_para_adotar(c):
    s, oferta = _gatil_cheio_com_oferta(c)
    candidatos = room_candidates(c, s)
    assert candidatos
    alvo = candidatos[0]
    moedas = s.coins
    valor = donate_cat(c, s, alvo.id)
    assert valor == donation_value(c, alvo) or valor >= 0
    assert s.coins == moedas + valor and occupied(s) == 17
    assert alvo.id not in [x.id for x in s.cats]
    adopt(c, s, oferta[0].id, enforce_capacity=True)
    assert oferta[0].id in [x.id for x in s.cats] and occupied(s) == 18


def test_doar_o_gato_novo_mantem_a_colecao_e_paga_moedas(c):
    s, oferta = _gatil_cheio_com_oferta(c, 1)
    cats_antes = [x.id for x in s.cats]
    valor = donate_offer(c, s, oferta[0].id)
    assert valor == donation_value(c, oferta[0]) and valor > 0
    assert s.coins == valor and [x.id for x in s.cats] == cats_antes
    assert s.pending_adoption is None


def test_nunca_ha_perda_automatica_de_gato_so_doacoes_explicitas(c):
    s, oferta = _gatil_cheio_com_oferta(c, 2)
    total = len(s.cats) + len(s.pending_adoption["cats"])
    with pytest.raises(IllegalAction):
        adopt(c, s, oferta[0].id, enforce_capacity=True)
    assert len(s.cats) + len(s.pending_adoption["cats"]) == total
    donate_cat(c, s, room_candidates(c, s)[0].id)           # 1 doacao explicita
    adopt(c, s, oferta[0].id, enforce_capacity=True)
    donate_offer(c, s, oferta[1].id)                         # 2a doacao explicita
    assert len(s.cats) + len(s.pending_adoption["cats"] if s.pending_adoption else []) \
        == total - 2


def test_adotar_gato_que_nao_esta_na_oferta_falha_mesmo_com_vaga(c, save):
    pending(save, [new_cat(save)])
    with pytest.raises(IllegalAction):
        adopt(c, save, "c-999999", enforce_capacity=True)


def test_adocao_com_vaga_livre_funciona_com_enforcement(c, save):
    novo = new_cat(save, iv_atk=4, iv_hp=4)
    pending(save, [novo])
    assert adopt(c, save, novo.id, enforce_capacity=True).id == novo.id
    assert occupied(save) == 17 and save.pending_adoption is None


# ------------------------------------------------------------ nao doar abaixo de 12 adultos
def test_nao_doa_adulto_se_sobrarem_menos_de_12_adultos_disponiveis(c):
    s = build(c, 12)
    fill_to(s, 18)                                   # 12 adultos + 6 filhotes
    alvo = s.cats[0].id
    ok, motivo = can_donate(c, s, alvo)
    assert not ok and motivo
    with pytest.raises(IllegalAction):
        donate_cat(c, s, alvo)
    assert len(s.cats) == 18


def test_com_12_adultos_so_filhotes_sao_candidatos_a_doacao(c):
    s = build(c, 12)
    fill_to(s, 18)
    cand = room_candidates(c, s)
    assert cand and all(x.stage == "kitten" for x in cand)
    assert len(cand) == 6


def test_com_13_adultos_um_adulto_pode_ser_doado_e_fica_exatamente_12(c):
    s = build(c, 13)
    fill_to(s, 18)
    donate_cat(c, s, s.cats[12].id)
    assert len(available_cats(s)) == 12


def test_candidatos_excluem_gatos_em_breed(c):
    s = build(c, 16)
    fill_to(s, 18)
    start_breed(c, s, M, F)
    ids = {x.id for x in room_candidates(c, s)}
    assert M not in ids and F not in ids


def test_gatil_cheio_sem_candidato_ainda_permite_doar_o_novo(c):
    """12 disponiveis + 6 adultos em 3 casais: ninguem da colecao pode ser doado."""
    s = build(c, 18)
    s.breeding = [{"male": cid(1 + 2 * i), "female": cid(2 + 2 * i), "runs_left": 2,
                   "ration": None, "ration_choice": None} for i in range(3)]
    s.deck = [cid(i) for i in range(7, 19)]
    assert room_candidates(c, s) == []
    novo = new_cat(s)
    pending(s, [novo])
    with pytest.raises(IllegalAction):
        adopt(c, s, novo.id, enforce_capacity=True)
    assert donate_offer(c, s, novo.id) >= 0 and s.pending_adoption is None


# ------------------------------------------------------------ nascimento com gatil cheio
def _quase_nascendo(c):
    """18/18 (16 adultos + 2 filhotes), casal M/F com 1 run restante."""
    s = build(c, 16)
    fill_to(s, 18)
    start_breed(c, s, M, F)
    s.breeding[0]["runs_left"] = 1
    return s


def test_nascimento_com_gatil_cheio_nasce_mesmo_assim_e_passa_do_limite(c):
    s = _quase_nascendo(c)
    assert occupied(s) == kennel_slots(c, s) == 18
    out = advance_after_run(c, s, Random(11), 3)
    assert 1 <= len(out.born) <= 3
    assert occupied(s) == 18 + len(out.born) and kennel_over_limit(c, s)


def test_depois_do_nascimento_adocao_e_novo_breed_ficam_bloqueados(c):
    s = _quase_nascendo(c)
    advance_after_run(c, s, Random(11), 3)
    assert not can_adopt(c, s)[0]
    assert not can_start_breed(c, s, cid(3), cid(4))[0]
    novo = new_cat(s)
    pending(s, [novo])
    with pytest.raises(IllegalAction):
        adopt(c, s, novo.id, enforce_capacity=True)
    with pytest.raises(IllegalAction):
        start_breed(c, s, cid(3), cid(4), enforce_limits=True)


def test_voltando_ao_limite_o_breed_abre_e_com_uma_vaga_livre_a_adocao_tambem(c):
    s = _quase_nascendo(c)
    advance_after_run(c, s, Random(11), 3)
    while kennel_over_limit(c, s):
        donate_cat(c, s, room_candidates(c, s)[0].id)
    assert occupied(s) == 18
    assert can_start_breed(c, s, cid(3), cid(4))[0]
    assert not can_adopt(c, s)[0]                      # cheio, nao acima: ainda pede doar
    donate_cat(c, s, room_candidates(c, s)[0].id)
    assert can_adopt(c, s)[0]


# ------------------------------------------------------------ invariante 12 + 2 + 3
def test_invariante_vagas_iniciais_cobrem_deck_casal_e_ninhada_maxima(c):
    deck = c.rules["duel"]["deck_size"]
    litter = c.rules["breed"]["litter_max"]
    assert (deck, litter) == (12, 3)
    assert c.shop["start"]["slots"] >= deck + 2 + litter == 17


def test_com_vagas_iniciais_um_breed_completo_nunca_deixa_o_gatil_acima_do_limite(c):
    for semente in range(40):             # pior caso (ninhada de 3) aparece em algumas seeds
        t = build(c, 14)
        start_breed(c, t, M, F, enforce_limits=True)
        t.breeding[0]["runs_left"] = 1
        out = advance_after_run(c, t, Random(semente), 3)
        assert not kennel_over_limit(c, t)
        assert occupied(t) <= 14 + 3 <= kennel_slots(c, t)
        assert len(out.born) <= 3


def test_conteudo_com_menos_de_17_vagas_iniciais_nao_carrega(tmp_path):
    pasta = tmp_path / "data"
    shutil.copytree(DATA, pasta)
    shop = json.loads((pasta / "shop.json").read_text("utf-8"))
    shop["start"]["slots"], shop["max_slots"] = 16, 28
    (pasta / "shop.json").write_text(json.dumps(shop), "utf-8")
    with pytest.raises(ValueError):
        load_content(pasta)
    shop["start"]["slots"], shop["max_slots"] = 17, 29
    (pasta / "shop.json").write_text(json.dumps(shop), "utf-8")
    assert load_content(pasta).shop["start"]["slots"] == 17


# ------------------------------------------------------------ decoracoes
def test_decoracao_exige_a_area_dela_e_falha_sem_alterar_o_save(c, save):
    save.coins = 500
    antes = save_to_dict(save)
    with pytest.raises(IllegalAction):
        buy_decoration(c, save, "deco-novelo")
    assert save_to_dict(save) == antes
    estados = {d["id"]: d["state"] for d in decoration_catalog(c, save)}
    assert estados["deco-novelo"] == "locked_area"


def test_decoracao_apos_a_area_debita_o_preco_e_fica_na_posse(c, save):
    save.coins = preco(c, 1) + 15
    unlock_area(c, save, ids_areas(c)[0])          # -preco da area 1
    d = buy_decoration(c, save, "deco-novelo")      # -10
    assert d["id"] == "deco-novelo" and save.coins == 5
    assert save.decorations_owned == ["deco-novelo"]
    estados = {x["id"]: x["state"] for x in decoration_catalog(c, save)}
    assert estados["deco-novelo"] == "owned" and estados["deco-ratinho"] == "available"


def test_comprar_a_mesma_decoracao_de_novo_falha_sem_debitar(c, save):
    save.coins = 100
    unlock_area(c, save, ids_areas(c)[0])
    buy_decoration(c, save, "deco-novelo")
    antes = save_to_dict(save)
    with pytest.raises(IllegalAction):
        buy_decoration(c, save, "deco-novelo")
    assert save_to_dict(save) == antes


def test_decoracao_sem_moedas_falha_sem_alterar_o_save(c, save):
    save.areas_unlocked = ids_areas(c)[:1]
    save.coins = 9
    antes = save_to_dict(save)
    with pytest.raises(IllegalAction):
        buy_decoration(c, save, "deco-novelo")
    assert save_to_dict(save) == antes


def test_decoracao_inexistente_falha(c, save):
    save.coins = 100
    with pytest.raises(IllegalAction):
        buy_decoration(c, save, "deco-nao-existe")


def test_decoracao_do_jardim_so_depois_da_area_4(c, save):
    p3(c, save)
    save.coins = 10000
    save.prestige = 3
    for a in ids_areas(c)[:3]:
        unlock_area(c, save, a)
    with pytest.raises(IllegalAction):
        buy_decoration(c, save, "deco-banco-arvore")
    unlock_area(c, save, ids_areas(c)[3])
    assert buy_decoration(c, save, "deco-banco-arvore")["price"] == 35


def test_decoracao_do_pomar_continua_inacessivel_na_10a(c, save):
    p3(c, save)
    save.coins = 100000
    save.prestige = 3
    unlock_all_possible(c, save)
    with pytest.raises(IllegalAction):
        buy_decoration(c, save, "deco-arvore-grande")


# ------------------------------------------------------------ proxima meta
def test_proxima_meta_no_comeco_e_a_primeira_area(c, save):
    save.coins = 4
    g = next_goal(c, save)
    assert (g["kind"], g["id"], g["price"], g["missing"]) == ("area", ids_areas(c)[0], preco(c, 1), preco(c, 1) - 4)


def test_proxima_meta_e_o_item_mais_barato_liberado(c, save):
    save.coins = preco(c, 1) + 5
    unlock_area(c, save, ids_areas(c)[0])
    g = next_goal(c, save)                         # area 2 custa 25; deco-novelo 10
    assert (g["kind"], g["id"], g["price"]) == ("decoration", "deco-novelo", 10)
    assert g["missing"] == 5


def test_proxima_meta_missing_nunca_negativo(c, save):
    save.coins = 999
    assert next_goal(c, save)["missing"] == 0


def test_proxima_meta_ignora_item_bloqueado_por_prestigio(c, save):
    save.coins = 1000
    save.areas_unlocked = ids_areas(c)[:3]
    g = next_goal(c, save)                          # area 4 pede P3; sobram as decoracoes
    assert g["kind"] == "decoration" and g["price"] == 10
