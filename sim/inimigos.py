"""Simulacao contra os inimigos reais de data/enemies.json (IA nos dois lados).

Uso: python -m sim.inimigos --duelos 300 --seed 1 [--inimigo id ...] [--variante nome ...] [--lista]

Dois tipos de deck do jogador (sorteados pelos pesos reais, IA simples):
  gatos : 12 gatos (raca, IV, natureza, sexo sorteados)
  medio : 6 gatos + 3 Espiritos + 3 efeitos sorteados
O jogador comeca em metade dos duelos e nao comeca na outra metade.
Variantes de inimigo rodam em memoria (copia profunda); data/ nunca e alterado.
"""
from __future__ import annotations

import argparse
import copy
import sys
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from random import Random

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import Content, load_content, roll_cat  # noqa: E402
from core.ai import choose_action  # noqa: E402
from core.duel import (apply_action, card_from_effect, card_from_special,  # noqa: E402
                       is_over, new_duel_vs_enemy)
from core.types import DeckSpec  # noqa: E402
from sim.run import MAX_ACTIONS, TURN_CAP, pct, wilson  # noqa: E402

DECKS = ("gatos", "medio")
ENEMIES = ("tonho-sem-sorte", "irmaos-pimenta", "berenice-da-matilha", "madame-fifi-pelucia")


# ------------------------------------------------------------ variantes de inimigo
@dataclass(frozen=True)
class VarInimigo:
    nome: str
    desc: str
    inimigo: str = "berenice-da-matilha"
    lider_hp: int | None = None
    iv_delta: int = 0                                   # soma aos IVs de todos os gatos (min 1)
    trocas: dict[str, str] = field(default_factory=dict)    # carta -> carta (mantem qtd)
    remove: tuple[str, ...] = ()                         # cartas removidas do deck (todas as copias)
    ivs: dict[str, tuple[int, int]] = field(default_factory=dict)  # raca -> (iv_atk, iv_hp)


def aplicar_inimigo(content: Content, v: VarInimigo) -> Content:
    """Copia do conteudo com a variante aplicada ao inimigo `v.inimigo`. Original intacto."""
    enemies = copy.deepcopy(content.enemies)
    if v.inimigo not in enemies:
        raise KeyError(f"inimigo desconhecido: {v.inimigo}")
    en = enemies[v.inimigo]
    if v.lider_hp is not None:
        en["lider_hp"] = v.lider_hp
    deck = []
    for e in en["deck"]:
        if e["carta"] in v.remove:
            continue
        e = dict(e)
        e["carta"] = v.trocas.get(e["carta"], e["carta"])
        if e["carta"] in content.breeds and "iv_atk" in e:
            if e["carta"] in v.ivs:
                e["iv_atk"], e["iv_hp"] = v.ivs[e["carta"]]
            e["iv_atk"] = max(1, e["iv_atk"] + v.iv_delta)
            e["iv_hp"] = max(1, e["iv_hp"] + v.iv_delta)
        deck.append(e)
    en["deck"] = deck
    return replace(content, enemies=enemies)


_E = "berenice-da-matilha"
VARIANTES: dict[str, VarInimigo] = {v.nome: v for v in [
    VarInimigo("base", "Dados atuais"),
    VarInimigo("e-lider20", "Elite: Lider 22 -> 20 HP", lider_hp=20),
    VarInimigo("e-iv-1", "Elite: todos os IVs dos gatos -1", iv_delta=-1),
    VarInimigo("e-sem-brasas", "Elite: Gata das Brasas (custo 5) -> Velha dos Novelos (custo 2)",
               trocas={"gata-das-brasas": "velha-dos-novelos"}),
    VarInimigo("e-sem-farejar", "Elite: remove Farejar a Despensa", remove=("farejar-a-despensa",)),
    VarInimigo("e-sem-mestre", "Elite: remove Mestre das Garras", remove=("mestre-das-garras",)),
    VarInimigo("e-mc-iv2", "Elite: Maine Coon IV 3/3 -> 2/2", ivs={"maine-coon": (2, 2)}),
    VarInimigo("e-lider20-mc2", "Elite: Lider 20 + Maine Coon IV 2/2", lider_hp=20,
               ivs={"maine-coon": (2, 2)}),
    VarInimigo("e-lider20-brasas", "Elite: Lider 20 + Gata das Brasas -> Velha dos Novelos",
               lider_hp=20, trocas={"gata-das-brasas": "velha-dos-novelos"}),
    VarInimigo("e-mc-iv2-3", "Elite: Maine Coon IV 2/3", ivs={"maine-coon": (2, 3)}),
    VarInimigo("e-lider20-sem-mestre", "Elite: Lider 20 + remove Mestre das Garras",
               lider_hp=20, remove=("mestre-das-garras",)),
    VarInimigo("e-mestre-por-velha", "Elite: Mestre das Garras (custo 4) -> Velha dos Novelos (custo 2)",
               trocas={"mestre-das-garras": "velha-dos-novelos"}),
    VarInimigo("e-sem-mestre-mc2", "Elite: remove Mestre das Garras + Maine Coon IV 2/2",
               remove=("mestre-das-garras",), ivs={"maine-coon": (2, 2)}),
    VarInimigo("e-lider20-iv-1", "Elite: Lider 20 + IVs -1", lider_hp=20, iv_delta=-1),
    VarInimigo("c-lider22", "Chefe: Lider 25 -> 22 HP", inimigo="madame-fifi-pelucia", lider_hp=22),
    VarInimigo("c-iv4", "Chefe: Siames e Sphynx de volta a IV 4/4",
               inimigo="madame-fifi-pelucia", ivs={"siames": (4, 4), "sphynx": (4, 4)}),
]}


