"""Testes de geracao de gato (T1.3), escritos a partir do GDD e de docs/CONTRATOS.md.

Usam so a API publica do core. Pulam enquanto core/ ou data/ nao existirem.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path
from random import Random

import pytest

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

import core

# Tabela: id -> (custo, atk_base, hp_base), conforme o GDD e docs/CONTRATOS.md 1.2.
BREEDS = {
    "vira-lata": (2, 2, 4),
    "siames": (3, 3, 3),
    "persa": (2, 1, 6),
    "sphynx": (3, 5, 2),
    "maine-coon": (3, 3, 7),
}
# Tabela do GDD: id -> (mod ATK, mod HP)
NATURES = {"calmo": (0, 1), "bravo": (1, -1), "agitado": (2, -2)}


@pytest.fixture(scope="module")
def content():
    return core.load_content(DATA)


def roll(content, seed: int = 1, **kw):
    return core.roll_cat(content, Random(seed), **kw)


def manual_cat(content, breed: str, nature: str, iv_atk: int, iv_hp: int):
    """Gato montado a mao (sem sorteio): parte de um gato valido e troca os campos."""
    base = roll(content, 0)
    return dataclasses.replace(base, breed=breed, nature=nature,
                               iv_atk=iv_atk, iv_hp=iv_hp)


def expected(breed: str, nature: str, iv_atk: int, iv_hp: int):
    cost, atk_b, hp_b = BREEDS[breed]
    n_atk, n_hp = NATURES[nature]
    atk = max(1, atk_b + (iv_atk - 1) // 2 + n_atk)
    hp = max(1, hp_b + (iv_hp - 1) + n_hp)
    return cost, atk, hp


def fields(cat):
    return (cat.breed, cat.sex, cat.nature, cat.iv_atk, cat.iv_hp, cat.stage)


# --- determinismo ---------------------------------------------------------

def test_mesma_seed_gera_o_mesmo_gato(content):
    assert fields(roll(content, 42)) == fields(roll(content, 42))


def test_mesma_seed_gera_a_mesma_sequencia_de_gatos(content):
    a, b = Random(7), Random(7)
    seq_a = [fields(core.roll_cat(content, a)) for _ in range(50)]
    seq_b = [fields(core.roll_cat(content, b)) for _ in range(50)]
    assert seq_a == seq_b


def test_seeds_diferentes_variam(content):
    assert len({fields(roll(content, s)) for s in range(100)}) > 10


# --- IV -------------------------------------------------------------------

def test_iv_sempre_entre_1_e_5(content):
    for seed in range(1000):
        cat = roll(content, seed)
        assert 1 <= cat.iv_atk <= 5
        assert 1 <= cat.iv_hp <= 5


# --- formula de status ----------------------------------------------------

@pytest.mark.parametrize("breed", list(BREEDS))
@pytest.mark.parametrize("nature", list(NATURES))
@pytest.mark.parametrize("iv_atk", range(1, 6))
@pytest.mark.parametrize("iv_hp", range(1, 6))
def test_formula_de_status_tabela_completa(content, breed, nature, iv_atk, iv_hp):
    cat = manual_cat(content, breed, nature, iv_atk, iv_hp)
    st = core.cat_stats(content, cat)
    cost, atk, hp = expected(breed, nature, iv_atk, iv_hp)
    assert (st.cost, st.atk, st.hp) == (cost, atk, hp)


def test_status_nunca_abaixo_de_1(content):
    for breed in BREEDS:
        for nature in NATURES:
            for iv_atk in range(1, 6):
                for iv_hp in range(1, 6):
                    st = core.cat_stats(content, manual_cat(content, breed, nature, iv_atk, iv_hp))
                    assert st.atk >= 1 and st.hp >= 1


def test_persa_iv_baixo_atk_minimo_1(content):
    # Persa ATK base 1, IV 1, Calmo 0: 1 (piso 1 respeitado)
    st = core.cat_stats(content, manual_cat(content, "persa", "calmo", 1, 1))
    assert st.atk == 1


def test_sphynx_agitado_iv_1_hp_minimo_1(content):
    # 2 + 0 - 2 = 0 -> sobe para 1
    st = core.cat_stats(content, manual_cat(content, "sphynx", "agitado", 1, 1))
    assert st.hp == 1


def test_status_de_gatos_sorteados_seguem_a_formula(content):
    for seed in range(300):
        cat = roll(content, seed)
        st = core.cat_stats(content, cat)
        assert (st.cost, st.atk, st.hp) == expected(cat.breed, cat.nature, cat.iv_atk, cat.iv_hp)


# --- custo ----------------------------------------------------------------

def test_custo_fixo_por_raca_independe_de_iv_e_natureza(content):
    for breed, (cost, _, _) in BREEDS.items():
        for nature in NATURES:
            for iv in range(1, 6):
                st = core.cat_stats(content, manual_cat(content, breed, nature, iv, 6 - iv))
                assert st.cost == cost


# --- distribuicoes (so presenca, nao pesos) -------------------------------

def test_sexo_aproximadamente_50_por_cento(content):
    rng = Random(123)
    n = 2000
    females = sum(core.roll_cat(content, rng).sex == "F" for _ in range(n))
    assert 0.40 <= females / n <= 0.60


def test_sexo_so_assume_M_ou_F(content):
    rng = Random(5)
    assert {core.roll_cat(content, rng).sex for _ in range(200)} == {"M", "F"}


def test_as_tres_naturezas_aparecem(content):
    rng = Random(11)
    assert {core.roll_cat(content, rng).nature for _ in range(500)} == set(NATURES)


def test_as_cinco_racas_aparecem(content):
    rng = Random(13)
    assert {core.roll_cat(content, rng).breed for _ in range(1000)} == set(BREEDS)


# --- estagio e raca fixa --------------------------------------------------

def test_estagio_padrao_e_adulto(content):
    assert roll(content, 1).stage == "adult"


def test_filhote_quando_pedido(content):
    assert roll(content, 1, stage="kitten").stage == "kitten"


@pytest.mark.parametrize("breed", list(BREEDS))
def test_breed_id_fixo_respeita_a_raca(content, breed):
    rng = Random(3)
    assert all(core.roll_cat(content, rng, breed_id=breed).breed == breed for _ in range(30))


def test_raca_inexistente_levanta_erro(content):
    with pytest.raises((ValueError, KeyError)):
        core.roll_cat(content, Random(1), breed_id="raca-que-nao-existe")
