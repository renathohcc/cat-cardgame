"""Prévia de ataque e de carta do core (T12.5, a partir de reports/T12.1-preview.md).

Contrato: `preview_attack`/`preview_card` devolvem exatamente o efeito direto de `apply_action`
com a mesma ação, sem tocar no duelo nem no RNG. Os testes comparam a prévia com `apply_action`
numa CÓPIA (usando só a API pública e as regras do GDD), nunca com o código interno.
"""
from __future__ import annotations

import copy
from random import Random

import pytest

from core.duel import (apply_action, card_from_effect, card_from_special, is_over,
                       legal_actions, preview_attack, preview_card, view)
from core.types import (Attack, Deadlock, DuelEnded, EndTurn, FieldCat, IllegalAction,
                        LeaderDamaged, PlayCat, PlayEffect,
                        Preview)
from duel_helpers import duel, fc, load, mk

PLAYER, ENEMY = "player", "enemy"
KWS = ("provocar", "investida", "primeira-patada", "robusto")
EFFECTS = ("arranhao-certeiro", "bote-no-lider", "lambida-curativa", "soneca-no-sol",
           "rugido-de-guerra", "petisco-surpresa", "farejar-a-despensa", "cochilo-revigorante")
SPECIALS = ("sombra-miuda", "velha-dos-novelos", "soneca-ancestral", "trovao-amarelo",
            "guardiao-bigodudo", "mestre-das-garras", "pelo-de-aco")


@pytest.fixture(scope="module")
def content():
    return load()


def clone(d):
    """Cópia independente do duelo (o `content` é compartilhado: é só leitura)."""
    return copy.deepcopy(d, {id(d.content): d.content})


def fingerprint(d):
    return (d.sides, d.turn_side, d.winner, len(d.log), d.stall_base, d.stall_half,
            d.stall_rounds, d.stall_triggered, d.rng.getstate())


def effect_of(pv: Preview):
    return pv.cats, pv.leaders, pv.winner, pv.deadlock


def preview_of(d, a) -> Preview | None:
    if isinstance(a, Attack):
        return preview_attack(d, a.attacker_slot, a.target)
    if isinstance(a, PlayEffect):
        return preview_card(d, a.hand_index, a.target)
    return preview_card(d, a.hand_index, a.target, a.slot)


# ------------------------------------------------------------ gerador de cenários
def rand_fc(rng: Random) -> FieldCat:
    hp_max = rng.randint(1, 8)
    kw = tuple(k for k in KWS if rng.random() < 0.2)
    c = fc(rng.randint(1, 6), rng.randint(1, hp_max), hp_max, kw, ready=rng.random() < 0.85)
    c.used_first_strike = rng.random() < 0.3
    return c


def rand_scenario(content, rng: Random):
    def field():
        return {s: rand_fc(rng) for s in range(5) if rng.random() < 0.5}

    def hand():
        out = []
        for _ in range(rng.randint(1, 5)):
            r = rng.random()
            if r < 0.4:
                out.append(mk(rng.randint(1, 5), rng.randint(1, 6), cost=rng.randint(1, 3)))
            elif r < 0.75:
                out.append(card_from_effect(content, rng.choice(EFFECTS)))
            else:
                out.append(card_from_special(content, rng.choice(SPECIALS)))
        return out

    return duel(content, seed=rng.randrange(10**6), turn_side=rng.choice((PLAYER, ENEMY)),
                player_hand=hand(), enemy_hand=hand(), player_deck=[mk(1, 1)] * 3,
                enemy_deck=[mk(1, 1)] * 3, player_field=field(), enemy_field=field(),
                player_energy=7, enemy_energy=7,
                player_leader_hp=rng.randint(1, 20), enemy_leader_hp=rng.randint(1, 20))


