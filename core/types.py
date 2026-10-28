"""Tipos do core (dataclasses simples, serializaveis)."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Stage = Literal["kitten", "adult"]
Sex = Literal["M", "F"]


@dataclass
class Cat:
    id: str
    breed: str
    sex: str
    nature: str
    iv_atk: int
    iv_hp: int
    stage: str = "adult"
    name: str | None = None
    rest_runs_left: int = 0
    runs_as_kitten: int = 0


@dataclass(frozen=True)
class Stats:
    cost: int
    atk: int
    hp: int


@dataclass
class Content:
    breeds: dict[str, dict[str, Any]]
    natures: dict[str, dict[str, Any]]
    keywords: dict[str, dict[str, Any]]
    rules: dict[str, Any]
    extras: dict[str, Any] = field(default_factory=dict)
    # Fase 3: indexados por id (vazios se o arquivo de data/ nao existir)
    effects: dict[str, dict[str, Any]] = field(default_factory=dict)
    specials: dict[str, dict[str, Any]] = field(default_factory=dict)
    enemies: dict[str, dict[str, Any]] = field(default_factory=dict)
    run: dict[str, Any] | None = None   # data/run.json (None = sem run)


# ---------------------------------------------------------------- duelo
from random import Random  # noqa: E402

Side = Literal["player", "enemy"]
Winner = Side
Target = tuple  # ("slot", n) ou ("leader",)


def other(side: str) -> str:
    return "enemy" if side == "player" else "player"


@dataclass
class Card:
    """Carta em deck/mao. `kind`: "cat" (gato de colecao), "special" (Espirito) ou "effect"."""
    kind: str
    ref: str                       # id do Cat, do Especial ou do efeito (data/)
    name: str
    cost: int
    atk: int = 0
    hp: int = 0
    keywords: tuple[str, ...] = ()
    breed: str | None = None
    # exibicao (None em cartas que nao sao gatos de colecao)
    breed_name: str | None = None
    cat_name: str | None = None    # nome dado ao gato, se houver
    sex: str | None = None
    nature: str | None = None
    iv_atk: int | None = None
    iv_hp: int | None = None
    text: str | None = None        # texto de jogo (efeito/Espirito)
    # acoes: do efeito (kind "effect") ou "ao entrar" (kind "special"); dicts de data/
    actions: tuple[dict[str, Any], ...] = ()


@dataclass
class DeckSpec:
    """Deck de entrada do duelo: gatos adultos de colecao (`cats`) mais cartas
    prontas (`cards`: Espiritos, efeitos, gatos de raca com IV fixo)."""
    cats: list[Cat] = field(default_factory=list)
    cards: list[Card] = field(default_factory=list)
    leader_hp: int | None = None        # None = rules.duel.leader_hp
    rule: dict[str, Any] | None = None  # regra_propria do chefe


@dataclass
class FieldCat:
    card: Card
    atk: int
    hp: int
    hp_max: int
    keywords: tuple[str, ...]
    ready: bool = False            # pode atacar agora
    used_first_strike: bool = False
    attacked: bool = False         # ja atacou neste turno
    atk_bonus_turn: int = 0        # parte de `atk` que expira no fim do turno do dono

    @property
    def first_strike_available(self) -> bool:
        return "primeira-patada" in self.keywords and not self.used_first_strike

    @property
    def can_attack(self) -> bool:
        return self.ready


@dataclass
class SideState:
    leader_hp: int
    leader_hp_max: int
    deck: list[Card]               # topo = indice 0
    hand: list[Card]
    field: list[FieldCat | None]
    energy: int = 0
    turns_taken: int = 0
    initial_deck: list[Card] = field(default_factory=list)
    rule: dict[str, Any] | None = None


# Acoes
@dataclass(frozen=True)
class PlayCat:
    hand_index: int
    slot: int
    target: Target | None = None   # alvo do "ao entrar" (Espiritos), se houver


@dataclass(frozen=True)
class PlayEffect:
    hand_index: int
    target: Target = ("leader",)


@dataclass(frozen=True)
class Attack:
    attacker_slot: int
    target: Target


@dataclass(frozen=True)
class EndTurn:
    pass


Action = PlayCat | PlayEffect | Attack | EndTurn


class IllegalAction(Exception):
    pass


# Eventos
@dataclass(frozen=True)
class DiceRolled:
    first: str


@dataclass(frozen=True)
class DrawSkipped:
    side: str


@dataclass(frozen=True)
class Deadlock:
    powers: dict
    first: str


@dataclass(frozen=True)
class TurnStarted:
    side: str
    turn: int          # n-esimo turno desse lado
    energy: int


@dataclass(frozen=True)
class Drew:
    side: str
    card: Card


@dataclass(frozen=True)
class CatPlayed:
    side: str
    slot: int
    card: Card


@dataclass(frozen=True)
class EffectPlayed:
    side: str
    card: Card
    target: Target


@dataclass(frozen=True)
class Attacked:
    side: str
    attacker_slot: int
    target: Target


@dataclass(frozen=True)
class DamageDealt:
    side: str          # lado do gato que recebeu
    slot: int
    amount: int
    hp_left: int


@dataclass(frozen=True)
class Healed:
    side: str
    slot: int
    amount: int
    hp_left: int


@dataclass(frozen=True)
class LeaderHealed:
    side: str          # lado do Lider curado
    amount: int
    hp_left: int


@dataclass(frozen=True)
class AtkBuffed:
    side: str
    slot: int
    amount: int
    atk: int           # ATK atual depois do bonus
    temporary: bool


@dataclass(frozen=True)
class AtkBuffExpired:
    side: str
    slot: int
    amount: int
    atk: int           # ATK depois de perder o bonus


@dataclass(frozen=True)
class CatDied:
    side: str
    slot: int
    card: Card


@dataclass(frozen=True)
class LeaderDamaged:
    side: str          # lado do Lider ferido
    amount: int
    hp_left: int


@dataclass(frozen=True)
class EnergyChanged:
    side: str
    energy: int


@dataclass(frozen=True)
class DuelEnded:
    winner: str


Event = (DiceRolled | DrawSkipped | Deadlock | TurnStarted | Drew | CatPlayed
         | EffectPlayed | Attacked | DamageDealt | Healed | LeaderHealed | AtkBuffed
         | AtkBuffExpired | CatDied
         | LeaderDamaged | EnergyChanged | DuelEnded)


@dataclass
class Duel:
    content: Content
    rng: Random
    sides: dict[str, SideState]
    turn_side: str
    first_side: str
    winner: str | None = None
    log: list = field(default_factory=list)
    # Estagnacao (impasse por janela): ver core/duel.py _stall_tick.
    stall_base: dict[str, int] | None = None   # HP dos Lideres no inicio da janela
    stall_half: int = 0                        # fins de turno desde o inicio da janela
    stall_rounds: int = 0                      # rodadas completas sem violacao
    stall_triggered: bool = False


@dataclass
class SideView:
    leader_hp: int
    energy: int
    deck_count: int
    hand_count: int
    hand: list[Card] | None        # None para o lado oculto
    field: list[FieldCat | None]
    turns_taken: int
    leader_hp_max: int = 0
    rule: dict[str, Any] | None = None   # regra propria do chefe (exibicao)


@dataclass
class DuelView:
    side: str
    turn_side: str
    winner: str | None
    me: SideView
    opponent: SideView
