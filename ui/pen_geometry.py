"""Geometria do cercado (Criatorio animado). Pura: so le JSON, sem pygame.

Formato de `assets/pen/pen.json`: {"bg","bg_periods":{periodo:arquivo},"zones":{z:{rect,objects}},"ambient":[{kind,x,y,periods?}],"walk_area":[x,y,w,h],"panel":[x,y,w,h]}.
Sem o arquivo (ou campo ausente/invalido) usa os padroes abaixo, que seguem o mesmo desenho.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

PEN_ROOT = Path(__file__).resolve().parent.parent / "assets" / "pen"

DEFAULT_AREA = (48, 96, 664, 372)
DEFAULT_PANEL = (736, 16, 208, 508)
# Fonte da verdade: data/rules.json -> meta.pen_max_cats / meta.pen_zone_caps. Valores abaixo = so fallback
# explicito quando a chave faltar (ex.: regras antigas em teste).
FALLBACK_MAX_CATS = 16
FALLBACK_ZONE_CAPS = {"adultos": 10, "breed": 6, "filhotes": 6}


ZONES = ("adultos", "breed", "filhotes")
DEFAULT_ZONES = {"adultos": (48, 96, 440, 372), "breed": (496, 96, 216, 180), "filhotes": (496, 288, 216, 180)}
BED_KINDS = ("cama_almofada", "cama_cesto", "cama_pedra", "cama_casal", "viveiro_cesto")   # anims enter/exit
SLEEP_KINDS = BED_KINDS + ("casinha", "casinha_filhote", "banco_arvore")
PLAY_KINDS = ("novelo", "ratinho", "arranhador", "bola_filhote", "tunel_filhote")
DECOR_KINDS = ("tigela", "tigela_racao", "casinha_filhote")                                   # estatico, sem slots nem funcao
MOVER_KINDS = ("novelo", "ratinho", "bola_filhote")
# objetos de reserva (formas simples) quando o pen.json nao traz "zones"
_FALLBACK_OBJECTS = {
    "adultos": [("cama_almofada", 90, 190), ("cama_cesto", 400, 180), ("cama_pedra", 110, 430),
                ("novelo", 250, 300), ("ratinho", 360, 400), ("tigela", 300, 230), ("arranhador", 430, 330)],
    "breed": [("cama_casal", 580, 170), ("cama_casal", 660, 250)],
    "filhotes": [("viveiro_cesto", 560, 360), ("bola_filhote", 660, 420), ("tunel_filhote", 600, 310)],
}
_FALLBACK_AMBIENT = (("lanterna", 40, 90), ("lanterna", 490, 90), ("vagalumes", 250, 200), ("vagalumes", 600, 380))


@dataclass
class ObjectSpec:
    kind: str
    x: float
    y: float
    slots: list[tuple[float, float]] = field(default_factory=lambda: [(0.0, 0.0)])
    slot_use: str = "play"
    layer: str = "sorted"            # floor: abaixo de todos os gatos; sorted: ordena por y


@dataclass
class ZoneSpec:
    rect: tuple[int, int, int, int]
    objects: list[ObjectSpec] = field(default_factory=list)


@dataclass
class AmbientSpec:
    kind: str
    x: float
    y: float
    phase: float = 0.0
    periods: tuple[str, ...] | None = None       # None = todos os periodos do dia


def default_slot_use(kind: str) -> str:
    return "sleep" if kind in SLEEP_KINDS else "play"


def _default_slots(kind: str) -> list[tuple[float, float]]:
    if kind in DECOR_KINDS:
        return []
    return [(-14.0, 0.0), (14.0, 0.0)] if kind == "cama_casal" else [(0.0, 0.0)]


def _objects(v) -> list[ObjectSpec]:
    out: list[ObjectSpec] = []
    for o in v if isinstance(v, list) else []:
        try:
            kind = str(o["kind"])
            raw_slots = o.get("slots")
            slots = ([(float(a), float(b)) for a, b in raw_slots] if isinstance(raw_slots, list) else [])                 or _default_slots(kind)
            if kind in DECOR_KINDS:
                slots = []
            use = o.get("slot_use")
            use = use if use in ("sleep", "play") else default_slot_use(kind)
            layer = o.get("layer") if o.get("layer") in ("floor", "sorted") else ("floor" if kind in BED_KINDS else "sorted")
            out.append(ObjectSpec(kind, float(o["x"]), float(o["y"]), slots, use, layer))
        except (TypeError, ValueError, KeyError, AttributeError):
            continue
    return out


def _fallback_zones() -> dict[str, ZoneSpec]:
    return {z: ZoneSpec(DEFAULT_ZONES[z], [ObjectSpec(k, x, y, _default_slots(k), default_slot_use(k))
                                           for k, x, y in _FALLBACK_OBJECTS[z]]) for z in ZONES}


def parse_zones(data: dict) -> tuple[dict[str, ZoneSpec], list[AmbientSpec]]:
    """Sem "zones" valido: zonas padrao com objetos simples de reserva. Zona ausente: retangulo padrao."""
    raw = data.get("zones")
    if not isinstance(raw, dict):
        zones = _fallback_zones()
    else:
        zones = {}
        for z in ZONES:
            zd = raw.get(z) if isinstance(raw.get(z), dict) else {}
            zones[z] = ZoneSpec(_rect4(zd.get("rect"), DEFAULT_ZONES[z]), _objects(zd.get("objects")))
    if isinstance(data.get("ambient"), list):
        amb = []
        for a in data["ambient"]:
            try:
                per = a.get("periods")
                per = tuple(str(p) for p in per) if isinstance(per, list) and per else None
                amb.append(AmbientSpec(str(a["kind"]), float(a["x"]), float(a["y"]), float(a.get("phase", 0)), per))
            except (TypeError, ValueError, KeyError):
                continue
    else:
        amb = [AmbientSpec(k, x, y) for k, x, y in _FALLBACK_AMBIENT] if not isinstance(raw, dict) else []
    return zones, amb


def _union(zones: dict[str, ZoneSpec]) -> tuple[int, int, int, int]:
    x0 = min(z.rect[0] for z in zones.values())
    y0 = min(z.rect[1] for z in zones.values())
    x1 = max(z.rect[0] + z.rect[2] for z in zones.values())
    y1 = max(z.rect[1] + z.rect[3] for z in zones.values())
    return (x0, y0, x1 - x0, y1 - y0)


@dataclass
class PenGeometry:
    zones: dict[str, ZoneSpec] = field(default_factory=_fallback_zones)
    ambient: list[AmbientSpec] = field(default_factory=lambda: [AmbientSpec(k, x, y) for k, x, y in _FALLBACK_AMBIENT])
    walk_area: tuple[int, int, int, int] = DEFAULT_AREA
    panel: tuple[int, int, int, int] = DEFAULT_PANEL
    bg: str | None = None
    bg_periods: dict[str, str] = field(default_factory=dict)      # periodo -> arquivo do fundo
    period_tint: dict[str, tuple[int, int, int]] = field(default_factory=dict)   # BLEND_MULT por periodo
    lantern_on: tuple[str, ...] = ("entardecer", "noite")


def _rect4(v, default):
    try:
        x, y, w, h = (int(n) for n in v)
        return (x, y, w, h) if w > 0 and h > 0 else default
    except (TypeError, ValueError):
        return default


def _bg_periods(v) -> dict[str, str]:
    from ui.daycycle import PERIODS
    if not isinstance(v, dict):
        return {}
    return {p: v[p] for p in PERIODS if isinstance(v.get(p), str)}


def _tints(v) -> dict[str, tuple[int, int, int]]:
    from ui.daycycle import PERIODS
    out: dict[str, tuple[int, int, int]] = {}
    for p in PERIODS:
        try:
            r, g, b = (max(0, min(255, int(n))) for n in v[p])
            out[p] = (r, g, b)
        except (TypeError, ValueError, KeyError, IndexError):
            continue
    return out


def _lantern(v) -> tuple[str, ...]:
    from ui.daycycle import LIT_PERIODS, PERIODS
    got = tuple(p for p in v if p in PERIODS) if isinstance(v, list) else ()
    return got or LIT_PERIODS


def pen_limits(rules: dict | None) -> tuple[int, dict[str, int]]:
    """(max de gatos, vagas por zona) lidos de rules["meta"]; fallback explicito por chave ausente/invalida."""
    meta = (rules or {}).get("meta") or {}

    def _pos(v, default: int) -> int:
        return v if isinstance(v, int) and not isinstance(v, bool) and v >= 1 else default

    raw = meta.get("pen_zone_caps")
    raw = raw if isinstance(raw, dict) else {}
    caps = {z: _pos(raw.get(z), FALLBACK_ZONE_CAPS[z]) for z in ZONES}
    return _pos(meta.get("pen_max_cats"), FALLBACK_MAX_CATS), caps


def parse_geometry(data: dict | None) -> PenGeometry:
    if not isinstance(data, dict):
        return PenGeometry()
    zones, amb = parse_zones(data)
    return PenGeometry(
        zones=zones, ambient=amb,
        walk_area=_union(zones),
        panel=_rect4(data.get("panel"), DEFAULT_PANEL),
        bg=data.get("bg") if isinstance(data.get("bg"), str) else None,
        bg_periods=_bg_periods(data.get("bg_periods")),
        period_tint=_tints(data.get("period_tint")),
        lantern_on=_lantern(data.get("lantern_on_periods")))


def load_geometry(root: Path | None = None) -> PenGeometry:
    try:
        data = json.loads(((root or PEN_ROOT) / "pen.json").read_text(encoding="utf-8"))
    except Exception:
        data = None
    return parse_geometry(data)
