"""Inimigos reais, IA com efeitos, impasse com cartas de efeito e determinismo (T3.3).

Fonte: CONTRATOS 1.8 e 2.3/2.4, proposta docs/propostas/2026-10-27-conteudo-fase3.md
(secoes 3 e 4.7). Escrito a partir das regras, nao do codigo do core.
"""
from __future__ import annotations

import json
from pathlib import Path
from random import Random

import pytest

from core.ai import choose_action
from core.duel import (apply_action, card_from_effect, card_from_special, enemy_deck_spec,
                       is_over, legal_actions, new_duel_vs_enemy, view)
from core.types import (Attack, Attacked, Card, DeckSpec, Deadlock, DuelEnded, EffectPlayed,
                        EndTurn, LeaderHealed, PlayCat, PlayEffect, TurnStarted)
from core.cats import roll_cat
from duel_helpers import deck_spec, duel, fc, load, mk

DATA = Path(__file__).resolve().parent.parent / "data"
MAX_ACOES = 3000

LIDER_HP = {"tonho-sem-sorte": 20, "irmaos-pimenta": 20, "berenice-da-matilha": 22,
            "madame-fifi-pelucia": 25}
TIPO = {"tonho-sem-sorte": "batalha", "irmaos-pimenta": "batalha",
        "berenice-da-matilha": "elite", "madame-fifi-pelucia": "chefe"}


@pytest.fixture(scope="module")
def content():
    return load()


def of(events, kind):
    return [e for e in events if isinstance(e, kind)]


def eff(content, eid):
    return card_from_effect(content, eid)


def sp(content, sid):
    return card_from_special(content, sid)


def deck_com_efeitos(content, seed: int) -> DeckSpec:
    """Deck do jogador de 12: 6 gatos + 3 efeitos + 3 Espiritos sorteados com a seed."""
    rng = Random(seed)
    efs = rng.sample(sorted(content.effects), 3)
    sps = rng.sample(sorted(content.specials), 3)
    return DeckSpec(cats=[roll_cat(content, rng) for _ in range(6)],
                    cards=[eff(content, e) for e in efs] + [sp(content, s) for s in sps])


def joga_ia_vs_ia(d, seed: int, coleta: list | None = None) -> int:
    """IA dos dois lados; confere que cada acao e legal. Devolve o numero de acoes."""
    rng = Random(seed)
    passos = 0
    while is_over(d) is None and passos < MAX_ACOES:
        acao = choose_action(d, d.turn_side, rng)
        assert acao in legal_actions(d), (seed, passos, acao)
        ev = apply_action(d, acao)
        if coleta is not None:
            coleta.extend(ev)
        passos += 1
    return passos


# ============================================================ 3. inimigos
def test_ha_4_inimigos_com_os_ids_e_tipos_esperados(content):
    assert set(content.enemies) == set(LIDER_HP)
    for eid, tipo in TIPO.items():
        assert content.enemies[eid]["tipo"] == tipo


@pytest.mark.parametrize("eid", sorted(LIDER_HP))
def test_deck_do_inimigo_tem_12_cartas(content, eid):
    spec = enemy_deck_spec(content, eid, Random(1))
    assert len(spec.cats) + len(spec.cards) == 12
    esperado = sum(e["qtd"] for e in json.loads((DATA / "enemies.json").read_text(
        encoding="utf-8"))["enemies"] if e["id"] == eid for e in e["deck"])
    assert esperado == 12


@pytest.mark.parametrize("eid", sorted(LIDER_HP))
def test_duelo_contra_inimigo_comeca_com_deck_de_12_e_lider_correto(content, eid):
    d = new_duel_vs_enemy(content, deck_spec(content, 5), eid, Random(5), player_first=True)
    v = view(d, "player")
    assert v.opponent.hand_count + v.opponent.deck_count == 12
    assert v.opponent.leader_hp == LIDER_HP[eid] == v.opponent.leader_hp_max
    assert v.me.leader_hp == 20
    assert v.me.hand_count + v.me.deck_count == 12


