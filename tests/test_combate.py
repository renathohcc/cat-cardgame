"""Testes de combate/turnos do duelo, a partir do GDD (Combate) e de docs/CONTRATOS.md 2.3.

So API publica do core. Todo sorteio usa Random com seed fixa.
"""
from __future__ import annotations

import copy
from random import Random

import pytest

from core.duel import apply_action, is_over, legal_actions, new_duel, view
from core.types import (Attack, CatDied, CatPlayed, DamageDealt, DiceRolled, DrawSkipped,
                        Drew, DuelEnded, EndTurn, EnergyChanged, IllegalAction,
                        LeaderDamaged, PlayCat, PlayEffect, TurnStarted)
from duel_helpers import deck_spec, duel, fc, load, mk


@pytest.fixture(scope="module")
def content():
    return load()


def attacks(d, slot=None):
    return [a for a in legal_actions(d)
            if isinstance(a, Attack) and (slot is None or a.attacker_slot == slot)]


def snapshot(d):
    return copy.deepcopy(d.sides), d.turn_side, d.winner, d.rng.getstate(), len(d.log)


# ---------------------------------------------------------------- troca de dano
def test_troca_de_dano_entre_gatos_ambos_recebem_o_atk_do_outro(content):
    d = duel(content, player_field={0: fc(3, 5)}, enemy_field={0: fc(2, 4)})
    apply_action(d, Attack(0, ("slot", 0)))
    assert d.sides["enemy"].field[0].hp == 1
    assert d.sides["player"].field[0].hp == 3


def test_gato_com_hp_zero_morre_e_libera_o_slot(content):
    d = duel(content, player_field={0: fc(4, 5)}, enemy_field={0: fc(1, 4)})
    ev = apply_action(d, Attack(0, ("slot", 0)))
    assert d.sides["enemy"].field[0] is None
    assert any(isinstance(e, CatDied) and e.side == "enemy" and e.slot == 0 for e in ev)


def test_troca_mortal_mata_os_dois_gatos(content):
    d = duel(content, player_field={0: fc(3, 3), 1: fc(1, 9)}, enemy_field={0: fc(3, 3), 1: fc(1, 9)})
    apply_action(d, Attack(0, ("slot", 0)))
    assert d.sides["player"].field[0] is None
    assert d.sides["enemy"].field[0] is None


def test_atacar_o_lider_nao_causa_dano_de_volta(content):
    d = duel(content, player_field={0: fc(3, 5)}, enemy_field={0: fc(9, 9)})
    ev = apply_action(d, Attack(0, ("leader",)))
    assert d.sides["enemy"].leader_hp == 17
    assert d.sides["player"].field[0].hp == 5
    assert not any(isinstance(e, DamageDealt) and e.side == "player" for e in ev)
    assert d.sides["player"].leader_hp == 20


def test_lider_nao_ataca_sozinho(content):
    d = duel(content, player_field={0: fc(1, 5)}, enemy_field={0: fc(1, 5)})
    assert all(not isinstance(a, Attack) or a.attacker_slot == 0 for a in legal_actions(d))
    apply_action(d, EndTurn())
    assert d.sides["player"].leader_hp == 20


def test_cada_gato_ataca_so_1_vez_por_turno(content):
    d = duel(content, player_field={0: fc(1, 5), 1: fc(1, 5)}, enemy_field={0: fc(1, 20)})
    apply_action(d, Attack(0, ("leader",)))
    assert attacks(d, 0) == []
    assert attacks(d, 1) != []
    with pytest.raises(IllegalAction):
        apply_action(d, Attack(0, ("leader",)))


def test_gato_volta_a_atacar_no_turno_seguinte(content):
    d = duel(content, player_field={0: fc(1, 5)}, enemy_field={0: fc(1, 20)})
    apply_action(d, Attack(0, ("leader",)))
    apply_action(d, EndTurn())
    apply_action(d, EndTurn())
    assert attacks(d, 0) != []


