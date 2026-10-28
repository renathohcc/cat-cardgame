"""Controladores do Criatorio e das Novidades do Criatorio. Puros (sem pygame).

So chamam a API publica do core (`can_breed`, `start_breed`, `cancel_breed`, `breeding_status`,
`available_cats`, `cat_stats`). Nenhuma regra mora aqui: o que a UI mostra de "regra" (percentual
da raca, tamanho da ninhada, tempo) vem de `rules.breed` via `breed_cfg`.

Elementos clicaveis do Criatorio:
    ("row", "M"|"F", id)  ("scroll", "M"|"F", +-1)  ("cancel", male_id, female_id)
    ("start",)  ("back",)
Novidades: ("news_continue",)
"""
from __future__ import annotations

from dataclasses import dataclass
from types import SimpleNamespace
from typing import Callable

from core import (RunAftermath, SaveData, available_cats, breeding_status, cancel_breed,
                  can_breed, cat_stats, get_cat, start_breed)
from core import Cat, Content, Stats, breed_cfg
from core.types import IllegalAction
from ui import layout_breed as LB
from ui.controller import Toast

Persist = Callable[[], "str | None"]


@dataclass
class BreedRow:
    cat: Cat
    stats: Stats
    label: str
    breed: str


@dataclass
class CoupleRow:
    male: Cat
    female: Cat
    runs_left: int
    can_cancel: bool
    why_not: str


def _names(content: Content, cat: Cat) -> tuple[str, str]:
    breed = content.breeds.get(cat.breed, {}).get("nome", cat.breed)
    return cat.name or breed, breed


class _Base:
    def __init__(self, content: Content, save: SaveData) -> None:
        self.content = content
        self.save = save
        self.toast: Toast | None = None
        self.high_sum = int((content.rules.get("adoption") or {}).get("high_iv_sum", 8))

    def say(self, text: str, kind: str = "error", ttl: float = 2.5) -> None:
        self.toast = Toast(text, kind, ttl)

    def breed_name(self, cat: Cat) -> str:
        return self.content.breeds.get(cat.breed, {}).get("nome", cat.breed)

    def nature_name(self, cat: Cat) -> str:
        return self.content.natures.get(cat.nature, {}).get("nome", cat.nature)

    def label(self, cat: Cat | None) -> str:
        return _names(self.content, cat)[0] if cat else ""

    def tier(self, cat: Cat) -> str:
        """"perfeito" (IV 5/5), "alto" (soma >= limite) ou ""."""
        if cat.iv_atk == 5 and cat.iv_hp == 5:
            return "perfeito"
        return "alto" if cat.iv_atk + cat.iv_hp >= self.high_sum else ""

    def update(self, dt: float) -> None:
        if self.toast:
            self.toast.ttl -= dt
            if self.toast.ttl <= 0:
                self.toast = None


