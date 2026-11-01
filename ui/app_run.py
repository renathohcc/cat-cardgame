"""Janela da mini-run (`python -m ui --run`): mapa, duelo, draft e fim. Compativel com pygbag."""
from __future__ import annotations

import asyncio
import math

import pygame

from ui import audio, errors, layout as L, scenes_run, widgets as Wd
from ui.shell import Shell
from ui.app import DRAG_THRESHOLD
from ui.display import Display
from ui.controller import load_game_content
from ui.hub_controller import DEFAULT_SAVE
from ui.render import UIState
from ui.render_run import draw_run_frame
from ui.run_controller import RunController
from ui.theme import H, W


def screenshot(path: str, seed: int, scene: str) -> None:
    from pathlib import Path
    pygame.init()
    made = scenes_run.make(seed, scene)
    if made is None:
        raise SystemExit(f"não consegui montar a cena {scene} com seed {seed}")
    rc, ui = made
    canvas = pygame.Surface((W, H))
    draw_run_frame(canvas, rc, ui)
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(canvas, str(out))


async def run(seed: int, scene: str | None = None) -> None:
    await errors.guarded(_run(seed, scene), "mini-run")


async def _run(seed: int, scene: str | None = None) -> None:
    pygame.init()
    audio.setup()
    hover = audio.HoverSound()
    disp = Display("mini-run")
    shell = Shell(disp)
    clock = pygame.time.Clock()
    ui = UIState()
    if scene and scene != "run":
        made = scenes_run.make(seed, scene)
        if made is None:
            raise SystemExit(f"não consegui montar a cena {scene} com seed {seed}")
        rc, ui = made
        ui.mouse = (-100, -100)
    else:
        rc = RunController(load_game_content(), seed)
    canvas = pygame.Surface((W, H))
    press: tuple[tuple | None, tuple[int, int]] | None = None

    def internal(pos: tuple[int, int]) -> tuple[int, int]:
        return disp.to_internal(pos)

    running = True
    while running and not rc.wants_quit:
        dt = clock.tick(60) / 1000.0
        duel = rc.duel_ctrl if rc.screen == "duel" and not rc.quit_confirm else None
        for ev in pygame.event.get():
            audio.on_event(ev)
            if ev.type == pygame.QUIT:
                running = False
            elif shell.handle(ev):
                pass
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    if not rc.escape():
                        shell.open_pause(run=True)
                    ui.drag = None
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    rc.confirm_key()
                elif duel is not None and ev.key == pygame.K_SPACE:
                    duel.space_key()
                elif duel is not None and ev.key == pygame.K_e:
                    duel.request_end_turn()
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                pos = internal(ev.pos)
                if ev.button == 1:
                    press = (rc.hit(pos), pos)
                elif ev.button == 3:
                    if duel is not None:
                        duel.cancel()
                    else:
                        rc.cancel()
                    ui.drag = None
                    press = None
            elif ev.type == pygame.MOUSEMOTION:
                pos = internal(ev.pos)
                ui.mouse = pos
                hover.update(rc.hit(pos))
                if duel is not None and press and ui.drag is None and press[0] is not None:
                    if math.dist(pos, press[1]) > DRAG_THRESHOLD and duel.drag_start(press[0]):
                        ui.drag = (press[0], pos)
                if ui.drag is not None:
                    ui.drag = (ui.drag[0], pos)
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                pos = internal(ev.pos)
                ui.mouse = pos
                elem = rc.hit(pos)
                if ui.drag is not None and duel is not None:
                    duel.drop(elem)
                    ui.drag = None
                elif press is not None and elem == press[0]:
                    rc.click(elem)
                press = None
        act = shell.take_action()
        if act == "quit":
            running = False
        elif act == "abandon":
            rc.request_abandon()
        if rc.screen != "duel":
            ui.drag = None
        shell.sync(ui)
        if rc.duel_ctrl is not None:
            rc.duel_ctrl.enemy_speed = ui.enemy_speed
            if not shell.paused:
                rc.duel_ctrl.speed = 6.0 if pygame.key.get_pressed()[pygame.K_SPACE] else 1.0
        if not shell.paused:                         # pausa: nem turno, nem animacao, nem relogio
            rc.update(dt)
            ui.t += dt
        audio.music(rc.audio_context())
        audio.update(dt)
        shell.tick(dt)
        draw_run_frame(canvas, rc, ui)
        Wd.mute_badge(canvas)
        shell.finish(canvas, rc.scene_key())
        disp.render(canvas)
        pygame.display.flip()
        await asyncio.sleep(0)
    pygame.quit()
