"""Gatil e quintal: vagas, areas compradas, casais paralelos, gatil cheio."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.prestige import prestige_level
from core.save import SaveData
from core.shop import shop_cfg, spend_coins
from core.types import Content, IllegalAction

__all__ = ["AreaStatus", "AreaUnlock", "kennel_slots", "kennel_capacity", "occupied", "kennel_over_limit",
           "can_adopt", "couples_allowed", "kittens_in_basket", "next_area",
           "area_status", "areas_status", "available_areas", "areas_blocked_by_prestige",
           "areas_blocked_by_coins", "unlock_area"]


def _areas(content: Content) -> list[dict[str, Any]]:
    return sorted(shop_cfg(content)["areas"], key=lambda a: a["order"])


def _unlocked(content: Content, save: SaveData) -> list[dict[str, Any]]:
    return [a for a in _areas(content) if a["id"] in save.areas_unlocked]


def _effects(areas: list[dict[str, Any]], kind: str) -> list[dict[str, Any]]:
    return [u for a in areas for u in a.get("unlocks", []) if u["type"] == kind]


# ------------------------------------------------------------ vagas
def kennel_slots(content: Content, save: SaveData) -> int:
    """Vagas do gatil: start.slots + bonus das areas compradas (max `max_slots`)."""
    shop = shop_cfg(content)
    bonus = sum(a["slots_bonus"] for a in _unlocked(content, save))
    return min(int(shop["max_slots"]), int(shop["start"]["slots"]) + bonus)


def occupied(save: SaveData) -> int:
    """Gatos que ocupam vaga: adultos, filhotes, casais em breed e o deck (todos
    estao em `save.cats`). Oferta pendente de adocao nao conta."""
    return len(save.cats)


def kennel_capacity(content: Content, save: SaveData) -> int:
    """Capacidade efetiva: max(vagas pelas areas, min(legacy_capacity, total de gatos)).
    As vagas de legado (saves v1) somem conforme o jogador doa e nao voltam."""
    return max(kennel_slots(content, save), min(save.legacy_capacity, occupied(save)))


def kennel_over_limit(content: Content, save: SaveData) -> bool:
    return occupied(save) > kennel_capacity(content, save)


def can_adopt(content: Content, save: SaveData) -> tuple[bool, str]:
    """(ok, motivo). Adotar exige uma vaga livre; gatil cheio pede doar um gato
    da colecao (`room_candidates`) ou o gato novo (`donate_offer`)."""
    free = kennel_capacity(content, save) - occupied(save)
    if free >= 1:
        return True, ""
    if free == 0:
        return False, "Gatil cheio: doe um gato para abrir espaço, ou doe o novo."
    return False, "Gatil acima do limite: doe gatos até voltar ao limite."


# ------------------------------------------------------------ casais e filhotes
def couples_allowed(content: Content, save: SaveData) -> int:
    """Casais paralelos: start.couples + 1 por area `couple_slot` comprada."""
    return int(shop_cfg(content)["start"]["couples"]) \
        + len(_effects(_unlocked(content, save), "couple_slot"))


def kittens_in_basket(content: Content, save: SaveData) -> bool:
    """True enquanto os filhotes ficam na cesta (antes da area `kitten_pen`)."""
    if not shop_cfg(content)["start"]["kittens_in_basket"]:
        return False
    return not _effects(_unlocked(content, save), "kitten_pen")


# ------------------------------------------------------------ areas
@dataclass(frozen=True)
class AreaStatus:
    """state: unlocked | available | blocked_prestige | blocked_coins | queued
    (queued = ainda nao e a vez: so a proxima da lista pode ser comprada)."""
    id: str
    name: str
    price: int
    prestige_required: int
    slots_bonus: int
    state: str
    missing_coins: int
    missing_prestige: int


@dataclass(frozen=True)
class AreaUnlock:
    area_id: str
    price: int
    slots_bonus: int
    slots_after: int
    coins_left: int
    effects: list[dict[str, Any]] = field(default_factory=list)   # `unlocks` do JSON


def next_area(content: Content, save: SaveData) -> dict[str, Any] | None:
    """Proxima area da lista que ainda nao foi comprada (None = tudo aberto)."""
    return next((a for a in _areas(content) if a["id"] not in save.areas_unlocked), None)


def area_status(content: Content, save: SaveData, area_id: str) -> AreaStatus:
    area = next((a for a in _areas(content) if a["id"] == area_id), None)
    if area is None:
        raise IllegalAction(f"Área inexistente: {area_id!r}.")
    level = prestige_level(content, save)      # puro: consultar nao grava
    m_coins = max(0, area["price"] - save.coins)
    m_prest = max(0, area["prestige_required"] - level)
    nxt = next_area(content, save)
    if area["id"] in save.areas_unlocked:
        state = "unlocked"
    elif nxt is None or nxt["id"] != area["id"]:
        state = "queued"
    elif m_prest:
        state = "blocked_prestige"
    elif m_coins:
        state = "blocked_coins"
    else:
        state = "available"
    return AreaStatus(area["id"], area["name"], area["price"], area["prestige_required"],
                      area["slots_bonus"], state, m_coins, m_prest)


def areas_status(content: Content, save: SaveData) -> list[AreaStatus]:
    return [area_status(content, save, a["id"]) for a in _areas(content)]


def _by_state(content: Content, save: SaveData, state: str) -> list[AreaStatus]:
    return [s for s in areas_status(content, save) if s.state == state]


def available_areas(content: Content, save: SaveData) -> list[AreaStatus]:
    """Areas que podem ser compradas agora (no maximo uma: a da vez)."""
    return _by_state(content, save, "available")


def areas_blocked_by_prestige(content: Content, save: SaveData) -> list[AreaStatus]:
    return _by_state(content, save, "blocked_prestige")


def areas_blocked_by_coins(content: Content, save: SaveData) -> list[AreaStatus]:
    return _by_state(content, save, "blocked_coins")


def unlock_area(content: Content, save: SaveData, area_id: str) -> AreaUnlock:
    """Compra a area da vez. Valida tudo antes de debitar (falha = save intacto)."""
    status = area_status(content, save, area_id)
    if status.state == "unlocked":
        raise IllegalAction("Área já desbloqueada.")
    if status.state == "queued":
        raise IllegalAction("Desbloqueie as áreas anteriores primeiro.")
    if status.state == "blocked_prestige":
        raise IllegalAction(f"Precisa de Prestígio {status.prestige_required}.")
    if status.state == "blocked_coins":
        raise IllegalAction(f"Moedas insuficientes: faltam {status.missing_coins}.")
    spend_coins(save, status.price)
    save.areas_unlocked.append(area_id)
    area = next(a for a in _areas(content) if a["id"] == area_id)
    return AreaUnlock(area_id, status.price, status.slots_bonus,
                      kennel_slots(content, save), save.coins,
                      [dict(u) for u in area.get("unlocks", [])])
