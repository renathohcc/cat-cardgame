"""Geracao de gatos e calculo de status."""
from __future__ import annotations

from random import Random

from core.types import Cat, Content, Stage, Stats


def _iv_table(content: Content) -> tuple[list[int], list[int]]:
    weights = content.rules["iv_weights"]
    ivs = sorted(int(k) for k in weights)
    values = [weights[str(i)] for i in ivs]
    if any(w is None for w in values):
        raise ValueError("rules.iv_weights tem pesos null (pendentes); preencha data/rules.json")
    return ivs, values


def _roll_iv(rng: Random, ivs: list[int], weights: list[int]) -> int:
    return rng.choices(ivs, weights=weights, k=1)[0]


def roll_cat(content: Content, rng: Random, breed_id: str | None = None,
             stage: Stage = "adult", iv_weights: dict[int, int] | None = None) -> Cat:
    ivs, weights = _iv_table(content)
    if iv_weights is not None:
        ivs = sorted(iv_weights)
        weights = [iv_weights[i] for i in ivs]
    if breed_id is None:
        breed_id = rng.choice(list(content.breeds))
    elif breed_id not in content.breeds:
        raise ValueError(f"raca inexistente: '{breed_id}'")
    sex = rng.choice(("M", "F"))
    nature = rng.choice(list(content.natures))
    iv_atk = _roll_iv(rng, ivs, weights)
    iv_hp = _roll_iv(rng, ivs, weights)
    return Cat(id="", breed=breed_id, sex=sex, nature=nature,
               iv_atk=iv_atk, iv_hp=iv_hp, stage=stage)


def cat_stats(content: Content, cat: Cat) -> Stats:
    breed = content.breeds[cat.breed]
    nature = content.natures[cat.nature]
    rules = content.rules["stats"]
    floor = rules["min_stat"]
    atk = breed["atk_base"] + (cat.iv_atk - 1) // rules["atk_iv_divisor"] + nature["atk"]
    hp = breed["hp_base"] + (cat.iv_hp - 1) + nature["hp"]
    return Stats(cost=breed["custo"], atk=max(floor, atk), hp=max(floor, hp))
