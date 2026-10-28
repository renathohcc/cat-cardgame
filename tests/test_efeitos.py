"""Cartas de efeito e Espiritos (T3.3).

Fonte: GDD (Combate, Loop da run), CONTRATOS 1.6, 1.7 e 2.3, e a proposta
docs/propostas/2026-10-27-conteudo-fase3.md (secoes 1 e 2). Escrito a partir
das regras, nao do codigo do core.
"""
from __future__ import annotations

import pytest

from core.duel import (apply_action, attack_targets, card_from_effect, card_from_special,
                       card_targets, is_over, legal_actions, view)
from core.types import (AtkBuffExpired, AtkBuffed, Attack, Card, CatDied, CatPlayed, DamageDealt,
                        DrawSkipped, Drew, DuelEnded, EffectPlayed, EndTurn, EnergyChanged,
                        Healed, IllegalAction, LeaderDamaged, LeaderHealed, PlayCat, PlayEffect)
from duel_helpers import duel, fc, load, mk

PROV = ("provocar",)


@pytest.fixture(scope="module")
def content():
    return load()


def eff(content, eid: str) -> Card:
    return card_from_effect(content, eid)


def sp(content, sid: str) -> Card:
    return card_from_special(content, sid)


def plays_effect(d, hand_index: int = 0) -> list[PlayEffect]:
    return [a for a in legal_actions(d) if isinstance(a, PlayEffect) and a.hand_index == hand_index]


def plays_cat(d, hand_index: int = 0) -> list[PlayCat]:
    return [a for a in legal_actions(d) if isinstance(a, PlayCat) and a.hand_index == hand_index]


def of(events, kind):
    return [e for e in events if isinstance(e, kind)]


def me(d):
    return view(d, "player").me


def opp(d):
    return view(d, "player").opponent


# ------------------------------------------------------------ tabelas da proposta
EFEITOS = {  # id: custo
    "arranhao-certeiro": 2, "bote-no-lider": 3, "lambida-curativa": 1, "soneca-no-sol": 2,
    "rugido-de-guerra": 1, "petisco-surpresa": 1, "farejar-a-despensa": 2,
    "cochilo-revigorante": 1,
}
ESPIRITOS = {  # id: (custo, atk, hp, keywords)
    "sombra-miuda": (1, 2, 2, {"investida"}),
    "velha-dos-novelos": (2, 2, 4, set()),
    "soneca-ancestral": (2, 1, 5, {"robusto"}),
    "trovao-amarelo": (3, 3, 3, {"investida"}),
    "guardiao-bigodudo": (3, 3, 7, {"provocar"}),
    "mestre-das-garras": (4, 4, 4, {"investida", "primeira-patada"}),
    "pelo-de-aco": (4, 4, 8, {"provocar", "robusto"}),
    "gata-das-brasas": (5, 5, 5, {"primeira-patada"}),
}


def cenario_geral(content, eid: str, energy: int):
    """Mesa em que qualquer um dos 8 efeitos e jogavel (energia a escolher)."""
    return duel(content, seed=3, player_hand=[eff(content, eid)],
                player_deck=[mk(1, 1), mk(1, 1), mk(1, 1)],
                player_field={0: fc(2, 2, hp_max=4)}, enemy_field={0: fc(2, 5)},
                player_energy=energy, player_leader_hp=15)


# ============================================================ 1. efeitos: geral
def test_oito_efeitos_existem_com_os_custos_da_proposta(content):
    assert set(content.effects) == set(EFEITOS)
    for eid, custo in EFEITOS.items():
        assert eff(content, eid).cost == custo, eid
        assert eff(content, eid).kind == "effect"


@pytest.mark.parametrize("eid", sorted(EFEITOS))
def test_efeito_cobra_o_custo_e_consome_a_carta(content, eid):
    d = cenario_geral(content, eid, energy=5)
    antes = me(d).energy
    acao = plays_effect(d)[0]
    ev = apply_action(d, acao)
    liquido = EFEITOS[eid] - (2 if eid == "cochilo-revigorante" else 0)
    assert me(d).energy == antes - liquido
    assert eid not in [c.ref for c in me(d).hand]       # consumida (nao volta a mao)
    assert of(ev, EffectPlayed) and of(ev, EffectPlayed)[0].card.ref == eid
    assert of(ev, EnergyChanged)


