"""python -m ui [--seed N] [--screenshot out.png [--cena inicio|selecionado|ataque|final|confirmar]]
python -m ui --run [--seed N]    mini-run (mapa, duelos, draft, fim)
python -m ui --seed 1 --screenshot out.png --cena mapa|draft|descanso|fimrun   cenas da run"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from random import Random


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ui", description="Duelo de teste (pygame)")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--screenshot", metavar="ARQ.png", default=None,
                    help="renderiza uma cena sem janela e salva o PNG (3x)")
    ap.add_argument("--cena", default="inicio",
                    help="inicio | selecionado | ataque | final | dado | tooltip | confirmar | "
                         "efeito | espirito | chefe | mapa | draft | descanso | fimrun | fimrun_vitoria | duelrun")
    ap.add_argument("--run", action="store_true", help="abre a mini-run (mapa, duelos, draft)")
    ap.add_argument("--inimigo", metavar="ID", default=None,
                    help="id de data/enemies.json (padrão: sorteia um inimigo real pelo seed)")
    args = ap.parse_args(argv)
    seed = args.seed if args.seed is not None else Random().randrange(1, 10**6)
    if args.screenshot:
        os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        from ui.scenes_run import RUN_SCENES
        if args.cena in RUN_SCENES:
            from ui.app_run import screenshot as run_shot
            run_shot(args.screenshot, seed, args.cena)
            print(f"salvo: {args.screenshot} (seed {seed}, cena {args.cena})")
            return 0
        from ui.app import screenshot
        screenshot(args.screenshot, seed, args.cena, args.inimigo)
        print(f"salvo: {args.screenshot} (seed {seed}, cena {args.cena})")
        return 0
    if args.run:
        from ui.app_run import run as run_game
        asyncio.run(run_game(seed))
        return 0
    from ui.app import run
    asyncio.run(run(seed, args.inimigo))
    return 0


if __name__ == "__main__":
    sys.exit(main())
