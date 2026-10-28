"""Adocao pos-run (Fase 5b): pesos, quantidade, doacao, pity, adopt/donate, save_deck_draft.

Fonte: regras do Renatho de 2026-10-28 e CONTRATOS 1.9 / 2.5 (so a API publica).
"""
from __future__ import annotations

import copy
import json
from dataclasses import asdict
from pathlib import Path
from random import Random

import pytest
from jsonschema import Draft202012Validator

from core import (Cat, SaveData, adopt, adoption_count, adoption_weights, available_cats,
                  can_donate, create_adoption, donate_cat, donate_offer, donation_value, get_cat,
                  has_pending_adoption, load_content, new_game, new_run_from_save,
                  read_save, roll_cat, save_deck_draft, save_from_dict, save_to_dict,
                  set_deck, write_save)
from core.ai import choose_action
from core.duel import apply_action
from core.types import IllegalAction

DATA = Path(__file__).resolve().parent.parent / "data"
SCHEMA = json.loads((DATA / "schemas" / "save.schema.json").read_text("utf-8"))
BASE = {1: 30, 2: 25, 3: 25, 4: 15, 5: 5}


@pytest.fixture(scope="module")
def content():
    return load_content(DATA)


@pytest.fixture
def save(content):
    return new_game(content, Random(3))


def soma(c: Cat) -> int:
    return c.iv_atk + c.iv_hp


def pend(save):
    return save.pending_adoption["cats"] if save.pending_adoption else []


def mk_cat(content, cid, a, h, stage="adult", **kw):
    return Cat(id=cid, breed=next(iter(content.breeds)), sex="M",
               nature=next(iter(content.natures)), iv_atk=a, iv_hp=h, stage=stage, **kw)


def extra_cat(content, save, seed=7):
    c = roll_cat(content, Random(seed))
    c.id = f"c-{save.next_cat_id:06d}"
    save.next_cat_id += 1
    save.cats.append(c)
    return c


def pesos(content, n):
    return {int(k): v for k, v in adoption_weights(content, n).items()}


# ------------------------------------------------------------ adoption_weights
def test_pesos_com_zero_nos_sao_os_pesos_base(content):
    assert pesos(content, 0) == BASE


@pytest.mark.parametrize("n", [1, 2, 3, 7])
def test_cada_no_desloca_dois_pontos_do_iv1_para_o_iv5(content, n):
    w = pesos(content, n)
    assert w[1] == 30 - 2 * n
    assert w[5] == 5 + 2 * n
    assert (w[2], w[3], w[4]) == (25, 25, 15)


def test_peso_do_iv1_para_em_zero_e_nunca_fica_negativo(content):
    w = pesos(content, 15)
    assert w[1] == 0 and w[5] == 35
    assert all(v >= 0 for v in w.values())


def test_soma_dos_pesos_e_constante(content):
    total = sum(BASE.values())
    for n in range(0, 25):
        assert sum(pesos(content, n).values()) == total


@pytest.mark.parametrize("n", [16, 50, 1000])
def test_n_grande_estabiliza_no_deslocamento_maximo(content, n):
    assert pesos(content, n) == {1: 0, 2: 25, 3: 25, 4: 15, 5: 35}


# ------------------------------------------------------------ adoption_count
@pytest.mark.parametrize("nos,esperado", [(0, 0), (1, 0), (2, 1), (3, 1), (5, 2), (6, 3)])
def test_quantidade_sem_vitoria_e_nos_div_2(content, nos, esperado):
    assert adoption_count(content, nos, "derrota") == esperado


@pytest.mark.parametrize("nos,esperado", [(0, 2), (1, 2), (2, 3), (3, 3), (5, 4), (6, 5)])
def test_quantidade_com_vitoria_soma_dois(content, nos, esperado):
    assert adoption_count(content, nos, "vitoria") == esperado


def test_abandono_conta_como_derrota(content):
    for nos in range(0, 7):
        assert adoption_count(content, nos, "abandono") == adoption_count(content, nos, "derrota")


