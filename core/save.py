"""Save local (CONTRATOS 1.9): dados da colecao e progresso. Sem run em andamento."""
from __future__ import annotations

import copy
import json
import os
import re
import shutil
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from random import Random
from typing import Any

from core.cats import roll_cat
from core.types import Cat, Content

__all__ = ["SaveData", "new_game", "save_to_dict", "save_from_dict",
           "write_save", "read_save", "meta_cfg", "start_cats", "name_max_length",
           "SCHEMA_VERSION", "migrate_save_dict"]

SCHEMA_VERSION = 2
_ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_V1_KEYS = ("schema_version", "cats", "deck", "coins", "next_cat_id", "breeding",
            "pity", "progress", "dex", "items", "settings")
_KEYS = _V1_KEYS + ("prestige", "areas_unlocked", "rations", "decorations_owned",
                    "first_league_win_claimed", "lifetime")
_HISTORY_KEYS = ("runs", "duels_won", "bosses_defeated")
_LIFETIME_KEYS = ("runs_completed", "duels_won")
_CAT_REQUIRED = ("id", "breed", "sex", "nature", "iv_atk", "iv_hp", "stage",
                 "rest_runs_left", "runs_as_kitten", "generation", "parents", "history")
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
    pending_adoption: dict[str, Any] | None = None   # {cats: [Cat], result, nodes_cleared}
    # save v2 (economia)
    prestige: int = 1
    areas_unlocked: list[str] = field(default_factory=list)
    rations: dict[str, int] = field(default_factory=dict)
    decorations_owned: list[str] = field(default_factory=list)
    first_league_win_claimed: bool = False
    lifetime: dict[str, int] = field(default_factory=lambda: {
        "runs_completed": 0, "duels_won": 0})
    legacy_capacity: int = 0            # vagas extras de saves v1 (ausente = 0)
    migrated_from: int | None = None    # versao lida do arquivo, se foi migrado (nao serializa)


def register_dex(save: SaveData, cat: Cat) -> None:
    """Registra raca vista e gato perfeito (IV 5/5) na dex, sem duplicar."""
    seen = save.dex.setdefault("breeds_seen", [])
    if cat.breed not in seen:
        seen.append(cat.breed)
    if cat.iv_atk == 5 and cat.iv_hp == 5:
        perfect = save.dex.setdefault("perfect_cats", [])
        if cat.id not in perfect:
            perfect.append(cat.id)


def meta_cfg(content: Content) -> dict[str, Any]:
    return content.rules.get("meta", {}) or {}


def start_cats(content: Content) -> int:
    return int(meta_cfg(content).get("start_cats", 12))


def name_max_length(content: Content) -> int:
    return int(meta_cfg(content).get("name_max_length", 16))


def zero_rations(content: Content | None) -> dict[str, int]:
    """Estoque zerado para cada racao de data/shop.json ({} sem loja)."""
    shop = content.shop if content is not None else {}
    return {r["id"]: 0 for r in (shop or {}).get("rations", [])}


def format_cat_id(n: int) -> str:
    return f"c-{n:06d}"


def new_game(content: Content, rng: Random) -> SaveData:
    """Jogo novo: `start_cats` adultos sorteados; o deck ja vem com eles."""
    save = SaveData(rations=zero_rations(content))
    for _ in range(start_cats(content)):
        cat = roll_cat(content, rng)
        cat.id = format_cat_id(save.next_cat_id)
        save.next_cat_id += 1
        save.cats.append(cat)
        register_dex(save, cat)
    save.deck = [c.id for c in save.cats][: content.rules["duel"]["deck_size"]]
    return save


# ------------------------------------------------------------ serializacao
def _cat_to_dict(c: Cat) -> dict[str, Any]:
    d = asdict(c)
    d["parents"] = list(c.parents)
    d["history"] = dict(c.history)
    if d.get("name") is None:
        d.pop("name", None)
    return d


