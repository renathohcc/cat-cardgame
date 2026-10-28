"""Duelo 1x1: estado, regras de combate e keywords. Puro, RNG injetado."""
from __future__ import annotations

import copy
from random import Random
from typing import Any

from core.cats import cat_stats, roll_cat
from core.content import actions_of
from core.types import (
    Action, AtkBuffed, AtkBuffExpired, Attack, Attacked, CatDied, CatPlayed, Card, Cat,
    Content, DamageDealt, Deadlock, DeckSpec, DiceRolled, Drew, DrawSkipped, Duel,
    DuelEnded, DuelView, EffectPlayed, EndTurn, EnergyChanged, Event, FieldCat, Healed,
    IllegalAction, LeaderDamaged, LeaderHealed, PlayCat, PlayEffect, Side, SideState,
    SideView, TurnStarted, Target, Winner, other,
)

__all__ = [
    "new_duel", "new_duel_vs_enemy", "enemy_deck_spec", "legal_actions", "apply_action",
    "view", "is_over", "card_from_cat", "card_from_effect", "card_from_special",
    "card_targets", "attack_targets", "keyword_info", "build_duel_for_tests", "IllegalAction",
]


def _rules(duel: Duel) -> dict[str, Any]:
    return duel.content.rules["duel"]


def card_from_cat(content: Content, cat: Cat) -> Card:
    st = cat_stats(content, cat)
    return Card(kind="cat", ref=cat.id, name=cat.name or content.breeds[cat.breed]["nome"],
                cost=st.cost, atk=st.atk, hp=st.hp,
                keywords=tuple(content.breeds[cat.breed].get("keywords", [])),
                breed=cat.breed, breed_name=content.breeds[cat.breed]['nome'],
                cat_name=cat.name, sex=cat.sex, nature=cat.nature,
                iv_atk=cat.iv_atk, iv_hp=cat.iv_hp)


def card_from_effect(content: Content, effect_id: str) -> Card:
    ef = content.effects[effect_id]
    return Card(kind="effect", ref=ef["id"], name=ef["nome"], cost=ef["custo"],
                text=ef["texto"], actions=tuple(copy.deepcopy(actions_of(ef["acoes"]))))


def card_from_special(content: Content, special_id: str) -> Card:
    sp = content.specials[special_id]
    return Card(kind="special", ref=sp["id"], name=sp["nome"], cost=sp["custo"],
                atk=sp["atk"], hp=sp["hp"], keywords=tuple(sp.get("keywords", [])),
                text=sp["texto"],
                actions=tuple(copy.deepcopy(actions_of(sp.get("efeito_ao_entrar")))))


def _cards(content: Content, spec: DeckSpec) -> list[Card]:
    for c in spec.cats:
        if c.stage != "adult":
            raise ValueError(f"deck so aceita gatos adultos (gato '{c.id}')")
    return ([card_from_cat(content, c) for c in spec.cats]
            + [copy.copy(c) for c in spec.cards])


def _side_state(rules: dict[str, Any], deck: list[Card], leader_hp: int | None = None,
                rule: dict[str, Any] | None = None) -> SideState:
    hp = rules["leader_hp"] if leader_hp is None else leader_hp
    return SideState(leader_hp=hp, leader_hp_max=hp,
                     deck=list(deck), hand=[], field=[None] * rules["slots"],
                     initial_deck=list(deck), rule=copy.deepcopy(rule))


# ------------------------------------------------------------------ criacao
def new_duel(content: Content, rng: Random, player: DeckSpec, enemy: DeckSpec,
             player_first: bool | None = None) -> Duel:
    rules = content.rules["duel"]
    pc, ec = _cards(content, player), _cards(content, enemy)
    sides = {"player": _side_state(rules, pc, player.leader_hp, player.rule),
             "enemy": _side_state(rules, ec, enemy.leader_hp, enemy.rule)}
    rng.shuffle(sides["player"].deck)
    rng.shuffle(sides["enemy"].deck)
    log: list[Event] = []
    if player_first is None:
        player_first = rng.random() < 0.5
        first = "player" if player_first else "enemy"
        log.append(DiceRolled(first))
    first = "player" if player_first else "enemy"
    duel = Duel(content=content, rng=rng, sides=sides, turn_side=first, first_side=first)
    for side in ("player", "enemy"):
        for _ in range(rules["initial_hand"]):
            _draw(duel, side, log, skip_if_full=True)
    _start_turn(duel, first, log)
    _check_deadlock(duel, log)
    duel.log.extend(log)
    return duel


