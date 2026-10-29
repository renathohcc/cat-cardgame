"""Janela do hub (`python -m ui --jogo`): menu, colecao, run e resultado. Compativel com pygbag."""
from __future__ import annotations

import asyncio
import math
from datetime import datetime
from pathlib import Path

import pygame

from ui import audio, layout as L, scenes_hub, widgets as Wd
from ui.app import DRAG_THRESHOLD
from ui.display import Display
from ui.controller import load_game_content
from ui.daycycle import fixed_clock
from ui.hub_controller import DEFAULT_SAVE, HubController
from ui.render import UIState
from ui.render_hub import draw_hub_frame
from ui.theme import H, W


def screenshot(path: str, seed: int, scene: str, hora: str | None = None) -> None:
    pygame.init()
    hub, ui = scenes_hub.make(seed, scene, hora)
    canvas = pygame.Surface((W, H))
    draw_hub_frame(canvas, hub, ui)
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(canvas, str(out))


async def run(seed: int, save_path: Path | str | None = DEFAULT_SAVE, scene: str | None = None,
              hora: str | None = None) -> None:
    """`hora` ("HH:MM") fixa a hora do cercado; sem ela usa a hora do computador."""
    pygame.init()
    audio.setup(legacy_dirs=(Path(save_path).parent,) if save_path else ())
    hover = audio.HoverSound()
    disp = Display()
    clock = pygame.time.Clock()
    if scene:
        hub, ui = scenes_hub.make(seed, scene, hora)
        ui.mouse = (-100, -100)
    else:
        now_fn = fixed_clock(hora) if hora else datetime.now
        hub, ui = HubController(load_game_content(), save_path, seed, clock=now_fn), UIState()
    canvas = pygame.Surface((W, H))
    press: tuple[tuple | None, tuple[int, int]] | None = None
    pygame.key.start_text_input()

    def internal(pos: tuple[int, int]) -> tuple[int, int]:
        return disp.to_internal(pos)

    running = True
    while running and not hub.wants_quit:
        dt = clock.tick(60) / 1000.0
        rc = hub.rc if hub.mode == "run" else None
        duel = rc.duel_ctrl if rc and rc.screen == "duel" and not rc.quit_confirm else None
        for ev in pygame.event.get():
            audio.on_event(ev)
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.TEXTINPUT:
                hub.text_input(ev.text)
            elif ev.type == pygame.MOUSEWHEEL:
                hub.scroll(-ev.y)
            elif disp.handle_key(ev):
                pass
            elif ev.type == pygame.KEYDOWN and audio.handle_key(ev.key, hub.editing_text):
                pass
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    hub.key_escape()
                    ui.drag = None
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    hub.key_enter()
                elif ev.key == pygame.K_BACKSPACE:
                    hub.backspace()
                elif ev.key in (pygame.K_UP, pygame.K_DOWN) and hub.mode == "colecao":
                    hub.scroll(-1 if ev.key == pygame.K_UP else 1)
                elif duel is not None and ev.key == pygame.K_SPACE:
                    duel.skip()
                elif duel is not None and ev.key == pygame.K_e:
                    duel.request_end_turn()
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                pos = internal(ev.pos)
                if ev.button == 1:
                    press = (hub.hit(pos), pos)
                elif ev.button == 3 and rc is not None:
                    if duel is not None:
                        duel.cancel()
                    else:
                        rc.cancel()
                    hub._check_run_end()
                    ui.drag = None
                    press = None
            elif ev.type == pygame.MOUSEMOTION:
                pos = internal(ev.pos)
                ui.mouse = pos
                hover.update(hub.hit(pos))
                if duel is not None and press and ui.drag is None and press[0] is not None:
                    if math.dist(pos, press[1]) > DRAG_THRESHOLD and duel.drag_start(press[0]):
                        ui.drag = (press[0], pos)
                if ui.drag is not None:
                    ui.drag = (ui.drag[0], pos)
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                pos = internal(ev.pos)
                ui.mouse = pos
                elem = hub.hit(pos)
                if ui.drag is not None and duel is not None:
                    duel.drop(elem)
                    ui.drag = None
                elif press is not None and elem == press[0]:
                    hub.click(elem)
                press = None
        if hub.mode != "run":
            ui.drag = None
        if hub.rc is not None and hub.rc.duel_ctrl is not None:
            hub.rc.duel_ctrl.speed = 6.0 if pygame.key.get_pressed()[pygame.K_SPACE] else 1.0
        hub.update(dt)
        audio.music(hub.audio_context())
        audio.update(dt)
        ui.t += dt
        draw_hub_frame(canvas, hub, ui)
        Wd.mute_badge(canvas)
        disp.render(canvas)
        pygame.display.flip()
        await asyncio.sleep(0)
    pygame.quit()
