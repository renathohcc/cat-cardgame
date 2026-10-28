"""Testes do controlador da UI (sem pygame, sem janela) e fumaça das cenas de screenshot.

Escritos a partir do GDD e de reports/T2.1-ui-duelo.md. O estado do jogo e sempre
conferido contra a API publica do core (`legal_actions`, `attack_targets`, `view`).
"""
from __future__ import annotations

import os
from random import Random

import pytest

from core.duel import attack_targets, legal_actions, view
from core.types import Attack, PlayCat
from duel_helpers import duel, fc, load, mk
from ui.controller import Controller

PLAYER, ENEMY = "player", "enemy"


@pytest.fixture(scope="module")
def content():
    return load()


def ctrl_with(content, seed: int = 1, **kw) -> Controller:
    """Controlador sobre um duelo montado (turno do jogador, tudo parado, pronto para agir)."""
    c = Controller(content, seed, ai_delay=0.0)
    c.duel = duel(content, **kw)
    c.phase = "play"
    c.beats.clear()
    c.cur = None
    c.fx = []
    c.toast = None
    c.banner = None
    c.refresh()
    return c


def snap(c: Controller):
    d = c.duel
    return (view(d, PLAYER), view(d, ENEMY), len(d.log), d.turn_side, d.winner)


def run_until(c: Controller, pred, steps: int = 4000, dt: float = 0.1) -> bool:
    for _ in range(steps):
        if pred(c):
            return True
        c.update(dt)
    return pred(c)


def p_side(c: Controller):
    return c.duel.sides[PLAYER]


def e_side(c: Controller):
    return c.duel.sides[ENEMY]


# ---------------------------------------------------------------- jogar carta da mao
def test_clicar_carta_da_mao_seleciona_e_so_slots_vagos_sao_alvo(content):
    c = ctrl_with(content, player_hand=[mk(2, 2, cost=1)], player_energy=3,
                  player_field={0: fc(1, 1, ready=False), 3: fc(1, 1, ready=False)})
    c.click(("hand", 0))
    assert c.sel == ("hand", 0)
    assert c.playable[0] == {1, 2, 4}                      # 0 e 3 ocupados


def test_alvos_da_carta_selecionada_coincidem_com_as_jogadas_legais_do_core(content):
    c = ctrl_with(content, player_hand=[mk(2, 2, cost=1), mk(1, 1, cost=2)], player_energy=3,
                  player_field={2: fc(1, 1, ready=False)})
    legal_slots = {i: {a.slot for a in legal_actions(c.duel)
                       if isinstance(a, PlayCat) and a.hand_index == i} for i in (0, 1)}
    for i in (0, 1):
        c.click(("hand", i))
        assert c.sel == ("hand", i)
        assert c.playable[i] == legal_slots[i] == {0, 1, 3, 4}


def test_carta_sem_energia_nao_seleciona_e_mostra_o_motivo(content):
    c = ctrl_with(content, player_hand=[mk(2, 2, cost=3)], player_energy=1)
    antes = snap(c)
    c.click(("hand", 0))
    assert c.sel is None
    assert c.toast is not None and "energia" in c.toast.text.lower()
    ok, motivo = c.hand_state(0)
    assert ok is False
    assert "FALTAM" in motivo and any("2" in linha for linha in motivo)   # custa 3, tem 1
    assert snap(c) == antes


def test_clicar_no_slot_joga_o_gato_e_a_energia_cai(content):
    c = ctrl_with(content, player_hand=[mk(3, 2, cost=2, name="Mimi")], player_energy=3)
    c.click(("hand", 0))
    c.click(("slot", PLAYER, 2))
    assert c.sel is None
    assert p_side(c).energy == 1
    assert p_side(c).field[2] is not None and p_side(c).field[2].card.name == "Mimi"
    assert p_side(c).hand == []