def test_inimigo_inexistente_levanta_erro(content):
    with pytest.raises((KeyError, ValueError)):
        new_duel_vs_enemy(content, deck_spec(content, 1), "nao-existe", Random(1),
                          player_first=True)


@pytest.mark.parametrize("eid", sorted(LIDER_HP))
def test_ia_vs_ia_joga_duelos_inteiros_sem_travar_e_sem_violar_regras(content, eid):
    terminaram = 0
    for seed in range(8):
        d = new_duel_vs_enemy(content, deck_com_efeitos(content, seed), eid, Random(seed))
        joga_ia_vs_ia(d, seed)
        terminaram += is_over(d) is not None
    if eid != "madame-fifi-pelucia":
        assert terminaram == 8
    # Chefe: ha proposta pendente (impasse com a cura); aqui so se exige nao violar regras.


@pytest.mark.parametrize("eid", sorted(LIDER_HP))
def test_ia_vs_ia_com_deck_comum_contra_inimigo_real(content, eid):
    for seed in range(8):
        d = new_duel_vs_enemy(content, deck_spec(content, seed + 100), eid, Random(seed),
                              player_first=bool(seed % 2))
        joga_ia_vs_ia(d, seed)
        if eid != "madame-fifi-pelucia":
            assert is_over(d) in ("player", "enemy")


def test_energia_e_maos_respeitam_limites_durante_duelo_completo(content):
    rules = content.rules["duel"]
    d = new_duel_vs_enemy(content, deck_com_efeitos(content, 3), "berenice-da-matilha", Random(3))
    rng = Random(3)
    for _ in range(MAX_ACOES):
        if is_over(d) is not None:
            break
        apply_action(d, choose_action(d, d.turn_side, rng))
        for lado in ("player", "enemy"):
            s = view(d, lado).me
            assert 0 <= s.energy <= rules["energy_cap"]
            assert s.hand_count <= rules["hand_max"]
            assert s.leader_hp <= s.leader_hp_max


# ---- Banho de Espuma
def test_chefe_traz_a_regra_banho_de_espuma(content):
    d = new_duel_vs_enemy(content, deck_spec(content, 1), "madame-fifi-pelucia", Random(1),
                          player_first=True)
    regra = view(d, "player").opponent.rule
    assert regra["id"] == "banho-de-espuma"
    assert view(d, "player").me.rule is None


def duelo_chefe(content, hp_chefe: int, hp_jogador: int = 20):
    d = new_duel_vs_enemy(content, deck_spec(content, 1), "madame-fifi-pelucia", Random(1),
                          player_first=True)
    d.sides["enemy"].leader_hp = hp_chefe          # preparacao do cenario
    d.sides["player"].leader_hp = hp_jogador
    return d


def test_banho_de_espuma_cura_1_no_inicio_do_turno_do_chefe(content):
    d = duelo_chefe(content, 20)
    ev = apply_action(d, EndTurn())                # comeca o turno do chefe
    assert view(d, "player").opponent.leader_hp == 21
    cura = of(ev, LeaderHealed)
    assert len(cura) == 1 and cura[0].side == "enemy" and cura[0].amount == 1
    # depois do inicio do turno dele
    tipos = [type(e) for e in ev]
    assert tipos.index(TurnStarted) < tipos.index(LeaderHealed)


def test_banho_de_espuma_nao_passa_do_maximo_25(content):
    d = duelo_chefe(content, 25)
    ev = apply_action(d, EndTurn())
    assert view(d, "player").opponent.leader_hp == 25
    assert not of(ev, LeaderHealed)
    d = duelo_chefe(content, 24)
    apply_action(d, EndTurn())
    assert view(d, "player").opponent.leader_hp == 25


def test_banho_de_espuma_cura_a_cada_turno_do_chefe(content):
    d = duelo_chefe(content, 10)
    for esperado in (11, 12):
        apply_action(d, EndTurn())                 # turno do chefe: cura
        assert view(d, "player").opponent.leader_hp == esperado
        apply_action(d, EndTurn())                 # volta ao jogador


