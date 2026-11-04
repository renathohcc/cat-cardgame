"""Testes de UI da loja do hub e da placa do portao (Fase 10a, T13.5). Headless (SDL dummy).

Escritos a partir de `docs/propostas/2026-11-03-especificacao-10a.md` e dos relatorios T13.1 a T13.4.
Precos, vagas e Prestigio sao lidos de `data/*.json` via `core`; nada de numero fixo aqui.
O estado final e conferido na API publica do `core`."""
from __future__ import annotations

import pygame
import pytest

from core import kennel_over_limit, kennel_slots, occupied, prestige_info, read_save, unlock_area
from ui import font, pen_world
from ui.render import UIState
from ui.render_hub import draw_hub_frame
from ui.theme import C, H, W
from ui_eco_helpers import (add_cats, area_def, area_ids, buy_area_at_yard, draw_texts, fill_kennel,
                            game_content, has_text, hub_no_cercado, open_shop)


@pytest.fixture(scope="module")
def c():
    return game_content()


@pytest.fixture
def hub():
    return hub_no_cercado()


def primeira_area_bloqueada_por_prestigio(c, h) -> dict:
    """Abre (por API) as areas anteriores e devolve a primeira que exige mais Prestigio que o save."""
    areas = sorted(c.shop["areas"], key=lambda a: a["order"])
    alvo = next(a for a in areas if a["prestige_required"] > h.save.prestige)
    h.save.coins = 10_000
    for aid in area_ids(c)[:area_ids(c).index(alvo["id"])]:
        unlock_area(c, h.save, aid)
    h.refresh_world()
    return alvo


def liberar_primeira_area(c, h) -> None:
    h.save.coins = area_def(c, 0)["price"]
    unlock_area(c, h.save, area_def(c, 0)["id"])
    h.refresh_world()


# ====================================================================== LOJA DO HUB: AREAS
def test_loja_mostra_o_saldo_de_moedas(hub):
    hub.save.coins = 37
    open_shop(hub)
    assert hub.shop.coins == 37
    assert "37" in draw_texts(hub)


def test_loja_lista_todas_as_areas_com_preco_e_prestigio_exigido(hub, c):
    open_shop(hub)
    texts = draw_texts(hub)
    for a in c.shop["areas"]:
        assert has_text(texts, a["name"]), a["name"]
        assert str(a["price"]) in texts, a["id"]
        assert has_text(texts, f"Prestígio {a['prestige_required']}"), a["id"]


def test_loja_tem_tres_abas_e_cada_uma_desenha(hub):
    open_shop(hub)
    assert hub.shop.tab == "areas"
    for aba, marca in (("racoes", "Ração Fofa"), ("decoracao", "DECORAÇÃO"), ("areas", "Cercado")):
        hub.click(("shop_tab", aba))
        assert hub.shop.tab == aba
        assert has_text(draw_texts(hub), marca), aba


def test_loja_mostra_prestigio_atual_e_proximo_marco(hub, c):
    open_shop(hub)
    info = prestige_info(c, hub.save)
    texts = draw_texts(hub)
    assert has_text(texts, f"PRESTÍGIO {info.level}")
    assert info.milestone["type"] == "win_league"            # nivel 2: vencer a liga 1
    assert has_text(texts, "Próximo", "liga")


def test_loja_esc_e_voltar_levam_ao_cercado(hub):
    open_shop(hub)
    hub.click(("shop_back",))
    assert hub.mode == "cercado"
    open_shop(hub)
    hub.key_escape()
    assert hub.mode == "cercado"


def test_comprar_area_debita_preco_e_soma_vagas(hub, c):
    a = area_def(c, 0)
    hub.save.coins = a["price"] + 5
    antes = kennel_slots(c, hub.save)
    buy_area_at_yard(hub, a["id"])
    s = hub.save
    assert a["id"] in s.areas_unlocked and s.coins == 5
    assert kennel_slots(c, s) == antes + a["slots_bonus"]
    assert hub.area_open is None and hub.unlock_fx            # animacao de desbloqueio em curso


