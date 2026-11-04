"""Previa de odds do breed: probabilidades exatas, sem sorteio (puro).

Espelha `core.breeding._birth`: raca 60/40, cada IV 50/50 entre os pais com
mutacao +1 (teto `iv_max`), ninhada uniforme, sexo e natureza uniformes."""
from __future__ import annotations

from dataclasses import dataclass, field

from core.breeding import breed_cfg, initial_runs
from core.collection import get_cat
from core.rations import IvChoice, check_choice, mutation_for
from core.save import SaveData
from core.types import Cat, Content, IllegalAction

__all__ = ["BreedOdds", "breed_odds", "iv_distribution"]


@dataclass(frozen=True)
class BreedOdds:
    breed: dict[str, float]              # raca do filhote
    iv_atk: dict[int, float]
    iv_hp: dict[int, float]
    sex: dict[str, float]
    nature: dict[str, float]
    litter: dict[int, float]             # tamanho da ninhada -> probabilidade
    litter_min: int
    litter_max: int
    litter_expected: float
    mutation: float                      # chance de mutacao por IV (com a racao)
    runs: int                            # duracao do breed com a racao
    runs_without_ration: int
    runs_left: int                       # restantes (igual a `runs` se o casal ainda nao abriu)
    ration: str | None = None
    choice: IvChoice | None = None
    fixed: dict[str, int | None] = field(default_factory=dict)   # {"atk": 3|None, "hp": ...}


def iv_distribution(father_iv: int, mother_iv: int, mutation: float, cap: int = 5,
                    fixed: int | None = None) -> dict[int, float]:
    """P(IV do filhote = v). `fixed` (Racao Escolha) vale 100% e sem mutacao."""
    if fixed is not None:
        return {fixed: 1.0}
    out: dict[int, float] = {}
    for base in (father_iv, mother_iv):
        for value, p in ((base, 1.0 - mutation), (min(cap, base + 1), mutation)):
            out[value] = out.get(value, 0.0) + 0.5 * p
    return {k: out[k] for k in sorted(out) if out[k] > 0.0}


def _breed_odds(father: Cat, mother: Cat, p_mother: float) -> dict[str, float]:
    out: dict[str, float] = {}
    out[mother.breed] = out.get(mother.breed, 0.0) + p_mother
    out[father.breed] = out.get(father.breed, 0.0) + (1.0 - p_mother)
    return out


def _pair(save: SaveData, father_id: str, mother_id: str) -> tuple[Cat, Cat]:
    father, mother = get_cat(save, father_id), get_cat(save, mother_id)
    if father.sex != "M" or mother.sex != "F":
        raise IllegalAction("O casal precisa de um macho e uma fêmea.")
    return father, mother


def breed_odds(content: Content, save: SaveData, father_id: str, mother_id: str,
               ration: str | None = None, choice: IvChoice | None = None) -> BreedOdds:
    father, mother = _pair(save, father_id, mother_id)
    check_choice(content, ration, choice)
    cfg = breed_cfg(content)
    mutation = mutation_for(content, cfg["mutation_chance"], ration)
    fixed: dict[str, int | None] = {"atk": None, "hp": None}
    if choice is not None:
        src = father if choice.parent == "father" else mother
        fixed[choice.stat] = src.iv_atk if choice.stat == "atk" else src.iv_hp
    lo, hi = cfg["litter_min"], cfg["litter_max"]
    litter = {n: 1.0 / (hi - lo + 1) for n in range(lo, hi + 1)}
    runs = initial_runs(content, ration)
    return BreedOdds(
        breed=_breed_odds(father, mother, cfg["mother_breed_chance"]),
        iv_atk=iv_distribution(father.iv_atk, mother.iv_atk, mutation, cfg["iv_max"],
                               fixed["atk"]),
        iv_hp=iv_distribution(father.iv_hp, mother.iv_hp, mutation, cfg["iv_max"],
                              fixed["hp"]),
        sex={"M": 0.5, "F": 0.5},
        nature={n: 1.0 / len(content.natures) for n in content.natures},
        litter=litter, litter_min=lo, litter_max=hi,
        litter_expected=sum(n * p for n, p in litter.items()),
        mutation=mutation, runs=runs, runs_without_ration=initial_runs(content, None),
        runs_left=_runs_left(content, save, father_id, mother_id, runs),
        ration=ration, choice=choice, fixed=fixed)


def _runs_left(content: Content, save: SaveData, father_id: str, mother_id: str,
               default: int) -> int:
    for b in save.breeding:
        if b["male"] == father_id and b["female"] == mother_id:
            return int(b["runs_left"])
    return default
