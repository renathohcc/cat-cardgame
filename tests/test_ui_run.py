"""Testes da UI da mini-run (T4.4b), sem janela: RunController, layout_run, cenas e fuzz.

Escritos a partir de reports/T4.3-ui-run.md e T4.2-core-run.md. O estado final e sempre
conferido na API publica do core (`run.status`, `run.result`, `run.cards`).
"""
from __future__ import annotations

import os
from random import Random

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from core.ai import choose_action
from core.types import EndTurn
from ui import layout as L
from ui import layout_run as LR
from ui import scenes_run
from ui.controller import Controller, load_game_content
from ui.run_controller import RunController
from ui.theme import H, W


@pytest.fixture(scope="module")
def content():
    return load_game_content()


def novo(content, seed: int = 1) -> RunController:
    return RunController(content, seed, ai_delay=0.0)


def jogar_duelo(rc: RunController, rng: Random, vencer: bool = True) -> None:
    """Termina o duelo atual: IA no lugar do jogador (vencer) ou so passando turno."""
    c = rc.duel_ctrl
    for _ in range(6000):
        if c.over:
            break
        if c.can_act():
            c._do(choose_action(c.duel, "player", rng) if vencer else EndTurn())
        c.update(5.0)
    for _ in range(5):
        c.update(1.0)
    assert c.final_visible


def rc_com_draft(content) -> RunController:
    """Run parada no draft logo apos vencer o primeiro duelo."""
    for s in range(1, 60):
        rc = novo(content, s)
        rc.click(("node", "c1-batalha"))
        jogar_duelo(rc, Random(s))
        rc.click(("continue",))
        if rc.screen == "draft":
            return rc
    raise AssertionError("nenhuma seed venceu o primeiro duelo")


def rc_derrota(content) -> RunController:
    """Run com o primeiro duelo perdido, painel final visivel (ainda nao continuou)."""
    for s in range(1, 30):
        rc = novo(content, s)
        rc.click(("node", "c1-batalha"))
        jogar_duelo(rc, Random(s), vencer=False)
        if rc.duel_ctrl.duel.winner == "enemy":
            return rc
    raise AssertionError("nao consegui perder passando turno")


# ------------------------------------------------------------------ mapa
def test_run_comeca_no_mapa_com_so_a_primeira_camada_disponivel(content):
    rc = novo(content)
    assert rc.screen == "map" and rc.run.status == "map"
    assert rc.available_ids() == ["c1-batalha"]


def test_clicar_no_disponivel_entra_no_duelo(content):
    rc = novo(content)
    rc.click(("node", "c1-batalha"))
    assert rc.screen == "duel" and rc.run.status == "duel"
    assert rc.duel_ctrl is not None and rc.visited == ["c1-batalha"]


def test_clicar_no_indisponivel_nao_entra_e_vira_aviso(content):
    rc = novo(content)
    rc.click(("node", "c6-chefe"))
    assert rc.screen == "map" and rc.run.status == "map"
    assert rc.visited == [] and rc.toast is not None


def test_no_ja_vencido_nao_pode_ser_escolhido_de_novo(content):
    rc = rc_com_draft(content)
    rc.click(("draft_card", 0))
    rc.click(("draft_pick", 0))
    assert rc.screen == "map"
    antes = list(rc.visited)
    rc.click(("node", "c1-batalha"))
    assert rc.screen == "map" and rc.visited == antes


def test_elementos_nulos_ou_de_outra_tela_nao_quebram_o_mapa(content):
    rc = novo(content)
    rc.click(None)
    rc.click(("nada",))
    rc.click(("draft_pick", 0))
    rc.click(("continue",))
    assert rc.screen == "map"


# ------------------------------------------------------------------ duelo -> draft / derrota
def test_vitoria_no_duelo_continuar_leva_ao_draft(content):
    rc = rc_com_draft(content)
    assert rc.screen == "draft" and rc.run.status == "draft"
    assert len(rc.run.draft_options) == 3 and rc.duel_ctrl is None


def test_continuar_antes_do_fim_do_duelo_nao_faz_nada(content):
    rc = novo(content)
    rc.click(("node", "c1-batalha"))
    rc.click(("continue",))
    rc.confirm_key()
    assert rc.screen == "duel"


