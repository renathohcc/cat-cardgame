"""Fumaca dos loops reais (async) em modo headless: roda N quadros e fecha com QUIT."""
from __future__ import annotations

import asyncio
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
import pytest


def _run_frames(monkeypatch, coro_fn, n: int = 5) -> int:
    frames = [0]
    real_flip = pygame.display.flip

    def flip() -> None:
        real_flip()
        frames[0] += 1
        if frames[0] >= n:
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    monkeypatch.setattr(pygame.display, "flip", flip)
    asyncio.run(coro_fn())
    return frames[0]


@pytest.mark.parametrize("hora", [None, "22:00"])
def test_loop_do_jogo_hub(monkeypatch, hora):
    from ui.app_hub import run
    assert _run_frames(monkeypatch, lambda: run(1, None, None, hora)) >= 5


def test_loop_do_hub_em_cena_criatorio(monkeypatch):
    from ui.app_hub import run
    assert _run_frames(monkeypatch, lambda: run(1, None, "criatorio_hub", "18:15")) >= 5


def test_loop_do_duelo(monkeypatch):
    from ui.app import run
    assert _run_frames(monkeypatch, lambda: run(1, None)) >= 5


def test_loop_da_mini_run(monkeypatch):
    from ui.app_run import run
    assert _run_frames(monkeypatch, lambda: run(1)) >= 5


# ------------------------------------------------------------------ cercado com relogio de verdade (T9.14)
def _hub_cercado(clock):
    from random import Random
    from core import new_game
    from ui.controller import load_game_content
    from ui.hub_controller import HubController
    content = load_game_content()
    h = HubController(content, None, 5, ai_delay=0.0, clock=clock)
    h.adopt_save(new_game(content, Random(5)))
    return h


def test_cercado_com_relogio_real_roda_updates_e_draws_sem_crash():
    from datetime import datetime
    from ui.render import UIState
    from ui.render_hub import draw_hub_frame
    from ui.theme import H, W
    pygame.init()
    h = _hub_cercado(datetime.now)               # hora=None no jogo => datetime.now
    h.enter_pen()
    assert h.mode == "cercado" and h.pen is not None
    surf, ui = pygame.Surface((W, H)), UIState()
    for i in range(240):
        h.update(1 / 60)
        ui.t += 1 / 60
        if i % 20 == 0:
            draw_hub_frame(surf, h, ui)
    h.open_ficha(h.pen.shown[0])
    for _ in range(30):
        h.update(1 / 60)
        draw_hub_frame(surf, h, ui)


def test_draw_ficha_nao_altera_a_selecao_da_colecao():
    from ui.render import UIState
    from ui.render_pen import draw_ficha
    from ui.theme import H, W
    pygame.init()
    h = _hub_cercado(None)
    h.enter_pen()
    a, b = h.pen.shown[0], h.pen.shown[1]
    h.open_ficha(a)
    assert h.col.selected == a
    h.col.selected = b                            # outra selecao: o desenho nao pode sobrescrever
    draw_ficha(pygame.Surface((W, H)), h, UIState())
    assert h.col.selected == b
