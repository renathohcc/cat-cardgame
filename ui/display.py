"""Apresentacao: escala fracionaria com letterbox, mouse -> coordenadas internas e fullscreen.

Funcoes puras (`dest_rect`, `to_internal`, `inside`) + `Display` (estado de janela/tela cheia).
Sem threads e sem disco: compativel com pygbag.
"""
from __future__ import annotations

import pygame

from ui.theme import H, W

START_SIZE = (W * 3 // 2, H * 3 // 2)      # 1440x810
MIN_SIZE = (W // 2, H // 2)
TITLE = "Chaoscats"


def dest_rect(win_size: tuple[int, int]) -> tuple[int, int, int, int]:
    """(x, y, w, h) do canvas na janela: maior escala (fracionaria) 16:9 que cabe, centralizado."""
    ww, wh = max(1, win_size[0]), max(1, win_size[1])
    if ww * H <= wh * W:  # limitado pela largura
        w, h = ww, max(1, ww * H // W)
    else:
        w, h = max(1, wh * W // H), wh
    return (ww - w) // 2, (wh - h) // 2, w, h


def to_internal(pos: tuple[int, int], win_size: tuple[int, int]) -> tuple[int, int]:
    """Mouse na janela -> coordenadas internas. Nas faixas pretas sai de [0,W) x [0,H)."""
    x, y, w, h = dest_rect(win_size)
    return ((pos[0] - x) * W // w, (pos[1] - y) * H // h)


def inside(pos: tuple[int, int]) -> bool:
    return 0 <= pos[0] < W and 0 <= pos[1] < H


def render_scaled(canvas: pygame.Surface, screen: pygame.Surface) -> None:
    x, y, w, h = dest_rect(screen.get_size())
    screen.fill((0, 0, 0))
    screen.blit(pygame.transform.scale(canvas, (w, h)), (x, y))  # vizinho mais proximo


def caption(suffix: str = "") -> str:
    return f"{TITLE} - {suffix}" if suffix else TITLE


class Display:
    """Cria a janela, alterna tela cheia (F11 / Alt+Enter) e converte o mouse."""

    def __init__(self, suffix: str = "") -> None:
        self.fullscreen = False
        self.windowed_size = START_SIZE
        self.windowed_pos: tuple[int, int] | None = None
        pygame.display.set_caption(caption(suffix))
        pygame.display.set_mode(START_SIZE, pygame.RESIZABLE)
        try:
            from pygame._sdl2.video import Window
            Window.from_display_module().minimum_size = MIN_SIZE
        except Exception:
            pass

    @property
    def size(self) -> tuple[int, int]:
        return pygame.display.get_surface().get_size()

    def to_internal(self, pos: tuple[int, int]) -> tuple[int, int]:
        return to_internal(pos, self.size)

    def render(self, canvas: pygame.Surface) -> None:
        render_scaled(canvas, pygame.display.get_surface())

    def handle_key(self, ev: pygame.event.Event) -> bool:
        """True se a tecla era de tela cheia (F11 ou Alt+Enter) e foi consumida."""
        if ev.type != pygame.KEYDOWN:
            return False
        alt_enter = ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and bool(ev.mod & pygame.KMOD_ALT)
        if ev.key == pygame.K_F11 or alt_enter:
            self.toggle_fullscreen()
            return True
        return False

    def _window_pos(self) -> tuple[int, int] | None:
        try:
            from pygame._sdl2.video import Window
            return tuple(Window.from_display_module().position)  # type: ignore[return-value]
        except Exception:
            return None

    def _restore_pos(self) -> None:
        if self.windowed_pos is None:
            return
        try:
            from pygame._sdl2.video import Window
            Window.from_display_module().position = self.windowed_pos
        except Exception:
            pass

    def toggle_fullscreen(self) -> None:
        try:
            if not self.fullscreen:
                self.windowed_size = self.size
                self.windowed_pos = self._window_pos()
                sizes = pygame.display.get_desktop_sizes()
                pygame.display.set_mode(sizes[0] if sizes else (0, 0), pygame.FULLSCREEN)
                self.fullscreen = True
            else:
                pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
                self.fullscreen = False
                self._restore_pos()
        except Exception:
            # falhou: continua em janela, sem derrubar o jogo
            self.fullscreen = False
            try:
                pygame.display.set_mode(self.windowed_size, pygame.RESIZABLE)
            except Exception:
                pass
