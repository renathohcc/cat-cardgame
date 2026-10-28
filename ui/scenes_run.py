"""Cenas de screenshot e autoplay da mini-run. Usa so o RunController (e o core.ai como jogador)."""
from __future__ import annotations

from random import Random

from core.ai import choose_action
from ui import layout_run as LR
from ui.controller import load_game_content
from ui.render import UIState
from ui.run_controller import RunController

RUN_SCENES = ("mapa", "draft", "draft_elite_1", "draft_elite_2", "descanso", "fimrun", "fimrun_vitoria", "duelrun")


def play_duel(rc: RunController, rng: Random) -> bool:
    """Joga o duelo da run com a IA no lugar do jogador e clica CONTINUAR. True se venceu."""
    c = rc.duel_ctrl
    for _ in range(4000):
        if c.over:
            break
        if c.can_act():
            c._do(choose_action(c.duel, "player", rng))
        c.update(5.0)
    for _ in range(5):
        c.update(1.0)
    won = c.duel.winner == "player"
    rc.click(("continue",))
    return won


def pick_random(rc: RunController, rng: Random) -> None:
    i = rng.randrange(len(rc.run.draft_options))
    rc.click(("draft_card", i))
    rc.click(("draft_pick", i))


def step(rc: RunController, rng: Random, node_choice: str | None = None) -> None:
    """Avanca a run um passo (mapa -> no, duelo -> fim, draft -> escolha)."""
    s = rc.screen
    if s == "map":
        ids = rc.available_ids()
        rc.click(("node", node_choice if node_choice in ids else rng.choice(ids)))
    elif s == "duel":
        play_duel(rc, rng)
    elif s == "draft":
        pick_random(rc, rng)


def autoplay(rc: RunController, rng: Random, max_steps: int = 200) -> None:
    for _ in range(max_steps):
        if rc.screen == "finished":
            return
        step(rc, rng)


def make(seed: int, name: str) -> tuple[RunController, UIState] | None:
    content = load_game_content()
    for s in range(seed, seed + 80):
        rc = RunController(content, s)
        rng = Random(s + 5)
        ui = UIState(t=0.2)
        if name == "mapa":                         # c1 vencida + descanso feito: camada 3
            if _until(rc, rng, lambda r: r.run.layer >= 2 and r.screen == "map",
                      prefer={"c2-descanso"}):
                ui.mouse = LR.node_rect(3, 0, 2, 6).center
                return rc, ui
        elif name == "draft":
            if _until(rc, rng, lambda r: r.screen == "draft"):
                rc.click(("draft_card", 1))
                ui.mouse = LR.draft_pick_rect(1, len(rc.run.draft_options)).center
                return rc, ui
        elif name in ("draft_elite_1", "draft_elite_2"):
            if _until(rc, rng, lambda r: r.screen == "draft" and r.draft_from == "elite",
                      prefer={"c4-elite"}, limit=120):
                if name == "draft_elite_2":
                    pick_random(rc, rng)
                    if rc.screen != "draft":
                        continue
                rc.click(("draft_card", 0))
                return rc, ui
        elif name == "descanso":
            if _until(rc, rng, lambda r: r.screen == "map" and r.run.layer == 1):
                rc.click(("node", "c2-descanso"))
                rc.click(("draft_card", 0))
                return rc, ui
        elif name in ("fimrun", "fimrun_vitoria"):
            autoplay(rc, rng)
            if rc.screen == "finished" and (name == "fimrun" or rc.run.result == "vitoria"):
                return rc, ui
        elif name == "duelrun":                    # fim de duelo com CONTINUAR
            rc.click(("node", "c1-batalha"))
            c = rc.duel_ctrl
            for _ in range(4000):
                if c.over:
                    break
                if c.can_act():
                    c._do(choose_action(c.duel, "player", rng))
                c.update(5.0)
            for _ in range(5):
                c.update(1.0)
            return rc, ui
        else:
            raise SystemExit(f"cena desconhecida: {name} (use: {', '.join(RUN_SCENES)})")
    return None


def _until(rc: RunController, rng: Random, done, prefer: set[str] = frozenset(),
           limit: int = 60) -> bool:
    for _ in range(limit):
        if done(rc):
            return True
        if rc.screen == "finished":
            return False
        pref = next((i for i in rc.available_ids() if i in prefer), None) if rc.screen == "map" else None
        step(rc, rng, pref)
    return done(rc)
