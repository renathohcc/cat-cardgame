"""Mundo do quintal em expansao (10a): areas bloqueadas, retangulo livre por zona e ancoras da decoracao.

Pura (sem pygame): le `assets/pen/lock/areas.json` e calcula, a partir das areas AINDA bloqueadas, o
maior retangulo livre de cada zona do cercado (onde os gatos podem andar) e quais objetos ficam
ativos. Nenhuma regra de jogo: quem diz o que esta comprado e o `core` (via o save).
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from ui.pen_geometry import PEN_ROOT

LOCK_ROOT = PEN_ROOT / "lock"
CELL = 16
Rect4 = tuple[int, int, int, int]

# Decoracao comprada -> (tipo do objeto desenhado, x, y) em ancora FIXA (centro-base), dentro da area
# que a libera. Sao so posicoes; o preco/estado vem de data/shop.json. Os `placeholder: true` do
# catalogo ("em breve") nao tem objeto e ficam fora desta tabela.
DECOR_ANCHORS: dict[str, tuple[str, int, int]] = {
    "deco-novelo": ("novelo", 176, 172),
    "deco-ratinho": ("ratinho", 300, 176),
    "deco-cama-almofada": ("cama_almofada", 398, 186),
    "deco-arranhador": ("arranhador", 290, 160),
    "deco-bola-filhote": ("bola_filhote", 690, 346),
    "deco-tunel-filhote": ("tunel_filhote", 590, 334),
    "deco-banco-arvore": ("banco_arvore", 206, 446),
}


# Objetos do pen.json que a arte das areas 4 a 6 cobre (a copa do pomar cai sobre o ratinho): quando a
# area abre, o objeto vai para o ponto novo, fora do retangulo. Chave: (kind, x, y) do pen.json.
RELOCATE: dict[tuple[str, int, int], tuple[int, int]] = {("ratinho", 336, 240): (262, 232)}
RELOCATE_AREA = {"ratinho": "pomar"}                       # kind -> area que dispara a mudanca


@dataclass(frozen=True)
class ContentSprite:
    file: str
    anchor: tuple[int, int]
    x: int
    y: int


@dataclass(frozen=True)
class ContentObject:
    kind: str
    x: int
    y: int
    layer: str
    slots: list[tuple[float, float]]
    slot_use: str


@dataclass(frozen=True)
class ContentArea:
    """Conteudo da arte de uma area (`lock/conteudo.json`): so aparece depois de desbloqueada."""
    id: str
    rect: Rect4
    floor: str
    anim_file: str = ""
    anim_frames: int = 0
    anim_size: tuple[int, int] = (0, 0)
    anim_fps: float = 0.0
    sprites: tuple[ContentSprite, ...] = ()
    objects: tuple[ContentObject, ...] = ()


def load_content_spec(root: Path | None = None) -> dict[str, ContentArea]:
    """`conteudo.json`; ausente/invalido = sem conteudo (as areas continuam so abrindo o gramado)."""
    try:
        data = json.loads(((root or LOCK_ROOT) / "conteudo.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out: dict[str, ContentArea] = {}
    raw = data.get("areas", {}) if isinstance(data, dict) else {}
    for aid, a in (raw.items() if isinstance(raw, dict) else []):
        try:
            rect = _rect(a["rect"])
            if rect is None:
                continue
            an = a.get("floor_anim") or {}
            sprites = tuple(ContentSprite(str(sp["file"]), (int(sp["anchor"][0]), int(sp["anchor"][1])),
                                          int(sp["x"]), int(sp["y"])) for sp in a.get("sorted", []))
            objs = tuple(ContentObject(str(o["kind"]), int(o["x"]), int(o["y"]), str(o.get("layer", "sorted")),
                                       [(float(p), float(q)) for p, q in o.get("slots", [])],
                                       str(o.get("slot_use", "play"))) for o in a.get("objects", []))
            size = an.get("frame_size", (0, 0))
            out[str(aid)] = ContentArea(str(aid), rect, str(a.get("floor", "")), str(an.get("file", "")),
                                        int(an.get("frames", 0)), (int(size[0]), int(size[1])),
                                        float(an.get("fps", 0)), sprites, objs)
        except (KeyError, TypeError, ValueError, IndexError):
            continue
    return out


@dataclass(frozen=True)
class LockArea:
    id: str
    file: str
    rect: Rect4
    anchor: tuple[int, int]            # base-centro da placa


@dataclass(frozen=True)
class LockSpec:
    areas: list[LockArea]
    sign_size: tuple[int, int] = (32, 32)
    text_rect: Rect4 = (4, 6, 24, 14)
    free_file: str = "placa_livre.png"
    locked_file: str = "placa_bloqueada.png"


def _rect(v) -> Rect4 | None:
    try:
        x, y, w, h = (int(n) for n in v)
        return (x, y, w, h) if w > 0 and h > 0 else None
    except (TypeError, ValueError):
        return None


def load_lock_spec(root: Path | None = None) -> LockSpec:
    """`areas.json` da arte de bloqueio; ausente/invalido = sem areas bloqueaveis."""
    try:
        data = json.loads(((root or LOCK_ROOT) / "areas.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return LockSpec([])
    areas: list[LockArea] = []
    for a in data.get("areas", []) if isinstance(data, dict) else []:
        try:
            r = _rect(a["rect"])
            ax, ay = (int(n) for n in a["anchor_sign"])
            if r is not None:
                areas.append(LockArea(str(a["id"]), str(a.get("file", "")), r, (ax, ay)))
        except (KeyError, TypeError, ValueError):
            continue
    sign = data.get("sign", {}) if isinstance(data, dict) else {}
    try:
        size = tuple(int(n) for n in sign["size"])
        size = (size[0], size[1])
    except (KeyError, TypeError, ValueError, IndexError):
        size = (32, 32)
    return LockSpec(areas, size, _rect(sign.get("text_rect")) or (4, 6, 24, 14),
                    str(sign.get("free", "placa_livre.png")), str(sign.get("locked", "placa_bloqueada.png")))


def sign_rect(area: LockArea, size: tuple[int, int] = (32, 32)) -> Rect4:
    """Retangulo da placa (a base fica no `anchor`, centrada)."""
    return (area.anchor[0] - size[0] // 2, area.anchor[1] - size[1], size[0], size[1])


def point_in(x: float, y: float, r: Rect4) -> bool:
    return r[0] <= x < r[0] + r[2] and r[1] <= y < r[1] + r[3]


def point_locked(x: float, y: float, locks: list[Rect4]) -> bool:
    return any(point_in(x, y, r) for r in locks)


def free_rect(base: Rect4, locks: list[Rect4]) -> Rect4 | None:
    """Maior retangulo (em grade de 16 px) dentro de `base` que nao toca nenhuma area bloqueada.
    Empate: o mais acima e a esquerda. None = a zona inteira esta coberta."""
    x0, y0, w, h = base
    cols, rows = w // CELL, h // CELL
    free = [[not point_locked(x0 + c * CELL + CELL // 2, y0 + r * CELL + CELL // 2, locks)
             for c in range(cols)] for r in range(rows)]
    best, best_area = None, 0
    for r0 in range(rows):
        for c0 in range(cols):
            if not free[r0][c0]:
                continue
            max_c = cols
            for r1 in range(r0, rows):
                run = 0
                while c0 + run < max_c and free[r1][c0 + run]:
                    run += 1
                max_c = c0 + run
                if run == 0:
                    break
                area = (r1 - r0 + 1) * run
                if area > best_area:
                    best_area, best = area, (c0, r0, run, r1 - r0 + 1)
    if best is None:
        return None
    c, r, cw, rh = best
    return (x0 + c * CELL, y0 + r * CELL, cw * CELL, rh * CELL)


def locked_rects(spec: LockSpec, unlocked: list[str] | set[str]) -> list[Rect4]:
    return [a.rect for a in spec.areas if a.id not in unlocked]


def decor_zone(zones: dict[str, Rect4], x: float, y: float) -> str | None:
    """Zona do cercado que contem o ponto (para ligar a decoracao a zona dos gatos)."""
    for name, r in zones.items():
        if point_in(x, y, r):
            return name
    return None
