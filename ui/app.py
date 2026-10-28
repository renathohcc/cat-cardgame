"""Janela pygame: loop, escala inteira, mouse/teclado -> controlador. Compativel com pygbag."""
from __future__ import annotations

import asyncio
import math
from pathlib import Path

import pygame

from ui import layout as L, scenes, scenes_novas
from ui.controller import Controller, load_game_content
from ui.render import UIState, draw_frame
from ui.theme import H, W

from ui.display import START_SIZE, Display, render_scaled  # noqa: F401  (re-export)

DRAG_THRESHOLD = 4


def make_controller(seed: int, enemy: str | None = None) -> Controller:
    """`enemy` None = sorteia um inimigo real pelo seed; senao o id de data/enemies.json."""
    content = load_game_content()
    if enemy is None:
        return Controller(content, seed, enemy_random=True)
    if enemy not in content.enemies:
        raise SystemExit(f"inimigo desconhecido: {enemy} (use: {', '.join(sorted(content.enemies))})")
    return Controller(content, seed, enemy_id=enemy)


def screenshot(path: str, seed: int, scene: str, enemy: str | None = None) -> None:
    pygame.init()
    if scene in scenes_novas.NEW_SCENES:
        ctrl = scenes_novas.make(seed, scene, enemy)
        if ctrl is None:
            raise SystemExit(f"não consegui montar a cena {scene} com seed {seed}")
        ui = scenes_novas.build(ctrl, scene)
    else:
        ctrl = make_controller(seed, enemy)
        ui = scenes.build(ctrl, scene)
    canvas = pygame.Surface((W, H))
    draw_frame(canvas, ctrl, ui)
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(pygame.transform.scale(canvas, (W * 3, H * 3)), str(out))


async def run(seed: int, enemy: str | None = None) -> None:
    pygame.init()
    disp = Display("duelo de teste")
    clock = pygame.time.Clock()
    ctrl = make_controller(seed, enemy)
    canvas = pygame.Surface((W, H))
    ui = UIState()
    press: tuple[tuple | None, tuple[int, int]] | None = None

    def internal(pos: tuple[int, int]) -> tuple[int, int]:
        return disp.to_internal(pos)

    def hit(pos: tuple[int, int]) -> tuple | None:
        return L.hit_test(pos, len(ctrl.shown.me.hand), final=ctrl.final_visible, confirm=ctrl.confirming)

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif disp.handle_key(ev):
                pass
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    ctrl.cancel()
                    ui.drag = None
                elif ev.key == pygame.K_SPACE:
                    ctrl.skip()
                elif ev.key == pygame.K_e:
                    ctrl.request_end_turn()
                elif ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and ctrl.final_visible:
                    ctrl.again()
                elif ev.key == pygame.K_r and ctrl.final_visible:
                    ctrl.repeat()
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                pos = internal(ev.pos)
                if ev.button == 1:
                    press = (hit(pos), pos)
                elif ev.button == 3:
                    ctrl.cancel()
                    ui.drag = None
                    press = None
            elif ev.type == pygame.MOUSEMOTION:
                pos = internal(ev.pos)
                ui.mouse = pos
                if press and ui.drag is None and press[0] is not None:
                    if math.dist(pos, press[1]) > DRAG_THRESHOLD and ctrl.drag_start(press[0]):
                        ui.drag = (press[0], pos)
                if ui.drag is not None:
                    ui.drag = (ui.drag[0], pos)
            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                pos = internal(ev.pos)
                ui.mouse = pos
                elem = hit(pos)
                if ui.drag is not None:
                    ctrl.drop(elem)
                    ui.drag = None
                elif press is not None and elem == press[0]:
                    ctrl.click(elem)
                press = None
        ctrl.speed = 6.0 if pygame.key.get_pressed()[pygame.K_SPACE] else 1.0
        ctrl.update(dt)
        ui.t += dt
        draw_frame(canvas, ctrl, ui)
        disp.render(canvas)
        pygame.display.flip()
        await asyncio.sleep(0)
    pygame.quit()
