"""python -m ui.demo <tela> [--seed N]: abre uma tela isolada.

Telas: elite1/elite2 (draft da elite 1/2 e 2/2), duelo, run (a run inteira), mapa, draft, descanso, fimrun (a run ja no ponto da tela).
"""
from __future__ import annotations

import asyncio
import sys
from random import Random

from ui.__main__ import main

TELAS = ("duelo", "run", "mapa", "draft", "elite1", "elite2", "descanso", "fimrun")

if __name__ == "__main__":
    tela = sys.argv[1] if len(sys.argv) > 1 else "duelo"
    if tela not in TELAS:
        raise SystemExit(f"tela desconhecida: {tela}. Disponiveis: {', '.join(TELAS)}")
    if tela == "duelo":
        sys.exit(main(sys.argv[2:]))
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args(sys.argv[2:])
    from ui.app_run import run
    tela = {"elite1": "draft_elite_1", "elite2": "draft_elite_2"}.get(tela, tela)
    asyncio.run(run(a.seed if a.seed is not None else Random().randrange(1, 10**6), tela))