def enemy_deck_spec(content: Content, enemy_id: str, rng: Random) -> DeckSpec:
    """DeckSpec de um inimigo de data/enemies.json (`rng` so sorteia IVs omitidos)."""
    if enemy_id not in content.enemies:
        raise ValueError(f"inimigo inexistente: '{enemy_id}'")
    en = content.enemies[enemy_id]
    cats: list[Cat] = []
    cards: list[Card] = []
    n = 0
    for entry in en["deck"]:
        cid = entry["carta"]
        for _ in range(entry["qtd"]):
            if cid in content.breeds:
                if "iv_atk" in entry:
                    cat = Cat(id="", breed=cid, sex="M" if n % 2 == 0 else "F",
                              nature=entry["nature"], iv_atk=entry["iv_atk"],
                              iv_hp=entry["iv_hp"])
                else:
                    cat = roll_cat(content, rng, cid)
                cat.id = f"{enemy_id}-{n}"
                cats.append(cat)
            elif cid in content.specials:
                cards.append(card_from_special(content, cid))
            else:
                cards.append(card_from_effect(content, cid))
            n += 1
    return DeckSpec(cats=cats, cards=cards, leader_hp=en.get("lider_hp"),
                    rule=copy.deepcopy(en.get("regra_propria")))


def new_duel_vs_enemy(content: Content, player: DeckSpec, enemy_id: str, rng: Random,
                      player_first: bool | None = None) -> Duel:
    """Duelo do jogador contra um inimigo de enemies.json (Lider/regra propria incluidos)."""
    return new_duel(content, rng, player, enemy_deck_spec(content, enemy_id, rng),
                    player_first)


# ------------------------------------------------------------------ helpers
def _draw(duel: Duel, side: str, log: list[Event], skip_if_full: bool = True) -> None:
    st = duel.sides[side]
    if not st.deck:
        return
    if len(st.hand) >= _rules(duel)["hand_max"]:
        log.append(DrawSkipped(side))
        return
    card = st.deck.pop(0)
    st.hand.append(card)
    log.append(Drew(side, card))


def _turn_energy(rules: dict[str, Any], n: int, is_first: bool = False) -> int:
    """Energia do n-esimo turno do lado; `is_first` = lado que comecou o duelo.

    `first_player_energy_start` vale SO no 1o turno de quem comeca (curva 1, 3, 4...);
    dos turnos seguintes em diante a curva e a comum.
    """
    start = rules["energy_start"]
    if is_first and n == 1:
        start = rules.get("first_player_energy_start", start)
    return min(rules["energy_cap"], start + (n - 1) * rules["energy_per_turn"])


def _start_turn(duel: Duel, side: str, log: list[Event]) -> None:
    rules = _rules(duel)
    st = duel.sides[side]
    duel.turn_side = side
    st.turns_taken += 1
    st.energy = _turn_energy(rules, st.turns_taken, side == duel.first_side)
    for fc in st.field:
        if fc is not None:
            fc.ready = True
            fc.attacked = False
    log.append(TurnStarted(side, st.turns_taken, st.energy))
    log.append(EnergyChanged(side, st.energy))
    if st.rule is not None:
        _run_actions(duel, side, actions_of(st.rule.get("acao", st.rule.get("acoes"))),
                     None, log)
    if st.turns_taken > 1 or rules["draw_on_first_turn"]:
        for _ in range(rules["draw_per_turn"]):
            _draw(duel, side, log)


def _taunt_slots(st: SideState) -> list[int]:
    return [i for i, fc in enumerate(st.field) if fc is not None and "provocar" in fc.keywords]


def _can_attack_now(duel: Duel) -> bool:
    rules = _rules(duel)
    st = duel.sides[duel.turn_side]
    if (rules["first_player_no_attack_first_turn"] and duel.turn_side == duel.first_side
            and st.turns_taken == 1):
        return False
    return True


