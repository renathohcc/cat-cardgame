"""Controller do duelo e prévia na UI, fase P1 (T12.5, a partir de T12.2 e T12.3).

Cobre: duração do beat de ataque x investida, pausa no impacto, tremor, velocidade do inimigo,
clique acelerando o turno inimigo, entrada do chefe, cache da prévia e um soak de duelos completos
desenhando `draw_frame` a cada quadro. Sem janela (SDL dummy); RNG sempre por seed.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

from random import Random

import pygame
import pytest

from core.ai import choose_action
from core.duel import card_from_effect, card_from_special, view
from core.types import Attack, EndTurn, PlayEffect
from duel_helpers import duel, fc, load, mk
from ui import layout as L, preview
from ui.controller import Controller
from ui.timing import Timing

PLAYER, ENEMY = "player", "enemy"
BOSS = "madame-fifi-pelucia"
INIMIGOS = ["tonho-sem-sorte", "irmaos-pimenta", "berenice-da-matilha", BOSS]


@pytest.fixture(scope="module")
def content():
    return load()


def ctrl_with(content, timing: Timing | None = None, seed: int = 1, **kw) -> Controller:
    """Controlador sobre um duelo montado: vez do jogador, tudo parado, pronto para agir."""
    c = Controller(content, seed, ai_delay=0.0, timing=timing)
    kw.setdefault("player_deck", [mk(1, 1), mk(1, 1)])          # evita Impasse por mesa vazia
    kw.setdefault("enemy_deck", [mk(1, 1), mk(1, 1)])
    c.duel = duel(content, **kw)
    c.phase = "play"
    c.beats.clear()
    c.cur = None
    c.fx = []
    c.toast = None
    c.banner = None
    c.intro_t = None
    c.refresh()
    return c


def attack(c: Controller, slot: int, target: tuple) -> None:
    c.click(("slot", PLAYER, slot))
    c.click(("slot", ENEMY, target[1]) if target[0] == "slot" else ("leader", ENEMY))


def until(c: Controller, pred, dt: float = 0.01, limit: int = 3000) -> bool:
    for _ in range(limit):
        if pred(c):
            return True
        c.update(dt)
    return pred(c)


def tempo(**blocos) -> Timing:
    return Timing(blocos)


# ------------------------------------------------------------------ investida x beat de ataque
@pytest.mark.parametrize("lunge_dur, beat, esperado", [
    (0.2, 0.34, 0.2 * 0.55),       # a investida bate antes do beat acabar: o beat acaba no impacto
    (1.0, 0.34, 0.34),             # beat curto manda
    (1.0, 0.05, 0.05),
    (0.4, 9.0, 0.4 * 0.55),
])
def test_beat_de_ataque_respeita_a_duracao_da_investida(content, lunge_dur, beat, esperado):
    tm = tempo(lunge={"duration": lunge_dur}, beats={"Attacked": beat})
    c = ctrl_with(content, tm, player_field={0: fc(2, 5)}, enemy_field={0: fc(1, 6)})
    attack(c, 0, ("slot", 0))
    primeiro = c.beats[0]
    assert type(primeiro.events[0]).__name__ == "Attacked"
    assert primeiro.duration == pytest.approx(esperado)


def test_a_investida_e_criada_como_efeito_do_ataque(content):
    c = ctrl_with(content, tempo(lunge={"duration": 0.6}), player_field={0: fc(2, 5)}, enemy_field={0: fc(1, 6)})
    attack(c, 0, ("slot", 0))
    c.update(0.0)
    investidas = [f for f in c.fx if f.kind == "lunge"]
    assert len(investidas) == 1 and investidas[0].life >= 0.6


# ------------------------------------------------------------------ pausa no impacto e tremor
HS = {"normal": 0.11, "lethal": 0.33, "leader": 0.22}
SK = {"leader_hit": {"amplitude": 2, "duration": 0.4}, "lethal": {"amplitude": 7, "duration": 0.6}}


def primeiro_impacto(c: Controller):
    assert until(c, lambda x: x.hitstop_t > 0), "nenhuma pausa no impacto"
    return c.hitstop_t, c.shake


def test_hitstop_normal_em_golpe_comum_sem_tremor(content):
    c = ctrl_with(content, tempo(hitstop=HS, shake=SK), player_field={0: fc(2, 5)}, enemy_field={0: fc(1, 6)})
    attack(c, 0, ("slot", 0))
    hs, shake = primeiro_impacto(c)
    assert hs == pytest.approx(0.11) and shake is None


def test_hitstop_letal_quando_morre_um_gato(content):
    c = ctrl_with(content, tempo(hitstop=HS, shake=SK), player_field={0: fc(5, 5)}, enemy_field={0: fc(1, 2)})
    attack(c, 0, ("slot", 0))
    hs, shake = primeiro_impacto(c)
    assert hs == pytest.approx(0.33) and shake == (7, 0.6)


def test_hitstop_do_lider_em_golpe_que_nao_mata(content):
    c = ctrl_with(content, tempo(hitstop=HS, shake=SK), player_field={0: fc(3, 5)}, enemy_leader_hp=20)
    attack(c, 0, ("leader",))
    hs, shake = primeiro_impacto(c)
    assert hs == pytest.approx(0.22) and shake == (2, 0.4)


def test_hitstop_letal_quando_o_lider_chega_a_zero(content):
    c = ctrl_with(content, tempo(hitstop=HS, shake=SK), player_field={0: fc(5, 5)}, enemy_leader_hp=3)
    attack(c, 0, ("leader",))
    hs, shake = primeiro_impacto(c)
    assert hs == pytest.approx(0.33) and shake == (7, 0.6)


def test_pausa_no_impacto_congela_beat_e_efeitos_e_skip_zera(content):
    c = ctrl_with(content, tempo(hitstop=HS, shake=SK), player_field={0: fc(2, 5)}, enemy_field={0: fc(1, 6)})
    attack(c, 0, ("slot", 0))
    hs, _ = primeiro_impacto(c)
    beat_t, idades = c.beat_t, [f.age for f in c.fx]
    c.update(hs / 2)
    assert c.hitstop_t == pytest.approx(hs / 2)
    assert c.beat_t == beat_t and [f.age for f in c.fx] == idades
    c.skip()
    assert c.hitstop_t == 0.0


def test_depois_da_pausa_o_tempo_volta_a_correr(content):
    c = ctrl_with(content, tempo(hitstop=HS), player_field={0: fc(2, 5)}, enemy_field={0: fc(1, 6)})
    attack(c, 0, ("slot", 0))
    hs, _ = primeiro_impacto(c)
    beat_t = c.beat_t
    c.update(hs + 0.05)
    assert c.hitstop_t == 0 and c.beat_t == pytest.approx(beat_t + 0.05)


def test_tremor_decai_e_termina(content):
    c = ctrl_with(content, tempo(shake=SK), player_field={0: fc(5, 5)}, enemy_leader_hp=3)
    attack(c, 0, ("leader",))
    primeiro_impacto(c)
    assert until(c, lambda x: x.shake_age >= 0.6)
    assert c.shake_offset() == (0, 0)


# ------------------------------------------------------------------ pular o jogo inteiro com e sem tremor
def play_out(content, eid: str, seed: int, speed: str = "1x", shake: bool = True, draw: bool = False,
             dt: float = 1 / 30) -> dict:
    """Duelo completo: jogador pela IA do core (seed própria), animações rodando. Devolve o resumo."""
    from ui.render import UIState, draw_frame
    c = Controller(content, seed, ai_delay=0.1, enemy_id=eid)
    c.enemy_speed = speed
    c.speed = 6.0
    ui = UIState(screen_shake=shake)
    ui.enemy_speed = speed
    canvas = pygame.Surface((960, 540)) if draw else None
    rng = Random(seed + 77)
    frames = enemy_frames = 0
    shaken = False
    while c.phase != "over" and frames < 40000:
        if c.intro or c.phase == "dice":
            c.skip()
        if c.can_act():
            c._do(choose_action(c.duel, PLAYER, rng))
        enemy_frames += c.shown.turn_side == ENEMY
        shaken |= c.shake_offset() != (0, 0)
        c.update(dt)
        ui.t += dt
        frames += 1
        if draw:
            draw_frame(canvas, c, ui)
    d = c.duel
    v = view(d, PLAYER)
    return {"winner": d.winner, "hp": (v.me.leader_hp, v.opponent.leader_hp), "frames": frames,
            "enemy_frames": enemy_frames, "over": c.phase == "over", "shaken": shaken, "turns": v.me.turns_taken}


@pytest.mark.parametrize("eid, seed", [("tonho-sem-sorte", 1), (BOSS, 2)])
def test_tremor_desligado_nao_muda_o_resultado_do_duelo(content, eid, seed):
    pygame.init()
    ligado = play_out(content, eid, seed, shake=True, draw=True, dt=1 / 12)
    desligado = play_out(content, eid, seed, shake=False, draw=True, dt=1 / 12)
    assert ligado["over"] and desligado["over"]
    assert (ligado["winner"], ligado["hp"], ligado["turns"]) == (desligado["winner"], desligado["hp"], desligado["turns"])


def test_tremor_desligado_desenha_o_quadro_sem_deslocamento(content):
    from ui.render import UIState, draw_frame
    pygame.init()
    c = ctrl_with(content, tempo(shake={"leader_hit": {"amplitude": 6, "duration": 1.0},
                                        "lethal": {"amplitude": 6, "duration": 1.0}}),
                  player_field={0: fc(5, 5)}, enemy_leader_hp=3)
    attack(c, 0, ("leader",))
    primeiro_impacto(c)
    c.update(0.11)
    c.update(0.03)
    assert c.shake_offset() != (0, 0), "cenário deveria ter tremor ativo"
    a, b, ref = (pygame.Surface((960, 540)) for _ in range(3))
    draw_frame(a, c, UIState(t=1.0, screen_shake=True))
    draw_frame(b, c, UIState(t=1.0, screen_shake=False))
    c.shake = None
    draw_frame(ref, c, UIState(t=1.0, screen_shake=True))
    assert pygame.image.tobytes(b, "RGB") == pygame.image.tobytes(ref, "RGB")
    assert pygame.image.tobytes(a, "RGB") != pygame.image.tobytes(b, "RGB")


# ------------------------------------------------------------------ velocidade do inimigo
def test_velocidade_padrao_vem_do_json(content):
    c = Controller(content, 1)
    assert c.enemy_speed == c.timing.enemy_speed.default == "1x"


@pytest.mark.parametrize("chave, fator", [("1x", 1.0), ("2x", 2.0), ("rapido", 5.0)])
def test_velocidade_escala_so_o_turno_do_inimigo(content, chave, fator):
    c = ctrl_with(content)
    c.enemy_speed = chave
    assert c.shown.turn_side == PLAYER and c.enemy_time_scale() == 1.0
    c.duel.turn_side = ENEMY
    c.refresh()
    c.shown = view(c.duel, PLAYER)
    assert c.enemy_time_scale() == pytest.approx(fator)


def test_velocidade_desconhecida_equivale_a_1x(content):
    c = ctrl_with(content)
    c.duel.turn_side = ENEMY
    c.shown = view(c.duel, PLAYER)
    c.phase = "play"
    c.enemy_speed = "turbo"
    assert c.enemy_time_scale() == 1.0


def test_velocidade_vem_de_ui_timing_injetado(content):
    tm = tempo(enemy_speed={"options": {"lento": 2.0, "normal": 1.0}, "default": "normal"})
    c = Controller(content, 1, timing=tm)
    assert c.enemy_speed == "normal"
    c.phase = "play"
    c.enemy_speed = "lento"
    c.duel.turn_side = ENEMY
    c.shown = view(c.duel, PLAYER)
    assert c.enemy_time_scale() == pytest.approx(0.5)


def test_beats_do_jogador_duram_o_mesmo_em_qualquer_velocidade(content):
    contagens = []
    for chave in ("1x", "2x", "rapido"):
        c = ctrl_with(content, player_field={0: fc(2, 5), 1: fc(2, 5)}, enemy_field={0: fc(1, 6)})
        c.enemy_speed = chave
        attack(c, 0, ("slot", 0))
        n = 0
        while not c.can_act() and n < 5000:
            c.update(1 / 60)
            n += 1
        contagens.append(n)
    assert contagens[0] == contagens[1] == contagens[2] > 0


@pytest.mark.parametrize("eid, seed", [("berenice-da-matilha", 4), (BOSS, 5)])
def test_resultado_do_duelo_identico_em_1x_2x_e_rapido(content, eid, seed):
    r = {k: play_out(content, eid, seed, speed=k) for k in ("1x", "2x", "rapido")}
    assert all(x["over"] for x in r.values())
    base = (r["1x"]["winner"], r["1x"]["hp"], r["1x"]["turns"])
    assert (r["2x"]["winner"], r["2x"]["hp"], r["2x"]["turns"]) == base
    assert (r["rapido"]["winner"], r["rapido"]["hp"], r["rapido"]["turns"]) == base
    assert r["1x"]["enemy_frames"] > r["2x"]["enemy_frames"] > r["rapido"]["enemy_frames"]


def test_clique_durante_a_espera_da_ia_acelera_o_turno_inimigo(content):
    c = Controller(content, 1, ai_delay=5.0)
    c.duel = duel(content, turn_side=ENEMY, player_field={0: fc(1, 5)}, enemy_field={0: fc(2, 5)},
                  player_deck=[mk(1, 1)], enemy_deck=[mk(1, 1)])
    c.phase, c.intro_t = "play", None
    c.beats.clear(); c.cur = None
    c.shown = view(c.duel, PLAYER)
    c.update(0.1)
    assert not c.beats and c.cur is None                     # a IA ainda espera
    c.click(None)
    assert c.toast is None                                   # não mostra mais "Aguarde"
    c.update(0.0)
    assert c.beats or c.cur is not None                      # a IA jogou na hora


def test_clique_durante_um_beat_do_inimigo_termina_o_beat_atual(content):
    c = ctrl_with(content, player_field={0: fc(1, 20)}, enemy_field={0: fc(2, 5)})
    c.end_turn()
    assert until(c, lambda x: x.shown.turn_side == ENEMY and x.cur is not None)
    velho = c.cur
    velho.duration = 50.0
    c.beat_t = 0.0
    c.click(None)
    assert c.toast is None and c.hitstop_t == 0.0
    c.update(0.0)
    assert c.cur is not velho                     # o beat de 50 s acabou na hora


def test_clique_no_turno_do_jogador_parado_nao_chama_skip(content):
    c = ctrl_with(content, player_hand=[mk(2, 2)], player_energy=3)
    c.click(None)
    assert c.can_act() and c.toast is None


# ------------------------------------------------------------------ entrada do chefe
def boss_ctrl(content, duracao: float | None = None) -> Controller:
    tm = tempo(boss_intro={"duration": duracao}) if duracao else None
    return Controller(content, 3, enemy_id=BOSS, timing=tm)


def test_entrada_do_chefe_so_existe_contra_chefe(content):
    assert boss_ctrl(content).intro is True
    assert Controller(content, 3, enemy_id="tonho-sem-sorte").intro is False
    assert Controller(content, 3).intro is False


@pytest.mark.parametrize("duracao", [1.0, 3.0])
def test_entrada_do_chefe_dura_boss_intro_duration(content, duracao):
    c = boss_ctrl(content, duracao)
    assert c.intro_time() == duracao
    t = 0.0                                                # a entrada nasce no início (intro_t = 0)
    while c.intro and t < 10:
        c.update(0.05)
        t += 0.05
    assert t == pytest.approx(duracao, abs=0.06)
    assert c.phase == "dice"                               # depois da entrada vem o dado


def test_entrada_do_chefe_nao_acaba_no_primeiro_quadro(content):
    c = boss_ctrl(content, 2.4)
    c.update(0.1)
    assert c.intro


def test_entrada_do_chefe_e_pulavel_por_clique(content):
    c = boss_ctrl(content)
    c.intro_t = 0.2
    c.click(None)
    assert not c.intro and c.phase == "dice"


def test_entrada_do_chefe_e_pulavel_por_skip_espaco(content):
    c = boss_ctrl(content)
    c.intro_t = 0.2
    c.space_key()
    assert not c.intro


def test_entrada_do_chefe_pulada_nao_pula_o_dado(content):
    c = boss_ctrl(content)
    c.intro_t = 0.2
    c.skip()
    assert c.phase == "dice"
    c.skip()
    assert c.phase == "play"


def test_entrada_do_chefe_nao_roda_a_ia_nem_o_relogio_do_dado(content):
    c = boss_ctrl(content, 3.0)
    c.intro_t = 0.0
    c.update(1.0)
    assert c.intro and c.dice_t == 0.0 and not c.beats


# ------------------------------------------------------------------ prévia na UI (cache, alvos, caveira)
def centro(side: str, n: int) -> tuple[int, int]:
    return L.slot_rect(side, n).center


@pytest.fixture
def conta_previas(monkeypatch):
    chamadas = {"attack": 0, "card": 0}
    real_a, real_c = preview.preview_attack, preview.preview_card

    def a(*x, **k):
        chamadas["attack"] += 1
        return real_a(*x, **k)

    def cc(*x, **k):
        chamadas["card"] += 1
        return real_c(*x, **k)

    monkeypatch.setattr(preview, "preview_attack", a)
    monkeypatch.setattr(preview, "preview_card", cc)
    return chamadas


def test_previa_sem_selecao_nao_existe(content):
    c = ctrl_with(content, player_field={0: fc(3, 5)}, enemy_field={0: fc(1, 4)})
    assert preview.hovered(c, centro(ENEMY, 0)) is None
    assert preview.current(c, centro(ENEMY, 0)) is None


def test_previa_mostra_dano_dos_dois_lados(content):
    c = ctrl_with(content, player_field={0: fc(3, 5)}, enemy_field={0: fc(2, 4)})
    c.click(("slot", PLAYER, 0))
    pv = preview.current(c, centro(ENEMY, 0))
    assert pv.cat(ENEMY, 0).damage == 3 and pv.cat(PLAYER, 0).damage == 2


def test_previa_cache_so_recalcula_quando_o_alvo_muda(content, conta_previas):
    c = ctrl_with(content, player_field={0: fc(3, 5)}, enemy_field={0: fc(1, 4), 1: fc(1, 4)})
    c.click(("slot", PLAYER, 0))
    p1 = preview.current(c, centro(ENEMY, 0))
    assert preview.current(c, (centro(ENEMY, 0)[0] + 2, centro(ENEMY, 0)[1] + 2)) is p1
    for _ in range(5):
        preview.current(c, centro(ENEMY, 0))
    assert conta_previas["attack"] == 1
    p2 = preview.current(c, centro(ENEMY, 1))
    assert p2 is not p1 and conta_previas["attack"] == 2


def test_previa_invalida_quando_o_estado_muda(content, conta_previas):
    c = ctrl_with(content, player_field={0: fc(3, 5), 1: fc(2, 5)}, enemy_field={0: fc(1, 4)})
    c.click(("slot", PLAYER, 0))
    antes = preview.current(c, centro(ENEMY, 0))
    assert antes.cat(ENEMY, 0).hp_after == 1 and not antes.cat(ENEMY, 0).dies
    c.cancel()
    attack(c, 1, ("slot", 0))                                # o outro gato fere o mesmo alvo (4 -> 2)
    assert until(c, lambda x: x.can_act())
    c.click(("slot", PLAYER, 0))
    depois = preview.current(c, centro(ENEMY, 0))
    assert depois is not antes and depois.cat(ENEMY, 0).dies
    assert conta_previas["attack"] == 2


def test_previa_troca_com_a_selecao_no_mesmo_alvo(content, conta_previas):
    c = ctrl_with(content, player_field={0: fc(3, 5), 1: fc(1, 5)}, enemy_field={0: fc(1, 4)})
    c.click(("slot", PLAYER, 0))
    p0 = preview.current(c, centro(ENEMY, 0))
    c.cancel()
    c.click(("slot", PLAYER, 1))
    p1 = preview.current(c, centro(ENEMY, 0))
    assert p0.cat(ENEMY, 0).damage == 3 and p1.cat(ENEMY, 0).damage == 1


def test_previa_some_ao_cancelar_ou_sair_do_alvo(content):
    c = ctrl_with(content, player_field={0: fc(3, 5)}, enemy_field={0: fc(1, 4)})
    c.click(("slot", PLAYER, 0))
    assert preview.current(c, centro(ENEMY, 0)) is not None
    assert preview.current(c, (5, 5)) is None
    c.cancel()
    assert preview.current(c, centro(ENEMY, 0)) is None


def test_alvos_invalidos_com_provocar_nao_geram_previa(content):
    c = ctrl_with(content, player_field={0: fc(3, 5)},
                  enemy_field={0: fc(1, 4, kw=("provocar",)), 1: fc(1, 4)})
    c.click(("slot", PLAYER, 0))
    assert preview.hovered(c, centro(ENEMY, 1)) is None
    assert preview.hovered(c, L.leader_rect(ENEMY).center) is None
    assert preview.current(c, centro(ENEMY, 1)) is None
    assert preview.current(c, L.leader_rect(ENEMY).center) is None
    assert preview.hovered(c, centro(ENEMY, 0)) == (ENEMY, ("slot", 0))
    assert c.target_blocked(ENEMY, 1) == "taunt" and c.leader_blocked(ENEMY)
    assert c.target_blocked(ENEMY, 0) is None


def test_previa_no_lider_sem_provocar(content):
    c = ctrl_with(content, player_field={0: fc(3, 5)}, enemy_leader_hp=10)
    c.click(("slot", PLAYER, 0))
    pv = preview.current(c, L.leader_rect(ENEMY).center)
    assert pv.leader(ENEMY).hp_after == 7 and pv.cats == ()


def test_previa_nao_aparece_fora_da_vez_nem_com_confirmacao(content):
    c = ctrl_with(content, player_hand=[mk(1, 1)], player_energy=3,
                  player_field={0: fc(3, 5)}, enemy_field={0: fc(1, 4)})
    c.click(("slot", PLAYER, 0))
    c.confirming = True
    assert preview.current(c, centro(ENEMY, 0)) is None
    c.confirming = False
    c.phase = "dice"
    assert preview.current(c, centro(ENEMY, 0)) is None


def test_previa_de_efeito_e_de_espirito(content):
    c = ctrl_with(content, player_hand=[card_from_effect(content, "arranhao-certeiro"),
                                        card_from_special(content, "trovao-amarelo")],
                  player_energy=7, enemy_field={0: fc(1, 5)})
    c.click(("hand", 0))
    assert preview.current(c, centro(ENEMY, 0)).cat(ENEMY, 0).damage == 3
    c.cancel()
    c.click(("hand", 1))
    c.click(("slot", PLAYER, 2))
    assert c.sel and c.sel[0] == "enter"
    assert preview.current(c, centro(ENEMY, 0)).cat(ENEMY, 0).damage == 2


def test_caveira_quando_o_alvo_morre(content):
    c = ctrl_with(content, player_field={0: fc(4, 5)}, enemy_field={0: fc(1, 4), 1: fc(1, 9)})
    c.click(("slot", PLAYER, 0))
    assert preview.current(c, centro(ENEMY, 0)).cat(ENEMY, 0).dies is True
    assert preview.current(c, centro(ENEMY, 1)).cat(ENEMY, 1).dies is False


def test_desenho_da_previa_altera_o_quadro_e_nao_o_duelo(content):
    from ui.render import UIState, draw_frame
    pygame.init()
    c = ctrl_with(content, player_field={0: fc(4, 5)}, enemy_field={0: fc(1, 4)})
    c.click(("slot", PLAYER, 0))
    before = (view(c.duel, PLAYER).me.leader_hp, len(c.duel.log), c.duel.rng.getstate())
    a, b = pygame.Surface((960, 540)), pygame.Surface((960, 540))
    draw_frame(a, c, UIState(t=1.0, mouse=(5, 5)))
    draw_frame(b, c, UIState(t=1.0, mouse=centro(ENEMY, 0)))
    assert pygame.image.tobytes(a, "RGB") != pygame.image.tobytes(b, "RGB")
    assert (view(c.duel, PLAYER).me.leader_hp, len(c.duel.log), c.duel.rng.getstate()) == before


def test_botao_passar_pisca_so_quando_nao_ha_mais_jogada(content):
    c = ctrl_with(content, player_field={0: fc(3, 5)}, enemy_field={0: fc(1, 4)})
    assert c.pass_only is False
    c.duel.sides[PLAYER].field[0].ready = False
    c.refresh()
    assert c.pass_only is True


# ------------------------------------------------------------------ soak: duelos completos desenhando
@pytest.mark.parametrize("eid", INIMIGOS)
def test_soak_duelo_completo_desenhando_cada_quadro(content, eid):
    pygame.init()
    r = play_out(content, eid, seed=11, draw=True, dt=1 / 12)
    assert r["over"] and r["winner"] in (PLAYER, ENEMY)


def test_soak_duelo_com_velocidade_rapida_desenhando(content):
    pygame.init()
    assert play_out(content, "irmaos-pimenta", 21, speed="rapido", draw=True, dt=1 / 12)["over"]