# ------------------------------------------------------------ donation_value
@pytest.mark.parametrize("s,moedas", [(2, 1), (3, 1), (4, 1), (5, 2), (6, 2), (7, 3),
                                      (8, 4), (9, 4), (10, 5)])
def test_doacao_por_faixa_de_soma(content, s, moedas):
    a = min(5, s - 1)
    b = s - a
    assert donation_value(content, mk_cat(content, "x", a, b)) == moedas


def test_doacao_independe_da_distribuicao_atk_hp(content):
    assert donation_value(content, mk_cat(content, "x", 1, 5)) == \
        donation_value(content, mk_cat(content, "y", 3, 3))


@pytest.mark.parametrize("s,adulto", [(2, 1), (4, 1), (5, 2), (7, 3), (8, 4), (10, 5)])
def test_filhote_vale_metade_arredondando_para_baixo(content, s, adulto):
    a = min(5, s - 1)
    k = mk_cat(content, "k", a, s - a, stage="kitten")
    assert donation_value(content, k) == adulto // 2


# ------------------------------------------------------------ create_adoption
def test_create_adoption_e_deterministico_por_seed(content):
    r = []
    for _ in range(2):
        s = new_game(content, Random(1))
        create_adoption(content, s, Random(5), "vitoria", 4)
        r.append([asdict(c) for c in pend(s)])
    assert r[0] == r[1] and len(r[0]) == 4


def test_seeds_diferentes_dao_ofertas_diferentes(content):
    ofertas = set()
    for seed in range(5):
        s = new_game(content, Random(1))
        create_adoption(content, s, Random(seed), "vitoria", 4)
        ofertas.add(tuple((c.breed, c.iv_atk, c.iv_hp, c.nature, c.sex) for c in pend(s)))
    assert len(ofertas) > 1


def test_ids_reservados_continuam_o_next_cat_id(content, save):
    antes = save.next_cat_id
    colecao = {c.id for c in save.cats}
    create_adoption(content, save, Random(2), "vitoria", 4)
    ids = [c.id for c in pend(save)]
    assert ids == [f"c-{i:06d}" for i in range(antes, antes + 4)]
    assert save.next_cat_id == antes + 4
    assert not set(ids) & colecao


def test_oferta_so_tem_gatos_adultos_validos(content, save):
    create_adoption(content, save, Random(2), "vitoria", 6)
    for c in pend(save):
        assert c.stage == "adult" and c.rest_runs_left == 0
        assert 1 <= c.iv_atk <= 5 and 1 <= c.iv_hp <= 5
        assert c.breed in content.breeds and c.nature in content.natures
        assert c.sex in ("M", "F")


def test_pending_adoption_fica_preenchido(content, save):
    create_adoption(content, save, Random(2), "vitoria", 4)
    assert has_pending_adoption(save)
    assert save.pending_adoption["result"] == "vitoria"
    assert save.pending_adoption["nodes_cleared"] == 4
    assert len(save.pending_adoption["cats"]) == 4


def test_zero_gatos_nao_deixa_pendente(content, save):
    antes = save.next_cat_id
    create_adoption(content, save, Random(2), "derrota", 1)
    assert save.pending_adoption is None
    assert not has_pending_adoption(save)
    assert save.next_cat_id == antes


def test_segunda_oferta_com_pendente_e_ilegal(content, save):
    create_adoption(content, save, Random(2), "vitoria", 4)
    snap = save_to_dict(save)
    with pytest.raises(IllegalAction):
        create_adoption(content, save, Random(3), "vitoria", 4)
    assert save_to_dict(save) == snap


def test_best_distance_so_sobe(content, save):
    save.progress["best_distance"] = 3
    create_adoption(content, save, Random(1), "derrota", 2)
    assert save.progress["best_distance"] == 3
    for c in list(pend(save)):
        donate_offer(content, save, c.id)
    create_adoption(content, save, Random(1), "derrota", 5)
    assert save.progress["best_distance"] == 5