@pytest.mark.parametrize("eid", sorted(EFEITOS))
def test_efeito_com_energia_insuficiente_e_ilegal_e_nao_muda_o_estado(content, eid):
    d = cenario_geral(content, eid, energy=EFEITOS[eid] - 1)
    assert plays_effect(d) == []
    for alvo in (("leader",), ("slot", 0)):
        with pytest.raises(IllegalAction):
            apply_action(d, PlayEffect(0, alvo))
    assert me(d).hand_count == 1 and me(d).energy == EFEITOS[eid] - 1


@pytest.mark.parametrize("eid", sorted(EFEITOS))
def test_efeito_com_energia_exata_e_jogavel(content, eid):
    d = cenario_geral(content, eid, energy=EFEITOS[eid])
    assert plays_effect(d)
    apply_action(d, plays_effect(d)[0])
    extra = 2 if eid == "cochilo-revigorante" else 0
    assert me(d).energy == extra


def test_efeito_fora_da_vez_e_ilegal(content):
    # turno do inimigo: a mao do jogador nao pode ser usada; mao do inimigo vazia
    d = duel(content, turn_side="enemy", player_hand=[eff(content, "petisco-surpresa")],
             player_energy=5, enemy_energy=5)
    assert not [a for a in legal_actions(d) if isinstance(a, PlayEffect)]
    with pytest.raises(IllegalAction):
        apply_action(d, PlayEffect(0, ("leader",)))


def test_efeito_depois_do_fim_do_duelo_e_ilegal(content):
    d = duel(content, player_hand=[eff(content, "bote-no-lider")], player_energy=5,
             enemy_leader_hp=4)
    apply_action(d, PlayEffect(0, ("leader",)))
    assert is_over(d) == "player"
    with pytest.raises(IllegalAction):
        apply_action(d, EndTurn())


# ============================================================ dano em gato
def test_arranhao_causa_3_de_dano_em_gato_inimigo_sem_matar(content):
    d = duel(content, player_hand=[eff(content, "arranhao-certeiro")], player_energy=2,
             enemy_field={0: fc(2, 5)})
    ev = apply_action(d, PlayEffect(0, ("slot", 0)))
    assert opp(d).field[0].hp == 2
    assert of(ev, DamageDealt)[0].amount == 3 and of(ev, DamageDealt)[0].side == "enemy"
    assert not of(ev, CatDied)


def test_arranhao_que_mata_remove_o_gato_e_emite_catdied(content):
    d = duel(content, player_hand=[eff(content, "arranhao-certeiro")], player_energy=2,
             enemy_field={0: fc(2, 5), 1: fc(2, 3)})
    ev = apply_action(d, PlayEffect(0, ("slot", 1)))
    assert opp(d).field[1] is None and opp(d).field[0] is not None
    assert [(e.side, e.slot) for e in of(ev, CatDied)] == [("enemy", 1)]


def test_arranhao_alvos_legais_sao_so_gatos_inimigos(content):
    d = duel(content, player_hand=[eff(content, "arranhao-certeiro")], player_energy=2,
             player_field={0: fc(2, 2)}, enemy_field={1: fc(2, 5), 3: fc(1, 1)})
    assert sorted(a.target for a in plays_effect(d)) == [("slot", 1), ("slot", 3)]
    assert sorted(card_targets(d, 0)) == [("slot", 1), ("slot", 3)]
    for ilegal in (("leader",), ("slot", 0), ("slot", 4)):
        with pytest.raises(IllegalAction):
            apply_action(d, PlayEffect(0, ilegal))


def test_arranhao_sem_gato_inimigo_nao_e_jogavel(content):
    d = duel(content, player_hand=[eff(content, "arranhao-certeiro")], player_energy=5,
             player_field={0: fc(2, 2)})
    assert plays_effect(d) == []


def test_provocar_nao_protege_gato_de_carta_de_efeito(content):
    d = duel(content, player_hand=[eff(content, "arranhao-certeiro")], player_energy=2,
             enemy_field={0: fc(1, 5, kw=PROV), 1: fc(2, 5)})
    assert ("slot", 1) in [a.target for a in plays_effect(d)]
    apply_action(d, PlayEffect(0, ("slot", 1)))
    assert opp(d).field[1].hp == 2


# ============================================================ dano em Lider
def test_bote_causa_4_no_lider_ignorando_provocar(content):
    d = duel(content, player_hand=[eff(content, "bote-no-lider")], player_energy=3,
             enemy_field={0: fc(1, 5, kw=PROV)})
    ev = apply_action(d, PlayEffect(0, ("leader",)))
    assert opp(d).leader_hp == 16
    assert of(ev, LeaderDamaged)[0].side == "enemy" and of(ev, LeaderDamaged)[0].amount == 4
    assert opp(d).field[0].hp == 5


