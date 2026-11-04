"""Racoes de breed (data/shop.json): efeitos puros, sem sorteio.

Uma racao por casal, gravada em `save.breeding[i]["ration"]`. A Racao Escolha
precisa da escolha do jogador (IV e pai); como o schema do casal so tem o campo
`ration` (id real de shop.json), a escolha vai em `breeding[i].ration_choice`
(`null` ou `{"stat", "parent"}`)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.shop import ration_def
from core.types import Content, IllegalAction

__all__ = ["IvChoice", "check_choice", "choice_to_dict", "choice_from_dict", "ration_effect", "needs_choice",
           "breed_runs_for", "mutation_for"]

_STATS = {"atk": "atk", "hp": "hp"}
_PARENTS = {"pai": "father", "mae": "mother"}
_PARENT_TOKEN = {v: k for k, v in _PARENTS.items()}


@dataclass(frozen=True)
class IvChoice:
    """IV fixado pela Racao Escolha: `stat` 'atk'|'hp', `parent` 'father'|'mother'."""
    stat: str
    parent: str

    def __post_init__(self) -> None:
        if self.stat not in _STATS or self.parent not in _PARENT_TOKEN:
            raise IllegalAction("Escolha inválida: use stat 'atk'/'hp' e pai 'father'/'mother'.")


def ration_effect(content: Content, ration_id: str) -> dict[str, Any]:
    return ration_def(content, ration_id)["effect"]


def needs_choice(content: Content, ration_id: str | None) -> bool:
    return ration_id is not None and ration_effect(content, ration_id)["type"] == "fix_one_iv"


def check_choice(content: Content, ration_id: str | None, choice: IvChoice | None) -> None:
    """A escolha e obrigatoria na Racao Escolha e proibida nas outras."""
    if ration_id is not None:
        ration_def(content, ration_id)    # existe?
    if needs_choice(content, ration_id) and choice is None:
        raise IllegalAction("A Ração Escolha precisa do IV e do pai escolhidos.")
    if choice is not None and not needs_choice(content, ration_id):
        raise IllegalAction("Só a Ração Escolha aceita escolha de IV.")


def choice_to_dict(choice: IvChoice | None) -> dict[str, str] | None:
    """Forma gravada em `breeding[i].ration_choice`."""
    return None if choice is None else {"stat": choice.stat, "parent": choice.parent}


def choice_from_dict(value: dict[str, str] | None) -> IvChoice | None:
    return None if value is None else IvChoice(value["stat"], value["parent"])


def breed_runs_for(content: Content, base_runs: int, ration_id: str | None) -> int:
    """Runs do breed com a racao (Veloz reduz, com minimo `min_runs`)."""
    if ration_id is None:
        return base_runs
    eff = ration_effect(content, ration_id)
    if eff["type"] != "breed_runs_reduction":
        return base_runs
    floor = int(eff.get("min_runs", 1))
    return max(min(base_runs, floor), base_runs - int(eff["value"]))


def mutation_for(content: Content, base: float, ration_id: str | None) -> float:
    """Chance de mutacao da ninhada (Fofa troca o valor base)."""
    if ration_id is None:
        return base
    eff = ration_effect(content, ration_id)
    return float(eff["value"]) if eff["type"] == "mutation_chance" else base
