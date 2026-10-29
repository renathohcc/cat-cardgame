"""T9.9: fundo do quintal = T9.8 com cercas/postes novos (build_t99_fence). Uso: python assets/tools/build_t99_bg.py (T98_OUT=staging)"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import build_t98_bg as BG  # noqa: E402
import build_t99_fence as F  # noqa: E402

BG.draw_fences = lambda c: F.draw_fences(c, BG.L)

if __name__ == "__main__":
    BG.main()