def test_bote_letal_encerra_o_duelo_com_vitoria_de_quem_jogou(content):
    d = duel(content, player_hand=[eff(content, "bote-no-lider")], player_energy=3,
             enemy_leader_hp=4, enemy_field={0: fc(1, 5, kw=PROV)})
    ev = apply_action(d, PlayEffect(0, ("leader",)))
    assert is_over(d) == "player"
    assert of(ev, DuelEnded)[0].winner == "player"


def test_bote_acima_do_letal_nao_encerra(content):
    d = duel(content, player_hand=[eff(content, "bote-no-lider")], player_energy=3,
             enemy_leader_hp=5, player_field={4: fc(1, 1)}, enemy_field={4: fc(1, 1)})
    apply_action(d, PlayEffect(0, ("leader",)))
    assert is_over(d) is None and opp(d).leader_hp == 1


def test_bote_so_aceita_o_lider_inimigo_como_alvo(content):
    d = duel(content, player_hand=[eff(content, "bote-no-lider")], player_energy=3,
             player_field={0: fc(2, 2)}, enemy_field={0: fc(2, 5)})
    assert [a.target for a in plays_effect(d)] == [("leader",)]
    with pytest.raises(IllegalAction):
        apply_action(d, PlayEffect(0, ("slot", 0)))


def test_bote_do_inimigo_fere_o_lider_do_jogador(content):
    d = duel(content, turn_side="enemy", enemy_hand=[eff(content, "bote-no-lider")],
             enemy_energy=3, player_field={4: fc(1, 1)}, enemy_field={4: fc(1, 1)})
    ev = apply_action(d, PlayEffect(0, ("leader",)))
    assert view(d, "player").me.leader_hp == 16
    assert of(ev, LeaderDamaged)[0].side == "player"


def test_dano_de_efeito_letal_no_lider_do_jogador_da_vitoria_ao_inimigo(content):
    d = duel(content, turn_side="enemy", enemy_hand=[eff(content, "bote-no-lider")],
             enemy_energy=3, player_leader_hp=3)
    apply_action(d, PlayEffect(0, ("leader",)))
    assert is_over(d) == "enemy"


# ============================================================ cura
def test_lambida_cura_3_no_gato_aliado(content):
    d = duel(content, player_hand=[eff(content, "lambida-curativa")], player_energy=1,
             player_field={0: fc(2, 2, hp_max=9)})
    ev = apply_action(d, PlayEffect(0, ("slot", 0)))
    assert me(d).field[0].hp == 5
    assert of(ev, Healed)[0].hp_left == 5


def test_lambida_nao_passa_do_hp_maximo_do_gato(content):
    d = duel(content, player_hand=[eff(content, "lambida-curativa")], player_energy=1,
             player_field={0: fc(2, 3, hp_max=4)})
    apply_action(d, PlayEffect(0, ("slot", 0)))
    assert me(d).field[0].hp == 4


def test_lambida_em_gato_com_vida_cheia_gasta_carta_e_energia_sem_passar_do_maximo(content):
    d = duel(content, player_hand=[eff(content, "lambida-curativa")], player_energy=1,
             player_field={0: fc(2, 4)})
    apply_action(d, PlayEffect(0, ("slot", 0)))
    assert me(d).field[0].hp == 4 and me(d).hand_count == 0 and me(d).energy == 0


def test_lambida_so_mira_gatos_aliados(content):
    d = duel(content, player_hand=[eff(content, "lambida-curativa")], player_energy=1,
             player_field={2: fc(2, 1, hp_max=4)}, enemy_field={0: fc(2, 1, hp_max=4)})
    assert [a.target for a in plays_effect(d)] == [("slot", 2)]
    for ilegal in (("leader",), ("slot", 0)):
        with pytest.raises(IllegalAction):
            apply_action(d, PlayEffect(0, ilegal))
    assert opp(d).field[0].hp == 1


def test_lambida_sem_aliado_nao_e_jogavel(content):
    d = duel(content, player_hand=[eff(content, "lambida-curativa")], player_energy=5,
             enemy_field={0: fc(2, 1, hp_max=4)})
    assert plays_effect(d) == []


def test_soneca_no_sol_cura_4_no_proprio_lider(content):
    d = duel(content, player_hand=[eff(content, "soneca-no-sol")], player_energy=2,
             player_leader_hp=10, player_field={4: fc(1, 1)}, enemy_field={4: fc(1, 1)})
    ev = apply_action(d, PlayEffect(0, ("leader",)))
    assert me(d).leader_hp == 14
    assert of(ev, LeaderHealed)[0].side == "player"
    assert view(d, "player").opponent.leader_hp == 20


