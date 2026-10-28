"""sim.inimigos: determinismo por seed, variantes em memoria, data/ intacto."""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from duel_helpers import load
from sim import inimigos as I

DATA = Path(__file__).resolve().parent.parent / "data"


def _hash_data() -> dict[str, str]:
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(DATA.rglob("*.json"))}


@pytest.mark.parametrize("tipo", I.DECKS)
def test_medicao_e_deterministica_por_seed(tipo):
    c = load()
    a = I.medir(c, "berenice-da-matilha", tipo, 7, 6)
    b = I.medir(c, "berenice-da-matilha", tipo, 7, 6)
    assert (a.vitorias, a.decididos, a.turnos) == (b.vitorias, b.decididos, b.turnos)
    assert a.erros == 0 and a.n == 6


def test_deck_medio_tem_6_gatos_3_espiritos_3_efeitos():
    from random import Random
    c = load()
    d = I.player_deck(c, Random(3), "medio")
    assert len(d.cats) == 6 and len(d.cards) == 6
    assert len(I.player_deck(c, Random(3), "gatos").cats) == 12


def test_variante_altera_so_a_copia_do_inimigo():
    c = load()
    v = I.VARIANTES["e-lider20-brasas"]
    novo = I.aplicar_inimigo(c, v)
    assert novo.enemies["berenice-da-matilha"]["lider_hp"] == 20
    assert c.enemies["berenice-da-matilha"]["lider_hp"] == 22
    cartas = {e["carta"] for e in novo.enemies["berenice-da-matilha"]["deck"]}
    assert "gata-das-brasas" not in cartas and "velha-dos-novelos" in cartas
    assert any(e["carta"] == "gata-das-brasas" for e in c.enemies["berenice-da-matilha"]["deck"])


def test_variante_iv_menos_1_nunca_abaixo_de_1():
    novo = I.aplicar_inimigo(load(), I.VarInimigo("t", "", iv_delta=-9))
    for e in novo.enemies["berenice-da-matilha"]["deck"]:
        if "iv_atk" in e:
            assert e["iv_atk"] == 1 and e["iv_hp"] == 1


def test_inimigo_desconhecido_da_erro():
    with pytest.raises(KeyError):
        I.aplicar_inimigo(load(), I.VarInimigo("t", "", inimigo="naoexiste"))


def test_simulacao_nao_altera_data():
    antes = _hash_data()
    c = load()
    I.medir_variante(c, I.VARIANTES["e-iv-1"], 1, 2)
    assert _hash_data() == antes
