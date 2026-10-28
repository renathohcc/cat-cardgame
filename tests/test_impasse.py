"""Testes do impasse (desempate). Fonte: docs/propostas/2026-10-27-desempate-impasse.md e CONTRATOS 2.3."""
from __future__ import annotations

import pytest

from core.duel import apply_action, is_over
from core.types import Attack, Deadlock, DuelEnded, LeaderDamaged
from duel_helpers import duel, fc, load, mk


@pytest.fixture(scope="module")
def content():
    return load()


def impasse(content, p_hp=20, e_hp=20, seed=1, p_atks=(3, 2), e_atks=(3, 1)):
    """Cada lado tem 2 gatos que se destroem trocando; ao fim ninguem tem nada."""
    d = duel(content, seed=seed, player_leader_hp=p_hp, enemy_leader_hp=e_hp,
             player_field={0: fc(p_atks[0], 3), 1: fc(p_atks[1], 1)},
             enemy_field={0: fc(e_atks[0], 3), 1: fc(e_atks[1], 1)})
    ev = apply_action(d, Attack(0, ("slot", 0)))
    ev += apply_action(d, Attack(1, ("slot", 1)))
    return d, ev


def test_impasse_emite_deadlock_e_termina_com_vencedor(content):
    d, ev = impasse(content)
    assert any(isinstance(e, Deadlock) for e in ev)
    assert any(isinstance(e, DuelEnded) for e in ev)
    assert is_over(d) in ("player", "enemy")


def test_poder_do_lider_e_a_media_de_atk_do_deck_inicial_arredondada_meio_para_cima(content):
    _, ev = impasse(content)
    dl = next(e for e in ev if isinstance(e, Deadlock))
    # jogador: (3+2)/2 = 2,5 -> 3 ; inimigo: (3+1)/2 = 2 -> 2
    assert dl.powers == {"player": 3, "enemy": 2}


def test_dano_de_cada_ataque_e_poder_mais_variacao_de_menos_1_a_mais_1(content):
    for seed in range(20):
        _, ev = impasse(content, seed=seed)
        dl = next(e for e in ev if isinstance(e, Deadlock))
        # LeaderDamaged.side = lado ferido; quem causa e o outro
        for e in (x for x in ev if isinstance(x, LeaderDamaged)):
            atacante = "enemy" if e.side == "player" else "player"
            assert dl.powers[atacante] - 1 <= e.amount <= dl.powers[atacante] + 1
            assert e.amount >= 1


def test_dano_minimo_1_quando_poder_menos_variacao_seria_zero_ou_menor(content):
    for seed in range(20):
        d = duel(content, seed=seed, player_field={0: fc(1, 1)}, enemy_field={0: fc(1, 1)})
        ev = apply_action(d, Attack(0, ("slot", 0)))
        assert all(e.amount >= 1 for e in ev if isinstance(e, LeaderDamaged))
        assert is_over(d) is not None


def test_comeca_atacando_o_lider_de_menor_hp(content):
    d, ev = impasse(content, p_hp=8, e_hp=15)
    dl = next(e for e in ev if isinstance(e, Deadlock))
    assert dl.first == "player"
    primeiro = next(e for e in ev if isinstance(e, LeaderDamaged))
    assert primeiro.side == "enemy"   # o jogador (menor HP) ataca o Lider inimigo


def test_comeca_o_inimigo_quando_ele_tem_menos_hp(content):
    _, ev = impasse(content, p_hp=15, e_hp=8)
    assert next(e for e in ev if isinstance(e, Deadlock)).first == "enemy"
    assert next(e for e in ev if isinstance(e, LeaderDamaged)).side == "player"


def test_lideres_se_atacam_alternando_ate_um_zerar(content):
    _, ev = impasse(content, p_hp=20, e_hp=20)
    lados = [e.side for e in ev if isinstance(e, LeaderDamaged)]
    assert len(lados) >= 2
    assert all(a != b for a, b in zip(lados, lados[1:]))
    zerados = [e for e in ev if isinstance(e, LeaderDamaged) and e.hp_left <= 0]
    assert len(zerados) == 1 and zerados[0] is [e for e in ev if isinstance(e, LeaderDamaged)][-1]


def test_vencedor_e_quem_sobrou_com_hp_positivo(content):
    for seed in range(30):
        d, _ = impasse(content, seed=seed)
        w = is_over(d)
        perdedor = "enemy" if w == "player" else "player"
        assert d.sides[perdedor].leader_hp <= 0
        assert d.sides[w].leader_hp > 0


def test_hp_igual_o_dado_do_duelo_decide_e_os_dois_lados_podem_comecar(content):
    primeiros = set()
    for seed in range(40):
        _, ev = impasse(content, seed=seed)
        primeiros.add(next(e for e in ev if isinstance(e, Deadlock)).first)
    assert primeiros == {"player", "enemy"}


def test_impasse_com_mesma_seed_e_deterministico(content):
    _, a = impasse(content, seed=9)
    _, b = impasse(content, seed=9)
    pick = lambda ev: [e for e in ev if isinstance(e, (Deadlock, LeaderDamaged, DuelEnded))]
    assert pick(a) == pick(b)


# ---------------------------------------------------------------- quando NAO dispara
def test_nao_dispara_se_um_lado_ainda_tem_carta_no_deck(content):
    d = duel(content, player_field={0: fc(3, 3)}, enemy_field={0: fc(3, 3)},
             enemy_deck=[mk(1, 1)])
    ev = apply_action(d, Attack(0, ("slot", 0)))
    assert not any(isinstance(e, Deadlock) for e in ev)
    assert is_over(d) is None


def test_nao_dispara_se_um_lado_ainda_tem_carta_na_mao(content):
    d = duel(content, player_field={0: fc(3, 3)}, enemy_field={0: fc(3, 3)},
             player_hand=[mk(1, 1)])
    ev = apply_action(d, Attack(0, ("slot", 0)))
    assert not any(isinstance(e, Deadlock) for e in ev)
    assert is_over(d) is None


def test_nao_dispara_se_um_gato_continua_em_campo(content):
    d = duel(content, player_field={0: fc(3, 3), 1: fc(1, 9)}, enemy_field={0: fc(3, 3)})
    ev = apply_action(d, Attack(0, ("slot", 0)))
    assert not any(isinstance(e, Deadlock) for e in ev)
    assert is_over(d) is None


def test_nao_dispara_com_gatos_em_campo_dos_dois_lados(content):
    d = duel(content, player_field={0: fc(1, 9)}, enemy_field={0: fc(1, 9)})
    ev = apply_action(d, Attack(0, ("slot", 0)))
    assert not any(isinstance(e, Deadlock) for e in ev)


def test_nao_dispara_com_mao_cheia_de_cartas_mesmo_sem_gatos_em_campo(content):
    d = duel(content, player_hand=[mk(1, 1)], enemy_hand=[mk(1, 1)], player_energy=3)
    assert is_over(d) is None


def test_impasse_disparado_na_criacao_do_duelo_com_decks_vazios(content):
    from random import Random
    from core.duel import new_duel
    from core.types import DeckSpec
    d = new_duel(content, Random(4), DeckSpec(cats=[]), DeckSpec(cats=[]), player_first=True)
    assert any(isinstance(e, Deadlock) for e in d.log)
    assert is_over(d) in ("player", "enemy")
    assert any(isinstance(e, DuelEnded) for e in d.log)