# ------------------------------------------------------------ igualdade prévia x real
def check_equal_to_real(d, a, pv: Preview) -> None:
    before = view(d, PLAYER)
    real = clone(d)
    ev = apply_action(real, a)
    after = view(real, PLAYER)
    assert pv.deadlock == any(isinstance(e, Deadlock) for e in ev), (a, pv)
    for side, b_side, a_side in ((PLAYER, before.me, after.me), (ENEMY, before.opponent, after.opponent)):
        for slot, b in enumerate(b_side.field):
            if b is None:
                continue                       # slot vazio: gato que entra não é previsto
            n = a_side.field[slot]
            cp = pv.cat(side, slot)
            changed = n is None or (n.hp, n.atk) != (b.hp, b.atk)
            assert (cp is not None) == changed, (a, side, slot, pv)
            if cp is None:
                continue
            assert cp.hp_before == b.hp and cp.atk_before == b.atk
            assert cp.dies == (n is None)
            assert cp.hp_after == (0 if n is None else n.hp)
            if n is not None:
                assert cp.atk_after == n.atk
                assert cp.hp_after == cp.hp_before - cp.damage + cp.heal
            assert cp.hp_after >= 0
    if pv.deadlock:                            # a resolução do impasse é sorteada: só gatos e aviso
        return
    for side, b_side, a_side in ((PLAYER, before.me, after.me), (ENEMY, before.opponent, after.opponent)):
        lp = pv.leader(side)
        assert (lp is not None) == (a_side.leader_hp != b_side.leader_hp), (a, side, pv)
        if lp is not None:
            assert lp.hp_before == b_side.leader_hp
            assert lp.hp_after == a_side.leader_hp >= 0
    assert pv.winner == is_over(real)


def walk(content, seed: int, scenarios: int, steps: int) -> tuple[int, dict[str, int]]:
    """Confere a prévia de TODA ação legal em cada estado; avança com uma ação aleatória."""
    rng = Random(seed)
    checked, seen = 0, {"attack": 0, "effect": 0, "cat": 0, "dies": 0, "leader": 0, "first": 0}
    for _ in range(scenarios):
        d = rand_scenario(content, rng)
        for _ in range(steps):
            if d.winner is not None:
                break
            snap = fingerprint(d)
            legal = [a for a in legal_actions(d) if not isinstance(a, EndTurn)]
            for a in legal:
                pv = preview_of(d, a)
                assert pv is not None
                check_equal_to_real(d, a, pv)
                checked += 1
                seen["attack" if isinstance(a, Attack) else "effect" if isinstance(a, PlayEffect) else "cat"] += 1
                seen["dies"] += any(c.dies for c in pv.cats)
                seen["leader"] += bool(pv.leaders)
                if isinstance(a, Attack):
                    att = (d.sides[d.turn_side].field[a.attacker_slot])
                    seen["first"] += att.first_strike_available
            assert fingerprint(d) == snap            # prévia não altera duelo nem RNG
            pool = legal_actions(d)
            apply_action(d, rng.choice(pool))
    return checked, seen


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5, 6])
def test_previa_igual_ao_resultado_real_em_centenas_de_acoes(content, seed):
    checked, seen = walk(content, seed, scenarios=14, steps=3)
    assert checked >= 100
    assert seen["attack"] and seen["effect"] and seen["cat"]


def test_cobertura_da_varredura_inclui_mortes_lider_e_primeira_patada(content):
    total = {"dies": 0, "leader": 0, "first": 0}
    for seed in (11, 12, 13):
        _, seen = walk(content, seed, scenarios=14, steps=3)
        for k in total:
            total[k] += seen[k]
    assert all(v > 0 for v in total.values()), total


# ------------------------------------------------------------ regras de ataque (do GDD)
def test_ataque_a_gato_causa_atk_do_atacante_e_contra_golpe_do_defensor(content):
    d = duel(content, player_field={0: fc(3, 5)}, enemy_field={2: fc(2, 6)})
    pv = preview_attack(d, 0, ("slot", 2))
    alvo, atacante = pv.cat(ENEMY, 2), pv.cat(PLAYER, 0)
    assert (alvo.damage, alvo.hp_after, alvo.dies) == (3, 3, False)
    assert (atacante.damage, atacante.hp_after) == (2, 3)
    assert pv.leaders == ()


