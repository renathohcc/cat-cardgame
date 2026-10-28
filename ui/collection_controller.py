"""Controlador da tela de Colecao. Puro (sem pygame).

So chama a API publica do core (`available_cats`, `set_deck`, `autofill_deck`, `rename_cat`,
`new_run_from_save`, `cat_stats`); nenhuma regra mora aqui. `IllegalAction` vira aviso.

Elementos clicaveis (`elem`):
    ("row", cat_id)  ("scroll", +-1)  ("sort", chave)  ("filter",)  ("rename",)
    ("complete",)  ("clear",)  ("start",)  ("back",)  ("breed",)  ("rename_ok",)  ("rename_cancel",)
"""
from __future__ import annotations

from dataclasses import dataclass
from random import Random
from typing import Callable

from core import (SaveData, autofill_deck, available_cats, can_donate, cat_stats,
                  donate_cat,
                  donation_value, get_cat, new_run_from_save, rename_cat, save_deck_draft,
                  set_deck)
from core import Cat, Content, Run, Stats, breed_cfg
from core.types import IllegalAction
from ui import layout_hub as LH
from ui.controller import Toast

SORT_LABEL = {"poder": "PODER", "raca": "RAÇA", "nome": "NOME"}
STATE_LABEL = {"deck": "deck", "livre": "livre", "filhote": "filh", "descanso": "desc",
               "breed": "brd"}
STATE_LONG = {"deck": "No deck", "livre": "Disponível", "filhote": "Filhote",
              "descanso": "Em descanso", "breed": "Em breed"}
Persist = Callable[[], "str | None"]     # grava o save; devolve texto de erro ou None


@dataclass
class CatRow:
    cat: Cat
    stats: Stats
    state: str            # deck | livre | filhote | descanso | breed
    label: str            # nome do gato ou, sem nome, o nome da raca
    breed: str
    runs_left: int = 0    # breed: runs ate a ninhada; filhote: runs ate virar adulto


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
        self.confirm_donate = False           # dialogo "Doar <nome> por N moedas?" aberto

    # ------------------------------------------------------------ consultas
    @property
    def coins(self) -> int:
        return self.save.coins

    def donate_value(self, cat: Cat) -> int:
        return donation_value(self.content, cat)

    def donate_question(self) -> str:
        cat = self.selected_cat()
        if cat is None:
            return ""
        return f"Doar {cat.name or self.breed_name(cat)} por {self.donate_value(cat)} moedas?"
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

    def runs_left_of(self, cat: Cat) -> int:
        """Runs que faltam: ate a ninhada (casal em breed) ou ate virar adulto (filhote)."""
        if cat.stage == "kitten":
            return max(0, breed_cfg(self.content)["growth_runs"] - cat.runs_as_kitten)
        for b in self.save.breeding:
            if cat.id in (b["male"], b["female"]):
                return b["runs_left"]
        return 0

    def in_breed(self, cat: Cat) -> bool:
        return any(cat.id in (b["male"], b["female"]) for b in self.save.breeding)

    def state_of(self, cat: Cat) -> str:
        if cat.stage == "kitten":
            return "filhote"
        if self.in_breed(cat):
            return "breed"
        if cat.rest_runs_left > 0:
            return "descanso"
        return "deck" if cat.id in self.picked else "livre"

    def row_of(self, cat: Cat) -> CatRow:
        breed = self.breed_name(cat)
        state = self.state_of(cat)
        left = self.runs_left_of(cat) if state in ("breed", "filhote") else 0
        return CatRow(cat, cat_stats(self.content, cat), state, cat.name or breed, breed, left)

    def state_text(self, row: CatRow) -> str:
        """Texto curto da coluna de estado: "brd2" / "filh2" (com as runs que faltam)."""
        base = STATE_LABEL[row.state]
        return f"{base}{row.runs_left}" if row.state in ("breed", "filhote") else base

    def state_long_text(self, row: CatRow) -> str:
        n = row.runs_left
        if row.state == "breed":
            return f"Em breed: falta{'m' if n != 1 else ''} {n} run{'s' if n != 1 else ''}"
        if row.state == "filhote":
            return f"Filhote: falta{'m' if n != 1 else ''} {n} run{'s' if n != 1 else ''}"
        return STATE_LONG[row.state]

    def refresh_deck(self) -> None:
        """Depois de mexer no Criatorio: tira do rascunho os gatos que ficaram indisponiveis."""
        ok = {c.id for c in available_cats(self.save)}
        self.picked = [i for i in self.picked if i in ok]

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
        return LH.hit_test(pos, "colecao", rows=self.visible_ids(), rename=self.editing,
                           donate=self.confirm_donate)

    def click(self, elem: tuple | None) -> str | None:
        """Trata o clique. Devolve "back" ou "start" quando o hub precisa agir."""
        if elem is None:
            return None
        kind = elem[0]
        try:
            if self.confirm_donate:
                if kind == "donate_yes":
                    self.do_donate()
                elif kind == "donate_no":
                    self.confirm_donate = False
                return None
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
            elif kind == "donate":
                if self.selected_cat() is None:
                    self.say("Selecione um gato primeiro.")
                else:
                    ok, motivo = can_donate(self.content, self.save, self.selected_cat().id)
                    if ok:
                        self.confirm_donate = True
                    else:
                        self.say(motivo)
            elif kind == "complete":
                self.complete()
            elif kind == "clear":
                self.clear()
            elif kind == "start":
                return "start" if self.can_start else self._not_ready()
            elif kind == "back":
                return "back"
            elif kind == "breed":
                return "breed"
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
            n = self.runs_left_of(cat)
            self.say(f"Filhote não entra no deck: falta{'m' if n != 1 else ''} {n} run{'s' if n != 1 else ''}.")
        elif self.in_breed(cat):
            self.say(f"Gato em breed, indisponível (faltam {self.runs_left_of(cat)} runs).")
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
            save_deck_draft(self.save, list(self.picked), self.content)
        self._persist()

    def do_donate(self) -> None:
        """Doa o gato selecionado (`donate_cat`); a regra dos 12 adultos e do core."""
        self.confirm_donate = False
        cat = self.selected_cat()
        if cat is None:
            return
        name = cat.name or self.breed_name(cat)
        ok, motivo = can_donate(self.content, self.save, cat.id)
        if not ok:
            self.say(motivo)
            return
        try:
            coins = donate_cat(self.content, self.save, cat.id)
        except IllegalAction as e:
            self.say(str(e))
            return
        if cat.id in self.picked:
            self.picked.remove(cat.id)
        rows = self.rows()
        self.selected = rows[0].cat.id if rows else None
        self.say(f"{name} doado: +{coins} moedas.", "info")
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
