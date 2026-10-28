"""Testes das 4 keywords (Provocar, Investida, Primeira Patada, Robusto).

Escritos a partir do GDD (Combate) e de docs/CONTRATOS.md 2.3, so com a API publica do core.
"""
from __future__ import annotations

import pytest

from core.duel import apply_action, legal_actions
from core.types import (Attack, CatDied, DamageDealt, EndTurn, Healed, IllegalAction,
                        LeaderDamaged, PlayCat)
from duel_helpers import duel, fc, load, mk


@pytest.fixture(scope="module")
def content():
    return load()


def attack_targets(d, slot):
    return {a.target for a in legal_actions(d) if isinstance(a, Attack) and a.attacker_slot == slot}


# ---------------------------------------------------------------- Provocar
def test_provocar_bloqueia_ataque_ao_lider(content):
    d = duel(content, player_field={0: fc(3, 5)}, enemy_field={0: fc(1, 5, kw=("provocar",))})
    assert ("leader",) not in attack_targets(d, 0)
    with pytest.raises(IllegalAction):
        apply_action(d, Attack(0, ("leader",)))


def test_provocar_obriga_atacar_so_o_provocar_e_nao_outro_gato(content):
    d = duel(content, player_field={0: fc(3, 5)},
             enemy_field={0: fc(1, 5, kw=("provocar",)), 1: fc(1, 5)})
    assert attack_targets(d, 0) == {("slot", 0)}
    with pytest.raises(IllegalAction):
        apply_action(d, Attack(0, ("slot", 1)))


def test_provocar_pode_ser_atacado_pelo_atacante_que_o_escolhe(content):
    d = duel(content, player_field={0: fc(3, 5)}, enemy_field={0: fc(1, 5, kw=("provocar",))})
    ev = apply_action(d, Attack(0, ("slot", 0)))
    assert any(isinstance(e, DamageDealt) and e.side == "enemy" and e.slot == 0 and e.amount == 3
               for e in ev)


def test_sem_provocar_atacante_escolhe_lider_ou_qualquer_gato(content):
    d = duel(content, player_field={0: fc(3, 5)}, enemy_field={0: fc(1, 5), 1: fc(1, 5)})
    assert attack_targets(d, 0) == {("leader",), ("slot", 0), ("slot", 1)}


def test_com_dois_provocar_e_preciso_destruir_os_dois(content):
    d = duel(content,
             player_field={0: fc(5, 9), 1: fc(5, 9), 2: fc(5, 9)},
             enemy_field={0: fc(1, 2, kw=("provocar",)), 1: fc(1, 2, kw=("provocar",)), 2: fc(1, 9)})
    assert attack_targets(d, 0) == {("slot", 0), ("slot", 1)}
    apply_action(d, Attack(0, ("slot", 0)))
    assert d.sides["enemy"].field[0] is None
    # um Provocar vivo: Lider e gato comum continuam protegidos
    assert attack_targets(d, 1) == {("slot", 1)}
    apply_action(d, Attack(1, ("slot", 1)))
    # os dois destruidos: Lider e gato comum liberados
    assert attack_targets(d, 2) == {("leader",), ("slot", 2)}


def test_provocar_do_proprio_lado_nao_restringe_os_proprios_ataques(content):
    d = duel(content, player_field={0: fc(2, 5, kw=("provocar",)), 1: fc(2, 5)},
             enemy_field={0: fc(1, 5)})
    assert ("leader",) in attack_targets(d, 1)


def test_provocar_vale_nos_dois_lados(content):
    d = duel(content, turn_side="enemy", player_field={0: fc(1, 5, kw=("provocar",))},
             enemy_field={0: fc(3, 5)})
    assert attack_targets(d, 0) == {("slot", 0)}


