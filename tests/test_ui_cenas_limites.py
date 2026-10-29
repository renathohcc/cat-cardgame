"""Varredura de todas as cenas (T8.6): nenhum texto fora de 960x540, nenhuma excecao ao desenhar
(com hover em varios pontos, com a arte/fonte/tema ausentes), textos curtos de hint()/summary(),
plural de donate_question e retrato do fim de run.

Escritos a partir de reports/T8.3 e T8.5. Seeds fixas; nada de janela real.
"""
from __future__ import annotations

import os
from random import Random

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
import pytest

from core import new_game
from ui import font, scenes, scenes_hub, scenes_novas, scenes_run, skin, sprites
from ui.app import make_controller
from ui.controller import Controller, load_game_content
from ui.hub_controller import HubController
from ui.render import UIState, draw_frame
from ui.render_hub import draw_hub_frame
from ui.render_run import draw_run_frame
from ui.run_controller import RunController
from ui.theme import H, W

SEED = 3
DUEL_SCENES = tuple(scenes.SCENES)
HUB_ALL = tuple(scenes_hub.HUB_SCENES) + tuple(scenes_hub.BREED_SCENES)
RUN_ALL = tuple(scenes_run.RUN_SCENES)
TODAS = [("duelo", n) for n in DUEL_SCENES] + [("hub", n) for n in HUB_ALL] + [("run", n) for n in RUN_ALL]

MOUSES = [(-100, -100), (10, 10), (480, 270), (900, 500), (300, 450), (480, 100), (700, 200), (150, 400)]


@pytest.fixture(scope="module", autouse=True)
def pygame_ligado():
    pygame.init()
    yield


def monta(tipo: str, nome: str):
    """(desenha(surface, ui), ui) para a cena, como os `screenshot` do ui/app*.py."""
    if tipo == "duelo":
        if nome in scenes_novas.NEW_SCENES:
            ctrl = scenes_novas.make(SEED, nome)
            assert ctrl is not None, f"nao montou a cena {nome}"
            ui = scenes_novas.build(ctrl, nome)
        else:
            ctrl = make_controller(SEED)
            ui = scenes.build(ctrl, nome)
        return (lambda s, u: draw_frame(s, ctrl, u)), ui, ctrl
    if tipo == "hub":
        hub, ui = scenes_hub.make(SEED, nome)
        return (lambda s, u: draw_hub_frame(s, hub, u)), ui, hub
    made = scenes_run.make(SEED, nome)
    assert made is not None, f"nao montou a cena {nome}"
    rc, ui = made
    return (lambda s, u: draw_run_frame(s, rc, u)), ui, rc


class EspiaFonte:
    def __init__(self) -> None:
        self.itens: list[tuple[str, int, int, int, str]] = []

    def __call__(self, surf, text, x, y, color, scale=1, align="left"):
        self.itens.append((text, x, y, scale, align))
        return ORIGINAL_DRAW(surf, text, x, y, color, scale, align)


ORIGINAL_DRAW = font.draw


def caixa(item) -> tuple[int, int, int, int]:
    text, x, y, scale, align = item
    w = font.width(text, scale)
    x0 = x - w // 2 if align == "center" else (x - w if align == "right" else x)
    return x0, y, x0 + w, y + font.CAP_H * scale


def fora_da_tela(itens) -> list:
    ruins = []
    for it in itens:
        if not it[0].strip() or font.width(it[0], it[3]) == 0:
            continue
        x0, y0, x1, y1 = caixa(it)
        if x0 < 0 or x1 > W or y0 < -2 or y1 > H + 2:
            ruins.append((it, (x0, y0, x1, y1)))
    return ruins


# ================================================================== limites de texto
@pytest.mark.parametrize("tipo,nome", TODAS)
def test_nenhum_texto_fora_de_960x540(tipo, nome, monkeypatch):
    desenha, ui, _ = monta(tipo, nome)
    espia = EspiaFonte()
    monkeypatch.setattr(font, "draw", espia)
    surf = pygame.Surface((W, H))
    desenha(surf, ui)
    assert espia.itens, "a cena nao desenhou texto nenhum"
    assert not fora_da_tela(espia.itens), fora_da_tela(espia.itens)[:5]


