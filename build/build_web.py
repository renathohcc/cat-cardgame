"""Gera o pacote de navegador: python build/build_web.py [--serve]  (precisa de pygbag; build exige rede).

Saida: build/out/web/app/build/web/{index.html,*.apk,...} (publicar essa pasta). --serve sobe em localhost:8000.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from stage import make_stage, tree_size_mb  # noqa: E402

OUT = HERE / "out" / "web"


def main() -> int:
    app = make_stage(OUT / "app")
    shutil.copy(HERE / "web" / "main.py", app / "main.py")
    shutil.copy(HERE / "web" / "jsonschema.py", app / "jsonschema.py")
    # favicon exigido pelo template do pygbag
    print(f"staging web: {tree_size_mb(app):.1f} MB")
    cmd = [sys.executable, "-m", "pygbag", "--ume_block", "0", "--title", "Chaoscats"]
    if "--serve" not in sys.argv:
        cmd += ["--build"]  # sem --build o pygbag constroi e SOBE o servidor local (porta 8000)
    cmd.append(str(app))
    rc = subprocess.call(cmd)
    out = app / "build" / "web"
    if rc == 0 and out.exists():
        print(f"ok: {out} ({tree_size_mb(out):.1f} MB)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