def save_to_dict(save: SaveData) -> dict[str, Any]:
    cats = [_cat_to_dict(c) for c in save.cats]
    out = {
        "schema_version": SCHEMA_VERSION, "cats": cats, "deck": list(save.deck),
        "coins": save.coins, "next_cat_id": save.next_cat_id,
        "breeding": copy.deepcopy(save.breeding), "pity": copy.deepcopy(save.pity),
        "progress": copy.deepcopy(save.progress), "dex": copy.deepcopy(save.dex),
        "items": copy.deepcopy(save.items), "settings": copy.deepcopy(save.settings),
        "prestige": save.prestige, "areas_unlocked": list(save.areas_unlocked),
        "rations": dict(save.rations), "decorations_owned": list(save.decorations_owned),
        "first_league_win_claimed": save.first_league_win_claimed,
        "lifetime": dict(save.lifetime),
    }
    if save.legacy_capacity > 0:
        out["legacy_capacity"] = save.legacy_capacity
    if save.pending_adoption is not None:
        p = save.pending_adoption
        out["pending_adoption"] = {
            "cats": [_cat_to_dict(c) for c in p["cats"]],
            "result": p["result"], "nodes_cleared": p["nodes_cleared"]}
    return out


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


def _id_list(v: Any, where: str) -> list[str]:
    if not isinstance(v, list) or any(not isinstance(i, str) or not _ID_RE.match(i)
                                      for i in v):
        raise ValueError(f"save invalido: {where} deve ser lista de ids")
    return list(v)


def _counters(v: Any, keys: tuple[str, ...], where: str) -> dict[str, int]:
    if not isinstance(v, dict) or set(v) != set(keys):
        raise ValueError(f"save invalido: {where} deve ter exatamente {list(keys)}")
    return {k: _int(v[k], f"{where}.{k}", 0) for k in keys}


