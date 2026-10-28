"""Breed e filhotes (Fase 5c). Sem Criatorio visual, racao ou racas hibridas."""
from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import Any

from core.collection import available_cats, get_cat
from core.save import SaveData, format_cat_id, register_dex
from core.types import Cat, Content, IllegalAction

__all__ = ["RunAftermath", "can_breed", "start_breed", "advance_after_run",
           "breeding_status", "cancel_breed", "breed_cfg"]


@dataclass
class RunAftermath:
    born: list[Cat] = field(default_factory=list)
    grown: list[Cat] = field(default_factory=list)
    couples_done: list[tuple[str, str]] = field(default_factory=list)  # (male_id, female_id)


def breed_cfg(content: Content) -> dict[str, Any]:
    cfg = content.rules.get("breed", {}) or {}
    return {
        "mutation_chance": _num(cfg.get("mutation_chance"), 0.07),
        "base_runs": int(_num(cfg.get("base_runs"), 2)),
        "growth_runs": int(_num(cfg.get("growth_runs"), 2)),
        "litter_min": int(_num(cfg.get("litter_min"), 1)),
        "litter_max": int(_num(cfg.get("litter_max"), 3)),
        "mother_breed_chance": _num(cfg.get("mother_breed_chance"), 0.6),
        "min_nodes_for_run_count": int(_num(cfg.get("min_nodes_for_run_count"), 1)),
        "min_adults_after_breed": int(_num(cfg.get("min_adults_after_breed"), 12)),
    }


def _num(v: Any, default: float) -> float:
    return default if v is None else v


def _in_breeding(save: SaveData, cat_id: str) -> bool:
    return any(cat_id in (b["male"], b["female"]) for b in save.breeding)


def can_breed(content: Content, save: SaveData, male_id: str,
              female_id: str) -> tuple[bool, str]:
    """(ok, motivo em portugues). Motivo vazio quando ok."""
    if male_id == female_id:
        return False, "Um gato não pode formar casal com ele mesmo."
    by_id = {c.id: c for c in save.cats}
    male, female = by_id.get(male_id), by_id.get(female_id)
    if male is None or female is None:
        return False, "Gato inexistente."
    if male.sex != "M" or female.sex != "F":
        return False, "O casal precisa de um macho e uma fêmea."
    for c in (male, female):
        if c.stage != "adult":
            return False, "Filhotes não podem fazer breed."
        if _in_breeding(save, c.id):
            return False, "Gato já está em um casal."
        if c.rest_runs_left != 0:
            return False, "Gato em descanso."
    need = breed_cfg(content)["min_adults_after_breed"]
    if len(available_cats(save)) - 2 < need:
        return False, f"Precisa manter {need} adultos disponíveis."
    return True, ""


def start_breed(content: Content, save: SaveData, male_id: str, female_id: str) -> None:
    ok, reason = can_breed(content, save, male_id, female_id)
    if not ok:
        raise IllegalAction(reason)
    save.breeding.append({"male": male_id, "female": female_id,
                          "runs_left": breed_cfg(content)["base_runs"]})
    save.deck = [i for i in save.deck if i not in (male_id, female_id)]


def cancel_breed(content: Content, save: SaveData, male_id: str, female_id: str) -> None:
    """Cancela sem custo, so se ainda nao passou nenhuma run. Pais nao voltam ao deck."""
    base = breed_cfg(content)["base_runs"]
    for i, b in enumerate(save.breeding):
        if b["male"] == male_id and b["female"] == female_id:
            if b["runs_left"] != base:
                raise IllegalAction("Breed já em andamento, não dá para cancelar.")
            save.breeding.pop(i)
            return
    raise IllegalAction("Casal não encontrado.")


def breeding_status(save: SaveData) -> list[dict[str, Any]]:
    """Para a UI: [{"male": Cat, "female": Cat, "runs_left": int}]."""
    return [{"male": get_cat(save, b["male"]), "female": get_cat(save, b["female"]),
             "runs_left": b["runs_left"]} for b in save.breeding]


def _kitten_iv(rng: Random, father_iv: int, mother_iv: int, mutation: float) -> int:
    iv = father_iv if rng.random() < 0.5 else mother_iv
    if rng.random() < mutation:
        iv = min(5, iv + 1)
    return iv


def _birth(content: Content, save: SaveData, rng: Random, male: Cat, female: Cat,
           cfg: dict[str, Any]) -> list[Cat]:
    n = rng.randint(cfg["litter_min"], cfg["litter_max"])
    kittens: list[Cat] = []
    for _ in range(n):
        breed = female.breed if rng.random() < cfg["mother_breed_chance"] else male.breed
        sex = rng.choice(("M", "F"))
        nature = rng.choice(list(content.natures))
        iv_atk = _kitten_iv(rng, male.iv_atk, female.iv_atk, cfg["mutation_chance"])
        iv_hp = _kitten_iv(rng, male.iv_hp, female.iv_hp, cfg["mutation_chance"])
        cat = Cat(id=format_cat_id(save.next_cat_id), breed=breed, sex=sex,
                  nature=nature, iv_atk=iv_atk, iv_hp=iv_hp, stage="kitten",
                  rest_runs_left=0, runs_as_kitten=0)
        save.next_cat_id += 1
        save.cats.append(cat)
        register_dex(save, cat)
        kittens.append(cat)
    return kittens


def advance_after_run(content: Content, save: SaveData, rng: Random,
                      nodes_cleared: int) -> RunAftermath:
    """Avanca breeds e crescimento uma vez por run concluida (nos vencidos >=
    min_nodes_for_run_count). Chame ANTES de create_adoption e grave uma vez so."""
    out = RunAftermath()
    cfg = breed_cfg(content)
    if nodes_cleared < cfg["min_nodes_for_run_count"]:
        return out
    for c in save.cats:  # filhotes ja existentes (os recem-nascidos ficam de fora)
        if c.stage == "kitten":
            c.runs_as_kitten += 1
            if c.runs_as_kitten >= cfg["growth_runs"]:
                c.stage = "adult"
                out.grown.append(c)
    remaining: list[dict[str, Any]] = []
    for b in save.breeding:
        b["runs_left"] = max(0, b["runs_left"] - 1)
        if b["runs_left"] > 0:
            remaining.append(b)
            continue
        out.born += _birth(content, save, rng, get_cat(save, b["male"]),
                           get_cat(save, b["female"]), cfg)
        out.couples_done.append((b["male"], b["female"]))
    save.breeding = remaining
    return out
