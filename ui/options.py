"""Opcoes do jogador (T12.4): modelo (`Options`) e tela de opcoes (`OptionsScreen`).

O modelo guarda tela cheia, velocidade do inimigo e tremor de tela em `saves/prefs.json`, o mesmo
arquivo do audio (que e quem escreve volumes e mudo): `audio.write_prefs` mescla as chaves, entao
nenhum dos dois apaga o outro. Leitura tolerante: arquivo ausente, antigo ou corrompido = padroes.
Volume e mudo vivem no `AudioManager` (a tela apenas chama `audio.manager()`).
A tela e so apresentacao: nenhuma regra de jogo.
"""
from __future__ import annotations

from pathlib import Path

import pygame

from ui import audio, font, layout_opts as LO, timing as timing_mod, widgets as Wd
from ui.theme import C

KEY_SHAKE, KEY_SPEED, KEY_FULL = "screen_shake", "enemy_speed", "fullscreen"
SPEED_LABEL = {"1x": "1X", "2x": "2X", "rapido": "RÁPIDO"}


def speed_keys() -> list[str]:
    return list(timing_mod.current().enemy_speed.options.as_dict())


def default_speed() -> str:
    return timing_mod.current().enemy_speed.default


def parse_prefs(raw: dict) -> dict:
    """Valida as chaves das opcoes; o que faltar ou vier invalido fica de fora (usa o padrao)."""
    out: dict = {}
    for key in (KEY_SHAKE, KEY_FULL):
        if isinstance(raw.get(key), bool):
            out[key] = raw[key]
    if raw.get(KEY_SPEED) in speed_keys():
        out[KEY_SPEED] = raw[KEY_SPEED]
    return out


class Options:
    """Preferencias de apresentacao. `path` None = so memoria (testes, capturas)."""

    def __init__(self, path: Path | None = None, *, load: bool = True) -> None:
        self.path = Path(path) if path is not None else None
        self.shake = True
        self.speed = default_speed()
        self.fullscreen = False
        if load:
            self.load()

    @classmethod
    def from_audio(cls) -> "Options":
        """Usa o mesmo prefs.json do `AudioManager` instalado."""
        return cls(audio.manager().prefs_path)

    def load(self) -> None:
        p = parse_prefs(audio.read_raw_prefs(self.path))
        self.shake = p.get(KEY_SHAKE, True)
        self.speed = p.get(KEY_SPEED, default_speed())
        self.fullscreen = p.get(KEY_FULL, False)

    def save(self) -> bool:
        return audio.write_prefs(self.path, {KEY_SHAKE: self.shake, KEY_SPEED: self.speed,
                                             KEY_FULL: self.fullscreen})

    def set_shake(self, v: bool) -> None:
        self.shake = bool(v)
        self.save()

    def set_speed(self, key: str) -> None:
        if key in speed_keys():
            self.speed = key
            self.save()

    def step_speed(self, d: int) -> None:
        keys = speed_keys()
        self.set_speed(keys[max(0, min(len(keys) - 1, keys.index(self.speed) + d))]
                       if self.speed in keys else keys[0])

    def set_fullscreen(self, v: bool) -> None:
        self.fullscreen = bool(v)
        self.save()

    def apply(self, ui) -> None:
        """Liga as opcoes no estado de desenho (`UIState`); os loops copiam `enemy_speed` ao Controller."""
        ui.screen_shake = self.shake
        ui.enemy_speed = self.speed