def test_banho_de_espuma_nao_vale_para_o_jogador(content):
    d = duelo_chefe(content, 25, hp_jogador=15)
    apply_action(d, EndTurn())                     # turno do chefe
    ev = apply_action(d, EndTurn())                # volta ao jogador
    assert view(d, "player").me.leader_hp == 15
    assert not [e for e in of(ev, LeaderHealed) if e.side == "player"]


def test_inimigo_sem_regra_propria_nao_se_cura_no_inicio_do_turno(content):
    d = new_duel_vs_enemy(content, deck_spec(content, 1), "tonho-sem-sorte", Random(1),
                          player_first=True)
    d.sides["enemy"].leader_hp = 10
    ev = apply_action(d, EndTurn())
    assert view(d, "player").opponent.leader_hp == 10 and not of(ev, LeaderHealed)


def test_regra_do_chefe_so_vale_no_turno_proprio_no_jogador_first_false(content):
    # chefe comeca: o primeiro turno dele tambem aciona o gatilho
    d = new_duel_vs_enemy(content, deck_spec(content, 1), "madame-fifi-pelucia", Random(1),
                          player_first=False)
    assert d.turn_side == "enemy"
    assert view(d, "player").opponent.leader_hp <= 25


# ============================================================ 4. IA com efeitos
def turno_da_ia(d, side, rng_seed=0, limite=60):
    rng = Random(rng_seed)
    acoes, eventos = [], []
    for _ in range(limite):
        a = choose_action(d, side, rng)
        assert a in legal_actions(d)
        acoes.append(a)
        eventos += apply_action(d, a)
        if isinstance(a, EndTurn) or is_over(d) is not None:
            break
    return acoes, eventos


def test_ia_cura_gato_abaixo_da_metade_do_hp(content):
    d = duel(content, turn_side="enemy", enemy_hand=[eff(content, "lambida-curativa")],
             enemy_energy=1, enemy_field={0: fc(3, 1, hp_max=6), 1: fc(3, 6)},
             player_field={0: fc(1, 20)})
    assert choose_action(d, "enemy", Random(0)) == PlayEffect(0, ("slot", 0))


def test_ia_nao_cura_gato_acima_da_metade(content):
    d = duel(content, turn_side="enemy", enemy_hand=[eff(content, "lambida-curativa")],
             enemy_energy=1, enemy_field={0: fc(3, 5, hp_max=6)}, player_field={0: fc(1, 20)})
    assert not isinstance(choose_action(d, "enemy", Random(0)), PlayEffect)


def test_ia_cura_lider_abaixo_da_metade(content):
    d = duel(content, turn_side="enemy", enemy_hand=[eff(content, "soneca-no-sol")],
             enemy_energy=2, enemy_leader_hp=8, enemy_field={0: fc(1, 3)},
             player_field={0: fc(1, 20)})
    assert choose_action(d, "enemy", Random(0)) == PlayEffect(0, ("leader",))


def test_ia_nao_cura_lider_com_vida_cheia(content):
    d = duel(content, turn_side="enemy", enemy_hand=[eff(content, "soneca-no-sol")],
             enemy_energy=2, enemy_field={0: fc(1, 3)}, player_field={0: fc(1, 20)})
    assert not isinstance(choose_action(d, "enemy", Random(0)), PlayEffect)


def test_ia_usa_dano_no_gato_inimigo_que_consegue_matar(content):
    d = duel(content, turn_side="enemy", enemy_hand=[eff(content, "arranhao-certeiro")],
             enemy_energy=2, enemy_field={0: fc(1, 3)}, player_field={0: fc(2, 3), 1: fc(2, 9)})
    assert choose_action(d, "enemy", Random(0)) == PlayEffect(0, ("slot", 0))


def test_ia_nao_gasta_dano_em_gato_que_nao_morre(content):
    d = duel(content, turn_side="enemy", enemy_hand=[eff(content, "arranhao-certeiro")],
             enemy_energy=2, enemy_field={0: fc(1, 3)}, player_field={0: fc(2, 9)})
    assert not isinstance(choose_action(d, "enemy", Random(0)), PlayEffect)


