"""Fim da run: moedas (rules.economy), historico dos gatos, lifetime e Prestigio.

Ordem na UI ao fechar a run: `close_run` -> `advance_after_run` -> `create_adoption`
-> UM unico `write_save`. As moedas da doacao seguem em `donate_offer`/`donate_cat`."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.prestige import update_prestige
from core.run import Run
from core.save import SaveData
from core.types import Content, IllegalAction

__all__ = ["RunSettlement", "run_earnings", "close_run"]

# tipo de no do mapa -> chave de rules.economy
_NODE_COIN_KEY = (("batalha", "coins_battle_node"), ("elite", "coins_elite_node"),
                  ("chefe", "coins_boss_node"))
FIRST_LEAGUE_WIN = "primeira-vitoria-liga"


@dataclass
class RunSettlement:
    earnings: list[tuple[str, int]] = field(default_factory=list)   # (fonte, moedas)
    coins: int = 0                  # total creditado (soma de earnings)
    counted: bool = False           # a run contou (>= min_nodes_for_run_count nos)
    first_league_win: bool = False
    league_cleared: bool = False
    prestige_before: int = 1
    prestige_after: int = 1

    @property
    def prestige_up(self) -> bool:
        return self.prestige_after > self.prestige_before


def _eco(content: Content) -> dict[str, Any]:
    return content.rules.get("economy", {}) or {}


DEFAULT_LEAGUE = 1   # so vale enquanto data/run.json nao traz o campo `league`


def _league(run: Run) -> int:
    """Liga da run: campo explicito `league` de data/run.json. Se o campo faltar
    (JSON antigo), usa DEFAULT_LEAGUE; um valor presente e invalido levanta erro."""
    if "league" not in run.cfg:
        return DEFAULT_LEAGUE
    league = run.cfg["league"]
    if isinstance(league, bool) or not isinstance(league, int) or league < 1:
        raise ValueError(f"run.json: 'league' deve ser inteiro >= 1, veio {league!r}")
    return league


def run_earnings(content: Content, run: Run, first_league_win: bool = False
                 ) -> list[tuple[str, int]]:
    """Moedas por fonte pelo que a run venceu (so fontes com valor > 0).
    Fontes: 'batalha', 'elite', 'chefe', 'primeira-vitoria-liga'."""
    eco = _eco(content)
    out = [(tipo, run.wins.get(tipo, 0) * int(eco.get(key, 0)))
           for tipo, key in _NODE_COIN_KEY]
    if first_league_win:
        out.append((FIRST_LEAGUE_WIN, int(eco.get("league1_first_win_bonus", 0))))
    return [(src, v) for src, v in out if v > 0]


def _min_nodes(content: Content) -> int:
    return int((content.rules.get("breed", {}) or {}).get("min_nodes_for_run_count", 1))


def _credit_history(save: SaveData, run: Run, counted: bool) -> None:
    duels = sum(run.wins.values())
    bosses = run.wins.get("chefe", 0)
    by_id = {c.id: c for c in save.cats}
    for rc in run.cats:
        cat = by_id.get(rc.id)
        if cat is None:
            continue
        cat.history["runs"] += 1 if counted else 0
        cat.history["duels_won"] += duels
        cat.history["bosses_defeated"] += bosses


def close_run(content: Content, save: SaveData, run: Run) -> RunSettlement:
    """Fecha a run no save: moedas, historico dos gatos do deck, lifetime, liga
    vencida e Prestigio. Run abandonada/derrotada paga so o que venceu. Uma vez
    por run (IllegalAction se repetir)."""
    if run.status != "finished":
        raise IllegalAction("close_run: a run ainda nao terminou")
    if run.settled:
        raise IllegalAction("close_run: run ja contabilizada")
    league = _league(run)
    won = run.result == "vitoria"
    first = won and league == 1 and not save.first_league_win_claimed
    out = RunSettlement(prestige_before=save.prestige)
    out.earnings = run_earnings(content, run, first)
    out.coins = sum(v for _, v in out.earnings)
    out.counted = run.nodes_cleared >= _min_nodes(content)
    out.first_league_win, out.league_cleared = first, won
    save.coins += out.coins
    if first:
        save.first_league_win_claimed = True
    if won:
        save.progress["leagues_cleared"] = max(save.progress.get("leagues_cleared", 0), league)
    save.lifetime["runs_completed"] += 1 if out.counted else 0
    save.lifetime["duels_won"] += sum(run.wins.values())
    _credit_history(save, run, out.counted)
    out.prestige_after = update_prestige(content, save)
    run.settled = True
    return out
