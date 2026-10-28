"""Valida cada data/*.json real contra data/schemas/<nome>.schema.json
e confere referências cruzadas (decks dos inimigos)."""
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

DATA = Path(__file__).resolve().parent
SCHEMAS = DATA / "schemas"


def _load(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def check_schemas() -> tuple[int, dict[str, dict]]:
    errors = 0
    docs: dict[str, dict] = {}
    for path in sorted(DATA.glob("*.json")):
        schema_path = SCHEMAS / f"{path.stem}.schema.json"
        if not schema_path.exists():
            print(f"FALHA {path.name}: sem schema")
            errors += 1
            continue
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        doc = json.loads(path.read_text(encoding="utf-8"))
        errs = list(Draft202012Validator(schema).iter_errors(doc))
        for e in errs:
            print(f"FALHA {path.name}: {list(e.path)}: {e.message}")
        errors += len(errs)
        if not errs:
            print(f"ok {path.name}")
            docs[path.stem] = doc
    return errors, docs


def check_cross_refs(docs: dict[str, dict]) -> int:
    needed = ("breeds", "specials", "effects", "enemies", "natures", "rules")
    if any(n not in docs for n in needed):
        print("FALHA refs: arquivos de dados ausentes ou inválidos")
        return 1
    breeds = {b["id"] for b in docs["breeds"]["breeds"]}
    specials = {s["id"] for s in docs["specials"]["specials"]}
    effects = {e["id"] for e in docs["effects"]["effects"]}
    natures = {n["id"] for n in docs["natures"]["natures"]}
    deck_size = docs["rules"]["duel"]["deck_size"]
    iv_min = docs["rules"]["stats"]["iv_min"]
    iv_max = docs["rules"]["stats"]["iv_max"]
    keywords = {k["id"] for k in docs["keywords"]["keywords"]}
    errors = 0

    def fail(msg: str) -> None:
        nonlocal errors
        print(f"FALHA refs: {msg}")
        errors += 1

    for kw_owner in docs["specials"]["specials"]:
        for kw in kw_owner["keywords"]:
            if kw not in keywords:
                fail(f"{kw_owner['id']}: keyword '{kw}' inexistente")
    all_ids = breeds | specials | effects
    if len(all_ids) != len(breeds) + len(specials) + len(effects):
        fail("id repetido entre raças, especiais e efeitos")
    enemy_ids: set[str] = set()
    for enemy in docs["enemies"]["enemies"]:
        eid = enemy["id"]
        if eid in enemy_ids:
            fail(f"inimigo repetido: {eid}")
        enemy_ids.add(eid)
        total = 0
        for entry in enemy["deck"]:
            card = entry["carta"]
            total += entry["qtd"]
            if card not in all_ids:
                fail(f"{eid}: carta '{card}' inexistente")
            if entry["qtd"] <= 0:
                fail(f"{eid}: qtd inválida em '{card}'")
            is_breed = card in breeds
            has_iv = "iv_atk" in entry
            if is_breed != has_iv:
                fail(f"{eid}: '{card}' " + ("sem IV/natureza" if is_breed else "não deve ter IV/natureza"))
            if has_iv:
                for key in ("iv_atk", "iv_hp"):
                    if not iv_min <= entry[key] <= iv_max:
                        fail(f"{eid}: {key} fora de {iv_min}-{iv_max} em '{card}'")
                if entry["nature"] not in natures:
                    fail(f"{eid}: natureza '{entry['nature']}' inexistente")
        if total != deck_size:
            fail(f"{eid}: deck soma {total}, esperado {deck_size}")
    if not errors:
        print("ok referências cruzadas")
    return errors


def check_run(docs: dict[str, dict]) -> int:
    if "run" not in docs or "enemies" not in docs or "rules" not in docs:
        print("FALHA run: arquivos ausentes ou inválidos")
        return 1
    run = docs["run"]
    enemies = {e["id"]: e["tipo"] for e in docs["enemies"]["enemies"]}
    errors = 0

    def fail(msg: str) -> None:
        nonlocal errors
        print(f"FALHA run: {msg}")
        errors += 1

    seen: set[str] = set()
    layers = run["map"]["layers"]
    for node in (n for layer in layers for n in layer["nodes"]):
        nid, tipo, ini = node["id"], node["tipo"], node["inimigo"]
        if nid in seen:
            fail(f"id de nó repetido: {nid}")
        seen.add(nid)
        if tipo == "descanso":
            if ini is not None:
                fail(f"{nid}: descanso não deve ter inimigo")
        elif ini not in enemies:
            fail(f"{nid}: inimigo '{ini}' inexistente")
        elif enemies[ini] != tipo:
            fail(f"{nid}: tipo '{tipo}' != tipo do inimigo '{enemies[ini]}'")
    last = layers[-1]["nodes"]
    if len(last) != 1 or last[0]["tipo"] != "chefe":
        fail("última camada deve ter exatamente 1 nó chefe")
    if run["start_deck"]["gatos"] != docs["rules"]["duel"]["deck_size"]:
        fail("start_deck.gatos != rules.duel.deck_size")
    pool = 0
    if run["pool"]["effects"] and "effects" in docs:
        pool += len(docs["effects"]["effects"])
    if run["pool"]["specials"] and "specials" in docs:
        pool += len(docs["specials"]["specials"])
    for key in ("draft_options", "draft_options_elite", "draft_options_rest"):
        if run[key] > pool:
            fail(f"{key} ({run[key]}) maior que o pool ({pool})")
    meta = docs["rules"]["meta"]
    if meta["start_cats"] < docs["rules"]["duel"]["deck_size"]:
        fail("meta.start_cats < duel.deck_size")
    if meta["name_max_length"] < 1:
        fail("meta.name_max_length < 1")
    if not errors:
        print("ok run")
    return errors


def main() -> int:
    errors, docs = check_schemas()
    errors += check_cross_refs(docs)
    errors += check_run(docs)
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