def test_nao_ataca_com_slot_vazio_nem_alvo_vazio(content):
    d = duel(content, player_field={0: fc(1, 5)}, enemy_field={0: fc(1, 20)})
    for bad in (Attack(3, ("leader",)), Attack(0, ("slot", 4)), Attack(9, ("leader",)),
                Attack(0, ("slot", 9))):
        with pytest.raises(IllegalAction):
            apply_action(d, bad)


# ---------------------------------------------------------------- primeiro turno
def test_quem_comeca_nao_ataca_no_primeiro_turno(content):
    d = duel(content, first_turn=True, player_field={0: fc(3, 5)}, enemy_field={0: fc(1, 5)})
    assert attacks(d) == []
    with pytest.raises(IllegalAction):
        apply_action(d, Attack(0, ("leader",)))


def test_quem_comeca_ataca_a_partir_do_segundo_turno(content):
    d = duel(content, first_turn=True, player_field={0: fc(3, 5)}, enemy_field={0: fc(1, 5)})
    apply_action(d, EndTurn())
    apply_action(d, EndTurn())
    assert attacks(d, 0) != []


def test_primeiro_turno_ainda_permite_jogar_gato(content):
    # Energia do 1o turno de quem comeca = 1 (CONTRATOS 1.4, decisao de 2026-10-27): gato de custo 1.
    d = duel(content, first_turn=True, player_hand=[mk(1, 1, cost=1)])
    assert d.sides["player"].energy == 1
    assert PlayCat(0, 0) in legal_actions(d)


def test_primeiro_turno_nao_permite_gato_de_custo_2(content):
    d = duel(content, first_turn=True, player_hand=[mk(1, 1, cost=2)])
    assert PlayCat(0, 0) not in legal_actions(d)


# ---------------------------------------------------------------- energia
# Curvas (GDD, Energia; CONTRATOS 1.4): 1o jogador 1, 3, 4, 5... ; 2o jogador
# 2, 3, 4... ; teto 7.
def _energias(eventos, lado):
    return [e.energy for e in eventos if isinstance(e, TurnStarted) and e.side == lado]


def _joga_ate_turnos(d, turnos):
    """Passa `turnos` turnos jogando um gato por turno quando possivel (jogar gato mantem o
    duelo vivo, pois a estagnacao exige rodadas sem gato jogado)."""
    eventos = list(d.log)
    for _ in range(turnos):
        jogadas = [a for a in legal_actions(d) if isinstance(a, PlayCat)]
        if jogadas:
            eventos += apply_action(d, jogadas[0])
        eventos += apply_action(d, EndTurn())
    return eventos


def test_energia_do_primeiro_jogador_1_3_4_teto_7(content):
    d = new_duel(content, Random(5), deck_spec(content, 1), deck_spec(content, 2), player_first=True)
    eventos = _joga_ate_turnos(d, 14)
    energias = _energias(eventos, "player")
    assert energias[:7] == [1, 3, 4, 5, 6, 7, 7]
    assert energias == [1] + [min(7, 2 + i) for i in range(1, len(energias))]
    assert max(energias) == 7


def test_energia_do_segundo_jogador_2_3_4_teto_7(content):
    d = new_duel(content, Random(5), deck_spec(content, 1), deck_spec(content, 2), player_first=True)
    eventos = _joga_ate_turnos(d, 14)
    energias = _energias(eventos, "enemy")
    assert energias[:7] == [2, 3, 4, 5, 6, 7, 7]
    assert energias == [min(7, 2 + i) for i in range(len(energias))]


def test_segundo_jogador_comeca_com_energia_2_e_o_primeiro_com_1(content):
    d = new_duel(content, Random(5), deck_spec(content, 1), deck_spec(content, 2), player_first=False)
    eventos = list(d.log) + apply_action(d, EndTurn())
    assert [e.energy for e in eventos if isinstance(e, TurnStarted)][:2] == [1, 2]


def test_energia_reinicia_a_cada_turno_e_nao_acumula(content):
    d = new_duel(content, Random(5), deck_spec(content, 1), deck_spec(content, 2), player_first=True)
    assert d.sides["player"].energy == 1
    apply_action(d, EndTurn())
    apply_action(d, EndTurn())
    assert d.sides["player"].energy == 3  # nao 1+gasto: reinicia na curva 1, 3, 4...


