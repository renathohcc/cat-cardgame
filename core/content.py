"""Carregamento e validacao do conteudo de data/."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema

from core.types import Content

_REQUIRED = {
    "keywords": "keywords",
    "breeds": "breeds",
    "natures": "natures",
    "rules": None,
}


def _read(data_dir: Path, name: str) -> Any:
    path = data_dir / f"{name}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"arquivo de dados ausente: {path}") from None
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON invalido em {path}: {e}") from e


def _validate(data_dir: Path, name: str, doc: Any) -> None:
    schema_path = data_dir / "schemas" / f"{name}.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        jsonschema.validate(doc, schema)
    except jsonschema.ValidationError as e:
        where = "/".join(str(p) for p in e.absolute_path) or "(raiz)"
        raise ValueError(f"{name}.json invalido em {where}: {e.message}") from e


def _index(items: list[dict[str, Any]], name: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in items:
        if item["id"] in out:
            raise ValueError(f"{name}.json: id duplicado '{item['id']}'")
        out[item["id"]] = item
    return out


def _cross_check(content: Content) -> None:
    for b in content.breeds.values():
        for kw in b.get("keywords", []):
            if kw not in content.keywords:
                raise ValueError(f"raca '{b['id']}' usa keyword inexistente '{kw}'")


def actions_of(raw: Any) -> list[dict[str, Any]]:
    """Normaliza `acoes`/`efeito_ao_entrar`/`acao`: None, objeto ou lista -> lista."""
    if raw is None:
        return []
    return [raw] if isinstance(raw, dict) else list(raw)


def _check_actions(owner: str, actions: list[dict[str, Any]]) -> None:
    chosen = {a["alvo"] for a in actions if a["alvo"].endswith("_escolhido")}
    if len(chosen) > 1:
        raise ValueError(f"{owner}: acoes com alvos escolhidos diferentes {sorted(chosen)}")
    for a in actions:
        if a["tipo"] == "buff_atk" and a["alvo"] != "aliado_escolhido":
            raise ValueError(f"{owner}: buff_atk so vale para aliado_escolhido")
        if a["tipo"] in ("comprar", "energia") and a["alvo"] != "nenhum":
            raise ValueError(f"{owner}: {a['tipo']} exige alvo 'nenhum'")


def _check_rule(owner: str, rule: dict[str, Any] | None) -> None:
    if rule is None:
        return
    if rule.get("gatilho") != "inicio_turno_proprio":
        raise ValueError(f"{owner}: regra_propria com gatilho desconhecido "
                         f"'{rule.get('gatilho')}'")
    acts = actions_of(rule.get("acao", rule.get("acoes")))
    if not acts:
        raise ValueError(f"{owner}: regra_propria sem 'acao'")
    _check_actions(owner, acts)
    if any(a["alvo"].endswith("_escolhido") for a in acts):
        raise ValueError(f"{owner}: regra_propria nao pode ter alvo escolhido")


def _cross_check_phase3(content: Content) -> None:
    ids = [("raca", content.breeds), ("especial", content.specials),
           ("efeito", content.effects)]
    seen: dict[str, str] = {}
    for kind, table in ids:
        for i in table:
            if i in seen:
                raise ValueError(f"id '{i}' repetido entre {seen[i]} e {kind}")
            seen[i] = kind
    for sp in content.specials.values():
        for kw in sp.get("keywords", []):
            if kw not in content.keywords:
                raise ValueError(f"especial '{sp['id']}' usa keyword inexistente '{kw}'")
        _check_actions(f"especial '{sp['id']}'", actions_of(sp.get("efeito_ao_entrar")))
    for ef in content.effects.values():
        _check_actions(f"efeito '{ef['id']}'", actions_of(ef["acoes"]))
    for en in content.enemies.values():
        _check_rule(f"inimigo '{en['id']}'", en.get("regra_propria"))
        for entry in en["deck"]:
            cid = entry["carta"]
            if cid not in seen:
                raise ValueError(f"inimigo '{en['id']}' usa carta inexistente '{cid}'")
            if seen[cid] == "raca":
                if entry.get("nature", "calmo") not in content.natures:
                    raise ValueError(f"inimigo '{en['id']}': natureza '{entry['nature']}' inexistente")
            elif "iv_atk" in entry:
                raise ValueError(f"inimigo '{en['id']}': IV/natureza so valem para raca ('{cid}')")


def _cross_check_run(content: Content) -> None:
    if content.run is None:
        return
    for layer in content.run["map"]["layers"]:
        for node in layer["nodes"]:
            en = node.get("inimigo")
            if en is not None and en not in content.enemies:
                raise ValueError(f"run.json: no '{node['id']}' usa inimigo inexistente '{en}'")
            if en is None and node["tipo"] != "descanso":
                raise ValueError(f"run.json: no '{node['id']}' ({node['tipo']}) sem inimigo")


def load_content(data_dir: Path) -> Content:
    data_dir = Path(data_dir)
    docs: dict[str, Any] = {}
    for name in _REQUIRED:
        docs[name] = _read(data_dir, name)
        _validate(data_dir, name, docs[name])
    extras: dict[str, Any] = {}
    for name in ("specials", "effects", "enemies", "run"):
        if (data_dir / f"{name}.json").exists():
            doc = _read(data_dir, name)
            _validate(data_dir, name, doc)
            extras[name] = doc
    content = Content(
        breeds=_index(docs["breeds"]["breeds"], "breeds"),
        natures=_index(docs["natures"]["natures"], "natures"),
        keywords=_index(docs["keywords"]["keywords"], "keywords"),
        rules=docs["rules"],
        extras=extras,
        effects=_index(extras.get("effects", {}).get("effects", []), "effects"),
        specials=_index(extras.get("specials", {}).get("specials", []), "specials"),
        enemies=_index(extras.get("enemies", {}).get("enemies", []), "enemies"),
        run=extras.get("run"),
    )
    _cross_check(content)
    _cross_check_phase3(content)
    _cross_check_run(content)
    return content