# ------------------------------------------------------------------ consulta
def legal_actions(duel: Duel) -> list[Action]:
    if duel.winner is not None:
        return []
    side = duel.turn_side
    me, foe = duel.sides[side], duel.sides[other(side)]
    acts: list[Action] = []
    free = [i for i, fc in enumerate(me.field) if fc is None]
    for hi, card in enumerate(me.hand):
        if card.cost > me.energy:
            continue
        if card.kind == "effect":
            acts.extend(PlayEffect(hi, t) for t in _effect_targets(duel, side, card))
        elif card.kind in ("cat", "special"):
            ts = _enter_targets(duel, side, card)
            acts.extend(PlayCat(hi, s, t) for s in free for t in ts)
    if _can_attack_now(duel):
        taunts = _taunt_slots(foe)
        if taunts:
            targets = [("slot", i) for i in taunts]
        else:
            targets = [("slot", i) for i, fc in enumerate(foe.field) if fc is not None]
            targets.append(("leader",))
        for si, fc in enumerate(me.field):
            if fc is not None and fc.ready:
                acts.extend(Attack(si, t) for t in targets)
    acts.append(EndTurn())
    return acts


def _choice_targets(duel: Duel, owner: str, actions: tuple | list) -> list[Target] | None:
    """None = as acoes nao pedem escolha; lista = gatos-alvo validos (pode ser vazia)."""
    for a in actions:
        if a["alvo"] in ("inimigo_escolhido", "aliado_escolhido"):
            side = other(owner) if a["alvo"] == "inimigo_escolhido" else owner
            return [("slot", i) for i, fc in enumerate(duel.sides[side].field)
                    if fc is not None]
    return None


def _effect_targets(duel: Duel, owner: str, card: Card) -> list[Target]:
    ts = _choice_targets(duel, owner, card.actions)
    return [("leader",)] if ts is None else ts


def _enter_targets(duel: Duel, owner: str, card: Card) -> list[Target | None]:
    """Alvos do "ao entrar"; [None] se nao ha escolha ou nao ha alvo valido (efeito perdido)."""
    ts = _choice_targets(duel, owner, card.actions) if card.kind == "special" else None
    return list(ts) if ts else [None]


def card_targets(duel: Duel, hand_index: int) -> list[Target]:
    """Alvos escolhiveis para a carta da mao do jogador da vez (vazio = sem escolha
    ou nao jogavel); derivado de legal_actions."""
    out: list[Target] = []
    for a in legal_actions(duel):
        if isinstance(a, PlayEffect) and a.hand_index == hand_index and a.target not in out:
            out.append(a.target)
        elif (isinstance(a, PlayCat) and a.hand_index == hand_index
              and a.target is not None and a.target not in out):
            out.append(a.target)
    return out


def attack_targets(duel: Duel, attacker_slot: int) -> list[Target]:
    """Alvos legais do gato em `attacker_slot` (derivado de legal_actions)."""
    return [a.target for a in legal_actions(duel)
            if isinstance(a, Attack) and a.attacker_slot == attacker_slot]


def keyword_info(content: Content, keyword_id: str) -> dict[str, Any]:
    """{'id','nome','texto',...} de uma keyword (= content.keywords[id])."""
    return content.keywords[keyword_id]


def is_over(duel: Duel) -> Winner | None:
    return duel.winner  # type: ignore[return-value]


def view(duel: Duel, side: Side) -> DuelView:
    def sv(s: str, hidden: bool) -> SideView:
        st = duel.sides[s]
        return SideView(leader_hp=st.leader_hp, energy=st.energy, deck_count=len(st.deck),
                        hand_count=len(st.hand),
                        hand=None if hidden else copy.deepcopy(st.hand),
                        field=copy.deepcopy(st.field), turns_taken=st.turns_taken,
                        leader_hp_max=st.leader_hp_max, rule=copy.deepcopy(st.rule))
    return DuelView(side=side, turn_side=duel.turn_side, winner=duel.winner,
                    me=sv(side, False), opponent=sv(other(side), True))


# ------------------------------------------------------------------ aplicar
def apply_action(duel: Duel, action: Action) -> list[Event]:
    if duel.winner is not None:
        raise IllegalAction("duelo ja terminou")
    if action not in legal_actions(duel):
        raise IllegalAction(f"acao ilegal: {action!r}")
    log: list[Event] = []
    if isinstance(action, PlayCat):
        _play_cat(duel, action, log)
    elif isinstance(action, PlayEffect):
        _play_effect(duel, action, log)
    elif isinstance(action, Attack):
        _attack(duel, action, log)
    else:
        _end_turn(duel, log)
    _stall_scan(duel, log)
    _check_deadlock(duel, log)
    duel.log.extend(log)
    return log