def test_clicar_na_mesma_carta_de_novo_cancela_a_selecao(content):
    c = ctrl_with(content, player_hand=[mk(2, 2)], player_energy=3)
    c.click(("hand", 0))
    c.click(("hand", 0))
    assert c.sel is None


def test_slot_ocupado_nao_pronto_nao_recebe_a_carta_e_nada_muda(content):
    c = ctrl_with(content, player_hand=[mk(2, 2)], player_energy=3,
                  player_field={1: fc(1, 1, ready=False)})
    c.click(("hand", 0))
    antes = snap(c)
    c.click(("slot", PLAYER, 1))
    assert snap(c) == antes
    assert c.toast is not None


# ---------------------------------------------------------------- atacar
def test_clicar_em_gato_pronto_seleciona_e_alvos_sao_os_de_attack_targets(content):
    c = ctrl_with(content, player_field={0: fc(3, 5)}, enemy_field={0: fc(1, 5), 2: fc(1, 5)})
    c.click(("slot", PLAYER, 0))
    assert c.sel == ("slot", 0)
    assert set(c.sel_targets) == set(attack_targets(c.duel, 0))
    assert set(c.sel_targets) == {("leader",), ("slot", 0), ("slot", 2)}


def test_com_provocar_o_lider_nao_e_alvo_e_a_ui_avisa_protegido(content):
    c = ctrl_with(content, player_field={0: fc(3, 5)},
                  enemy_field={0: fc(1, 5, kw=("provocar",)), 1: fc(1, 5)})
    c.click(("slot", PLAYER, 0))
    assert ("leader",) not in c.sel_targets
    assert set(c.sel_targets) == set(attack_targets(c.duel, 0)) == {("slot", 0)}
    assert c.taunt_in_way() is True
    hp = e_side(c).leader_hp
    c.click(("leader", ENEMY))
    assert e_side(c).leader_hp == hp
    assert c.toast is not None and "provocar" in c.toast.text.lower()
    assert c.sel == ("slot", 0)                           # seleciona continua, pode escolher outro alvo


def test_sem_provocar_nao_ha_aviso_de_protecao(content):
    c = ctrl_with(content, player_field={0: fc(3, 5)}, enemy_field={0: fc(1, 5)})
    assert c.taunt_in_way() is False


def test_clicar_no_lider_inimigo_quando_legal_ataca(content):
    c = ctrl_with(content, player_field={0: fc(3, 5)}, enemy_field={0: fc(1, 5)})
    # o gato inimigo e alvo possivel mas o Lider tambem (sem Provocar)
    hp = e_side(c).leader_hp
    c.click(("slot", PLAYER, 0))
    c.click(("leader", ENEMY))
    assert e_side(c).leader_hp == hp - 3
    assert c.sel is None


def test_clicar_num_gato_inimigo_legal_ataca_o_gato(content):
    c = ctrl_with(content, player_field={0: fc(2, 5)}, enemy_field={1: fc(1, 5)})
    c.click(("slot", PLAYER, 0))
    c.click(("slot", ENEMY, 1))
    assert e_side(c).field[1].hp == 3


def test_gato_que_nao_pode_atacar_nao_e_selecionado_e_mostra_motivo(content):
    c = ctrl_with(content, player_field={0: fc(3, 5, ready=False)}, enemy_field={0: fc(1, 5)})
    antes = snap(c)
    c.click(("slot", PLAYER, 0))
    assert c.sel is None
    assert c.toast is not None
    assert snap(c) == antes


def test_gato_que_ja_atacou_nao_ataca_de_novo(content):
    c = ctrl_with(content, player_field={0: fc(3, 5)}, enemy_field={0: fc(1, 9)})
    c.click(("slot", PLAYER, 0))
    c.click(("slot", ENEMY, 0))
    c.settle()
    c.click(("slot", PLAYER, 0))
    assert c.sel is None
    assert 0 not in c.attackers


