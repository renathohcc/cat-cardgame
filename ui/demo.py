"""python -m ui.demo <tela> [--seed N]: abre uma tela isolada.

Telas: pausa/opcoes (menu de pausa e opcoes sobre o hub), elite1/elite2 (draft da elite 1/2 e 2/2), duelo, run (a run inteira), mapa, draft, descanso, fimrun (a run ja no ponto da tela).
quintal_0/quintal_2/quintal_3/quintal_4/quintal_6 (+ _noite), quintal_painel, quintal_desbloqueio, loja_areas/racoes/decoracao, adocao_cheio, breed_racao, ficha_historico, fim_run_meta, prestigio_selo (10a, economia)
criatorio_hub (cercado animado)/menu/colecao/.../doar_confirmar/criatorio/criatorio_casal/criatorio_recusado/novidades: hub em memoria (sem tocar em saves/).
"""
from __future__ import annotations

import asyncio
import sys
from random import Random

from ui.__main__ import main

TELAS = ("duelo", "run", "mapa", "draft", "elite1", "elite2", "descanso", "fimrun", "abandonar",
         "menu", "colecao", "colecao_deck", "renomear", "adocao", "adocao_vazia", "doar_confirmar",
         "criatorio", "criatorio_casal", "criatorio_recusado", "novidades",
         "criatorio_hub", "criatorio_hub_ficha", "criatorio_hub_adocao", "pausa", "opcoes",
         "quintal_0", "quintal_0_noite", "quintal_2", "quintal_2_noite", "quintal_4", "quintal_4_noite",
         "quintal_3", "quintal_6", "quintal_6_noite",
         "quintal_painel", "quintal_desbloqueio", "loja_areas", "loja_racoes", "loja_decoracao",
         "adocao_cheio", "breed_racao", "ficha_historico", "fim_run_meta", "prestigio_selo")

if __name__ == "__main__":
    tela = sys.argv[1] if len(sys.argv) > 1 else "duelo"
    if tela not in TELAS:
        raise SystemExit(f"tela desconhecida: {tela}. Disponiveis: {', '.join(TELAS)}")
    if tela == "duelo":
        sys.exit(main(sys.argv[2:]))
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--hora", metavar="HH:MM", default=None, help="forca a hora do cercado")
    a = ap.parse_args(sys.argv[2:])
    if tela in TELAS[9:]:
        from ui.app_hub import run as run_hub
        asyncio.run(run_hub(a.seed if a.seed is not None else Random().randrange(1, 10**6), None, tela, a.hora))
        sys.exit(0)
    from ui.app_run import run
    tela = {"elite1": "draft_elite_1", "elite2": "draft_elite_2"}.get(tela, tela)
    asyncio.run(run(a.seed if a.seed is not None else Random().randrange(1, 10**6), tela))