def test_soneca_no_sol_nao_passa_do_hp_maximo_do_lider(content):
    d = duel(content, player_hand=[eff(content, "soneca-no-sol")], player_energy=2,
             player_leader_hp=18, player_field={4: fc(1, 1)}, enemy_field={4: fc(1, 1)})
    apply_action(d, PlayEffect(0, ("leader",)))
    assert me(d).leader_hp == 20


def test_soneca_no_sol_com_lider_cheio_nao_ultrapassa_o_maximo(content):
    d = duel(content, player_hand=[eff(content, "soneca-no-sol")], player_energy=2,
             player_field={4: fc(1, 1)}, enemy_field={4: fc(1, 1)})
    apply_action(d, PlayEffect(0, ("leader",)))
    assert me(d).leader_hp == 20


def test_soneca_no_sol_nao_mira_gato(content):
    d = duel(content, player_hand=[eff(content, "soneca-no-sol")], player_energy=2,
             player_field={0: fc(2, 1, hp_max=4)}, player_leader_hp=5)
    assert [a.target for a in plays_effect(d)] == [("leader",)]
    with pytest.raises(IllegalAction):
        apply_action(d, PlayEffect(0, ("slot", 0)))


def test_cura_de_lider_respeita_maximo_do_lider_com_hp_acima_de_20(content):
    # Lider de 25 de HP (chefe): cura vai ate 25, nao ate 20
    d = duel(content, player_hand=[eff(content, "soneca-no-sol")], player_energy=2,
             player_leader_hp=25, player_field={4: fc(1, 1)}, enemy_field={4: fc(1, 1)})
    d.sides["player"].leader_hp = 23
    apply_action(d, PlayEffect(0, ("leader",)))
    assert me(d).leader_hp == 25


# ============================================================ buff de ATK
def test_rugido_da_2_de_atk_e_o_gato_ataca_com_o_bonus(content):
    d = duel(content, player_hand=[eff(content, "rugido-de-guerra")], player_energy=1,
             player_field={0: fc(2, 3)})
    ev = apply_action(d, PlayEffect(0, ("slot", 0)))
    assert me(d).field[0].atk == 4
    assert of(ev, AtkBuffed)[0].amount == 2
    apply_action(d, Attack(0, ("leader",)))
    assert opp(d).leader_hp == 16


def test_rugido_expira_no_fim_do_turno_do_dono(content):
    d = duel(content, player_hand=[eff(content, "rugido-de-guerra")], player_energy=1,
             player_field={0: fc(2, 3)})
    apply_action(d, PlayEffect(0, ("slot", 0)))
    ev = apply_action(d, EndTurn())
    assert me(d).field[0].atk == 2
    assert of(ev, AtkBuffExpired)
    assert of(ev, AtkBuffExpired)[0].atk == 2


def test_rugido_nao_vale_no_proximo_turno_do_dono(content):
    d = duel(content, player_hand=[eff(content, "rugido-de-guerra")], player_energy=1,
             player_field={0: fc(2, 3)})
    apply_action(d, PlayEffect(0, ("slot", 0)))
    apply_action(d, EndTurn())
    apply_action(d, EndTurn())          # turno do inimigo
    assert d.turn_side == "player"
    apply_action(d, Attack(0, ("leader",)))
    assert opp(d).leader_hp == 18


def test_rugido_so_mira_gato_aliado(content):
    d = duel(content, player_hand=[eff(content, "rugido-de-guerra")], player_energy=1,
             player_field={1: fc(2, 3)}, enemy_field={0: fc(2, 3)})
    assert [a.target for a in plays_effect(d)] == [("slot", 1)]
    for ilegal in (("leader",), ("slot", 0), ("slot", 2)):
        with pytest.raises(IllegalAction):
            apply_action(d, PlayEffect(0, ilegal))


def test_rugido_sem_aliado_nao_e_jogavel(content):
    d = duel(content, player_hand=[eff(content, "rugido-de-guerra")], player_energy=3,
             enemy_field={0: fc(2, 3)})
    assert plays_effect(d) == []


def test_dois_rugidos_no_mesmo_gato_somam_e_ambos_expiram(content):
    r = eff(content, "rugido-de-guerra")
    d = duel(content, player_hand=[r, r], player_energy=2, player_field={0: fc(2, 3)})
    apply_action(d, PlayEffect(0, ("slot", 0)))
    apply_action(d, PlayEffect(0, ("slot", 0)))
    assert me(d).field[0].atk == 6
    apply_action(d, EndTurn())
    assert me(d).field[0].atk == 2


