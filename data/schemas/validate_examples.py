"""Valida exemplos validos (devem passar) e invalidos (devem falhar) contra os schemas."""
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

HERE = Path(__file__).parent


def load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def main() -> int:
    fails = 0
    for sp in sorted(HERE.glob("*.schema.json")):
        name = sp.name.removesuffix(".schema.json")
        schema = load(sp)
        Draft202012Validator.check_schema(schema)
        v = Draft202012Validator(schema)
        ok = HERE / "examples" / f"{name}.example.json"
        bads = sorted((HERE / "examples" / "invalid").glob(f"{name}.invalid*.json"))
        errs = list(v.iter_errors(load(ok))) if ok.exists() else ["exemplo valido ausente"]
        failed = False
        if errs:
            print(f"FALHA {name}: exemplo valido rejeitado: {errs[0]}")
            failed = True
        if not bads:
            print(f"FALHA {name}: exemplo invalido ausente")
            failed = True
        for bad in bads:
            if not list(v.iter_errors(load(bad))):
                print(f"FALHA {name}: exemplo invalido aceito: {bad.name}")
                failed = True
        if failed:
            fails += 1
        else:
            print(f"ok {name}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