def test_primeira_patada_dobra_so_no_primeiro_ataque_e_contra_golpe_nao_dobra(content):
    d = duel(content, player_field={0: fc(3, 9, kw=("primeira-patada",))},
             enemy_field={0: fc(2, 20)})
    pv = preview_attack(d, 0, ("slot", 0))
    assert pv.cat(ENEMY, 0).damage == 6                  # 3 x 2
    assert pv.cat(PLAYER, 0).damage == 2                 # contra-golpe: ATK do defensor, sem dobrar
    apply_action(d, Attack(0, ("slot", 0)))
    d.sides[PLAYER].field[0].attacked = False            # novo ataque do mesmo gato (outro turno)
    d.sides[PLAYER].field[0].ready = True
    pv2 = preview_attack(d, 0, ("slot", 0))
    assert pv2.cat(ENEMY, 0).damage == 3                 # só o 1o ataque da vida dobra


def test_primeira_patada_ja_gasta_nao_dobra(content):
    gato = fc(4, 9, kw=("primeira-patada",))
    gato.used_first_strike = True
    d = duel(content, player_field={0: gato}, enemy_field={0: fc(1, 20)})
    assert preview_attack(d, 0, ("slot", 0)).cat(ENEMY, 0).damage == 4


def test_atacar_o_lider_nao_causa_dano_de_volta(content):
    d = duel(content, player_field={0: fc(3, 4)}, enemy_leader_hp=10)
    pv = preview_attack(d, 0, ("leader",))
    assert pv.cats == ()
    lp = pv.leader(ENEMY)
    assert (lp.damage, lp.hp_before, lp.hp_after) == (3, 10, 7)
    assert pv.leader(PLAYER) is None and pv.winner is None


def test_golpe_letal_no_lider_marca_vencedor_e_hp_zero(content):
    d = duel(content, player_field={0: fc(5, 2)}, enemy_leader_hp=3)
    pv = preview_attack(d, 0, ("leader",))
    assert pv.winner == PLAYER
    assert pv.leader(ENEMY).hp_after == 0 and pv.leader(ENEMY).damage == 5   # dano bruto passa do HP


def test_gato_que_morre_marca_caveira_com_hp_zero(content):
    d = duel(content, player_field={0: fc(4, 5)}, enemy_field={1: fc(1, 3)})
    cp = preview_attack(d, 0, ("slot", 1)).cat(ENEMY, 1)
    assert cp.dies and cp.hp_after == 0


def test_atacante_pode_morrer_no_contra_golpe(content):
    d = duel(content, player_field={0: fc(1, 2)}, enemy_field={0: fc(5, 9)})
    pv = preview_attack(d, 0, ("slot", 0))
    assert pv.cat(PLAYER, 0).dies and not pv.cat(ENEMY, 0).dies


def test_provocar_impede_prever_ataque_ao_lider_e_a_gato_sem_provocar(content):
    d = duel(content, player_field={0: fc(3, 3)},
             enemy_field={0: fc(1, 4, kw=("provocar",)), 1: fc(1, 4)})
    with pytest.raises(IllegalAction):
        preview_attack(d, 0, ("leader",))
    with pytest.raises(IllegalAction):
        preview_attack(d, 0, ("slot", 1))
    assert preview_attack(d, 0, ("slot", 0)).cat(ENEMY, 0).damage == 3


# ------------------------------------------------------------ cartas
def test_efeito_de_dano_em_gato_previsto(content):
    d = duel(content, player_hand=[card_from_effect(content, "arranhao-certeiro")],
             enemy_field={0: fc(1, 5)}, player_energy=3)
    cp = preview_card(d, 0, ("slot", 0)).cat(ENEMY, 0)
    assert (cp.damage, cp.hp_after, cp.dies) == (3, 2, False)


def test_efeito_sem_alvo_explicito_vai_para_o_lider(content):
    d = duel(content, player_hand=[card_from_effect(content, "bote-no-lider")],
             enemy_leader_hp=10, player_energy=3, enemy_field={0: fc(1, 4, kw=("provocar",))})
    pv = preview_card(d, 0)                               # target=None => Líder; ignora Provocar
    assert pv.leader(ENEMY).hp_after == 6 and pv.cats == ()


def test_buff_de_atk_aparece_em_atk_after_sem_mexer_no_hp(content):
    d = duel(content, player_hand=[card_from_effect(content, "rugido-de-guerra")],
             player_field={1: fc(2, 4)}, player_energy=2)
    cp = preview_card(d, 0, ("slot", 1)).cat(PLAYER, 1)
    assert (cp.atk_before, cp.atk_after, cp.hp_before, cp.hp_after) == (2, 4, 4, 4)
    assert cp.damage == 0 and cp.heal == 0 and not cp.dies


