"""Controlador do duelo: estado da selecao, clique -> acao, fila de animacao e log.

Puro (sem pygame): da para testar sem janela. So chama a API publica do core
(`new_duel`, `legal_actions`, `attack_targets`, `apply_action`, `view`,
`choose_action`) e nunca reimplementa regra: tudo que e permitido vem de
`legal_actions`/`attack_targets`. O estado mostrado (`shown`) e uma copia da
`view` que os eventos de `apply_action` vao atualizando, beat por beat, para a
animacao mostrar os passos em ordem; ao esvaziar a fila ele e ressincronizado
com o core.

Elementos clicaveis (`elem`), como o layout os devolve:
    ("hand", i)  ("slot", side, n)  ("leader", side)  ("pass",)  ("again",)  ("repeat",)

Selecao (`sel`):
    ("hand", i)         carta da mao (gato, Espirito ou efeito)
    ("enter", i, slot)  Espirito ja posicionado no slot, esperando o alvo do "ao entrar"
    ("slot", n)         gato proprio pronto para atacar
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from random import Random
from typing import Any, Callable

from core import load_content, roll_cat
from core.ai import choose_action
from core.duel import (
    apply_action, attack_targets, card_targets, keyword_info, legal_actions, new_duel,
    new_duel_vs_enemy, view,
)
from core.types import (
    Attack, Attacked, AtkBuffExpired, AtkBuffed, Card, CatDied, CatPlayed, Content,
    DamageDealt, Deadlock, DeckSpec, DiceRolled, Drew, DrawSkipped, Duel, DuelEnded, DuelView,
    EffectPlayed, EndTurn, EnergyChanged, FieldCat, Healed, IllegalAction, LeaderDamaged,
    LeaderHealed, PlayCat, PlayEffect, TurnStarted,
)
from ui import text as T

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DICE_TIME = 2.6
AI_DELAY = 0.5
LOG_MAX = 80


@dataclass
class Fx:
    """Efeito visual de vida curta. `slot=None` = Lider."""
    kind: str                 # float | flash | line | die | enter
    side: str
    slot: int | None
    life: float
    text: str = ""
    color: str = "bad"
    card: Any = None
    to_side: str | None = None
    to_slot: int | None = None
    age: float = 0.0


@dataclass
class Beat:
    events: list
    duration: float


@dataclass
class Toast:
    text: str
    kind: str = "error"       # error | warn | info
    ttl: float = 2.5


def load_game_content() -> Content:
    return load_content(DATA_DIR)


class Controller:
    def __init__(self, content: Content, seed: int, *, ai_delay: float = AI_DELAY,
                 seed_source: Callable[[], int] | None = None, enemy_id: str | None = None,
                 enemy_random: bool = False, player_spec: DeckSpec | None = None,
                 duel: Duel | None = None) -> None:
        """`enemy_id` None = duelo antigo (dois decks sorteados); com id usa
        `new_duel_vs_enemy`. `enemy_random` sorteia o inimigo a cada partida (pelo seed).
        `player_spec` fixa o deck do jogador (cenas/testes). `duel` usa um duelo ja criado
        (a mini-run cria o duelo por `Run.start_duel`; vale so para a primeira partida) e
        liga `run_mode` (o painel final mostra CONTINUAR em vez de jogar de novo)."""
        self.content = content
        self.preset_duel = duel
        self.run_mode = duel is not None
        self.ai_delay = ai_delay
        self.enemy_id = enemy_id
        self.enemy_random = enemy_random
        self.player_spec = player_spec
        self.seed_source = seed_source or (lambda: Random().randrange(1, 10**6))
        self.speed = 1.0
        self.new_game(seed)

    # ------------------------------------------------------------ partida
    def new_game(self, seed: int) -> None:
        self.seed = seed
        rng = Random(seed)
        if self.enemy_random:
            self.enemy_id = Random(seed).choice(sorted(self.content.enemies))
        player = self.player_spec or (None if self.preset_duel else self._deck(rng, "p"))
        if self.preset_duel is not None:
            self.duel, self.preset_duel = self.preset_duel, None
        elif self.enemy_id is not None:
            self.duel = new_duel_vs_enemy(self.content, player, self.enemy_id, rng)
        else:
            self.duel = new_duel(self.content, rng, player, self._deck(rng, "e"))
        self.enemy: dict | None = (self.content.enemies.get(self.enemy_id)
                                   if self.enemy_id else None)
        self.final_line: str | None = None
        self.line_rng = Random(seed + 2)
        self.ai_rng = Random(seed + 1)
        self.beats: deque[Beat] = deque()
        self.cur: Beat | None = None
        self.beat_t = 0.0
        self.fx: list[Fx] = []
        self.log: list[tuple[str, str]] = []
        self.toast: Toast | None = None
        self.banner: tuple[list[str], float] | None = None
        self.sel: tuple | None = None
        self.sel_targets: list[tuple] = []
        self.confirming = False
        self.ai_t = 0.0
        self.over_t = 0.0
        self.in_deadlock = False
        self.stats = {"lost": 0, "killed": 0, "deadlock": False}
        self.turn_energy = {"player": 0, "enemy": 0}
        self.energy_cap = self.content.rules["duel"]["energy_cap"]
        self._dirty = False
        self.phase = "dice"
        self.dice_t = 0.0
        self.first = self.duel.first_side
        self.shown: DuelView = view(self.duel, "player")
        for ev in self.duel.log:                      # dado e compra inicial (ja no estado)
            if isinstance(ev, TurnStarted):
                self.turn_energy[ev.side] = ev.energy
            line = T.describe(ev, self.shown)
            if line and not isinstance(ev, (Drew, DrawSkipped)):
                self._log(*line)
        self.refresh()

    def _deck(self, rng: Random, prefix: str) -> DeckSpec:
        cats = []
        for i in range(self.content.rules["duel"]["deck_size"]):
            cat = roll_cat(self.content, rng)
            cat.id = f"{prefix}{i + 1}"
            cats.append(cat)
        return DeckSpec(cats=cats)

    def again(self) -> None:
        self.new_game(self.seed_source())

    def repeat(self) -> None:
        self.new_game(self.seed)

    # ------------------------------------------------------------ estado derivado
    def refresh(self) -> None:
        """Ressincroniza `shown` e os conjuntos de jogadas legais com o core."""
        d = self.duel
        self.shown = view(d, "player")
        self.legal = legal_actions(d)
        self.playable: dict[int, set[int]] = {}
        self.attackers: set[int] = set()
        if d.winner is None and d.turn_side == "player":
            for a in self.legal:
                if isinstance(a, PlayCat):
                    self.playable.setdefault(a.hand_index, set()).add(a.slot)
                elif isinstance(a, PlayEffect):
                    self.playable.setdefault(a.hand_index, set())
            for n in range(len(self.shown.me.field)):
                if attack_targets(d, n):
                    self.attackers.add(n)
        self.sel = None
        self.sel_targets = []
        self.confirming = False

    @property
    def idle(self) -> bool:
        return self.phase == "play" and self.cur is None and not self.beats

    def can_act(self) -> bool:
        return self.idle and self.duel.winner is None and self.duel.turn_side == "player"

    @property
    def over(self) -> bool:
        return self.phase == "over"

    @property
    def final_visible(self) -> bool:
        return self.phase == "over" and self.over_t >= 0.8

    @property
    def pass_only(self) -> bool:
        """So resta passar o turno (o botao pisca)."""
        return self.can_act() and all(isinstance(a, EndTurn) for a in self.legal)

    def hand_state(self, i: int) -> tuple[bool, list[str]]:
        """(jogavel, linhas curtas do motivo) da carta i da mao do jogador."""
        if not self.can_act():
            return True, []
        if i in self.playable:
            return True, []
        card = self.shown.me.hand[i]
        if card.cost > self.shown.me.energy:
            return False, T.energy_short_reason(card, self.shown.me.energy)
        if card.kind == "effect":
            return False, ["SEM ALVO", "VÁLIDO"]
        return False, ["SEM SLOT", "VAZIO"]

    # ------------------------------------------------------------ alvos de efeito
    @staticmethod
    def effect_plan(card: Card) -> tuple[str | None, str | None]:
        """(lado do gato escolhido, lado do Lider fixo) das acoes da carta. So exibicao:
        a validade vem de `card_targets`/`legal_actions`. (None, None) = sem alvo."""
        choice = leader = None
        for a in card.actions:
            alvo = a.get("alvo")
            if alvo == "inimigo_escolhido":
                choice = "enemy"
            elif alvo == "aliado_escolhido":
                choice = "player"
            elif alvo == "lider_inimigo" and leader is None:
                leader = "enemy"
            elif alvo == "lider_proprio" and leader is None:
                leader = "player"
        return choice, (None if choice else leader)

    def sel_card(self) -> Card | None:
        """Carta da mao envolvida na selecao atual (ou None)."""
        if (self.sel and self.sel[0] in ("hand", "enter")
                and self.sel[1] < len(self.shown.me.hand)):
            return self.shown.me.hand[self.sel[1]]
        return None

    def targeting(self) -> bool:
        """Esperando o jogador escolher um alvo para uma carta (efeito ou Espirito)."""
        card = self.sel_card()
        if card is None:
            return False
        return self.sel[0] == "enter" or card.kind == "effect"

    def needs_confirm(self) -> bool:
        """Efeito selecionado sem alvo: um segundo clique na carta o usa."""
        card = self.sel_card()
        return (card is not None and self.sel[0] == "hand" and card.kind == "effect"
                and self.effect_plan(card) == (None, None))

    def slot_target(self, side: str, n: int) -> str | None:
        """Rotulo do destaque do gato em (side, n): "ATACAR", "ALVO" ou None."""
        if ("slot", n) not in self.sel_targets:
            return None
        if self.sel and self.sel[0] == "slot":
            return "ATACAR" if side == "enemy" else None
        card = self.sel_card()
        if card is None:
            return None
        return "ALVO" if self.effect_plan(card)[0] == side else None

    def leader_target(self, side: str) -> str | None:
        """"attack", "effect" ou None: o Lider de `side` e alvo valido agora?"""
        if ("leader",) not in self.sel_targets:
            return None
        if self.sel and self.sel[0] == "slot":
            return "attack" if side == "enemy" else None
        card = self.sel_card()
        if card is not None and self.effect_plan(card)[1] == side:
            return "effect"
        return None

    def spirit_ghost(self) -> tuple[int, Card] | None:
        """(slot, carta) do Espirito posicionado e esperando o alvo."""
        card = self.sel_card()
        if card is not None and self.sel[0] == "enter":
            return self.sel[2], card
        return None

    def enemy_name(self) -> str:
        return self.enemy["nome"] if self.enemy else "Inimigo"

    def cat_status(self, side: str, fc: FieldCat) -> tuple[str, str]:
        """(chave, texto) do estado do gato em campo, para destaque/tooltip."""
        if self.duel.turn_side != side or self.duel.winner is not None:
            return "idle", ""
        if fc.attacked:
            return "spent", "Já atacou neste turno"
        if side == "player" and self.idle:
            slot = next((n for n, c in enumerate(self.shown.me.field) if c is not None
                         and c.card is fc.card), None)
            if slot is not None and slot in self.attackers:
                return "ready", "Pode atacar"
            if fc.ready:
                return "wait", "Ninguém pode atacar neste turno (quem começa não ataca no 1o turno)"
            return "new", "Acabou de entrar: não ataca neste turno"
        if fc.ready:
            return "ready", "Pode atacar"
        return "new", "Acabou de entrar: não ataca neste turno"

    def taunt_in_way(self) -> bool:
        return any(fc is not None and "provocar" in fc.keywords
                   for fc in self.shown.opponent.field)

    def keyword_text(self, kid: str) -> tuple[str, str]:
        info = keyword_info(self.content, kid)
        return info["nome"], info["texto"]

    # ------------------------------------------------------------ mensagens
    def say(self, text: str, kind: str = "error", ttl: float = 2.5) -> None:
        self.toast = Toast(text, kind, ttl)

    def _log(self, text: str, side: str) -> None:
        self.log.append((text, side))
        del self.log[:-LOG_MAX]

    def has_other_moves(self) -> bool:
        """Ha jogada legal alem de EndTurn (decidido so por `legal_actions`)."""
        return self.can_act() and any(not isinstance(a, EndTurn) for a in self.legal)

    def hint(self) -> str:
        if self.confirming:
            return "Passar mesmo assim? (E/ESC)"
        if self.phase == "dice":
            return "Clique para continuar"
        if self.over:
            return "Fim do duelo"
        if self.duel.turn_side == "enemy":
            return "Turno do inimigo..."
        if not self.idle:
            return "..."
        card = self.sel_card()
        if self.sel and self.sel[0] == "enter":
            return "Escolha o alvo (ESC)"
        if card is not None and card.kind == "effect":
            if self.needs_confirm():
                return "Clique de novo p/ usar"
            return "Clique no alvo (ESC)"
        if self.sel and self.sel[0] == "hand":
            return "Escolha um slot (ESC)"
        if self.sel:
            return "Escolha o alvo (ESC)"
        if self.pass_only:
            return "Passe o turno (E)"
        return "Escolha carta ou gato"

    # ------------------------------------------------------------ entrada
    def click(self, elem: tuple | None) -> None:
        if self.phase == "dice":
            self.dismiss_dice()
            return
        if self.phase == "over":
            if self.final_visible and elem:
                if self.run_mode:                  # a run trata o "continuar"
                    return
                if elem[0] == "again":
                    self.again()
                elif elem[0] == "repeat":
                    self.repeat()
            return
        if not self.can_act():
            if elem and elem[0] != "none":
                self.say("Aguarde: é o turno do inimigo", "info", 1.2)
            return
        if self.confirming:
            if elem == ("pass_yes",):
                self.confirm_end_turn()
            else:                                  # Nao, ou qualquer outro lugar
                self.cancel_confirm()
            return
        if elem is None or elem[0] == "none":
            self.cancel()
            return
        kind = elem[0]
        if kind == "pass":
            self.request_end_turn()
        elif kind == "hand":
            self._click_hand(elem[1])
        elif kind == "slot":
            self._click_slot(elem[1], elem[2])
        elif kind == "leader":
            self._click_leader(elem[1])

    def end_turn(self) -> None:
        if self.can_act():
            self._do(EndTurn())

    def request_end_turn(self) -> None:
        """Botao/tecla E: passa direto se so resta EndTurn; senao pede confirmacao.
        Com a confirmacao aberta, repetir o pedido (E) confirma."""
        if not self.can_act():
            return
        if self.confirming:
            self.confirm_end_turn()
        elif self.has_other_moves():
            self.cancel()
            self.confirming = True
        else:
            self.end_turn()

    def confirm_end_turn(self) -> None:
        if self.confirming:
            self.end_turn()

    def cancel_confirm(self) -> None:
        self.confirming = False

    def cancel(self) -> None:
        self.sel = None
        self.sel_targets = []
        self.confirming = False

    def draggable(self, elem: tuple | None) -> bool:
        """Se `elem` pode virar origem de arrastar (carta jogavel ou gato que ataca)."""
        if not elem or not self.can_act() or self.confirming:
            return False
        if elem[0] == "hand":
            return elem[1] in self.playable
        return elem[0] == "slot" and elem[1] == "player" and elem[2] in self.attackers

    def drag_start(self, elem: tuple) -> bool:
        if not self.draggable(elem):
            return False
        self.cancel()
        self.click(elem)
        return self.sel is not None

    def drop(self, elem: tuple | None) -> None:
        """Soltar depois de arrastar: age se for destino valido, senao cancela."""
        if self.sel is None:
            return
        if elem is not None and elem != self._sel_elem():
            self.click(elem)
        if self.sel is not None and self.sel[0] != "enter":      # "enter": falta so o alvo
            if elem is not None and elem != self._sel_elem():
                self.say("Destino inválido para essa jogada", "error", 1.5)
            self.cancel()

    def _sel_elem(self) -> tuple | None:
        if not self.sel:
            return None
        if self.sel[0] in ("hand", "enter"):
            return ("hand", self.sel[1])
        return ("slot", "player", self.sel[1])

    def _click_hand(self, i: int) -> None:
        if i >= len(self.shown.me.hand):
            return
        if self.sel == ("hand", i) and self.needs_confirm():
            self._do(PlayEffect(i, ("leader",)))             # segundo clique: usar
            return
        if self.sel is not None and self.sel[0] in ("hand", "enter") and self.sel[1] == i:
            self.cancel()
            return
        ok, why = self.hand_state(i)
        if not ok:
            card = self.shown.me.hand[i]
            self.cancel()
            if why and why[0] == "FALTAM":
                self.say(f"Energia insuficiente: {T.label(card)} custa {card.cost} e você tem "
                         f"{self.shown.me.energy}", "error")
            elif why and why[0] == "SEM SLOT":
                self.say("Seu campo está cheio: não há slot vazio", "error")
            else:
                self.say("Essa carta não pode ser jogada agora", "error")
            return
        self.sel = ("hand", i)
        card = self.shown.me.hand[i]
        # alvos de efeito vem do core (card_targets); Espirito so os pede depois do slot
        self.sel_targets = card_targets(self.duel, i) if card.kind == "effect" else []

    def _click_slot(self, side: str, n: int) -> None:
        if self.targeting():
            self._click_card_target(side, ("slot", n))
        elif side == "player":
            self._click_own_slot(n)
        else:
            self._click_enemy_target(("slot", n))

    def _click_own_slot(self, n: int) -> None:
        fc = self.shown.me.field[n]
        if self.sel and self.sel[0] == "hand":
            if fc is not None:
                if n in self.attackers:          # troca a selecao para o gato pronto
                    self.sel = ("slot", n)
                    self.sel_targets = attack_targets(self.duel, n)
                else:
                    self.say("Esse slot já está ocupado: escolha um vazio", "error")
                return
            self._place_card(self.sel[1], n)
            return
        if fc is None:
            self.cancel()
            return
        if self.sel == ("slot", n):
            self.cancel()
            return
        if n in self.attackers:
            self.sel = ("slot", n)
            self.sel_targets = attack_targets(self.duel, n)
            return
        self.cancel()
        kind, why = self.cat_status("player", fc)
        self.say(why or "Esse gato não pode atacar agora", "error")

    def _place_card(self, i: int, n: int) -> None:
        """Gato ou Espirito da mao `i` no slot vazio `n` (so jogadas de `legal_actions`)."""
        card = self.shown.me.hand[i]
        plain = PlayCat(i, n)
        if plain in self.legal:
            if card.kind == "special" and self.effect_plan(card)[0] is not None:
                self.say("Sem alvo válido: o efeito ao entrar foi perdido", "warn", 3.5)
            self._do(plain)
        elif any(isinstance(a, PlayCat) and a.hand_index == i and a.slot == n
                 for a in self.legal):                       # pede alvo do "ao entrar"
            self.sel = ("enter", i, n)
            self.sel_targets = card_targets(self.duel, i)
        else:
            self.say("Não dá para jogar essa carta nesse slot", "error")

    def _click_card_target(self, side: str, target: tuple) -> None:
        """Clique durante a escolha de alvo de um efeito ou do "ao entrar" de um Espirito."""
        card = self.sel_card()
        if card is None:
            return
        i = self.sel[1]
        choice, leader = self.effect_plan(card)
        is_enter = self.sel[0] == "enter"
        if target[0] == "slot" and choice == side and target in self.sel_targets:
            action = PlayCat(i, self.sel[2], target) if is_enter else PlayEffect(i, target)
        elif target[0] == "leader" and not is_enter and leader == side:
            action = PlayEffect(i, ("leader",))
        else:
            action = None
        if action is not None and action in self.legal:
            self._do(action)
        elif is_enter or choice is not None:
            self.say("Escolha um dos alvos destacados (ESC cancela)", "error")
        elif leader is not None:
            self.say("Esse efeito vai no Líder destacado (ESC cancela)", "error")
        else:
            self.say("Clique de novo na carta para usar o efeito", "info")

    def _click_enemy_target(self, target: tuple) -> None:
        if not self.sel or self.sel[0] != "slot":
            if self.sel and self.sel[0] == "hand":
                self.say("Escolha um slot vazio do seu campo para jogar a carta", "error")
            else:
                self.say("Primeiro clique num gato seu que esteja pronto (verde)", "info")
            return
        action = Attack(self.sel[1], target)
        if action in self.legal:
            self._do(action)
        elif self.taunt_in_way():
            self.say("Provocar: derrote primeiro o gato com Provocar", "error")
        else:
            self.say("Esse alvo não é permitido", "error")

    def _click_leader(self, side: str) -> None:
        if self.targeting():
            self._click_card_target(side, ("leader",))
        elif side == "enemy":
            self._click_enemy_target(("leader",))
        else:
            self.say("Esse é o seu Líder: ele não ataca nem é alvo seu", "info")

    # ------------------------------------------------------------ aplicar acao
    def _do(self, action: Any) -> bool:
        try:
            events = apply_action(self.duel, action)
        except IllegalAction as e:
            self.say(f"Ação ilegal: {e}", "error")
            self.cancel()
            return False
        self._dirty = True
        self.confirming = False
        self.sel = None
        self.sel_targets = []
        self._enqueue(events)
        return True

    # ------------------------------------------------------------ fila de beats
    _DUR = {"Attacked": 0.34, "CatPlayed": 0.4, "EffectPlayed": 0.4, "result": 0.55,
            "heal": 0.45, "buff": 0.45, "turn": 0.4, "Deadlock": 2.6, "deadhit": 0.6, "DuelEnded": 0.3}

    def _kind(self, ev: Any, dead: bool) -> str:
        if isinstance(ev, (DamageDealt, CatDied)):
            return "result"
        if isinstance(ev, LeaderDamaged):
            return "deadhit" if dead else "result"
        if isinstance(ev, (Healed, LeaderHealed)):
            return "heal"
        if isinstance(ev, (AtkBuffed, AtkBuffExpired)):
            return "buff"
        if isinstance(ev, (TurnStarted, Drew, DrawSkipped)):
            return "turn"
        if isinstance(ev, EnergyChanged):
            return "join"
        return type(ev).__name__

    def _enqueue(self, events: list) -> None:
        dead = False
        groups: list[tuple[str, list]] = []
        for ev in events:
            if isinstance(ev, Deadlock):
                dead = True
            k = self._kind(ev, dead)
            if k == "join" and groups:
                groups[-1][1].append(ev)
            elif groups and k == groups[-1][0] and k in ("result", "heal", "turn", "buff"):
                groups[-1][1].append(ev)
            else:
                groups.append((k, [ev]))
        for k, evs in groups:
            self.beats.append(Beat(evs, self._DUR.get(k, 0.3)))

    def _begin(self, beat: Beat) -> None:
        self.cur = beat
        self.beat_t = 0.0
        for ev in beat.events:
            line = T.describe(ev, self.shown)
            if line:
                self._log(*line)
            self._fx_for(ev, starting=any(isinstance(e, TurnStarted) for e in beat.events))
            self._apply_shown(ev)

    def _target_side(self, ev: EffectPlayed) -> tuple[str, int | None] | None:
        """(lado, slot|None) alvo de um EffectPlayed, so para destacar (exibicao)."""
        choice, leader = self.effect_plan(ev.card)
        foe = "enemy" if ev.side == "player" else "player"
        rel = {"player": ev.side, "enemy": foe}
        if ev.target[0] == "slot":
            return (rel[choice], ev.target[1]) if choice else None
        return (rel[leader], None) if leader else None

    def _fx_for(self, ev: Any, starting: bool = False) -> None:
        fx = self.fx
        if isinstance(ev, EffectPlayed):
            fx.append(Fx("cast", ev.side, None, 1.1, text=ev.card.name))
            tgt = self._target_side(ev)
            if tgt:
                fx.append(Fx("enter", tgt[0], tgt[1], 0.6))
        elif isinstance(ev, LeaderHealed):
            fx.append(Fx("flash", ev.side, None, 0.4, color="good"))
            fx.append(Fx("float", ev.side, None, 1.0, text=f"+{ev.amount}", color="good"))
        elif isinstance(ev, AtkBuffed):
            fx.append(Fx("flash", ev.side, ev.slot, 0.4, color="buff"))
            fx.append(Fx("float", ev.side, ev.slot, 0.95, text=f"+{ev.amount} ATK", color="buff"))
        elif isinstance(ev, AtkBuffExpired):
            fx.append(Fx("float", ev.side, ev.slot, 0.8, text=f"-{ev.amount} ATK", color="dim"))
        elif isinstance(ev, EnergyChanged) and not starting:
            gain = ev.energy - T.side_view(self.shown, ev.side).energy
            if gain > 0:
                self._tag_fx(ev.side, "energy", f"+{gain} ENERGIA", "energy")
        elif isinstance(ev, Drew) and not starting:
            self._tag_fx(ev.side, "draw", "+1 CARTA", "good")
        if isinstance(ev, Attacked):
            foe = "enemy" if ev.side == "player" else "player"
            fx.append(Fx("line", ev.side, ev.attacker_slot, 0.4, to_side=foe,
                         to_slot=None if ev.target[0] == "leader" else ev.target[1]))
        elif isinstance(ev, DamageDealt):
            fx.append(Fx("flash", ev.side, ev.slot, 0.32, color="bad"))
            fx.append(Fx("float", ev.side, ev.slot, 0.95, text=f"-{ev.amount}", color="bad"))
        elif isinstance(ev, LeaderDamaged):
            fx.append(Fx("flash", ev.side, None, 0.36, color="bad"))
            fx.append(Fx("float", ev.side, None, 1.0, text=f"-{ev.amount}", color="bad"))
        elif isinstance(ev, Healed):
            fx.append(Fx("flash", ev.side, ev.slot, 0.4, color="good"))
            fx.append(Fx("float", ev.side, ev.slot, 0.95, text=f"+{ev.amount}", color="good"))
        elif isinstance(ev, CatPlayed):
            fx.append(Fx("enter", ev.side, ev.slot, 0.4))
        elif isinstance(ev, CatDied):
            fx.append(Fx("die", ev.side, ev.slot, 0.5, card=ev.card))
        elif isinstance(ev, DrawSkipped) and ev.side == "player":
            self.say("Mão cheia: a compra foi pulada", "warn", 3.5)
        elif isinstance(ev, TurnStarted):
            mine = ev.side == "player"
            self.banner = (["SEU TURNO" if mine else "TURNO DO INIMIGO"], 0.9)
        elif isinstance(ev, Deadlock):
            self.banner = (["IMPASSE!", f"Poder dos Líderes: você {ev.powers['player']}, "
                            f"inimigo {ev.powers['enemy']}",
                            "Começa: " + ("você" if ev.first == "player" else "o inimigo")], 2.6)

    def _tag_fx(self, side: str, where: str, text: str, color: str) -> None:
        """Texto flutuante em posicao fixa; o render decide o retangulo por `card`=where."""
        self.fx.append(Fx("tag", side, None, 1.0, text=text, color=color, card=where))

    def _apply_shown(self, ev: Any) -> None:
        sh = self.shown
        if isinstance(ev, TurnStarted):
            sh.turn_side = ev.side
            sv = T.side_view(sh, ev.side)
            sv.turns_taken = ev.turn
            sv.energy = ev.energy
            self.turn_energy[ev.side] = ev.energy
        elif isinstance(ev, EnergyChanged):
            T.side_view(sh, ev.side).energy = ev.energy
        elif isinstance(ev, Drew):
            sv = T.side_view(sh, ev.side)
            sv.deck_count -= 1
            sv.hand_count += 1
            if sv.hand is not None:
                sv.hand.append(ev.card)
        elif isinstance(ev, CatPlayed):
            sv = T.side_view(sh, ev.side)
            c = ev.card
            sv.field[ev.slot] = FieldCat(c, c.atk, c.hp, c.hp, c.keywords, ready=False)
            sv.hand_count -= 1
            if sv.hand is not None:
                for k, h in enumerate(sv.hand):
                    if h.ref == c.ref:
                        del sv.hand[k]
                        break
        elif isinstance(ev, Attacked):
            fc = T.side_view(sh, ev.side).field[ev.attacker_slot]
            if fc is not None:
                fc.ready, fc.attacked = False, True
        elif isinstance(ev, (DamageDealt, Healed)):
            fc = T.side_view(sh, ev.side).field[ev.slot]
            if fc is not None:
                fc.hp = ev.hp_left
        elif isinstance(ev, EffectPlayed):
            if ev.card.kind == "effect":
                sv = T.side_view(sh, ev.side)
                sv.hand_count -= 1
                if sv.hand is not None:
                    for k, h in enumerate(sv.hand):
                        if h.ref == ev.card.ref:
                            del sv.hand[k]
                            break
        elif isinstance(ev, LeaderHealed):
            T.side_view(sh, ev.side).leader_hp = ev.hp_left
        elif isinstance(ev, AtkBuffed):
            fc = T.side_view(sh, ev.side).field[ev.slot]
            if fc is not None:
                fc.atk = ev.atk
                if ev.temporary:
                    fc.atk_bonus_turn += ev.amount
        elif isinstance(ev, AtkBuffExpired):
            fc = T.side_view(sh, ev.side).field[ev.slot]
            if fc is not None:
                fc.atk = ev.atk
                fc.atk_bonus_turn = max(0, fc.atk_bonus_turn - ev.amount)
        elif isinstance(ev, CatDied):
            T.side_view(sh, ev.side).field[ev.slot] = None
            self.stats["lost" if ev.side == "player" else "killed"] += 1
        elif isinstance(ev, LeaderDamaged):
            T.side_view(sh, ev.side).leader_hp = ev.hp_left
        elif isinstance(ev, Deadlock):
            self.in_deadlock = True
            self.stats["deadlock"] = True
        elif isinstance(ev, DuelEnded):
            sh.winner = ev.winner

    # ------------------------------------------------------------ tempo
    def dismiss_dice(self) -> None:
        if self.phase == "dice":
            self.phase = "play"
            self.ai_t = 0.0
            pass

    def skip(self) -> None:
        """ESPACO: pula o passo atual (dado, animacao ou espera da IA)."""
        if self.phase == "dice":
            self.dismiss_dice()
        elif self.cur is not None:
            self.beat_t = self.cur.duration
        elif self.phase == "over":
            self.over_t = max(self.over_t, 0.8)
        else:
            self.ai_t = self.ai_delay

    def update(self, dt: float) -> None:
        dt *= self.speed
        for f in self.fx:
            f.age += dt
        self.fx = [f for f in self.fx if f.age < f.life]
        if self.toast:
            self.toast.ttl -= dt
            if self.toast.ttl <= 0:
                self.toast = None
        if self.banner:
            self.banner = (self.banner[0], self.banner[1] - dt) if self.banner[1] > dt else None
        if self.phase == "dice":
            self.dice_t += dt
            if self.dice_t >= DICE_TIME:
                self.dismiss_dice()
            return
        if self.phase == "over":
            self.over_t += dt
            return
        if self.cur is not None:
            self.beat_t += dt
            if self.beat_t < self.cur.duration:
                return
            self.cur = None
        if self.beats:
            self._begin(self.beats.popleft())
            return
        self._idle(dt)

    def _idle(self, dt: float) -> None:
        d = self.duel
        if self._dirty:
            self._dirty = False
            self.refresh()
        if d.winner is not None:
            self.phase = "over"
            self.over_t = 0.0
            self.final_line = self._pick_line()
            return
        if d.turn_side == "enemy":
            self.ai_t += dt
            if self.ai_t >= self.ai_delay:
                self.ai_t = 0.0
                self._do(choose_action(d, "enemy", self.ai_rng))

    def _pick_line(self) -> str | None:
        """Fala do inimigo-pessoa: vitoria se ele ganhou, derrota se perdeu (rng injetado)."""
        if not self.enemy:
            return None
        falas = self.enemy.get("falas", {})
        lines = falas.get("vitoria" if self.duel.winner == "enemy" else "derrota")
        return self.line_rng.choice(lines) if lines else None

    # ------------------------------------------------------------ resumo / testes
    def summary(self) -> list[str]:
        sh = self.shown
        lines = [
            f"Turnos: você {sh.me.turns_taken}, inimigo {sh.opponent.turns_taken}",
            f"Seu Líder: {sh.me.leader_hp}/{sh.me.leader_hp_max} HP",
            f"Líder inimigo: {sh.opponent.leader_hp}/{sh.opponent.leader_hp_max} HP",
            f"Seus gatos perdidos: {self.stats['lost']}",
            f"Gatos inimigos derrotados: {self.stats['killed']}",
        ]
        if self.stats["deadlock"]:
            lines.append("O duelo foi decidido no Impasse")
        lines.append(f"Seed: {self.seed}")
        return lines

    def settle(self, max_steps: int = 5000) -> None:
        """Roda animacoes e a IA ate o jogador poder agir (ou o duelo acabar). Sem render."""
        for _ in range(max_steps):
            if self.phase == "dice":
                self.dismiss_dice()
            if self.can_act() or self.phase == "over":
                return
            self.update(5.0)