def test_energia_nao_gasta_nao_acumula(content):
    d = new_duel(content, Random(5), deck_spec(content, 1), deck_spec(content, 2), player_first=True)
    for _ in range(3):
        apply_action(d, EndTurn())
        apply_action(d, EndTurn())
    assert d.sides["player"].energy == 5  # 4o turno do 1o jogador: 1, 3, 4, 5


def test_nada_de_energia_1_no_segundo_turno_do_primeiro_jogador(content):
    for seed in range(10):
        d = new_duel(content, Random(seed), deck_spec(content, 1), deck_spec(content, 2))
        primeiro = d.first_side
        eventos = list(d.log)
        for _ in range(6):
            eventos += apply_action(d, EndTurn())
        energias = _energias(eventos, primeiro)
        assert energias[0] == 1 and energias[1] == 3 and 1 not in energias[1:]


def test_segundo_jogador_nao_e_afetado_pela_chave(content):
    for seed in range(10):
        d = new_duel(content, Random(seed), deck_spec(content, 1), deck_spec(content, 2))
        outro = "enemy" if d.first_side == "player" else "player"
        eventos = list(d.log)
        for _ in range(8):
            eventos += apply_action(d, EndTurn())
        assert _energias(eventos, outro)[:3] == [2, 3, 4]


def test_jogar_gato_gasta_energia_igual_ao_custo(content):
    d = duel(content, player_hand=[mk(1, 1, cost=2)], player_energy=3)
    ev = apply_action(d, PlayCat(0, 0))
    assert d.sides["player"].energy == 1
    assert any(isinstance(e, CatPlayed) and e.slot == 0 for e in ev)
    assert any(isinstance(e, EnergyChanged) and e.side == "player" and e.energy == 1 for e in ev)
    assert d.sides["player"].hand == []


def test_custo_maior_que_a_energia_e_ilegal(content):
    d = duel(content, player_hand=[mk(1, 1, cost=4)], player_energy=3)
    assert PlayCat(0, 0) not in legal_actions(d)
    with pytest.raises(IllegalAction):
        apply_action(d, PlayCat(0, 0))


def test_custo_igual_a_energia_e_legal(content):
    d = duel(content, player_hand=[mk(1, 1, cost=3)], player_energy=3)
    apply_action(d, PlayCat(0, 0))
    assert d.sides["player"].energy == 0


# ---------------------------------------------------------------- compra
def test_compra_1_carta_por_turno_inclusive_no_primeiro(content):
    d = new_duel(content, Random(3), deck_spec(content, 1), deck_spec(content, 2), player_first=True)
    assert len(d.sides["player"].hand) == 5   # 4 iniciais + 1 do primeiro turno
    assert len(d.sides["enemy"].hand) == 4
    ev = apply_action(d, EndTurn())
    assert len(d.sides["enemy"].hand) == 5
    assert sum(isinstance(e, Drew) and e.side == "enemy" for e in ev) == 1


def test_deck_de_12_so_gatos_comecam_com_mao_4_e_deck_restante(content):
    d = new_duel(content, Random(3), deck_spec(content, 1), deck_spec(content, 2), player_first=False)
    assert len(d.sides["player"].hand) == 4 and len(d.sides["player"].deck) == 8
    assert len(d.sides["enemy"].hand) == 5 and len(d.sides["enemy"].deck) == 7


def test_mao_com_7_pula_a_compra_e_emite_drawskipped_sem_descartar(content):
    cartas = [mk(1, 1) for _ in range(7)]
    d = duel(content, turn_side="enemy", player_hand=cartas, player_deck=[mk(1, 1)],
             enemy_field={0: fc(1, 5)})
    mao_antes = list(d.sides["player"].hand)
    ev = apply_action(d, EndTurn())
    assert any(isinstance(e, DrawSkipped) and e.side == "player" for e in ev)
    assert not any(isinstance(e, Drew) and e.side == "player" for e in ev)
    assert d.sides["player"].hand == mao_antes
    assert len(d.sides["player"].deck) == 1