def test_cura_em_gato_respeita_o_teto_de_hp(content):
    d = duel(content, player_hand=[card_from_effect(content, "lambida-curativa")],
             player_field={0: fc(1, 5, hp_max=6)}, player_energy=2)
    cp = preview_card(d, 0, ("slot", 0)).cat(PLAYER, 0)
    assert (cp.heal, cp.hp_after) == (1, 6)               # cura 3, mas só cabe 1


def test_cura_no_lider_respeita_o_teto(content):
    d = duel(content, player_hand=[card_from_effect(content, "soneca-no-sol")], player_energy=3)
    teto = view(d, PLAYER).me.leader_hp_max
    d.sides[PLAYER].leader_hp = teto - 1
    lp = preview_card(d, 0).leader(PLAYER)
    assert (lp.heal, lp.hp_after) == (1, teto)


@pytest.mark.parametrize("efeito", ["petisco-surpresa", "farejar-a-despensa", "cochilo-revigorante"])
def test_efeitos_de_compra_e_energia_nao_mudam_gatos_nem_lideres(content, efeito):
    d = duel(content, player_hand=[card_from_effect(content, efeito)], player_energy=3,
             player_deck=[mk(1, 1), mk(1, 1)], player_field={0: fc(2, 2)}, enemy_field={0: fc(2, 2)})
    pv = preview_card(d, 0)
    assert pv.cats == () and pv.leaders == () and pv.winner is None


def test_espirito_com_dano_ao_entrar_prevê_o_alvo(content):
    d = duel(content, player_hand=[card_from_special(content, "trovao-amarelo")], player_energy=5,
             enemy_field={3: fc(1, 5)})
    alvo = [a for a in legal_actions(d) if isinstance(a, PlayCat) and a.target == ("slot", 3)]
    assert alvo
    a = alvo[0]
    pv = preview_card(d, 0, a.target, a.slot)
    assert pv.cat(ENEMY, 3).damage == 2
    # o slot escolhido não muda o resultado
    outro = [x for x in alvo if x.slot != a.slot][0]
    assert preview_card(d, 0, outro.target, outro.slot) == pv or \
        preview_card(d, 0, outro.target, outro.slot).cats == pv.cats


def test_espirito_sem_slot_pega_o_primeiro_jogavel(content):
    d = duel(content, player_hand=[card_from_special(content, "guardiao-bigodudo")], player_energy=5)
    legais = [a for a in legal_actions(d) if isinstance(a, PlayCat)]
    pv = preview_card(d, 0, legais[0].target)
    assert effect_of(pv) == effect_of(preview_card(d, 0, legais[0].target, legais[0].slot))


def test_espirito_sem_alvo_valido_ainda_gera_previa_coerente(content):
    d = duel(content, player_hand=[card_from_special(content, "trovao-amarelo")], player_energy=5)
    for a in (x for x in legal_actions(d) if isinstance(x, PlayCat)):
        check_equal_to_real(d, a, preview_of(d, a))


# ------------------------------------------------------------ pureza e ilegais
def test_previa_nao_altera_duelo_nem_consome_rng(content):
    d = duel(content, seed=9, player_field={0: fc(3, 3), 1: fc(2, 2)},
             enemy_field={0: fc(2, 2, kw=("provocar",))},
             player_hand=[card_from_effect(content, "arranhao-certeiro")], player_energy=4)
    snap = fingerprint(d)
    for _ in range(5):
        preview_attack(d, 0, ("slot", 0))
        preview_card(d, 0, ("slot", 0))
    assert fingerprint(d) == snap


def test_previa_nao_perturba_a_sequencia_do_rng(content):
    def build():
        return duel(content, seed=21, player_field={0: fc(3, 3)}, enemy_field={0: fc(2, 8)})
    a, b = build(), build()
    preview_attack(a, 0, ("slot", 0))
    ev_a, ev_b = apply_action(a, Attack(0, ("slot", 0))), apply_action(b, Attack(0, ("slot", 0)))
    assert ev_a == ev_b and a.rng.getstate() == b.rng.getstate()