def test_ia_usa_bote_quando_e_letal_mesmo_com_provocar(content):
    d = duel(content, turn_side="enemy", enemy_hand=[eff(content, "bote-no-lider")],
             enemy_energy=3, player_leader_hp=4, enemy_field={0: fc(1, 3)},
             player_field={0: fc(1, 20, kw=("provocar",))})
    assert choose_action(d, "enemy", Random(0)) == PlayEffect(0, ("leader",))


def test_ia_nao_usa_bote_primeiro_quando_nao_e_letal(content):
    d = duel(content, turn_side="enemy", enemy_hand=[eff(content, "bote-no-lider")],
             enemy_energy=3, player_leader_hp=5, enemy_field={0: fc(1, 3)},
             player_field={0: fc(1, 20)})
    assert not isinstance(choose_action(d, "enemy", Random(0)), PlayEffect)


def test_ia_joga_gato_antes_de_comprar(content):
    d = duel(content, turn_side="enemy",
             enemy_hand=[eff(content, "petisco-surpresa"), mk(2, 2, cost=2, name="g")],
             enemy_deck=[mk(1, 1, name="x")], enemy_energy=3)
    assert isinstance(choose_action(d, "enemy", Random(0)), PlayCat)


def test_ia_compra_quando_sobra_energia_e_a_mao_aceita(content):
    d = duel(content, turn_side="enemy", enemy_hand=[eff(content, "petisco-surpresa")],
             enemy_deck=[mk(1, 1, name="x")], enemy_energy=3)
    acoes, ev = turno_da_ia(d, "enemy")
    assert any(isinstance(a, PlayEffect) for a in acoes)
    assert acoes[-1] == EndTurn()


def test_ia_usa_energia_para_destravar_carta_da_mao(content):
    d = duel(content, turn_side="enemy",
             enemy_hand=[eff(content, "cochilo-revigorante"), mk(3, 3, cost=3, name="caro")],
             enemy_energy=2)
    acoes, _ = turno_da_ia(d, "enemy")
    assert isinstance(acoes[0], PlayEffect)
    assert any(isinstance(a, PlayCat) for a in acoes)


def test_ia_usa_buff_antes_de_atacar_com_o_gato_beneficiado(content):
    d = duel(content, turn_side="enemy", enemy_hand=[eff(content, "rugido-de-guerra")],
             enemy_energy=1, enemy_field={0: fc(2, 3)}, player_field={0: fc(1, 3)})
    acoes, ev = turno_da_ia(d, "enemy")
    iefeito = next(i for i, a in enumerate(acoes) if isinstance(a, PlayEffect))
    iataque = next(i for i, a in enumerate(acoes) if isinstance(a, Attack))
    assert iefeito < iataque and acoes[iefeito].target == ("slot", 0)
    assert acoes[iataque].attacker_slot == 0


def test_ia_nao_usa_buff_em_gato_que_nao_pode_atacar(content):
    d = duel(content, turn_side="enemy", enemy_hand=[eff(content, "rugido-de-guerra")],
             enemy_energy=1, enemy_field={0: fc(2, 3, ready=False)},
             player_field={0: fc(1, 3)})
    acoes, _ = turno_da_ia(d, "enemy")
    assert not any(isinstance(a, PlayEffect) for a in acoes)


@pytest.mark.parametrize("seed", range(10))
def test_ia_nunca_sai_de_legal_actions_com_efeitos_e_espiritos_nos_dois_lados(content, seed):
    d = new_duel_vs_enemy(content, deck_com_efeitos(content, seed + 50), "irmaos-pimenta",
                          Random(seed))
    rng_a, rng_b = Random(seed), Random(seed + 1)
    for _ in range(MAX_ACOES):
        if is_over(d) is not None:
            break
        rng = rng_a if d.turn_side == "player" else rng_b
        a = choose_action(d, d.turn_side, rng)
        assert a in legal_actions(d)
        apply_action(d, a)
    assert is_over(d) is not None