def test_painel_final_em_run_mode_so_tem_continuar(content):
    rc = novo(content)
    rc.click(("node", "c1-batalha"))
    jogar_duelo(rc, Random(3))
    assert rc.duel_ctrl.run_mode
    assert rc.hit(L.final_buttons()["again"].center) is None
    assert rc.hit(L.final_buttons()["repeat"].center) is None
    assert rc.hit(L.continue_rect().center) == ("continue",)
    rc.click(("again",))
    rc.click(("repeat",))
    assert rc.screen == "duel" and rc.duel_ctrl.over       # ignorados em run_mode


def test_derrota_no_duelo_leva_ao_fim_da_run(content):
    rc = rc_derrota(content)
    rc.click(("continue",))
    assert rc.screen == "finished" and rc.run.status == "finished"
    assert rc.run.result == "derrota"
    assert rc.path_lines()[-1][1] == "lost"


def test_enter_no_fim_do_duelo_continua(content):
    rc = rc_derrota(content)
    rc.confirm_key()
    assert rc.screen == "finished"


def test_fora_do_run_mode_painel_final_continua_com_jogar_de_novo(content):
    c = Controller(content, 1, ai_delay=0.0)
    assert not c.run_mode
    for _ in range(6000):
        if c.over:
            break
        if c.can_act():
            c._do(choose_action(c.duel, "player", Random(1)))
        c.update(5.0)
    for _ in range(5):
        c.update(1.0)
    assert c.final_visible
    c.click(("again",))
    assert not c.over


# ------------------------------------------------------------------ draft
def test_draft_primeiro_clique_seleciona_sem_escolher(content):
    rc = rc_com_draft(content)
    cartas = len(rc.run.cards)
    rc.click(("draft_card", 1))
    assert rc.draft_sel == 1 and rc.screen == "draft" and len(rc.run.cards) == cartas


def test_draft_segundo_clique_na_carta_confirma(content):
    rc = rc_com_draft(content)
    escolhida = rc.run.draft_options[1]
    rc.click(("draft_card", 1))
    rc.click(("draft_card", 1))
    assert rc.screen == "map" and rc.run.cards[-1] == escolhida


def test_draft_botao_escolher_confirma(content):
    rc = rc_com_draft(content)
    escolhida = rc.run.draft_options[2]
    rc.click(("draft_card", 2))
    assert rc.hit(LR.draft_pick_rect(2, 3).center) == ("draft_pick", 2)
    rc.click(("draft_pick", 2))
    assert rc.screen == "map" and rc.run.cards == [escolhida]


def test_draft_enter_confirma_so_com_selecao(content):
    rc = rc_com_draft(content)
    rc.confirm_key()
    assert rc.screen == "draft" and rc.run.cards == []
    rc.click(("draft_card", 0))
    esc = rc.run.draft_options[0]
    rc.confirm_key()
    assert rc.screen == "map" and rc.run.cards == [esc]


def test_draft_esc_desmarca_e_nao_sai_da_tela(content):
    rc = rc_com_draft(content)
    rc.click(("draft_card", 0))
    rc.cancel()
    assert rc.draft_sel is None and rc.screen == "draft" and not rc.quit_confirm


def test_draft_trocar_selecao_nao_confirma(content):
    rc = rc_com_draft(content)
    rc.click(("draft_card", 0))
    rc.click(("draft_card", 1))
    assert rc.draft_sel == 1 and rc.screen == "draft" and rc.run.cards == []


def test_pick_adiciona_a_carta_ao_deck_summary(content):
    rc = rc_com_draft(content)
    antes = rc.deck_summary()
    cid = rc.run.draft_options[0]
    rc.click(("draft_card", 0))
    rc.click(("draft_pick", 0))
    depois = rc.deck_summary()
    assert depois["cards"] == antes["cards"] + 1 and depois["cats"] == antes["cats"]
    chave = "spirits" if rc.is_spirit(cid) else "effects"
    assert depois[chave] == antes[chave] + 1
    assert rc.draft_owned(cid) == 1


def test_draft_com_indice_invalido_nao_levanta_nem_escolhe(content):
    rc = rc_com_draft(content)
    rc.click(("draft_pick", 9))
    rc.click(("draft_card", 9))
    rc.click(("draft_card", -1))
    assert rc.screen == "draft" and rc.run.cards == []


