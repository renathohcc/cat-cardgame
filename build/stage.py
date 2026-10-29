"""Copia filtrada do projeto para uma pasta de staging (compartilhada por PC e web).

Inclui: core/, ui/, data/ e as pastas de assets usadas pelo jogo.
Exclui: tudo que comeca com '_' (_src, _proposta, _v*, _candidatos...), assets/tools, __pycache__,
reports, docs, tests, sim, saves e arquivos de trabalho.
"""
from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGES = ("core", "ui", "data")
ASSET_EXCLUDE_TOP = {"tools"}
EXTRA_SKIP_SUFFIX = {".pyc", ".webp", ".psd", ".aseprite", ".md"}


def _ignore(_dir: str, names: list[str]) -> set[str]:
    skip = set()
    for n in names:
        if n.startswith("_") and not (n.startswith("__") and n.endswith(".py")) and n != "__pycache__":
            skip.add(n)
        elif n == "__pycache__" or Path(n).suffix in EXTRA_SKIP_SUFFIX:
            skip.add(n)
    return skip


def make_stage(dest: Path, *, with_audio: bool = True) -> Path:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for pkg in PACKAGES:
        shutil.copytree(ROOT / pkg, dest / pkg, ignore=_ignore)
    for sub in sorted((ROOT / "assets").iterdir()):
        if not sub.is_dir() or sub.name.startswith("_") or sub.name in ASSET_EXCLUDE_TOP:
            continue
        if sub.name == "audio" and not with_audio:
            continue
        shutil.copytree(sub, dest / "assets" / sub.name, ignore=_ignore)
    return dest


def tree_size_mb(p: Path) -> float:
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file()) / 1e6
