"""Opções, prefs, pausa, Esc/Espaço, fade e log de erros (T12.5, a partir de T12.4).

Prefs e saves sempre isolados (fixture autouse `prefs_dir` do conftest, mais `tmp_path`).
Os loops reais rodam headless (SDL dummy) com eventos postados quadro a quadro.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import asyncio
import json
import sys
from pathlib import Path
from random import Random

import pygame
import pytest

from core import new_game
from duel_helpers import duel, fc, load, mk
from ui import audio, errors, layout_opts as LO
from ui.controller import Controller
from ui.options import Options, OptionsScreen
from ui.pause import Overlay
from ui.render import UIState
from ui.shell import Shell
from ui.transition import Transition

PLAYER, ENEMY = "player", "enemy"
REPO_PREFS = Path(__file__).resolve().parent.parent / "saves" / "prefs.json"


@pytest.fixture(scope="module")
def content():
    return load()


def key(k: int) -> pygame.event.Event:
    return pygame.event.Event(pygame.KEYDOWN, key=k, mod=0, unicode="", scancode=0)


def ler(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ opções e prefs
def test_opcoes_novas_comecam_nos_padroes_sem_arquivo(tmp_path):
    o = Options(tmp_path / "prefs.json")
    assert (o.shake, o.speed, o.fullscreen) == (True, "1x", False)


def test_ciclo_alterar_gravar_e_reler(tmp_path):
    p = tmp_path / "saves" / "prefs.json"
    o = Options(p)
    o.set_shake(False)
    o.set_speed("rapido")
    o.set_fullscreen(True)
    assert ler(p)["screen_shake"] is False and ler(p)["enemy_speed"] == "rapido" and ler(p)["fullscreen"] is True
    novo = Options(p)
    assert (novo.shake, novo.speed, novo.fullscreen) == (False, "rapido", True)


def test_set_speed_ignora_chave_desconhecida(tmp_path):
    o = Options(tmp_path / "prefs.json")
    o.set_speed("turbo")
    assert o.speed == "1x" and not (tmp_path / "prefs.json").exists()


def test_step_speed_anda_pelas_opcoes_e_trava_nas_pontas(tmp_path):
    o = Options(tmp_path / "p.json")
    o.step_speed(-1)
    assert o.speed == "1x"
    o.step_speed(1)
    o.step_speed(1)
    o.step_speed(1)
    assert o.speed == "rapido"


def test_gravar_opcoes_preserva_as_chaves_de_audio(tmp_path):
    p = tmp_path / "prefs.json"
    p.write_text(json.dumps({"version": 1, "music": 0.3, "sfx": 0.4, "muted": True}), encoding="utf-8")
    Options(p).set_speed("2x")
    raw = ler(p)
    assert (raw["music"], raw["sfx"], raw["muted"]) == (0.3, 0.4, True)
    assert raw["enemy_speed"] == "2x"


def test_write_prefs_mescla_e_nao_apaga_chaves_de_outras_telas(tmp_path):
    p = tmp_path / "prefs.json"
    assert audio.write_prefs(p, {"screen_shake": False, "enemy_speed": "2x"})
    assert audio.write_prefs(p, {"music": 0.5, "sfx": 0.6, "muted": False})
    raw = ler(p)
    assert raw["screen_shake"] is False and raw["enemy_speed"] == "2x" and raw["music"] == 0.5
    audio.write_prefs(p, {"music": 0.9})
    assert ler(p)["sfx"] == 0.6                      # mescla também entre gravações de áudio


def test_write_prefs_sobre_arquivo_corrompido_recomeca_limpo(tmp_path):
    p = tmp_path / "prefs.json"
    p.write_text("{quebrado", encoding="utf-8")
    assert audio.write_prefs(p, {"music": 0.2})
    assert ler(p)["music"] == 0.2


def test_write_prefs_sem_caminho_ou_com_falha_devolve_false(tmp_path):
    assert audio.write_prefs(None, {"music": 0.2}) is False
    arquivo = tmp_path / "arq"
    arquivo.write_text("x")
    assert audio.write_prefs(arquivo / "dentro" / "prefs.json", {"music": 0.2}) is False


def test_arquivo_antigo_sem_chaves_novas_carrega_os_padroes(tmp_path):
    p = tmp_path / "prefs.json"
    p.write_text(json.dumps({"version": 1, "music": 0.3, "sfx": 0.4, "muted": False}), encoding="utf-8")
    o = Options(p)
    assert (o.shake, o.speed, o.fullscreen) == (True, "1x", False)


@pytest.mark.parametrize("conteudo", ["", "{quebrado", "[]", "null", "123", '"x"'])
def test_arquivo_corrompido_carrega_os_padroes(tmp_path, conteudo):
    p = tmp_path / "prefs.json"
    p.write_text(conteudo, encoding="utf-8")
    o = Options(p)
    assert (o.shake, o.speed, o.fullscreen) == (True, "1x", False)


@pytest.mark.parametrize("raw", [
    {"screen_shake": "sim", "enemy_speed": "turbo", "fullscreen": 1},
    {"screen_shake": None, "enemy_speed": 2, "fullscreen": "true"},
    {"screen_shake": 0, "enemy_speed": ["2x"], "fullscreen": []},
])
def test_valores_invalidos_carregam_os_padroes(tmp_path, raw):
    p = tmp_path / "prefs.json"
    p.write_text(json.dumps(raw), encoding="utf-8")
    o = Options(p)
    assert (o.shake, o.speed, o.fullscreen) == (True, "1x", False)


def test_valor_invalido_nao_estraga_os_validos_ao_lado(tmp_path):
    p = tmp_path / "prefs.json"
    p.write_text(json.dumps({"screen_shake": False, "enemy_speed": "turbo", "fullscreen": True}), encoding="utf-8")
    o = Options(p)
    assert (o.shake, o.speed, o.fullscreen) == (False, "1x", True)


def test_options_sem_caminho_so_vive_em_memoria():
    o = Options(None)
    assert o.set_shake(False) is None and o.shake is False
    assert o.save() is False


def test_opcoes_ligam_em_uistate(tmp_path):
    o = Options(tmp_path / "p.json")
    o.set_shake(False)
    o.set_speed("2x")
    ui = UIState()
    assert ui.screen_shake is True and ui.enemy_speed == "1x"
    o.apply(ui)
    assert ui.screen_shake is False and ui.enemy_speed == "2x"


def test_shell_sync_aplica_as_opcoes_e_esconde_o_mouse_na_pausa(tmp_path):
    shell = Shell(None, Options(tmp_path / "p.json"), fade=False)
    shell.options.set_speed("rapido")
    ui = UIState(mouse=(300, 200))
    shell.sync(ui)
    assert ui.enemy_speed == "rapido" and ui.mouse == (300, 200)
    shell.open_pause()
    shell.sync(ui)
    assert ui.mouse[0] < 0 and ui.drag is None


def test_velocidade_do_ui_chega_ao_controller_no_loop_do_duelo(monkeypatch, content):
    from ui import app
    caps = loop_capture(monkeypatch, app)
    caps["script"] = {3: lambda: caps["shell"][0].options.set_speed("2x"),
                      6: lambda: caps.setdefault("seen", caps["ctrl"][0].enemy_speed)}
    run_loop(monkeypatch, lambda: app.run(1, "tonho-sem-sorte"), caps, frames=8)
    assert caps["seen"] == "2x"


# ------------------------------------------------------------------ tela de opções
def test_tela_de_opcoes_alterna_tremor_por_clique_e_teclado(tmp_path):
    o = Options(tmp_path / "p.json")
    s = OptionsScreen(o)
    s.click(("opt_shake",))
    assert o.shake is False
    s.focus = LO.ROWS.index("tremor")
    s.key(pygame.K_RIGHT)
    assert o.shake is True
    s.key(pygame.K_LEFT)
    assert o.shake is False
    assert ler(tmp_path / "p.json")["screen_shake"] is False


def test_tela_de_opcoes_muda_velocidade_por_setas_e_clique(tmp_path):
    o = Options(tmp_path / "p.json")
    s = OptionsScreen(o)
    s.focus = LO.ROWS.index("velocidade")
    s.key(pygame.K_RIGHT)
    assert o.speed == "2x"
    s.key(pygame.K_RIGHT)
    s.key(pygame.K_RIGHT)
    assert o.speed == "rapido"
    s.click(("opt_speed", "1x"))
    assert o.speed == "1x"


def test_tela_de_opcoes_foco_circula_e_esc_volta(tmp_path):
    s = OptionsScreen(Options(tmp_path / "p.json"))
    n = len(LO.ROWS)
    s.key(pygame.K_UP)
    assert s.focus == n - 1
    s.key(pygame.K_DOWN)
    assert s.focus == 0
    assert s.key(pygame.K_ESCAPE) == "back"
    assert s.click(("opt_back",)) == "back"
    assert s.click(None) is None


def test_ciclo_completo_com_audio_e_opcoes_no_mesmo_arquivo_isolado(prefs_dir):
    antes = REPO_PREFS.read_bytes() if REPO_PREFS.exists() else None
    mgr = audio.setup()
    assert Path(mgr.prefs_path).parent == prefs_dir
    o = Options.from_audio()
    s = OptionsScreen(o)
    s.click(("opt_shake",))
    s.click(("opt_speed", "2x"))
    s.click(("opt_mute",))
    s.click(("opt_vol", "musica", -1))
    raw = ler(mgr.prefs_path)
    assert raw["screen_shake"] is False and raw["enemy_speed"] == "2x" and raw["muted"] is True
    assert raw["music"] < 1.0
    mgr2 = audio.setup()                          # "reabrir o jogo"
    o2 = Options.from_audio()
    assert (o2.shake, o2.speed) == (False, "2x")
    assert mgr2.muted is True and mgr2.music_volume == pytest.approx(raw["music"])
    assert (REPO_PREFS.read_bytes() if REPO_PREFS.exists() else None) == antes   # repo intocado


# ------------------------------------------------------------------ Esc: precedência
def test_esc_no_duelo_cancela_selecao_depois_confirmacao_e_so_entao_libera_a_pausa(content):
    c = Controller(content, 1, ai_delay=0.0)
    c.duel = duel(content, player_hand=[mk(1, 1)], player_energy=3, player_field={0: fc(2, 2)},
                  player_deck=[mk(1, 1)], enemy_deck=[mk(1, 1)])
    c.phase = "play"; c.intro_t = None; c.beats.clear(); c.cur = None; c.refresh()
    c.click(("hand", 0))
    assert c.sel is not None
    assert c.escape() is True and c.sel is None        # 1o Esc cancela
    assert c.escape() is False                          # nada a cancelar: a UI abre a pausa
    c.request_end_turn()
    assert c.confirming is True
    assert c.escape() is True and c.confirming is False
    assert c.escape() is False


def make_rc(content, seed: int = 1):
    from ui.run_controller import RunController
    return RunController(content, seed, ai_delay=0.0)


def test_esc_no_mapa_sem_nada_a_cancelar_abre_a_pausa_e_nao_o_abandono(content):
    rc = make_rc(content)
    assert rc.screen == "map"
    assert rc.escape() is False
    assert rc.quit_confirm is False


def test_esc_cancela_a_confirmacao_de_abandono_antes_de_tudo(content):
    rc = make_rc(content)
    rc.request_abandon()
    assert rc.quit_confirm is True
    assert rc.escape() is True and rc.quit_confirm is False
    assert rc.run.status != "finished"


def test_esc_no_duelo_da_run_cancela_selecao_e_depois_abre_a_pausa(content):
    rc = make_rc(content)
    _entra_no_primeiro_duelo(rc)
    c = rc.duel_ctrl
    c.dismiss_dice()
    c.refresh()
    assert rc.escape() is False                         # nada selecionado
    atacante = next(iter(c.attackers), None)
    if atacante is not None:
        c.click(("slot", PLAYER, atacante))
        assert rc.escape() is True and c.sel is None
    for i in range(len(c.shown.me.hand)):
        if i in c.playable:
            c.click(("hand", i))
            assert rc.escape() is True and c.sel is None
            break


def _entra_no_primeiro_duelo(rc):
    node = next(n for n in rc.run.layers[0]["nodes"] if n.get("inimigo"))
    rc.choose(node["id"])
    assert rc.screen == "duel" and rc.duel_ctrl is not None


def test_esc_no_fim_do_duelo_e_ignorado_sem_abrir_pausa(content):
    rc = make_rc(content)
    _entra_no_primeiro_duelo(rc)
    rc.duel_ctrl.phase = "over"
    assert rc.escape() is True


def test_esc_no_draft_cancela_a_selecao_e_sem_selecao_abre_a_pausa(content):
    rc = make_rc(content)
    rc.run.status = "draft"
    rc.run.draft_options = rc.run.draft_options or []
    rc.draft_sel = 0
    assert rc.screen == "draft"
    assert rc.escape() is True and rc.draft_sel is None
    assert rc.escape() is False


def _hub(content, tmp_path=None):
    from ui.hub_controller import HubController
    h = HubController(content, None, 5, ai_delay=0.0)
    h.adopt_save(new_game(content, Random(5)))
    return h


def test_esc_no_cercado_fecha_a_ficha_primeiro_e_depois_libera_a_pausa(content):
    h = _hub(content)
    h.enter_pen()
    assert h.mode == "cercado"
    assert h.escape() is False                         # nada aberto: pausa
    h.open_ficha(h.pen.shown[0])
    assert h.ficha
    assert h.escape() is True and not h.ficha and h.mode == "cercado"
    assert h.escape() is False


def test_esc_no_cercado_cancela_edicao_de_nome(content):
    h = _hub(content)
    h.enter_pen()
    h.col.selected = h.pen.shown[0]
    h.col.begin_rename()
    assert h.col.editing
    assert h.escape() is True and not h.col.editing


def test_esc_nas_telas_de_volta_volta_sem_abrir_pausa(content):
    h = _hub(content)
    h.mode = "colecao"
    assert h.escape() is True
    assert h.mode == "cercado"


def test_esc_no_hub_em_run_segue_o_controller_da_run(content):
    h = _hub(content)
    h.mode, h.rc = "run", make_rc(content)
    assert h.escape() is False                         # mapa sem nada a cancelar
    h.rc.request_abandon()
    assert h.escape() is True and h.rc.quit_confirm is False


def test_pausa_no_cercado_oferece_menu_e_sair_mas_nao_abandonar(tmp_path):
    o = Overlay(Options(None, load=False))
    o.open_pause(menu=True)
    assert o.items == ["continue", "options", "menu", "quit"]


def test_pausa_na_run_oferece_abandonar_e_nao_menu():
    o = Overlay(Options(None, load=False))
    o.open_pause(run=True)
    assert o.items == ["continue", "options", "abandon", "quit"]


def test_pausa_so_continuar_opcoes_e_sair_no_duelo_de_teste():
    o = Overlay(Options(None, load=False))
    o.open_pause()
    assert o.items == ["continue", "options", "quit"]


# ------------------------------------------------------------------ pausa (Overlay) e abandono
def overlay(**kw) -> Overlay:
    o = Overlay(Options(None, load=False))
    o.open_pause(**kw)
    return o


def test_esc_fecha_a_pausa_e_consome_o_evento():
    o = overlay()
    assert o.handle(key(pygame.K_ESCAPE), lambda p: p) is True
    assert not o.open


def test_overlay_fechado_nao_consome_eventos():
    o = Overlay(Options(None, load=False))
    assert o.handle(key(pygame.K_SPACE), lambda p: p) is False


def test_esc_nas_opcoes_volta_para_a_pausa_e_outro_esc_continua():
    o = overlay()
    o.handle(key(pygame.K_DOWN), lambda p: p)
    o.handle(key(pygame.K_RETURN), lambda p: p)
    assert o.view == "options"
    o.handle(key(pygame.K_ESCAPE), lambda p: p)
    assert o.view == "pause"
    o.handle(key(pygame.K_ESCAPE), lambda p: p)
    assert not o.open


def test_abandonar_run_pede_acao_abandon_e_fecha_a_pausa():
    o = overlay(run=True)
    o.click(("pause", "abandon"))
    assert o.take_action() == "abandon" and not o.open
    assert o.take_action() is None


def test_sair_do_jogo_dentro_de_run_pede_confirmacao_e_nao_sair_cancela():
    o = overlay(run=True)
    o.click(("pause", "quit"))
    assert o.view == "ask" and o.ask_focus == 1 and o.take_action() is None
    o.handle(key(pygame.K_RETURN), lambda p: p)          # foco padrao: NAO
    assert o.view == "pause" and o.take_action() is None
    o.click(("pause", "quit"))
    o.click(("ask_yes",))
    assert o.take_action() == "quit"


def test_sair_do_jogo_fora_de_run_nao_pede_confirmacao():
    o = overlay(menu=True)
    o.click(("pause", "quit"))
    assert o.take_action() == "quit"


def test_abandonar_pela_pausa_usa_o_fluxo_de_derrota_da_run(content):
    rc = make_rc(content)
    rc.request_abandon()                                 # o que o loop faz com a acao "abandon"
    assert rc.quit_confirm and rc.run.status != "finished"
    rc.click(("quit_no",))
    assert not rc.quit_confirm and rc.run.status != "finished" and not rc.abandoned
    rc.request_abandon()
    rc.click(("quit_yes",))
    assert rc.run.status == "finished" and rc.run.result == "derrota" and rc.abandoned is True


def test_request_abandon_nao_faz_nada_com_run_terminada(content):
    rc = make_rc(content)
    rc.abandon()
    rc.request_abandon()
    assert rc.quit_confirm is False


def test_menu_da_pausa_no_cercado_volta_ao_menu_principal(content):
    h = _hub(content)
    h.enter_pen()
    h.go_menu()
    assert h.mode == "menu"


# ------------------------------------------------------------------ Espaço
def ctrl_pronto(content, **kw) -> Controller:
    c = Controller(content, 1, ai_delay=0.0)
    kw.setdefault("player_deck", [mk(1, 1)])
    kw.setdefault("enemy_deck", [mk(1, 1)])
    c.duel = duel(content, **kw)
    c.phase, c.intro_t = "play", None
    c.beats.clear(); c.cur = None; c.fx = []
    c.refresh()
    return c


def test_espaco_passa_o_turno_direto_quando_nao_ha_mais_jogada(content):
    c = ctrl_pronto(content, player_field={0: fc(1, 1, ready=False)}, enemy_field={0: fc(1, 5)})
    assert c.pass_only
    c.space_key()
    assert c.duel.turn_side == ENEMY and c.confirming is False


def test_espaco_pede_confirmacao_se_ainda_ha_jogada_e_o_segundo_espaco_confirma(content):
    c = ctrl_pronto(content, player_hand=[mk(1, 1)], player_energy=3, player_field={0: fc(1, 1)},
                    enemy_field={0: fc(1, 5)})
    c.space_key()
    assert c.confirming is True and c.duel.turn_side == PLAYER
    c.space_key()
    assert c.duel.turn_side == ENEMY and c.confirming is False


def test_espaco_e_equivalente_a_tecla_e(content):
    a = ctrl_pronto(content, player_hand=[mk(1, 1)], player_energy=3, enemy_field={0: fc(1, 5)})
    b = ctrl_pronto(content, player_hand=[mk(1, 1)], player_energy=3, enemy_field={0: fc(1, 5)})
    a.space_key(); b.request_end_turn()
    assert a.confirming == b.confirming and a.duel.turn_side == b.duel.turn_side


def test_espaco_fora_da_vez_do_jogador_pula_o_passo_atual(content):
    c = ctrl_pronto(content, turn_side=ENEMY, player_field={0: fc(1, 5)}, enemy_field={0: fc(1, 5)})
    c.ai_delay = 9.0
    c.ai_t = 0.0
    c.space_key()
    assert c.ai_t == 9.0 and c.duel.turn_side == ENEMY


def test_espaco_no_dado_comeca_o_jogo(content):
    c = Controller(content, 1)
    assert c.phase == "dice"
    c.space_key()
    assert c.phase == "play"


def test_espaco_no_loop_real_nao_levanta_em_nenhuma_fase(monkeypatch):
    from ui import app
    caps = loop_capture(monkeypatch, app)
    caps["events"] = {f: key(pygame.K_SPACE) for f in (2, 4, 6, 8, 10)}
    run_loop(monkeypatch, lambda: app.run(2, "tonho-sem-sorte"), caps, frames=12)


# ------------------------------------------------------------------ loops reais: pausa congela tudo
def loop_capture(monkeypatch, module) -> dict:
    """Prepara a captura do Shell e do controller do loop `module` (app, app_run ou app_hub)."""
    caps: dict = {"shell": [], "ctrl": [], "rc": [], "hub": [], "events": {}, "script": {}}

    class CapShell(Shell):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            caps["shell"].append(self)

    monkeypatch.setattr(module, "Shell", CapShell)
    if hasattr(module, "make_controller"):
        real = module.make_controller

        def mc(*a, **k):
            c = real(*a, **k)
            caps["ctrl"].append(c)
            return c

        monkeypatch.setattr(module, "make_controller", mc)
    if hasattr(module, "RunController"):
        Real = module.RunController

        class CapRC(Real):
            def __init__(self, *a, **k):
                super().__init__(*a, **k)
                caps["rc"].append(self)

        monkeypatch.setattr(module, "RunController", CapRC)
    if hasattr(module, "scenes_hub"):
        real_make = module.scenes_hub.make

        def mk_hub(*a, **k):
            hub, ui = real_make(*a, **k)
            caps["hub"].append(hub)
            return hub, ui

        monkeypatch.setattr(module.scenes_hub, "make", mk_hub)
    return caps


def run_loop(monkeypatch, coro_fn, caps: dict, frames: int) -> int:
    n = [0]
    real_flip = pygame.display.flip

    def flip() -> None:
        real_flip()
        n[0] += 1
        ev = caps["events"].get(n[0])
        if ev is not None:
            pygame.event.post(ev)
        fn = caps["script"].get(n[0])
        if fn is not None:
            fn()
        if n[0] >= frames:
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    monkeypatch.setattr(pygame.display, "flip", flip)
    asyncio.run(coro_fn())
    return n[0]


def test_loop_do_duelo_esc_abre_a_pausa_e_congela_o_controller(monkeypatch):
    from ui import app
    caps = loop_capture(monkeypatch, app)
    chamadas, marca = [0], {}
    real_update = Controller.update

    def contando(self, dt):
        chamadas[0] += 1
        return real_update(self, dt)

    monkeypatch.setattr(Controller, "update", contando)

    def abre_depois():
        marca["aberta"] = caps["shell"][0].paused
        marca["n0"] = chamadas[0]

    def ainda_aberta():
        marca["n1"] = chamadas[0]
        marca["ainda"] = caps["shell"][0].paused

    def fechada():
        marca["fechada"] = not caps["shell"][0].paused
        marca["n2"] = chamadas[0]

    caps["events"] = {3: key(pygame.K_ESCAPE), 16: key(pygame.K_ESCAPE)}
    caps["script"] = {5: abre_depois, 15: ainda_aberta, 20: fechada}
    run_loop(monkeypatch, lambda: app.run(1, "tonho-sem-sorte"), caps, frames=24)
    assert marca["aberta"] is True and marca["ainda"] is True
    assert marca["n1"] == marca["n0"]                      # 10 quadros de pausa: update nao rodou
    assert marca["fechada"] is True
    assert chamadas[0] > marca["n2"]                        # depois de continuar volta a rodar


def test_loop_do_duelo_pausa_congela_beats_e_o_turno_inimigo(monkeypatch):
    from ui import app
    caps = loop_capture(monkeypatch, app)
    marca = {}

    def prepara():
        c = caps["ctrl"][0]
        c.dismiss_dice()
        c.duel.turn_side = ENEMY                           # vez do inimigo: a IA agiria sozinha
        c.shown.turn_side = ENEMY
        c.ai_delay = 0.0
        c.ai_t = 0.0
        caps["shell"][0].open_pause()
        marca["log"] = len(c.duel.log)
        marca["beats"] = len(c.beats)

    def congelado():
        c = caps["ctrl"][0]
        marca["log2"], marca["beats2"] = len(c.duel.log), len(c.beats)
        marca["ainda"] = caps["shell"][0].paused

    caps["script"] = {4: prepara, 14: congelado}
    run_loop(monkeypatch, lambda: app.run(1, "tonho-sem-sorte"), caps, frames=16)
    assert marca["ainda"] is True
    assert (marca["log2"], marca["beats2"]) == (marca["log"], marca["beats"])


def test_loop_da_run_esc_no_mapa_abre_pausa_com_abandonar_e_pede_confirmacao(monkeypatch):
    from ui import app_run
    caps = loop_capture(monkeypatch, app_run)
    marca = {}

    def pausa():
        sh = caps["shell"][0]
        marca["paused"], marca["items"] = sh.paused, list(sh.overlay.items)
        marca["confirm_antes"] = caps["rc"][0].quit_confirm

    def depois():
        marca["confirm"] = caps["rc"][0].quit_confirm
        marca["status"] = caps["rc"][0].run.status

    ev = {3: key(pygame.K_ESCAPE), 7: key(pygame.K_DOWN), 8: key(pygame.K_DOWN), 9: key(pygame.K_RETURN)}
    caps["events"], caps["script"] = ev, {5: pausa, 14: depois}
    run_loop(monkeypatch, lambda: app_run.run(1), caps, frames=16)
    assert marca["paused"] and "abandon" in marca["items"] and "menu" not in marca["items"]
    assert marca["confirm_antes"] is False
    assert marca["confirm"] is True and marca["status"] != "finished"    # confirma antes de perder a run


def test_loop_da_run_pausa_nao_atualiza_o_rc(monkeypatch):
    from ui import app_run
    from ui.run_controller import RunController
    caps = loop_capture(monkeypatch, app_run)
    chamadas, marca = [0], {}
    real = RunController.update

    def contando(self, dt):
        chamadas[0] += 1
        return real(self, dt)

    monkeypatch.setattr(RunController, "update", contando)
    caps["events"] = {3: key(pygame.K_ESCAPE)}
    caps["script"] = {5: lambda: marca.update(a=chamadas[0]), 14: lambda: marca.update(b=chamadas[0], p=caps["shell"][0].paused)}
    run_loop(monkeypatch, lambda: app_run.run(1), caps, frames=16)
    assert marca["p"] and marca["a"] == marca["b"]


def test_loop_do_criatorio_esc_abre_pausa_com_sair_para_o_menu(monkeypatch):
    from ui import app_hub
    caps = loop_capture(monkeypatch, app_hub)
    marca = {}

    def aberta():
        sh = caps["shell"][0]
        marca["paused"], marca["items"], marca["mode"] = sh.paused, list(sh.overlay.items), caps["hub"][0].mode

    caps["events"] = {3: key(pygame.K_ESCAPE)}
    caps["script"] = {6: aberta}
    run_loop(monkeypatch, lambda: app_hub.run(1, None, "criatorio_hub", "12:00"), caps, frames=8)
    assert marca["mode"] == "cercado" and marca["paused"]
    assert "menu" in marca["items"] and "abandon" not in marca["items"]


def test_loop_do_criatorio_segundo_esc_fecha_a_pausa(monkeypatch):
    from ui import app_hub
    caps = loop_capture(monkeypatch, app_hub)
    marca = {}
    caps["events"] = {3: key(pygame.K_ESCAPE), 6: key(pygame.K_ESCAPE)}
    caps["script"] = {9: lambda: marca.update(paused=caps["shell"][0].paused, mode=caps["hub"][0].mode)}
    run_loop(monkeypatch, lambda: app_hub.run(1, None, "criatorio_hub", "12:00"), caps, frames=10)
    assert marca == {"paused": False, "mode": "cercado"}


def test_loop_do_criatorio_sair_para_o_menu_pela_pausa(monkeypatch):
    from ui import app_hub
    caps = loop_capture(monkeypatch, app_hub)
    marca = {}
    ev = {3: key(pygame.K_ESCAPE), 5: key(pygame.K_DOWN), 6: key(pygame.K_DOWN), 7: key(pygame.K_RETURN)}
    caps["events"] = ev
    caps["script"] = {10: lambda: marca.update(mode=caps["hub"][0].mode, paused=caps["shell"][0].paused)}
    run_loop(monkeypatch, lambda: app_hub.run(1, None, "criatorio_hub", "12:00"), caps, frames=12)
    assert marca == {"mode": "menu", "paused": False}


# ------------------------------------------------------------------ transição (fade)
def tela(cor) -> pygame.Surface:
    s = pygame.Surface((32, 32))
    s.fill(cor)
    return s


@pytest.fixture(autouse=False)
def fade_on(monkeypatch):
    monkeypatch.delenv("CHAOSCATS_FADE", raising=False)


def test_fade_comeca_ao_trocar_a_chave_e_termina_na_cena_nova(fade_on):
    pygame.init()
    t = Transition(duration=0.2)
    t.apply(tela((255, 0, 0)), "a")
    assert not t.active
    novo = tela((0, 0, 255))
    t.apply(novo, "b")
    assert t.active and t.progress == 0.0
    assert novo.get_at((5, 5))[:3] == (255, 0, 0)                  # 1o quadro: ainda o antigo
    t.tick(1.0)
    fim = tela((0, 0, 255))
    t.apply(fim, "b")
    assert not t.active and fim.get_at((5, 5))[:3] == (0, 0, 255)


def test_fade_mistura_a_cena_antiga_com_a_nova_no_meio_do_caminho(fade_on):
    pygame.init()
    t = Transition(duration=0.2)
    t.apply(tela((255, 0, 0)), "a")
    t.apply(tela((0, 0, 255)), "b")
    t.tick(0.1)
    meio = tela((0, 0, 255))
    t.apply(meio, "b")
    r, _, b, *_ = meio.get_at((5, 5))
    assert 0 < r < 255 and 0 < b < 255
    assert meio.get_at((5, 5))[:3] not in ((255, 0, 0), (0, 0, 255))   # nem cena antiga nem nova pura


def test_fade_mesma_chave_nao_dissolve(fade_on):
    t = Transition(duration=0.2)
    t.apply(tela((255, 0, 0)), "a")
    t.apply(tela((0, 255, 0)), "a")
    assert not t.active


def test_fade_pulavel_por_skip_e_nunca_bloqueia(fade_on):
    t = Transition(duration=5.0)
    t.apply(tela((255, 0, 0)), "a")
    t.apply(tela((0, 0, 255)), "b")
    assert t.active
    t.skip()
    novo = tela((0, 0, 255))
    t.apply(novo, "b")
    assert not t.active and t.progress == 1.0 and novo.get_at((1, 1))[:3] == (0, 0, 255)


def test_fade_tick_negativo_nao_volta_no_tempo(fade_on):
    t = Transition(duration=0.2)
    t.apply(tela((1, 1, 1)), "a")
    t.apply(tela((2, 2, 2)), "b")
    t.tick(0.1)
    p = t.t
    t.tick(-5)
    assert t.t == p


@pytest.mark.parametrize("kw", [{"enabled": False}, {"duration": 0.0}])
def test_fade_desligado_troca_na_hora(fade_on, kw):
    t = Transition(**({"duration": 0.2} | kw))
    t.apply(tela((255, 0, 0)), "a")
    novo = tela((0, 0, 255))
    t.apply(novo, "b")
    assert not t.active and novo.get_at((1, 1))[:3] == (0, 0, 255)


def test_fade_desligado_por_variavel_de_ambiente(monkeypatch):
    monkeypatch.setenv("CHAOSCATS_FADE", "off")
    t = Transition(duration=0.2)
    assert t.enabled is False
    t.apply(tela((9, 9, 9)), "a")
    t.apply(tela((1, 1, 1)), "b")
    assert not t.active


def test_fade_usa_a_duracao_do_ui_timing(fade_on):
    from ui import timing
    timing.use(timing.Timing({"fade": {"scene": 0.37}}))
    try:
        assert Transition().duration == pytest.approx(0.37)
    finally:
        timing.use(None)


@pytest.mark.parametrize("ev", [pygame.event.Event(pygame.KEYDOWN, key=pygame.K_x, mod=0, unicode="x", scancode=0),
                                pygame.event.Event(pygame.MOUSEBUTTONDOWN, pos=(1, 1), button=1)])
def test_clique_ou_tecla_pula_o_fade_e_o_evento_segue_para_o_jogo(fade_on, tmp_path, ev):
    pygame.init()
    shell = Shell(None, Options(None, load=False), fade=True)
    shell.fade.apply(tela((255, 0, 0)), "a")
    shell.fade.apply(tela((0, 0, 255)), "b")
    assert shell.fade.active
    assert shell.handle(ev) is False                    # nao engole o clique
    assert not shell.fade.active


def test_shell_sem_fade_nunca_ativa(tmp_path):
    shell = Shell(None, Options(None, load=False), fade=False)
    shell.fade.apply(tela((0, 0, 0)), "a")
    shell.fade.apply(tela((9, 9, 9)), "b")
    assert shell.fade.active is False


# ------------------------------------------------------------------ log de erros
def explode(msg="boom") -> ValueError:
    try:
        raise ValueError(msg)
    except ValueError as e:
        return e


def test_log_grava_traceback_com_data_e_contexto(tmp_path):
    p = tmp_path / "pasta" / "errors.log"
    assert errors.log_exception(explode("falha-xyz"), "duelo", path=p) is True
    txt = p.read_text(encoding="utf-8")
    assert "Traceback" in txt and "ValueError: falha-xyz" in txt and "duelo" in txt
    assert "explode" in txt                                  # a pilha aparece
    import re
    assert re.search(r"=== \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", txt)


def test_log_acrescenta_sem_apagar_o_anterior(tmp_path):
    p = tmp_path / "errors.log"
    errors.log_exception(explode("primeiro"), path=p)
    errors.log_exception(explode("segundo"), path=p)
    txt = p.read_text(encoding="utf-8")
    assert "primeiro" in txt and "segundo" in txt and txt.index("primeiro") < txt.index("segundo")


def test_log_gira_acima_de_200kb(tmp_path):
    p = tmp_path / "errors.log"
    p.write_bytes(b"A" * (errors.MAX_BYTES + 1))
    errors.log_exception(explode("novo"), path=p)
    velho = tmp_path / errors.OLD_NAME
    assert velho.exists() and velho.stat().st_size == errors.MAX_BYTES + 1
    novo = p.read_text(encoding="utf-8")
    assert "novo" in novo and "AAAA" not in novo and len(novo) < 5000
    assert 190 * 1024 <= errors.MAX_BYTES <= 210 * 1024


def test_log_nao_gira_abaixo_do_limite(tmp_path):
    p = tmp_path / "errors.log"
    p.write_bytes(b"A" * (errors.MAX_BYTES - 100))
    errors.log_exception(explode("x"), path=p)
    assert not (tmp_path / errors.OLD_NAME).exists()


def test_rotacao_sobrescreve_o_log_antigo(tmp_path):
    p, velho = tmp_path / "errors.log", tmp_path / errors.OLD_NAME
    velho.write_text("MUITO ANTIGO")
    p.write_bytes(b"B" * (errors.MAX_BYTES + 5))
    errors.log_exception(explode(), path=p)
    assert velho.read_bytes().startswith(b"BBBB")


def test_falha_de_escrita_e_silenciosa(tmp_path):
    arquivo = tmp_path / "arq"
    arquivo.write_text("x")
    assert errors.log_exception(explode(), path=arquivo / "sub" / "errors.log") is False


def test_falha_ao_abrir_o_arquivo_e_silenciosa(tmp_path, monkeypatch):
    def nega(self, *a, **k):
        raise PermissionError("sem permissao")
    monkeypatch.setattr(Path, "open", nega)
    assert errors.log_exception(explode(), path=tmp_path / "e.log") is False


def test_log_padrao_vai_para_a_pasta_de_prefs_isolada(prefs_dir):
    errors.log_exception(explode("padrao"))
    assert errors.log_path() == prefs_dir / "errors.log"
    assert "padrao" in (prefs_dir / "errors.log").read_text(encoding="utf-8")


def test_no_navegador_o_log_e_ignorado(monkeypatch, prefs_dir):
    monkeypatch.setattr(sys, "platform", "emscripten")
    assert errors.log_exception(explode()) is False
    assert not (prefs_dir / "errors.log").exists()


def test_guarded_grava_e_relanca_sob_pytest(prefs_dir):
    async def quebra():
        raise RuntimeError("explodiu-no-loop")
    with pytest.raises(RuntimeError, match="explodiu-no-loop"):
        asyncio.run(errors.guarded(quebra(), "teste"))
    assert "explodiu-no-loop" in (prefs_dir / "errors.log").read_text(encoding="utf-8")


def test_guarded_em_producao_mostra_a_tela_de_falha_e_nao_relanca(monkeypatch, prefs_dir):
    visto = {}

    async def fake_crash(exc, logged):
        visto["exc"], visto["logged"] = exc, logged

    monkeypatch.setattr(errors, "reraise_mode", lambda: False)
    monkeypatch.setattr(errors, "crash_screen", fake_crash)
    monkeypatch.setattr(pygame, "quit", lambda: None)

    async def quebra():
        raise RuntimeError("em-producao")
    asyncio.run(errors.guarded(quebra(), "teste"))
    assert str(visto["exc"]) == "em-producao" and visto["logged"] is True


def test_guarded_nao_interfere_quando_nao_ha_erro():
    feito = []

    async def ok():
        feito.append(1)
    asyncio.run(errors.guarded(ok()))
    assert feito == [1]


@pytest.mark.parametrize("logged", [True, False])
def test_tela_de_falha_desenha_sem_levantar(logged):
    pygame.init()
    errors.draw_crash(pygame.Surface((960, 540)), explode("a" * 300 + "\nlinha2"), logged)
