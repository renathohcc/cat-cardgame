"""Arte de bloqueio do quintal (`assets/pen/lock/`): camadas, placas, animacao de desbloqueio, icones.

Aceita a arte real; sem ela (arquivo ausente) cai em retangulos/formas por codigo, para as telas
nao mudarem quando a arte entrar. Tudo com cache; nearest sempre.
"""
from __future__ import annotations

import json
from pathlib import Path

import pygame

from ui import pen_world
from ui.pen_world import LOCK_ROOT, LockArea, LockSpec

ICON_NAMES = ("moeda", "prestigio", "cadeado", "racao_fofa", "racao_veloz", "racao_escolha",
              "decoracao_vaso", "decoracao_pincel")
ICON_SIZE = 16
_FALLBACK_COLORS = {"moeda": (255, 200, 64), "prestigio": (190, 110, 255), "cadeado": (170, 176, 196),
                    "racao_fofa": (255, 140, 200), "racao_veloz": (96, 200, 255),
                    "racao_escolha": (96, 230, 120), "decoracao_vaso": (200, 120, 70),
                    "decoracao_pincel": (255, 214, 64)}


class LockArt:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or LOCK_ROOT
        self.spec: LockSpec = pen_world.load_lock_spec(self.root)
        self.layers: dict[str, pygame.Surface] = {}
        self.sign_free = self._load(self.spec.free_file)
        self.sign_locked = self._load(self.spec.locked_file)
        self.frames: list[pygame.Surface] = []
        self.fps = 20.0
        self.icons: dict[str, pygame.Surface] = {}
        self._tint_cache: dict[tuple, pygame.Surface] = {}
        self._content_cache: dict[tuple, object] = {}
        self.content = pen_world.load_content_spec(self.root)
        self._load_anim()
        self._load_icons()
        for a in self.spec.areas:
            self.layers[a.id] = self._layer(a)

    # ------------------------------------------------------------ carga
    def _load(self, name: str) -> pygame.Surface | None:
        if not name:
            return None
        try:
            img = pygame.image.load(str(self.root / name))
            return img.convert_alpha() if pygame.display.get_surface() else img
        except (OSError, pygame.error):
            return None

    def _layer(self, a: LockArea) -> pygame.Surface:
        img = self._load(a.file)
        w, h = a.rect[2], a.rect[3]
        if img is not None and img.get_size() == (w, h):
            return img
        s = pygame.Surface((w, h), pygame.SRCALPHA)       # reserva: bloco liso com uma borda
        s.fill((58, 78, 52, 255))
        pygame.draw.rect(s, (36, 50, 34, 255), s.get_rect(), 3)
        return s

    def _load_anim(self) -> None:
        try:
            data = json.loads((self.root / "unlock_anim.json").read_text(encoding="utf-8"))
            fw, fh = (int(n) for n in data["frame_size"])
            n = int(data["frames"])
            self.fps = float(data.get("fps", 20))
            sheet = self._load(str(data["image"]))
            if sheet is not None and fw > 0 and fh > 0:
                self.frames = [sheet.subsurface(pygame.Rect(i * fw, 0, fw, fh)).copy() for i in range(n)]
        except (OSError, ValueError, KeyError, TypeError, pygame.error):
            self.frames = []

    def _load_icons(self) -> None:
        try:
            data = json.loads((self.root / "icons.json").read_text(encoding="utf-8"))
            sheet = self._load(str(data["image"]))
            if sheet is not None:
                for name, r in data["sprites"].items():
                    self.icons[name] = sheet.subsurface(pygame.Rect(r["x"], r["y"], r["w"], r["h"])).copy()
        except (OSError, ValueError, KeyError, TypeError, pygame.error):
            self.icons = {}

    # ------------------------------------------------------------ conteudo das areas
    def _content_img(self, name: str) -> pygame.Surface | None:
        if not name:
            return None
        try:
            img = pygame.image.load(str(self.root / "conteudo" / name))
            return img.convert_alpha() if pygame.display.get_surface() else img
        except (OSError, pygame.error):
            return None

    def content_floor(self, area_id: str, t: float) -> pygame.Surface | None:
        """Chao da area aberta (quadro da agua animada, se houver); None = sem arte."""
        ca = self.content.get(area_id)
        if ca is None:
            return None
        key = ("floor", area_id)
        if key not in self._content_cache:
            frames: list[pygame.Surface] = []
            sheet = self._content_img(ca.anim_file)
            fw, fh = ca.anim_size
            if sheet is not None and ca.anim_frames > 0 and fw > 0 and fh > 0:
                frames = [sheet.subsurface(pygame.Rect(i * fw, 0, fw, fh)).copy() for i in range(ca.anim_frames)]
            still = self._content_img(ca.floor)
            self._content_cache[key] = (still, frames)
        still, frames = self._content_cache[key]
        if frames and ca.anim_fps > 0:
            return frames[int(t * ca.anim_fps) % len(frames)]
        return still

    def content_sprite(self, name: str) -> pygame.Surface | None:
        key = ("sprite", name)
        if key not in self._content_cache:
            self._content_cache[key] = self._content_img(name)
        return self._content_cache[key]

    # ------------------------------------------------------------ consulta
    def icon(self, name: str) -> pygame.Surface:
        """Icone 16x16 (arte real ou forma simples colorida)."""
        img = self.icons.get(name)
        if img is None:
            img = self._fallback_icon(name)
            self.icons[name] = img
        return img

    @staticmethod
    def _fallback_icon(name: str) -> pygame.Surface:
        s = pygame.Surface((ICON_SIZE, ICON_SIZE), pygame.SRCALPHA)
        col = _FALLBACK_COLORS.get(name, (200, 200, 200))
        if name == "moeda":
            pygame.draw.circle(s, col, (8, 8), 7)
            pygame.draw.circle(s, (160, 112, 24), (8, 8), 7, 1)
        elif name == "cadeado":
            pygame.draw.rect(s, col, (3, 7, 10, 8))
            pygame.draw.rect(s, col, (5, 2, 6, 7), 2)
        else:
            pygame.draw.rect(s, col, (3, 3, 10, 10), border_radius=3)
        return s

    def area(self, area_id: str) -> LockArea | None:
        return next((a for a in self.spec.areas if a.id == area_id), None)

    def sign(self, free: bool) -> pygame.Surface:
        img = self.sign_free if free else self.sign_locked
        if img is not None:
            return img
        w, h = self.spec.sign_size
        s = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(s, (200, 170, 100) if free else (110, 96, 76), (0, 0, w, h - 8))
        pygame.draw.rect(s, (80, 56, 36), (w // 2 - 2, h - 8, 4, 8))
        return s

    def tinted(self, img: pygame.Surface, tint: tuple[int, int, int]) -> pygame.Surface:
        if tint == (255, 255, 255):
            return img
        key = (id(img), tint)
        out = self._tint_cache.get(key)
        if out is None:
            out = img.copy()
            out.fill((*tint, 255), special_flags=pygame.BLEND_RGBA_MULT)
            self._tint_cache[key] = out
        return out

    def frame_at(self, progress: float) -> pygame.Surface | None:
        if not self.frames:
            return None
        return self.frames[min(len(self.frames) - 1, max(0, int(progress * len(self.frames))))]


_art: LockArt | None = None


def art() -> LockArt:
    global _art
    if _art is None:
        _art = LockArt()
    return _art


def reset() -> None:
    global _art
    _art = None