def _lineage(d: dict[str, Any], where: str) -> tuple[list[str], dict[str, int]]:
    parents = _id_list(d["parents"], f"{where}.parents")
    if len(parents) not in (0, 2):
        raise ValueError(f"save invalido: {where}.parents deve ter 0 ou 2 ids")
    return parents, _counters(d["history"], _HISTORY_KEYS, f"{where}.history")


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
    parents, history = _lineage(d, where)
    return Cat(id=d["id"], breed=d["breed"], sex=d["sex"], nature=d["nature"],
               generation=_int(d["generation"], f"{where}.generation", 1),
               parents=parents, history=history,
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
    version = d.get("schema_version")
    migrated_from: int | None = None
    if isinstance(version, int) and not isinstance(version, bool) and version == 1:
        d, migrated_from = migrate_save_dict(d, content), 1
    elif version != SCHEMA_VERSION or isinstance(version, bool):
        raise ValueError(f"versao de save desconhecida: {version!r}")
    missing = [k for k in _KEYS if k not in d]
    if missing:
        raise ValueError(f"save invalido: faltam campos {missing}")
    extra = [k for k in d if k not in _KEYS and k not in ("pending_adoption", "legacy_capacity")]
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
    in_couple: set[str] = set()
    for i, b in enumerate(d["breeding"]):
        if not isinstance(b, dict) or set(b) != {"male", "female", "runs_left", "ration",
                                         "ration_choice"}:
            raise ValueError(f"save invalido: breeding[{i}] malformado")
        if b["male"] not in by_id or b["female"] not in by_id:
            raise ValueError(f"save invalido: breeding[{i}] usa gato inexistente")
        _int(b["runs_left"], f"breeding[{i}].runs_left", 0)
        if b["ration"] is not None and (not isinstance(b["ration"], str)
                                        or not _ID_RE.match(b["ration"])):
            raise ValueError(f"save invalido: breeding[{i}].ration invalida")
        _check_ration_choice(b["ration_choice"], i)
        m, f = by_id[b["male"]], by_id[b["female"]]
        if m.sex != "M" or f.sex != "F":
            raise ValueError(f"save invalido: breeding[{i}] sem macho e femea")
        if m.stage != "adult" or f.stage != "adult":
            raise ValueError(f"save invalido: breeding[{i}] com filhote")
        for cid in (m.id, f.id):
            if cid in in_couple:
                raise ValueError(f"save invalido: gato '{cid}' em mais de um casal")
            in_couple.add(cid)
    for cid in deck:
        if cid in in_couple:
            raise ValueError(f"save invalido: gato '{cid}' esta no deck e em um casal "
                             "de criatorio ao mesmo tempo")
    next_id = _int(d["next_cat_id"], "next_cat_id", 1)
    pending = _pending_from_dict(d.get("pending_adoption"), content, by_id)
    all_ids = list(by_id)
    if pending is not None:
        all_ids += [c.id for c in pending["cats"]]
    for cid in all_ids:
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
    econ = _economy_from_dict(d, content)
    econ["legacy_capacity"] = _int(d.get("legacy_capacity", 0), "legacy_capacity", 0)
    return SaveData(cats=cats, deck=list(deck), coins=_int(d["coins"], "coins", 0),
                    next_cat_id=next_id, breeding=copy.deepcopy(d["breeding"]),
                    pity=copy.deepcopy(pity), progress=copy.deepcopy(progress),
                    dex=copy.deepcopy(dex), items=copy.deepcopy(items),
                    settings=copy.deepcopy(settings), pending_adoption=pending,
                    migrated_from=migrated_from, **econ)


def _check_ration_choice(rc: Any, i: int) -> None:
    if rc is None:
        return
    if (not isinstance(rc, dict) or set(rc) != {"stat", "parent"}
            or rc["stat"] not in ("atk", "hp") or rc["parent"] not in ("father", "mother")):
        raise ValueError(f"save invalido: breeding[{i}].ration_choice invalida")


def _economy_from_dict(d: dict[str, Any], content: Content | None) -> dict[str, Any]:
    areas = _id_list(d["areas_unlocked"], "areas_unlocked")
    decos = _id_list(d["decorations_owned"], "decorations_owned")
    if len(set(areas)) != len(areas) or len(set(decos)) != len(decos):
        raise ValueError("save invalido: areas/decoracoes repetidas")
    rations = d["rations"]
    if not isinstance(rations, dict) or any(not isinstance(k, str) or not _ID_RE.match(k)
                                            for k in rations):
        raise ValueError("save invalido: rations deve ser objeto de ids")
    rations = {k: _int(v, f"rations.{k}", 0) for k, v in rations.items()}
    if not isinstance(d["first_league_win_claimed"], bool):
        raise ValueError("save invalido: first_league_win_claimed deve ser booleano")
    if content is not None and content.shop:
        _check_shop_ids(content, areas, decos, rations)
    return {"prestige": _int(d["prestige"], "prestige", 1, 5), "areas_unlocked": areas,
            "rations": rations, "decorations_owned": decos,
            "first_league_win_claimed": d["first_league_win_claimed"],
            "lifetime": _counters(d["lifetime"], _LIFETIME_KEYS, "lifetime")}


def _check_shop_ids(content: Content, areas: list[str], decos: list[str],
                    rations: dict[str, int]) -> None:
    shop = content.shop
    for ids, key, label in ((areas, "areas", "area"), (decos, "decorations", "decoracao"),
                            (list(rations), "rations", "racao")):
        known = {x["id"] for x in shop[key]}
        for i in ids:
            if i not in known:
                raise ValueError(f"save invalido: {label} inexistente '{i}'")


def migrate_save_dict(d: dict[str, Any], content: Content | None = None) -> dict[str, Any]:
    """Save v1 -> v2 (copia; nao muta `d`). Acrescenta so os campos novos com
    valores neutros; qualquer defeito do v1 continua para a validacao reclamar."""
    out = copy.deepcopy(d)
    out["schema_version"] = SCHEMA_VERSION
    for c in _dict_items(out.get("cats")):
        _add_lineage(c)
    pend = out.get("pending_adoption")
    if isinstance(pend, dict):
        for c in _dict_items(pend.get("cats")):
            _add_lineage(c)
    for b in _dict_items(out.get("breeding")):
        b.setdefault("ration", None)
        b["ration"], legacy = split_legacy_ration(b["ration"])
        b.setdefault("ration_choice", legacy)
    out.setdefault("prestige", 1)
    out.setdefault("areas_unlocked", [])
    out.setdefault("rations", zero_rations(content))
    out.setdefault("decorations_owned", [])
    out.setdefault("first_league_win_claimed", False)
    out.setdefault("lifetime", {"runs_completed": 0, "duels_won": 0})
    _add_legacy_capacity(out, content)
    return out


def _add_legacy_capacity(out: dict[str, Any], content: Content | None) -> None:
    """Vagas extras: numero de gatos do v1, so se maior que as vagas iniciais."""
    cats = out.get("cats")
    if "legacy_capacity" in out or not isinstance(cats, list):
        return
    start = 0
    if content is not None and content.shop:
        start = int(content.shop["start"]["slots"])
    if len(cats) > start:
        out["legacy_capacity"] = len(cats)


_LEGACY_RATION_RE = re.compile(r"(racao-escolha)-(atk|hp)-(pai|mae)")


def split_legacy_ration(value: str | None) -> tuple[str | None, dict[str, str] | None]:
    """Migracao: `racao-escolha-<stat>-<pai|mae>` -> (`racao-escolha`, ration_choice).
    Qualquer outro valor passa intacto, com escolha None."""
    m = _LEGACY_RATION_RE.fullmatch(value) if isinstance(value, str) else None
    if m is None:
        return value, None
    return m.group(1), {"stat": m.group(2), "parent": {"pai": "father", "mae": "mother"}[m.group(3)]}


def _dict_items(v: Any) -> list[dict[str, Any]]:
    return [x for x in v if isinstance(x, dict)] if isinstance(v, list) else []


def _add_lineage(c: dict[str, Any]) -> None:
    c.setdefault("generation", 1)
    c.setdefault("parents", [])
    c.setdefault("history", {"runs": 0, "duels_won": 0, "bosses_defeated": 0})


def _pending_from_dict(p: Any, content: Content | None,
                       by_id: dict[str, Cat]) -> dict[str, Any] | None:
    if p is None:
        return None
    if not isinstance(p, dict) or set(p) != {"cats", "result", "nodes_cleared"} \
            or not isinstance(p["cats"], list) or not isinstance(p["result"], str):
        raise ValueError("save invalido: pending_adoption malformado")
    _int(p["nodes_cleared"], "pending_adoption.nodes_cleared", 0)
    cats = [_cat_from_dict(c, i, content) for i, c in enumerate(p["cats"])]
    if any(c.stage != "adult" for c in cats):
        raise ValueError("save invalido: pending_adoption com filhote")
    seen = set(by_id)
    for c in cats:
        if c.id in seen:
            raise ValueError(f"save invalido: id de gato repetido '{c.id}'")
        seen.add(c.id)
    if not cats:
        return None
    return {"cats": cats, "result": p["result"], "nodes_cleared": p["nodes_cleared"]}


# ------------------------------------------------------------ arquivo
def _is_v1_file(path: Path) -> bool:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    v = raw.get("schema_version") if isinstance(raw, dict) else None
    return v == 1 and not isinstance(v, bool)


def v1_backup_path(path: str | Path) -> Path:
    """`save.json` -> `save.v1.bak` (mesma pasta)."""
    path = Path(path)
    return path.with_name(path.stem + ".v1.bak")


def _backup_v1(path: Path) -> str | None:
    """Se `path` guarda um save v1, preserva em `<nome>.v1.bak` (atomico). O primeiro
    v1 vale: se o backup ja existe, nao e sobrescrito. Devolve aviso ou None."""
    try:
        if not path.is_file() or not _is_v1_file(path):
            return None
        dest = v1_backup_path(path)
        if dest.exists():
            return None
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=dest.name + ".", suffix=".tmp")
        os.close(fd)
        try:
            shutil.copyfile(path, tmp)
            os.replace(tmp, dest)
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise
    except OSError as e:
        return f"nao foi possivel guardar o backup do save v1: {e}"
    return None


def write_save(save: SaveData, path: str | Path) -> str | None:
    """Escrita atomica: temporario na mesma pasta + replace. Se o arquivo atual e um
    save v1, antes o preserva em `<nome>.v1.bak`. Devolve um aviso (texto) se esse
    backup falhou; a gravacao segue mesmo assim."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    warning = _backup_v1(path)
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
    return warning


def read_save(path: str | Path, content: Content | None = None) -> SaveData:
    path = Path(path)
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"save ausente: {path}") from None
    except json.JSONDecodeError as e:
        raise ValueError(f"save com JSON invalido em {path}: {e}") from e
    return save_from_dict(raw, content)