def test_comprar_area_atualiza_a_contagem_de_vagas_na_tela(hub, c):
    a = area_def(c, 0)
    hub.save.coins = a["price"]
    occ = occupied(hub.save)
    assert f"{occ}/{c.shop['start']['slots']}" in draw_texts(hub)
    buy_area_at_yard(hub, a["id"])
    assert f"{occ}/{c.shop['start']['slots'] + a['slots_bonus']}" in draw_texts(hub)


def test_area_sem_moedas_suficientes_nao_compra_e_diz_quanto_falta(hub, c):
    a = area_def(c, 0)
    hub.save.coins = a["price"] - 1
    row = hub.shop.area(a["id"])
    assert row.state == "blocked_coins" and row.missing_coins == 1 and not row.can_buy
    assert row.button() == "FALTAM 1"
    buy_area_at_yard(hub, a["id"])
    assert hub.save.coins == a["price"] - 1 and a["id"] not in hub.save.areas_unlocked
    assert hub.shop.toast is not None and hub.shop.toast.kind == "error"


def test_painel_da_area_sem_moedas_mostra_o_que_falta(hub, c):
    a = area_def(c, 0)
    hub.save.coins = 0
    open_shop(hub)
    hub.click(("shop_area", a["id"]))
    texts = draw_texts(hub)
    assert has_text(texts, a["name"]) and has_text(texts, "Faltam", str(a["price"]), "moedas")


def test_area_bloqueada_por_prestigio_nao_compra_mesmo_com_moedas(hub, c):
    alvo = primeira_area_bloqueada_por_prestigio(c, hub)
    row = hub.shop.area(alvo["id"])
    assert row.state == "blocked_prestige" and row.missing_prestige >= 1
    assert row.button() == f"PRESTÍGIO {alvo['prestige_required']}"
    moedas = hub.save.coins
    buy_area_at_yard(hub, alvo["id"])
    assert hub.save.coins == moedas and alvo["id"] not in hub.save.areas_unlocked
    assert hub.shop.toast.kind == "error"


def test_painel_da_area_bloqueada_mostra_exigencia_e_nivel_atual(hub, c):
    alvo = primeira_area_bloqueada_por_prestigio(c, hub)
    open_shop(hub)
    hub.click(("shop_area", alvo["id"]))
    texts = draw_texts(hub)
    assert has_text(texts, f"Exige Prestígio {alvo['prestige_required']}")
    assert has_text(texts, f"Seu Prestígio: {hub.save.prestige}")


def test_prestigio_maior_destrava_a_area(hub, c):
    alvo = primeira_area_bloqueada_por_prestigio(c, hub)
    hub.save.prestige = alvo["prestige_required"]
    hub.prestige_seen = hub.save.prestige
    assert hub.shop.area(alvo["id"]).can_buy
    antes = hub.save.coins
    buy_area_at_yard(hub, alvo["id"])
    assert alvo["id"] in hub.save.areas_unlocked and hub.save.coins == antes - alvo["price"]


def test_areas_so_se_compram_na_ordem(hub, c):
    segunda = area_def(c, 1)
    hub.save.coins = 10_000
    assert hub.shop.area(segunda["id"]).state == "queued"
    buy_area_at_yard(hub, segunda["id"])
    assert segunda["id"] not in hub.save.areas_unlocked and hub.save.coins == 10_000


def test_area_ja_comprada_nao_cobra_de_novo(hub, c):
    a = area_def(c, 0)
    hub.save.coins = a["price"] * 3
    buy_area_at_yard(hub, a["id"])
    sobra = hub.save.coins
    assert hub.shop.buy_area(a["id"]) is False
    assert hub.save.coins == sobra and hub.save.areas_unlocked.count(a["id"]) == 1


def test_compra_de_area_grava_o_save_em_disco(c, tmp_path):
    p = tmp_path / "save.json"
    h = hub_no_cercado(save_path=p)
    a = area_def(c, 0)
    h.save.coins = a["price"]
    buy_area_at_yard(h, a["id"])
    s = read_save(p, c)
    assert a["id"] in s.areas_unlocked and s.coins == 0


def test_compra_de_area_destaca_as_vagas_na_placa(hub, c):
    a = area_def(c, 0)
    hub.save.coins = a["price"]
    buy_area_at_yard(hub, a["id"])
    assert hub.hud_flash > 0


