"""Casca comum dos loops (T12.4): eventos globais, pausa/opcoes, fade e opcoes ligadas na UI.

Os tres loops (`app`, `app_run`, `app_hub`) criam um `Shell` e chamam, por quadro:
    shell.handle(ev, typing)   para cada evento (tela cheia, mudo, camada de pausa/opcoes, pula o fade)
    shell.take_action()        acao pedida pela pausa: "abandon" | "menu" | "quit"
    shell.sync(ui)             liga opcoes no UIState; com a pausa aberta esconde o mouse do jogo
    shell.paused               True = nao atualizar o jogo nem o relogio de animacao
    shell.finish(canvas, key)  fade entre cenas + camada de pausa/opcoes por cima
Sem regra de jogo aqui.
"""
from __future__ import annotations

import pygame

from ui import audio
from ui.display import Display
from ui.options import Options
from ui.pause import Overlay
from ui.transition import Transition

_SKIP_FADE = (pygame.MOUSEBUTTONDOWN, pygame.KEYDOWN)


class Shell:
    def __init__(self, display: Display | None = None, options: Options | None = None,
                 fade: bool = True) -> None:
        self.disp = display
        self.options = options or Options.from_audio()
        self.overlay = Overlay(self.options, display)
        self.fade = Transition(enabled=fade)
        if display is not None and self.options.fullscreen:
            display.toggle_fullscreen()
            self.options.fullscreen = display.fullscreen

    # ------------------------------------------------------------ estado
    @property
    def paused(self) -> bool:
        return self.overlay.open

    def open_pause(self, *, run: bool = False, menu: bool = False) -> None:
        self.overlay.open_pause(run=run, menu=menu)

    def open_options(self) -> None:
        self.overlay.open_options()

    def take_action(self) -> str | None:
        return self.overlay.take_action()

    # ------------------------------------------------------------ eventos
    def handle(self, ev: pygame.event.Event, typing: bool = False) -> bool:
        """True = evento consumido (tela cheia, mudo ou camada aberta). Clique/tecla pula o fade
        mas o evento segue para o jogo (o fade nunca engole cliques)."""
        if ev.type in _SKIP_FADE:
            self.fade.skip()
        if self.disp is not None and self.disp.handle_key(ev):
            self.options.set_fullscreen(self.disp.fullscreen)
            return True
        if ev.type == pygame.KEYDOWN and audio.handle_key(ev.key, typing):
            return True
        to_internal = self.disp.to_internal if self.disp is not None else (lambda p: p)
        return self.overlay.handle(ev, to_internal)

    # ------------------------------------------------------------ quadro
    def sync(self, ui) -> None:
        self.options.apply(ui)
        if self.paused:
            ui.mouse = (-100, -100)
            ui.drag = None

    def tick(self, dt: float) -> None:
        self.fade.tick(dt)

    def finish(self, canvas: pygame.Surface, scene_key: str) -> None:
        """Depois de desenhar a cena (e o selo de mudo): fade e, por cima, a pausa/opcoes."""
        self.fade.apply(canvas, scene_key)
        self.overlay.draw(canvas)