@pytest.mark.parametrize("tipo,nome", TODAS)
def test_nenhum_texto_fora_da_tela_com_o_mouse_em_varios_pontos(tipo, nome, monkeypatch):
    desenha, ui, _ = monta(tipo, nome)
    espia = EspiaFonte()
    monkeypatch.setattr(font, "draw", espia)
    surf = pygame.Surface((W, H))
    for pos in MOUSES:
        ui.mouse = pos
        desenha(surf, ui)
    assert not fora_da_tela(espia.itens), fora_da_tela(espia.itens)[:5]


@pytest.mark.parametrize("eid", ["tonho-sem-sorte", "irmaos-pimenta", "berenice-da-matilha", "madame-fifi-pelucia"])
@pytest.mark.parametrize("cena", ["inicio", "final", "chefe", "tooltip"])
def test_duelo_com_cada_inimigo_sem_texto_fora_da_tela(eid, cena, monkeypatch):
    if cena == "chefe":
        ctrl = scenes_novas.make(2, cena, eid)
        assert ctrl is not None
        ui = scenes_novas.build(ctrl, cena)
    else:
        ctrl = make_controller(2, eid)
        ui = scenes.build(ctrl, cena)
    espia = EspiaFonte()
    monkeypatch.setattr(font, "draw", espia)
    draw_frame(pygame.Surface((W, H)), ctrl, ui)
    assert not fora_da_tela(espia.itens), fora_da_tela(espia.itens)[:5]


def test_mao_cheia_com_nomes_longos_nao_estoura_a_tela(monkeypatch):
    from core.types import Card
    from duel_helpers import duel, load
    content = load()
    cartas = [Card(kind="cat", ref=f"c{i}", name=f"c{i}", cost=1, atk=1, hp=1, breed="persa",
                   breed_name="Persa Imperial Gigante", cat_name="Sir Bigodes Terceiro de Todos os Gatos",
                   sex="M", nature="calmo", iv_atk=5, iv_hp=5) for i in range(7)]
    c = Controller(content, 1, ai_delay=0.0)
    c.duel = duel(content, player_hand=cartas, player_field={0: cartas[0]}, enemy_field={0: cartas[1]})
    c.phase = "play"
    c.beats.clear()
    c.cur = None
    c.fx = []
    c.refresh()
    espia = EspiaFonte()
    monkeypatch.setattr(font, "draw", espia)
    from ui import layout as L
    for pos in [L.hand_rect(i, 7).center for i in range(7)] + [L.slot_rect("player", 0).center]:
        draw_frame(pygame.Surface((W, H)), c, UIState(t=0.2, mouse=pos))
    assert not fora_da_tela(espia.itens), fora_da_tela(espia.itens)[:5]


# ================================================================== fallback total
@pytest.fixture
def tudo_ausente(monkeypatch):
    """Sem sprites, sem tema (rects de paleta) e com a fonte 5x7."""
    monkeypatch.setattr(sprites, "get", lambda *a, **k: None)
    skin.THEME = "tema-que-nao-existe"
    skin.reset()
    font.use_bitmap(False)
    yield
    skin.THEME = "noturno"
    skin.reset()
    font.use_bitmap(True)


@pytest.mark.parametrize("tipo,nome", TODAS)
def test_cena_desenha_sem_arte_sem_tema_e_com_fonte_5x7(tipo, nome, tudo_ausente):
    desenha, ui, _ = monta(tipo, nome)
    surf = pygame.Surface((W, H))
    for pos in MOUSES[:4]:
        ui.mouse = pos
        desenha(surf, ui)
    assert len({surf.get_at((x, y))[:3] for x in range(0, W, 37) for y in range(0, H, 29)}) > 2


# ================================================================== desenho em geral
@pytest.mark.parametrize("tipo,nome", TODAS)
def test_cena_desenha_sem_excecao_e_nao_e_um_quadro_em_branco(tipo, nome):
    desenha, ui, _ = monta(tipo, nome)
    surf = pygame.Surface((W, H))
    desenha(surf, ui)
    assert len({surf.get_at((x, y))[:3] for x in range(0, W, 31) for y in range(0, H, 23)}) > 4


