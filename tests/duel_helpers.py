"""Auxiliares dos testes de duelo (so API publica do core)."""
from __future__ import annotations

from pathlib import Path
from random import Random

from core import load_content, roll_cat
from core.duel import build_duel_for_tests
from core.types import Card, DeckSpec, FieldCat

DATA = Path(__file__).resolve().parent.parent / "data"

_counter = 0


def load():
    return load_content(DATA)


def mk(atk: int, hp: int, cost: int = 1, kw: tuple[str, ...] = (), name: str | None = None) -> Card:
    """Carta de gato com status exatos (sem IV nem natureza)."""
    global _counter
    _counter += 1
    n = name or f"gato-{_counter}"
    return Card(kind="cat", ref=n, name=n, cost=cost, atk=atk, hp=hp, keywords=tuple(kw))


def fc(atk: int, hp: int, hp_max: int | None = None, kw: tuple[str, ...] = (),
       ready: bool = True) -> FieldCat:
    c = mk(atk, hp_max or hp, kw=kw)
    return FieldCat(card=c, atk=atk, hp=hp, hp_max=hp_max or hp, keywords=tuple(kw), ready=ready)


def duel(content, **kw):
    return build_duel_for_tests(content, Random(kw.pop("seed", 1)), **kw)


def deck_spec(content, seed: int, n: int = 12) -> DeckSpec:
    rng = Random(seed)
    return DeckSpec(cats=[roll_cat(content, rng) for _ in range(n)])