def _play_cat(duel: Duel, a: PlayCat, log: list[Event]) -> None:
    side = duel.turn_side
    st = duel.sides[side]
    card = st.hand.pop(a.hand_index)
    st.energy -= card.cost
    fc = FieldCat(card=card, atk=card.atk, hp=card.hp, hp_max=card.hp,
                  keywords=card.keywords, ready="investida" in card.keywords)
    st.field[a.slot] = fc
    log.append(CatPlayed(side, a.slot, card))
    log.append(EnergyChanged(side, st.energy))
    if card.kind == "special" and card.actions:
        needs_choice = any(x["alvo"].endswith("_escolhido") for x in card.actions)
        if needs_choice and a.target is None:
            return  # sem alvo valido: efeito perdido, o gato entra do mesmo jeito
        log.append(EffectPlayed(side, card, a.target if a.target is not None else ("leader",)))
        _run_actions(duel, side, card.actions, a.target, log)


def _play_effect(duel: Duel, a: PlayEffect, log: list[Event]) -> None:
    side = duel.turn_side
    st = duel.sides[side]
    card = st.hand.pop(a.hand_index)
    st.energy -= card.cost
    log.append(EffectPlayed(side, card, a.target))
    log.append(EnergyChanged(side, st.energy))
    _run_actions(duel, side, card.actions, a.target, log)


def _run_actions(duel: Duel, owner: str, actions: tuple | list, target: Target | None,
                 log: list[Event]) -> None:
    for act in actions:
        if duel.winner is not None:
            return
        _run_action(duel, owner, act, target, log)


def _heal_cat(duel: Duel, side: str, slot: int, amount: int, log: list[Event]) -> None:
    fc = duel.sides[side].field[slot]
    assert fc is not None
    gain = min(amount, fc.hp_max - fc.hp)
    if gain > 0:
        fc.hp += gain
        log.append(Healed(side, slot, gain, fc.hp))


def _heal_leader(duel: Duel, side: str, amount: int, log: list[Event]) -> None:
    st = duel.sides[side]
    gain = min(amount, st.leader_hp_max - st.leader_hp)
    if gain > 0:
        st.leader_hp += gain
        log.append(LeaderHealed(side, gain, st.leader_hp))


def _run_action(duel: Duel, owner: str, act: dict[str, Any], target: Target | None,
                log: list[Event]) -> None:
    """Executa uma acao de efeito. `target` so importa para alvos *_escolhido."""
    tipo, alvo, valor = act["tipo"], act["alvo"], act["valor"]
    me = duel.sides[owner]
    if tipo == "comprar":
        for _ in range(valor):
            _draw(duel, owner, log)
        return
    if tipo == "energia":
        me.energy = min(_rules(duel)["energy_cap"], me.energy + valor)
        log.append(EnergyChanged(owner, me.energy))
        return
    if alvo in ("lider_inimigo", "lider_proprio"):
        side = other(owner) if alvo == "lider_inimigo" else owner
        if tipo == "dano":
            _hit_leader(duel, side, valor, log)
        elif tipo == "cura":
            _heal_leader(duel, side, valor, log)
        return
    if target is None or target[0] != "slot":
        return
    side = other(owner) if alvo == "inimigo_escolhido" else owner
    slot = target[1]
    fc = duel.sides[side].field[slot]
    if fc is None:
        return
    if tipo == "dano":
        if _hit_cat(duel, side, slot, valor, log):
            _kill(duel, side, slot, log)
    elif tipo == "cura":
        _heal_cat(duel, side, slot, valor, log)
    elif tipo == "buff_atk":
        temporary = act.get("duracao") != "permanente"
        fc.atk += valor
        if temporary:
            fc.atk_bonus_turn += valor
        log.append(AtkBuffed(side, slot, valor, fc.atk, temporary))


def _finish(duel: Duel, winner: str, log: list[Event]) -> None:
    duel.winner = winner
    log.append(DuelEnded(winner))


def _hit_leader(duel: Duel, side: str, amount: int, log: list[Event]) -> None:
    st = duel.sides[side]
    st.leader_hp = max(0, st.leader_hp - amount)
    log.append(LeaderDamaged(side, amount, st.leader_hp))
    if st.leader_hp <= 0 and duel.winner is None:
        _finish(duel, other(side), log)


