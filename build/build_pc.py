"""Gera o executavel de PC: python build/build_pc.py  (usa o python que o executa; precisa de pyinstaller).

Saida: build/out/pc/Chaoscats/Chaoscats.exe (--onedir, sem console).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from stage import make_stage, tree_size_mb  # noqa: E402

OUT = HERE / "out" / "pc"


def main() -> int:
    stage = make_stage(OUT / "stage")
    print(f"staging: {tree_size_mb(stage):.1f} MB")
    env = dict(os.environ, CHAOSCATS_STAGE=str(stage))
    cmd = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
           "--distpath", str(OUT / "dist"), "--workpath", str(OUT / "work"),
           str(HERE / "chaoscats_pc.spec")]
    rc = subprocess.call(cmd, env=env, cwd=HERE)
    exe = OUT / "dist" / "Chaoscats" / "Chaoscats.exe"
    if rc == 0 and exe.exists():
        print(f"ok: {exe} ({tree_size_mb(exe.parent):.1f} MB)")
    return rc


if __name__ == "__main__":
    sys.exit(main())
