"""Testes da CLI: render, parse_command e play com entrada/saida injetadas."""
from __future__ import annotations

import io
from random import Random

import pytest

from core.cli import main, parse_command, play, render
from core.types import Attack, EndTurn, PlayCat
from duel_helpers import duel, fc, load, mk


@pytest.fixture(scope="module")
def content():
    return load()


def test_render_mostra_hp_dos_lideres_campo_e_mao(content):
    d = duel(content, player_leader_hp=17, enemy_leader_hp=13,
             player_hand=[mk(2, 3, cost=2, name="Zeca")],
             player_field={0: fc(4, 5)}, enemy_field={1: fc(1, 2)})
    txt = render(d)
    assert "13 HP" in txt and "17 HP" in txt
    assert "ATK 4" in txt and "HP 5/5" in txt
    assert "ATK 1" in txt and "HP 2/2" in txt
    assert "Zeca" in txt and "custo 2" in txt and "ATK 2" in txt and "HP 3" in txt


def test_render_mostra_estrelas_de_iv_da_mao_de_um_duelo_real(content):
    from core.cli import Roster, build_deck
    from core.duel import new_duel
    rng = Random(3)
    roster = Roster()
    p, e = build_deck(content, rng, "p", roster), build_deck(content, rng, "e", roster)
    d = new_duel(content, rng, p, e, True)
    assert "★" in render(d, "player", roster)


def test_render_avisa_mao_cheia_com_7_cartas(content):
    d = duel(content, player_hand=[mk(1, 1, name=f"g{i}") for i in range(7)])
    assert "Mão cheia" in render(d)


def test_render_nao_avisa_mao_cheia_com_6_cartas(content):
    d = duel(content, player_hand=[mk(1, 1, name=f"g{i}") for i in range(6)])
    assert "Mão cheia" not in render(d)


def test_parse_command_aceita_comandos_validos(content):
    d = duel(content, player_hand=[mk(1, 1, cost=1)], player_field={0: fc(2, 2)},
             enemy_field={0: fc(1, 1)})
    assert parse_command(d, "j 1 2") == ("action", PlayCat(0, 1))
    assert parse_command(d, "a 1 1") == ("action", Attack(0, ("slot", 0)))
    assert parse_command(d, "p") == ("action", EndTurn())
    assert parse_command(d, "?")[0] == "help"
    assert parse_command(d, "s")[0] == "quit"


def test_parse_command_ataque_ao_lider_com_l(content):
    d = duel(content, player_field={0: fc(2, 2)})
    assert parse_command(d, "a 1 l") == ("action", Attack(0, ("leader",)))


@pytest.mark.parametrize("linha", [
    "", "   ", "xyz", "j", "j 1", "j a b", "j 99 1", "j 1 99", "j 0 0", "j -1 1",
    "a", "a 1", "a x y", "a 9 1", "a 1 9", "a 1 l l", "\x00\xff", "j 1 1 1", "💥",
])
def test_parse_command_rejeita_lixo_sem_excecao(content, linha):
    d = duel(content, player_hand=[mk(1, 1, cost=1)])
    kind, val = parse_command(d, linha)
    assert kind == "error" and isinstance(val, str)


def test_parse_command_nao_altera_o_duelo(content):
    d = duel(content, player_hand=[mk(1, 1)])
    antes = (len(d.sides["player"].hand), d.sides["player"].energy, list(d.sides["player"].field))
    parse_command(d, "j 1 1")
    assert antes == (len(d.sides["player"].hand), d.sides["player"].energy, list(d.sides["player"].field))


def _entradas(linhas):
    it = iter(linhas)

    def inp() -> str:
        return next(it)  # StopIteration seria bug: o fim deve vir por EOFError
    return inp


def test_partida_inteira_com_entradas_validas_e_invalidas_termina(content):
    saida: list[str] = []
    ruido = ["", "lixo", "j", "j 99 99", "a 1 1", "?", "j 1 1", "j 1 2", "a 1 l", "a 2 l", "p"]

    def inp() -> str:
        inp.n += 1
        if inp.n > 4000:
            raise EOFError
        return ruido[inp.n % len(ruido)]
    inp.n = 0

    d = play(content, 7, "player", False, inp, saida.append)
    assert d is not None
    assert saida and any("!" in s for s in saida)  # mensagens de erro apareceram
    assert d.winner is not None or any("Saindo" in s or "limite" in s for s in saida)


def test_partida_so_passando_turno_termina_com_vitoria_ou_derrota(content):
    saida: list[str] = []
    d = play(content, 5, "dado", False, lambda: "p", saida.append)
    assert d.winner in ("player", "enemy")
    assert any("VITÓRIA" in s or "DERROTA" in s for s in saida)


def test_fim_da_entrada_sai_sem_excecao(content):
    saida: list[str] = []

    def inp() -> str:
        raise EOFError
    d = play(content, 1, "player", False, inp, saida.append)
    assert d.winner is None
    assert any("Saindo" in s for s in saida)


def test_comando_sair_encerra_a_partida(content):
    saida: list[str] = []
    d = play(content, 1, "player", False, lambda: "s", saida.append)
    assert d.winner is None and any("saiu" in s for s in saida)


def test_auto_seed_1_termina_com_vitoria_ou_derrota(content):
    saida: list[str] = []
    d = play(content, 1, "dado", True, None, saida.append)
    assert d.winner in ("player", "enemy")
    assert any("VITÓRIA" in s or "DERROTA" in s for s in saida)


def test_main_auto_seed_1_com_stdout_injetado(content):
    buf = io.StringIO()
    assert main(["--auto", "--seed", "1"], stdout=buf) == 0
    txt = buf.getvalue()
    assert "Seed: 1" in txt and ("VITÓRIA" in txt or "DERROTA" in txt)


def test_auto_e_deterministico_por_seed(content):
    a, b = [], []
    play(content, 4, "dado", True, None, a.append)
    play(content, 4, "dado", True, None, b.append)
    assert a == b