def test_mao_com_6_compra_e_chega_a_7(content):
    d = duel(content, turn_side="enemy", player_hand=[mk(1, 1) for _ in range(6)],
             player_deck=[mk(1, 1)], enemy_field={0: fc(1, 5)})
    apply_action(d, EndTurn())
    assert len(d.sides["player"].hand) == 7 and d.sides["player"].deck == []


def test_deck_vazio_nao_compra_e_nao_causa_dano(content):
    d = duel(content, turn_side="enemy", player_hand=[mk(1, 1)], player_field={0: fc(1, 5)},
             enemy_field={0: fc(1, 5)})
    ev = apply_action(d, EndTurn())
    assert len(d.sides["player"].hand) == 1
    assert d.sides["player"].leader_hp == 20
    assert not any(isinstance(e, (Drew, LeaderDamaged)) for e in ev)
    assert d.winner is None


# ---------------------------------------------------------------- slots
def test_nao_joga_o_6o_gato_com_5_slots_ocupados(content):
    d = duel(content, player_hand=[mk(1, 1)], player_field={i: fc(1, 1) for i in range(5)},
             enemy_field={0: fc(1, 5)}, player_energy=5)
    assert not [a for a in legal_actions(d) if isinstance(a, PlayCat)]
    with pytest.raises(IllegalAction):
        apply_action(d, PlayCat(0, 0))


def test_slot_alem_do_quinto_nao_existe(content):
    d = duel(content, player_hand=[mk(1, 1)], enemy_field={0: fc(1, 5)})
    with pytest.raises(IllegalAction):
        apply_action(d, PlayCat(0, 5))


def test_nao_joga_em_slot_ocupado_mas_joga_em_slot_livre(content):
    d = duel(content, player_hand=[mk(1, 1)], player_field={2: fc(1, 1)}, enemy_field={0: fc(1, 5)})
    with pytest.raises(IllegalAction):
        apply_action(d, PlayCat(0, 2))
    apply_action(d, PlayCat(0, 3))
    assert d.sides["player"].field[3] is not None


def test_o_jogador_escolhe_o_slot_ao_jogar(content):
    carta = mk(1, 1, name="escolhido")
    d = duel(content, player_hand=[carta], enemy_field={0: fc(1, 5)})
    apply_action(d, PlayCat(0, 4))
    assert d.sides["player"].field[4].card.name == "escolhido"


def test_indice_de_mao_inexistente_e_ilegal(content):
    d = duel(content, player_hand=[mk(1, 1)], enemy_field={0: fc(1, 5)})
    with pytest.raises(IllegalAction):
        apply_action(d, PlayCat(3, 0))


# ---------------------------------------------------------------- legalidade
def test_acao_ilegal_levanta_illegalaction_e_nao_altera_estado_nem_rng(content):
    d = duel(content, player_hand=[mk(1, 1, cost=5)], player_field={0: fc(2, 5)},
             enemy_field={0: fc(1, 5, kw=("provocar",)), 1: fc(1, 5)})
    antes = snapshot(d)
    for bad in (PlayCat(0, 1), Attack(0, ("leader",)), Attack(0, ("slot", 1)),
                Attack(4, ("leader",)), PlayCat(7, 0)):
        with pytest.raises(IllegalAction):
            apply_action(d, bad)
    assert snapshot(d) == antes


def test_fora_do_turno_o_lado_nao_ataca(content):
    d = duel(content, turn_side="enemy", player_field={0: fc(3, 5)}, enemy_field={0: fc(1, 5)})
    for a in legal_actions(d):
        if isinstance(a, Attack):
            assert a.attacker_slot == 0
    # o unico gato com ataque legal e o do inimigo (slot 0 dele), nunca o do jogador
    assert d.turn_side == "enemy"


def test_endturn_sempre_legal_enquanto_ha_jogo(content):
    d = duel(content, player_field={0: fc(1, 5)}, enemy_field={0: fc(1, 5)})
    assert EndTurn() in legal_actions(d)


def test_endturn_passa_a_vez_ao_adversario(content):
    d = duel(content, player_field={0: fc(1, 5)}, enemy_field={0: fc(1, 5)})
    ev = apply_action(d, EndTurn())
    assert d.turn_side == "enemy"
    assert any(isinstance(e, TurnStarted) and e.side == "enemy" for e in ev)