# ====================================================================== LOJA DO HUB: RACOES E DECORACAO
def test_racao_compra_debita_e_soma_estoque(hub, c):
    r = next(r for r in c.shop["rations"] if r["prestige_required"] <= hub.save.prestige)
    hub.save.coins = r["price"] + 1
    open_shop(hub)
    hub.click(("shop_tab", "racoes"))
    hub.click(("shop_ration", r["id"]))
    assert hub.save.rations[r["id"]] == 1 and hub.save.coins == 1


def test_racao_exigindo_prestigio_maior_nao_compra(hub, c):
    r = next(r for r in c.shop["rations"] if r["prestige_required"] > hub.save.prestige)
    hub.save.coins = 10_000
    open_shop(hub)
    hub.click(("shop_tab", "racoes"))
    row = next(x for x in hub.shop.rations() if x.id == r["id"])
    assert not row.prestige_ok and row.button() == f"PRESTÍGIO {r['prestige_required']}"
    hub.click(("shop_ration", r["id"]))
    assert hub.save.rations.get(r["id"], 0) == 0 and hub.save.coins == 10_000


def test_racao_sem_moedas_diz_quanto_falta(hub, c):
    r = next(r for r in c.shop["rations"] if r["prestige_required"] <= hub.save.prestige)
    hub.save.coins = r["price"] - 2
    open_shop(hub)
    hub.click(("shop_tab", "racoes"))
    hub.click(("shop_ration", r["id"]))
    assert hub.save.rations.get(r["id"], 0) == 0
    assert hub.shop.toast is not None and hub.shop.toast.kind == "error"
    assert next(x for x in hub.shop.rations() if x.id == r["id"]).button() == "FALTAM 2"


def test_decoracao_de_area_bloqueada_nao_compra(hub, c):
    d = next(d for d in c.shop["decorations"] if d["area_required"] not in hub.save.areas_unlocked
             and not d.get("placeholder"))
    hub.save.coins = 10_000
    open_shop(hub)
    hub.click(("shop_tab", "decoracao"))
    row = next(x for x in hub.shop.decorations() if x.id == d["id"])
    assert row.state == "locked_area" and row.button() == "ÁREA BLOQUEADA"
    hub.click(("shop_deco", d["id"]))
    assert d["id"] not in hub.save.decorations_owned and hub.save.coins == 10_000


def test_decoracao_liberada_compra_e_o_quintal_religa_sem_erro(hub, c):
    liberar_primeira_area(c, hub)
    row = next(x for x in hub.shop.decorations() if x.state == "available" and not x.soon)
    hub.save.coins = row.price + 3
    open_shop(hub)
    hub.click(("shop_tab", "decoracao"))
    hub.click(("shop_deco", row.id))
    assert row.id in hub.save.decorations_owned and hub.save.coins == 3
    assert next(x for x in hub.shop.decorations() if x.id == row.id).button() == "COMPRADA"
    hub.click(("shop_back",))
    assert hub.mode == "cercado"
    draw_texts(hub)


def test_decoracao_sem_moedas_nao_compra(hub, c):
    liberar_primeira_area(c, hub)
    row = next(x for x in hub.shop.decorations() if x.state == "available" and not x.soon)
    hub.save.coins = row.price - 1
    open_shop(hub)
    hub.click(("shop_tab", "decoracao"))
    hub.click(("shop_deco", row.id))
    assert row.id not in hub.save.decorations_owned and hub.save.coins == row.price - 1


def test_loja_linha_da_area_disponivel_escreve_pode_comprar_inteiro(hub, c):
    hub.save.coins = area_def(c, 0)["price"]
    open_shop(hub)
    assert "Pode comprar!" in draw_texts(hub)


# ====================================================================== PLACA DO PORTAO
def test_placa_mostra_vagas_ocupadas_e_total(hub, c):
    s = hub.save
    texts = draw_texts(hub)
    assert "VAGAS" in texts and f"{occupied(s)}/{kennel_slots(c, s)}" in texts
    assert kennel_slots(c, s) == c.shop["start"]["slots"]


