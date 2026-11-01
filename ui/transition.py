"""Fade curto entre cenas (T12.4): dissolve do quadro anterior para o novo.

Duracao em `data/ui_timing.json` (`fade.scene`). Nunca bloqueia: e so um desenho por cima do quadro
novo (que ja responde a cliques); clique ou tecla pula (`skip`). Desligado (`enabled=False`,
duracao 0 ou `CHAOSCATS_FADE=off`) a troca e instantanea. Sem threads, sem disco.
Uso por quadro: `fade.tick(dt)`; depois de desenhar a cena `fade.apply(canvas, chave_da_cena)`.
"""
from __future__ import annotations

import os

import pygame

from ui import timing as timing_mod


class Transition:
    def __init__(self, duration: float | None = None, enabled: bool = True) -> None:
        d = timing_mod.current().fade.scene if duration is None else duration
        self.duration = max(0.0, float(d))
        self.enabled = bool(enabled) and self.duration > 0 and os.environ.get("CHAOSCATS_FADE", "").lower() != "off"
        self.key: str | None = None
        self.t = self.duration
        self._prev: pygame.Surface | None = None      # quadro anterior (limpo)
        self._cur: pygame.Surface | None = None

    @property
    def active(self) -> bool:
        return self.enabled and self.t < self.duration

    @property
    def progress(self) -> float:
        """0 = quadro antigo inteiro, 1 = cena nova inteira."""
        return 1.0 if not self.active else self.t / self.duration

    def tick(self, dt: float) -> None:
        if self.t < self.duration:
            self.t = min(self.duration, self.t + max(0.0, dt))

    def skip(self) -> None:
        self.t = self.duration

    def start(self) -> None:
        """Comeca a dissolver do ultimo quadro guardado (se houver)."""
        if self.enabled and self._prev is not None:
            self.t = 0.0

    def apply(self, canvas: pygame.Surface, key: str) -> None:
        """Chamar com o quadro da cena ja desenhado. Trocar `key` dispara o fade."""
        if not self.enabled:
            self.key = key
            return
        if self._prev is None:
            self._prev, self._cur = canvas.copy(), canvas.copy()
        if self.key is not None and key != self.key:
            self.start()
        self.key = key
        if self.active:
            # `_prev` fica congelado na cena antiga durante todo o fade; so ela some aos poucos.
            self._prev.set_alpha(round(255 * (1.0 - self.progress)))
            canvas.blit(self._prev, (0, 0))
        else:
            self._prev.set_alpha(None)
            self._prev.blit(canvas, (0, 0))