def test_clicar_no_proprio_lider_nao_altera_o_duelo(content):
    c = ctrl_with(content, player_field={0: fc(3, 5)})
    c.click(("slot", PLAYER, 0))
    antes = snap(c)
    c.click(("leader", PLAYER))
    assert snap(c) == antes


# ---------------------------------------------------------------- cancelar e cliques invalidos
def test_cancelar_limpa_a_selecao_de_carta_e_de_gato(content):
    c = ctrl_with(content, player_hand=[mk(2, 2)], player_energy=3, player_field={0: fc(3, 5)},
                  enemy_field={0: fc(1, 5)})
    c.click(("hand", 0))
    c.cancel()
    assert c.sel is None and c.sel_targets == []
    c.click(("slot", PLAYER, 0))
    assert c.sel is not None
    c.cancel()
    assert c.sel is None and c.sel_targets == []


def test_clicar_no_vazio_cancela_a_selecao(content):
    c = ctrl_with(content, player_hand=[mk(2, 2)], player_energy=3)
    c.click(("hand", 0))
    c.click(None)
    assert c.sel is None
    c.click(("hand", 0))
    c.click(("none",))
    assert c.sel is None


def test_cliques_invalidos_nao_alteram_o_duelo_nem_levantam_excecao(content):
    c = ctrl_with(content, player_hand=[mk(2, 2, cost=5)], player_energy=1,
                  player_field={0: fc(3, 5, ready=False)}, enemy_field={0: fc(1, 5)})
    antes = snap(c)
    invalidos = [("slot", ENEMY, 0), ("slot", ENEMY, 4), ("leader", ENEMY), ("leader", PLAYER),
                 ("hand", 0), ("hand", 9), ("slot", PLAYER, 0), ("slot", PLAYER, 3),
                 ("again",), ("repeat",), ("xyz",), ("none",), None]
    for elem in invalidos:
        c.click(elem)
        assert snap(c) == antes, elem
    assert c.sel is None


def test_cliques_enquanto_o_inimigo_joga_sao_ignorados(content):
    c = ctrl_with(content, player_hand=[mk(2, 2)], player_energy=3)
    c.end_turn()                                          # passa: agora ha animacao / turno inimigo
    assert not c.can_act()
    antes = snap(c)
    c.click(("hand", 0))
    c.click(("slot", PLAYER, 1))
    assert snap(c) == antes
    assert c.sel is None


def test_soltar_em_destino_invalido_cancela_sem_alterar_o_duelo(content):
    c = ctrl_with(content, player_hand=[mk(2, 2)], player_energy=3, enemy_field={0: fc(1, 1)})
    assert c.drag_start(("hand", 0))
    antes = snap(c)
    c.drop(("slot", ENEMY, 0))
    assert snap(c) == antes
    assert c.sel is None


def test_arrastar_carta_para_slot_vazio_joga(content):
    c = ctrl_with(content, player_hand=[mk(2, 2, cost=1)], player_energy=3)
    assert c.drag_start(("hand", 0))
    c.drop(("slot", PLAYER, 4))
    assert p_side(c).field[4] is not None
    assert p_side(c).energy == 2


# ---------------------------------------------------------------- avisos e fim
def test_mao_cheia_gera_o_aviso_de_compra_pulada(content):
    mao = [mk(1, 1, cost=7) for _ in range(7)]            # hand_max = 7, nada jogavel
    c = ctrl_with(content, player_hand=mao, player_deck=[mk(1, 1) for _ in range(5)],
                  enemy_deck=[mk(1, 1) for _ in range(5)], player_energy=1)
    assert not c.has_other_moves()                        # so resta EndTurn: passa direto
    c.click(("pass",))
    assert run_until(c, lambda x: x.toast is not None and "Mão cheia" in x.toast.text)


