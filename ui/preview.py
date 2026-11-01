"""Previa de ataque/carta do duelo (pura, sem pygame): qual alvo esta sob o mouse e o `Preview`
do core para ele. So chama `preview_attack`/`preview_card` (nada de regra aqui). O resultado fica
em cache no controlador, por (rev da acao, selecao, alvo): so recalcula quando o alvo muda.
"""
from __future__ import annotations

from core.duel import preview_attack, preview_card
from core.types import IllegalAction, Preview
from ui import layout as L
from ui.controller import Controller


def hovered(ctrl: Controller, pos: tuple[int, int]) -> tuple[str, tuple] | None:
    """(lado, alvo) valido sob `pos` para a selecao atual, ou None. Alvo = ("slot", n) | ("leader",)."""
    if not ctrl.can_act() or ctrl.sel is None or ctrl.confirming:
        return None
    elem = L.hit_test(pos, len(ctrl.shown.me.hand))
    if elem is None:
        return None
    if elem[0] == "slot":
        side, target = elem[1], ("slot", elem[2])
        ok = ctrl.slot_target(side, elem[2]) is not None
    elif elem[0] == "leader":
        side, target = elem[1], ("leader",)
        ok = ctrl.leader_target(side) is not None
    else:
        return None
    return (side, target) if ok else None


def _compute(ctrl: Controller, target: tuple) -> Preview | None:
    sel = ctrl.sel
    try:
        if sel[0] == "slot":
            return preview_attack(ctrl.duel, sel[1], target)
        if sel[0] == "enter":
            return preview_card(ctrl.duel, sel[1], target, slot=sel[2])
        return preview_card(ctrl.duel, sel[1], target)
    except IllegalAction:
        return None


def current(ctrl: Controller, pos: tuple[int, int]) -> Preview | None:
    """Previa do alvo sob o mouse (cache por rev, selecao e alvo)."""
    got = hovered(ctrl, pos)
    if got is None:
        return None
    target = got[1]
    key = (ctrl.rev, ctrl.sel, got)
    if ctrl.pv_cache is not None and ctrl.pv_cache[0] == key:
        return ctrl.pv_cache[1]
    pv = _compute(ctrl, target)
    ctrl.pv_cache = (key, pv)
    return pv
