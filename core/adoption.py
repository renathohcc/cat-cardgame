"""Adocao pos-run, doacao e moedas (Fase 5b). Sem breed/filhotes (5c)."""
from __future__ import annotations

from random import Random
from typing import Any

from core.cats import roll_cat
from core.collection import available_cats, get_cat
from core.save import SaveData, format_cat_id, register_dex
from core.types import Cat, Content, IllegalAction

__all__ = ["adoption_weights", "adoption_count", "donation_value", "create_adoption",
           "adopt", "donate_offer", "donate_cat", "can_donate", "has_pending_adoption"]

_MAX_TRIES = 200
_VICTORY = ("vitoria", "victory")


def _cfg(content: Content) -> dict[str, Any]:
    return content.rules.get("adoption", {}) or {}


def _base_weights(content: Content) -> dict[int, int]:
    w = content.rules["iv_weights"]
    if any(v is None for v in w.values()):
        raise ValueError("rules.iv_weights tem pesos null")
    return {int(k): int(v) for k, v in w.items()}


def adoption_weights(content: Content, nodes_cleared: int) -> dict[int, int]:
    """Pesos de IV da oferta: cada no desloca `iv_shift_per_node` de `from` para `to`."""
    cfg = _cfg(content)
    per = int(cfg.get("iv_shift_per_node", 2))
    src, dst = int(cfg.get("iv_shift_from", 1)), int(cfg.get("iv_shift_to", 5))
    w = _base_weights(content)
    moved = min(w.get(src, 0), per * max(0, nodes_cleared))
    w[src] = w.get(src, 0) - moved
    w[dst] = w.get(dst, 0) + moved
    return w


def adoption_count(content: Content, nodes_cleared: int, result: str) -> int:
    cfg = _cfg(content)
    n = max(0, nodes_cleared) // max(1, int(cfg.get("nodes_per_cat", 2)))
    if result in _VICTORY:
        n += int(cfg.get("victory_bonus_cats", 2))
    return n


def donation_value(content: Content, cat: Cat) -> int:
    cfg = _cfg(content)
    table = cfg.get("donation_by_iv_sum") or []
    total = cat.iv_atk + cat.iv_hp
    best_min, value = None, 0
    for row in table:
        m = int(row["min_sum"])
        if m <= total and (best_min is None or m > best_min):
            best_min, value = m, int(row["coins"])
    if cat.stage == "kitten":
        value = int(value * float(cfg.get("kitten_donation_factor", 0.5)))
    return value


def has_pending_adoption(save: SaveData) -> bool:
    return bool(save.pending_adoption and save.pending_adoption["cats"])


def _sum(c: Cat) -> int:
    return c.iv_atk + c.iv_hp


def _high_cat(content: Content, rng: Random, weights: dict[int, int],
              high: int) -> Cat:
    """Gato com soma >= high: rejeicao limitada, depois eleva IVs deterministicamente."""
    cat = roll_cat(content, rng, iv_weights=weights)
    for _ in range(_MAX_TRIES):
        if _sum(cat) >= high:
            return cat
        cat = roll_cat(content, rng, iv_weights=weights)
    while _sum(cat) < high and (cat.iv_atk < 5 or cat.iv_hp < 5):
        if cat.iv_atk <= cat.iv_hp and cat.iv_atk < 5:
            cat.iv_atk += 1
        else:
            cat.iv_hp += 1
    return cat


def create_adoption(content: Content, save: SaveData, rng: Random, result: str,
                    nodes_cleared: int) -> None:
    if has_pending_adoption(save):
        raise IllegalAction("ja existe uma adocao pendente")
    cfg = _cfg(content)
    high = int(cfg.get("high_iv_sum", 8))
    pity_runs = int(cfg.get("pity_runs", 5))
    weights = adoption_weights(content, nodes_cleared)
    cats = [roll_cat(content, rng, iv_weights=weights)
            for _ in range(adoption_count(content, nodes_cleared, result))]
    if cats:  # oferta vazia nao cria gato nem mexe no pity
        if save.pity.get("runs_without_high_iv", 0) >= pity_runs \
                and not any(_sum(c) >= high for c in cats):
            low = min(range(len(cats)), key=lambda i: _sum(cats[i]))
            cats[low] = _high_cat(content, rng, weights, high)
        if any(_sum(c) >= high for c in cats):
            save.pity["runs_without_high_iv"] = 0
        else:
            save.pity["runs_without_high_iv"] = save.pity.get("runs_without_high_iv", 0) + 1
    for c in cats:
        c.id = format_cat_id(save.next_cat_id)
        save.next_cat_id += 1
    save.progress["best_distance"] = max(save.progress.get("best_distance", 0),
                                         nodes_cleared)
    save.pending_adoption = ({"cats": cats, "result": result,
                              "nodes_cleared": nodes_cleared} if cats else None)


def _take(save: SaveData, cat_id: str) -> Cat:
    if not has_pending_adoption(save):
        raise IllegalAction("nao ha adocao pendente")
    cats = save.pending_adoption["cats"]  # type: ignore[index]
    for i, c in enumerate(cats):
        if c.id == cat_id:
            cats.pop(i)
            if not cats:
                save.pending_adoption = None
            return c
    raise IllegalAction(f"gato {cat_id!r} nao esta na oferta")


def adopt(content: Content, save: SaveData, cat_id: str) -> Cat:
    cat = _take(save, cat_id)
    save.cats.append(cat)
    register_dex(save, cat)
    return cat


def donate_offer(content: Content, save: SaveData, cat_id: str) -> int:
    cat = _take(save, cat_id)
    value = donation_value(content, cat)
    save.coins += value
    return value


def can_donate(content: Content, save: SaveData, cat_id: str) -> tuple[bool, str]:
    """(ok, motivo em portugues). Motivo vazio quando ok."""
    if not any(c.id == cat_id for c in save.cats):
        return False, "Gato inexistente."
    if any(cat_id in (b.get("male"), b.get("female")) for b in save.breeding):
        return False, "Gato em breed."
    size = content.rules["duel"]["deck_size"]
    if len([c for c in available_cats(save) if c.id != cat_id]) < size:
        return False, f"Precisa manter {size} adultos disponíveis."
    return True, ""


def donate_cat(content: Content, save: SaveData, cat_id: str) -> int:
    ok, reason = can_donate(content, save, cat_id)
    if not ok:
        raise IllegalAction(reason)
    cat = get_cat(save, cat_id)
    value = donation_value(content, cat)
    save.cats = [c for c in save.cats if c.id != cat_id]
    save.deck = [i for i in save.deck if i != cat_id]
    save.coins += value
    return value