def test_impasse_gera_banner_e_o_duelo_termina_com_resumo(content):
    c = ctrl_with(content, player_field={0: fc(3, 3), 1: fc(2, 1)},
                  enemy_field={0: fc(3, 3), 1: fc(1, 1)})
    c.click(("slot", PLAYER, 0))
    c.click(("slot", ENEMY, 0))
    c.settle()
    c.click(("slot", PLAYER, 1))
    c.click(("slot", ENEMY, 1))
    assert run_until(c, lambda x: x.banner is not None and "IMPASSE" in x.banner[0][0])
    assert run_until(c, lambda x: x.over)
    assert c.duel.winner in (PLAYER, ENEMY)
    linhas = c.summary()
    assert any("Impasse" in linha for linha in linhas)
    assert any(f"Seed: {c.seed}" in linha for linha in linhas)


def test_fim_do_duelo_produz_resumo_e_botoes_de_novo_e_repetir(content):
    c = ctrl_with(content, player_field={0: fc(5, 5)}, enemy_leader_hp=3)
    c.click(("slot", PLAYER, 0))
    c.click(("leader", ENEMY))
    assert run_until(c, lambda x: x.final_visible)
    assert c.duel.winner == PLAYER and c.shown.winner == PLAYER
    linhas = c.summary()
    assert len(linhas) >= 3 and all(isinstance(x, str) and x for x in linhas)
    assert any(linha.startswith("Turnos") for linha in linhas)
    assert not c.can_act()
    c.click(("slot", PLAYER, 0))                           # nada de jogar depois do fim
    assert c.over


def test_botao_repetir_reinicia_com_a_mesma_seed_e_jogar_de_novo_usa_outra(content):
    c = Controller(content, 5, ai_delay=0.0, seed_source=lambda: 77)
    c.phase = "over"
    c.over_t = 5.0
    c.click(("repeat",))
    assert c.seed == 5 and c.phase == "dice" and not c.over
    c.phase, c.over_t = "over", 5.0
    c.click(("again",))
    assert c.seed == 77 and not c.over


def test_repetir_a_seed_reproduz_o_mesmo_duelo_inicial(content):
    a = Controller(content, 11)
    b = Controller(content, 11)
    assert view(a.duel, PLAYER) == view(b.duel, PLAYER)
    a.new_game(12)
    a.repeat()
    assert a.seed == 12
    assert view(a.duel, PLAYER) == view(Controller(content, 12).duel, PLAYER)


# ---------------------------------------------------------------- propriedade: duelos por cliques
def random_click(c: Controller, rng: Random) -> tuple | None:
    n_hand = len(c.shown.me.hand)
    r = rng.random()
    if r < 0.10:
        return ("pass",)
    if r < 0.32 and n_hand:
        return ("hand", rng.randrange(n_hand))
    if r < 0.40:
        return ("hand", rng.randrange(0, 12))             # inclui indices fora da mao
    if r < 0.60:
        return ("slot", PLAYER, rng.randrange(5))
    if r < 0.80:
        return ("slot", ENEMY, rng.randrange(5))
    if r < 0.88:
        return ("leader", rng.choice([PLAYER, ENEMY]))
    if r < 0.94:
        return rng.choice([None, ("none",), ("again",), ("repeat",)])
    return ("slot", PLAYER, rng.randrange(5))


def check_consistent(c: Controller) -> None:
    d = c.duel
    rules = c.content.rules["duel"]
    for side in (PLAYER, ENEMY):
        st = d.sides[side]
        assert len(st.field) == rules["slots"]
        assert len(st.hand) <= rules["hand_max"]
        assert 0 <= st.energy <= rules["energy_cap"]
    if c.can_act():
        assert c.shown == view(d, PLAYER)                  # tela == core quando parado
        assert c.sel is None or c.sel_targets == [] or set(c.sel_targets) <= {
            t for n in c.attackers for t in attack_targets(d, n)}
        assert set(c.playable) == {a.hand_index for a in legal_actions(d) if isinstance(a, PlayCat)}
        assert c.attackers == {a.attacker_slot for a in legal_actions(d) if isinstance(a, Attack)}
    if c.sel and c.sel[0] == "slot":
        assert set(c.sel_targets) == set(attack_targets(d, c.sel[1]))