# ------------------------------------------------------------ qualidade
def media_iv(content, nos, amostras=300, seed=11):
    rng = Random(seed)
    total = n = 0
    for _ in range(amostras):
        s = SaveData()
        create_adoption(content, s, rng, "vitoria", nos)
        for c in pend(s):
            total += c.iv_atk + c.iv_hp
            n += 2
    return total / n


def test_mais_nos_dao_iv_medio_maior(content):
    m0, m4, m10 = media_iv(content, 0), media_iv(content, 4), media_iv(content, 10)
    assert m0 < m4 < m10


# ------------------------------------------------------------ pity
def limpa(content, s):
    for c in list(pend(s)):
        donate_offer(content, s, c.id)


def oferta_sem_alto(content, s, nos=2, result="derrota"):
    """Cria oferta de 1 gato sem alto (tenta seeds em copias) e aplica no save s."""
    for seed in range(500):
        t = copy.deepcopy(s)
        create_adoption(content, t, Random(seed), result, nos)
        if pend(t) and not any(soma(c) >= 8 for c in pend(t)):
            create_adoption(content, s, Random(seed), result, nos)
            return
    raise AssertionError("nao achou oferta sem gato alto")


def test_contador_sobe_em_oferta_com_gato_sem_alto(content, save):
    oferta_sem_alto(content, save)
    assert save.pity["runs_without_high_iv"] == 1
    limpa(content, save)
    oferta_sem_alto(content, save)
    assert save.pity["runs_without_high_iv"] == 2


def test_contador_zera_quando_sai_gato_alto(content, save):
    save.pity["runs_without_high_iv"] = 5
    create_adoption(content, save, Random(1), "vitoria", 0)
    assert any(soma(c) >= 8 for c in pend(save))
    assert save.pity["runs_without_high_iv"] == 0


def test_contador_zera_com_gato_alto_natural_antes_do_pity(content, save):
    for seed in range(300):
        s = new_game(content, Random(1))
        s.pity["runs_without_high_iv"] = 2
        create_adoption(content, s, Random(seed), "vitoria", 6)
        if any(soma(c) >= 8 for c in pend(s)):
            assert s.pity["runs_without_high_iv"] == 0
            return
    raise AssertionError("nenhum gato alto natural")


@pytest.mark.parametrize("contador", [0, 4, 5, 9])
@pytest.mark.parametrize("nos,result", [(0, "abandono"), (1, "derrota")])
def test_oferta_vazia_nao_muda_contador_nem_cria_gato(content, save, contador, nos, result):
    save.pity["runs_without_high_iv"] = contador
    antes = save.next_cat_id
    create_adoption(content, save, Random(1), result, nos)
    assert save.pending_adoption is None
    assert save.pity["runs_without_high_iv"] == contador
    assert save.next_cat_id == antes


def test_20_abandonos_seguidos_no_no_0_nunca_dao_gato_nem_mexem_no_pity(content, save):
    save.pity["runs_without_high_iv"] = 5
    for i in range(20):
        create_adoption(content, save, Random(i), "abandono", 0)
        assert save.pending_adoption is None
    assert save.pity["runs_without_high_iv"] == 5
    assert len(save.cats) == 12


def test_best_distance_sobe_mesmo_com_oferta_vazia(content, save):
    save.progress["best_distance"] = 0
    create_adoption(content, save, Random(1), "derrota", 1)
    assert pend(save) == []
    assert save.progress["best_distance"] == 1


def test_pity_nao_dispara_com_contador_4(content, save):
    save.pity["runs_without_high_iv"] = 4
    oferta_sem_alto(content, save)
    assert save.pity["runs_without_high_iv"] == 5


def test_contador_chega_a_5_e_pity_dispara_na_oferta_seguinte(content):
    for k in range(10):
        s = new_game(content, Random(1))
        for _ in range(5):
            oferta_sem_alto(content, s)
            limpa(content, s)
        assert s.pity["runs_without_high_iv"] == 5
        create_adoption(content, s, Random(k), "derrota", 2)   # 1 gato
        assert len(pend(s)) == 1
        assert soma(pend(s)[0]) >= 8
        assert s.pity["runs_without_high_iv"] == 0