# ---------------------------------------------------------------- entrada / Investida
def test_gato_nao_ataca_no_turno_em_que_entra(content):
    d = duel(content, player_hand=[mk(3, 3, cost=2)], enemy_field={0: fc(1, 5)})
    apply_action(d, PlayCat(0, 0))
    assert not [a for a in legal_actions(d) if isinstance(a, Attack) and a.attacker_slot == 0]
    with pytest.raises(IllegalAction):
        apply_action(d, Attack(0, ("leader",)))


def test_investida_ataca_no_turno_em_que_entra(content):
    d = duel(content, player_hand=[mk(3, 3, cost=2, kw=("investida",))], enemy_field={0: fc(1, 5)})
    apply_action(d, PlayCat(0, 0))
    assert ("leader",) in attack_targets(d, 0)
    ev = apply_action(d, Attack(0, ("leader",)))
    assert any(isinstance(e, LeaderDamaged) and e.side == "enemy" and e.amount == 3 for e in ev)


def test_gato_que_entrou_ataca_no_turno_seguinte_do_dono(content):
    d = duel(content, player_hand=[mk(3, 3, cost=2)], enemy_field={0: fc(1, 5)})
    apply_action(d, PlayCat(0, 0))
    apply_action(d, EndTurn())
    apply_action(d, EndTurn())
    assert ("leader",) in attack_targets(d, 0)


# ---------------------------------------------------------------- Primeira Patada
def _skip_to_my_turn(d):
    apply_action(d, EndTurn())
    apply_action(d, EndTurn())


def test_primeira_patada_dobra_so_o_primeiro_ataque_da_vida(content):
    d = duel(content, player_field={0: fc(2, 9, kw=("primeira-patada",))},
             enemy_field={0: fc(1, 20)})
    ev = apply_action(d, Attack(0, ("slot", 0)))
    assert [e.amount for e in ev if isinstance(e, DamageDealt) and e.side == "enemy"] == [4]
    _skip_to_my_turn(d)
    ev = apply_action(d, Attack(0, ("slot", 0)))
    assert [e.amount for e in ev if isinstance(e, DamageDealt) and e.side == "enemy"] == [2]


def test_primeira_patada_dobra_tambem_contra_o_lider(content):
    d = duel(content, player_field={0: fc(2, 9, kw=("primeira-patada",))},
             enemy_field={0: fc(1, 20)})
    apply_action(d, Attack(0, ("leader",)))
    assert d.sides["enemy"].leader_hp == 16
    _skip_to_my_turn(d)
    apply_action(d, Attack(0, ("leader",)))
    assert d.sides["enemy"].leader_hp == 14


def test_primeira_patada_gasta_no_ataque_a_gato_nao_dobra_ataque_ao_lider_depois(content):
    d = duel(content, player_field={0: fc(2, 9, kw=("primeira-patada",))},
             enemy_field={0: fc(1, 20)})
    apply_action(d, Attack(0, ("slot", 0)))
    _skip_to_my_turn(d)
    apply_action(d, Attack(0, ("leader",)))
    assert d.sides["enemy"].leader_hp == 18


def test_primeira_patada_nao_dobra_o_dano_recebido(content):
    d = duel(content, turn_side="enemy", player_field={0: fc(2, 9, kw=("primeira-patada",))},
             enemy_field={0: fc(3, 9)})
    ev = apply_action(d, Attack(0, ("slot", 0)))
    recebido = [e.amount for e in ev if isinstance(e, DamageDealt) and e.side == "player"]
    assert recebido == [3]


def test_primeira_patada_defendendo_nao_gasta_o_bonus_do_primeiro_ataque(content):
    d = duel(content, turn_side="enemy", player_field={0: fc(2, 9, kw=("primeira-patada",))},
             enemy_field={0: fc(3, 9)})
    apply_action(d, Attack(0, ("slot", 0)))
    apply_action(d, EndTurn())
    apply_action(d, Attack(0, ("leader",)))
    assert d.sides["enemy"].leader_hp == 16


