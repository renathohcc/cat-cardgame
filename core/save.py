"""Save local (CONTRATOS 1.9): dados da colecao e progresso. Sem run em andamento."""
from __future__ import annotations

import copy
import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from random import Random
from typing import Any

from core.cats import roll_cat
from core.types import Cat, Content

__all__ = ["SaveData", "new_game", "save_to_dict", "save_from_dict",
           "write_save", "read_save", "meta_cfg", "start_cats", "name_max_length"]

SCHEMA_VERSION = 1
_ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_KEYS = ("schema_version", "cats", "deck", "coins", "next_cat_id", "breeding",
         "pity", "progress", "dex", "items", "settings")
_CAT_REQUIRED = ("id", "breed", "sex", "nature", "iv_atk", "iv_hp", "stage",
                 "rest_runs_left", "runs_as_kitten")
_CAT_KEYS = _CAT_REQUIRED + ("name",)


@dataclass
class SaveData:
    cats: list[Cat] = field(default_factory=list)
    deck: list[str] = field(default_factory=list)
    coins: int = 0
    next_cat_id: int = 1
    breeding: list[dict[str, Any]] = field(default_factory=list)
    pity: dict[str, Any] = field(default_factory=lambda: {"runs_without_high_iv": 0})
    progress: dict[str, Any] = field(default_factory=lambda: {
        "leagues_cleared": 0, "best_distance": 0, "records": {}})
    dex: dict[str, Any] = field(default_factory=lambda: {
        "breeds_seen": [], "perfect_cats": []})
    items: dict[str, Any] = field(default_factory=lambda: {"nature_item": False})
    settings: dict[str, Any] = field(default_factory=dict)


def meta_cfg(content: Content) -> dict[str, Any]:
    return content.rules.get("meta", {}) or {}


def start_cats(content: Content) -> int:
    return int(meta_cfg(content).get("start_cats", 12))


def name_max_length(content: Content) -> int:
    return int(meta_cfg(content).get("name_max_length", 16))


def format_cat_id(n: int) -> str:
    return f"c-{n:06d}"


def new_game(content: Content, rng: Random) -> SaveData:
    """Jogo novo: `start_cats` adultos sorteados; o deck ja vem com eles."""
    save = SaveData()
    for _ in range(start_cats(content)):
        cat = roll_cat(content, rng)
        cat.id = format_cat_id(save.next_cat_id)
        save.next_cat_id += 1
        save.cats.append(cat)
    save.deck = [c.id for c in save.cats][: content.rules["duel"]["deck_size"]]
    return save


# ------------------------------------------------------------ serializacao
def save_to_dict(save: SaveData) -> dict[str, Any]:
    cats = []
    for c in save.cats:
        d = asdict(c)
        if d.get("name") is None:
            d.pop("name", None)
        cats.append(d)
    return {
        "schema_version": SCHEMA_VERSION, "cats": cats, "deck": list(save.deck),
        "coins": save.coins, "next_cat_id": save.next_cat_id,
        "breeding": copy.deepcopy(save.breeding), "pity": copy.deepcopy(save.pity),
        "progress": copy.deepcopy(save.progress), "dex": copy.deepcopy(save.dex),
        "items": copy.deepcopy(save.items), "settings": copy.deepcopy(save.settings),
    }


def _int(v: Any, where: str, lo: int, hi: int | None = None) -> int:
    if isinstance(v, bool) or not isinstance(v, int):
        raise ValueError(f"save invalido: {where} deve ser inteiro (veio {v!r})")
    if v < lo or (hi is not None and v > hi):
        faixa = f">= {lo}" if hi is None else f"{lo} a {hi}"
        raise ValueError(f"save invalido: {where} fora da faixa ({faixa}): {v}")
    return v


def _dict(d: dict[str, Any], key: str) -> dict[str, Any]:
    v = d[key]
    if not isinstance(v, dict):
        raise ValueError(f"save invalido: '{key}' deve ser objeto")
    return v


def _cat_from_dict(d: Any, i: int, content: Content | None) -> Cat:
    where = f"cats[{i}]"
    if not isinstance(d, dict):
        raise ValueError(f"save invalido: {where} deve ser objeto")
    missing = [k for k in _CAT_REQUIRED if k not in d]
    if missing:
        raise ValueError(f"save invalido: {where} sem campos {missing}")
    extra = [k for k in d if k not in _CAT_KEYS]
    if extra:
        raise ValueError(f"save invalido: {where} com campos desconhecidos {extra}")
    for k in ("id", "breed", "nature"):
        if not isinstance(d[k], str) or not _ID_RE.match(d[k]):
            raise ValueError(f"save invalido: {where}.{k} invalido: {d[k]!r}")
    if d["sex"] not in ("M", "F"):
        raise ValueError(f"save invalido: {where}.sex invalido: {d['sex']!r}")
    if d["stage"] not in ("kitten", "adult"):
        raise ValueError(f"save invalido: {where}.stage invalido: {d['stage']!r}")
    name = d.get("name")
    if "name" in d and (not isinstance(name, str) or not name):
        raise ValueError(f"save invalido: {where}.name deve ser texto nao vazio")
    if content is not None:
        if d["breed"] not in content.breeds:
            raise ValueError(f"save invalido: {where}: raca inexistente '{d['breed']}'")
        if d["nature"] not in content.natures:
            raise ValueError(f"save invalido: {where}: natureza inexistente '{d['nature']}'")
    return Cat(id=d["id"], breed=d["breed"], sex=d["sex"], nature=d["nature"],
               iv_atk=_int(d["iv_atk"], f"{where}.iv_atk", 1, 5),
               iv_hp=_int(d["iv_hp"], f"{where}.iv_hp", 1, 5),
               stage=d["stage"], name=name,
               rest_runs_left=_int(d["rest_runs_left"], f"{where}.rest_runs_left", 0),
               runs_as_kitten=_int(d["runs_as_kitten"], f"{where}.runs_as_kitten", 0))