def test_pity_troca_o_gato_de_menor_soma_e_mantem_tamanho(content):
    for seed in range(40):
        ref = new_game(content, Random(1))
        create_adoption(content, ref, Random(seed), "vitoria", 0)   # sem pity
        s = new_game(content, Random(1))
        s.pity["runs_without_high_iv"] = 5
        create_adoption(content, s, Random(seed), "vitoria", 0)
        assert len(pend(s)) == len(pend(ref)) == 2
        assert any(soma(c) >= 8 for c in pend(s))
        assert s.pity["runs_without_high_iv"] == 0
        if not any(soma(c) >= 8 for c in pend(ref)):
            menor = min(pend(ref), key=soma)
            ficou = [c for c in pend(ref) if c is not menor]
            assert [(c.breed, c.iv_atk, c.iv_hp) for c in ficou][0] in                 [(c.breed, c.iv_atk, c.iv_hp) for c in pend(s)]


def test_pity_acima_de_5_tambem_dispara(content):
    s = new_game(content, Random(1))
    s.pity["runs_without_high_iv"] = 9
    create_adoption(content, s, Random(1), "vitoria", 0)
    assert any(soma(c) >= 8 for c in pend(s))


def test_200_runs_de_derrota_precoce_nunca_passam_de_5_ofertas_sem_alto(content):
    s = new_game(content, Random(1))
    rng = Random(77)
    seq = maximo = 0
    for i in range(200):
        create_adoption(content, s, rng, "derrota", 2 + i % 2)   # 1 gato
        if any(soma(c) >= 8 for c in pend(s)):
            seq = 0
        elif pend(s):
            seq += 1
        maximo = max(maximo, seq)
        limpa(content, s)
    assert maximo <= 5


def test_300_runs_mistas_ninguem_recebe_alto_garantido_sem_5_ofertas_sem_alto(content):
    s = new_game(content, Random(1))
    rng = Random(2026)
    sem_alto = 0       # ofertas nao vazias seguidas sem gato alto
    for i in range(300):
        if i % 3 == 0:
            create_adoption(content, s, rng, "abandono", 0)
        elif i % 3 == 1:
            create_adoption(content, s, rng, "derrota", 1 + i % 4)
        else:
            create_adoption(content, s, rng, "vitoria", 6)
        if pend(s):
            if any(soma(c) >= 8 for c in pend(s)):
                sem_alto = 0
            else:
                sem_alto += 1
        assert sem_alto <= 5
        assert s.pity["runs_without_high_iv"] <= 5
        limpa(content, s)


def test_300_runs_mistas_contador_acompanha_ofertas_nao_vazias(content):
    s = new_game(content, Random(1))
    rng = Random(99)
    esperado = 0
    for i in range(300):
        nos, res = [(0, "abandono"), (1, "derrota"), (2, "derrota"), (6, "vitoria")][i % 4]
        antes = s.pity["runs_without_high_iv"]
        create_adoption(content, s, rng, res, nos)
        oferta = pend(s)
        if not oferta:
            assert s.pity["runs_without_high_iv"] == antes
        elif any(soma(c) >= 8 for c in oferta):
            assert s.pity["runs_without_high_iv"] == 0
            if antes >= 5:
                assert len(oferta) == adoption_count(content, nos, res)
        else:
            assert s.pity["runs_without_high_iv"] == antes + 1
            assert antes < 5      # com contador >= 5 sempre sai gato alto
        limpa(content, s)


# ------------------------------------------------------------ adopt
def test_adopt_move_gato_da_oferta_para_a_colecao(content, save):
    create_adoption(content, save, Random(2), "vitoria", 2)
    alvo = pend(save)[1]
    n = len(save.cats)
    cat = adopt(content, save, alvo.id)
    assert cat.id == alvo.id
    assert len(save.cats) == n + 1 and get_cat(save, alvo.id) is cat
    assert alvo.id not in [c.id for c in pend(save)]
    assert len(pend(save)) == 2