def _hit_cat(duel: Duel, side: str, slot: int, amount: int, log: list[Event]) -> bool:
    fc = duel.sides[side].field[slot]
    assert fc is not None
    fc.hp -= amount
    log.append(DamageDealt(side, slot, amount, max(0, fc.hp)))
    return fc.hp <= 0


def _kill(duel: Duel, side: str, slot: int, log: list[Event]) -> None:
    fc = duel.sides[side].field[slot]
    assert fc is not None
    duel.sides[side].field[slot] = None
    log.append(CatDied(side, slot, fc.card))


def _attack(duel: Duel, a: Attack, log: list[Event]) -> None:
    side = duel.turn_side
    foe_side = other(side)
    me = duel.sides[side]
    atk_cat = me.field[a.attacker_slot]
    assert atk_cat is not None
    log.append(Attacked(side, a.attacker_slot, a.target))
    atk_cat.ready = False
    atk_cat.attacked = True
    damage = atk_cat.atk
    if "primeira-patada" in atk_cat.keywords and not atk_cat.used_first_strike:
        damage *= 2
    atk_cat.used_first_strike = True
    if a.target[0] == "leader":
        _hit_leader(duel, foe_side, damage, log)
        return
    slot = a.target[1]
    defender = duel.sides[foe_side].field[slot]
    assert defender is not None
    counter = defender.atk
    atk_dies = False
    def_dies = _hit_cat(duel, foe_side, slot, damage, log)
    atk_dies = _hit_cat(duel, side, a.attacker_slot, counter, log)
    if atk_dies:
        _kill(duel, side, a.attacker_slot, log)
    if def_dies:
        _kill(duel, foe_side, slot, log)


def _end_turn(duel: Duel, log: list[Event]) -> None:
    side = duel.turn_side
    st = duel.sides[side]
    _stall_tick(duel)
    for slot, fc in enumerate(st.field):
        if fc is not None and fc.atk_bonus_turn:
            fc.atk -= fc.atk_bonus_turn
            log.append(AtkBuffExpired(side, slot, fc.atk_bonus_turn, fc.atk))
            fc.atk_bonus_turn = 0
    for slot, fc in enumerate(st.field):
        if fc is not None and "robusto" in fc.keywords:
            cura = duel.content.keywords["robusto"]["params"]["cura"]
            gain = min(cura, fc.hp_max - fc.hp)
            if gain > 0:
                fc.hp += gain
                log.append(Healed(side, slot, gain, fc.hp))
    _start_turn(duel, other(side), log)


# ------------------------------------------------------------------ impasse
def _stall_reset(duel: Duel) -> None:
    duel.stall_base, duel.stall_half, duel.stall_rounds = None, 0, 0


def _stall_scan(duel: Duel, log: list[Event]) -> None:
    """Gato jogado (inclui Espirito) ou morto reinicia a janela de estagnacao."""
    if any(isinstance(ev, (CatPlayed, CatDied)) for ev in log):
        _stall_reset(duel)


def _stall_tick(duel: Duel) -> None:
    """Chamado no fim de cada turno, antes do turno seguinte comecar.

    O 1o fim de turno apos um reinicio fixa o HP-base dos Lideres. A cada 2 fins de
    turno (uma rodada, sempre na mesma fase) compara-se o HP: menor que a base =
    perda liquida, reinicia com base nova; senao conta +1 rodada. Ao chegar em
    rules.deadlock.stall_rounds, `stall_triggered`. Sem o campo, desligado.
    """
    need = duel.content.rules["deadlock"].get("stall_rounds")
    if not need:
        return
    hp = {k: v.leader_hp for k, v in duel.sides.items()}
    if duel.stall_base is None:
        duel.stall_base, duel.stall_half, duel.stall_rounds = hp, 0, 0
        return
    duel.stall_half += 1
    if duel.stall_half % 2:
        return
    if any(hp[k] < duel.stall_base[k] for k in hp):
        duel.stall_base, duel.stall_half, duel.stall_rounds = hp, 0, 0
        return
    duel.stall_rounds += 1
    if duel.stall_rounds >= need:
        duel.stall_triggered = True


