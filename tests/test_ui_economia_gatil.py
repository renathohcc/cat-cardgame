"""Testes de UI do gatil cheio (Fase 10a, T13.5): adocao e nascimento com o gatil no limite.

Regra (especificacao 10a, secao 3): adocao com gatil cheio pede doar um da colecao ou o novo, nunca ha
perda automatica; filhotes nascem mesmo acima do limite e so a adocao e o novo breed ficam bloqueados;
doar respeita 12 adultos disponiveis. Headless (SDL dummy)."""
from __future__ import annotations

from random import Random

import pytest

from core import (advance_after_run, available_cats, can_adopt, donate_cat, has_pending_adoption,
                  kennel_over_limit, kennel_slots, occupied, room_candidates, start_breed, unlock_area)
from ui_eco_helpers import (add_cats, area_ids, couple, draw_texts, fill_kennel, game_content, has_text,
                            hub_no_cercado, offer)


@pytest.fixture(scope="module")
def c():
    return game_content()


@pytest.fixture
def hub():
    return hub_no_cercado()


def com_12_adultos_e_filhotes(c, h) -> None:
    """12 adultos (o minimo) + filhotes ate lotar o gatil: so filhote pode ser doado."""
    deck = c.rules["duel"]["deck_size"]
    s = h.save
    s.cats = [x for x in s.cats if x.stage == "adult"][:deck]
    s.deck = [x.id for x in s.cats]
    add_cats(s, kittens=kennel_slots(c, s) - len(s.cats))
    assert occupied(s) == kennel_slots(c, s) and len(available_cats(s)) == deck


# ====================================================================== ADOCAO
def test_adocao_com_vaga_livre_adota_direto(hub, c):
    cats = offer(c, hub)
    n = len(hub.save.cats)
    hub.click(("adopt", cats[0].id))
    assert len(hub.save.cats) == n + 1 and not hub.adopt.room_for


def test_adocao_com_gatil_cheio_abre_painel_e_nao_adota_nem_perde(hub, c):
    fill_kennel(c, hub.save)
    cats = offer(c, hub)
    ids = {x.id for x in cats}
    n, coins = len(hub.save.cats), hub.save.coins
    assert hub.adopt.kennel_full
    hub.click(("adopt", cats[0].id))
    assert hub.adopt.room_for == cats[0].id                          # painel aberto
    assert len(hub.save.cats) == n and hub.save.coins == coins
    assert {x.id for x in hub.save.pending_adoption["cats"]} == ids  # nada se perdeu
    assert has_text(draw_texts(hub), "GATIL CHEIO")


def test_painel_de_gatil_cheio_lista_candidatos_e_mostra_vagas(hub, c):
    fill_kennel(c, hub.save)
    cats = offer(c, hub)
    hub.click(("adopt", cats[0].id))
    assert hub.adopt.room_cats()
    assert f"Vagas {occupied(hub.save)}/{kennel_slots(c, hub.save)}" in hub.adopt.slots_text


def test_doar_um_da_colecao_adota_o_novo_sem_passar_do_limite(hub, c):
    fill_kennel(c, hub.save)
    novo = offer(c, hub)[0]
    hub.click(("adopt", novo.id))
    doado = hub.adopt.room_cats()[0]
    n, coins = len(hub.save.cats), hub.save.coins
    hub.click(("room_pick", doado.id))
    hub.click(("room_donate",))
    s = hub.save
    ids = {x.id for x in s.cats}
    assert doado.id not in ids and novo.id in ids
    assert len(s.cats) == n and occupied(s) <= kennel_slots(c, s)
    assert s.coins > coins                                           # doar paga
    assert not hub.adopt.room_for
    assert all(i in ids for i in s.deck)                             # deck sem gato fantasma


def test_doar_sem_escolher_ninguem_nao_faz_nada(hub, c):
    fill_kennel(c, hub.save)
    novo = offer(c, hub)[0]
    hub.click(("adopt", novo.id))
    n = len(hub.save.cats)
    hub.click(("room_donate",))
    assert len(hub.save.cats) == n and hub.adopt.room_for == novo.id


def test_escolher_de_novo_o_mesmo_gato_desmarca(hub, c):
    fill_kennel(c, hub.save)
    novo = offer(c, hub)[0]
    hub.click(("adopt", novo.id))
    alvo = hub.adopt.room_cats()[0]
    hub.click(("room_pick", alvo.id))
    assert hub.adopt.room_sel == alvo.id
    hub.click(("room_pick", alvo.id))
    assert hub.adopt.room_sel is None


