"""Ponto de entrada do executavel de PC (PyInstaller). Save em %APPDATA%\Chaoscats\save.json."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def _save_path() -> Path:
    base = os.environ.get("CHAOSCATS_HOME")
    if not base:
        base = os.path.join(os.environ.get("APPDATA") or str(Path.home()), "Chaoscats")
    p = Path(base)
    p.mkdir(parents=True, exist_ok=True)
    return p / "save.json"


if __name__ == "__main__":
    from ui.__main__ import main

    extra = sys.argv[1:]
    # prefs (volumes/mudo) na mesma pasta do save, nao em <instalacao>/_internal/saves (ver reports/T11.0)
    from functools import partial

    from ui import audio

    audio.setup = partial(audio.setup, prefs_dir=_save_path().parent)
    if "--save" not in extra:
        extra = ["--save", str(_save_path())] + extra
    sys.exit(main(["--jogo"] + extra))
