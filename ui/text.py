"""Textos em portugues da UI (puro: sem pygame). Nenhuma regra aqui, so formatacao."""
from __future__ import annotations

from typing import Any

from core.types import (
    Attacked, AtkBuffExpired, AtkBuffed, CatDied, CatPlayed, Card, DamageDealt, Deadlock,
    DiceRolled, Drew, DrawSkipped, DuelEnded, DuelView, EffectPlayed, EnergyChanged, Healed,
    LeaderDamaged, LeaderHealed, TurnStarted,
)

SIDE_NAME = {"player": "Você", "enemy": "Inimigo"}
SEX_NAME = {"M": "Macho", "F": "Fêmea"}


def label(card: Card) -> str:
    """Nome para mostrar: nome dado ao gato ou, na falta, a raça."""
    return card.cat_name or card.breed_name or card.name


def side_view(shown: DuelView, side: str):
    return shown.me if side == "player" else shown.opponent


def cat_label(shown: DuelView, side: str, slot: int) -> str:
    fc = side_view(shown, side).field[slot]
    return label(fc.card) if fc is not None else "gato"


def owner_tag(side: str) -> str:
    return "seu" if side == "player" else "inimigo"


def describe(ev: Any, shown: DuelView) -> tuple[str, str] | None:
    """Linha de log (texto, lado de cor) do evento, lida ANTES de aplicar o evento ao `shown`."""
    if isinstance(ev, DiceRolled):
        return (f"Dado: {'você começa' if ev.first == 'player' else 'o inimigo começa'}", ev.first)
    if isinstance(ev, TurnStarted):
        return (f"-- Turno {ev.turn} de {SIDE_NAME[ev.side]} --", ev.side)
    if isinstance(ev, Drew):
        if ev.side == "player":
            return (f"Você compra {label(ev.card)}", "player")
        return ("Inimigo compra uma carta", "enemy")
    if isinstance(ev, DrawSkipped):
        if ev.side == "player":
            return ("Mão cheia: a compra foi pulada", "warn")
        return ("Inimigo: mão cheia, compra pulada", "enemy")
    if isinstance(ev, CatPlayed):
        return (f"{SIDE_NAME[ev.side]} joga {label(ev.card)}", ev.side)
    if isinstance(ev, EffectPlayed):
        if ev.card.kind == "special":
            return (f"{ev.card.name}: efeito ao entrar", ev.side)
        return (f"{SIDE_NAME[ev.side]} usa {ev.card.name}", ev.side)
    if isinstance(ev, LeaderHealed):
        who = "Seu Líder" if ev.side == "player" else "Líder inimigo"
        return (f"{who} recupera {ev.amount} HP ({ev.hp_left} HP)", "good")
    if isinstance(ev, AtkBuffed):
        tag = " neste turno" if ev.temporary else ""
        return (f"{cat_label(shown, ev.side, ev.slot)} ({owner_tag(ev.side)}) ganha "
                f"+{ev.amount} ATK{tag}", "good")
    if isinstance(ev, AtkBuffExpired):
        return (f"{cat_label(shown, ev.side, ev.slot)} ({owner_tag(ev.side)}) perde o bônus "
                f"de ATK", ev.side)
    if isinstance(ev, Attacked):
        a = cat_label(shown, ev.side, ev.attacker_slot)
        foe = "enemy" if ev.side == "player" else "player"
        tgt = "o Líder" if ev.target[0] == "leader" else cat_label(shown, foe, ev.target[1])
        return (f"{SIDE_NAME[ev.side]}: {a} ataca {tgt}", ev.side)
    if isinstance(ev, DamageDealt):
        return (f"{cat_label(shown, ev.side, ev.slot)} ({owner_tag(ev.side)}) leva {ev.amount} "
                f"de dano", ev.side)
    if isinstance(ev, Healed):
        return (f"{cat_label(shown, ev.side, ev.slot)} ({owner_tag(ev.side)}) recupera "
                f"{ev.amount} HP", "good")
    if isinstance(ev, CatDied):
        return (f"{label(ev.card)} ({owner_tag(ev.side)}) foi derrotado", ev.side)
    if isinstance(ev, LeaderDamaged):
        who = "Seu Líder" if ev.side == "player" else "Líder inimigo"
        return (f"{who} leva {ev.amount} de dano ({ev.hp_left} HP)", ev.side)
    if isinstance(ev, Deadlock):
        return ("Impasse! Os Líderes decidem na pancada", "warn")
    if isinstance(ev, DuelEnded):
        return ("Você venceu!" if ev.winner == "player" else "Você perdeu!",
                "good" if ev.winner == "player" else "bad")
    if isinstance(ev, EnergyChanged):
        return None
    return None


