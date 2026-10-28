"""Controlador da tela de Colecao. Puro (sem pygame).

So chama a API publica do core (`available_cats`, `set_deck`, `autofill_deck`, `rename_cat`,
`new_run_from_save`, `cat_stats`); nenhuma regra mora aqui. `IllegalAction` vira aviso.

Elementos clicaveis (`elem`):
    ("row", cat_id)  ("scroll", +-1)  ("sort", chave)  ("filter",)  ("rename",)
    ("complete",)  ("clear",)  ("start",)  ("back",)  ("rename_ok",)  ("rename_cancel",)
"""
from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Callable

from core import (SaveData, autofill_deck, available_cats, cat_stats, get_cat,
                  new_run_from_save, rename_cat, set_deck)
from core.run import Run
from core.types import Cat, Content, IllegalAction, Stats
from ui import layout_hub as LH
from ui.controller import Toast

SORT_LABEL = {"poder": "PODER", "raca": "RAÇA", "nome": "NOME"}
STATE_LABEL = {"deck": "deck", "livre": "livre", "filhote": "filh", "descanso": "desc"}
STATE_LONG = {"deck": "No deck", "livre": "Disponível", "filhote": "Filhote",
              "descanso": "Em descanso"}
Persist = Callable[[], "str | None"]     # grava o save; devolve texto de erro ou None


@dataclass
class CatRow:
    cat: Cat
    stats: Stats
    state: str            # deck | livre | filhote | descanso
    label: str            # nome do gato ou, sem nome, o nome da raca
    breed: str


