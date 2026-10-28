"""Mini-run: mapa em camadas, draft e deck da run. Puro, RNG injetado."""
from __future__ import annotations

import copy
from dataclasses import asdict
from random import Random
from typing import Any

from core.cats import roll_cat
from core.duel import card_from_effect, card_from_special, new_duel_vs_enemy
from core.types import Cat, Content, DeckSpec, Duel, IllegalAction

__all__ = ["Run", "new_run", "draft_pool", "RUN_STATUSES"]

RUN_STATUSES = ("map", "draft", "duel", "finished")


def _run_cfg(content: Content) -> dict[str, Any]:
    cfg = content.run
    if not cfg:
        raise ValueError("conteudo sem data/run.json: nao ha run")
    return cfg


def draft_pool(content: Content) -> list[str]:
    """Ids sorteaveis no draft (ordem deterministica). Sem `pool`: todos os
    efeitos e Espiritos. `pool` pode ser lista de ids ou dict de listas de ids."""
    cfg = _run_cfg(content)
    raw = cfg.get("pool", cfg.get("draft_pool"))
    if raw is None:
        raw = {"effects": True, "specials": True}
    if isinstance(raw, dict):   # formato de data/run.json: {"effects": bool|[ids], ...}
        ids = []
        for key, table in (("effects", content.effects), ("specials", content.specials)):
            v = raw.get(key, False)
            ids += list(table) if v is True else (list(v) if v else [])
    else:
        ids = list(raw)
    for i in ids:
        if i not in content.effects and i not in content.specials:
            raise ValueError(f"run.json: carta de draft inexistente '{i}'")
    return list(dict.fromkeys(ids))


def _rng_state(rng: Random) -> list[Any]:
    version, internal, gauss = rng.getstate()
    return [version, list(internal), gauss]


def _set_rng_state(rng: Random, st: list[Any]) -> None:
    rng.setstate((st[0], tuple(st[1]), st[2]))