def test_draft_apos_vitoria_nao_tem_titulo_de_descanso(content):
    assert "Descanso" not in rc_com_draft(content).draft_title()


def test_descanso_abre_draft_com_titulo_de_descanso(content):
    rc = rc_com_draft(content)
    rc.click(("draft_card", 0))
    rc.click(("draft_pick", 0))
    assert "c2-descanso" in rc.available_ids()
    rc.click(("node", "c2-descanso"))
    assert rc.screen == "draft" and rc.run.status == "draft"
    assert rc.draft_title() == "Descanso: escolha 1 de 2"
    assert rc.duel_ctrl is None and len(rc.run.draft_options) == 2
    rc.click(("draft_card", 0))
    rc.click(("draft_pick", 0))
    assert rc.screen == "map" and rc.run.layer == 2


# ------------------------------------------------------------------ fim da run
def _run_vitoriosa() -> RunController:
    for s in range(1, 120):
        made = scenes_run.make(s, "fimrun_vitoria")
        if made:
            return made[0]
    raise AssertionError("sem run vitoriosa")


def test_chefe_vencido_termina_em_vitoria(content):
    rc = _run_vitoriosa()
    assert rc.screen == "finished" and rc.run.result == "vitoria"
    assert rc.visited[-1] == "c6-chefe" and rc.run.nodes_cleared >= 1
    assert not rc.abandoned


def test_fim_da_run_sair_e_nova_run(content):
    rc = rc_derrota(content)
    rc.click(("continue",))
    rc.seed_source = lambda: 77
    assert rc.hit(LR.end_buttons()["quit"].center) == ("quit",)
    rc.click(("quit",))
    assert rc.wants_quit
    rc.wants_quit = False
    rc.click(("new_run",))
    assert rc.screen == "map" and rc.seed == 77 and rc.visited == []
    assert rc.run.result is None


def test_esc_no_fim_pede_para_sair_e_enter_comeca_nova_run(content):
    rc = rc_derrota(content)
    rc.click(("continue",))
    rc.cancel()
    assert rc.wants_quit
    rc.seed_source = lambda: 5
    rc.confirm_key()
    assert rc.screen == "map" and rc.seed == 5


# ------------------------------------------------------------------ abandonar
def test_abandonar_pede_confirmacao_e_nao_abandona_antes(content):
    rc = novo(content)
    rc.click(("abandon",))
    assert rc.quit_confirm and rc.screen == "map" and rc.run.status == "map"
    rc.click(("quit_no",))
    assert not rc.quit_confirm and rc.screen == "map"


def test_abandonar_sim_termina_em_derrota(content):
    rc = novo(content)
    rc.click(("abandon",))
    rc.click(("quit_yes",))
    assert rc.screen == "finished" and rc.run.result == "derrota" and rc.abandoned


def test_esc_no_mapa_pede_confirmacao_e_esc_de_novo_cancela(content):
    rc = novo(content)
    rc.cancel()
    assert rc.quit_confirm
    rc.cancel()
    assert not rc.quit_confirm and rc.screen == "map"


def test_com_confirmacao_aberta_so_os_botoes_da_confirmacao_respondem(content):
    rc = novo(content)
    rc.cancel()
    rc.click(("node", "c1-batalha"))
    assert rc.screen == "map" and rc.quit_confirm
    assert rc.hit(LR.node_rect(0, 0, 1, 6).center) is None
    assert rc.hit(LR.quit_buttons()["quit_yes"].center) == ("quit_yes",)


def test_esc_no_duelo_sem_selecao_pede_abandono_e_sim_da_derrota(content):
    rc = novo(content)
    rc.click(("node", "c1-batalha"))
    rc.duel_ctrl.dismiss_dice() if rc.duel_ctrl.phase == "dice" else None
    rc.duel_ctrl.update(10.0)
    while not rc.duel_ctrl.can_act() and not rc.duel_ctrl.over:
        rc.duel_ctrl.update(5.0)
    rc.cancel()
    assert rc.quit_confirm
    rc.click(("quit_yes",))
    assert rc.screen == "finished" and rc.run.result == "derrota"


