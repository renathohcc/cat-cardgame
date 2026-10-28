"""Colecao e deck: renomear, disponiveis, montar/completar o deck da run."""
from __future__ import annotations

from core.cats import cat_stats
from core.save import SaveData, name_max_length
from core.types import Cat, Content, IllegalAction

__all__ = ["rename_cat", "available_cats", "set_deck", "autofill_deck",
           "cat_stats", "get_cat", "deck_cats", "save_deck_draft"]


def get_cat(save: SaveData, cat_id: str) -> Cat:
    for c in save.cats:
        if c.id == cat_id:
            return c
    raise IllegalAction(f"gato inexistente: {cat_id!r}")


def rename_cat(save: SaveData, cat_id: str, name: str | None,
               content: Content | None = None, max_length: int | None = None) -> None:
    """Nome ate `name_max_length` (16) apos strip; vazio/None remove o nome.
    Passe `content` (ou `max_length`) para usar o limite de data/rules.json."""
    cat = get_cat(save, cat_id)
    if max_length is None:
        max_length = name_max_length(content) if content is not None else 16
    if name is None:
        cat.name = None
        return
    if not isinstance(name, str):
        raise IllegalAction("rename_cat: nome deve ser texto")
    name = name.strip()
    if len(name) > max_length:
        raise IllegalAction(f"rename_cat: nome com mais de {max_length} caracteres")
    cat.name = name or None


def _is_available(cat: Cat) -> bool:
    return cat.rest_runs_left == 0 and cat.stage == "adult"


def available_cats(save: SaveData) -> list[Cat]:
    """Adultos fora de descanso e fora de breed, na ordem da colecao."""
    busy = {i for b in save.breeding for i in (b["male"], b["female"])}
    return [c for c in save.cats if _is_available(c) and c.id not in busy]


def _check_ids(save: SaveData, ids: list[str]) -> None:
    if len(set(ids)) != len(ids):
        raise IllegalAction("deck com gatos repetidos")
    ok = {c.id for c in available_cats(save)}
    for cid in ids:
        get_cat(save, cid)
        if cid not in ok:
            raise IllegalAction(f"gato '{cid}' indisponivel (filhote ou em descanso)")


def set_deck(content: Content, save: SaveData, cat_ids: list[str]) -> None:
    size = content.rules["duel"]["deck_size"]
    ids = list(cat_ids)
    if len(ids) != size:
        raise IllegalAction(f"o deck precisa de exatamente {size} gatos (veio {len(ids)})")
    _check_ids(save, ids)
    save.deck = ids


def save_deck_draft(save: SaveData, cat_ids: list[str],
                    content: Content | None = None) -> None:
    """Rascunho: grava 0 a deck_size ids validos (distintos, disponiveis), sem exigir 12."""
    ids = list(cat_ids)
    size = content.rules["duel"]["deck_size"] if content is not None else 12
    if len(ids) > size:
        raise IllegalAction(f"o deck nao pode ter mais de {size} gatos")
    _check_ids(save, ids)
    save.deck = ids


def autofill_deck(content: Content, save: SaveData, picked: list[str]) -> list[str]:
    """Mantem `picked` e completa ate deck_size com os melhores restantes
    (maior ATK+HP finais, desempate por id). Nao altera o save."""
    size = content.rules["duel"]["deck_size"]
    ids = list(picked)
    if len(ids) > size:
        raise IllegalAction(f"mais de {size} gatos escolhidos")
    _check_ids(save, ids)
    rest = []
    for c in available_cats(save):
        if c.id not in ids:
            s = cat_stats(content, c)
            rest.append((-(s.atk + s.hp), c.id))
    rest.sort()
    need = size - len(ids)
    if len(rest) < need:
        raise IllegalAction(f"gatos disponiveis insuficientes para o deck de {size}")
    return ids + [cid for _, cid in rest[:need]]


def deck_cats(save: SaveData) -> list[Cat]:
    """Gatos do deck, na ordem de `save.deck`."""
    return [get_cat(save, cid) for cid in save.deck]
