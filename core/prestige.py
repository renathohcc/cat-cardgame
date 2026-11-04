"""Prestigio (rules.prestige): nivel por marcos, nunca desce."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.save import SaveData
from core.types import Content

__all__ = ["PrestigeInfo", "prestige_reached", "prestige_level", "update_prestige",
           "prestige_info"]


@dataclass(frozen=True)
class PrestigeInfo:
    level: int
    next_level: int | None          # None = nivel maximo
    milestone: dict[str, Any] | None   # marco do proximo nivel (copia do JSON)
    current: int | None             # progresso atual (None = sem contagem ou travado)
    target: int | None
    missing: int | None             # quanto falta; None se travado ou sem contagem
    locked: bool                    # proximo nivel desligado (enabled false)


def _levels(content: Content) -> list[dict[str, Any]]:
    cfg = content.rules.get("prestige", {}) or {}
    return sorted(cfg.get("levels", []), key=lambda lv: lv["level"])


def _progress(save: SaveData, milestone: dict[str, Any]) -> tuple[int | None, int | None]:
    kind = milestone.get("type")
    if kind == "win_league":
        return int(save.progress.get("leagues_cleared", 0)), int(milestone["league"])
    if kind == "distinct_breeds":
        return len({c.breed for c in save.cats}), int(milestone["count"])
    if kind == "distinct_breeds_min_iv":
        need = int(milestone["min_iv_sum"])
        good = {c.breed for c in save.cats if c.iv_atk + c.iv_hp >= need}
        return len(good), int(milestone["count"])
    return None, None


def _met(save: SaveData, milestone: dict[str, Any]) -> bool:
    if milestone.get("type") == "start":
        return True
    cur, tgt = _progress(save, milestone)
    return cur is not None and tgt is not None and cur >= tgt


def prestige_reached(content: Content, save: SaveData) -> int:
    """Nivel que os marcos dao, sequencial a partir do nivel guardado no save (o
    nivel n pede o n-1; o guardado nunca desce)."""
    reached = max(1, save.prestige)
    for lv in _levels(content):
        if lv["level"] <= reached:
            continue
        if lv["level"] != reached + 1 or not lv.get("enabled", False) \
                or not _met(save, lv["milestone"]):
            break
        reached = lv["level"]
    return reached


def prestige_level(content: Content, save: SaveData) -> int:
    """Nivel efetivo (puro): o maior entre o guardado e o dos marcos."""
    return max(save.prestige, prestige_reached(content, save))


def update_prestige(content: Content, save: SaveData) -> int:
    """Grava no save o nivel efetivo (nunca desce) e o devolve."""
    save.prestige = prestige_level(content, save)
    return save.prestige


def prestige_info(content: Content, save: SaveData) -> PrestigeInfo:
    """Nivel atual, proximo marco e o que falta (para a barra do portao)."""
    level = prestige_level(content, save)
    nxt = next((lv for lv in _levels(content) if lv["level"] == level + 1), None)
    if nxt is None:
        return PrestigeInfo(level, None, None, None, None, None, False)
    locked = not nxt.get("enabled", False)
    cur, tgt = (None, None) if locked else _progress(save, nxt["milestone"])
    missing = None if cur is None or tgt is None else max(0, tgt - cur)
    return PrestigeInfo(level, nxt["level"], dict(nxt["milestone"]), cur, tgt, missing,
                        locked)
