"""Testes de UI da racao e da previa de odds no breed, da ficha (historico/linhagem) e do fim de run
(Fase 10a, T13.5). Headless (SDL dummy).

Escritos a partir da especificacao 10a (secoes 2, 4 e 5). Chances e duracoes sao lidas de `data/*.json`
e comparadas com `core.breed_odds`; o estado final e conferido na API publica do `core`."""
from __future__ import annotations

import pytest

from core import (IvChoice, breed_odds, choice_to_dict, close_run, next_goal, prestige_info, run_earnings)
from economia_helpers import finished_run
from ui_eco_helpers import (add_cats, couple, draw_texts, finish_run, game_content, has_text, hub_no_cercado,
                            to_result)


@pytest.fixture(scope="module")
def c():
    return game_content()


@pytest.fixture
def hub():
    return hub_no_cercado()


@pytest.fixture
def breed_hub(c):
    """Breed aberto com um casal de racas diferentes escolhido, Prestigio 3 e 2 de cada racao."""
    h = hub_no_cercado()
    s = h.save
    add_cats(s, adults=4)
    s.prestige = 3
    h.prestige_seen = 3
    for r in c.shop["rations"]:
        s.rations[r["id"]] = 2
    m, f = couple(s)
    m.iv_atk, m.iv_hp, f.iv_atk, f.iv_hp = 4, 2, 1, 5
    h.open_breed()
    h.breed.click(("row", "M", m.id))
    h.breed.click(("row", "F", f.id))
    h.pair = (m, f)
    return h


# ====================================================================== RACAO E PREVIA DE ODDS
def test_breed_oferece_nenhuma_e_as_tres_racoes_com_estoque(breed_hub, c):
    opts = breed_hub.breed.ration_options()
    assert opts[0][0] is None
    assert [o[0] for o in opts[1:]] == [r["id"] for r in c.shop["rations"]]
    assert len(c.shop["rations"]) == 3
    assert all(o[2] == 2 for o in opts[1:])


def test_breed_desenha_um_chip_por_racao(breed_hub, c):
    texts = draw_texts(breed_hub)
    for r in c.shop["rations"]:
        assert has_text(texts, r["name"].replace("Ração ", ""))


def test_breed_previa_so_aparece_com_casal_escolhido():
    h = hub_no_cercado()
    h.open_breed()
    assert h.breed.odds() is None
    assert "PRÉVIA DE CHANCES" not in draw_texts(h)


def test_breed_previa_sem_racao_bate_com_o_core_e_mostra_raca_60_40(breed_hub, c):
    m, f = breed_hub.pair
    od = breed_hub.breed.odds()
    assert od == breed_odds(c, breed_hub.save, m.id, f.id)
    ch = c.rules["breed"]["mother_breed_chance"]
    assert od.breed[f.breed] == pytest.approx(ch) and od.breed[m.breed] == pytest.approx(1 - ch)
    assert od.mutation == pytest.approx(c.rules["breed"]["mutation_chance"])
    texts = draw_texts(breed_hub)
    assert "PRÉVIA DE CHANCES" in texts and has_text(texts, f"{round(ch * 100)}%")


def test_breed_previa_mostra_a_faixa_da_ninhada(breed_hub, c):
    lo, hi = c.rules["breed"]["litter_min"], c.rules["breed"]["litter_max"]
    assert has_text(draw_texts(breed_hub), f"Ninhada: {lo} a {hi}")


def test_breed_racao_fofa_sobe_a_mutacao_na_previa_e_na_tela(breed_hub, c):
    m, f = breed_hub.pair
    bc = breed_hub.breed
    bc.click(("ration", "racao-fofa"))
    fofa = next(r for r in c.shop["rations"] if r["id"] == "racao-fofa")["effect"]["value"]
    od = bc.odds()
    assert od.mutation == pytest.approx(fofa) and od.mutation > c.rules["breed"]["mutation_chance"]
    assert od == breed_odds(c, breed_hub.save, m.id, f.id, "racao-fofa", None)
    assert has_text(draw_texts(breed_hub), f"Mutação por IV: {round(fofa * 100)}%")


