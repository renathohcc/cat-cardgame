"""Impasse por estagnacao (decisao do Renatho, 2026-10-27).

Regra: uma janela de `rules.deadlock.stall_rounds` (5) rodadas completas seguidas sem gato/Espirito
jogado, sem gato morto e sem Lider terminar abaixo do HP-base da janela dispara o impasse dos
Lideres (evento Deadlock). Jogar gato ou morrer gato reinicia; cura que compensa conta como sem
perda liquida; sem o campo `stall_rounds`, a estagnacao fica desligada. Sem limite de turnos.
Escrito a partir da regra, so com a API publica.
"""
from __future__ import annotations

from random import Random

import pytest

from core.ai import choose_action
from core.duel import (apply_action, card_from_effect, is_over, legal_actions,
                       new_duel_vs_enemy)
from core.types import (Attack, Deadlock, DuelEnded, EndTurn, IllegalAction, PlayCat,
                        PlayEffect)
from duel_helpers import deck_spec, duel, fc, load, mk

RODADA = 2          # fins de turno por rodada completa
N = 5               # rules.deadlock.stall_rounds
BANHO = {"id": "banho-de-espuma", "gatilho": "inicio_turno_proprio",
         "acao": {"tipo": "cura", "alvo": "lider_proprio", "valor": 1}}


@pytest.fixture(scope="module")
def content():
    return load()


def parado(content, **kw):
    """Cada lado com um gato resistente em campo que nunca ataca (nao ha impasse pela regra antiga)."""
    kw.setdefault("player_field", {0: fc(1, 50)})
    kw.setdefault("enemy_field", {0: fc(1, 50)})
    kw.setdefault("player_leader_hp", 20)
    kw.setdefault("enemy_leader_hp", 20)
    return duel(content, **kw)


def passar(d, maximo):
    """EndTurn ate Deadlock ou `maximo` turnos. Devolve (eventos, turnos_usados)."""
    ev = []
    for i in range(1, maximo + 1):
        ev += apply_action(d, EndTurn())
        if any(isinstance(e, Deadlock) for e in ev):
            return ev, i
    return ev, maximo


def deadlock_em(ev):
    return any(isinstance(e, Deadlock) for e in ev)


def jogada(d, tipo):
    return next(a for a in legal_actions(d) if isinstance(a, tipo))


# ---------------- disparo ----------------

def test_estagnacao_dispara_apos_5_rodadas_completas(content):
    d = parado(content)
    ev, n = passar(d, 40)
    assert deadlock_em(ev)
    # 5 rodadas = 10 fins de turno; a janela comeca a contar no 1o fim de turno (+1 no maximo)
    assert N * RODADA <= n <= N * RODADA + 1
    assert is_over(d) in ("player", "enemy")


def test_estagnacao_nao_dispara_com_4_rodadas(content):
    d = parado(content)
    ev, _ = passar(d, (N - 1) * RODADA)
    assert not deadlock_em(ev)
    assert is_over(d) is None


def test_estagnacao_respeita_stall_rounds_configurado(content, monkeypatch):
    monkeypatch.setitem(content.rules["deadlock"], "stall_rounds", 2)
    d = parado(content)
    ev, n = passar(d, 40)
    assert deadlock_em(ev)
    assert 2 * RODADA <= n <= 2 * RODADA + 1


def test_depois_do_impasse_ha_vencedor_e_o_duelo_termina(content):
    d = parado(content)
    ev, _ = passar(d, 40)
    assert any(isinstance(e, DuelEnded) for e in ev)
    assert is_over(d) in ("player", "enemy")
    assert legal_actions(d) == []
    with pytest.raises(IllegalAction):
        apply_action(d, EndTurn())


# ---------------- reinicio ----------------

