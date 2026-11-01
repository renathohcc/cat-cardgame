"""Menu de pausa e tela de opcoes como camada sobre qualquer tela (T12.4).

`Overlay` guarda so estado de apresentacao: qual vista esta aberta (pausa, opcoes, confirmacao),
o foco do teclado e as acoes pedidas ao loop (`take_action`): "abandon" | "menu" | "quit".
O loop decide o que cada acao faz (chama `RunController`/`HubController`); nenhuma regra aqui.
Enquanto aberta, `Overlay.handle` consome teclado e mouse e o loop nao atualiza o jogo.

Contexto da pausa (`open_pause`): `run` (ha run em andamento: mostra ABANDONAR RUN), `menu`
(hub: mostra SAIR PARA O MENU). SAIR DO JOGO sempre aparece; dentro de uma run pede confirmacao
(a run em andamento se perde, como ao fechar a janela).
"""
from __future__ import annotations

import pygame

from ui import audio, font, layout_opts as LO, widgets as Wd
from ui.options import Options, OptionsScreen
from ui.theme import C

LABEL = {"continue": "CONTINUAR", "options": "OPÇÕES", "abandon": "ABANDONAR RUN",
         "menu": "SAIR PARA O MENU", "quit": "SAIR DO JOGO"}
DANGER = (160, 64, 64)
ASK_TEXT = {"quit": ("SAIR DO JOGO?", "A run em andamento será perdida.")}