def test_breed_racao_veloz_encurta_o_tempo_na_previa_e_na_tela(breed_hub, c):
    bc = breed_hub.breed
    bc.click(("ration", "racao-veloz"))
    od = bc.odds()
    base = c.rules["breed"]["base_runs"]
    assert od.runs_without_ration == base and od.runs == max(1, base - 1)
    assert has_text(draw_texts(breed_hub), f"Tempo: {od.runs} run", f"sem ração: {base}")


def test_breed_racao_escolha_sem_escolher_nao_inicia_e_pede_o_iv(breed_hub):
    bc = breed_hub.breed
    bc.click(("ration", "racao-escolha"))
    assert bc.needs_choice and bc.choice is None
    ok, motivo = bc.verdict()
    assert ok is False and "Escolha" in motivo
    bc.click(("start",))
    assert breed_hub.save.breeding == [] and breed_hub.save.rations["racao-escolha"] == 2


@pytest.mark.parametrize("stat,parent", [("atk", "father"), ("atk", "mother"), ("hp", "father"), ("hp", "mother")])
def test_breed_racao_escolha_fixa_o_iv_do_pai_ou_da_mae_na_previa(breed_hub, stat, parent):
    m, f = breed_hub.pair
    bc = breed_hub.breed
    bc.click(("ration", "racao-escolha"))
    bc.click(("choice", stat, parent))
    od = bc.odds()
    esperado = getattr(m if parent == "father" else f, f"iv_{stat}")
    outro = "hp" if stat == "atk" else "atk"
    assert od.fixed[stat] == esperado and od.fixed.get(outro) is None
    dist = od.iv_atk if stat == "atk" else od.iv_hp
    assert dist == {esperado: pytest.approx(1.0)}                    # 100% e sem mutacao
    assert has_text(draw_texts(breed_hub), f"{stat.upper()} fixado em {esperado}")


def test_breed_racao_escolha_clicar_a_mesma_escolha_desmarca(breed_hub):
    bc = breed_hub.breed
    bc.click(("ration", "racao-escolha"))
    bc.click(("choice", "atk", "father"))
    bc.click(("choice", "atk", "father"))
    assert bc.choice is None and not bc.can_start


def test_breed_racao_escolha_iniciada_consome_estoque_e_grava_a_escolha(breed_hub):
    m, f = breed_hub.pair
    bc = breed_hub.breed
    bc.click(("ration", "racao-escolha"))
    bc.click(("choice", "hp", "mother"))
    assert bc.can_start
    bc.click(("start",))
    s = breed_hub.save
    assert s.rations["racao-escolha"] == 1
    b = s.breeding[0]
    assert (b["male"], b["female"], b["ration"]) == (m.id, f.id, "racao-escolha")
    assert b["ration_choice"] == choice_to_dict(IvChoice("hp", "mother"))


def test_breed_racao_sem_estoque_nao_seleciona_e_avisa(breed_hub):
    bc = breed_hub.breed
    breed_hub.save.rations["racao-fofa"] = 0
    bc.click(("ration", "racao-fofa"))
    assert bc.ration is None and bc.toast is not None and bc.toast.kind == "error"


def test_breed_racao_clicada_de_novo_desmarca(breed_hub):
    bc = breed_hub.breed
    bc.click(("ration", "racao-fofa"))
    bc.click(("ration", "racao-fofa"))
    assert bc.ration is None


def test_breed_uma_racao_por_casal_trocar_substitui_e_gasta_so_a_escolhida(breed_hub):
    bc = breed_hub.breed
    bc.click(("ration", "racao-fofa"))
    bc.click(("ration", "racao-veloz"))
    assert bc.ration == "racao-veloz"
    bc.click(("start",))
    s = breed_hub.save
    assert s.breeding[0]["ration"] == "racao-veloz"
    assert s.rations["racao-veloz"] == 1 and s.rations["racao-fofa"] == 2


def test_breed_racao_veloz_iniciada_usa_a_duracao_da_previa(breed_hub):
    bc = breed_hub.breed
    bc.click(("ration", "racao-veloz"))
    prev = bc.odds().runs
    bc.click(("start",))
    assert breed_hub.save.breeding[0]["runs_left"] == prev


def test_breed_sem_racao_nenhum_estoque_e_gasto(breed_hub):
    breed_hub.breed.click(("start",))
    s = breed_hub.save
    assert s.breeding[0]["ration"] is None and all(v == 2 for v in s.rations.values())