class Run:
    """Estado de uma run. Estados: map -> (duel | draft) -> map ... -> finished."""

    def __init__(self, content: Content, rng: Random, cats: list[Cat]) -> None:
        self.content = content
        self.rng = rng
        self.cfg = _run_cfg(content)
        self.cats: list[Cat] = cats
        self.cards: list[str] = []          # ids de efeitos/Espiritos do draft
        self.layer = 0
        self.status = "map"
        self.result: str | None = None      # "vitoria" | "derrota"
        self.nodes_cleared = 0
        self.node: dict[str, Any] | None = None   # no escolhido na camada atual
        self.draft_options: list[str] = []
        self.drafts_left = 0        # drafts ainda por abrir DEPOIS do atual
        self.draft_total = 0        # tamanho da sequencia de drafts em curso
        self._draft_taken: list[str] = []   # escolhidas nesta sequencia
        self._draft_key = "draft_options"
        self.duel: Duel | None = None

    # ------------------------------------------------------------ consulta
    @property
    def layers(self) -> list[dict[str, Any]]:
        return self.cfg["map"]["layers"]

    @property
    def draft_step(self) -> int:
        """Posicao (1-based) do draft atual na sequencia; 0 fora de draft."""
        if self.status != "draft":
            return 0
        return self.draft_total - self.drafts_left

    def available_nodes(self) -> list[dict[str, Any]]:
        if self.status != "map":
            return []
        return [copy.deepcopy(n) for n in self.layers[self.layer]["nodes"]]

    def deck_spec(self) -> DeckSpec:
        """Deck atual da run (copias; o duelo nao altera a run)."""
        cards = [card_from_special(self.content, c) if c in self.content.specials
                 else card_from_effect(self.content, c) for c in self.cards]
        return DeckSpec(cats=[copy.copy(c) for c in self.cats], cards=cards)

    def deck_size(self) -> int:
        return len(self.cats) + len(self.cards)

    def _need(self, status: str, what: str) -> None:
        if self.status != status:
            raise IllegalAction(f"{what}: run em '{self.status}', esperado '{status}'")

    # ------------------------------------------------------------ transicoes
    def choose_node(self, node_id: str) -> None:
        self._need("map", "choose_node")
        for n in self.layers[self.layer]["nodes"]:
            if n["id"] == node_id:
                self.node = copy.deepcopy(n)
                break
        else:
            raise IllegalAction(f"no '{node_id}' nao esta disponivel nesta camada")
        if self.node["tipo"] == "descanso":
            if self.cfg.get("rest_draft", True):
                self._open_draft("draft_options_rest", 1, fallback="draft_options")
            else:
                self.nodes_cleared += 1
                self._advance()
        else:
            self.status = "duel"

    def start_duel(self, rng: Random, player_first: bool | None = None) -> Duel:
        self._need("duel", "start_duel")
        if self.duel is not None:
            raise IllegalAction("start_duel: duelo ja em andamento")
        enemy = self.node["inimigo"]
        if not enemy:
            raise IllegalAction(f"no '{self.node['id']}' sem inimigo")
        self.duel = new_duel_vs_enemy(self.content, self.deck_spec(), enemy, rng,
                                      player_first)
        return self.duel

    def finish_duel(self, duel: Duel) -> None:
        self._need("duel", "finish_duel")
        if duel is not self.duel:
            raise IllegalAction("finish_duel: duelo nao pertence a esta run")
        if duel.winner is None:
            raise IllegalAction("finish_duel: duelo ainda nao terminou")
        self.duel = None
        if duel.winner != "player":
            self._finish("derrota")
            return
        self.nodes_cleared += 1
        if self.node["tipo"] == "chefe":
            self._finish("vitoria")
        else:
            if self.node["tipo"] == "elite":
                self._open_draft("draft_options_elite", self.cfg.get("drafts_elite", 1),
                                 fallback="draft_options")
            else:
                self._open_draft("draft_options", 1)

    def pick_draft(self, index: int) -> str:
        self._need("draft", "pick_draft")
        if isinstance(index, bool) or not isinstance(index, int) \
                or not 0 <= index < len(self.draft_options):
            raise IllegalAction(f"pick_draft: indice invalido {index!r}")
        card = self.draft_options[index]
        self.cards.append(card)
        self.draft_options = []
        self._draft_taken.append(card)
        if self.drafts_left > 0:
            self.drafts_left -= 1
            self._roll_draft()
            return card
        self.draft_total = 0
        self._draft_taken = []
        if self.node["tipo"] == "descanso":
            self.nodes_cleared += 1
        self._advance()
        return card

    def _advance(self) -> None:
        self.node = None
        self.layer += 1
        if self.layer >= len(self.layers):
            self._finish("vitoria")
        else:
            self.status = "map"

    def abandon(self) -> None:
        if self.status == "finished":
            raise IllegalAction("run ja encerrada")
        self.duel = None
        self._finish("derrota")

    # ------------------------------------------------------------ internos
    def _open_draft(self, key: str, count: int, fallback: str = "draft_options") -> None:
        self._draft_key = key if key in self.cfg else fallback
        self.draft_total = max(1, int(count))
        self.drafts_left = self.draft_total - 1
        self._draft_taken = []
        self._roll_draft()

    def _roll_draft(self) -> None:
        n = self.cfg.get(self._draft_key, 3)
        pool = draft_pool(self.content)
        fresh = [c for c in pool if c not in self._draft_taken]
        if len(fresh) >= min(n, len(pool)):   # sem repetir a ja escolhida na sequencia
            pool = fresh
        self.draft_options = self.rng.sample(pool, min(n, len(pool)))
        self.status = "draft"

    def _finish(self, result: str) -> None:
        self.status = "finished"
        self.result = result
        self.node = None
        self.draft_options = []
        self.drafts_left = self.draft_total = 0
        self._draft_taken = []

    # ------------------------------------------------------------ serializacao
    def to_dict(self) -> dict[str, Any]:
        if self.duel is not None:
            raise IllegalAction("to_dict: a run so e salva entre duelos")
        return {
            "version": 1,
            "status": self.status, "result": self.result, "layer": self.layer,
            "nodes_cleared": self.nodes_cleared, "node": copy.deepcopy(self.node),
            "draft_options": list(self.draft_options),
            "drafts_left": self.drafts_left, "draft_total": self.draft_total,
            "draft_taken": list(self._draft_taken), "draft_key": self._draft_key,
            "cats": [asdict(c) for c in self.cats], "cards": list(self.cards),
            "rng": _rng_state(self.rng),
        }

    @classmethod
    def from_dict(cls, content: Content, d: dict[str, Any]) -> "Run":
        if d.get("version") != 1:
            raise ValueError(f"versao de run desconhecida: {d.get('version')!r}")
        if d["status"] not in RUN_STATUSES:
            raise ValueError(f"status de run invalido: {d['status']!r}")
        run = cls(content, Random(), [Cat(**c) for c in d["cats"]])
        run.status, run.result, run.layer = d["status"], d["result"], d["layer"]
        run.nodes_cleared = d["nodes_cleared"]
        run.node = copy.deepcopy(d["node"])
        run.draft_options = list(d["draft_options"])
        run.cards = list(d["cards"])
        in_draft = run.status == "draft"
        run.drafts_left = d.get("drafts_left", 0)
        run.draft_total = d.get("draft_total", 1 if in_draft else 0)
        run._draft_taken = list(d.get("draft_taken", []))
        run._draft_key = d.get("draft_key", "draft_options")
        _set_rng_state(run.rng, d["rng"])
        return run


def new_run(content: Content, rng: Random) -> Run:
    """Cria a run: deck inicial de gatos adultos sorteados pelo `rng`."""
    cfg = _run_cfg(content)
    start = cfg["start_deck"]
    size = content.rules["duel"]["deck_size"]
    if start.get("origem", "sorteio") != "sorteio":
        raise ValueError(f"start_deck.origem desconhecida: '{start.get('origem')}'")
    if start["gatos"] != size:
        raise ValueError(f"start_deck.gatos ({start['gatos']}) != rules.duel.deck_size ({size})")
    cats = []
    for i in range(size):
        cat = roll_cat(content, rng)
        cat.id = f"run-{i + 1}"
        cats.append(cat)
    return Run(content, rng, cats)