# ------------------------------------------------------------------ determinismo
def test_segundo_duelo_da_run_usa_o_indice_dois(content):
    rc = rc_com_draft(content)
    assert rc.duels_started == 1 and rc.seed * 1000 + 1 == rc.seed * 1000 + rc.duels_started
    rc.click(("draft_card", 0))
    rc.click(("draft_pick", 0))
    rc.click(("node", [i for i in rc.available_ids() if "batalha" in i][0]))
    assert rc.duels_started == 2


def _assinatura(seed: int, content) -> tuple:
    rc = novo(content, seed)
    scenes_run.autoplay(rc, Random(seed + 5))
    return (rc.run.result, tuple(rc.visited), tuple(rc.run.cards), rc.run.nodes_cleared)


def test_mesma_seed_gera_a_mesma_run(content):
    assert _assinatura(4, content) == _assinatura(4, content)


def test_duelo_da_run_e_deterministico_por_seed(content):
    def hist(seed):
        rc = novo(content, seed)
        rc.click(("node", "c1-batalha"))
        jogar_duelo(rc, Random(2))
        return rc.duel_ctrl.duel.winner, len(rc.duel_ctrl.duel.log)
    assert hist(9) == hist(9)


# ------------------------------------------------------------------ fuzz
def _tela_bate_com_o_core(rc: RunController) -> None:
    assert rc.screen == rc.run.status
    assert (rc.duel_ctrl is not None) == (rc.run.status == "duel")
    if rc.run.status == "finished":
        assert rc.run.result in ("vitoria", "derrota")
    else:
        assert rc.run.result is None


@pytest.mark.parametrize("seed", range(50))
def test_fuzz_cliques_aleatorios_sem_excecao_e_tela_bate_com_o_core(content, seed):
    rc = novo(content, seed + 1)
    rng = Random(seed)
    for _ in range(400):
        _tela_bate_com_o_core(rc)
        if rc.screen == "finished":
            break
        if rc.screen == "duel":
            jogar_duelo(rc, rng, vencer=rng.random() < 0.8)
            rc.click(rng.choice([("continue",), None, ("again",)]))
            continue
        if rng.random() < 0.5:
            elem = rc.hit((rng.randrange(-5, W + 5), rng.randrange(-5, H + 5)))
        else:
            elem = rng.choice([("node", rng.choice(["c1-batalha", "c6-chefe", "x"])),
                               ("draft_card", rng.randrange(-1, 5)),
                               ("draft_pick", rng.randrange(-1, 5)),
                               ("quit_no",), None, ("abandon",)])
        rc.click(elem)
        if rng.random() < 0.1:
            rc.cancel()
        if rng.random() < 0.1:
            rc.confirm_key()
        rc.update(0.1)
        rc.wants_quit = False
    _tela_bate_com_o_core(rc)


@pytest.mark.parametrize("seed", range(5))
def test_fuzz_run_completa_com_ia_chega_ao_fim(content, seed):
    rc = novo(content, seed + 100)
    scenes_run.autoplay(rc, Random(seed))
    assert rc.screen == "finished" and rc.run.status == "finished"


# ------------------------------------------------------------------ layout
def _rects_mapa():
    layers = [1, 2, 1, 2, 1, 1]
    return {(li, ni): LR.node_rect(li, ni, n, len(layers))
            for li, n in enumerate(layers) for ni in range(n)}


def _rects_todos():
    d = {f"no{k}": r for k, r in _rects_mapa().items()}
    d["abandon"] = LR.abandon_rect()
    d["info"] = LR.map_info_rect()
    for i in range(3):
        d[f"card{i}"] = LR.draft_card_rect(i, 3)
        d[f"pick{i}"] = LR.draft_pick_rect(i, 3)
    d["deck"] = LR.draft_deck_rect()
    d["continue"] = L.continue_rect()
    d.update({f"fim_{k}": r for k, r in LR.end_buttons().items()})
    d["quitpanel"] = LR.quit_panel()
    d.update({f"q_{k}": r for k, r in LR.quit_buttons().items()})
    return d


def test_layout_run_todos_os_rects_dentro_da_tela():
    for nome, r in _rects_todos().items():
        assert 0 <= r.left and r.right <= W and 0 <= r.top and r.bottom <= H, nome