# ============================================================ comprar
def test_petisco_compra_1_carta(content):
    a, b = mk(1, 1, name="a"), mk(1, 1, name="b")
    d = duel(content, player_hand=[eff(content, "petisco-surpresa")], player_deck=[a, b],
             player_energy=1)
    ev = apply_action(d, PlayEffect(0, ("leader",)))
    assert [c.ref for c in me(d).hand] == ["a"]
    assert me(d).deck_count == 1
    assert len(of(ev, Drew)) == 1


def test_farejar_compra_2_cartas(content):
    cartas = [mk(1, 1, name=n) for n in "abc"]
    d = duel(content, player_hand=[eff(content, "farejar-a-despensa")], player_deck=cartas,
             player_energy=2)
    apply_action(d, PlayEffect(0, ("leader",)))
    assert [c.ref for c in me(d).hand] == ["a", "b"]
    assert me(d).deck_count == 1


def test_comprar_com_mao_cheia_pula_a_compra_sem_descartar(content):
    mao = [eff(content, "farejar-a-despensa")] + [mk(1, 1, name=f"m{i}") for i in range(6)]
    deck = [mk(1, 1, name="x"), mk(1, 1, name="y"), mk(1, 1, name="z")]
    d = duel(content, player_hand=mao, player_deck=deck, player_energy=2)
    assert me(d).hand_count == 7
    ev = apply_action(d, PlayEffect(0, ("leader",)))
    # a carta jogada liberou 1 vaga: 1 compra entra, a outra e pulada
    assert me(d).hand_count == 7
    assert len(of(ev, Drew)) == 1 and len(of(ev, DrawSkipped)) == 1
    assert me(d).deck_count == 2                     # a carta pulada continua no deck
    assert [c.ref for c in me(d).hand][-1] == "x"
    assert {f"m{i}" for i in range(6)} <= {c.ref for c in me(d).hand}   # nada descartado


def test_petisco_com_deck_vazio_nao_compra_nem_da_erro_nem_ha_fadiga(content):
    d = duel(content, player_hand=[eff(content, "petisco-surpresa"), mk(1, 1, name="k")],
             player_energy=1)
    hp = me(d).leader_hp
    ev = apply_action(d, PlayEffect(0, ("leader",)))
    assert not of(ev, Drew)
    assert [c.ref for c in me(d).hand] == ["k"]
    assert me(d).energy == 0 and me(d).leader_hp == hp


def test_farejar_com_so_uma_carta_no_deck_compra_so_ela(content):
    d = duel(content, player_hand=[eff(content, "farejar-a-despensa")],
             player_deck=[mk(1, 1, name="unica")], player_energy=2)
    ev = apply_action(d, PlayEffect(0, ("leader",)))
    assert [c.ref for c in me(d).hand] == ["unica"] and me(d).deck_count == 0
    assert len(of(ev, Drew)) == 1


def test_comprar_nao_aceita_alvo_de_gato(content):
    d = duel(content, player_hand=[eff(content, "petisco-surpresa")], player_energy=1,
             player_field={0: fc(1, 1)}, enemy_field={0: fc(1, 1)})
    assert [a.target for a in plays_effect(d)] == [("leader",)]
    with pytest.raises(IllegalAction):
        apply_action(d, PlayEffect(0, ("slot", 0)))


# ============================================================ energia
def test_cochilo_da_2_de_energia_lucro_liquido_de_1(content):
    d = duel(content, player_hand=[eff(content, "cochilo-revigorante")], player_energy=3)
    apply_action(d, PlayEffect(0, ("leader",)))
    assert me(d).energy == 4


def test_cochilo_nao_passa_do_teto_de_7(content):
    for antes in (6, 7):
        d = duel(content, player_hand=[eff(content, "cochilo-revigorante")], player_energy=antes)
        apply_action(d, PlayEffect(0, ("leader",)))
        assert me(d).energy == 7, antes


def test_cochilo_com_energia_1_deixa_energia_2(content):
    d = duel(content, player_hand=[eff(content, "cochilo-revigorante")], player_energy=1)
    apply_action(d, PlayEffect(0, ("leader",)))
    assert me(d).energy == 2


def test_cochilo_destrava_carta_cara_na_mesma_vez(content):
    d = duel(content, player_hand=[eff(content, "cochilo-revigorante"), mk(3, 3, cost=3)],
             player_energy=2)
    assert plays_cat(d, 1) == []
    apply_action(d, PlayEffect(0, ("leader",)))
    assert plays_cat(d, 0)          # a carta cara agora esta no indice 0