@pytest.mark.parametrize("tipo,nome", [t for t in TODAS if t[0] != "run"])
def test_cena_desenha_igual_duas_vezes_na_mesma_seed(tipo, nome):
    def quadro():
        desenha, ui, _ = monta(tipo, nome)
        s = pygame.Surface((W, H))
        desenha(s, ui)
        return pygame.image.tobytes(s, "RGB")
    assert quadro() == quadro()


def test_cenas_do_mesmo_tipo_nao_sao_todas_iguais():
    def quadro(tipo, nome):
        desenha, ui, _ = monta(tipo, nome)
        s = pygame.Surface((W, H))
        desenha(s, ui)
        return pygame.image.tobytes(s, "RGB")
    for tipo, nomes in (("hub", HUB_ALL), ("run", ("mapa", "draft", "descanso", "fimrun"))):
        assert len({quadro(tipo, n) for n in nomes}) == len(nomes)


def test_cena_de_run_com_mouse_sobre_cada_no_e_botao_nao_levanta():
    from ui import layout_run as LR
    made = scenes_run.make(SEED, "mapa")
    rc, ui = made
    surf = pygame.Surface((W, H))
    for layer in range(6):
        for idx in range(2):
            ui.mouse = LR.node_rect(layer, idx, 2, 6).center
            draw_run_frame(surf, rc, ui)
    for r in (LR.abandon_rect(), LR.map_info_rect(), LR.title_rect()):
        ui.mouse = r.center
        draw_run_frame(surf, rc, ui)


def test_hub_com_mouse_sobre_cada_elemento_da_colecao_nao_levanta():
    from ui import layout_hub as LH
    hub, ui = scenes_hub.make(SEED, "colecao")
    surf = pygame.Surface((W, H))
    for i in range(LH.ROWS_VISIBLE):
        ui.mouse = LH.row_rect(i).center
        draw_hub_frame(surf, hub, ui)
    for r in (LH.rename_button(), LH.donate_button(), *LH.action_buttons().values(),
              LH.filter_button(), LH.scroll_up_rect(), LH.scroll_down_rect()):
        ui.mouse = r.center
        draw_hub_frame(surf, hub, ui)


def test_adocao_com_mouse_sobre_cada_oferta_e_botao_nao_levanta():
    from ui import layout_hub as LH
    hub, ui = scenes_hub.make(SEED, "adocao")
    surf = pygame.Surface((W, H))
    for i in range(LH.ADOPT_PER_PAGE):
        ui.mouse = LH.adopt_card(i).center
        draw_hub_frame(surf, hub, ui)
        for r in LH.adopt_buttons(i).values():
            ui.mouse = r.center
            draw_hub_frame(surf, hub, ui)
    for r in LH.adopt_nav().values():
        ui.mouse = r.center
        draw_hub_frame(surf, hub, ui)


# ================================================================== textos de resumo / dica
def terminou(ctrl: Controller) -> Controller:
    from core.ai import choose_action
    rng = Random(ctrl.seed + 7)
    for _ in range(4000):
        if ctrl.over:
            break
        if ctrl.can_act():
            ctrl._do(choose_action(ctrl.duel, "player", rng))
        ctrl.update(5.0)
    for _ in range(5):
        ctrl.update(1.0)
    return ctrl


@pytest.mark.parametrize("seed", [1, 2, 3, 4, 5])
def test_summary_do_duelo_tem_linhas_curtas(seed):
    c = terminou(Controller(load_game_content(), seed, ai_delay=0.0))
    assert c.over
    lines = c.summary()
    assert lines and all(isinstance(x, str) and 0 < len(x) <= 40 for x in lines), lines


def test_hint_do_duelo_tem_no_maximo_30_caracteres_em_todos_os_estados():
    c = make_controller(SEED)
    vistos = {c.hint()}
    c.settle()
    vistos.add(c.hint())
    if c.playable:
        c.click(("hand", min(c.playable)))
        vistos.add(c.hint())
    c.sel = None
    if c.has_other_moves():
        c.click(("pass",))
        vistos.add(c.hint())
        c.confirming = False
    c.phase = "dice"
    vistos.add(c.hint())
    c.phase = "play"
    c.duel.turn_side = "enemy"
    vistos.add(c.hint())
    c.duel.turn_side = "player"
    terminou(c)
    vistos.add(c.hint())
    assert len(vistos) >= 4
    for h in vistos:
        assert 0 < len(h) <= 30, h