# ---------------------------------------------------------------- Robusto
def test_robusto_cura_1_no_fim_do_turno_do_dono(content):
    d = duel(content, player_field={0: fc(1, 3, hp_max=5, kw=("robusto",))},
             enemy_field={0: fc(1, 5)})
    ev = apply_action(d, EndTurn())
    assert d.sides["player"].field[0].hp == 4
    assert any(isinstance(e, Healed) and e.side == "player" and e.amount == 1 and e.hp_left == 4
               for e in ev)


def test_robusto_nao_passa_do_hp_maximo(content):
    d = duel(content, player_field={0: fc(1, 5, hp_max=5, kw=("robusto",))},
             enemy_field={0: fc(1, 5)})
    apply_action(d, EndTurn())
    assert d.sides["player"].field[0].hp == 5


def test_robusto_cura_so_1_por_turno_mesmo_muito_ferido(content):
    d = duel(content, player_field={0: fc(1, 1, hp_max=7, kw=("robusto",))},
             enemy_field={0: fc(1, 5)})
    apply_action(d, EndTurn())
    assert d.sides["player"].field[0].hp == 2


def test_robusto_nao_cura_no_fim_do_turno_do_adversario(content):
    d = duel(content, turn_side="enemy", player_field={0: fc(1, 3, hp_max=5, kw=("robusto",))},
             enemy_field={0: fc(1, 5)})
    apply_action(d, EndTurn())
    assert d.sides["player"].field[0].hp == 3


def test_robusto_do_adversario_nao_cura_no_meu_fim_de_turno(content):
    d = duel(content, player_field={0: fc(1, 5)},
             enemy_field={0: fc(1, 3, hp_max=5, kw=("robusto",))})
    apply_action(d, EndTurn())
    assert d.sides["enemy"].field[0].hp == 3


def test_robusto_cura_depois_de_apanhar_no_proprio_turno(content):
    d = duel(content, player_field={0: fc(1, 5, hp_max=5, kw=("robusto",))},
             enemy_field={0: fc(3, 9)})
    apply_action(d, Attack(0, ("slot", 0)))      # recebe 3 de volta
    assert d.sides["player"].field[0].hp == 2
    apply_action(d, EndTurn())
    assert d.sides["player"].field[0].hp == 3


def test_robusto_morto_nao_cura(content):
    d = duel(content, player_field={0: fc(1, 2, hp_max=5, kw=("robusto",)), 1: fc(1, 5)},
             enemy_field={0: fc(5, 9)})
    ev = apply_action(d, Attack(0, ("slot", 0)))
    assert any(isinstance(e, CatDied) for e in ev)
    ev = apply_action(d, EndTurn())
    assert not any(isinstance(e, Healed) for e in ev)


# ---------------------------------------------------------------- lacunas T1.10b
def _ataques(d):
    from core.types import Attack
    return [a for a in legal_actions(d) if isinstance(a, Attack)]


def test_persa_recem_chegado_protege_o_lider_no_turno_seguinte_do_adversario(content):
    from core import roll_cat
    from random import Random as R
    persa = roll_cat(content, R(1), breed_id="persa")
    d = duel(content, player_hand=[persa], player_energy=3, enemy_field={0: fc(3, 5)})
    apply_action(d, PlayCat(0, 0))
    apply_action(d, EndTurn())
    assert d.turn_side == "enemy"
    alvos = [a.target for a in _ataques(d)]
    assert alvos and ("leader",) not in alvos
    assert set(alvos) == {("slot", 0)}
    with pytest.raises(IllegalAction):
        apply_action(d, Attack(0, ("leader",)))


def test_investida_do_primeiro_jogador_no_turno_1_continua_sem_ataque(content):
    # Energia do 1o turno de quem comeca = 1 (CONTRATOS 1.4, 2026-10-27): gato de custo 1.
    d = duel(content, first_turn=True, player_hand=[mk(3, 3, cost=1, kw=("investida",))],
             enemy_field={0: fc(1, 5)})
    apply_action(d, PlayCat(0, 0))
    assert _ataques(d) == []
    with pytest.raises(IllegalAction):
        apply_action(d, Attack(0, ("leader",)))