class CollectionController:
    def __init__(self, content: Content, save: SaveData, persist: Persist | None = None) -> None:
        self.content = content
        self.save = save
        self.persist = persist
        self.deck_size: int = content.rules["duel"]["deck_size"]
        self.name_max: int = int((content.rules.get("meta") or {}).get("name_max_length", 16))
        ok = {c.id for c in available_cats(save)}
        self.picked: list[str] = []
        for cid in save.deck:
            if cid in ok and cid not in self.picked and len(self.picked) < self.deck_size:
                self.picked.append(cid)
        self.sort = "poder"
        self.filter_breed: str | None = None
        self.scroll = 0
        self.selected: str | None = save.cats[0].id if save.cats else None
        self.edit: str | None = None          # texto do campo de renomear (None = fechado)
        self.toast: Toast | None = None

    # ------------------------------------------------------------ consultas
    def say(self, text: str, kind: str = "error", ttl: float = 2.5) -> None:
        self.toast = Toast(text, kind, ttl)

    def breed_name(self, cat: Cat) -> str:
        return self.content.breeds.get(cat.breed, {}).get("nome", cat.breed)

    def nature_name(self, cat: Cat) -> str:
        return self.content.natures.get(cat.nature, {}).get("nome", cat.nature)

    def nature_effect(self, cat: Cat) -> str:
        n = self.content.natures.get(cat.nature, {})
        return f"ATK {n.get('atk', 0):+d}  HP {n.get('hp', 0):+d}"

    def keyword_names(self, cat: Cat) -> list[tuple[str, str]]:
        """[(id, nome)] das keywords da raca."""
        ids = self.content.breeds.get(cat.breed, {}).get("keywords", [])
        return [(k, self.content.keywords.get(k, {}).get("nome", k)) for k in ids]

    def state_of(self, cat: Cat) -> str:
        if cat.stage == "kitten":
            return "filhote"
        if cat.rest_runs_left > 0:
            return "descanso"
        return "deck" if cat.id in self.picked else "livre"

    def row_of(self, cat: Cat) -> CatRow:
        breed = self.breed_name(cat)
        return CatRow(cat, cat_stats(self.content, cat), self.state_of(cat), cat.name or breed, breed)

    def breeds_present(self) -> list[str]:
        present = {c.breed for c in self.save.cats}
        return [b for b in self.content.breeds if b in present]

    def filter_label(self) -> str:
        if self.filter_breed is None:
            return "Raça: todas"
        return f"Raça: {self.content.breeds.get(self.filter_breed, {}).get('nome', self.filter_breed)}"

    def rows(self) -> list[CatRow]:
        rows = [self.row_of(c) for c in self.save.cats
                if self.filter_breed is None or c.breed == self.filter_breed]
        if self.sort == "poder":
            rows.sort(key=lambda r: (-(r.stats.atk + r.stats.hp), r.cat.id))
        elif self.sort == "raca":
            rows.sort(key=lambda r: (r.breed, -(r.stats.atk + r.stats.hp), r.cat.id))
        else:
            rows.sort(key=lambda r: (r.label.lower(), r.cat.id))
        return rows

    def max_scroll(self) -> int:
        return max(0, len(self.rows()) - LH.ROWS_VISIBLE)

    def visible_rows(self) -> list[CatRow]:
        self.scroll = max(0, min(self.scroll, self.max_scroll()))
        return self.rows()[self.scroll:self.scroll + LH.ROWS_VISIBLE]

    def visible_ids(self) -> list[str]:
        return [r.cat.id for r in self.visible_rows()]

    def selected_cat(self) -> Cat | None:
        try:
            return get_cat(self.save, self.selected) if self.selected else None
        except IllegalAction:
            return None

    @property
    def deck_count(self) -> int:
        return len(self.picked)

    @property
    def deck_text(self) -> str:
        return f"Deck {self.deck_count}/{self.deck_size}"

    @property
    def can_start(self) -> bool:
        return self.deck_count == self.deck_size

    @property
    def editing(self) -> bool:
        return self.edit is not None

    def edit_counter(self) -> str:
        return f"{len(self.edit or '')}/{self.name_max}"

    def hint(self) -> str:
        if self.editing:
            return "Enter confirma, ESC cancela"
        if not self.can_start:
            return f"Escolha {self.deck_size - self.deck_count} gato(s) ou use COMPLETAR"
        return "Deck pronto: clique em INICIAR RUN"

    # ------------------------------------------------------------ entrada
    def hit(self, pos: tuple[int, int]) -> tuple | None:
        return LH.hit_test(pos, "colecao", rows=self.visible_ids(), rename=self.editing)

    def click(self, elem: tuple | None) -> str | None:
        """Trata o clique. Devolve "back" ou "start" quando o hub precisa agir."""
        if elem is None:
            return None
        kind = elem[0]
        try:
            if kind == "rename_ok":
                self.confirm_rename()
            elif kind == "rename_cancel":
                self.cancel_rename()
            elif self.editing:
                return None
            elif kind == "row":
                self.toggle(elem[1])
            elif kind == "scroll":
                self.scroll_by(elem[1])
            elif kind == "sort":
                self.sort = elem[1]
                self.scroll = 0
            elif kind == "filter":
                self.cycle_filter()
            elif kind == "rename":
                self.begin_rename()
            elif kind == "complete":
                self.complete()
            elif kind == "clear":
                self.clear()
            elif kind == "start":
                return "start" if self.can_start else self._not_ready()
            elif kind == "back":
                return "back"
        except IllegalAction as e:
            self.say(str(e))
        return None

    def _not_ready(self) -> None:
        self.say(f"O deck precisa de {self.deck_size} gatos ({self.deck_count}/{self.deck_size}).")
        return None

    # ------------------------------------------------------------ lista
    def scroll_by(self, n: int) -> None:
        self.scroll = max(0, min(self.scroll + n, self.max_scroll()))

    def cycle_filter(self) -> None:
        opts: list[str | None] = [None, *self.breeds_present()]
        i = opts.index(self.filter_breed) if self.filter_breed in opts else 0
        self.filter_breed = opts[(i + 1) % len(opts)]
        self.scroll = 0

    def select(self, cat_id: str) -> None:
        self.selected = cat_id

    # ------------------------------------------------------------ deck
    def toggle(self, cat_id: str) -> None:
        cat = get_cat(self.save, cat_id)
        self.selected = cat_id
        if cat.stage == "kitten":
            self.say("Filhote ainda não pode entrar no deck.")
        elif cat.rest_runs_left > 0:
            self.say("Gato em descanso, indisponível.")
        elif cat_id in self.picked:
            self.picked.remove(cat_id)
            self._store_deck()
        elif len(self.picked) >= self.deck_size:
            self.say(f"Deck cheio ({self.deck_size}/{self.deck_size}). Tire um gato antes.")
        else:
            self.picked.append(cat_id)
            self._store_deck()

    def complete(self) -> None:
        self.picked = autofill_deck(self.content, self.save, self.picked)
        self._store_deck()
        self.say("Deck completado com os melhores gatos.", "info")

    def clear(self) -> None:
        self.picked = []
        self._store_deck()

    def _store_deck(self) -> None:
        """Guarda o deck no save e grava. `set_deck` exige 12; rascunho menor vai direto
        (o contrato aceita `deck` com menos de 12 ids; so iniciar a run exige 12)."""
        if len(self.picked) == self.deck_size:
            set_deck(self.content, self.save, list(self.picked))
        else:
            self.save.deck = list(self.picked)
        self._persist()

    def _persist(self) -> None:
        if self.persist is not None:
            err = self.persist()
            if err:
                self.say(f"Não consegui salvar: {err}")

    def start_run(self, rng: Random) -> Run:
        """Valida o deck (set_deck) e cria a run com ele (new_run_from_save)."""
        set_deck(self.content, self.save, list(self.picked))
        self._persist()
        return new_run_from_save(self.content, self.save, rng)

    # ------------------------------------------------------------ renomear
    def begin_rename(self) -> None:
        cat = self.selected_cat()
        if cat is None:
            self.say("Selecione um gato primeiro.")
            return
        self.edit = cat.name or ""

    def type_text(self, text: str) -> None:
        if self.edit is None:
            return
        for ch in text:
            if ch.isprintable() and len(self.edit) < self.name_max:
                self.edit += ch

    def backspace(self) -> None:
        if self.edit:
            self.edit = self.edit[:-1]

    def confirm_rename(self) -> None:
        cat = self.selected_cat()
        if self.edit is None or cat is None:
            return
        try:
            rename_cat(self.save, cat.id, self.edit, self.content)
        except IllegalAction as e:
            self.say(str(e))
            return
        self.edit = None
        self._persist()

    def cancel_rename(self) -> None:
        self.edit = None

    # ------------------------------------------------------------ tempo
    def update(self, dt: float) -> None:
        if self.toast:
            self.toast.ttl -= dt
            if self.toast.ttl <= 0:
                self.toast = None