class BreedController(_Base):
    def __init__(self, content: Content, save: SaveData, persist: Persist | None = None) -> None:
        super().__init__(content, save)
        self.persist = persist
        self.cfg = breed_cfg(content)
        self.sel: dict[str, str | None] = {"M": None, "F": None}
        self.scroll: dict[str, int] = {"M": 0, "F": 0}

    # ------------------------------------------------------------ consultas
    def rows(self, side: str) -> list[BreedRow]:
        out = []
        for c in available_cats(self.save):
            if c.sex == side:
                label, breed = _names(self.content, c)
                out.append(BreedRow(c, cat_stats(self.content, c), label, breed))
        out.sort(key=lambda r: (-(r.stats.atk + r.stats.hp), r.cat.id))
        return out

    def max_scroll(self, side: str) -> int:
        return max(0, len(self.rows(side)) - LB.ROWS)

    def visible_rows(self, side: str) -> list[BreedRow]:
        self.scroll[side] = max(0, min(self.scroll[side], self.max_scroll(side)))
        a = self.scroll[side]
        return self.rows(side)[a:a + LB.ROWS]

    def visible_ids(self, side: str) -> list[str]:
        return [r.cat.id for r in self.visible_rows(side)]

    def free_adults(self) -> int:
        return len(available_cats(self.save))

    def selected(self, side: str) -> Cat | None:
        cid = self.sel[side]
        if cid is None:
            return None
        try:
            cat = get_cat(self.save, cid)
        except IllegalAction:
            self.sel[side] = None
            return None
        if cat.id not in {c.id for c in available_cats(self.save)}:
            self.sel[side] = None
            return None
        return cat

    def pair(self) -> tuple[Cat, Cat] | None:
        m, f = self.selected("M"), self.selected("F")
        return (m, f) if m and f else None

    def verdict(self) -> tuple[bool, str]:
        """(pode iniciar, texto). Sem casal escolhido: texto-guia; recusado: `motivo` do core."""
        p = self.pair()
        if p is None:
            return False, "Escolha um macho e uma fêmea."
        return can_breed(self.content, self.save, p[0].id, p[1].id)

    @property
    def can_start(self) -> bool:
        return self.verdict()[0]

    def breed_odds(self) -> list[tuple[int, str]]:
        """[(percentual, raca)] do filhote; 100% se mae e pai tem a mesma raca."""
        p = self.pair()
        if p is None:
            return []
        m_name, f_name = self.breed_name(p[0]), self.breed_name(p[1])
        pct = round(self.cfg["mother_breed_chance"] * 100)
        if p[0].breed == p[1].breed:
            return [(100, f_name)]
        return [(pct, f_name), (100 - pct, m_name)]

    def litter_text(self) -> str:
        lo, hi = self.cfg["litter_min"], self.cfg["litter_max"]
        return f"Ninhada: {lo}" if lo == hi else f"Ninhada: {lo} a {hi}"

    def time_text(self) -> str:
        n = self.cfg["base_runs"]
        return f"Tempo: {n} run{'s' if n != 1 else ''}"

    def couples(self) -> list[CoupleRow]:
        out = []
        for b in breeding_status(self.save):
            ok, why = self._cancel_check(b["male"].id, b["female"].id)
            out.append(CoupleRow(b["male"], b["female"], b["runs_left"], ok, why))
        return out

    def _cancel_check(self, male_id: str, female_id: str) -> tuple[bool, str]:
        """Pergunta ao core (em copia so do breeding) se o cancelamento e permitido."""
        stub = SimpleNamespace(breeding=[dict(b) for b in self.save.breeding])
        try:
            cancel_breed(self.content, stub, male_id, female_id)      # type: ignore[arg-type]
        except IllegalAction as e:
            return False, str(e)
        return True, ""

    def cancel_pairs(self) -> list[tuple[str, str]]:
        return [(c.male.id, c.female.id) for c in self.couples()[:LB.COUPLES_VISIBLE]]

    def kittens(self) -> list[tuple[Cat, int]]:
        """[(filhote, runs que faltam para virar adulto)]."""
        g = self.cfg["growth_runs"]
        return [(c, max(0, g - c.runs_as_kitten)) for c in self.save.cats if c.stage == "kitten"]

    # ------------------------------------------------------------ entrada
    def hit(self, pos: tuple[int, int]) -> tuple | None:
        return LB.breed_hit(pos, self.visible_ids("M"), self.visible_ids("F"), self.cancel_pairs())

    def click(self, elem: tuple | None) -> str | None:
        """Devolve "back" quando a tela deve fechar."""
        if elem is None:
            return None
        kind = elem[0]
        if kind == "row":
            side, cid = elem[1], elem[2]
            self.sel[side] = None if self.sel[side] == cid else cid
        elif kind == "scroll":
            self.scroll_by(elem[1], elem[2])
        elif kind == "start":
            self.start()
        elif kind == "cancel":
            self.cancel(elem[1], elem[2])
        elif kind == "back":
            return "back"
        return None

    def scroll_by(self, side: str, n: int) -> None:
        self.scroll[side] = max(0, min(self.scroll[side] + n, self.max_scroll(side)))

    def start(self) -> None:
        ok, motivo = self.verdict()
        if not ok:
            self.say(motivo)
            return
        m, f = self.pair()
        try:
            start_breed(self.content, self.save, m.id, f.id)
        except IllegalAction as e:
            self.say(str(e))
            return
        self.sel = {"M": None, "F": None}
        self.say(f"Breed iniciado: {self.cfg['base_runs']} runs até a ninhada.", "info")
        self._persist()

    def cancel(self, male_id: str, female_id: str) -> None:
        try:
            cancel_breed(self.content, self.save, male_id, female_id)
        except IllegalAction as e:
            self.say(str(e))
            return
        self.say("Breed cancelado.", "info")
        self._persist()

    def _persist(self) -> None:
        if self.persist is not None:
            err = self.persist()
            if err:
                self.say(f"Não consegui salvar: {err}")


class NewsController(_Base):
    """Tela "Novidades do Criatorio": o que o fim da run trouxe (nascidos e adultos novos)."""

    def __init__(self, content: Content, save: SaveData, aftermath: RunAftermath) -> None:
        super().__init__(content, save)
        self.born = list(aftermath.born)
        self.grown = list(aftermath.grown)
        self.couples_done = list(aftermath.couples_done)

    @property
    def empty(self) -> bool:
        return not self.born and not self.grown

    def born_title(self) -> str:
        n = len(self.born)
        return f"Nasceu {n} filhote" if n == 1 else f"Nasceram {n} filhotes"

    def grown_title(self) -> str:
        n = len(self.grown)
        return f"{n} filhote virou adulto" if n == 1 else f"{n} filhotes viraram adultos"

    def grown_labels(self) -> list[str]:
        return [f"{self.label(c)} ({self.nature_name(c)})" for c in self.grown]

    def couple_labels(self) -> list[str]:
        out = []
        for mid, fid in self.couples_done:
            try:
                out.append(f"{self.label(get_cat(self.save, mid))} e {self.label(get_cat(self.save, fid))}")
            except IllegalAction:
                continue
        return out

    def hit(self, pos: tuple[int, int]) -> tuple | None:
        return LB.news_hit(pos)

    def click(self, elem: tuple | None) -> str | None:
        return "done" if elem == ("news_continue",) else None
