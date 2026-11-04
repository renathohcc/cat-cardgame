"""Loja (data/shop.json): acessores, carteira, racao e decoracao. Puro, sem sorteio."""
from __future__ import annotations

from typing import Any

from core.prestige import prestige_level, update_prestige
from core.save import SaveData
from core.types import Content, IllegalAction

__all__ = ["shop_cfg", "ration_def", "rations_catalog", "buy_ration", "ration_stock",
           "decoration_catalog", "available_decorations", "buy_decoration",
           "next_goal", "spend_coins"]


def shop_cfg(content: Content) -> dict[str, Any]:
    if not content.shop:
        raise ValueError("conteudo sem data/shop.json: nao ha loja")
    return content.shop


def spend_coins(save: SaveData, price: int) -> None:
    if save.coins < price:
        raise IllegalAction(f"Moedas insuficientes: faltam {price - save.coins}.")
    save.coins -= price


def ration_def(content: Content, ration_id: str) -> dict[str, Any]:
    for r in shop_cfg(content)["rations"]:
        if r["id"] == ration_id:
            return r
    raise IllegalAction(f"Ração inexistente: {ration_id!r}.")


def ration_stock(save: SaveData, ration_id: str) -> int:
    return int(save.rations.get(ration_id, 0))


def rations_catalog(content: Content, save: SaveData) -> list[dict[str, Any]]:
    """Racoes com preco, Prestigio, estoque e se da para comprar agora."""
    level = prestige_level(content, save)      # puro: consultar nao grava
    out = []
    for r in shop_cfg(content)["rations"]:
        out.append({**r, "stock": ration_stock(save, r["id"]),
                    "prestige_ok": level >= r["prestige_required"],
                    "can_buy": level >= r["prestige_required"] and save.coins >= r["price"]})
    return out


def buy_ration(content: Content, save: SaveData, ration_id: str) -> int:
    """Compra 1 racao. Devolve o novo estoque. Nao altera o save se falhar."""
    r = ration_def(content, ration_id)
    if update_prestige(content, save) < r["prestige_required"]:
        raise IllegalAction(f"Precisa de Prestígio {r['prestige_required']}.")
    spend_coins(save, r["price"])
    save.rations[ration_id] = ration_stock(save, ration_id) + 1
    return save.rations[ration_id]


# ------------------------------------------------------------ decoracao
def _decor_state(save: SaveData, d: dict[str, Any]) -> str:
    if d["id"] in save.decorations_owned:
        return "owned"
    if d["area_required"] not in save.areas_unlocked:
        return "locked_area"
    return "available"


def decoration_catalog(content: Content, save: SaveData) -> list[dict[str, Any]]:
    """Todas as pecas com `state`: owned | available | locked_area."""
    return [{**d, "state": _decor_state(save, d)} for d in shop_cfg(content)["decorations"]]


def available_decorations(content: Content, save: SaveData) -> list[dict[str, Any]]:
    return [d for d in decoration_catalog(content, save) if d["state"] == "available"]


def buy_decoration(content: Content, save: SaveData, decoration_id: str) -> dict[str, Any]:
    deco = next((d for d in shop_cfg(content)["decorations"] if d["id"] == decoration_id),
                None)
    if deco is None:
        raise IllegalAction(f"Decoração inexistente: {decoration_id!r}.")
    state = _decor_state(save, deco)
    if state == "owned":
        raise IllegalAction("Decoração já comprada.")
    if state == "locked_area":
        raise IllegalAction("Desbloqueie a área desta decoração primeiro.")
    spend_coins(save, deco["price"])
    save.decorations_owned.append(decoration_id)
    return deco


# ------------------------------------------------------------ meta
def next_goal(content: Content, save: SaveData) -> dict[str, Any] | None:
    """Item mais barato ainda nao comprado e liberado pelo Prestigio (barra de
    meta do fim da run): proxima area (so a da vez) ou decoracao disponivel.
    Racao e consumivel e fica fora. {"kind","id","name","price","missing"} ou None."""
    from core.kennel import next_area   # evita ciclo de import
    level = prestige_level(content, save)      # puro: consultar nao grava
    options: list[dict[str, Any]] = []
    area = next_area(content, save)
    if area is not None and level >= area["prestige_required"]:
        options.append({"kind": "area", **_goal(area, save)})
    for d in available_decorations(content, save):
        options.append({"kind": "decoration", **_goal(d, save)})
    return min(options, key=lambda o: (o["price"], o["id"])) if options else None


def _goal(item: dict[str, Any], save: SaveData) -> dict[str, Any]:
    return {"id": item["id"], "name": item["name"], "price": item["price"],
            "missing": max(0, item["price"] - save.coins)}