def test_adopt_mantem_nome_do_gato(content, save):
    create_adoption(content, save, Random(2), "vitoria", 2)
    c = pend(save)[0]
    c.name = "Mingau"
    adopt(content, save, c.id)
    assert get_cat(save, c.id).name == "Mingau"


def test_adopt_do_ultimo_zera_a_pendente(content, save):
    create_adoption(content, save, Random(2), "vitoria", 0)
    for c in list(pend(save)):
        adopt(content, save, c.id)
    assert save.pending_adoption is None
    create_adoption(content, save, Random(3), "vitoria", 0)   # permitido de novo
    assert has_pending_adoption(save)


def test_adopt_registra_raca_na_dex_sem_duplicar(content, save):
    save.dex["breeds_seen"] = []
    create_adoption(content, save, Random(2), "vitoria", 2)
    a, b = pend(save)[0], pend(save)[1]
    b.breed = a.breed
    adopt(content, save, a.id)
    adopt(content, save, b.id)
    assert save.dex["breeds_seen"].count(a.breed) == 1


def test_adopt_registra_gato_perfeito_na_dex(content, save):
    create_adoption(content, save, Random(2), "vitoria", 2)
    c = pend(save)[0]
    c.iv_atk = c.iv_hp = 5
    adopt(content, save, c.id)
    assert c.id in save.dex["perfect_cats"]


def test_adopt_nao_registra_perfeito_para_gato_comum(content, save):
    create_adoption(content, save, Random(2), "vitoria", 2)
    c = pend(save)[0]
    c.iv_atk, c.iv_hp = 5, 4
    adopt(content, save, c.id)
    assert c.id not in save.dex["perfect_cats"]


def test_novo_jogo_ja_registra_a_dex(content, save):
    assert set(save.dex["breeds_seen"]) == {c.breed for c in save.cats}
    perfeitos = {c.id for c in save.cats if c.iv_atk == 5 and c.iv_hp == 5}
    assert set(save.dex["perfect_cats"]) == perfeitos


def test_adopt_id_inexistente_e_erro(content, save):
    create_adoption(content, save, Random(2), "vitoria", 2)
    with pytest.raises(IllegalAction):
        adopt(content, save, "c-999999")
    assert len(pend(save)) == 3


def test_adopt_sem_pendente_e_erro(content, save):
    with pytest.raises(IllegalAction):
        adopt(content, save, "c-000001")


# ------------------------------------------------------------ donate_offer
def test_donate_offer_da_moedas_e_remove_da_pendente(content, save):
    create_adoption(content, save, Random(2), "vitoria", 2)
    c = pend(save)[0]
    esperado = donation_value(content, c)
    n = len(save.cats)
    assert donate_offer(content, save, c.id) == esperado
    assert save.coins == esperado
    assert c.id not in [x.id for x in pend(save)]
    assert len(save.cats) == n


def test_donate_offer_acumula_moedas(content, save):
    save.coins = 10
    create_adoption(content, save, Random(2), "vitoria", 2)
    total = sum(donation_value(content, c) for c in pend(save))
    for c in list(pend(save)):
        donate_offer(content, save, c.id)
    assert save.coins == 10 + total


def test_donate_offer_do_ultimo_deixa_pendente_none(content, save):
    create_adoption(content, save, Random(2), "vitoria", 0)
    for c in list(pend(save)):
        donate_offer(content, save, c.id)
    assert save.pending_adoption is None


def test_donate_offer_id_inexistente_e_erro(content, save):
    create_adoption(content, save, Random(2), "vitoria", 0)
    with pytest.raises(IllegalAction):
        donate_offer(content, save, "c-999999")
    assert save.coins == 0


def test_misturar_adotar_e_doar_na_mesma_oferta(content, save):
    create_adoption(content, save, Random(2), "vitoria", 2)
    a, b, c = pend(save)
    adopt(content, save, a.id)
    donate_offer(content, save, b.id)
    adopt(content, save, c.id)
    assert save.pending_adoption is None
    assert len(save.cats) == 14