# ============================================================ 2. Espiritos
@pytest.mark.parametrize("sid", sorted(ESPIRITOS))
def test_espirito_tem_status_fixos_keywords_e_nenhum_iv(content, sid):
    custo, atk, hp, kws = ESPIRITOS[sid]
    c = sp(content, sid)
    assert (c.kind, c.cost, c.atk, c.hp) == ("special", custo, atk, hp)
    assert set(c.keywords) == kws
    assert c.iv_atk is None and c.iv_hp is None


def test_ha_exatamente_8_espiritos(content):
    assert set(content.specials) == set(ESPIRITOS)


@pytest.mark.parametrize("sid", sorted(ESPIRITOS))
def test_espirito_entra_no_campo_com_os_status_fixos(content, sid):
    custo, atk, hp, _ = ESPIRITOS[sid]
    d = duel(content, player_hand=[sp(content, sid)], player_energy=custo,
             enemy_field={0: fc(1, 20)})
    acao = plays_cat(d)[0]
    ev = apply_action(d, acao)
    assert of(ev, CatPlayed)
    campo = me(d).field[acao.slot]
    assert (campo.atk, campo.hp, campo.hp_max) == (atk, hp, hp)


@pytest.mark.parametrize("sid", sorted(ESPIRITOS))
def test_espirito_com_custo_maior_que_a_energia_e_ilegal(content, sid):
    custo = ESPIRITOS[sid][0]
    d = duel(content, player_hand=[sp(content, sid)], player_energy=custo - 1,
             enemy_field={0: fc(1, 20)}, enemy_leader_hp=20)
    assert plays_cat(d) == []
    with pytest.raises(IllegalAction):
        apply_action(d, PlayCat(0, 0))
    with pytest.raises(IllegalAction):
        apply_action(d, PlayCat(0, 0, ("slot", 0)))
    assert me(d).hand_count == 1 and opp(d).field[0].hp == 20


def test_espirito_cobra_custo_de_energia(content):
    d = duel(content, player_hand=[sp(content, "mestre-das-garras")], player_energy=6)
    apply_action(d, PlayCat(0, 2))
    assert me(d).energy == 2


# ---- efeito ao entrar com alvo escolhido
def test_trovao_amarelo_entra_e_causa_2_no_gato_escolhido(content):
    d = duel(content, player_hand=[sp(content, "trovao-amarelo")], player_energy=3,
             enemy_field={0: fc(2, 5), 1: fc(2, 5)})
    ev = apply_action(d, PlayCat(0, 0, ("slot", 1)))
    assert opp(d).field[1].hp == 3 and opp(d).field[0].hp == 5
    assert me(d).field[0] is not None
    tipos = [type(e) for e in ev]
    assert tipos.index(CatPlayed) < tipos.index(DamageDealt)
    assert of(ev, EffectPlayed)


def test_trovao_amarelo_gera_uma_variante_por_slot_e_por_alvo(content):
    d = duel(content, player_hand=[sp(content, "trovao-amarelo")], player_energy=3,
             enemy_field={1: fc(2, 5), 4: fc(2, 5)})
    alvos = {a.target for a in plays_cat(d)}
    assert alvos == {("slot", 1), ("slot", 4)}
    assert {a.slot for a in plays_cat(d)} == {0, 1, 2, 3, 4}
    assert len(plays_cat(d)) == 10


def test_trovao_amarelo_mata_gato_inimigo_ao_entrar(content):
    d = duel(content, player_hand=[sp(content, "trovao-amarelo")], player_energy=3,
             enemy_field={0: fc(2, 2)})
    ev = apply_action(d, PlayCat(0, 0, ("slot", 0)))
    assert opp(d).field[0] is None
    assert [(e.side, e.slot) for e in of(ev, CatDied)] == [("enemy", 0)]


def test_alvo_ilegal_no_ao_entrar_e_rejeitado(content):
    d = duel(content, player_hand=[sp(content, "trovao-amarelo")], player_energy=3,
             player_field={1: fc(2, 5)}, enemy_field={0: fc(2, 5)})
    for ilegal in (("leader",), ("slot", 3), None):
        with pytest.raises(IllegalAction):
            apply_action(d, PlayCat(0, 2, ilegal))
    assert opp(d).field[0].hp == 5 and me(d).hand_count == 1


def test_trovao_amarelo_sem_gato_inimigo_perde_o_efeito_mas_entra(content):
    d = duel(content, player_hand=[sp(content, "trovao-amarelo")], player_energy=3)
    acoes = plays_cat(d)
    assert acoes and all(a.target is None for a in acoes)
    ev = apply_action(d, PlayCat(0, 0))
    assert me(d).field[0] is not None
    assert not of(ev, DamageDealt)
    assert me(d).energy == 0


