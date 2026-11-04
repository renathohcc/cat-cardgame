"""T13.2f (UI): `_settle` nao engole erros, `retry_settle`, RATION_RULE e deck_size no texto da
adocao. Escrito a partir de reports/T13.4f-settle-e-magicos.md; estado final conferido pela API
publica do core. Headless (SDL dummy)."""
from __future__ import annotations

import copy
from pathlib import Path

import pytest

from ui_eco_helpers import game_content, has_text, hub_no_cercado  # noqa: F401 (SDL dummy)

import pygame

import ui.errors as errors
import ui.hub_controller as hub_mod
import ui.widgets as Wd
from core import SaveData, close_run, save_to_dict
from core.types import IllegalAction
from economia_helpers import finished_run
from ui import font
from ui.adoption_controller import AdoptionController
from ui.render import UIState
from ui.render_adopt import draw_room
from ui.theme import H, W

UI_DIR = Path(__file__).resolve().parent.parent / "ui"


@pytest.fixture(scope="module")
def c():
    return game_content()


@pytest.fixture
def logado(monkeypatch):
    """Intercepta o log de excecoes (nao escreve errors.log de verdade)."""
    vistos: list[tuple[BaseException, str]] = []
    monkeypatch.setattr(errors, "log_exception", lambda e, where="", path=None: vistos.append((e, where)) or True)
    return vistos


def quebrar_close_run(monkeypatch, erro: Exception) -> None:
    def falha(*a, **k):
        raise erro
    monkeypatch.setattr(hub_mod, "close_run", falha)


def run_vencida(c, h):
    return finished_run(c, h.save, wins={"batalha": 2, "chefe": 1}, result="vitoria")


# ------------------------------------------------------------ _settle
def test_excecao_inesperada_no_close_run_vai_para_o_log_e_mantem_a_run_pendente(c, monkeypatch, logado):
    h = hub_no_cercado()
    run = run_vencida(c, h)
    moedas = h.save.coins
    quebrar_close_run(monkeypatch, RuntimeError("bug no core"))
    resumo = h._settle(run, True, 3)
    assert resumo is None
    assert len(logado) == 1 and isinstance(logado[0][0], RuntimeError) and logado[0][1] == "close_run"
    assert h.unsettled == (run, True, 3)
    assert h.save.coins == moedas                      # nada foi creditado pela metade
    assert h.toast is not None and "pendent" in h.toast.text.lower()
    assert any("moedas" in t.lower() for t in h.result_detail)


def test_retry_settle_conserta_depois_e_as_moedas_nao_se_perdem(c, monkeypatch, logado):
    h = hub_no_cercado()
    run = run_vencida(c, h)
    esperado = copy.deepcopy(h.save)
    ganho = close_run(c, esperado, copy.deepcopy(run))     # referencia: o que o core credita
    ganho_total = esperado.coins - h.save.coins
    assert ganho_total > 0
    real = hub_mod.close_run
    quebrar_close_run(monkeypatch, RuntimeError("falha temporaria"))
    assert h._settle(run, True, 3) is None and h.unsettled is not None
    assert h.save.coins == esperado.coins - ganho_total
    monkeypatch.setattr(hub_mod, "close_run", real)
    h.retry_settle()
    assert h.unsettled is None
    assert h.summary is not None and h.summary.win and h.summary.nodes == 3
    assert h.save.coins == esperado.coins
    assert h.save.lifetime == esperado.lifetime
    assert ganho is not None


def test_retry_settle_ao_abrir_o_cercado(c, monkeypatch, logado):
    h = hub_no_cercado()
    run = run_vencida(c, h)
    antes = h.save.coins
    real = hub_mod.close_run
    quebrar_close_run(monkeypatch, ValueError("x"))
    h._settle(run, True, 3)
    monkeypatch.setattr(hub_mod, "close_run", real)
    h.enter_pen()
    assert h.unsettled is None and h.save.coins > antes


def test_retry_settle_que_falha_de_novo_continua_pendente_sem_perder_a_run(c, monkeypatch, logado):
    h = hub_no_cercado()
    run = run_vencida(c, h)
    quebrar_close_run(monkeypatch, RuntimeError("persistente"))
    h._settle(run, False, 2)
    h.retry_settle()
    assert h.unsettled == (run, False, 2)
    assert len(logado) == 2