# ------------------------------------------------------------ donate_cat
def test_donate_cat_da_moedas_e_remove_da_colecao(content, save):
    extra = extra_cat(content, save)
    valor = donation_value(content, extra)
    assert donate_cat(content, save, extra.id) == valor
    assert save.coins == valor
    assert extra.id not in [c.id for c in save.cats]


def test_donate_cat_tira_do_deck(content, save):
    extra = extra_cat(content, save)
    save.deck[0] = extra.id
    donate_cat(content, save, extra.id)
    assert extra.id not in save.deck


def test_donate_cat_recusa_se_sobrarem_menos_de_12_adultos(content, save):
    alvo = save.cats[0]
    assert len(available_cats(save)) == 12
    with pytest.raises(IllegalAction):
        donate_cat(content, save, alvo.id)
    assert len(save.cats) == 12 and save.coins == 0


def test_donate_cat_conta_so_adultos_disponiveis(content, save):
    extra_cat(content, save, 7)
    save.cats[0].rest_runs_left = 2     # 12 adultos, mas so 12-1+1... = 12 disponiveis com o extra
    assert len(available_cats(save)) == 12
    with pytest.raises(IllegalAction):
        donate_cat(content, save, save.cats[1].id)


def test_donate_cat_filhote_permitido_mesmo_com_12_adultos(content, save):
    k = mk_cat(content, "c-000500", 4, 4, stage="kitten", runs_as_kitten=0)
    save.cats.append(k)
    save.next_cat_id = 501
    assert donate_cat(content, save, k.id) == 2     # 4 moedas / 2
    assert k.id not in [c.id for c in save.cats]


def test_donate_cat_em_descanso_extra_pode_sair(content, save):
    e = extra_cat(content, save)
    e.rest_runs_left = 1       # indisponivel: nao conta para os 12
    donate_cat(content, save, e.id)
    assert e.id not in [c.id for c in save.cats]


def test_donate_cat_recusa_gato_em_breeding(content, save):
    e1 = extra_cat(content, save, 7)
    e2 = extra_cat(content, save, 8)
    save.breeding.append({"male": e1.id, "female": e2.id, "runs_left": 2})
    with pytest.raises(IllegalAction):
        donate_cat(content, save, e1.id)
    with pytest.raises(IllegalAction):
        donate_cat(content, save, e2.id)
    assert e1.id in [c.id for c in save.cats]


def test_donate_cat_inexistente_e_erro(content, save):
    with pytest.raises(IllegalAction):
        donate_cat(content, save, "c-999999")


# ------------------------------------------------------------ can_donate
def test_can_donate_ok_com_adulto_fora_do_minimo(content, save):
    e = extra_cat(content, save)
    assert can_donate(content, save, e.id) == (True, "")


def test_can_donate_recusa_quando_sobrariam_menos_de_12(content, save):
    ok, motivo = can_donate(content, save, save.cats[0].id)
    assert ok is False
    assert motivo == "Precisa manter 12 adultos disponíveis."


def test_can_donate_recusa_gato_em_breeding(content, save):
    e1, e2 = extra_cat(content, save, 7), extra_cat(content, save, 8)
    save.breeding.append({"male": e1.id, "female": e2.id, "runs_left": 2})
    assert can_donate(content, save, e1.id) == (False, "Gato em breed.")
    assert can_donate(content, save, e2.id) == (False, "Gato em breed.")


def test_can_donate_gato_inexistente(content, save):
    assert can_donate(content, save, "c-999999") == (False, "Gato inexistente.")


def test_can_donate_filhote_e_permitido(content, save):
    k = mk_cat(content, "c-000500", 3, 3, stage="kitten", runs_as_kitten=0)
    save.cats.append(k)
    assert can_donate(content, save, k.id) == (True, "")


