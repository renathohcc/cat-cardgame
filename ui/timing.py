"""Tempos e intensidades das animacoes do duelo, lidos de `data/ui_timing.json`.

Unica fonte de duracoes, amplitudes e escalas da UI. Le o JSON uma vez; valor faltando ou
invalido cai no padrao (`DEFAULTS`, igual ao arquivo), arquivo ausente usa so os padroes.
Sem pygame, sem RNG, sem threads (compativel com pygbag). Para testes: `Timing(dict)` ou
`use(Timing(...))`, e o `Controller` aceita `timing=`.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PATH = Path(__file__).resolve().parent.parent / "data" / "ui_timing.json"

DEFAULTS: dict[str, Any] = {
    "beats": {"Attacked": 0.34, "CatPlayed": 0.4, "EffectPlayed": 0.4, "result": 0.55,
              "heal": 0.45, "buff": 0.45, "turn": 0.4, "Deadlock": 2.6, "deadhit": 0.6,
              "DuelEnded": 0.3, "default": 0.3},
    "lunge": {"duration": 0.25, "reach": 0.85},
    "hitstop": {"normal": 0.05, "lethal": 0.08, "leader": 0.07},
    "shake": {"leader_hit": {"amplitude": 3, "duration": 0.18},
              "lethal": {"amplitude": 5, "duration": 0.25}},
    "damage_number": {"pop_scale": 2.0, "pop_time": 0.12, "rise": 36, "life": 0.95,
                      "big_threshold": 5, "big_scale": 3},
    "poof": {"particles": 14, "life": 0.5, "speed": 60},
    "hand": {"draw_slide": 0.25, "play_arc": 0.3, "hover_lift": 14, "hover_scale": 1.25,
             "hover_spread": 10},
    "breathing": {"amplitude": 1, "period": 2.4},
    "turn_banner": {"duration": 0.9},
    "energy": {"gem_stagger": 0.06},
    "fade": {"scene": 0.2},
    "boss_intro": {"duration": 2.4},
    "enemy_speed": {"options": {"1x": 1.0, "2x": 0.5, "rapido": 0.2}, "default": "1x"},
}

_POSITIVE = {("breathing", "period"), ("boss_intro", "duration")}          # precisam ser > 0
_UNIT = {("lunge", "reach")}                   # 0..1


class Section:
    """Bloco do JSON com acesso por atributo (`t.lunge.duration`) e por chave (`t.beats["x"]`)."""

    def __init__(self, data: dict) -> None:
        self._d = data

    def __getattr__(self, name: str) -> Any:
        try:
            v = self._d[name]
        except KeyError:
            raise AttributeError(name) from None
        return Section(v) if isinstance(v, dict) else v

    def __getitem__(self, key: str) -> Any:
        v = self._d[key]
        return Section(v) if isinstance(v, dict) else v

    def get(self, key: str, default: Any = None) -> Any:
        return self._d.get(key, default)

    def as_dict(self) -> dict:
        return self._d


def _num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _ok(path: tuple[str, ...], default: Any, v: Any) -> bool:
    if not _num(v) or v < 0:
        return False
    if path in _POSITIVE and v <= 0:
        return False
    if path in _UNIT and v > 1:
        return False
    if isinstance(default, int) and not isinstance(default, bool):
        return v == int(v)
    return True


def _merge(default: dict, raw: Any, path: tuple[str, ...] = ()) -> dict:
    """Copia de `default` trocando por `raw` so o que for valido (sem erro, sem chave nova)."""
    out: dict = {}
    for k, d in default.items():
        v = raw.get(k) if isinstance(raw, dict) else None
        if isinstance(d, dict) and k != "options":
            out[k] = _merge(d, v, path + (k,))
        elif k == "options":
            ok = isinstance(v, dict) and v and all(_num(x) and x > 0 for x in v.values())
            out[k] = dict(v) if ok else dict(d)
        elif k == "default" and path == ("enemy_speed",):
            out[k] = v if isinstance(v, str) else d
        else:
            out[k] = (float(v) if isinstance(d, float) else v) if v is not None and _ok(path + (k,), d, v) else d
    if path == ("enemy_speed",) and out["default"] not in out["options"]:
        out["default"] = next(iter(out["options"]))
    return out


class Timing(Section):
    def __init__(self, raw: dict | None = None) -> None:
        super().__init__(_merge(DEFAULTS, raw or {}))


def load(path: Path | str | None = None) -> Timing:
    """Le e valida o JSON; qualquer falha (arquivo, JSON, tipo) devolve os padroes."""
    try:
        raw = json.loads(Path(path or PATH).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raw = {}
    return Timing(raw if isinstance(raw, dict) else {})


_current: Timing | None = None


def current() -> Timing:
    global _current
    if _current is None:
        _current = load()
    return _current


def use(timing: Timing | None) -> None:
    """Troca o Timing global (None = recarrega do arquivo na proxima leitura). Para testes."""
    global _current
    _current = timing
