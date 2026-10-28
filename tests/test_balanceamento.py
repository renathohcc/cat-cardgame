"""sim/balanceamento.py: smoke, determinismo por seed, variantes so em memoria e emulacao do breed."""
from __future__ import annotations

import copy
import hashlib
from dataclasses import replace
from pathlib import Path
from random import Random

from core import roll_cat
from core.breeding import advance_after_run
from core.save import format_cat_id, new_game
from duel_helpers import load
from sim import balanceamento as B

DATA = Path(__file__).resolve().parent.parent / "data"


def _hash_data() -> dict[str, str]:
    return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(DATA.rglob("*.json"))}


def test_lista_mostra_temas_e_variantes(capsys):
    assert B.main(["--lista"]) == 0
    saida = capsys.readouterr().out
    for tema in B.TEMAS:
        assert tema in saida
    assert "custo4" in saida and "melhor-pai" in saida


def test_patch_altera_so_a_copia():
    content = load()
    novo = B.aplicar_patch(content, {"breeds": {"siames": {"custo": 4, "keywords": []}},
                                     "natures": {"calmo": {"atk": 0, "hp": 2}},
                                     "rules": {"breed": {"mutation_chance": 0.03},
                                               "iv_weights": {1: 1, 2: 1, 3: 1, 4: 1, 5: 1}}})
    assert novo.breeds["siames"]["custo"] == 4 and novo.breeds["siames"]["keywords"] == []
    assert novo.natures["calmo"]["hp"] == 2
    assert novo.rules["breed"]["mutation_chance"] == 0.03
    assert novo.rules["iv_weights"]["5"] == 1
    assert content.breeds["siames"]["custo"] == 3
    assert content.breeds["siames"]["keywords"] == ["investida"]
    assert content.natures["calmo"]["hp"] == 1
    assert content.rules["iv_weights"]["5"] == 5


def test_smoke_nao_toca_em_data_e_e_deterministico_por_seed():
    antes = _hash_data()
    a = B.construir(["siames"], [1], 10, 2, 1, 3, 1, ["base", "custo4"])
    b = B.construir(["siames"], [1], 10, 2, 1, 3, 1, ["base", "custo4"])
    assert a == b
    assert "Tema 1" in a and "custo4" in a
    assert _hash_data() == antes


def test_natureza_deterministica_por_seed():
    a = B.medir_natureza(B.VAR_NAT["calmo0+2"][1], 1, 8)
    b = B.medir_natureza(B.VAR_NAT["calmo0+2"][1], 1, 8)
    assert a == b
    assert set(a["par3"]) == {"calmo|bravo", "calmo|agitado", "bravo|agitado"}


def test_iv_deterministico_e_completo_tem_tabela_por_raca():
    a = B.medir_iv({}, 2, 8, 2, completo=True)
    assert a == B.medir_iv({}, 2, 8, 2, completo=True)
    assert "vira-lata|5/5 vs 1/1" in a["mono"] and "maine-coon|5/5" in a["um"]
    assert set(B.PERFIS) <= set(a["runs"])


def test_deck_deterministico_e_politica_com_limite_por_raca():
    a = B.medir_deck("atk*hp-cap3", 1, 3)
    assert a == B.medir_deck("atk*hp-cap3", 1, 3)
    content = load()
    rng = Random(4)
    pool = B.deck_perfil(content, rng, "real", 30)
    deck = B.escolher_deck(content, pool, 3)
    assert len(deck) == 12 and len({c.id for c in deck}) == 12
    assert max(sum(1 for c in deck if c.breed == b) for b in content.breeds) <= 3


def test_breed_deterministico_e_estrategias_diferentes_por_seed():
    a = B.medir_breed("base", "simples", 1, 2, 6)
    assert a == B.medir_breed("base", "simples", 1, 2, 6)
    outra = B.medir_breed("base", "simples", 2, 2, 6)
    assert a != outra
    for j in a["jog"]:
        assert len(j["hist"]["win"]) == 6


def test_pontos_do_casal_preferem_pais_5_5_a_5_1_com_1_5():
    content = load()
    mk = lambda sex, ia, ih: replace(roll_cat(content, Random(1)), sex=sex, iv_atk=ia, iv_hp=ih)
    bom = B.pontos_casal(mk("M", 5, 5), mk("F", 5, 5), 0.07, False)
    cruzado = B.pontos_casal(mk("M", 5, 1), mk("F", 1, 5), 0.07, False)
    assert bom[0] == 1.0 and abs(cruzado[0] - 0.25) < 1e-9
    assert B.pontos_casal(mk("M", 5, 1), mk("F", 1, 5), 0.07, True)[0] == 1.0


def _save_com_casal(content, m_iv, f_iv):
    rng = Random(3)
    save = new_game(content, rng)
    pais = []
    for sex, (ia, ih) in (("M", m_iv), ("F", f_iv)):
        c = replace(roll_cat(content, rng), sex=sex, iv_atk=ia, iv_hp=ih, id=format_cat_id(save.next_cat_id))
        save.next_cat_id += 1
        save.cats.append(c)
        pais.append(c)
    save.breeding = [{"male": pais[0].id, "female": pais[1].id, "runs_left": 1}]
    return save, pais


def test_nascimento_emulado_sem_melhor_pai_igual_ao_do_core():
    content = load()
    s1, _ = _save_com_casal(content, (5, 2), (3, 4))
    s2 = copy.deepcopy(s1)
    core = advance_after_run(content, s1, Random(7), 3).born
    m, f = (next(c for c in s2.cats if c.id == i) for i in (s2.breeding[0]["male"], s2.breeding[0]["female"]))
    emul = B.nascer_emulado(content, s2, Random(7), m, f, False)
    assert emul == core and emul


def test_melhor_pai_da_o_maior_iv_de_cada_pai():
    content = B.aplicar_patch(load(), {"rules": {"breed": {"mutation_chance": 0.0}}})
    save, _ = _save_com_casal(content, (5, 1), (1, 5))
    out = B.avancar(content, save, Random(5), 3, True)
    assert out.born and all((k.iv_atk, k.iv_hp) == (5, 5) for k in out.born)
    assert save.breeding == [] and out.couples_done


def test_somar_soma_dicts_e_concatena_listas():
    assert B.somar({"a": {"w": 1, "n": 2}, "l": [1]}, {"a": {"w": 2, "n": 3}, "l": [2], "x": 5}) == \
        {"a": {"w": 3, "n": 5}, "l": [1, 2], "x": 5}