def test_breed_trocar_o_casal_mantem_a_racao_mas_zera_a_escolha(breed_hub):
    bc = breed_hub.breed
    bc.click(("ration", "racao-escolha"))
    bc.click(("choice", "atk", "father"))
    bc.click(("ration", "racao-fofa"))
    assert bc.ration == "racao-fofa" and bc.choice is None


def test_breed_cesta_avisa_que_filhotes_vao_para_a_cesta(breed_hub):
    assert breed_hub.breed.basket is True
    assert has_text(draw_texts(breed_hub), "cesta")


def test_breed_mostra_casais_e_vagas(breed_hub):
    bc = breed_hub.breed
    assert bc.couples_text().startswith("Casais 0/")
    assert bc.slots_text.startswith("Vagas ")


# ====================================================================== FICHA
def test_ficha_mostra_geracao_pais_e_historico(hub):
    cats = hub.save.cats
    cats[0].name, cats[1].name = "Pipoca", "Bolota"
    kid = cats[2]
    kid.generation, kid.parents = 2, [cats[0].id, cats[1].id]
    kid.history = {"runs": 6, "duels_won": 14, "bosses_defeated": 2}
    hub.sync_pen()
    hub.open_ficha(kid.id)
    texts = draw_texts(hub)
    assert has_text(texts, "G2", "Pais:", "Pipoca", "Bolota")
    assert has_text(texts, "Runs 6", "Duelos 14", "Chefes 2")


def test_ficha_de_gato_adotado_mostra_g1_adotado_e_historico_zerado(hub):
    hub.open_ficha(hub.save.cats[0].id)
    texts = draw_texts(hub)
    assert has_text(texts, "G1", "Adotado") and has_text(texts, "Runs 0", "Duelos 0", "Chefes 0")


def test_ficha_historico_cresce_apos_fechar_uma_run(c):
    h = hub_no_cercado()
    deck_ids = list(h.save.deck)
    close_run(c, h.save, finished_run(c, h.save, wins={"batalha": 2, "chefe": 1}, result="vitoria"))
    h.open_ficha(deck_ids[0])
    assert has_text(draw_texts(h), "Runs 1", "Chefes 1")


def test_ficha_de_filhote_nascido_mostra_pais_e_g2(c):
    from core import advance_after_run, start_breed
    from random import Random
    h = hub_no_cercado()
    add_cats(h.save, adults=4)
    m, f = couple(h.save)
    start_breed(c, h.save, m.id, f.id)
    nascidos = []
    for _ in range(10):
        nascidos = advance_after_run(c, h.save, Random(2), 6).born
        if nascidos:
            break
    assert nascidos
    h.sync_pen()
    h.open_ficha(nascidos[0].id)
    assert has_text(draw_texts(h), "G2", "Pais:")


# ====================================================================== FIM DE RUN
def test_fim_de_run_credita_as_moedas_das_fontes(c):
    h = hub_no_cercado()
    antes = h.save.coins
    run = finish_run(c, h, {"batalha": 3, "elite": 1}, "derrota")
    esperado = sum(v for _, v in run_earnings(c, run))
    assert esperado > 0
    assert h.summary.settlement.coins == esperado and h.save.coins == antes + esperado


def test_fim_de_run_resumo_mostra_ganhos_por_fonte_e_total(c):
    h = hub_no_cercado()
    finish_run(c, h, {"batalha": 3, "elite": 1})
    to_result(h)
    assert h.mode == "resultado"
    texts = draw_texts(h, frames=2)
    assert "GANHOS DA RUN" in texts and "Batalhas vencidas" in texts and "Elites vencidas" in texts
    assert "TOTAL" in texts


def test_fim_de_run_barra_de_meta_diz_quanto_falta_para_o_proximo_item(c):
    h = hub_no_cercado()
    finish_run(c, h, {"batalha": 1})
    to_result(h)
    g = next_goal(c, h.save)
    assert g is not None and g["missing"] == g["price"] - h.save.coins > 0
    texts = draw_texts(h, frames=2)
    assert "PRÓXIMA META" in texts
    assert has_text(texts, f"Faltam {g['missing']} moedas para") and has_text(texts, f"{h.save.coins}/{g['price']}")


