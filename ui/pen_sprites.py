"""Arte do cercado: spritesheet de gatos 64x64, fundo e geometria, com fallback por codigo.

Formato esperado (`assets/pen/`):
- `cats_pen.json`: {"image","size":[w,h],"frame":[64,64],"anims":{"<id>":{"idle":{"row","frames","fps"},
  "walk":{...},"sleep":{...},"play":{...}}}}; ids = racas e "<id>_filhote". Frames voltados para a
  DIREITA; o frame `i` da linha `row` fica em (i*64, row*64).
- `pen_bg.png` + `pen.json` (geometria, ver `ui/pen_geometry.py`).
Sem a arte, usa o gato de `assets/cats96` reduzido com um balanco senoidal (bob) feito por codigo,
e o fundo padrao das telas. Tudo com cache; nearest sempre.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import pygame

from ui import sprites
from ui.pen_geometry import PEN_ROOT, PenGeometry, load_geometry

FRAME = 64
FALLBACK_PHASES = 16          # quadros do ciclo do balanco por codigo
FALLBACK_FPS = 12
ANIMS = ("idle", "walk", "sleep", "play")


class PenArt:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or PEN_ROOT
        self.geo: PenGeometry = load_geometry(self.root)
        self.sheet: pygame.Surface | None = None
        self.frame_size = (FRAME, FRAME)
        self.anims: dict[str, dict[str, dict]] = {}
        self.bg: pygame.Surface | None = None
        self.bg_periods: dict[str, pygame.Surface] = {}        # periodo -> fundo (vazio = so `bg`)
        self.fx_sheet: pygame.Surface | None = None
        self.fx_rects: dict[str, pygame.Rect] = {}
        self._cache: dict[tuple, pygame.Surface] = {}
        self.objs = self._load_objects("objects")           # kind -> (imagem, (w, h), anims)
        self.amb = self._load_objects("ambient")
        self._load_sheet()
        self._load_bg()
        self._load_fx()

    # ------------------------------------------------------------ carga
    def _img(self, name: str) -> pygame.Surface | None:
        try:
            img = pygame.image.load(str(self.root / name))
            return img.convert_alpha() if pygame.display.get_surface() else img
        except Exception:
            return None

    def _load_sheet(self) -> None:
        try:
            data = json.loads((self.root / "cats_pen.json").read_text(encoding="utf-8"))
            img = self._img(str(data["image"]))
            fw, fh = (int(n) for n in data.get("frame", (FRAME, FRAME)))
            anims = data["anims"]
            if img is None or fw <= 0 or fh <= 0 or not isinstance(anims, dict):
                return
            self.sheet, self.frame_size, self.anims = img, (fw, fh), anims
        except Exception:
            self.sheet, self.anims = None, {}

    def _load_objects(self, stem: str) -> dict[str, tuple]:
        """`objects.json` / `ambient.json`: {"image","objects":{kind:{"frame":[w,h],"anims":{anim:{row,frames,fps}}}}}."""
        out: dict[str, tuple] = {}
        try:
            data = json.loads((self.root / f"{stem}.json").read_text(encoding="utf-8"))
            img = self._img(str(data["image"]))
            if img is None:
                return out
            for kind, d in (data.get("objects") or data["ambient"]).items():
                fw, fh = (int(n) for n in d["frame"])
                if fw > 0 and fh > 0 and isinstance(d.get("anims"), dict):
                    out[kind] = (img, (fw, fh), d["anims"], d.get("anchor"))
        except Exception:
            return {}
        return out

    def _anim_frame(self, table: dict, tag: str, kind: str, anim: str, t: float, flip: bool = False,
                    once: bool = False):
        ent = table.get(kind)
        if ent is None:
            return None
        img, (fw, fh), anims = ent[:3]
        info = anims.get(anim) or anims.get("idle")
        if not isinstance(info, dict):
            return None
        try:
            n = max(1, int(info.get("frames", 1)))
            idx = int(t * float(info.get("fps", 6)))
            idx = min(idx, n - 1) if once else idx % n
            key = (tag, kind, anim if anim in anims else "idle", idx, flip)
            if key not in self._cache:
                spr = img.subsurface(pygame.Rect(idx * fw, int(info["row"]) * fh, fw, fh)).copy()
                self._cache[key] = pygame.transform.flip(spr, True, False) if flip else spr
            return self._cache[key]
        except (ValueError, KeyError, TypeError, pygame.error):
            return None

    def anchor(self, kind: str, ambient: bool = False) -> tuple[int, int]:
        """Ancora (centro-base) do quadro: o quadro desenha-se em (x - ax, y - ay)."""
        ent = (self.amb if ambient else self.objs).get(kind)
        if ent is None:
            return (0, 0)
        fw, fh = ent[1]
        a = ent[3] if len(ent) > 3 else None
        return (int(a[0]), int(a[1])) if a else (fw // 2, fh - 4)

    def object_frame(self, kind: str, anim: str, t: float, once: bool = False) -> pygame.Surface | None:
        """Quadro do objeto (idle/use/enter/exit) ou None: quem desenha usa a forma simples por codigo.
        `once`: toca a anim uma vez (segura o ultimo quadro)."""
        return self._anim_frame(self.objs, "o", kind, anim, t, once=once)

    def has_anim(self, kind: str, anim: str, ambient: bool = False) -> bool:
        ent = (self.amb if ambient else self.objs).get(kind)
        return ent is not None and isinstance(ent[2].get(anim), dict)

    def anim_duration(self, kind: str, anim: str) -> float:
        """Duracao (s) de uma anim one-shot do objeto; 0 se nao existe."""
        ent = self.objs.get(kind)
        info = ent[2].get(anim) if ent else None
        if not isinstance(info, dict):
            return 0.0
        try:
            return max(1, int(info.get("frames", 1))) / max(0.1, float(info.get("fps", 6)))
        except (TypeError, ValueError):
            return 0.0

    def ambient_frame(self, kind: str, t: float, anim: str = "idle") -> pygame.Surface | None:
        return self._anim_frame(self.amb, "a", kind, anim, t)

    def _load_bg(self) -> None:
        if self.geo.bg:
            self.bg = self._img(self.geo.bg)
        elif (self.root / "pen_bg.png").exists():
            self.bg = self._img("pen_bg.png")
        for period, name in self.geo.bg_periods.items():
            img = self._img(name)
            if img is not None:
                self.bg_periods[period] = img
        if self.bg is None and self.bg_periods:
            self.bg = self.bg_periods.get("dia") or next(iter(self.bg_periods.values()))

    def tint_for(self, day) -> tuple[int, int, int]:
        """Tint (BLEND_MULT) do periodo, misturado pelo crossfade; branco sem `period_tint`."""
        tints = self.geo.period_tint
        if day is None or not tints:
            return (255, 255, 255)
        w = day.weights()
        tot = sum(v for p, v in w.items() if p in tints) or 1.0
        return tuple(round(sum(tints[p][k] * v for p, v in w.items() if p in tints) / tot) for k in range(3))

    def tinted(self, img: pygame.Surface, tint: tuple[int, int, int]) -> pygame.Surface:
        """Copia do quadro multiplicada pelo tint (cache; branco devolve o proprio quadro)."""
        if tint == (255, 255, 255):
            return img
        key = ("t", id(img), tint)
        out = self._cache.get(key)
        if out is None:
            out = img.copy()
            out.fill((*tint, 255), special_flags=pygame.BLEND_RGBA_MULT)
            if len(self._cache) > 4000:
                self._cache.clear()
            self._cache[key] = out
        return out

    def background(self, period: str) -> pygame.Surface | None:
        """Fundo do periodo; sem fundos por periodo, o `bg` unico."""
        return self.bg_periods.get(period) or self.bg

    def _load_fx(self) -> None:
        """`fx.json`: {"image","sprites":{nome:{x,y,w,h}}} (heart, z, note, sparkle, star...)."""
        try:
            data = json.loads((self.root / "fx.json").read_text(encoding="utf-8"))
            img = self._img(str(data["image"]))
            rects = {k: pygame.Rect(v["x"], v["y"], v["w"], v["h"]) for k, v in data["sprites"].items()}
            if img is not None:
                self.fx_sheet, self.fx_rects = img, rects
        except Exception:
            self.fx_sheet, self.fx_rects = None, {}

    def fx(self, name: str, scale: int = 1) -> pygame.Surface | None:
        """Icone de efeito (coracao, z, nota...) ou None (quem desenha usa o desenho por codigo)."""
        r = self.fx_rects.get(name)
        if self.fx_sheet is None or r is None:
            return None
        key = ("fx", name, scale)
        if key not in self._cache:
            try:
                img = self.fx_sheet.subsurface(r).copy()
            except (ValueError, pygame.error):
                return None
            self._cache[key] = pygame.transform.scale(img, (r.w * scale, r.h * scale)) if scale != 1 else img
        return self._cache[key]

    # ------------------------------------------------------------ consulta
    @staticmethod
    def sheet_id(breed: str, kitten: bool) -> str:
        return f"{breed}_filhote" if kitten else breed

    def has_art(self, breed: str, kitten: bool = False) -> bool:
        """True se o spritesheet novo cobre esse gato."""
        return self.sheet is not None and self.sheet_id(breed, kitten) in self.anims

    def frame(self, breed: str, kitten: bool, anim: str, t: float, flip: bool = False) -> pygame.Surface:
        """Quadro 64x64 (ou o tamanho do sheet) para o instante `t`. Nunca devolve None."""
        sid = self.sheet_id(breed, kitten)
        info = self.anims.get(sid, {}).get(anim) if self.sheet is not None else None
        if info is None and self.sheet is not None:
            info = self.anims.get(sid, {}).get("idle")
        if info is not None:
            try:
                n = max(1, int(info.get("frames", 1)))
                idx = int(t * float(info.get("fps", 6))) % n
                key = ("s", sid, anim, idx, flip)
                if key not in self._cache:
                    fw, fh = self.frame_size
                    spr = self.sheet.subsurface(pygame.Rect(idx * fw, int(info["row"]) * fh, fw, fh)).copy()
                    self._cache[key] = pygame.transform.flip(spr, True, False) if flip else spr
                return self._cache[key]
            except (ValueError, KeyError, TypeError, pygame.error):
                pass
        return self._fallback(breed, kitten, anim, t, flip)

    # ------------------------------------------------------------ fallback
    def _fallback(self, breed: str, kitten: bool, anim: str, t: float, flip: bool) -> pygame.Surface:
        phase = int(t * FALLBACK_FPS) % FALLBACK_PHASES
        key = ("f", breed, kitten, anim, phase, flip)
        surf = self._cache.get(key)
        if surf is None:
            surf = self._build_fallback(breed, kitten, anim, phase)
            if flip:
                surf = pygame.transform.flip(surf, True, False)
            if len(self._cache) > 2000:
                self._cache.clear()
            self._cache[key] = surf
        return surf

    def _build_fallback(self, breed: str, kitten: bool, anim: str, phase: int) -> pygame.Surface:
        out = pygame.Surface((FRAME, FRAME), pygame.SRCALPHA)
        side = 40 if kitten else 56
        base = sprites.get("cat", breed, side)
        if base is None:
            base = _placeholder(breed, side)
        w, h = base.get_size()
        a = 2 * math.pi * phase / FALLBACK_PHASES
        dy, squash = 0, 1.0
        if anim == "walk":
            dy = -round(abs(math.sin(a * 2)) * 3)
        elif anim == "play":
            dy = -round(abs(math.sin(a * 2)) * 9)
        elif anim == "sleep":
            squash = 0.62 + 0.03 * math.sin(a)
        else:
            dy = -round(max(0.0, math.sin(a)) * 1.5)
        if squash != 1.0:
            base = pygame.transform.scale(base, (round(w * 1.12), round(h * squash)))
            w, h = base.get_size()
        out.blit(base, ((FRAME - w) // 2, FRAME - 2 - h + dy))
        return out


def _placeholder(breed: str, side: int) -> pygame.Surface:
    from ui.widgets import breed_color
    s = pygame.Surface((side, side), pygame.SRCALPHA)
    col = breed_color(breed)
    r = side // 3
    cx, cy = side // 2, side - r - 2
    pygame.draw.circle(s, col, (cx, cy), r)
    pygame.draw.polygon(s, col, [(cx - r, cy - r // 3), (cx - r + 2, cy - r - r // 2), (cx - r // 4, cy - r + 2)])
    pygame.draw.polygon(s, col, [(cx + r, cy - r // 3), (cx + r - 2, cy - r - r // 2), (cx + r // 4, cy - r + 2)])
    return s


_art: PenArt | None = None


def art() -> PenArt:
    global _art
    if _art is None:
        _art = PenArt()
    return _art


def reset() -> None:
    global _art
    _art = None