def test_playeffect_levanta_illegalaction_ainda_nao_suportado(content):
    d = duel(content, player_hand=[mk(1, 1)], enemy_field={0: fc(1, 5)})
    with pytest.raises(IllegalAction):
        apply_action(d, PlayEffect(0, ("leader",)))
    assert not [a for a in legal_actions(d) if isinstance(a, PlayEffect)]


# ---------------------------------------------------------------- vitoria
def test_vence_quem_zerar_o_hp_do_lider(content):
    d = duel(content, player_field={0: fc(3, 5)}, enemy_field={0: fc(1, 5)}, enemy_leader_hp=3)
    ev = apply_action(d, Attack(0, ("leader",)))
    assert any(isinstance(e, DuelEnded) and e.winner == "player" for e in ev)
    assert is_over(d) == "player" and d.winner == "player"
    assert legal_actions(d) == []


def test_inimigo_tambem_vence_zerando_o_lider_do_jogador(content):
    d = duel(content, turn_side="enemy", player_field={0: fc(1, 5)}, enemy_field={0: fc(4, 5)},
             player_leader_hp=4)
    apply_action(d, Attack(0, ("leader",)))
    assert is_over(d) == "enemy"


def test_dano_acima_do_hp_do_lider_tambem_vence(content):
    d = duel(content, player_field={0: fc(9, 5)}, enemy_field={0: fc(1, 5)}, enemy_leader_hp=2)
    apply_action(d, Attack(0, ("leader",)))
    assert is_over(d) == "player"


def test_duelo_em_andamento_nao_tem_vencedor(content):
    d = duel(content, player_field={0: fc(1, 5)}, enemy_field={0: fc(1, 5)})
    assert is_over(d) is None


def test_depois_do_fim_nenhuma_acao_e_aceita(content):
    d = duel(content, player_field={0: fc(3, 5)}, enemy_field={0: fc(1, 5)}, enemy_leader_hp=3)
    apply_action(d, Attack(0, ("leader",)))
    with pytest.raises(IllegalAction):
        apply_action(d, EndTurn())


# ---------------------------------------------------------------- determinismo / dado
def _roda(content, seed):
    d = new_duel(content, Random(seed), deck_spec(content, 10), deck_spec(content, 11))
    pol = Random(seed + 1000)
    for _ in range(300):
        if d.winner:
            break
        apply_action(d, pol.choice(legal_actions(d)))
    return d


def test_mesma_seed_e_mesmas_acoes_dao_o_mesmo_resultado(content):
    a, b = _roda(content, 7), _roda(content, 7)
    assert a.log == b.log
    assert a.sides == b.sides and a.winner == b.winner


def test_new_duel_sorteia_quem_comeca_e_emite_dicerolled(content):
    primeiros = set()
    for seed in range(30):
        d = new_duel(content, Random(seed), deck_spec(content, 1), deck_spec(content, 2))
        dado = [e for e in d.log if isinstance(e, DiceRolled)]
        assert len(dado) == 1 and dado[0].first == d.turn_side
        primeiros.add(d.turn_side)
    assert primeiros == {"player", "enemy"}


def test_player_first_explicito_nao_rola_o_dado(content):
    d = new_duel(content, Random(1), deck_spec(content, 1), deck_spec(content, 2), player_first=False)
    assert d.turn_side == "enemy"


def test_new_duel_rejeita_filhote_no_deck(content):
    spec = deck_spec(content, 1)
    spec.cats[0].stage = "kitten"
    with pytest.raises(ValueError):
        new_duel(content, Random(1), spec, deck_spec(content, 2))


# ---------------------------------------------------------------- view
def test_view_oculta_a_mao_do_adversario(content):
    d = duel(content, player_hand=[mk(1, 1), mk(2, 2)], enemy_hand=[mk(3, 3)],
             player_field={0: fc(1, 5)}, enemy_field={0: fc(1, 5)})
    vp, ve = view(d, "player"), view(d, "enemy")
    assert vp.opponent.hand is None and vp.opponent.hand_count == 1
    assert vp.me.hand is not None and len(vp.me.hand) == 2 and vp.me.hand_count == 2
    assert ve.opponent.hand is None and ve.opponent.hand_count == 2
    assert vp.me.leader_hp == 20 and vp.turn_side == "player" and vp.winner is None