def test_sem_alvo_valido_alvo_informado_e_ilegal(content):
    d = duel(content, player_hand=[sp(content, "trovao-amarelo")], player_energy=3)
    with pytest.raises(IllegalAction):
        apply_action(d, PlayCat(0, 0, ("slot", 0)))


def test_efeito_ao_entrar_que_mata_o_ultimo_provocar_libera_o_lider(content):
    d = duel(content, player_hand=[sp(content, "trovao-amarelo")], player_energy=3,
             enemy_field={0: fc(1, 2, kw=PROV), 2: fc(4, 4)})
    apply_action(d, PlayCat(0, 1, ("slot", 0)))
    assert opp(d).field[0] is None
    # Investida: ataca ja, e sem Provocar em campo o Lider e alvo legal
    assert ("leader",) in attack_targets(d, 1)
    apply_action(d, Attack(1, ("leader",)))
    assert opp(d).leader_hp == 17


def test_com_outro_provocar_em_campo_o_lider_continua_protegido(content):
    d = duel(content, player_hand=[sp(content, "trovao-amarelo")], player_energy=3,
             enemy_field={0: fc(1, 2, kw=PROV), 2: fc(1, 4, kw=PROV)})
    apply_action(d, PlayCat(0, 1, ("slot", 0)))
    assert attack_targets(d, 1) == [("slot", 2)]


def test_guardiao_bigodudo_cura_3_no_lider_proprio_ao_entrar(content):
    d = duel(content, player_hand=[sp(content, "guardiao-bigodudo")], player_energy=3,
             player_leader_hp=15)
    ev = apply_action(d, PlayCat(0, 0))
    assert me(d).leader_hp == 18
    assert of(ev, LeaderHealed)[0].amount == 3


def test_guardiao_bigodudo_nao_cura_alem_do_maximo(content):
    d = duel(content, player_hand=[sp(content, "guardiao-bigodudo")], player_energy=3,
             player_leader_hp=19)
    apply_action(d, PlayCat(0, 0))
    assert me(d).leader_hp == 20


def test_guardiao_bigodudo_cura_mesmo_com_campo_vazio_e_nao_pede_alvo(content):
    d = duel(content, player_hand=[sp(content, "guardiao-bigodudo")], player_energy=3,
             player_leader_hp=10)
    assert all(a.target is None for a in plays_cat(d))
    apply_action(d, PlayCat(0, 3))
    assert me(d).leader_hp == 13


def test_gata_das_brasas_causa_3_no_lider_inimigo_ignorando_provocar(content):
    d = duel(content, player_hand=[sp(content, "gata-das-brasas")], player_energy=5,
             enemy_field={0: fc(1, 5, kw=PROV)})
    ev = apply_action(d, PlayCat(0, 0))
    assert opp(d).leader_hp == 17
    assert of(ev, LeaderDamaged)[0].amount == 3


def test_gata_das_brasas_pode_vencer_o_duelo_ao_entrar(content):
    d = duel(content, player_hand=[sp(content, "gata-das-brasas")], player_energy=5,
             enemy_leader_hp=3)
    ev = apply_action(d, PlayCat(0, 0))
    assert is_over(d) == "player" and of(ev, DuelEnded)[0].winner == "player"


def test_velha_dos_novelos_compra_1_ao_entrar(content):
    d = duel(content, player_hand=[sp(content, "velha-dos-novelos")], player_energy=2,
             player_deck=[mk(1, 1, name="p"), mk(1, 1, name="q")])
    ev = apply_action(d, PlayCat(0, 0))
    assert [c.ref for c in me(d).hand] == ["p"] and me(d).deck_count == 1
    assert len(of(ev, Drew)) == 1


def test_velha_dos_novelos_com_deck_vazio_entra_normalmente(content):
    d = duel(content, player_hand=[sp(content, "velha-dos-novelos")], player_energy=2)
    ev = apply_action(d, PlayCat(0, 0))
    assert me(d).field[0] is not None and me(d).hand_count == 0 and not of(ev, Drew)


def test_soneca_ancestral_devolve_1_de_energia_ao_entrar(content):
    d = duel(content, player_hand=[sp(content, "soneca-ancestral")], player_energy=4)
    apply_action(d, PlayCat(0, 0))
    assert me(d).energy == 3                       # 4 - 2 + 1