class OptionsScreen:
    """Tela de opcoes. Mouse e teclado (setas, Enter, Esc). `display` e opcional (tela cheia)."""

    def __init__(self, options: Options, display=None) -> None:
        self.options = options
        self.display = display
        self.focus = 0

    # ------------------------------------------------------------ valores
    def fullscreen_on(self) -> bool:
        return bool(self.display.fullscreen) if self.display is not None else self.options.fullscreen

    def toggle_fullscreen(self) -> None:
        if self.display is not None:
            self.display.toggle_fullscreen()
        self.options.set_fullscreen(self.display.fullscreen if self.display is not None
                                    else not self.options.fullscreen)

    # ------------------------------------------------------------ entrada
    def hit(self, pos: tuple[int, int]) -> tuple | None:
        return LO.hit_test(pos, speed_keys())

    def click(self, elem: tuple | None) -> str | None:
        """Aplica o clique. Devolve "back" ao voltar; senao None. Toca ui_click/ui_back."""
        if not elem:
            return None
        kind = elem[0]
        if kind == "opt_back":
            audio.sfx("ui_back")
            return "back"
        self.focus = LO.row_of(elem)
        self._act(elem)
        audio.sfx("ui_click")
        return None

    def _act(self, elem: tuple) -> None:
        kind, mgr, o = elem[0], audio.manager(), self.options
        if kind == "opt_vol":
            mgr.adjust_volume(elem[1], elem[2])
        elif kind == "opt_vol_set":
            mgr.set_volume(elem[1], elem[2])
        elif kind == "opt_mute":
            mgr.toggle_mute()
        elif kind == "opt_full":
            self.toggle_fullscreen()
        elif kind == "opt_speed":
            o.set_speed(elem[1])
        elif kind == "opt_shake":
            o.set_shake(not o.shake)

    def key(self, key: int) -> str | None:
        """Setas movem o foco/ajustam, Enter/Espaco ativa, Esc volta. Devolve "back" ou None."""
        n = len(LO.ROWS)
        if key == pygame.K_ESCAPE:
            audio.sfx("ui_back")
            return "back"
        if key == pygame.K_UP:
            self.focus = (self.focus - 1) % n
        elif key == pygame.K_DOWN:
            self.focus = (self.focus + 1) % n
        elif key in (pygame.K_LEFT, pygame.K_RIGHT):
            self._arrow(1 if key == pygame.K_RIGHT else -1)
        elif key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
            return self.click(self._enter_elem())
        return None

    def _row(self) -> str:
        return LO.ROWS[self.focus]

    def _enter_elem(self) -> tuple:
        row = self._row()
        if row in ("musica", "efeitos"):
            return ("opt_vol", row, 1)
        return {"mudo": ("opt_mute",), "tela": ("opt_full",), "tremor": ("opt_shake",),
                "voltar": ("opt_back",)}.get(row, ("opt_speed", self._next_speed()))

    def _next_speed(self) -> str:
        keys = speed_keys()
        return keys[(keys.index(self.options.speed) + 1) % len(keys)] if self.options.speed in keys else keys[0]

    def _arrow(self, d: int) -> None:
        row = self._row()
        if row in ("musica", "efeitos"):
            audio.manager().adjust_volume(row, d)
        elif row == "velocidade":
            self.options.step_speed(d)
        elif row == "mudo":
            audio.manager().set_muted(d < 0)
        elif row == "tela":
            if self.fullscreen_on() != (d > 0):
                self.toggle_fullscreen()
        elif row == "tremor":
            self.options.set_shake(d > 0)
        else:
            return
        audio.sfx("ui_click")

    def hover(self, elem: tuple | None) -> None:
        """Mouse sobre uma linha move o foco do teclado para ela."""
        if elem and elem[0].startswith("opt_"):
            self.focus = LO.row_of(elem)

    # ------------------------------------------------------------ desenho
    def draw(self, surf: pygame.Surface, mouse, focus_on: bool = True) -> None:
        mgr, o = audio.manager(), self.options
        panel = LO.panel()
        Wd.modal(surf, panel, "OPÇÕES")
        for i, row in enumerate(LO.ROWS):
            if row == "voltar":
                continue
            y = LO.row_y(i)
            lit = focus_on and self.focus == i
            if lit:
                pygame.draw.rect(surf, C["slot"], LO.row_rect(i), border_radius=4)
                pygame.draw.rect(surf, C["warn"], LO.row_rect(i), 1, border_radius=4)
            font.draw(surf, LO.LABELS[row], LO.LABEL_X, y + (LO.BTN_H - font.CAP_H) // 2,
                      C["warn"] if lit else C["text"], 1)
        self._draw_volumes(surf, mouse, mgr)
        self._draw_toggle(surf, 2, mouse, "MUDO" if mgr.muted else "SOM LIGADO", mgr.muted, bad=True)
        self._draw_toggle(surf, 3, mouse, "TELA CHEIA" if self.fullscreen_on() else "JANELA", self.fullscreen_on())
        self._draw_speed(surf, mouse)
        self._draw_toggle(surf, 5, mouse, "LIGADO" if o.shake else "DESLIGADO", o.shake)
        Wd.button(surf, LO.back_rect(), "VOLTAR", mouse, scale=2, focus=focus_on and self.focus == len(LO.ROWS) - 1)
        font.draw(surf, "SETAS: escolher/ajustar   ENTER: ativar   ESC: voltar", panel.centerx, panel.bottom - 20,
                  C["dim"], 1, "center")

    def _draw_volumes(self, surf: pygame.Surface, mouse, mgr) -> None:
        for i, which in enumerate(LO.VOL_ROWS):
            v = mgr.volume_of(which)
            Wd.button(surf, LO.vol_minus(i), "-", mouse, v > 0, scale=2)
            Wd.volume_bar(surf, LO.vol_bar(i), v, not mgr.muted)
            Wd.button(surf, LO.vol_plus(i), "+", mouse, v < 1, scale=2)
            font.draw(surf, f"{round(v * 100)}%", LO.vol_plus(i).right + 12,
                      LO.row_y(i) + (LO.BTN_H - font.CAP_H) // 2, C["dim"] if mgr.muted else C["text"], 1)

    def _draw_toggle(self, surf: pygame.Surface, i: int, mouse, label: str, on: bool, bad: bool = False) -> None:
        base = (150, 60, 60) if (on and bad) else (C["button"] if (on and not bad) else (70, 76, 104))
        Wd.button(surf, LO.toggle_rect(i), label, mouse, base=base, scale=1)

    def _draw_speed(self, surf: pygame.Surface, mouse) -> None:
        for k, key in enumerate(speed_keys()):
            on = key == self.options.speed
            Wd.button(surf, LO.speed_rect(k, len(speed_keys())), SPEED_LABEL.get(key, key.upper()), mouse,
                      base=C["button"] if on else (70, 76, 104), scale=1)