def energy_short_reason(card: Card, energy: int) -> list[str]:
    need = card.cost - energy
    return ["FALTAM", f"{need} ENERGIA" if need != 1 else "1 ENERGIA"]


def stars(n: int | None) -> str:
    return "?" if n is None else f"{n}/5"


# ------------------------------------------------------------------ descricao de acoes
# Apenas apresentacao: traduz o dict de data/ em texto. Nenhuma regra e decidida aqui.
_TARGET_SHORT = {"inimigo_escolhido": "gato inimigo", "aliado_escolhido": "gato aliado",
                 "lider_inimigo": "Líder inimigo", "lider_proprio": "seu Líder",
                 "nenhum": ""}
_TARGET_LONG = {"inimigo_escolhido": "a um gato inimigo à sua escolha",
                "aliado_escolhido": "a um gato aliado à sua escolha",
                "lider_inimigo": "ao Líder inimigo", "lider_proprio": "ao seu Líder",
                "nenhum": ""}


_TARGET_OF = {"inimigo_escolhido": "de um gato inimigo à sua escolha",
              "aliado_escolhido": "de um gato aliado à sua escolha",
              "lider_inimigo": "do Líder inimigo", "lider_proprio": "do seu Líder"}


def action_short(act: dict) -> tuple[str, str]:
    """(manchete, alvo) curtos de uma acao: ('3 DANO', 'gato inimigo')."""
    v, kind = act.get("valor", 0), act.get("tipo")
    tgt = _TARGET_SHORT.get(act.get("alvo", "nenhum"), "")
    if kind == "dano":
        return f"{v} DANO", tgt
    if kind == "cura":
        return f"CURA {v}", tgt
    if kind == "buff_atk":
        return f"+{v} ATK", (tgt + " (turno)").strip() if act.get("duracao", "turno") == "turno" else tgt
    if kind == "comprar":
        return f"COMPRA {v}", ""
    if kind == "energia":
        return f"+{v} ENERGIA", ""
    return str(kind or "?").upper(), tgt


def action_sentence(act: dict) -> str:
    v, kind = act.get("valor", 0), act.get("tipo")
    tgt = _TARGET_LONG.get(act.get("alvo", "nenhum"), "")
    if kind == "dano":
        return f"Causa {v} de dano {tgt}."
    if kind == "cura":
        return f"Cura {v} de vida {_TARGET_OF.get(act.get('alvo', ''), '')}."
    if kind == "buff_atk":
        dur = "neste turno" if act.get("duracao", "turno") == "turno" else "permanente"
        return f"Dá +{v} de ATK ({dur}) {tgt}."
    if kind == "comprar":
        return f"Compra {v} carta{'s' if v != 1 else ''}."
    if kind == "energia":
        return f"Ganha {v} de energia."
    return ""


def card_summary(card: Card) -> list[str]:
    """Linhas curtas do efeito da carta (cabem no cartao 62 px)."""
    out: list[str] = []
    for act in card.actions:
        head, tgt = action_short(act)
        out.append(head)
        if tgt:
            out.append(tgt)
    return out


def card_sentences(card: Card) -> list[str]:
    return [s for s in (action_sentence(a) for a in card.actions) if s]


_SMALL = {"de", "da", "do", "das", "dos"}


def rule_name(rule: dict) -> str:
    """Nome de exibicao da regra propria (derivado do id, ate o data/ trazer um nome)."""
    if rule.get("nome"):
        return str(rule["nome"])
    parts = str(rule.get("id", "regra")).replace("_", "-").split("-")
    return " ".join(p if (i and p in _SMALL) else p.capitalize() for i, p in enumerate(parts))


_TRIGGER = {"inicio_turno_proprio": "No início do turno dele"}


def rule_text(rule: dict) -> str:
    if rule.get("texto"):
        return str(rule["texto"])
    acts = rule.get("acao", rule.get("acoes"))
    acts = [acts] if isinstance(acts, dict) else list(acts or [])
    body = " ".join(action_sentence(a) for a in acts)
    return f"{_TRIGGER.get(rule.get('gatilho'), 'Regra própria')}: {body}"
