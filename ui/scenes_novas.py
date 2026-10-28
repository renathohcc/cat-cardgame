"""Cenas de screenshot da T3.4 (efeito, espirito, chefe). Usa so o controlador."""
from __future__ import annotations

from random import Random

from core import load_content, roll_cat
from core.ai import choose_action
from core.duel import card_from_effect, card_from_special
from core.types import DeckSpec, EndTurn, PlayCat
from ui import layout as L
from ui.controller import DATA_DIR, Controller
from ui.render import UIState

NEW_SCENES = ("efeito", "espirito", "chefe")


def _spec(content, seed: int, effects: tuple[str, ...], specials: tuple[str, ...]) -> DeckSpec:
    """Deck de 12: gatos sorteados + as cartas pedidas."""
    rng = Random(seed)
    cards = [card_from_effect(content, e) for e in effects] + \
            [card_from_special(content, e) for e in specials]
    cats = []
    for i in range(12 - len(cards)):
        c = roll_cat(content, rng)
        c.id = f"p{i + 1}"
        cats.append(c)
    return DeckSpec(cats=cats, cards=cards)


def _hand_index(ctrl: Controller, ref: str) -> int | None:
    for i, c in enumerate(ctrl.shown.me.hand):
        if c.ref == ref:
            return i
    return None


def _step(ctrl: Controller) -> None:
    """Joga so gatos (nunca as cartas do cenario) ou passa o turno."""
    for a in ctrl.legal:
        if (isinstance(a, PlayCat) and a.target is None
                and ctrl.shown.me.hand[a.hand_index].kind == "cat"):
            ctrl._do(a)
            break
    else:
        ctrl._do(EndTurn())
    ctrl.settle()


def _foes(ctrl: Controller) -> bool:
    return any(fc is not None for fc in ctrl.shown.opponent.field)


def make(seed: int, name: str, enemy_id: str | None = None) -> Controller | None:
    """Controlador pronto para a cena, tentando seeds seguidos ate o cenario existir."""
    content = load_content(DATA_DIR)
    for s in range(seed, seed + 60):
        if name == "chefe":
            ctrl = Controller(content, s, enemy_id=enemy_id or "madame-fifi-pelucia")
        elif name == "efeito":
            spec = _spec(content, s, ("rugido-de-guerra", "arranhao-certeiro",
                                      "lambida-curativa", "soneca-no-sol", "petisco-surpresa"),
                         ("sombra-miuda",))
            ctrl = Controller(content, s, enemy_id=enemy_id or "irmaos-pimenta", player_spec=spec)
        elif name == "espirito":
            spec = _spec(content, s, ("rugido-de-guerra",),
                         ("trovao-amarelo", "trovao-amarelo", "guardiao-bigodudo",
                          "velha-dos-novelos"))
            ctrl = Controller(content, s, enemy_id=enemy_id or "tonho-sem-sorte", player_spec=spec)
        else:
            return None
        ctrl.settle()
        if _arrange(ctrl, name):
            return ctrl
    return None


def _arrange(ctrl: Controller, name: str) -> bool:
    if name == "chefe":
        return _chefe(ctrl)
    for _ in range(40):
        if ctrl.over:
            return False
        if ctrl.can_act() and (_efeito(ctrl) if name == "efeito" else _espirito(ctrl)):
            return True
        _step(ctrl)
    return False


def _efeito(ctrl: Controller) -> bool:
    rug, arr = _hand_index(ctrl, "rugido-de-guerra"), _hand_index(ctrl, "arranhao-certeiro")
    mine = next((n for n, fc in enumerate(ctrl.shown.me.field) if fc), None)
    if rug is None or arr is None or mine is None or not _foes(ctrl):
        return False
    if ctrl.shown.me.energy < 3 or rug not in ctrl.playable or arr not in ctrl.playable:
        return False
    ctrl.click(("hand", rug))
    ctrl.click(("slot", "player", mine))               # buff de ATK no gato
    ctrl.settle()
    arr = _hand_index(ctrl, "arranhao-certeiro")
    if arr is None or arr not in ctrl.playable or not ctrl.can_act():
        return False
    ctrl.click(("hand", arr))
    return True


def _espirito(ctrl: Controller) -> bool:
    i = _hand_index(ctrl, "trovao-amarelo")
    if i is None or i not in ctrl.playable or not _foes(ctrl):
        return False
    ctrl.click(("hand", i))
    ctrl.click(("slot", "player", min(ctrl.playable[i])))
    return ctrl.sel is not None and ctrl.sel[0] == "enter"


def _chefe(ctrl: Controller) -> bool:
    rng = Random(ctrl.seed)
    for _ in range(400):
        if ctrl.over or (ctrl.duel.sides["enemy"].turns_taken >= 4 and ctrl.can_act()):
            break
        if ctrl.can_act():
            ctrl._do(choose_action(ctrl.duel, "player", rng))
        ctrl.update(5.0)
    return not ctrl.over


def build(ctrl: Controller, name: str) -> UIState:
    ui = UIState(t=0.2)
    if name == "chefe":
        ui.mouse = L.leader_rect("enemy").move(40, 0).center
    return ui
