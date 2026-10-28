"""IA inimiga simples. Puro; so usa o `rng` recebido (desempates)."""
from __future__ import annotations

from random import Random

from core.duel import legal_actions
from core.types import (
    Action, Attack, Card, Duel, EndTurn, FieldCat, PlayCat, PlayEffect, Side, other,
)

__all__ = ["choose_action"]

# Depois deste numero de turnos proprios a IA ataca mesmo se for suicida
# (garante que o duelo termina). Constante de heuristica, nao de design.
PATIENCE_TURNS = 10


def _damage(fc: FieldCat) -> int:
    return fc.atk * (2 if "primeira-patada" in fc.keywords and not fc.used_first_strike else 1)


def _score(duel: Duel, side: str, atk_slot: int, target: tuple, bonus: int = 0) -> int:
    me = duel.sides[side]
    foe = duel.sides[other(side)]
    att = me.field[atk_slot]
    dmg = _damage(att) + bonus * (2 if "primeira-patada" in att.keywords
                                  and not att.used_first_strike else 1)
    if target[0] == "leader":
        return 1000 if dmg >= foe.leader_hp else 30 + dmg
    d = foe.field[target[1]]
    kills = dmg >= d.hp
    dies = d.atk >= att.hp
    if kills and not dies:
        return 100 + d.atk + d.card.cost
    if kills and dies:
        return 50 + d.card.cost - att.card.cost
    if not dies:
        return 10 + dmg
    return -100


# ------------------------------------------------------------------ efeitos
URGENT, HEAL, BUFF, UTILITY, DUMP = 100, 70, 50, 20, 5


def _effect_score(duel: Duel, side: str, card: Card, target: tuple, attacks: list[Attack],
                  hand: list[Card], energy_after: int) -> int | None:
    """Valor de jogar `card` agora no `target`; None = nao vale a pena."""
    me, foe = duel.sides[side], duel.sides[other(side)]
    cfg = duel.content.rules["duel"]
    best: int | None = None

    def offer(v: int) -> None:
        nonlocal best
        best = v if best is None else max(best, v)

    leader_dmg = sum(a["valor"] for a in card.actions
                     if a["tipo"] == "dano" and a["alvo"] == "lider_inimigo")
    if leader_dmg >= foe.leader_hp:
        return 10000
    if leader_dmg:
        offer(DUMP)
    for a in card.actions:
        tipo, alvo, v = a["tipo"], a["alvo"], a["valor"]
        if tipo == "cura":
            if alvo == "lider_proprio" and me.leader_hp * 2 < me.leader_hp_max:
                offer(HEAL + 5)
            elif alvo == "aliado_escolhido":
                fc = me.field[target[1]]
                if fc is not None and fc.hp * 2 < fc.hp_max:
                    offer(HEAL + fc.card.cost)
        elif tipo == "dano" and alvo == "inimigo_escolhido":
            d = foe.field[target[1]]
            if d is not None and v >= d.hp:
                offer(URGENT + d.card.cost + d.atk)
        elif tipo == "comprar":
            if me.deck and len(me.hand) - 1 < cfg["hand_max"]:
                offer(UTILITY)
        elif tipo == "energia":
            gain_to = min(cfg["energy_cap"], energy_after + v)
            if any(energy_after < c.cost <= gain_to for c in hand if c is not card):
                offer(UTILITY)
        elif tipo == "buff_atk" and alvo == "aliado_escolhido":
            slot = target[1]
            mine = [x for x in attacks if x.attacker_slot == slot]
            if mine and attacks:
                base = max(_score(duel, side, x.attacker_slot, x.target) for x in attacks)
                gain = max(_score(duel, side, slot, x.target, v) for x in mine)
                plain = max(_score(duel, side, slot, x.target) for x in mine)
                if gain >= 30 and gain > plain and gain >= base:
                    offer(BUFF)
    return best


def _enter_target_score(duel: Duel, side: str, card: Card, target: tuple | None) -> int:
    if target is None:
        return 0
    me, foe = duel.sides[side], duel.sides[other(side)]
    for a in card.actions:
        if a["alvo"] == "inimigo_escolhido":
            d = foe.field[target[1]]
            return (URGENT + d.card.cost + d.atk) if a["valor"] >= d.hp else d.atk
        if a["alvo"] == "aliado_escolhido":
            fc = me.field[target[1]]
            return (fc.hp_max - fc.hp) if a["tipo"] == "cura" else fc.atk
    return 0


def _pick_effect(duel: Duel, side: str, rng: Random, acts: list[Action], lo: int,
                 hi: int | None = None) -> Action | None:
    hand = duel.sides[side].hand
    energy = duel.sides[side].energy
    attacks = [a for a in acts if isinstance(a, Attack)]
    scored: list[tuple[int, Action]] = []
    for a in acts:
        if isinstance(a, PlayEffect):
            card = hand[a.hand_index]
            v = _effect_score(duel, side, card, a.target, attacks, hand, energy - card.cost)
            if v is not None and v >= lo and (hi is None or v < hi):
                scored.append((v, a))
    if not scored:
        return None
    top = max(v for v, _ in scored)
    return rng.choice([a for v, a in scored if v == top])


def choose_action(duel: Duel, side: Side, rng: Random) -> Action:
    """Heuristica: (0) efeitos urgentes (letal no Lider, dano que mata gato) e cura
    de quem esta abaixo de metade do HP; (1) joga gatos/Especiais: maior custo
    primeiro, primeiro slot livre, melhor alvo do "ao entrar"; (1b) comprar/energia
    com a energia que sobra; buff so se o beneficiado vai atacar; (2) ataca com a
    melhor dupla (atacante, alvo) pela pontuacao: letal no Lider > troca boa (mata
    e sobrevive) > troca (mata e morre) > dano ao Lider > pancada sem morrer >
    suicidio. Suicidio so depois de PATIENCE_TURNS turnos proprios (evita impasse
    eterno); (3) dano no Lider que sobrou; (4) EndTurn. Desempates via rng."""
    if duel.winner is not None or duel.turn_side != side:
        raise ValueError("nao e a vez de 'side' ou o duelo acabou")
    acts = legal_actions(duel)
    if any(isinstance(a, PlayEffect) for a in acts):
        pick = _pick_effect(duel, side, rng, acts, HEAL)
        if pick is not None:
            return pick
    hand = duel.sides[side].hand
    plays = [a for a in acts if isinstance(a, PlayCat)]
    if plays:
        best = max(hand[a.hand_index].cost for a in plays)
        top = [a for a in plays if hand[a.hand_index].cost == best]
        tscore = {id(a): _enter_target_score(duel, side, hand[a.hand_index], a.target)
                  for a in top}
        bt = max(tscore.values())
        top = [a for a in top if tscore[id(a)] == bt]
        low = min(a.slot for a in top)
        return rng.choice([a for a in top if a.slot == low])
    if any(isinstance(a, PlayEffect) for a in acts):
        pick = _pick_effect(duel, side, rng, acts, UTILITY)
        if pick is not None:
            return pick
    attacks = [a for a in acts if isinstance(a, Attack)]
    if attacks:
        scored = [(_score(duel, side, a.attacker_slot, a.target), a) for a in attacks]
        top = max(s for s, _ in scored)
        if top >= 0 or duel.sides[side].turns_taken > PATIENCE_TURNS:
            return rng.choice([a for s, a in scored if s == top])
    pick = _pick_effect(duel, side, rng, acts, DUMP)
    return pick if pick is not None else EndTurn()