def test_placa_acompanha_a_ocupacao_ao_entrar_gatos(hub, c):
    add_cats(hub.save, adults=3)
    assert f"{occupied(hub.save)}/{kennel_slots(c, hub.save)}" in draw_texts(hub)


def test_placa_mostra_prestigio_e_barra_do_proximo_marco(hub, c):
    texts = draw_texts(hub)
    info = prestige_info(c, hub.save)
    assert f"PRESTÍGIO {info.level}" in texts
    assert has_text(texts, f"Nível {info.next_level}")          # a frase quebra em duas linhas
    assert has_text(texts, f"({info.current}/{info.target})")


def test_placa_mostra_nivel_de_prestigio_guardado_no_save(hub):
    hub.save.prestige = 2
    hub.prestige_seen = 2
    assert "PRESTÍGIO 2" in draw_texts(hub)


def test_placa_mostra_nivel_travado_quando_o_proximo_esta_desligado(hub, c):
    hub.save.prestige = 3
    hub.prestige_seen = 3
    info = prestige_info(c, hub.save)
    if info.locked:                     # 10a: niveis 4 e 5 ficam travados
        assert has_text(draw_texts(hub), "travado")


def _cor_do_texto(h, texto: str):
    """Cor com que `texto` foi desenhado no quadro (via spy em font.draw)."""
    got, real = {}, font.draw

    def spy(surf, text, x, y, color, *a, **k):
        got[str(text)] = color
        return real(surf, text, x, y, color, *a, **k)

    font.draw = spy
    try:
        draw_hub_frame(pygame.Surface((W, H)), h, UIState())
    finally:
        font.draw = real
    return got[texto]


def test_placa_vagas_verdes_abaixo_amarelas_no_limite_vermelhas_acima(hub, c):
    def rotulo() -> str:
        return f"{occupied(hub.save)}/{kennel_slots(c, hub.save)}"
    assert _cor_do_texto(hub, rotulo()) == C["good"]
    fill_kennel(c, hub.save)
    assert _cor_do_texto(hub, rotulo()) == C["warn"]
    add_cats(hub.save, adults=1)
    assert kennel_over_limit(c, hub.save) and _cor_do_texto(hub, rotulo()) == C["bad"]


def _centro_da_placa(h, a) -> tuple[int, int]:
    x, y, w, hh = pen_world.sign_rect(a, h.lock_spec.sign_size)
    return x + w // 2, y + hh // 2


def test_ha_uma_placa_no_quintal_para_cada_area(hub, c):
    assert len(hub.lock_spec.areas) == len(c.shop["areas"])
    assert {a.id for a in hub.lock_spec.areas} == set(area_ids(c))


def test_clicar_na_placa_abre_o_painel_da_area_e_esc_fecha(hub):
    primeira = hub.lock_spec.areas[0]
    hub.save.coins = area_def(game_content(), 0)["price"]
    pos = _centro_da_placa(hub, primeira)
    assert hub.sign_at(pos) == primeira.id and hub.hit(pos) == ("area_sign", primeira.id)
    hub.click(hub.hit(pos))
    assert hub.area_open == primeira.id
    assert has_text(draw_texts(hub), "COMPRAR")
    assert hub.escape() is True and hub.area_open is None


def test_placa_some_depois_de_comprar_a_area(hub, c):
    primeira = next(a for a in hub.lock_spec.areas if a.id == area_def(c, 0)["id"])
    pos = _centro_da_placa(hub, primeira)
    hub.save.coins = area_def(c, 0)["price"]
    buy_area_at_yard(hub, primeira.id)
    assert hub.sign_at(pos) is None


def test_painel_da_area_clique_fora_fecha_sem_comprar(hub, c):
    a = area_def(c, 0)
    hub.save.coins = a["price"]
    hub.area_open = a["id"]
    hub.click(("pen_floor",))
    assert hub.area_open is None and a["id"] not in hub.save.areas_unlocked and hub.save.coins == a["price"]


def test_painel_da_area_so_fecha_com_botao_fechar(hub, c):
    a = area_def(c, 0)
    hub.area_open = a["id"]
    hub.click(("area_close",))
    assert hub.area_open is None