class Overlay:
    def __init__(self, options: Options, display=None) -> None:
        self.options = options
        self.screen = OptionsScreen(options, display)
        self.view: str | None = None          # None | "pause" | "options" | "ask"
        self.items: list[str] = []
        self.focus = 0
        self.from_pause = False               # opcoes abertas pela pausa (Voltar volta a ela)
        self.ask_what = ""
        self.ask_focus = 1                    # NAO por padrao
        self.mouse: tuple[int, int] = (-100, -100)
        self.actions: list[str] = []
        self.ask_run = False                  # pausa dentro de uma run (SAIR pede confirmacao)
        self._press: tuple | None = None
        self.hover = audio.HoverSound()

    # ------------------------------------------------------------ estado
    @property
    def open(self) -> bool:
        return self.view is not None

    def take_action(self) -> str | None:
        return self.actions.pop(0) if self.actions else None

    def open_pause(self, *, run: bool = False, menu: bool = False) -> None:
        self.items = ["continue", "options"] + (["abandon"] if run else []) + (["menu"] if menu else []) + ["quit"]
        self.ask_run = run
        self.view, self.focus, self.from_pause = "pause", 0, True
        audio.sfx("ui_open_modal")

    def open_options(self) -> None:
        self.view, self.from_pause = "options", False
        self.screen.focus = 0
        audio.sfx("ui_open_modal")

    def close(self) -> None:
        self.view = None
        self.hover.last = None

    def _back_from_options(self) -> None:
        self.view = "pause" if self.from_pause else None

    # ------------------------------------------------------------ entrada
    def hit(self, pos: tuple[int, int]) -> tuple | None:
        if self.view == "pause":
            return LO.pause_hit(pos, self.items)
        if self.view == "options":
            return self.screen.hit(pos)
        if self.view == "ask":
            return LO.ask_hit(pos)
        return None

    def handle(self, ev: pygame.event.Event, to_internal) -> bool:
        """Processa um evento com a camada aberta. True = consumido (sempre, enquanto aberta)."""
        if not self.open:
            return False
        t = ev.type
        if t == pygame.KEYDOWN:
            self._key(ev.key)
        elif t == pygame.MOUSEMOTION:
            self.mouse = to_internal(ev.pos)
            elem = self.hit(self.mouse)
            self.hover.update(elem)
            self._focus_from(elem)
        elif t == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            self.mouse = to_internal(ev.pos)
            self._press = self.hit(self.mouse)
        elif t == pygame.MOUSEBUTTONUP and ev.button == 1:
            self.mouse = to_internal(ev.pos)
            elem = self.hit(self.mouse)
            if elem is not None and elem == self._press:
                self.click(elem)
            self._press = None
        elif t == pygame.MOUSEBUTTONDOWN and ev.button == 3:
            self._key(pygame.K_ESCAPE)
        return True

    def _focus_from(self, elem: tuple | None) -> None:
        if elem is None:
            return
        if self.view == "pause":
            self.focus = self.items.index(elem[1])
        elif self.view == "options":
            self.screen.hover(elem)
        elif self.view == "ask":
            self.ask_focus = 0 if elem == ("ask_yes",) else 1

    def _key(self, key: int) -> None:
        if self.view == "options":
            if self.screen.key(key) == "back":
                self._back_from_options()
        elif self.view == "ask":
            self._key_ask(key)
        else:
            self._key_pause(key)

    def _key_pause(self, key: int) -> None:
        n = len(self.items)
        if key == pygame.K_ESCAPE:
            audio.sfx("ui_back")
            self.close()
        elif key == pygame.K_UP:
            self.focus = (self.focus - 1) % n
        elif key == pygame.K_DOWN:
            self.focus = (self.focus + 1) % n
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.click(("pause", self.items[self.focus]))

    def _key_ask(self, key: int) -> None:
        if key == pygame.K_ESCAPE:
            self.click(("ask_no",))
        elif key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN, pygame.K_TAB):
            self.ask_focus = 1 - self.ask_focus
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            self.click(("ask_yes",) if self.ask_focus == 0 else ("ask_no",))

    def click(self, elem: tuple) -> None:
        if self.view == "options":
            if self.screen.click(elem) == "back":
                self._back_from_options()
            return
        if elem[0] == "ask_yes":
            audio.sfx("ui_click")
            self.actions.append(self.ask_what)
            self.close()
        elif elem[0] == "ask_no":
            audio.sfx("ui_back")
            self.view = "pause"
        elif elem[0] == "pause":
            self._pause_pick(elem[1])

    def _pause_pick(self, name: str) -> None:
        if name == "continue":
            audio.sfx("ui_back")
            self.close()
        elif name == "options":
            audio.sfx("ui_click")
            self.view = "options"
            self.screen.focus = 0
        elif name == "quit" and self.ask_run:
            audio.sfx("ui_open_modal")
            self.view, self.ask_what, self.ask_focus = "ask", "quit", 1
        else:
            audio.sfx("ui_click")
            self.actions.append(name)
            self.close()

    # ------------------------------------------------------------ desenho
    def draw(self, surf: pygame.Surface, canvas_mouse=None) -> None:
        if not self.open:
            return
        mouse = self.mouse
        if self.view == "options":
            self.screen.draw(surf, mouse)
        elif self.view == "ask":
            self._draw_ask(surf, mouse)
        else:
            self._draw_pause(surf, mouse)

    def _draw_pause(self, surf: pygame.Surface, mouse) -> None:
        n = len(self.items)
        p = LO.pause_panel(n)
        Wd.modal(surf, p, "PAUSA")
        for i, name in enumerate(self.items):
            Wd.button(surf, LO.pause_button(i, n), LABEL[name], mouse, scale=2,
                      base=DANGER if name in ("abandon", "quit") else None, focus=i == self.focus)
        font.draw(surf, "ESC continua   M muda o som", p.centerx, p.bottom - 20, C["dim"], 1, "center")

    def _draw_ask(self, surf: pygame.Surface, mouse) -> None:
        head, body = ASK_TEXT.get(self.ask_what, ("CONFIRMAR?", ""))
        p = LO.ask_panel()
        Wd.modal(surf, p, head)
        font.draw(surf, body, p.centerx, p.y + 80, C["text"], 1, "center")
        for name, r in LO.ask_buttons().items():
            yes = name == "ask_yes"
            Wd.button(surf, r, "SIM, SAIR" if yes else "NÃO, VOLTAR", mouse, scale=2,
                      base=DANGER if yes else None, focus=(self.ask_focus == 0) == yes)