def test_ia_usa_efeitos_de_verdade_em_duelos_completos(content):
    usados = 0
    for seed in range(10):
        d = new_duel_vs_enemy(content, deck_com_efeitos(content, seed), "tonho-sem-sorte",
                              Random(seed))
        ev: list = []
        joga_ia_vs_ia(d, seed, ev)
        usados += len(of(ev, EffectPlayed))
    assert usados > 0


# ============================================================ 5. impasse com efeitos
# Decisao do core, DUVIDA ABERTA para o Renatho: o gatilho do impasse conta so gatos e
# Especiais; cartas de efeito que sobram na mao/deck nao seguram o impasse.
def impasse_com_efeito(content, mao_p, mao_e, deck_p=None, deck_e=None, seed=1):
    d = duel(content, seed=seed, player_hand=mao_p, enemy_hand=mao_e, player_deck=deck_p,
             enemy_deck=deck_e,
             player_field={0: fc(3, 3), 1: fc(2, 1)}, enemy_field={0: fc(3, 3), 1: fc(2, 1)})
    ev = apply_action(d, Attack(0, ("slot", 0)))
    ev += apply_action(d, Attack(1, ("slot", 1)))
    return d, ev


def test_efeito_restante_na_mao_nao_segura_o_impasse(content):
    # (decisao do core, duvida aberta) efeito sem alvo possivel: nao e jogavel de qualquer forma
    d, ev = impasse_com_efeito(content, [eff(content, "arranhao-certeiro")],
                               [eff(content, "lambida-curativa")])
    assert of(ev, Deadlock)
    assert is_over(d) in ("player", "enemy")


def test_efeito_restante_no_deck_nao_segura_o_impasse(content):
    d, ev = impasse_com_efeito(content, [], [], deck_p=[eff(content, "petisco-surpresa")],
                               deck_e=[eff(content, "cochilo-revigorante")])
    assert of(ev, Deadlock)


def test_efeito_na_mao_nao_entra_no_poder_do_lider(content):
    # poder = media de ATK dos gatos do deck inicial: (3+2)/2 -> 3 e o mesmo para o inimigo;
    # contando o efeito (ATK 0) cairia para 2.
    _, ev = impasse_com_efeito(content, [eff(content, "soneca-no-sol")],
                               [eff(content, "soneca-no-sol")])
    assert of(ev, Deadlock)[0].powers == {"player": 3, "enemy": 3}


def test_especial_jogavel_na_mao_ainda_segura_o_impasse(content):
    d, ev = impasse_com_efeito(content, [sp(content, "sombra-miuda")], [])
    assert not of(ev, Deadlock)
    assert is_over(d) is None


def test_especial_no_deck_ainda_segura_o_impasse(content):
    d, ev = impasse_com_efeito(content, [], [], deck_e=[sp(content, "velha-dos-novelos")])
    assert not of(ev, Deadlock)
    assert is_over(d) is None


# ============================================================ 7. determinismo
def log_completo(content, eid: str, seed: int) -> list:
    d = new_duel_vs_enemy(content, deck_com_efeitos(content, seed), eid, Random(seed))
    ev: list = []
    joga_ia_vs_ia(d, seed, ev)
    return ev


@pytest.mark.parametrize("eid", ["tonho-sem-sorte", "irmaos-pimenta", "berenice-da-matilha"])
def test_mesma_seed_gera_o_mesmo_log_de_eventos_com_efeitos(content, eid):
    assert log_completo(content, eid, 7) == log_completo(content, eid, 7)


def test_mesma_seed_chefe_primeiros_eventos_iguais(content):
    a = log_completo(content, "madame-fifi-pelucia", 4)
    b = log_completo(content, "madame-fifi-pelucia", 4)
    assert a == b


def test_seeds_diferentes_dao_logs_diferentes(content):
    assert log_completo(content, "irmaos-pimenta", 1) != log_completo(content, "irmaos-pimenta", 2)


def test_ordem_dos_eventos_de_um_duelo_termina_com_duelended(content):
    ev = log_completo(content, "tonho-sem-sorte", 3)
    assert isinstance(ev[-1], DuelEnded)
    assert len(of(ev, DuelEnded)) == 1
