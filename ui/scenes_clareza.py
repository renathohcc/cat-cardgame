"""Cenas de screenshot da T12.3 (clareza do duelo): previa, alvos apagados por Provocar, Passar
pulsando, registro com icones, regra do chefe e carta em foco. So usa o controlador e a API do
core (`attack_targets`, `preview_attack`): procura, jogando, um estado que mostre o caso.
`python -m ui --screenshot x.png --cena previa_gato --seed 3`."""
from __future__ import annotations

from random import Random
from typing import Callable

from core import load_content
from core.ai import choose_action
from core.duel import attack_targets, preview_attack
from ui import layout as L
from ui.controller import DATA_DIR, Controller
from ui.render import UIState

SCENES = ("previa_gato", "previa_lider", "previa_morte", "provocar", "passar", "registro",
          "regra_chefe", "foco_mao")

Setup = Callable[[Controller, UIState], bool]


def _pairs(ctrl: Controller):
    """(atacante, alvo, Preview) de cada ataque legal do jogador."""
    for n in sorted(ctrl.attackers):
        for t in attack_targets(ctrl.duel, n):
            yield n, t, preview_attack(ctrl.duel, n, t)


def _aim(ctrl: Controller, ui: UIState, n: int, target: tuple) -> None:
    ctrl.click(("slot", "player", n))
    rect = L.leader_rect("enemy") if target[0] == "leader" else L.slot_rect("enemy", target[1])
    ui.mouse = rect.center


def _attack_scene(want: Callable[[tuple], bool]) -> Setup:
    def go(ctrl: Controller, ui: UIState) -> bool:
        for n, t, pv in _pairs(ctrl):
            if want((t, pv)):
                _aim(ctrl, ui, n, t)
                return True
        return False
    return go


def _gato(item: tuple) -> bool:
    t, pv = item
    own = [c for c in pv.cats if c.side == "player"]
    return t[0] == "slot" and not any(c.dies for c in pv.cats) and bool(own)


def _lider(item: tuple) -> bool:
    return item[0][0] == "leader"


def _morte(item: tuple) -> bool:
    t, pv = item
    return t[0] == "slot" and any(c.dies and c.side == "enemy" for c in pv.cats)


def _provocar(ctrl: Controller, ui: UIState) -> bool:
    if not (ctrl.attackers and ctrl.taunt_in_way()):
        return False
    others = [n for n, fc in enumerate(ctrl.shown.opponent.field)
              if fc is not None and "provocar" not in fc.keywords]
    if not others:
        return False
    ctrl.click(("slot", "player", min(ctrl.attackers)))
    ui.mouse = (L.field_rect("enemy").centerx, L.CENTER_Y)
    return True


def _passar(ctrl: Controller, ui: UIState) -> bool:
    return ctrl.pass_only and any(fc is not None for fc in ctrl.shown.me.field)


def _registro(ctrl: Controller, ui: UIState) -> bool:
    from ui.render import log_rows
    seen = {r[2] for r in log_rows(ctrl, L.log_rect().w - 18, (L.log_rect().h - 26) // 14)}
    return {"attack", "damage", "skull"} <= seen and ctrl.can_act()


def _foco(ctrl: Controller, ui: UIState) -> bool:
    n = len(ctrl.shown.me.hand)
    if n < 6:
        return False
    ui.mouse = L.hand_rect(n - 2, n).center
    return True


_SETUPS: dict[str, Setup] = {
    "previa_gato": _attack_scene(_gato), "previa_lider": _attack_scene(_lider),
    "previa_morte": _attack_scene(_morte), "provocar": _provocar, "passar": _passar,
    "registro": _registro, "foco_mao": _foco,
}


def _search(ctrl: Controller, ui: UIState, setup: Setup) -> bool:
    rng = Random(ctrl.seed + 11)
    for _ in range(260):
        if ctrl.over:
            return False
        if ctrl.can_act():
            if setup(ctrl, ui):
                return True
            ctrl._do(choose_action(ctrl.duel, "player", rng))
        ctrl.update(5.0)
    return False


def _controller(content, seed: int, scene: str, enemy: str | None) -> Controller:
    if scene == "regra_chefe":
        return Controller(content, seed, enemy_id=enemy or "madame-fifi-pelucia")
    if scene in ("provocar", "registro") and enemy is None:
        return Controller(content, seed, enemy_id="madame-fifi-pelucia")
    if enemy:
        return Controller(content, seed, enemy_id=enemy)
    return Controller(content, seed, enemy_random=True)


def setup(seed: int, scene: str, enemy: str | None = None) -> tuple[Controller, UIState]:
    """Controlador e UIState prontos para a cena (tenta seeds seguidos ate o caso existir)."""
    from ui.render import draw_frame
    import pygame
    content = load_content(DATA_DIR)
    for s in range(seed, seed + 80):
        ctrl, ui = _controller(content, s, scene, enemy), UIState(t=0.2)
        ctrl.settle()
        ctrl.intro_t = None
        if scene == "regra_chefe":
            ui.mouse = L.rule_rect().center
            return ctrl, ui
        if _search(ctrl, ui, _SETUPS[scene]):
            if scene == "foco_mao":                 # deixa o foco da mao chegar ao fim
                from ui.render import board_surface
                board_surface()
                draw_frame(pygame.Surface((960, 540)), ctrl, ui)
                ui.t += 1.0
            return ctrl, ui
    raise SystemExit(f"não consegui montar a cena {scene} com seed {seed}")