def _cenario(content, save, nome):
    if nome == "minimo":
        return save.cats[0].id
    if nome == "breed":
        e1, e2 = extra_cat(content, save, 7), extra_cat(content, save, 8)
        save.breeding.append({"male": e1.id, "female": e2.id, "runs_left": 2})
        return e1.id
    return "c-999999"


CENARIOS = ["minimo", "breed", "inexistente"]


@pytest.mark.parametrize("nome", CENARIOS)
def test_donate_cat_usa_o_mesmo_motivo_do_can_donate(content, save, nome):
    cid = _cenario(content, save, nome)
    ok, motivo = can_donate(content, save, cid)
    assert not ok and motivo
    with pytest.raises(IllegalAction) as exc:
        donate_cat(content, save, cid)
    assert motivo in str(exc.value)


@pytest.mark.parametrize("nome", CENARIOS)
def test_donate_cat_recusado_nao_altera_o_save(content, save, nome):
    cid = _cenario(content, save, nome)
    snap = save_to_dict(save)
    with pytest.raises(IllegalAction):
        donate_cat(content, save, cid)
    assert save_to_dict(save) == snap


def test_can_donate_nao_altera_o_save(content, save):
    e = extra_cat(content, save)
    snap = save_to_dict(save)
    can_donate(content, save, e.id)
    can_donate(content, save, save.cats[0].id)
    assert save_to_dict(save) == snap


# ------------------------------------------------------------ save_deck_draft
@pytest.mark.parametrize("n", [0, 1, 5, 12])
def test_rascunho_aceita_0_a_12(content, save, n):
    ids = [c.id for c in save.cats][:n]
    save_deck_draft(save, ids, content)
    assert save.deck == ids


def test_rascunho_com_13_e_recusado(content, save):
    extra_cat(content, save)
    antes = list(save.deck)
    with pytest.raises(IllegalAction):
        save_deck_draft(save, [c.id for c in save.cats][:13], content)
    assert save.deck == antes


def test_rascunho_repetido_e_recusado(content, save):
    i = save.cats[0].id
    with pytest.raises(IllegalAction):
        save_deck_draft(save, [i, i], content)


def test_rascunho_com_filhote_e_recusado(content, save):
    k = mk_cat(content, "c-000500", 3, 3, stage="kitten")
    save.cats.append(k)
    with pytest.raises(IllegalAction):
        save_deck_draft(save, [k.id], content)


def test_rascunho_com_gato_em_descanso_e_recusado(content, save):
    save.cats[0].rest_runs_left = 1
    with pytest.raises(IllegalAction):
        save_deck_draft(save, [save.cats[0].id], content)


def test_rascunho_com_gato_inexistente_e_recusado(content, save):
    with pytest.raises(IllegalAction):
        save_deck_draft(save, ["c-999999"], content)


def test_set_deck_continua_exigindo_12(content, save):
    with pytest.raises(IllegalAction):
        set_deck(content, save, [c.id for c in save.cats][:5])
    with pytest.raises(IllegalAction):
        set_deck(content, save, [])
    set_deck(content, save, [c.id for c in save.cats][:12])
    assert len(save.deck) == 12


def test_nova_run_com_rascunho_incompleto_e_recusada(content, save):
    save_deck_draft(save, [c.id for c in save.cats][:5], content)
    with pytest.raises(IllegalAction):
        new_run_from_save(content, save, Random(1))


# ------------------------------------------------------------ save / schema
def erros_schema(d):
    return list(Draft202012Validator(SCHEMA).iter_errors(d))


def save_com_pendente(content):
    s = new_game(content, Random(1))
    create_adoption(content, s, Random(4), "vitoria", 4)
    return s


def test_save_com_pendente_valida_no_schema(content):
    d = save_to_dict(save_com_pendente(content))
    assert "pending_adoption" in d
    assert erros_schema(d) == []


def test_save_sem_pendente_valida_no_schema(content, save):
    assert erros_schema(save_to_dict(save)) == []