def test_retry_settle_sem_pendencia_nao_faz_nada(c):
    h = hub_no_cercado()
    antes = save_to_dict(h.save)
    h.retry_settle()
    assert h.unsettled is None and save_to_dict(h.save) == antes


def test_illegal_action_no_close_run_e_aviso_sem_log_e_sem_pendencia(c, monkeypatch, logado):
    h = hub_no_cercado()
    quebrar_close_run(monkeypatch, IllegalAction("Run ja fechada."))
    assert h._settle(run_vencida(c, h), True, 3) is None
    assert logado == [] and h.unsettled is None
    assert h.toast is not None and "fechada" in h.toast.text


def test_settle_normal_devolve_resumo_e_nao_deixa_pendencia(c):
    h = hub_no_cercado()
    antes = h.save.coins
    resumo = h._settle(run_vencida(c, h), True, 3)
    assert resumo is not None and h.unsettled is None and h.save.coins > antes


# ------------------------------------------------------------ RATION_RULE
def test_ration_rule_e_o_texto_unico_da_regra():
    assert Wd.RATION_RULE == "uma ração por casal"


def test_nenhuma_tela_repete_a_regra_da_racao_como_literal():
    for arq in UI_DIR.glob("*.py"):
        if arq.name == "widgets.py":
            continue
        assert "uma ração por casal" not in arq.read_text("utf-8").lower(), arq.name


# ------------------------------------------------------------ deck_size no texto da adocao
def texto_do_painel(c, ad) -> list[str]:
    surf, seen, real = pygame.Surface((W, H)), [], font.draw

    def spy(s, text, *a, **k):
        seen.append(str(text))
        return real(s, text, *a, **k)
    font.draw = spy
    try:
        draw_room(surf, ad, UIState())
    finally:
        font.draw = real
    return seen


def painel_sem_candidatos(c, deck_size: int):
    c2 = copy.deepcopy(c)
    c2.rules["duel"]["deck_size"] = deck_size
    h = hub_no_cercado()
    s: SaveData = h.save
    s.cats = [x for x in s.cats if x.stage == "adult"][:deck_size]   # so o minimo: ninguem pode ser doado
    ad = AdoptionController(c2, s)
    novo = copy.deepcopy(s.cats[0])
    novo.id = f"c-{s.next_cat_id:06d}"
    s.pending_adoption = {"cats": [novo], "result": "vitoria", "nodes_cleared": 4}
    ad.room_for = novo.id
    return ad


def test_texto_da_adocao_usa_o_deck_size_das_regras(c):
    assert c.rules["duel"]["deck_size"] == 12
    ad = AdoptionController(c, hub_no_cercado().save)
    assert ad.deck_size == 12


def test_texto_do_painel_cheio_mostra_o_deck_size_lido_das_regras(c):
    ad = painel_sem_candidatos(c, 12)
    assert ad.room_cats() == []
    assert has_text(texto_do_painel(c, ad), "manter 12 adultos")


def test_texto_do_painel_acompanha_um_deck_size_diferente(c):
    ad = painel_sem_candidatos(c, 12)
    ad.deck_size = 9                                   # o texto vem do controlador, nao de literal
    assert ad.room_cats() == []
    textos = texto_do_painel(c, ad)
    assert has_text(textos, "manter 9 adultos") and not has_text(textos, "manter 12 adultos")


# ------------------------------------------------------------ bloco economy do ui_timing.json
def test_ui_timing_json_tem_o_bloco_economy_completo():
    import json
    d = json.loads((UI_DIR.parent / "data" / "ui_timing.json").read_text("utf-8"))
    chaves = {"unlock_fade", "unlock_fx_hold", "sign_pulse_period", "hud_flash", "seal_time",
              "seal_pop", "seal_fade", "goal_fill", "coin_tick", "area_toast"}
    assert chaves <= set(d["economy"])
    assert all(isinstance(d["economy"][k], (int, float)) and d["economy"][k] > 0 for k in chaves)