def _check_deadlock(duel: Duel, log: list[Event]) -> None:
    if duel.winner is not None:
        return
    if duel.stall_triggered:
        _resolve_deadlock(duel, log)
        return
    # Cartas de efeito restantes nao seguram o impasse: so gatos/Especiais contam.
    for st in duel.sides.values():
        if (any(c.kind != "effect" for c in st.hand)
                or any(c.kind != "effect" for c in st.deck)
                or any(fc is not None for fc in st.field)):
            return
    _resolve_deadlock(duel, log)


def _leader_power(st: SideState) -> int:
    cards = [c for c in st.initial_deck if c.kind != "effect"]
    n = len(cards)
    if n == 0:
        return 0
    total = sum(c.atk for c in cards)
    return (2 * total + n) // (2 * n)  # media arredondada, metade para cima


def _resolve_deadlock(duel: Duel, log: list[Event]) -> None:
    rng, cfg = duel.rng, duel.content.rules["deadlock"]
    s = duel.sides
    if s["player"].leader_hp != s["enemy"].leader_hp:
        cur = min(s, key=lambda k: s[k].leader_hp)
    else:
        cur = rng.choice(["player", "enemy"])
    power = {k: _leader_power(v) for k, v in s.items()}
    log.append(Deadlock(dict(power), cur))
    while duel.winner is None:
        dmg = max(cfg["min_damage"], power[cur] + rng.choice(cfg["variation"]))
        _hit_leader(duel, other(cur), dmg, log)
        cur = other(cur)


# ------------------------------------------------------------------ testes
def build_duel_for_tests(
    content: Content, rng: Random | None = None, *, turn_side: str = "player",
    player_hand: list[Cat | Card] | None = None, enemy_hand: list[Cat | Card] | None = None,
    player_deck: list[Cat | Card] | None = None, enemy_deck: list[Cat | Card] | None = None,
    player_field: dict[int, Cat | Card | FieldCat] | None = None,
    enemy_field: dict[int, Cat | Card | FieldCat] | None = None,
    player_energy: int | None = None, enemy_energy: int | None = None,
    player_leader_hp: int | None = None, enemy_leader_hp: int | None = None,
    first_turn: bool = False,
) -> Duel:
    """Monta um Duel em cenario controlado, sem sorteios nem compra inicial.

    Gatos de campo entram prontos para atacar (ready=True). Por padrao ambos os
    lados ja jogaram 2 turnos (sem restricao de primeiro turno); `first_turn=True`
    faz `turn_side` estar no seu 1o turno como quem comecou. Energia padrao = a
    do turno corrente. O deck inicial (para o impasse) = mao + deck + campo.
    """
    rules = content.rules["duel"]

    def card(x: Cat | Card | FieldCat) -> Card:
        if isinstance(x, FieldCat):
            return x.card
        return x if isinstance(x, Card) else card_from_cat(content, x)

    def build(hand, deck, fld, energy, leader_hp) -> SideState:
        st = _side_state(rules, [])
        st.hand = [card(c) for c in hand or []]
        st.deck = [card(c) for c in deck or []]
        for slot, x in (fld or {}).items():
            if isinstance(x, FieldCat):
                st.field[slot] = x
            else:
                c = card(x)
                st.field[slot] = FieldCat(c, c.atk, c.hp, c.hp, c.keywords, ready=True)
        st.initial_deck = (list(st.hand) + list(st.deck)
                           + [fc.card for fc in st.field if fc is not None])
        st.turns_taken = 2
        st.energy = energy if energy is not None else _turn_energy(rules, 2)
        if leader_hp is not None:
            st.leader_hp = leader_hp
            st.leader_hp_max = max(st.leader_hp_max, leader_hp)
        return st

    sides = {
        "player": build(player_hand, player_deck, player_field, player_energy, player_leader_hp),
        "enemy": build(enemy_hand, enemy_deck, enemy_field, enemy_energy, enemy_leader_hp),
    }
    first = turn_side if first_turn else other(turn_side)
    if first_turn:
        sides[turn_side].turns_taken = 1
        if player_energy is None and turn_side == "player" or \
                enemy_energy is None and turn_side == "enemy":
            sides[turn_side].energy = _turn_energy(rules, 1, True)
    return Duel(content=content, rng=rng or Random(0), sides=sides, turn_side=turn_side,
                first_side=first)