def test_round_trip_dict_preserva_pendente(content):
    s = save_com_pendente(content)
    d = save_to_dict(s)
    s2 = save_from_dict(copy.deepcopy(d), content)
    assert save_to_dict(s2) == d
    assert [asdict(c) for c in pend(s2)] == [asdict(c) for c in pend(s)]
    assert s2.pending_adoption["result"] == "vitoria"
    assert s2.pending_adoption["nodes_cleared"] == 4


def test_round_trip_arquivo_preserva_pendente_e_pity(content, tmp_path):
    s = save_com_pendente(content)
    s.pity["runs_without_high_iv"] = 3
    p = tmp_path / "save.json"
    write_save(s, p)
    s2 = read_save(p, content)
    assert save_to_dict(s2) == save_to_dict(s)
    assert s2.pity["runs_without_high_iv"] == 3


def test_save_antigo_sem_pending_adoption_carrega(content, save):
    d = save_to_dict(save)
    d.pop("pending_adoption", None)
    s = save_from_dict(d, content)
    assert s.pending_adoption is None


def test_pending_adoption_null_carrega_como_none(content, save):
    d = save_to_dict(save)
    d["pending_adoption"] = None
    assert save_from_dict(d, content).pending_adoption is None


def test_id_repetido_entre_colecao_e_pendente_e_erro(content):
    d = save_to_dict(save_com_pendente(content))
    d["pending_adoption"]["cats"][0]["id"] = d["cats"][0]["id"]
    with pytest.raises(ValueError):
        save_from_dict(d, content)


def test_id_repetido_dentro_da_pendente_e_erro(content):
    d = save_to_dict(save_com_pendente(content))
    d["pending_adoption"]["cats"][1]["id"] = d["pending_adoption"]["cats"][0]["id"]
    with pytest.raises(ValueError):
        save_from_dict(d, content)


def test_next_cat_id_nao_pode_ficar_atras_do_pendente(content):
    d = save_to_dict(save_com_pendente(content))
    d["next_cat_id"] = 1
    with pytest.raises(ValueError):
        save_from_dict(d, content)


# ------------------------------------------------------------ run completa
def jogar_run(content, s, seed):
    run = new_run_from_save(content, s, Random(seed))
    rng = Random(seed + 1)
    for _ in range(500):
        if run.status == "finished":
            return run
        if run.status == "map":
            run.choose_node(run.available_nodes()[0]["id"])
        elif run.status == "duel":
            d = run.start_duel(rng)
            for _ in range(4000):
                if d.winner is not None:
                    break
                apply_action(d, choose_action(d, d.turn_side, rng))
            run.finish_duel(d)
        elif run.status == "draft":
            run.pick_draft(0)
    raise AssertionError("run nao terminou")


def test_run_completa_da_ia_termina_em_adocao_e_adota_todos(content, save):
    run = jogar_run(content, save, 5)
    assert run.result in ("vitoria", "derrota")
    create_adoption(content, save, Random(9), run.result, run.nodes_cleared)
    esperado = adoption_count(content, run.nodes_cleared, run.result)
    assert len(pend(save)) == esperado
    assert save.progress["best_distance"] >= run.nodes_cleared
    n = len(save.cats)
    for c in list(pend(save)):
        adopt(content, save, c.id)
    assert save.pending_adoption is None
    assert len(save.cats) == n + esperado
    ids = [c.id for c in save.cats]
    assert len(set(ids)) == len(ids)
    assert erros_schema(save_to_dict(save)) == []
    # o jogo segue: o deck de 12 continua valido para a proxima run
    new_run_from_save(content, save, Random(2))


def test_varias_runs_seguidas_mantem_save_consistente(content, save):
    for i in range(4):
        run = jogar_run(content, save, 10 + i)
        create_adoption(content, save, Random(i), run.result, run.nodes_cleared)
        for c in list(pend(save)):
            adopt(content, save, c.id)
        ids = [c.id for c in save.cats]
        assert len(set(ids)) == len(ids)
        assert save.next_cat_id > max(int(x.split("-")[1]) for x in ids)
        assert erros_schema(save_to_dict(save)) == []
