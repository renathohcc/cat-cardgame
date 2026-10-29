"""Layouts contra a arte (T8.6): duelo (retrato, gema de HP, botao, paineis, mao 1..7), hub, run e
criatorio dentro de 960x540, botoes dentro de modais. So geometria, sem janela.

Escritos a partir de reports/T8.2, T8.3 e T8.5 (tabela de geometria e marcadores da arte).
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
import pytest

from ui import layout as L
from ui import layout_breed as LB
from ui import layout_hub as LH
from ui import layout_run as LR
from ui.theme import H, W

PLAYER, ENEMY = "player", "enemy"
TELA = pygame.Rect(0, 0, W, H)


def dentro(r: pygame.Rect, area: pygame.Rect = TELA) -> bool:
    return area.contains(r)


# ================================================================== duelo x arte
def test_resolucao_interna_e_960x540():
    assert (W, H) == (960, 540)


@pytest.mark.parametrize("side,y", [(ENEMY, 2), (PLAYER, 322)])
def test_retrato_do_lider_e_64x56_no_medalhao(side, y):
    r = L.leader_rect(side)
    assert r.size == (64, 56) and r.x == 448 and r.y == y
    assert dentro(r)


@pytest.mark.parametrize("side", [ENEMY, PLAYER])
def test_gema_de_hp_do_lider_e_40x40_em_x540_e_nao_toca_o_retrato(side):
    g = L.leader_hp_rect(side)
    assert g.size == (40, 40) and g.x == 540 and dentro(g)
    assert not g.colliderect(L.leader_rect(side))
    assert g.centery == L.leader_hp_center(side)[1] and g.centerx == L.leader_hp_center(side)[0]
    assert abs(g.centery - L.leader_rect(side).centery) <= 24


def test_botao_de_fim_de_turno_fica_na_coluna_direita_e_na_altura_da_arte():
    r = L.pass_rect()
    assert dentro(r, pygame.Rect(802, 154, 955 - 802 + 1, 225 - 154 + 1))
    assert r.size[0] >= 140 and r.size[1] >= 56


def test_confirmacao_de_passar_turno_cabe_no_botao():
    p = L.pass_rect()
    for r in (L.pass_yes_rect(), L.pass_no_rect()):
        assert p.contains(r) and r.w > 20 and r.h > 10
    assert not L.pass_yes_rect().colliderect(L.pass_no_rect())


COLUNA_ESQ = pygame.Rect(6, 0, 150, H)
COLUNA_DIR = pygame.Rect(802, 0, 154, H)


def paineis_esquerdos():
    return {"turno": L.turn_rect(), "info": L.info_rect(), "log": L.log_rect(), "mensagem": L.message_rect()}


def test_paineis_da_esquerda_ficam_na_coluna_pintada_e_nao_se_sobrepoem():
    ps = paineis_esquerdos()
    for nome, r in ps.items():
        assert r.x >= 6 and r.right <= 156 and r.y >= 0 and r.bottom <= H, nome
    nomes = list(ps)
    for i, a in enumerate(nomes):
        for b in nomes[i + 1:]:
            assert not ps[a].colliderect(ps[b]), (a, b)


def test_paineis_da_esquerda_nao_tocam_o_campo():
    campo = pygame.Rect(L.FIELD_X, 0, L.MAIN_W, H)
    for nome, r in paineis_esquerdos().items():
        assert not r.colliderect(campo), nome


def test_paineis_da_esquerda_tem_ordem_vertical_turno_info_log_mensagem():
    ys = [L.turn_rect().y, L.info_rect().y, L.log_rect().y, L.message_rect().y]
    assert ys == sorted(ys) and len(set(ys)) == 4


def test_baralhos_energia_e_botao_ficam_na_coluna_direita_sem_se_tocar():
    rs = {"pilha_inimiga": L.enemy_pile_rect(), "botao": L.pass_rect(), "pilha": L.pile_rect(),
          "energia": L.energy_rect()}
    for nome, r in rs.items():
        assert r.x >= 778 and r.right <= 956 and dentro(r), nome
    nomes = list(rs)
    for i, a in enumerate(nomes):
        for b in nomes[i + 1:]:
            assert not rs[a].colliderect(rs[b]), (a, b)


def test_slots_nao_se_sobrepoem_e_ficam_entre_as_colunas():
    todos = [(s, n, L.slot_rect(s, n)) for s in (PLAYER, ENEMY) for n in range(5)]
    for i, (_, _, a) in enumerate(todos):
        assert dentro(a) and a.x >= 160 and a.right <= 800
        for _, _, b in todos[i + 1:]:
            assert not a.colliderect(b)


def test_lideres_nao_cobrem_slots_nem_a_mao():
    for side in (PLAYER, ENEMY):
        for r in (L.leader_rect(side), L.leader_hp_rect(side), L.leader_taunt_rect(side),
                  L.leader_name_rect(side)):
            for s in (PLAYER, ENEMY):
                for n in range(5):
                    assert not r.colliderect(L.slot_rect(s, n)), (side, r, s, n)


def test_lider_do_jogador_fica_acima_da_faixa_da_mao():
    assert L.leader_rect(PLAYER).bottom <= L.HAND_STRIP_Y
    assert L.leader_rect(ENEMY).bottom <= L.slot_rect(ENEMY, 0).y


# ================================================================== mao 1..7 x tudo
def elementos_fixos(com_slots_do_jogador: bool = False) -> dict[str, pygame.Rect]:
    d = {"pilha": L.pile_rect(), "pilha_inimiga": L.enemy_pile_rect(), "energia": L.energy_rect(),
         "botao": L.pass_rect(), "turno": L.turn_rect(), "info": L.info_rect(), "log": L.log_rect(),
         "mensagem": L.message_rect()}
    for s in (PLAYER, ENEMY):
        d[f"lider_{s}"] = L.leader_rect(s)
        d[f"hp_{s}"] = L.leader_hp_rect(s)
        d[f"taunt_{s}"] = L.leader_taunt_rect(s)
        d[f"nome_{s}"] = L.leader_name_rect(s)
    if com_slots_do_jogador:
        for n in range(5):
            d[f"slot_{n}"] = L.slot_rect(PLAYER, n)
    return d


@pytest.mark.parametrize("n", range(1, 8))
def test_mao_cabe_na_faixa_propria(n):
    for i in range(n):
        r = L.hand_rect(i, n)
        assert r.x >= 12 and r.right <= 772 and r.y >= L.HAND_STRIP_Y and r.bottom <= H, (n, i, r)
        assert r.size == (L.CARD_W, L.CARD_H)


@pytest.mark.parametrize("n", range(1, 8))
def test_mao_nao_sobrepoe_lider_energia_botoes_nem_baralho(n):
    fixos = elementos_fixos(com_slots_do_jogador=True)
    for i in range(n):
        for rotulo, r in (("repouso", L.hand_rect(i, n)), ("area_de_hover", L.hand_hit_rect(i, n))):
            for nome, f in fixos.items():
                assert not r.colliderect(f), f"mao n={n} i={i} ({rotulo}) cobre {nome}"


@pytest.mark.parametrize("n", range(1, 8))
def test_carta_da_mao_em_hover_ampliada_nao_cobre_energia_botoes_nem_baralhos(n):
    """Hover sobe 18 e cresce 8 (render.draw_hand): confere o retangulo desenhado."""
    fixos = elementos_fixos(com_slots_do_jogador=True)
    for nome in ("lider_player", "hp_player", "nome_player", "taunt_player"):
        fixos.pop(nome)                  # o lider tem checagem propria logo abaixo
    for i in range(n):
        r = L.hand_rect(i, n).move(0, -L.HOVER_RISE).inflate(8, 8)
        assert TELA.contains(r)
        for nome, f in fixos.items():
            assert not r.colliderect(f), f"hover n={n} i={i} cobre {nome}"


@pytest.mark.parametrize("n", range(1, 8))
def test_carta_da_mao_em_hover_nao_cobre_o_retrato_do_lider_do_jogador(n):
    lider = L.leader_rect(PLAYER)
    for i in range(n):
        r = L.hand_rect(i, n).move(0, -L.HOVER_RISE).inflate(8, 8)
        assert not r.colliderect(lider), f"hover n={n} i={i}: {r} cobre {lider}"


@pytest.mark.parametrize("n", range(1, 8))
def test_mao_e_simetrica_em_torno_do_centro_da_faixa(n):
    xs0 = L.hand_rect(0, n).x
    xs1 = L.hand_rect(n - 1, n).right
    assert abs((xs0 + xs1) / 2 - (L.HAND_X0 + L.HAND_X1) / 2) <= 1


@pytest.mark.parametrize("n", range(2, 8))
def test_mao_em_ordem_da_esquerda_para_a_direita_e_passo_no_maximo_o_do_campo(n):
    xs = [L.hand_rect(i, n).x for i in range(n)]
    assert xs == sorted(xs) and len(set(xs)) == n
    assert L.hand_pitch(n) <= L.PITCH


def test_hit_test_acha_cada_carta_da_mao_no_proprio_centro_sem_roubar_de_vizinha():
    for n in range(1, 8):
        for i in range(n):
            assert L.hit_test(L.hand_rect(i, n).topleft, n) == ("hand", i)


def test_hit_test_do_botao_e_dos_slots():
    assert L.hit_test(L.pass_rect().center, 3) == ("pass",)
    assert L.hit_test(L.slot_rect(PLAYER, 2).center, 3) == ("slot", PLAYER, 2)
    assert L.hit_test(L.slot_rect(ENEMY, 0).center, 3) == ("slot", ENEMY, 0)


def test_painel_final_e_botoes_ficam_dentro_da_tela():
    p = L.final_panel()
    assert dentro(p)
    for nome, r in L.final_buttons().items():
        assert p.contains(r), nome
    assert p.contains(L.continue_rect())


def test_botoes_finais_nao_se_sobrepoem():
    rs = list(L.final_buttons().values())
    for i, a in enumerate(rs):
        for b in rs[i + 1:]:
            assert not a.colliderect(b)


# ================================================================== hub
def rects_do_hub() -> dict[str, pygame.Rect]:
    d: dict[str, pygame.Rect] = {}
    for i, _ in enumerate(LH.MENU_ITEMS):
        d[f"menu_{i}"] = LH.menu_button(i)
    d["menu_info"] = LH.menu_info_rect()
    d["confirm_panel"] = LH.confirm_panel()
    for k, r in LH.confirm_buttons().items():
        d[k] = r
    for i in range(LH.ROWS_VISIBLE):
        d[f"linha_{i}"] = LH.row_rect(i)
    d["rolar_cima"], d["rolar_baixo"], d["trilho"] = LH.scroll_up_rect(), LH.scroll_down_rect(), LH.scroll_track()
    for i in range(len(LH.SORT_KEYS)):
        d[f"ordem_{i}"] = LH.sort_button(i)
    d["filtro"] = LH.filter_button()
    d["detalhe"] = LH.detail_panel()
    d["renomear"], d["doar"] = LH.rename_button(), LH.donate_button()
    d["doar_painel"] = LH.donate_panel()
    for k, r in LH.donate_buttons().items():
        d["doar_" + k] = r
    for k, r in LH.action_buttons().items():
        d["acao_" + k] = r
    d["rename_painel"], d["rename_input"] = LH.rename_panel(), LH.rename_input()
    for k, r in LH.rename_buttons().items():
        d["rename_" + k] = r
    d["resultado"] = LH.result_button()
    for i in range(LH.ADOPT_PER_PAGE):
        d[f"oferta_{i}"] = LH.adopt_card(i)
        for k, r in LH.adopt_buttons(i).items():
            d[f"oferta_{i}_{k}"] = r
    for k, r in LH.adopt_nav().items():
        d["nav_" + k] = r
    return d


@pytest.mark.parametrize("nome,r", rects_do_hub().items())
def test_retangulo_do_hub_cabe_em_960x540(nome, r):
    assert dentro(r), (nome, r)
    assert r.w > 0 and r.h > 0


def test_linhas_da_colecao_nao_se_sobrepoem_nem_tocam_o_painel_de_detalhe():
    det = LH.detail_panel()
    rows = [LH.row_rect(i) for i in range(LH.ROWS_VISIBLE)]
    for i, a in enumerate(rows):
        assert not a.colliderect(det)
        for b in rows[i + 1:]:
            assert not a.colliderect(b)
    for r in (LH.scroll_up_rect(), LH.scroll_down_rect(), LH.scroll_track()):
        assert not r.colliderect(det)
        for row in rows:
            assert not r.colliderect(row)


def test_botoes_do_detalhe_ficam_dentro_do_painel_de_detalhe():
    det = LH.detail_panel()
    for r in (LH.rename_button(), LH.donate_button()):
        assert det.contains(r), r


def test_botoes_de_acao_da_colecao_ficam_abaixo_do_detalhe_sem_se_sobrepor():
    det = LH.detail_panel()
    bs = list(LH.action_buttons().values())
    for i, a in enumerate(bs):
        assert not a.colliderect(det) and dentro(a)
        for b in bs[i + 1:]:
            assert not a.colliderect(b)


def test_botoes_dos_modais_ficam_dentro_do_painel_e_sem_se_sobrepor():
    pares = [(LH.confirm_panel(), LH.confirm_buttons()), (LH.donate_panel(), LH.donate_buttons()),
             (LH.rename_panel(), {**LH.rename_buttons(), "input": LH.rename_input()}),
             (LR.quit_panel(), LR.quit_buttons())]
    for painel, botoes in pares:
        rs = list(botoes.values())
        for nome, r in botoes.items():
            assert painel.contains(r), (painel, nome, r)
        for i, a in enumerate(rs):
            for b in rs[i + 1:]:
                assert not a.colliderect(b), (painel, a, b)


def test_quatro_ofertas_de_adocao_nao_se_sobrepoem_e_seus_botoes_ficam_no_cartao():
    cards = [LH.adopt_card(i) for i in range(LH.ADOPT_PER_PAGE)]
    for i, a in enumerate(cards):
        assert dentro(a)
        for b in cards[i + 1:]:
            assert not a.colliderect(b)
        bs = list(LH.adopt_buttons(i).values())
        for b in bs:
            assert a.contains(b)
        assert not bs[0].colliderect(bs[1])


def test_navegacao_da_adocao_nao_toca_nos_cartoes_nem_entre_si():
    nav = list(LH.adopt_nav().values())
    for r in nav:
        for i in range(LH.ADOPT_PER_PAGE):
            assert not r.colliderect(LH.adopt_card(i))
    for i, a in enumerate(nav):
        for b in nav[i + 1:]:
            assert not a.colliderect(b)


def test_botoes_do_menu_nao_se_sobrepoem():
    rs = [LH.menu_button(i) for i in range(len(LH.MENU_ITEMS))]
    for i, a in enumerate(rs):
        for b in rs[i + 1:]:
            assert not a.colliderect(b)


# ================================================================== criatorio
def rects_do_criatorio() -> dict[str, pygame.Rect]:
    d: dict[str, pygame.Rect] = {}
    for s in ("M", "F"):
        d[f"cab_{s}"] = LB.list_header(s)
        for dd in (-1, 1):
            d[f"rolar_{s}_{dd}"] = LB.scroll_button(s, dd)
        for i in range(LB.ROWS):
            d[f"linha_{s}_{i}"] = LB.row_rect(s, i)
    d["painel_casais"], d["painel_filhotes"], d["lateral"] = LB.breed_panel(), LB.kitten_panel(), LB.side_panel()
    for i in range(LB.COUPLES_VISIBLE):
        d[f"casal_{i}"] = LB.couple_rect(i)
        d[f"cancelar_{i}"] = LB.cancel_button(i)
    for k, r in LB.action_buttons().items():
        d["acao_" + k] = r
    d["novidades"] = LB.news_button()
    return d


@pytest.mark.parametrize("nome,r", rects_do_criatorio().items())
def test_retangulo_do_criatorio_cabe_em_960x540(nome, r):
    assert dentro(r), (nome, r)


def test_listas_do_criatorio_nao_se_sobrepoem_nem_cobrem_os_paineis():
    paineis = [LB.breed_panel(), LB.kitten_panel(), LB.side_panel()]
    linhas = [LB.row_rect(s, i) for s in ("M", "F") for i in range(LB.ROWS)]
    for i, a in enumerate(linhas):
        for p in paineis:
            assert not a.colliderect(p), (a, p)
        for b in linhas[i + 1:]:
            assert not a.colliderect(b)
    assert not LB.breed_panel().colliderect(LB.kitten_panel())
    assert not LB.breed_panel().colliderect(LB.side_panel())
    assert not LB.kitten_panel().colliderect(LB.side_panel())


def test_casais_e_cancelar_ficam_dentro_do_painel_e_o_cancelar_dentro_do_casal():
    p = LB.breed_panel()
    for i in range(LB.COUPLES_VISIBLE):
        assert p.contains(LB.couple_rect(i))
        assert LB.couple_rect(i).contains(LB.cancel_button(i))
    cs = [LB.couple_rect(i) for i in range(LB.COUPLES_VISIBLE)]
    for i, a in enumerate(cs):
        for b in cs[i + 1:]:
            assert not a.colliderect(b)


def test_botoes_do_criatorio_ficam_no_painel_lateral_sem_se_tocar():
    side = LB.side_panel()
    bs = list(LB.action_buttons().values())
    for b in bs:
        assert side.contains(b)
    assert not bs[0].colliderect(bs[1])


def test_botoes_de_rolagem_ficam_dentro_do_cabecalho_da_lista():
    for s in ("M", "F"):
        h = LB.list_header(s)
        for d in (-1, 1):
            assert h.contains(LB.scroll_button(s, d))
        assert not LB.scroll_button(s, -1).colliderect(LB.scroll_button(s, 1))


# ================================================================== run
def camadas_reais() -> list[int]:
    """Quantidade de nos por camada, lida de data/run.json (o mapa real do jogo)."""
    import json
    from pathlib import Path
    d = json.loads((Path(__file__).resolve().parent.parent / "data" / "run.json").read_text(encoding="utf-8"))
    return [len(c["nodes"]) for c in d["map"]["layers"]]


def test_nos_do_mapa_real_cabem_na_tela_e_nao_se_sobrepoem():
    camadas = camadas_reais()
    flat = [LR.node_rect(layer, idx, n, len(camadas)) for layer, n in enumerate(camadas) for idx in range(n)]
    for i, a in enumerate(flat):
        assert dentro(a), a
        for b in flat[i + 1:]:
            assert not a.colliderect(b), (a, b)


def test_nos_de_um_mapa_menor_que_o_real_tambem_cabem():
    for n_layers in (2, 4, 6):
        for n_in in (1, 2, 3):
            flat = [LR.node_rect(layer, idx, n_in, n_layers) for layer in range(n_layers) for idx in range(n_in)]
            for i, a in enumerate(flat):
                assert dentro(a)
                for b in flat[i + 1:]:
                    assert not a.colliderect(b)


def test_no_unico_numa_camada_so_fica_dentro_da_tela_e_acima_do_painel_de_info():
    r = LR.node_rect(0, 0, 1, 1)
    assert dentro(r)
    assert not r.colliderect(LR.map_info_rect())


def test_mapa_nos_nao_tocam_titulo_info_nem_abandonar():
    for n_layers in (len(camadas_reais()),):
        for n_in in (1, 2, 3):
            for layer in range(n_layers):
                for idx in range(n_in):
                    r = LR.node_rect(layer, idx, n_in, n_layers)
                    for o in (LR.title_rect(), LR.map_info_rect(), LR.abandon_rect()):
                        assert not r.colliderect(o), (layer, idx, n_in, n_layers, o)


def test_rects_fixos_da_run_cabem_na_tela():
    for r in (LR.map_info_rect(), LR.abandon_rect(), LR.title_rect(), LR.draft_deck_rect(),
              LR.quit_panel(), *LR.end_buttons().values(), *LR.quit_buttons().values()):
        assert dentro(r), r


@pytest.mark.parametrize("n", [1, 2, 3])
def test_draft_com_n_cartas_cabe_na_tela_sem_sobrepor_o_deck(n):
    cards = [LR.draft_card_rect(i, n) for i in range(n)]
    for i, a in enumerate(cards):
        assert dentro(a) and dentro(LR.draft_pick_rect(i, n))
        assert not a.colliderect(LR.draft_deck_rect())
        assert not LR.draft_pick_rect(i, n).colliderect(LR.draft_deck_rect())
        assert not LR.draft_pick_rect(i, n).colliderect(a)
        for b in cards[i + 1:]:
            assert not a.colliderect(b)


def test_botoes_do_fim_da_run_nao_se_sobrepoem():
    a, b = LR.end_buttons().values()
    assert not a.colliderect(b)
