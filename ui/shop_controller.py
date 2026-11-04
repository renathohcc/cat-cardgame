"""Controlador da loja do hub (areas, racoes, decoracao). Puro (sem pygame).

So chama a API publica do `core` (`areas_status`, `unlock_area`, `rations_catalog`, `buy_ration`,
`decoration_catalog`, `buy_decoration`, `prestige_info`). Nenhuma regra mora aqui: preco, Prestigio
exigido e ordem das areas vem do core/`data/shop.json`; a UI so traduz o estado em texto e botoes.

Elementos clicaveis: ("shop_tab", nome) ("shop_area", id) ("shop_ration", id) ("shop_deco", id)
("shop_back",)   e, no painel da area (no cercado): ("area_buy", id) ("area_close",)
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from core import (SaveData, areas_status, buy_decoration, buy_ration, decoration_catalog, prestige_info,
                  rations_catalog, unlock_area, update_prestige)
from core import Content
from core.types import IllegalAction
from ui import layout_shop as LS, timing as timing_mod
from ui.controller import Toast
from ui.pen_world import DECOR_ANCHORS

Persist = Callable[[], "str | None"]

TABS = ("areas", "racoes", "decoracao")
TAB_NAME = {"areas": "ÁREAS", "racoes": "RAÇÕES", "decoracao": "DECORAÇÃO"}

# ids de `unlocks` do shop.json -> texto curto (pt-BR). Tipo desconhecido e ignorado.
def effect_text(unlock: dict[str, Any]) -> str:
    kind = unlock.get("type")
    if kind == "kitten_pen":
        return "Filhotes saem da cesta"
    if kind == "couple_slot":
        return f"Casal nº {unlock.get('couple', '?')} no breed"
    if kind == "decor_set":
        return f"Decoração do conjunto {str(unlock.get('set', '')).capitalize()}"
    if kind == "decor_rare":
        return "Decoração rara"
    return ""


def milestone_text(milestone: dict[str, Any] | None) -> str:
    """Frase do que falta para o proximo nivel de Prestigio (a partir do marco do core)."""
    if not milestone:
        return ""
    kind = milestone.get("type")
    if kind == "win_league":
        return f"vencer a liga {milestone.get('league', 1)}"
    if kind == "distinct_breeds":
        return f"ter {milestone.get('count', '?')} raças na coleção"
    if kind == "distinct_breeds_min_iv":
        return (f"{milestone.get('count', '?')} raças, cada uma com um gato de "
                f"IV total {milestone.get('min_iv_sum', '?')}+")
    return "marco ainda travado"


@dataclass
class AreaRow:
    id: str
    name: str
    description: str
    price: int
    prestige: int
    slots_bonus: int
    state: str                 # unlocked | available | blocked_prestige | blocked_coins | queued
    missing_coins: int
    missing_prestige: int
    effects: list[str]
    before: str = ""           # nome da area que precisa vir antes (state queued)

    @property
    def done(self) -> bool:
        return self.state == "unlocked"

    @property
    def can_buy(self) -> bool:
        return self.state == "available"

    def reason(self) -> str:
        """Por que nao da para comprar agora (vazio se da)."""
        if self.state == "blocked_prestige":
            return f"Precisa de Prestígio {self.prestige}."
        if self.state == "blocked_coins":
            return f"Faltam {self.missing_coins} moedas."
        if self.state == "queued":
            return f"Antes, compre: {self.before}."
        return ""

    def short(self) -> str:
        return {"unlocked": "", "available": "Pode comprar!", "blocked_prestige": "Falta Prestígio",
                "blocked_coins": f"Faltam {self.missing_coins}", "queued": "Em fila"}[self.state]

    def button(self) -> str:
        return {"unlocked": "COMPRADA", "available": f"COMPRAR {self.price}",
                "blocked_prestige": f"PRESTÍGIO {self.prestige}",
                "blocked_coins": f"FALTAM {self.missing_coins}", "queued": "EM FILA"}[self.state]


@dataclass
class RationRow:
    id: str
    name: str
    description: str
    price: int
    prestige: int
    stock: int
    prestige_ok: bool
    can_buy: bool
    missing_coins: int

    def button(self) -> str:
        if not self.prestige_ok:
            return f"PRESTÍGIO {self.prestige}"
        return f"COMPRAR {self.price}" if self.can_buy else f"FALTAM {self.missing_coins}"

    def reason(self) -> str:
        if not self.prestige_ok:
            return f"Precisa de Prestígio {self.prestige}."
        return "" if self.can_buy else f"Faltam {self.missing_coins} moedas."


@dataclass
class DecoRow:
    id: str
    name: str
    description: str
    price: int
    kind: str
    area_id: str
    area_name: str
    state: str                 # owned | available | locked_area
    soon: bool                 # placeholder sem objeto: "em breve"
    can_buy: bool
    missing_coins: int
    has_anchor: bool

    def button(self) -> str:
        if self.soon:
            return "EM BREVE"
        if self.state == "owned":
            return "COMPRADA"
        if self.state == "locked_area":
            return "ÁREA BLOQUEADA"
        return f"COMPRAR {self.price}" if self.can_buy else f"FALTAM {self.missing_coins}"

    def reason(self) -> str:
        if self.soon:
            return "Chega em breve."
        if self.state == "locked_area":
            return f"Antes: {self.area_name}."
        if self.state == "available" and not self.can_buy:
            return f"Faltam {self.missing_coins} moedas."
        return ""


class ShopController:
    def __init__(self, content: Content, save: SaveData, persist: Persist | None = None,
                 on_change: Callable[[], None] | None = None,
                 on_area: Callable[[str], None] | None = None) -> None:
        self.content = content
        self.save = save
        self.persist = persist
        self.on_change = on_change             # o hub religa o mundo do quintal
        self.on_area = on_area                 # area comprada (anim + som)
        self.tab = "areas"
        self.toast: Toast | None = None
        self.sold_flash = 0.0

    # ------------------------------------------------------------ consultas
    @property
    def coins(self) -> int:
        return self.save.coins

    def say(self, text: str, kind: str = "error", ttl: float = 2.5) -> None:
        self.toast = Toast(text, kind, ttl)

    def level(self) -> int:
        return update_prestige(self.content, self.save)

    def areas(self) -> list[AreaRow]:
        defs = {a["id"]: a for a in self.content.shop["areas"]}
        status = areas_status(self.content, self.save)
        out: list[AreaRow] = []
        nxt = next((s.name for s in status if s.state != "unlocked"), "")      # a area da vez
        for st in status:
            d = defs[st.id]
            out.append(AreaRow(st.id, st.name, d.get("description", ""), st.price, st.prestige_required,
                               st.slots_bonus, st.state, st.missing_coins, st.missing_prestige,
                               [t for t in (effect_text(u) for u in d.get("unlocks", [])) if t],
                               before=nxt))
        return out

    def area(self, area_id: str) -> AreaRow | None:
        return next((a for a in self.areas() if a.id == area_id), None)

    def rations(self) -> list[RationRow]:
        return [RationRow(r["id"], r["name"], r.get("description", ""), r["price"], r["prestige_required"],
                          r["stock"], r["prestige_ok"], r["can_buy"], max(0, r["price"] - self.coins))
                for r in rations_catalog(self.content, self.save)]

    def decorations(self) -> list[DecoRow]:
        names = {a["id"]: a["name"] for a in self.content.shop["areas"]}
        out = []
        for d in decoration_catalog(self.content, self.save):
            ok = d["state"] == "available" and not d.get("placeholder") and self.coins >= d["price"]
            out.append(DecoRow(d["id"], d["name"], d.get("description", ""), d["price"], d.get("kind", ""),
                               d["area_required"], names.get(d["area_required"], d["area_required"]), d["state"],
                               bool(d.get("placeholder")) or d["id"] not in DECOR_ANCHORS, ok,
                               max(0, d["price"] - self.coins), d["id"] in DECOR_ANCHORS))
        return out

    def stats(self) -> dict[str, Any]:
        return {"coins": self.coins, "info": prestige_info(self.content, self.save)}

    # ------------------------------------------------------------ entrada
    def hit(self, pos: tuple[int, int]) -> tuple | None:
        return LS.shop_hit(pos, self.tab, [a.id for a in self.areas()], [r.id for r in self.rations()],
                           [d.id for d in self.decorations()])

    def click(self, elem: tuple | None) -> str | tuple | None:
        """Devolve "back" para fechar, ("goto_area", id) para ver a placa no quintal."""
        if elem is None:
            return None
        kind = elem[0]
        if kind == "shop_back":
            return "back"
        if kind == "shop_tab" and elem[1] in TABS:
            self.tab = elem[1]
        elif kind == "shop_area":
            row = self.area(elem[1])
            if row is not None and not row.done:
                return ("goto_area", row.id)
        elif kind == "shop_ration":
            self.buy_ration(elem[1])
        elif kind == "shop_deco":
            self.buy_deco(elem[1])
        return None

    # ------------------------------------------------------------ compras
    def _saved(self) -> None:
        if self.persist is not None:
            err = self.persist()
            if err:
                self.say(f"Não consegui salvar: {err}")

    def buy_area(self, area_id: str) -> bool:
        try:
            res = unlock_area(self.content, self.save, area_id)
        except IllegalAction as e:
            self.say(str(e))
            return False
        self.say(f"Área aberta! Agora são {res.slots_after} vagas.", "info", timing_mod.current().economy.area_toast)
        self._saved()
        if self.on_change:
            self.on_change()
        if self.on_area:
            self.on_area(area_id)
        return True

    def buy_ration(self, ration_id: str) -> bool:
        row = next((r for r in self.rations() if r.id == ration_id), None)
        try:
            stock = buy_ration(self.content, self.save, ration_id)
        except IllegalAction as e:
            self.say(str(e))
            return False
        self.say(f"{row.name if row else 'Ração'} comprada (estoque {stock}).", "info")
        self._saved()
        return True

    def buy_deco(self, deco_id: str) -> bool:
        row = next((d for d in self.decorations() if d.id == deco_id), None)
        if row is None:
            return False
        if row.soon:
            self.say("Essa peça chega em breve.", "warn")
            return False
        try:
            buy_decoration(self.content, self.save, deco_id)
        except IllegalAction as e:
            self.say(str(e))
            return False
        self.say(f"{row.name}: peça colocada no quintal.", "info")
        self._saved()
        if self.on_change:
            self.on_change()
        return True

    def update(self, dt: float) -> None:
        if self.toast:
            self.toast.ttl -= dt
            if self.toast.ttl <= 0:
                self.toast = None
