"""CLI jogavel do duelo (unico lugar do core que usa print/input).

Uso: python -m core.cli [--seed N] [--primeiro player|enemy|dado] [--auto]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from random import Random
from typing import Callable, TextIO

from core import load_content, roll_cat
from core.ai import choose_action
from core.duel import apply_action, legal_actions, new_duel, view
from core.types import (
    Attack, Attacked, CatDied, CatPlayed, Cat, Content, DamageDealt, Deadlock,
    DeckSpec, DiceRolled, Drew, DrawSkipped, Duel, DuelEnded, EndTurn, Event,
    Healed, IllegalAction, LeaderDamaged, PlayCat, TurnStarted, FieldCat, Card,
)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
MAX_ACTIONS = 5000
NAMES = {"player": "Você", "enemy": "Inimigo"}
SEXO = {"M": "♂", "F": "♀"}

HELP = """Comandos:
  j <carta> <slot>   jogar a carta (numero da mao) no slot livre (1-5)
  a <slot> <alvo>    atacar com seu gato do <slot>; alvo = slot inimigo (1-5) ou 'l' (Lider)
  p                  passar o turno
  ?                  esta ajuda
  s                  sair"""


# ------------------------------------------------------------------ montagem
class Roster:
    """Liga Card.ref ao Cat de origem (para mostrar IV, natureza e sexo)."""

    def __init__(self) -> None:
        self.cats: dict[str, Cat] = {}


def build_deck(content: Content, rng: Random, prefix: str, roster: Roster) -> DeckSpec:
    cats = []
    for i in range(content.rules["duel"]["deck_size"]):
        cat = roll_cat(content, rng)
        cat.id = f"{prefix}{i + 1}"
        roster.cats[cat.id] = cat
        cats.append(cat)
    return DeckSpec(cats=cats)


def stars(n: int) -> str:
    return "★" * n


# ------------------------------------------------------------------ render
def _kw(content: Content, keywords: tuple[str, ...]) -> str:
    return ",".join(content.keywords[k]["nome"] for k in keywords)


def _field_line(content: Content, slot: int, fc: FieldCat | None, mine: bool,
                can_attack: bool) -> str:
    if fc is None:
        return f"  [{slot + 1}] (vazio)"
    kws = _kw(content, fc.keywords)
    taunt = "provocar" in fc.keywords
    parts = [f"  [{slot + 1}] {fc.card.name}  ATK {fc.atk}  HP {fc.hp}/{fc.hp_max}"]
    if kws:
        parts.append(f"<{kws}>")
    if taunt:
        parts.append("<<< PROVOCAR >>>")
    if mine:
        parts.append("pode atacar" if fc.ready and can_attack else "(sem ataque)")
    return "  ".join(parts)


def _hand_line(content: Content, idx: int, card: Card, roster: Roster | None,
               energy: int) -> str:
    kws = _kw(content, card.keywords)
    line = f"  ({idx + 1}) {card.name}  custo {card.cost}  ATK {card.atk}  HP {card.hp}"
    if kws:
        line += f"  <{kws}>"
    cat = roster.cats.get(card.ref) if roster else None
    if cat is not None:
        nat = content.natures[cat.nature]["nome"]
        line += (f"  ATK {stars(cat.iv_atk)} HP {stars(cat.iv_hp)}  {nat} {SEXO.get(cat.sex, cat.sex)}")
    if card.cost > energy:
        line += "  (energia insuficiente)"
    return line


def render(duel: Duel, side: str = "player", roster: Roster | None = None) -> str:
    """Texto da mesa do ponto de vista de `side`. Pura: sem input/print."""
    v = view(duel, side)
    c = duel.content
    hand_max = c.rules["duel"]["hand_max"]
    energy_max = c.rules["duel"]["energy_cap"]
    can_atk = duel.winner is None and any(
        isinstance(a, Attack) for a in legal_actions(duel)) if v.turn_side == side else False
    lines = ["=" * 60,
             f"Líder inimigo: {v.opponent.leader_hp} HP   |   Seu Líder: {v.me.leader_hp} HP",
             f"Inimigo: deck {v.opponent.deck_count}, mão {v.opponent.hand_count}",
             "Campo inimigo:"]
    for i, fc in enumerate(v.opponent.field):
        lines.append(_field_line(c, i, fc, False, False))
    lines.append("Seu campo:")
    for i, fc in enumerate(v.me.field):
        lines.append(_field_line(c, i, fc, True, can_atk))
    lines.append(f"Energia: {v.me.energy} (máx {energy_max})   Seu deck: {v.me.deck_count}   "
                 f"Mão: {len(v.me.hand or [])}/{hand_max}")
    if len(v.me.hand or []) >= hand_max:
        lines.append("Mão cheia: a compra foi pulada.")
    lines.append("Sua mão:")
    if not v.me.hand:
        lines.append("  (vazia)")
    for i, card in enumerate(v.me.hand or []):
        lines.append(_hand_line(c, i, card, roster, v.me.energy))
    return "\n".join(lines)


# ------------------------------------------------------------------ narracao
def _target_text(duel: Duel, side: str, target: tuple) -> str:
    foe = "enemy" if side == "player" else "player"
    if target[0] == "leader":
        return f"o Líder de {NAMES[foe]}"
    return f"slot {target[1] + 1} de {NAMES[foe]}"


def narrate(duel: Duel, ev: Event, hidden_draw: str | None = "enemy") -> str | None:
    """Uma linha de texto para o evento (None = nao mostrar)."""
    if isinstance(ev, DiceRolled):
        return f"Dado inicial: {NAMES[ev.first]} começa."
    if isinstance(ev, DrawSkipped):
        return "Mão cheia: a compra foi pulada." if ev.side == "player" else \
            "Inimigo está com a mão cheia: a compra foi pulada."
    if isinstance(ev, Deadlock):
        p = ev.powers
        return (f"IMPASSE: ninguém tem cartas. Os Líderes se enfrentam "
                f"(poder Você {p['player']}, Inimigo {p['enemy']}); começa {NAMES[ev.first]}.")
    if isinstance(ev, TurnStarted):
        return f"--- Turno {ev.turn} de {NAMES[ev.side]} (energia {ev.energy}) ---"
    if isinstance(ev, Drew):
        return f"Você comprou {ev.card.name}." if ev.side == "player" else None
    if isinstance(ev, CatPlayed):
        return f"{NAMES[ev.side]} jogou {ev.card.name} no slot {ev.slot + 1}."
    if isinstance(ev, Attacked):
        att = duel.sides[ev.side].field[ev.attacker_slot]
        who = att.card.name if att else f"slot {ev.attacker_slot + 1}"
        return f"{NAMES[ev.side]}: {who} (slot {ev.attacker_slot + 1}) atacou {_target_text(duel, ev.side, ev.target)}."
    if isinstance(ev, DamageDealt):
        return f"  {ev.amount} de dano no gato do slot {ev.slot + 1} de {NAMES[ev.side]} (HP {ev.hp_left})."
    if isinstance(ev, Healed):
        return f"  Robusto: gato do slot {ev.slot + 1} de {NAMES[ev.side]} curou {ev.amount} (HP {ev.hp_left})."
    if isinstance(ev, CatDied):
        return f"  {ev.card.name} de {NAMES[ev.side]} morreu."
    if isinstance(ev, LeaderDamaged):
        return f"  Líder de {NAMES[ev.side]} levou {ev.amount} de dano (HP {ev.hp_left})."
    if isinstance(ev, DuelEnded):
        return None
    return None


def summary(duel: Duel) -> str:
    p, e = duel.sides["player"], duel.sides["enemy"]
    head = "VITÓRIA! Você venceu o duelo." if duel.winner == "player" else \
        "DERROTA. O inimigo venceu o duelo."
    return (f"{head}\nResumo: Líder seu {p.leader_hp} HP, inimigo {e.leader_hp} HP; "
            f"turnos seus {p.turns_taken}, do inimigo {e.turns_taken}.")


# ------------------------------------------------------------------ entrada
def parse_command(duel: Duel, line: str) -> tuple[str, object]:
    """Interpreta a linha. Retorna (tipo, valor): ('action', Action), ('help', None),
    ('quit', None) ou ('error', mensagem). Nao altera o duelo."""
    parts = line.strip().lower().split()
    if not parts:
        return "error", "Digite um comando (? para ajuda)."
    cmd, args = parts[0], parts[1:]
    me = duel.sides[duel.turn_side]
    if cmd == "?":
        return "help", None
    if cmd == "s":
        return "quit", None
    if cmd == "p":
        return "action", EndTurn()
    if cmd == "j":
        if len(args) != 2 or not all(a.isdigit() for a in args):
            return "error", "Uso: j <carta> <slot>  (ex.: j 1 3)"
        hi, slot = int(args[0]) - 1, int(args[1]) - 1
        if not 0 <= hi < len(me.hand):
            return "error", f"Carta {args[0]} não existe na sua mão."
        if not 0 <= slot < len(me.field):
            return "error", f"Slot {args[1]} inválido (1 a {len(me.field)})."
        if me.field[slot] is not None:
            return "error", f"O slot {slot + 1} está ocupado."
        card = me.hand[hi]
        if card.cost > me.energy:
            return "error", f"Energia insuficiente: {card.name} custa {card.cost}, você tem {me.energy}."
        return "action", PlayCat(hi, slot)
    if cmd == "a":
        if len(args) != 2:
            return "error", "Uso: a <slot> <alvo>  (alvo = slot inimigo ou 'l' para o Líder)"
        if not args[0].isdigit() or not (args[1].isdigit() or args[1] == "l"):
            return "error", "Uso: a <slot> <alvo>  (ex.: a 1 2  ou  a 1 l)"
        slot = int(args[0]) - 1
        if not 0 <= slot < len(me.field) or me.field[slot] is None:
            return "error", f"Você não tem gato no slot {args[0]}."
        foe = duel.sides["enemy" if duel.turn_side == "player" else "player"]
        if args[1] == "l":
            target: tuple = ("leader",)
        else:
            t = int(args[1]) - 1
            if not 0 <= t < len(foe.field) or foe.field[t] is None:
                return "error", f"Não há gato inimigo no slot {args[1]}."
            target = ("slot", t)
        act = Attack(slot, target)
        if act not in legal_actions(duel):
            if not me.field[slot].ready:
                return "error", "Esse gato não pode atacar agora."
            if any("provocar" in f.keywords for f in foe.field if f):
                return "error", "Há um gato com Provocar: ataque-o primeiro."
            return "error", "Ataque não permitido agora (o 1º turno de quem começa não ataca)."
        return "action", act
    return "error", f"Comando desconhecido '{cmd}'. Digite ? para ajuda."


def list_legal(duel: Duel) -> str:
    plays: dict[int, list[int]] = {}
    atks: dict[int, list[str]] = {}
    for a in legal_actions(duel):
        if isinstance(a, PlayCat):
            plays.setdefault(a.hand_index, []).append(a.slot + 1)
        elif isinstance(a, Attack):
            atks.setdefault(a.attacker_slot, []).append(
                "l" if a.target[0] == "leader" else str(a.target[1] + 1))
    out = [f"j {h + 1} [slots {','.join(map(str, s))}]" for h, s in plays.items()]
    out += [f"a {s + 1} [alvos {','.join(t)}]" for s, t in atks.items()]
    return "Ações: " + "; ".join(out + ["p (passar)"])


# ------------------------------------------------------------------ laco
Out = Callable[[str], None]


def _apply(duel: Duel, action, out: Out) -> None:
    # Attacked precisa do gato ainda vivo: narra com o estado anterior.
    pre = _snapshot_names(duel)
    events = apply_action(duel, action)
    for ev in events:
        if isinstance(ev, Attacked):
            who = pre.get((ev.side, ev.attacker_slot), f"slot {ev.attacker_slot + 1}")
            out(f"{NAMES[ev.side]}: {who} (slot {ev.attacker_slot + 1}) atacou "
                f"{_target_text(duel, ev.side, ev.target)}.")
            continue
        text = narrate(duel, ev)
        if text:
            out(text)


def _snapshot_names(duel: Duel) -> dict[tuple[str, int], str]:
    return {(s, i): fc.card.name for s, st in duel.sides.items()
            for i, fc in enumerate(st.field) if fc is not None}


def play(content: Content, seed: int, primeiro: str, auto: bool,
         inp: Callable[[], str] | None, out: Out) -> Duel | None:
    """Joga o duelo. Retorna o Duel (None nao ocorre); `inp` devolve uma linha
    (levanta EOFError no fim). Sem print/input: tudo via `out`/`inp`."""
    rng = Random(seed)
    roster = Roster()
    pdeck = build_deck(content, rng, "p", roster)
    edeck = build_deck(content, rng, "e", roster)
    first = {"player": True, "enemy": False, "dado": None}[primeiro]
    duel = new_duel(content, rng, pdeck, edeck, first)
    ai_rng = Random(seed + 1)
    ai_rng2 = Random(seed + 2)
    out(f"Seed: {seed}  (repita com --seed {seed})")
    if first is not None:
        out(f"{NAMES[duel.first_side]} começa.")
    for ev in duel.log:
        t = narrate(duel, ev)
        if t:
            out(t)
    if not auto:
        out("Digite ? para ajuda.")
    n = 0
    while duel.winner is None and n < MAX_ACTIONS:
        n += 1
        side = duel.turn_side
        if auto:
            rg = ai_rng if side == "enemy" else ai_rng2
            _apply(duel, choose_action(duel, side, rg), out)
            continue
        if side == "enemy":
            _apply(duel, choose_action(duel, "enemy", ai_rng), out)
            continue
        out(render(duel, "player", roster))
        out(list_legal(duel))
        try:
            line = inp() if inp else ""
        except EOFError:
            out("Entrada encerrada. Saindo.")
            return duel
        kind, val = parse_command(duel, line)
        if kind == "quit":
            out("Você saiu do duelo.")
            return duel
        if kind == "help":
            out(HELP)
        elif kind == "error":
            out(f"! {val}")
        else:
            try:
                _apply(duel, val, out)
            except IllegalAction as e:
                out(f"! Ação ilegal: {e}")
    if duel.winner is not None:
        out(summary(duel))
    else:
        out("Duelo interrompido (limite de ações).")
    return duel


def main(argv: list[str] | None = None, stdin: TextIO | None = None,
         stdout: TextIO | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m core.cli", description="Duelo de gatos no terminal.")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--primeiro", choices=["player", "enemy", "dado"], default="dado")
    ap.add_argument("--auto", action="store_true", help="IA contra IA")
    args = ap.parse_args(argv)
    if stdout is None and hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sin, sout = stdin or sys.stdin, stdout or sys.stdout
    seed = args.seed if args.seed is not None else Random().randrange(1, 10**6)
    content = load_content(DATA_DIR)

    def out(s: str) -> None:
        print(s, file=sout)

    def inp() -> str:
        print("> ", end="", file=sout, flush=True)
        line = sin.readline()
        if line == "":
            raise EOFError
        return line

    play(content, seed, args.primeiro, args.auto, inp, out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
