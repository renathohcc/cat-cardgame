"""Roda os validadores de dados (schemas) e exige sucesso."""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

SCRIPTS = [
    "data/validate_data.py",
    "data/schemas/validate_examples.py",
]


@pytest.mark.parametrize("script", SCRIPTS)
def test_validador_de_dados_passa(script: str) -> None:
    r = subprocess.run([sys.executable, str(ROOT / script)], cwd=ROOT,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


# ---------------------------------------------------------------- valores x GDD
import json  # noqa: E402

DATA = ROOT / "data"

# id: (custo, atk_base, hp_base, keywords), conforme a tabela do GDD e docs/CONTRATOS.md 1.2.
GDD_RACAS = {
    "vira-lata": (2, 2, 4, []),
    "siames": (3, 4, 3, ["investida"]),
    "persa": (2, 1, 6, ["provocar"]),
    "sphynx": (3, 5, 2, ["primeira-patada"]),
    "maine-coon": (3, 3, 7, ["robusto"]),
}
GDD_NATUREZAS = {"calmo": (-1, 1), "bravo": (1, -1), "agitado": (2, -2)}


def _json(nome: str) -> dict:
    return json.loads((DATA / nome).read_text(encoding="utf-8"))


def test_racas_batem_com_a_tabela_do_gdd() -> None:
    racas = {b["id"]: b for b in _json("breeds.json")["breeds"]}
    assert set(racas) == set(GDD_RACAS)
    for rid, (custo, atk, hp, kws) in GDD_RACAS.items():
        b = racas[rid]
        assert (b["custo"], b["atk_base"], b["hp_base"], b["keywords"]) == (custo, atk, hp, kws), rid


def test_naturezas_batem_com_a_tabela_do_gdd() -> None:
    nat = {n["id"]: n for n in _json("natures.json")["natures"]}
    assert set(nat) == set(GDD_NATUREZAS)
    for nid, (atk, hp) in GDD_NATUREZAS.items():
        assert (nat[nid]["atk"], nat[nid]["hp"]) == (atk, hp), nid


def test_pesos_de_iv_decididos_pelo_renatho() -> None:
    w = _json("rules.json")["iv_weights"]
    assert w == {"1": 30, "2": 25, "3": 25, "4": 15, "5": 5}
    assert sum(w.values()) == 100


def test_regras_de_duelo_batem_com_o_gdd() -> None:
    # first_player_energy_start = 1: quem comeca tem energia 1 so no 1o turno (GDD, CONTRATOS 1.4).
    r = _json("rules.json")
    assert r["duel"] == {
        "leader_hp": 20, "slots": 5, "initial_hand": 4, "draw_per_turn": 1,
        "hand_max": 7, "energy_start": 2, "first_player_energy_start": 1,
        "energy_per_turn": 1, "energy_cap": 7,
        "deck_size": 12, "first_player_no_attack_first_turn": True,
        "draw_on_first_turn": True,
    }
    assert r["deadlock"] == {"variation": [-1, 0, 1], "min_damage": 1, "stall_rounds": 5}
    assert (r["stats"]["iv_min"], r["stats"]["iv_max"]) == (1, 5)