def test_doar_o_gato_novo_ganha_moedas_e_ele_nao_entra_na_colecao(hub, c):
    fill_kennel(c, hub.save)
    novo = offer(c, hub)[0]
    n, coins = len(hub.save.cats), hub.save.coins
    hub.click(("adopt", novo.id))
    hub.click(("room_donate_new",))
    s = hub.save
    assert len(s.cats) == n and novo.id not in {x.id for x in s.cats}
    assert s.coins > coins
    restantes = {x.id for x in (s.pending_adoption or {"cats": []})["cats"]}
    assert novo.id not in restantes


def test_cancelar_o_painel_nao_perde_nada(hub, c):
    fill_kennel(c, hub.save)
    cats = offer(c, hub)
    n, coins = len(hub.save.cats), hub.save.coins
    hub.click(("adopt", cats[0].id))
    hub.click(("room_cancel",))
    assert not hub.adopt.room_for
    assert len(hub.save.cats) == n and hub.save.coins == coins
    assert len(hub.save.pending_adoption["cats"]) == len(cats)


def test_esc_no_painel_so_fecha_o_painel_e_a_oferta_fica_no_save(hub, c):
    fill_kennel(c, hub.save)
    cats = offer(c, hub)
    hub.click(("adopt", cats[0].id))
    hub.key_escape()
    assert hub.mode == "adocao" and not hub.adopt.room_for
    hub.key_escape()
    assert hub.mode == "cercado" and has_pending_adoption(hub.save)
    assert len(hub.save.pending_adoption["cats"]) == len(cats)


def test_clicar_fora_do_painel_nao_adota_nem_doa_sozinho(hub, c):
    fill_kennel(c, hub.save)
    cats = offer(c, hub)
    n, coins = len(hub.save.cats), hub.save.coins
    hub.click(("adopt", cats[0].id))
    hub.click(None)                                 # clique no vazio = cancelar o painel
    assert len(hub.save.cats) == n and hub.save.coins == coins
    assert len(hub.save.pending_adoption["cats"]) == len(cats)


def test_com_12_adultos_nao_oferece_adulto_para_doar(hub, c):
    com_12_adultos_e_filhotes(c, hub)
    cats = offer(c, hub)
    hub.click(("adopt", cats[0].id))
    assert hub.adopt.room_for
    assert all(x.stage == "kitten" for x in hub.adopt.room_cats()), "doar adulto deixaria menos de 12"


def test_com_12_adultos_doar_filhotes_nunca_deixa_menos_de_12(hub, c):
    com_12_adultos_e_filhotes(c, hub)
    s, deck = hub.save, c.rules["duel"]["deck_size"]
    cats = offer(c, hub)
    hub.click(("adopt", cats[0].id))
    for cand in list(hub.adopt.room_cats()):
        hub.click(("room_pick", cand.id))
        hub.click(("room_donate",))
        if not hub.adopt.room_for:
            break
    assert len([x for x in s.cats if x.stage == "adult"]) >= deck
    assert len(available_cats(s)) >= deck


def test_candidatos_para_doar_vem_dos_piores_ivs_primeiro(hub, c):
    fill_kennel(c, hub.save)
    novo = offer(c, hub)[0]
    hub.click(("adopt", novo.id))
    somas = [x.iv_atk + x.iv_hp for x in hub.adopt.room_cats()]
    assert somas == sorted(somas)


def test_candidatos_da_ui_sao_os_do_core(hub, c):
    fill_kennel(c, hub.save)
    novo = offer(c, hub)[0]
    hub.click(("adopt", novo.id))
    assert {x.id for x in hub.adopt.room_cats()} == {x.id for x in room_candidates(c, hub.save)}


def test_core_recusa_adotar_com_gatil_cheio(hub, c):
    fill_kennel(c, hub.save)
    ok, why = can_adopt(c, hub.save)
    assert ok is False and why


def test_botao_adotar_avisa_que_nao_ha_vaga(hub, c):
    fill_kennel(c, hub.save)
    offer(c, hub)
    assert has_text(draw_texts(hub), "SEM VAGA")


def test_doar_pela_ui_no_gatil_cheio_continua_permitido_para_o_gato_da_oferta(hub, c):
    fill_kennel(c, hub.save)
    cats = offer(c, hub)
    coins = hub.save.coins
    hub.click(("donate", cats[0].id))
    assert hub.save.coins > coins and len(hub.save.pending_adoption["cats"]) == len(cats) - 1