def test_layout_run_nos_do_mapa_e_abandonar_nao_se_sobrepoem():
    r = dict(_rects_mapa())
    r["abandon"] = LR.abandon_rect()
    nomes = list(r)
    for i, a in enumerate(nomes):
        for b in nomes[i + 1:]:
            assert not r[a].colliderect(r[b]), (a, b)


def test_layout_run_botoes_de_cada_tela_nao_se_sobrepoem():
    grupos = [
        [LR.draft_card_rect(i, 3) for i in range(3)] + [LR.draft_pick_rect(i, 3) for i in range(3)],
        list(LR.end_buttons().values()),
        list(LR.quit_buttons().values()),
    ]
    for g in grupos:
        for i, a in enumerate(g):
            for b in g[i + 1:]:
                assert not a.colliderect(b)
    for i in range(3):
        assert not LR.draft_pick_rect(i, 3).colliderect(LR.draft_deck_rect())
    for b in LR.quit_buttons().values():
        assert LR.quit_panel().contains(b)


@pytest.mark.parametrize("escala", [1, 2, 3, 4])
def test_hit_test_devolve_os_elementos_certos_em_todas_as_escalas(escala):
    size = (W * escala, H * escala)               # janela em escala inteira do canvas 960x540

    def pt(r):                                    # mouse na janela -> coordenadas internas 960x540
        return L.to_internal((r.centerx * escala, r.centery * escala), size)

    nodes = [(f"id{k}", r) for k, r in _rects_mapa().items()]
    for nid, r in nodes:
        assert LR.hit_test(pt(r), "map", nodes=nodes) == ("node", nid)
    assert LR.hit_test(pt(LR.abandon_rect()), "map", nodes=nodes) == ("abandon",)
    assert LR.hit_test((0, 0), "map", nodes=nodes) is None
    for i in range(3):
        assert LR.hit_test(pt(LR.draft_card_rect(i, 3)), "draft", n_draft=3) == ("draft_card", i)
        assert LR.hit_test(pt(LR.draft_pick_rect(i, 3)), "draft", n_draft=3, selected=i) == ("draft_pick", i)
        assert LR.hit_test(pt(LR.draft_pick_rect(i, 3)), "draft", n_draft=3) is None
    for k, r in LR.end_buttons().items():
        assert LR.hit_test(pt(r), "finished") == (k,)
    for k, r in LR.quit_buttons().items():
        assert LR.hit_test(pt(r), "map", confirm=True) == (k,)


# ------------------------------------------------------------------ screenshots
@pytest.mark.parametrize("cena", ["mapa", "draft", "descanso", "fimrun", "fimrun_vitoria", "duelrun"])
def test_cenas_de_screenshot_da_run_geram_png(cena, tmp_path):
    from ui.__main__ import main
    out = tmp_path / f"{cena}.png"
    assert main(["--seed", "1", "--screenshot", str(out), "--cena", cena]) == 0
    data = out.read_bytes()
    assert len(data) > 1000 and data[:8] == b"\x89PNG\r\n\x1a\n"


@pytest.mark.parametrize("cena", ["mapa", "draft", "descanso", "fimrun", "duelrun"])
def test_cenas_da_run_sao_deterministicas_por_seed(cena):
    def estado():
        made = scenes_run.make(2, cena)
        assert made is not None
        rc, _ = made
        return (rc.screen, tuple(rc.visited), tuple(rc.run.cards), tuple(rc.run.draft_options))
    assert estado() == estado()


# ------------------------------------------------------------------ T4.9: recompensas (elite 2/2, 2 e 3 opcoes)
def _escolher_primeira(rc: RunController) -> None:
    rc.click(("draft_card", 0))
    rc.click(("draft_pick", 0))


def _avancar_ate_elite(content, seed: int) -> RunController | None:
    """Joga com a IA ate vencer o duelo da elite (c4-elite); None se perder pelo caminho."""
    rc = novo(content, seed)
    rng = Random(seed)
    while rc.screen != "finished":
        if rc.screen == "map":
            ids = rc.available_ids()
            alvo = "c4-elite" if "c4-elite" in ids else next(
                (i for i in ids if "batalha" in i), ids[0])
            rc.click(("node", alvo))
        elif rc.screen == "duel":
            jogar_duelo(rc, rng)
            rc.click(("continue",))
            if rc.screen == "draft" and rc.draft_from == "elite":
                return rc
        elif rc.screen == "draft":
            _escolher_primeira(rc)
    return None