@pytest.mark.parametrize("seed", range(1, 51))
def test_duelo_so_por_cliques_aleatorios_termina_consistente(content, seed):
    c = Controller(content, seed, ai_delay=0.0)
    rng = Random(seed * 7919)
    guard = 0
    while not c.over and guard < 4000:
        guard += 1
        c.settle()
        if c.over:
            break
        before = snap(c)
        elem = random_click(c, rng)
        c.click(elem)
        if elem is not None and elem[0] in ("again", "repeat", "none"):
            assert snap(c) == before
        check_consistent(c)
        if guard % 25 == 0 and c.can_act():                # garante progresso do duelo
            c.end_turn()
    c.settle()
    assert c.over, f"duelo da seed {seed} nao terminou"
    assert c.duel.winner in (PLAYER, ENEMY)
    assert c.summary()


# ---------------------------------------------------------------- fumaca: cenas de screenshot
@pytest.mark.parametrize("cena", ["inicio", "selecionado", "ataque", "final", "confirmar"])
def test_cenas_de_screenshot_renderizam_e_geram_png_nao_vazio(cena, tmp_path, monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("SDL_AUDIODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    from ui.__main__ import main
    out = tmp_path / f"{cena}.png"
    assert main(["--seed", "1", "--screenshot", str(out), "--cena", cena]) == 0
    data = out.read_bytes()
    assert len(data) > 1000
    assert data[:8] == b"\x89PNG\r\n\x1a\n"


def test_cena_de_screenshot_nao_e_uma_imagem_de_uma_cor_so(tmp_path, monkeypatch):
    monkeypatch.setenv("SDL_VIDEODRIVER", "dummy")
    monkeypatch.setenv("PYGAME_HIDE_SUPPORT_PROMPT", "1")
    import pygame
    from ui.__main__ import main
    out = tmp_path / "inicio.png"
    main(["--seed", "2", "--screenshot", str(out), "--cena", "inicio"])
    img = pygame.image.load(str(out))
    cores = {tuple(img.get_at((x, y)))[:3] for x in range(0, img.get_width(), 17)
             for y in range(0, img.get_height(), 17)}
    assert len(cores) > 3


# ---------------------------------------------------------------- confirmar "Passar turno"
def com_jogada(content, **kw) -> Controller:
    """Turno do jogador com uma carta jogavel na mao (legal_actions tem algo alem de EndTurn)."""
    c = ctrl_with(content, player_hand=[mk(2, 2, cost=1)], player_energy=3, **kw)
    assert any(isinstance(a, PlayCat) for a in legal_actions(c.duel))
    return c


def so_passar(content) -> Controller:
    c = ctrl_with(content)
    assert all(type(a).__name__ == "EndTurn" for a in legal_actions(c.duel))
    return c


def test_passar_turno_com_jogadas_abre_confirmacao_e_nao_passa(content):
    c = com_jogada(content)
    antes = snap(c)
    c.click(("pass",))
    assert c.confirming is True
    assert c.has_other_moves()
    assert snap(c) == antes
    assert c.duel.turn_side == PLAYER
    assert "Passar mesmo assim" in c.hint()


def test_passar_turno_sem_outras_jogadas_passa_direto(content):
    c = so_passar(content)
    assert c.has_other_moves() is False
    c.click(("pass",))
    assert c.confirming is False
    assert c.duel.turn_side == ENEMY


def test_request_end_turn_sem_outras_jogadas_passa_direto(content):
    c = so_passar(content)
    c.request_end_turn()
    assert c.duel.turn_side == ENEMY


def test_pass_yes_na_confirmacao_passa_o_turno(content):
    c = com_jogada(content)
    c.click(("pass",))
    c.click(("pass_yes",))
    assert c.duel.turn_side == ENEMY
    assert c.confirming is False


def test_request_end_turn_duas_vezes_passa_o_turno(content):
    c = com_jogada(content)
    c.request_end_turn()
    assert c.confirming and c.duel.turn_side == PLAYER
    c.request_end_turn()
    assert c.duel.turn_side == ENEMY and not c.confirming


def test_confirm_end_turn_sem_confirmacao_aberta_nao_faz_nada(content):
    c = com_jogada(content)
    antes = snap(c)
    c.confirm_end_turn()
    assert snap(c) == antes


@pytest.mark.parametrize("como", ["pass_no", "cancel_confirm", "cancel", "mao", "slot_vazio",
                                  "none", "None", "lider_inimigo"])
def test_cancelar_a_confirmacao_nao_passa_o_turno(content, como):
    c = com_jogada(content, enemy_field={0: fc(1, 1)})
    c.click(("pass",))
    assert c.confirming
    antes = snap(c)
    acoes = {
        "pass_no": lambda: c.click(("pass_no",)),
        "cancel_confirm": c.cancel_confirm,
        "cancel": c.cancel,
        "mao": lambda: c.click(("hand", 0)),
        "slot_vazio": lambda: c.click(("slot", PLAYER, 2)),
        "none": lambda: c.click(("none",)),
        "None": lambda: c.click(None),
        "lider_inimigo": lambda: c.click(("leader", ENEMY)),
    }
    acoes[como]()
    assert c.confirming is False
    assert snap(c) == antes                               # o clique foi consumido
    assert c.sel is None
    assert c.duel.turn_side == PLAYER


def test_clique_em_outro_elemento_cancela_e_so_o_proximo_clique_seleciona(content):
    c = com_jogada(content)
    c.click(("pass",))
    c.click(("hand", 0))
    assert c.confirming is False and c.sel is None
    c.click(("hand", 0))
    assert c.sel == ("hand", 0)


def test_acao_que_muda_o_estado_cancela_a_confirmacao(content):
    c = com_jogada(content)
    c.click(("pass",))
    assert c.confirming
    assert c._do(PlayCat(0, 1))
    assert c.confirming is False
    assert p_side(c).field[1] is not None


def test_refresh_cancela_a_confirmacao(content):
    c = com_jogada(content)
    c.request_end_turn()
    c.refresh()
    assert c.confirming is False


def test_confirmacao_cancelada_pode_ser_reaberta(content):
    c = com_jogada(content)
    c.click(("pass",))
    c.click(("pass_no",))
    c.click(("pass",))
    assert c.confirming


def test_arrastar_fica_desligado_durante_a_confirmacao(content):
    c = ctrl_with(content, player_hand=[mk(2, 2, cost=1)], player_energy=3,
                  player_field={0: fc(3, 5)}, enemy_field={0: fc(1, 5)})
    assert c.draggable(("hand", 0)) and c.draggable(("slot", PLAYER, 0))
    c.click(("pass",))
    assert c.confirming
    assert not c.draggable(("hand", 0))
    assert not c.draggable(("slot", PLAYER, 0))
    assert c.drag_start(("hand", 0)) is False
    assert c.drag_start(("slot", PLAYER, 0)) is False
    assert c.sel is None
    c.cancel_confirm()
    assert c.draggable(("hand", 0))


def test_end_turn_direto_continua_passando_sem_confirmacao(content):
    c = com_jogada(content)
    c.end_turn()
    assert c.confirming is False
    assert c.duel.turn_side == ENEMY


def test_confirmacao_nao_abre_fora_do_turno_do_jogador(content):
    c = com_jogada(content)
    c.end_turn()
    assert not c.can_act()
    c.request_end_turn()
    assert c.confirming is False


def test_selecao_e_descartada_ao_abrir_a_confirmacao(content):
    c = com_jogada(content)
    c.click(("hand", 0))
    assert c.sel == ("hand", 0)
    c.click(("pass",))
    assert c.confirming and c.sel is None