# ------------------------------------------------------------ decks do jogador
def player_deck(content: Content, rng: Random, tipo: str) -> DeckSpec:
    if tipo == "gatos":
        cats = [replace(roll_cat(content, rng), id=f"p-{i}") for i in range(12)]
        return DeckSpec(cats=cats)
    if tipo == "medio":
        cats = [replace(roll_cat(content, rng), id=f"p-{i}") for i in range(6)]
        sp = [card_from_special(content, rng.choice(sorted(content.specials))) for _ in range(3)]
        ef = [card_from_effect(content, rng.choice(sorted(content.effects))) for _ in range(3)]
        return DeckSpec(cats=cats, cards=sp + ef)
    raise ValueError(f"tipo de deck desconhecido: {tipo}")


@dataclass
class Resultado:
    n: int = 0
    vitorias: int = 0
    decididos: int = 0
    turnos: list[int] = field(default_factory=list)
    erros: int = 0

    @property
    def taxa(self) -> float:
        return self.vitorias / self.decididos if self.decididos else float("nan")


def duelo(content: Content, rng: Random, tipo: str, inimigo: str, jogador_comeca: bool):
    """Um duelo. Devolve (vencedor|None, turnos)."""
    deck = player_deck(content, rng, tipo)
    d = new_duel_vs_enemy(content, deck, inimigo, rng, jogador_comeca)
    acoes = 0
    while is_over(d) is None:
        total = sum(s.turns_taken for s in d.sides.values())
        acoes += 1
        if total >= TURN_CAP or acoes > MAX_ACTIONS:
            return None, total
        apply_action(d, choose_action(d, d.turn_side, rng))
    return is_over(d), sum(s.turns_taken for s in d.sides.values())


def medir(content: Content, inimigo: str, tipo: str, seed: int, n: int) -> Resultado:
    """n duelos; metade com o jogador comecando. Determinístico por (inimigo, tipo, seed, n)."""
    rng = Random(f"{seed}/{inimigo}/{tipo}")
    r = Resultado()
    for t in range(n):
        r.n += 1
        try:
            w, turnos = duelo(content, rng, tipo, inimigo, t % 2 == 0)
        except Exception:  # noqa: BLE001 - contar excecoes
            r.erros += 1
            continue
        r.turnos.append(turnos)
        if w is not None:
            r.decididos += 1
            r.vitorias += w == "player"
    return r


def medir_variante(content: Content, v: VarInimigo, seed: int, n: int) -> dict[str, Resultado]:
    c = aplicar_inimigo(content, v)
    return {t: medir(c, v.inimigo, t, seed, n) for t in DECKS}


def linha(label: str, r: Resultado) -> str:
    lo, hi = wilson(r.vitorias, r.decididos)
    return (f"| {label} | {r.decididos} | {pct(r.taxa)} | {pct(lo)} a {pct(hi)} | "
            f"{sum(r.turnos) / max(1, len(r.turnos)):.1f} |")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sim.inimigos")
    ap.add_argument("--duelos", type=int, default=300)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--inimigo", nargs="*", help="ids (padrao: os 4)")
    ap.add_argument("--variante", nargs="*", help="variantes de inimigo (rodam so no inimigo delas)")
    ap.add_argument("--lista", action="store_true")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.lista:
        for v in VARIANTES.values():
            print(f"{v.nome}: {v.desc}")
        return 0
    content = load_content(ROOT / "data")
    t0 = time.time()
    head = "| Cenario | Duelos | Jogador vence | IC 95% | Turnos medios |\n|---|---|---|---|---|"
    out = [f"# Jogador vs inimigos reais (seed {args.seed}, {args.duelos} duelos por linha)\n", head]
    erros = 0
    if args.variante:
        for nome in args.variante:
            for t, r in medir_variante(content, VARIANTES[nome], args.seed, args.duelos).items():
                out.append(linha(f"{nome} / deck {t}", r))
                erros += r.erros
    else:
        for en in args.inimigo or ENEMIES:
            for t in DECKS:
                r = medir(content, en, t, args.seed, args.duelos)
                out.append(linha(f"{en} / deck {t}", r))
                erros += r.erros
    print("\n".join(out))
    print(f"[tempo {time.time() - t0:.1f}s]")
    return 1 if erros else 0


if __name__ == "__main__":
    raise SystemExit(main())