def test_ataque_ilegal_levanta_illegal_action(content):
    d = duel(content, player_field={0: fc(3, 3), 1: fc(3, 3, ready=False)}, enemy_field={0: fc(1, 1)})
    for slot, alvo in ((2, ("slot", 0)),            # sem gato no slot
                       (1, ("slot", 0)),            # gato sem poder atacar
                       (0, ("slot", 4)),            # alvo vazio
                       (7, ("slot", 0))):           # slot inexistente
        with pytest.raises(IllegalAction):
            preview_attack(d, slot, alvo)


def test_carta_ilegal_levanta_illegal_action(content):
    d = duel(content, player_hand=[card_from_effect(content, "bote-no-lider"), mk(1, 1, cost=1)],
             player_energy=1, player_field={i: fc(1, 1) for i in range(5)})
    with pytest.raises(IllegalAction):
        preview_card(d, 0)                                  # sem energia
    with pytest.raises(IllegalAction):
        preview_card(d, 1, None, 0)                         # campo cheio


@pytest.mark.parametrize("idx", [99, 5, -1, -7])
def test_preview_card_com_indice_invalido_se_comporta_como_apply_action(content, idx):
    d = duel(content, player_hand=[mk(1, 1)], player_energy=3)
    with pytest.raises(IllegalAction):
        apply_action(clone(d), PlayEffect(idx))
    with pytest.raises(IllegalAction):
        preview_card(d, idx)


def test_duelo_encerrado_nao_aceita_previa(content):
    d = duel(content, player_field={0: fc(9, 3)}, enemy_leader_hp=1)
    apply_action(d, Attack(0, ("leader",)))
    assert d.winner == PLAYER
    with pytest.raises(IllegalAction):
        preview_attack(d, 0, ("leader",))
    with pytest.raises(IllegalAction):
        preview_card(d, 0)


# ------------------------------------------------------------ impasse
def impasse_duel(content, seed=1):
    return duel(content, seed=seed, player_leader_hp=20, enemy_leader_hp=20,
                player_field={0: fc(3, 3), 1: fc(2, 1)}, enemy_field={0: fc(3, 3), 1: fc(3, 1)})


def test_ataque_que_esvazia_o_campo_dos_dois_lados_dispara_impasse_na_previa(content):
    d = impasse_duel(content)
    apply_action(d, Attack(0, ("slot", 0)))                 # trocam e morrem (3x3 contra 3x3)
    pv = preview_attack(d, 1, ("slot", 1))                  # ultimos gatos: nenhum sobra
    assert pv.deadlock is True
    assert pv.cat(PLAYER, 1).dies and pv.cat(ENEMY, 1).dies
    assert pv.winner is None                                # o vencedor sai de um sorteio


def test_ataque_anterior_ao_impasse_nao_marca_deadlock(content):
    d = impasse_duel(content)
    assert preview_attack(d, 0, ("slot", 0)).deadlock is False


def test_previa_de_impasse_nao_consome_rng_e_o_real_resolve_depois(content):
    a, b = impasse_duel(content, seed=5), impasse_duel(content, seed=5)
    for d in (a, b):
        apply_action(d, Attack(0, ("slot", 0)))
    snap = fingerprint(a)
    pv = preview_attack(a, 1, ("slot", 1))
    assert pv.deadlock and fingerprint(a) == snap
    ev_a = apply_action(a, Attack(1, ("slot", 1)))
    ev_b = apply_action(b, Attack(1, ("slot", 1)))
    sorteio = lambda ev: [e for e in ev if isinstance(e, (Deadlock, LeaderDamaged, DuelEnded))]
    assert sorteio(ev_a) == sorteio(ev_b)                   # a prévia não alterou o sorteio
    assert a.rng.getstate() == b.rng.getstate()
    assert any(isinstance(e, Deadlock) for e in ev_a) and is_over(a) in (PLAYER, ENEMY)


def test_impasse_pelo_inimigo_tambem_e_previsto(content):
    d = duel(content, seed=3, turn_side=ENEMY, player_field={0: fc(2, 2)}, enemy_field={0: fc(2, 2)})
    pv = preview_attack(d, 0, ("slot", 0))
    assert pv.deadlock and pv.cat(PLAYER, 0).dies and pv.cat(ENEMY, 0).dies
