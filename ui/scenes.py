"""Cenas prontas para verificacao sem janela (`--screenshot`). Usa so o controlador."""
from __future__ import annotations

from random import Random

from core.ai import choose_action
from ui import layout as L
from ui.controller import Controller
from ui.render import UIState

SCENES = ("inicio", "selecionado", "ataque", "final", "dado", "tooltip", "tooltip_mao", "confirmar",
          "efeito", "espirito", "chefe")


def build(ctrl: Controller, name: str) -> UIState:
    ui = UIState(t=0.2)
    if name == "dado":
        ctrl.dice_t = 1.8
        return ui
    ctrl.settle()
    if name == "inicio":
        return ui
    if name == "selecionado":
        for _ in range(40):
            if ctrl.playable:
                ctrl.click(("hand", max(ctrl.playable)))
                return ui
            ctrl.end_turn()
            ctrl.settle()
        return ui
    if name in ("ataque", "tooltip"):
        for _ in range(80):
            foes = any(fc is not None for fc in ctrl.shown.opponent.field)
            if ctrl.attackers and (foes or _ > 40):
                n = min(ctrl.attackers)
                if name == "ataque":
                    ctrl.click(("slot", "player", n))
                else:
                    ui.mouse = L.slot_rect("player", n).center
                return ui
            if ctrl.playable:
                i = min(ctrl.playable)
                s = min(ctrl.playable[i])
                ctrl.click(("hand", i))
                ctrl.click(("slot", "player", s))
            else:
                ctrl.end_turn()
            ctrl.settle()
        return ui
    if name == "tooltip_mao":
        if ctrl.shown.me.hand:
            ui.mouse = L.hand_rect(min(1, len(ctrl.shown.me.hand) - 1), len(ctrl.shown.me.hand)).center
        return ui
    if name == "confirmar":
        for _ in range(40):
            if ctrl.has_other_moves():
                ctrl.click(("pass",))
                ui.mouse = L.pass_yes_rect().center
                return ui
            ctrl.end_turn()
            ctrl.settle()
        return ui
    if name == "final":
        rng = Random(ctrl.seed + 7)
        for _ in range(3000):
            if ctrl.over:
                break
            if ctrl.can_act():
                ctrl._do(choose_action(ctrl.duel, "player", rng))
            ctrl.update(5.0)
        for _ in range(5):
            ctrl.update(1.0)
        return ui
    raise SystemExit(f"cena desconhecida: {name} (use: {', '.join(SCENES)})")