def test_soneca_ancestral_e_robusta(content):
    d = duel(content, player_hand=[sp(content, "soneca-ancestral")], player_energy=2,
             enemy_field={0: fc(2, 9)})
    apply_action(d, PlayCat(0, 0))
    me(d)  # sanidade
    d.sides["player"].field[0].hp = 2           # preparacao do cenario: gato ferido
    apply_action(d, EndTurn())
    assert me(d).field[0].hp == 3


def test_espirito_sem_efeito_ao_entrar_nao_pede_alvo(content):
    for sid in ("sombra-miuda", "mestre-das-garras", "pelo-de-aco"):
        custo = ESPIRITOS[sid][0]
        d = duel(content, player_hand=[sp(content, sid)], player_energy=custo,
                 enemy_field={0: fc(1, 5)})
        assert all(a.target is None for a in plays_cat(d)), sid
        ev = apply_action(d, plays_cat(d)[0])
        assert not of(ev, EffectPlayed), sid


# ---- alvo aliado nunca inclui o proprio Espirito (carta sintetica: nenhum Espirito real usa)
def espirito_aliado() -> Card:
    return Card(kind="special", ref="espirito-teste", name="Espirito de Teste", cost=1,
                atk=1, hp=1,
                actions=({"tipo": "cura", "alvo": "aliado_escolhido", "valor": 2},))


def test_ao_entrar_aliado_sem_outro_gato_perde_o_efeito(content):
    d = duel(content, player_hand=[espirito_aliado()], player_energy=1)
    acoes = plays_cat(d)
    assert acoes and all(a.target is None for a in acoes)
    apply_action(d, acoes[0])
    assert me(d).field[acoes[0].slot] is not None


def test_ao_entrar_aliado_nao_inclui_o_proprio_espirito(content):
    d = duel(content, player_hand=[espirito_aliado()], player_energy=1,
             player_field={0: fc(2, 1, hp_max=5)})
    alvos = {a.target for a in plays_cat(d)}
    assert alvos == {("slot", 0)}
    apply_action(d, PlayCat(0, 3, ("slot", 0)))
    assert me(d).field[0].hp == 3
    with pytest.raises(IllegalAction):
        d2 = duel(content, player_hand=[espirito_aliado()], player_energy=1,
                  player_field={0: fc(2, 1, hp_max=5)})
        apply_action(d2, PlayCat(0, 3, ("slot", 3)))      # o proprio slot de entrada


# ---- keywords dos Espiritos compostos
def test_mestre_das_garras_entra_e_ataca_logo_com_dano_dobrado(content):
    d = duel(content, player_hand=[sp(content, "mestre-das-garras")], player_energy=4)
    apply_action(d, PlayCat(0, 0))
    assert Attack(0, ("leader",)) in legal_actions(d)          # Investida
    apply_action(d, Attack(0, ("leader",)))
    assert opp(d).leader_hp == 12                                # Primeira Patada: 4 x 2


def test_mestre_das_garras_so_dobra_o_primeiro_ataque(content):
    d = duel(content, player_hand=[sp(content, "mestre-das-garras")], player_energy=4)
    apply_action(d, PlayCat(0, 0))
    apply_action(d, Attack(0, ("leader",)))
    assert Attack(0, ("leader",)) not in legal_actions(d)       # ja atacou neste turno
    apply_action(d, EndTurn())
    apply_action(d, EndTurn())
    apply_action(d, Attack(0, ("leader",)))
    assert opp(d).leader_hp == 8                                 # 12 - 4 (sem dobro)


def test_pelo_de_aco_provoca_e_se_regenera(content):
    d = duel(content, player_hand=[sp(content, "pelo-de-aco")], player_energy=4,
             player_field={4: fc(1, 1)})
    apply_action(d, PlayCat(0, 0))
    apply_action(d, EndTurn())
    # turno do inimigo: so pode atacar o Provocar, nao o outro gato nem o Lider
    d.sides["enemy"].field[0] = fc(3, 9)
    assert attack_targets(d, 0) == [("slot", 0)]
    apply_action(d, Attack(0, ("slot", 0)))
    assert me(d).field[0].hp == 5                                # 8 - 3
    apply_action(d, EndTurn())                                   # volta ao jogador
    apply_action(d, EndTurn())                                   # fim do turno: Robusto
    assert me(d).field[0].hp == 6


def test_pelo_de_aco_robusto_nao_passa_do_maximo(content):
    d = duel(content, player_hand=[sp(content, "pelo-de-aco")], player_energy=4)
    apply_action(d, PlayCat(0, 0))
    apply_action(d, EndTurn())
    apply_action(d, EndTurn())
    apply_action(d, EndTurn())
    assert me(d).field[0].hp == 8
