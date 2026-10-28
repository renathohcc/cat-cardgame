"""Controlador da tela de Adocao pos-run. Puro (sem pygame).

So chama a API publica do core (`adopt`, `donate_offer`, `donation_value`, `cat_stats`,
`has_pending_adoption`). Cada decisao grava o save; falha de gravacao vira aviso.

Elementos clicaveis: ("reveal", id) ("reveal_all",) ("page", +-1) ("adopt", id) ("donate", id)
"""
from __future__ import annotations

from typing import Callable

from core import (SaveData, adopt, cat_stats, donate_offer, donation_value,
                  has_pending_adoption)
from core.types import Cat, Content, IllegalAction, Stats
from ui import layout_hub as LH
from ui.controller import Toast

Persist = Callable[[], "str | None"]


class AdoptionController:
    def __init__(self, content: Content, save: SaveData, persist: Persist | None = None) -> None:
        self.content = content
        self.save = save
        self.persist = persist
        self.page = 0
        self.revealed: set[str] = set()
        self.toast: Toast | None = None
        self.high_sum = int((content.rules.get("adoption") or {}).get("high_iv_sum", 8))

    # ------------------------------------------------------------ consultas
    def say(self, text: str, kind: str = "error", ttl: float = 2.5) -> None:
        self.toast = Toast(text, kind, ttl)

    @property
    def coins(self) -> int:
        return self.save.coins

    def cats(self) -> list[Cat]:
        return list(self.save.pending_adoption["cats"]) if has_pending_adoption(self.save) else []

    @property
    def done(self) -> bool:
        return not has_pending_adoption(self.save)

    @property
    def pages(self) -> int:
        return max(1, -(-len(self.cats()) // LH.ADOPT_PER_PAGE))

    @property
    def paged(self) -> bool:
        return self.pages > 1

    def visible(self) -> list[Cat]:
        self.page = max(0, min(self.page, self.pages - 1))
        a = self.page * LH.ADOPT_PER_PAGE
        return self.cats()[a:a + LH.ADOPT_PER_PAGE]

    def visible_ids(self) -> list[str]:
        return [c.id for c in self.visible()]

    def all_revealed(self) -> bool:
        return all(c.id in self.revealed for c in self.cats())

    def summary(self) -> str:
        p = self.save.pending_adoption or {}
        res = p.get("result", "")
        word = {"vitoria": "Vitória", "victory": "Vitória", "abandono": "Abandono"}.get(res, "Derrota")
        return f"{word}, {p.get('nodes_cleared', 0)} nós vencidos"

    def breed_name(self, cat: Cat) -> str:
        return self.content.breeds.get(cat.breed, {}).get("nome", cat.breed)

    def nature_name(self, cat: Cat) -> str:
        return self.content.natures.get(cat.nature, {}).get("nome", cat.nature)

    def nature_effect(self, cat: Cat) -> str:
        n = self.content.natures.get(cat.nature, {})
        return f"ATK {n.get('atk', 0):+d}  HP {n.get('hp', 0):+d}"

    def keyword_names(self, cat: Cat) -> list[tuple[str, str]]:
        ids = self.content.breeds.get(cat.breed, {}).get("keywords", [])
        return [(k, self.content.keywords.get(k, {}).get("nome", k)) for k in ids]

    def stats_of(self, cat: Cat) -> Stats:
        return cat_stats(self.content, cat)

    def value_of(self, cat: Cat) -> int:
        return donation_value(self.content, cat)

    def tier(self, cat: Cat) -> str:
        """"perfeito" (IV 5/5), "alto" (soma >= limite) ou ""."""
        if cat.iv_atk == 5 and cat.iv_hp == 5:
            return "perfeito"
        return "alto" if cat.iv_atk + cat.iv_hp >= self.high_sum else ""

    # ------------------------------------------------------------ entrada
    def hit(self, pos: tuple[int, int]) -> tuple | None:
        return LH.adopt_hit(pos, self.visible_ids(), self.revealed, self.paged)

    def click(self, elem: tuple | None) -> str | None:
        """Devolve "done" quando a oferta acabou."""
        if elem is None:
            return None
        kind = elem[0]
        try:
            if kind == "reveal" and elem[1] in self.visible_ids():
                self.revealed.add(elem[1])
            elif kind == "reveal_all":
                self.revealed.update(c.id for c in self.cats())
            elif kind == "page":
                self.scroll_by(elem[1])
            elif kind in ("adopt", "donate") and elem[1] in self.revealed:
                self._decide(kind, elem[1])
        except IllegalAction as e:
            self.say(str(e))
        return "done" if self.done else None

    def scroll_by(self, n: int) -> None:
        self.page = max(0, min(self.page + n, self.pages - 1))

    def _decide(self, kind: str, cat_id: str) -> None:
        cat = next((c for c in self.cats() if c.id == cat_id), None)
        if cat is None:
            return
        name = self.breed_name(cat)
        if kind == "adopt":
            adopt(self.content, self.save, cat_id)
            msg = f"{name} adotado!"
        else:
            msg = f"{name} doado: +{donate_offer(self.content, self.save, cat_id)} moedas."
        self.revealed.discard(cat_id)
        self.say(msg, "info")
        if self.persist is not None:
            err = self.persist()
            if err:
                self.say(f"Não consegui salvar: {err}")

    def update(self, dt: float) -> None:
        if self.toast:
            self.toast.ttl -= dt
            if self.toast.ttl <= 0:
                self.toast = None
