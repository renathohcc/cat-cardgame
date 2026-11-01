"""Cenas de captura da T12.4: pausa, opcoes, botoes nos 4 estados e uma transicao no meio.

`python -m ui --seed 3 --screenshot out.png --cena pausa|pausa_cercado|opcoes|botoes|transicao`.
Tudo em memoria (prefs nao sao lidas nem gravadas) e sem janela.
"""
from __future__ import annotations

import pygame

from ui import font, scenes, scenes_hub, widgets as Wd
from ui.controller import load_game_content
from ui.options import Options
from ui.pause import Overlay
from ui.render import UIState, draw_frame
from ui.render_hub import draw_hub_frame
from ui.theme import C, H, W
from ui.transition import Transition

SCENES = ("pausa", "pausa_cercado", "opcoes", "opcoes_pausa", "botoes", "transicao")


def _duel_canvas(seed: int) -> tuple[pygame.Surface, UIState]:
    from ui.app import make_controller
    ctrl = make_controller(seed)
    ui = scenes.build(ctrl, "inicio")
    ui.mouse = (-100, -100)
    canvas = pygame.Surface((W, H))
    draw_frame(canvas, ctrl, ui)
    return canvas, ui


def _hub_canvas(seed: int, name: str) -> pygame.Surface:
    hub, ui = scenes_hub.make(seed, name)
    ui.mouse = (-100, -100)
    canvas = pygame.Surface((W, H))
    draw_hub_frame(canvas, hub, ui)
    return canvas


def _overlay() -> Overlay:
    ov = Overlay(Options(None, load=False))
    ov.mouse = (-100, -100)
    return ov


def _buttons(canvas: pygame.Surface) -> None:
    Wd.fill_background(canvas)
    Wd.title(canvas, "BOTÕES: 4 ESTADOS", W // 2, 40, C["warn"], 3, "center")
    states = (("rest", "REPOUSO"), ("hover", "HOVER"), ("pressed", "PRESSIONADO"), ("disabled", "DESABILITADO"))
    for col, (st, label) in enumerate(states):
        x = 60 + col * 220
        font.draw(canvas, label, x + 80, 110, C["dim"], 1, "center")
        for row, (base, name) in enumerate(((None, "PADRÃO"), ((160, 64, 64), "PERIGO"), (C["card"], "NEUTRO"))):
            Wd.button(canvas, pygame.Rect(x, 140 + row * 70, 160, 48), name, (-100, -100), scale=2, base=base, state=st)
    Wd.button(canvas, pygame.Rect(W // 2 - 90, 380, 180, 48), "FOCO (TECLADO)", (-100, -100), scale=1, focus=True)


def shot(path: str, seed: int, scene: str) -> None:
    pygame.init()
    canvas = pygame.Surface((W, H))
    if scene == "botoes":
        _buttons(canvas)
    elif scene == "transicao":
        fade = Transition(0.2, enabled=True)
        old = _hub_canvas(seed, "menu")
        new = _hub_canvas(seed, "criatorio_hub")
        fade.apply(old, "menu")             # guarda o quadro antigo
        fade.start()
        fade.tick(0.1)                      # metade do fade: as duas cenas misturadas
        canvas.blit(new, (0, 0))
        fade.apply(canvas, "menu")
    elif scene == "pausa":
        canvas, _ = _duel_canvas(seed)
        ov = _overlay()
        ov.open_pause(run=True)
        ov.focus = 0
        ov.draw(canvas)
    elif scene == "pausa_cercado":
        canvas = _hub_canvas(seed, "criatorio_hub")
        ov = _overlay()
        ov.open_pause(menu=True)
        ov.focus = 1
        ov.draw(canvas)
    else:
        canvas = _hub_canvas(seed, "menu")
        ov = _overlay()
        ov.open_pause(menu=True)
        if scene == "opcoes":
            ov.from_pause = False
        ov.view = "options"
        ov.screen.focus = 4
        ov.mouse = (-100, -100)
        ov.draw(canvas)
    from pathlib import Path
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(canvas, str(out))