@pytest.fixture(scope="module")
def rc_elite(content):
    for s in range(1, 80):
        rc = _avancar_ate_elite(content, s)
        if rc is not None:
            return rc
    raise AssertionError("nenhuma seed venceu a elite")


def test_titulo_do_draft_da_elite_mostra_1_de_2_e_depois_2_de_2(rc_elite):
    rc = rc_elite
    assert rc.draft_title() == "Vitória! Escolha 1 de 3 (1/2)"
    _escolher_primeira(rc)
    assert rc.draft_title() == "Vitória! Escolha 1 de 3 (2/2)"


def test_elite_continua_em_draft_apos_o_primeiro_pick_e_volta_ao_mapa_no_segundo(rc_elite):
    rc = rc_elite
    # o fixture e compartilhado: se o teste anterior ja fez o 1o pick, seguimos do 2o
    if rc.run.draft_step == 1:
        n = len(rc.run.cards)
        _escolher_primeira(rc)
        assert rc.screen == "draft" and rc.run.status == "draft"
        assert len(rc.run.cards) == n + 1
    assert rc.run.draft_step == 2
    n = len(rc.run.cards)
    _escolher_primeira(rc)
    assert rc.screen == "map" and rc.run.status == "map"
    assert len(rc.run.cards) == n + 1


def test_batalha_comum_tem_titulo_sem_sufixo(content):
    rc = rc_com_draft(content)
    assert rc.draft_title() == "Vitória! Escolha 1 de 3"
    assert rc.draft_progress() == ""


def test_descanso_tem_titulo_sem_sufixo_de_progresso(content):
    rc = rc_com_draft(content)
    _escolher_primeira(rc)
    rc.click(("node", "c2-descanso"))
    assert rc.draft_progress() == "" and "(" not in rc.draft_title()


@pytest.mark.parametrize("n", [2, 3])
def test_layout_do_draft_com_n_opcoes_sem_sobreposicao(n):
    cartas = [LR.draft_card_rect(i, n) for i in range(n)]
    picks = [LR.draft_pick_rect(i, n) for i in range(n)]
    todos = cartas + picks + [LR.draft_deck_rect()]
    for r in todos:
        assert 0 <= r.left and r.right <= W and 0 <= r.top and r.bottom <= H
    for i, a in enumerate(todos):
        for b in todos[i + 1:]:
            if a is picks[0] and b is cartas[0]:
                continue
            assert not a.colliderect(b), (a, b)
    # simetria horizontal: o conjunto fica centralizado na tela
    assert abs((cartas[0].left + cartas[-1].right) / 2 - W / 2) <= 1


@pytest.mark.parametrize("n", [2, 3])
def test_hit_test_do_draft_acerta_cada_carta_com_n_opcoes(n):
    for i in range(n):
        assert LR.hit_test(LR.draft_card_rect(i, n).center, "draft", n_draft=n) == ("draft_card", i)
        assert LR.hit_test(LR.draft_pick_rect(i, n).center, "draft", n_draft=n,
                           selected=i) == ("draft_pick", i)


def _dica(content, tipo: str) -> list[str]:
    from ui.render_run import node_tip
    rc = novo(content)
    for layer in rc.run.layers:
        for node in layer["nodes"]:
            if node["tipo"] == tipo:
                return [t for t, _ in node_tip(rc, node)]
    raise AssertionError(tipo)


def test_dica_do_mapa_para_elite_diz_duas_escolhas(content):
    txt = " ".join(_dica(content, "elite"))
    assert "2 escolhas" in txt and "1 de 3" in txt


def test_dica_do_mapa_para_batalha_diz_1_de_3(content):
    txt = " ".join(_dica(content, "batalha"))
    assert "1 carta" in txt and "1 de 3" in txt and "2 escolhas" not in txt


def test_dica_do_mapa_para_descanso_diz_1_carta_entre_2(content):
    assert "Descanso: 1 carta entre 2." in _dica(content, "descanso")