@pytest.mark.parametrize("cena", ["inicio", "selecionado", "ataque", "confirmar", "final", "dado"])
def test_hint_das_cenas_do_duelo_cabe_em_30_caracteres(cena):
    c = make_controller(SEED)
    scenes.build(c, cena)
    assert 0 < len(c.hint()) <= 30, c.hint()


# ================================================================== donate_question
def hub_na_colecao() -> HubController:
    hub, _ = scenes_hub.make(SEED, "colecao")
    return hub


def test_donate_question_no_singular_diz_1_moeda(monkeypatch):
    col = hub_na_colecao().col
    assert col.selected_cat() is not None
    monkeypatch.setattr(col, "donate_value", lambda cat: 1)
    q = col.donate_question()
    assert "1 moeda?" in q and "moedas" not in q


@pytest.mark.parametrize("v", [0, 2, 3, 10])
def test_donate_question_no_plural_diz_moedas(monkeypatch, v):
    col = hub_na_colecao().col
    monkeypatch.setattr(col, "donate_value", lambda cat: v)
    assert f"{v} moedas?" in col.donate_question()


def test_donate_question_com_o_valor_real_do_core_e_consistente():
    col = hub_na_colecao().col
    cat = col.selected_cat()
    v = col.donate_value(cat)
    q = col.donate_question()
    assert str(v) in q and q.endswith("?") and ("moeda?" in q) == (v == 1)
    assert (cat.name or col.breed_name(cat)) in q


def test_donate_question_sem_selecao_e_vazia():
    col = hub_na_colecao().col
    col.sel = None if hasattr(col, "sel") else None
    col.selected_cat = lambda: None
    assert col.donate_question() == ""


# ================================================================== retrato do fim de run
def run_ate_o_fim(vencer_tudo: bool, seed: int = 1) -> RunController:
    from core.ai import choose_action
    from core.types import EndTurn
    content = load_game_content()
    for s in range(seed, seed + 60):
        rc = RunController(content, s, ai_delay=0.0)
        rng = Random(s)
        for _ in range(400):
            if rc.screen == "finished":
                break
            if rc.screen == "map":
                rc.click(("node", rc.available_ids()[0]))
            elif rc.screen == "draft":
                rc.click(("draft_card", 0))
                rc.click(("draft_pick", 0))
            elif rc.duel_ctrl is not None:
                c = rc.duel_ctrl
                for _ in range(6000):
                    if c.over:
                        break
                    if c.can_act():
                        c._do(choose_action(c.duel, "player", rng) if vencer_tudo else EndTurn())
                    c.update(5.0)
                for _ in range(5):
                    c.update(1.0)
                rc.click(("continue",))
            else:
                break
        if rc.screen == "finished":
            return rc
    raise AssertionError("nenhuma run terminou")


def test_perder_um_duelo_com_fala_preenche_o_retrato_do_lider_no_fim_da_run():
    rc = run_ate_o_fim(vencer_tudo=False)
    assert rc.run.result in ("derrota", "defeat")
    assert rc.end_leader_id in load_game_content().enemies
    assert rc.end_line is not None and rc.end_line[1]
    desenha = pygame.Surface((W, H))
    draw_run_frame(desenha, rc, UIState(t=0.2))


def test_tela_de_fim_de_run_desenha_com_e_sem_retrato():
    rc = run_ate_o_fim(vencer_tudo=False)
    rc.end_leader_id = None
    draw_run_frame(pygame.Surface((W, H)), rc, UIState(t=0.2))
    rc.end_leader_id = "id-inexistente"
    draw_run_frame(pygame.Surface((W, H)), rc, UIState(t=0.2))


# ================================================================== sanidade do jogo novo
def test_hub_novo_desenha_o_menu_sem_save():
    hub = HubController(load_game_content(), None, SEED, ai_delay=0.0)
    draw_hub_frame(pygame.Surface((W, H)), hub, UIState())
    hub.adopt_save(new_game(load_game_content(), Random(SEED)))
    draw_hub_frame(pygame.Surface((W, H)), hub, UIState())