def test_view_e_copia_e_nao_expoe_o_estado_interno(content):
    d = duel(content, player_hand=[mk(1, 1)], player_field={0: fc(1, 5)}, enemy_field={0: fc(1, 5)})
    v = view(d, "player")
    v.me.hand.clear()
    v.me.field[0].hp = 99
    assert len(d.sides["player"].hand) == 1
    assert d.sides["player"].field[0].hp == 5


# ---------------------------------------------------------------- propriedade
SEEDS = range(150)


@pytest.mark.parametrize("seed", SEEDS)
def test_duelo_aleatorio_sempre_termina_com_vencedor_e_respeita_invariantes(content, seed):
    rng = Random(seed)
    d = new_duel(content, Random(seed), deck_spec(content, seed * 2 + 1),
                 deck_spec(content, seed * 2 + 2))
    regras = content.rules["duel"]
    for passo in range(4000):
        if d.winner:
            break
        acoes = legal_actions(d)
        nao_passar = [a for a in acoes if not isinstance(a, EndTurn)]
        a = rng.choice(nao_passar) if nao_passar and rng.random() < 0.9 else EndTurn()
        apply_action(d, a)
        for lado in d.sides.values():
            assert lado.leader_hp <= lado.leader_hp_max
            assert len(lado.field) == regras["slots"]
            assert sum(c is not None for c in lado.field) <= regras["slots"]
            assert lado.energy <= regras["energy_cap"]
            assert len(lado.hand) <= regras["hand_max"]
            for c in lado.field:
                assert c is None or 0 < c.hp <= c.hp_max
    assert d.winner in ("player", "enemy"), "duelo nao terminou em 4000 passos"
    assert is_over(d) == d.winner
    assert legal_actions(d) == []


def test_segundo_jogador_pode_atacar_no_seu_primeiro_turno(content):
    d = duel(content, first_turn=True, player_field={0: fc(3, 5)}, enemy_field={0: fc(1, 5)})
    apply_action(d, EndTurn())
    assert d.turn_side == "enemy" and d.first_side == "player"
    assert Attack(0, ("leader",)) in legal_actions(d)
    apply_action(d, Attack(0, ("leader",)))
    assert d.sides["player"].leader_hp == 19


# ---------------------------------------------------------------- chave first_player_energy_start
def _sem_chave(content):
    c = copy.deepcopy(content)
    c.rules["duel"].pop("first_player_energy_start", None)
    return c


def test_chave_ausente_vale_energy_start_para_os_dois(content):
    c = _sem_chave(content)
    assert "first_player_energy_start" not in c.rules["duel"]
    for primeiro in (True, False):
        d = new_duel(c, Random(5), deck_spec(c, 1), deck_spec(c, 2), player_first=primeiro)
        eventos = list(d.log)
        for _ in range(8):
            eventos += apply_action(d, EndTurn())
        for lado in ("player", "enemy"):
            assert _energias(eventos, lado)[:4] == [2, 3, 4, 5]


def test_chave_vale_para_quem_ganhou_o_dado_nos_dois_sorteios(content):
    vistos = {}
    for seed in range(40):
        d = new_duel(content, Random(seed), deck_spec(content, 1), deck_spec(content, 2))
        vistos.setdefault(d.first_side, seed)
        if len(vistos) == 2:
            break
    assert set(vistos) == {"player", "enemy"}
    for primeiro, seed in vistos.items():
        outro = "enemy" if primeiro == "player" else "player"
        d = new_duel(content, Random(seed), deck_spec(content, 1), deck_spec(content, 2))
        assert d.sides[primeiro].energy == 1
        eventos = list(d.log) + apply_action(d, EndTurn())
        assert _energias(eventos, primeiro)[0] == 1
        assert _energias(eventos, outro)[0] == 2