def test_fim_de_run_barra_de_meta_avisa_quando_ja_da_para_comprar(c):
    h = hub_no_cercado()
    h.save.coins = 500
    finish_run(c, h, {"batalha": 1})
    to_result(h)
    g = next_goal(c, h.save)
    assert g["missing"] == 0
    assert has_text(draw_texts(h, frames=2), "Você já pode comprar")


def test_fim_de_run_barra_de_meta_mostra_o_nome_completo_do_item(c):
    h = hub_no_cercado()
    finish_run(c, h, {"batalha": 1})
    to_result(h)
    g = next_goal(c, h.save)
    junto = " ".join(draw_texts(h, frames=2))     # a barra quebra o texto em ate 2 linhas
    assert "moedas para" in junto and g["name"] in junto


def test_fim_de_run_meta_e_o_item_mais_barato_liberado(c):
    h = hub_no_cercado()
    g = next_goal(c, h.save)
    assert g["kind"] == "area" and g["id"] == sorted(c.shop["areas"], key=lambda a: a["order"])[0]["id"]
    assert g["price"] == c.shop["areas"][0]["price"]


def test_fim_de_run_derrota_sem_vitorias_nao_ganha_moedas_e_diz(c):
    h = hub_no_cercado()
    antes = h.save.coins
    finish_run(c, h, {})
    to_result(h)
    assert h.save.coins == antes
    assert has_text(draw_texts(h, frames=2), "Nenhuma vitória")


def test_fim_de_run_barra_de_prestigio_mostra_o_proximo_marco(c):
    h = hub_no_cercado()
    finish_run(c, h, {"batalha": 2})
    to_result(h)
    texts = draw_texts(h, frames=2)
    assert has_text(texts, "PRESTÍGIO 1") and has_text(texts, "Nível 2")
    assert not h.summary.prestige_up


def test_vitoria_na_liga_1_paga_bonus_e_sobe_o_prestigio_com_selo(c):
    h = hub_no_cercado()
    antes = h.save.coins
    finish_run(c, h, {"batalha": 3, "elite": 1, "chefe": 1}, "vitoria", league=1)
    st = h.summary.settlement
    bonus = c.rules["economy"]["league1_first_win_bonus"]
    assert st.first_league_win and ("primeira-vitoria-liga", bonus) in st.earnings
    assert st.prestige_up and st.prestige_after == 2
    assert h.save.prestige == 2 and h.save.coins == antes + st.coins
    assert h.seal is not None and h.seal[0] == 2
    assert has_text(draw_texts(h), "PRESTÍGIO SUBIU!")             # selo aparece em qualquer tela
    to_result(h)
    assert has_text(draw_texts(h, frames=2), "PRESTÍGIO SUBIU!", "")


def test_bonus_da_primeira_vitoria_so_paga_uma_vez(c):
    h = hub_no_cercado()
    finish_run(c, h, {"chefe": 1}, "vitoria", league=1)
    to_result(h)
    h.click(("result_back",))
    finish_run(c, h, {"chefe": 1}, "vitoria", league=1)
    assert not h.summary.settlement.first_league_win
    assert all(src != "primeira-vitoria-liga" for src, _ in h.summary.settlement.earnings)


def test_selo_de_prestigio_some_depois_do_tempo(c):
    h = hub_no_cercado()
    finish_run(c, h, {"chefe": 1}, "vitoria", league=1)
    assert h.seal is not None
    for _ in range(80):
        h.update(0.05)
    assert h.seal is None


def test_prestigio_nunca_desce_depois_de_uma_derrota(c):
    h = hub_no_cercado()
    finish_run(c, h, {"chefe": 1}, "vitoria", league=1)
    to_result(h)
    h.click(("result_back",))
    finish_run(c, h, {}, "derrota")
    assert h.save.prestige == 2 and not h.summary.prestige_up
    assert prestige_info(c, h.save).level == 2


def test_resumo_vem_depois_de_novidades_e_adocao(c):
    h = hub_no_cercado()
    finish_run(c, h, {"batalha": 2})
    assert h.summary_pending and h.mode in ("novidades", "adocao", "resultado")
    to_result(h)
    assert h.mode == "resultado" and h.summary is not None


def test_voltar_do_resumo_leva_ao_cercado_sem_resumo_pendente(c):
    h = hub_no_cercado()
    finish_run(c, h, {"batalha": 2})
    to_result(h)
    h.click(("result_back",))
    assert h.mode == "cercado" and not h.summary_pending