def test_jogar_gato_reinicia_a_contagem(content):
    d = parado(content, player_hand=[mk(1, 5)])
    ev, _ = passar(d, 8)                       # 4 rodadas
    assert not deadlock_em(ev)
    apply_action(d, jogada(d, PlayCat))
    ev, _ = passar(d, 8)                       # mais 4 rodadas: sem a jogada, ja teria disparado
    assert not deadlock_em(ev)
    ev, _ = passar(d, 12)
    assert deadlock_em(ev)


def test_gato_morto_reinicia_a_contagem(content):
    d = parado(content, enemy_field={0: fc(1, 50), 1: fc(1, 1)})
    ev, _ = passar(d, 8)
    assert not deadlock_em(ev)
    ev = apply_action(d, Attack(0, ("slot", 1)))      # mata o gato de HP 1
    assert not deadlock_em(ev)
    ev, _ = passar(d, 8)
    assert not deadlock_em(ev)
    ev, _ = passar(d, 12)
    assert deadlock_em(ev)


def test_lider_com_hp_liquido_menor_reinicia_a_contagem(content):
    d = parado(content)
    ev, _ = passar(d, 8)
    assert not deadlock_em(ev)
    apply_action(d, Attack(0, ("leader",)))           # Lider inimigo perde 1 HP
    ev, _ = passar(d, 8)
    assert not deadlock_em(ev)
    ev, _ = passar(d, 12)
    assert deadlock_em(ev)


def test_cura_que_compensa_o_dano_nao_reinicia_banho_de_espuma(content):
    # Gato de ATK 1 bate no Lider todo turno; o Banho de Espuma cura 1 por turno: sem perda liquida.
    d = parado(content, enemy_leader_hp=25)
    d.sides["enemy"].rule = dict(BANHO)
    eventos = []
    for _ in range(300):
        if is_over(d) is not None:
            break
        ataques = [a for a in legal_actions(d) if d.turn_side == "player" and isinstance(a, Attack)
                    and a.target == ("leader",)]
        eventos += apply_action(d, ataques[0] if ataques else EndTurn())
    assert deadlock_em(eventos)
    assert is_over(d) in ("player", "enemy")


def test_efeito_que_nao_altera_nada_nao_reinicia(content):
    # Cura de Lider com o Lider cheio: nao joga gato, nao mata, nao baixa HP.
    soneca = card_from_effect(content, "soneca-no-sol")
    d = parado(content, player_hand=[soneca] * 6, enemy_hand=[soneca] * 6)
    n_total = 0
    ev = []
    while not deadlock_em(ev) and n_total < 40:
        for a in legal_actions(d):
            if isinstance(a, PlayEffect):
                ev += apply_action(d, a)
                break
        ev += apply_action(d, EndTurn())
        n_total += 1
    assert deadlock_em(ev)
    assert n_total <= N * RODADA + 1


# ---------------- desligado ----------------

def test_sem_stall_rounds_a_estagnacao_fica_desligada(content, monkeypatch):
    monkeypatch.delitem(content.rules["deadlock"], "stall_rounds")
    d = parado(content)
    ev, n = passar(d, 200)
    assert n == 200 and not deadlock_em(ev)
    assert is_over(d) is None


# ---------------- determinismo e IA ----------------

def ia_vs_madame(content, seed):
    rng = Random(seed)
    d = new_duel_vs_enemy(content, deck_spec(content, seed), "madame-fifi-pelucia", rng)
    ev = list(d.log)
    for _ in range(5000):
        if is_over(d) is not None:
            break
        ev += apply_action(d, choose_action(d, d.turn_side, rng))
    return d, ev


def test_estagnacao_e_deterministica_por_seed(content):
    d1, e1 = ia_vs_madame(content, 7)
    d2, e2 = ia_vs_madame(content, 7)
    assert e1 == e2
    assert is_over(d1) == is_over(d2) is not None


def test_150_duelos_ia_contra_madame_fifi_pelucia_terminam_todos(content):
    for seed in range(150):
        d, _ = ia_vs_madame(content, seed)
        assert is_over(d) in ("player", "enemy"), f"seed {seed} nao terminou"