def save_from_dict(d: Any, content: Content | None = None) -> SaveData:
    """Valida e constroi o SaveData. Com `content`, confere tambem raca/natureza
    existentes e o tamanho maximo do deck. Erro -> ValueError."""
    if not isinstance(d, dict):
        raise ValueError("save invalido: raiz deve ser objeto")
    if d.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"versao de save desconhecida: {d.get('schema_version')!r}")
    missing = [k for k in _KEYS if k not in d]
    if missing:
        raise ValueError(f"save invalido: faltam campos {missing}")
    extra = [k for k in d if k not in _KEYS]
    if extra:
        raise ValueError(f"save invalido: campos desconhecidos {extra}")
    if not isinstance(d["cats"], list) or not isinstance(d["deck"], list) \
            or not isinstance(d["breeding"], list):
        raise ValueError("save invalido: 'cats', 'deck' e 'breeding' devem ser listas")
    cats = [_cat_from_dict(c, i, content) for i, c in enumerate(d["cats"])]
    by_id: dict[str, Cat] = {}
    for c in cats:
        if c.id in by_id:
            raise ValueError(f"save invalido: id de gato repetido '{c.id}'")
        by_id[c.id] = c
    deck = d["deck"]
    if len(set(map(str, deck))) != len(deck):
        raise ValueError("save invalido: deck com ids repetidos")
    if content is not None and len(deck) > content.rules["duel"]["deck_size"]:
        raise ValueError("save invalido: deck maior que rules.duel.deck_size")
    for cid in deck:
        cat = by_id.get(cid) if isinstance(cid, str) else None
        if cat is None:
            raise ValueError(f"save invalido: deck usa gato inexistente {cid!r}")
        if cat.stage != "adult":
            raise ValueError(f"save invalido: deck usa filhote '{cid}'")
    for i, b in enumerate(d["breeding"]):
        if not isinstance(b, dict) or set(b) != {"male", "female", "runs_left"}:
            raise ValueError(f"save invalido: breeding[{i}] malformado")
        if b["male"] not in by_id or b["female"] not in by_id:
            raise ValueError(f"save invalido: breeding[{i}] usa gato inexistente")
        _int(b["runs_left"], f"breeding[{i}].runs_left", 0)
    next_id = _int(d["next_cat_id"], "next_cat_id", 1)
    for cid in by_id:
        m = re.fullmatch(r"c-(\d+)", cid)
        if m and int(m.group(1)) >= next_id:
            raise ValueError(f"save invalido: next_cat_id ({next_id}) <= id existente '{cid}'")
    pity, progress = _dict(d, "pity"), _dict(d, "progress")
    dex, items = _dict(d, "dex"), _dict(d, "items")
    settings = _dict(d, "settings")
    _int(pity.get("runs_without_high_iv"), "pity.runs_without_high_iv", 0)
    _int(progress.get("leagues_cleared"), "progress.leagues_cleared", 0)
    _int(progress.get("best_distance"), "progress.best_distance", 0)
    if not isinstance(progress.get("records"), dict):
        raise ValueError("save invalido: progress.records deve ser objeto")
    for k in ("breeds_seen", "perfect_cats"):
        if not isinstance(dex.get(k), list):
            raise ValueError(f"save invalido: dex.{k} deve ser lista")
    if not isinstance(items.get("nature_item"), bool):
        raise ValueError("save invalido: items.nature_item deve ser booleano")
    return SaveData(cats=cats, deck=list(deck), coins=_int(d["coins"], "coins", 0),
                    next_cat_id=next_id, breeding=copy.deepcopy(d["breeding"]),
                    pity=copy.deepcopy(pity), progress=copy.deepcopy(progress),
                    dex=copy.deepcopy(dex), items=copy.deepcopy(items),
                    settings=copy.deepcopy(settings))


# ------------------------------------------------------------ arquivo
def write_save(save: SaveData, path: str | Path) -> None:
    """Escrita atomica: temporario na mesma pasta + replace."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(save_to_dict(save), ensure_ascii=False, indent=2)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def read_save(path: str | Path, content: Content | None = None) -> SaveData:
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"save ausente: {path}") from None
    except json.JSONDecodeError as e:
        raise ValueError(f"save com JSON invalido em {path}: {e}") from e
    return save_from_dict(raw, content)