def test_adotar_a_oferta_inteira_volta_ao_cercado_ou_resumo(hub, c):
    cats = offer(c, hub)
    for x in cats:
        hub.click(("adopt", x.id))
        if hub.mode != "adocao":
            break
    assert hub.mode in ("cercado", "resultado") and not has_pending_adoption(hub.save)


# ====================================================================== NASCIMENTO
def nascer_com_gatil_cheio(c, h):
    add_cats(h.save, adults=4)                  # o breed exige 12 adultos disponiveis alem do casal
    m, f = couple(h.save)
    start_breed(c, h.save, m.id, f.id)
    fill_kennel(c, h.save)
    rng = Random(11)
    for _ in range(10):
        aft = advance_after_run(c, h.save, rng, 6)
        if aft.born:
            return aft
    raise AssertionError("o casal deveria ter tido ninhada")


def test_nasce_mesmo_com_gatil_cheio_e_passa_do_limite(hub, c):
    aft = nascer_com_gatil_cheio(c, hub)
    s = hub.save
    assert all(k.id in {x.id for x in s.cats} for k in aft.born)
    assert kennel_over_limit(c, s) and occupied(s) > kennel_slots(c, s)


def test_acima_do_limite_a_placa_mostra_ocupacao_maior_que_as_vagas(hub, c):
    nascer_com_gatil_cheio(c, hub)
    s = hub.save
    assert f"{occupied(s)}/{kennel_slots(c, s)}" in draw_texts(hub)
    assert occupied(s) > kennel_slots(c, s)


def test_acima_do_limite_bloqueia_adocao_e_novo_breed(hub, c):
    nascer_com_gatil_cheio(c, hub)
    s = hub.save
    assert can_adopt(c, s)[0] is False
    hub.open_breed()
    bc = hub.breed
    m, f = couple(s)
    bc.click(("row", "M", m.id))
    bc.click(("row", "F", f.id))
    ok, motivo = bc.verdict()
    assert ok is False and motivo
    n = len(s.breeding)
    bc.click(("start",))
    assert len(s.breeding) == n and bc.toast is not None and bc.toast.kind == "error"


def test_acima_do_limite_a_adocao_diz_gatil_acima_do_limite(hub, c):
    nascer_com_gatil_cheio(c, hub)
    hub.click(("adopt", offer(c, hub)[0].id))
    assert hub.adopt.room_for and has_text(draw_texts(hub), "ACIMA DO LIMITE")


def test_voltando_ao_limite_adocao_e_breed_voltam(hub, c):
    nascer_com_gatil_cheio(c, hub)
    s = hub.save
    while occupied(s) >= kennel_slots(c, s):
        donate_cat(c, s, room_candidates(c, s)[0].id)
    assert can_adopt(c, s)[0] is True
    hub.open_breed()
    m, f = couple(s)
    hub.breed.click(("row", "M", m.id))
    hub.breed.click(("row", "F", f.id))
    assert hub.breed.verdict()[0] is True


def test_filhotes_ficam_na_cesta_ate_comprar_o_cercadinho(hub, c):
    nascer_com_gatil_cheio(c, hub)
    assert hub.basket_count >= 1
    cercadinho = next(a for a in sorted(c.shop["areas"], key=lambda a: a["order"])
                      if any(u["type"] == "kitten_pen" for u in a["unlocks"]))
    s = hub.save
    s.coins = 10_000
    for aid in area_ids(c)[:area_ids(c).index(cercadinho["id"]) + 1]:
        unlock_area(c, s, aid)
    hub.refresh_world()
    assert hub.basket_count == 0


def test_fim_de_run_real_com_nascimento_e_gatil_cheio_nao_perde_gato(c):
    from ui_eco_helpers import finish_run
    h = hub_no_cercado()
    add_cats(h.save, adults=4)
    m, f = couple(h.save)
    start_breed(c, h.save, m.id, f.id)
    s = h.save
    s.breeding[0]["runs_left"] = 1
    fill_kennel(c, s)
    antes = {x.id for x in s.cats}
    finish_run(c, h, {"batalha": 2})
    assert h.mode == "novidades"                                     # nasceu ninhada
    assert antes <= {x.id for x in s.cats} and len(s.cats) > len(antes)
    assert has_text(draw_texts(h), "Nasce")
