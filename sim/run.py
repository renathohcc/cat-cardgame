"""Simulador de balanceamento: duelos IA vs IA deterministicos por seed.

Uso: python -m sim.run --duelos 1000 --seed 1 [--saida caminho.md]
O relatorio nao contem tempo de execucao (duas execucoes = saida identica).
"""
from __future__ import annotations

import argparse
import math
import sys
import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from random import Random
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import Cat, Content, load_content, roll_cat  # noqa: E402
from core.ai import choose_action  # noqa: E402
from core.duel import apply_action, is_over, new_duel  # noqa: E402
from core.types import Deadlock, DeckSpec  # noqa: E402

TURN_CAP = 200       # teto de seguranca: soma de turnos dos dois lados (so no simulador)
MAX_ACTIONS = 5000   # protecao extra contra loop de acoes
DECK = 12

Variant = Callable[[Cat, Random], Cat]


@dataclass
class Result:
    winner: str | None
    turns: int
    deadlock: bool
    capped: bool
    error: str | None = None


@dataclass
class Stats:
    n: int = 0
    wins_a: int = 0          # vitorias do lado A ("player")
    first_wins: int = 0      # vitorias de quem comecou
    decided: int = 0
    turns: list[int] = field(default_factory=list)
    deadlocks: int = 0
    capped: int = 0
    errors: int = 0

    def add(self, r: Result, a_first: bool) -> None:
        self.n += 1
        self.turns.append(r.turns)
        self.deadlocks += r.deadlock
        self.capped += r.capped
        self.errors += r.error is not None
        if r.winner is None:
            return
        a_won = r.winner == "player"
        self.wins_a += a_won
        self.decided += 1
        self.first_wins += a_won == a_first

    @property
    def rate(self) -> float:
        return self.wins_a / self.decided if self.decided else float("nan")


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return ((c - m) / d, (c + m) / d)


def pct(x: float) -> str:
    return f"{100 * x:.1f}%"


def _second(duel) -> str:
    return "enemy" if duel.first_side == "player" else "player"


def apply_handicap_start(duel, hc: dict) -> None:
    """Emula (em memoria) ajustes assimetricos que o core ainda nao suporta por dados."""
    first, second = duel.first_side, _second(duel)
    duel.sides[first].energy = max(0, duel.sides[first].energy - hc.get("first_turn1_energy_penalty", 0))
    st = duel.sides[second]
    st.leader_hp += hc.get("second_leader_hp_bonus", 0)
    st.leader_hp_max += hc.get("second_leader_hp_bonus", 0)
    for _ in range(hc.get("second_extra_cards", 0)):
        if st.deck and len(st.hand) < duel.content.rules["duel"]["hand_max"]:
            st.hand.append(st.deck.pop(0))


def apply_handicap_turn(duel, hc: dict, cap: int) -> None:
    """Chamado logo depois de um turno comecar (troca de lado)."""
    second = _second(duel)
    if duel.turn_side != second:
        return
    st = duel.sides[second]
    bonus = hc.get("second_energy_bonus_all", 0)
    if st.turns_taken <= hc.get("second_bonus_turns", 1):
        bonus += hc.get("second_turn1_energy_bonus", 0)
    st.energy = min(cap, st.energy + bonus)


def run_duel(content: Content, rng: Random, a: list[Cat], b: list[Cat],
             player_first: bool | None) -> tuple[Result, bool]:
    """Roda um duelo IA vs IA. Devolve (resultado, A comecou)."""
    try:
        duel = new_duel(content, rng, DeckSpec(a), DeckSpec(b), player_first)
        a_first = duel.first_side == "player"
        hc = content.extras.get("sim_handicap")
        if hc:
            apply_handicap_start(duel, hc)
        actions = 0
        while is_over(duel) is None:
            total = sum(s.turns_taken for s in duel.sides.values())
            actions += 1
            if total >= TURN_CAP or actions > MAX_ACTIONS:
                return Result(None, total, False, True), a_first
            before = duel.turn_side
            apply_action(duel, choose_action(duel, duel.turn_side, rng))
            if hc and duel.turn_side != before and is_over(duel) is None:
                apply_handicap_turn(duel, hc, content.rules["duel"]["energy_cap"])
        total = sum(s.turns_taken for s in duel.sides.values())
        dead = any(isinstance(e, Deadlock) for e in duel.log)
        return Result(is_over(duel), total, dead, False), a_first
    except Exception as exc:  # noqa: BLE001 - contar excecoes e requisito
        return Result(None, 0, False, False, f"{type(exc).__name__}: {exc}"), True


def deck_of(content: Content, rng: Random, breed: str | None = None) -> list[Cat]:
    return [replace(roll_cat(content, rng, breed), id=f"c-{i}") for i in range(DECK)]


def with_iv(c: Cat, atk: int, hp: int) -> Cat:
    return replace(c, iv_atk=atk, iv_hp=hp)


# ------------------------------------------------------------ experimentos
def exp_baseline(content: Content, seed: int, n: int) -> Stats:
    """Misto vs misto, mesma distribuicao; o dado decide quem comeca."""
    rng = Random(seed * 1000 + 1)
    st = Stats()
    for _ in range(n):
        a, b = deck_of(content, rng), deck_of(content, rng)
        r, af = run_duel(content, rng, a, b, None)
        st.add(r, af)
    return st


def exp_races(content: Content, seed: int, n: int) -> dict[str, Stats]:
    """Deck mono-raca (A) vs deck misto aleatorio (B); dado decide quem comeca."""
    out = {}
    for k, breed in enumerate(content.breeds):
        rng = Random(seed * 1000 + 10 + k)
        st = Stats()
        for _ in range(n):
            a, b = deck_of(content, rng, breed), deck_of(content, rng)
            r, af = run_duel(content, rng, a, b, None)
            st.add(r, af)
        out[breed] = st
    return out


def exp_round_robin(content: Content, seed: int, n_pair: int) -> dict[tuple[str, str], Stats]:
    """Mono-raca vs mono-raca; quem comeca alterna para anular a vantagem de iniciar."""
    out = {}
    breeds = list(content.breeds)
    for i, x in enumerate(breeds):
        for j, y in enumerate(breeds):
            if i >= j:
                continue
            rng = Random(seed * 1000 + 100 + i * 10 + j)
            st = Stats()
            for t in range(n_pair):
                a, b = deck_of(content, rng, x), deck_of(content, rng, y)
                r, af = run_duel(content, rng, a, b, t % 2 == 0)
                st.add(r, af)
            out[(x, y)] = st
    return out


def exp_marginal(content: Content, seed: int, n: int, copies: int = 4) -> dict[str, Stats]:
    """Deck A = `copies` gatos da raca + resto misto vs deck misto B; quem comeca alterna.

    Mede o peso de uma raca num deck realista (mais util que mono-raca, que e extremo).
    """
    out = {}
    for k, breed in enumerate(content.breeds):
        rng = Random(seed * 1000 + 600 + k)
        st = Stats()
        for t in range(n):
            a = [replace(roll_cat(content, rng, breed if i < copies else None), id=f"c-{i}")
                 for i in range(DECK)]
            b = deck_of(content, rng)
            r, af = run_duel(content, rng, a, b, t % 2 == 0)
            st.add(r, af)
        out[breed] = st
    return out


def exp_paired(content: Content, seed: int, n: int, salt: int,
               va: Variant, vb: Variant) -> Stats:
    """Decks mistos sorteados; A e B recebem variantes (IV/natureza). Quem comeca alterna.

    A e B vem de bases diferentes (sorteios independentes), entao o ruido de composicao
    e comum aos dois lados e o controle (mesma variante dos dois lados) mede esse ruido.
    """
    rng = Random(seed * 1000 + salt)
    st = Stats()
    for t in range(n):
        base_a, base_b = deck_of(content, rng), deck_of(content, rng)
        a = [va(c, rng) for c in base_a]
        b = [vb(c, rng) for c in base_b]
        r, af = run_duel(content, rng, a, b, t % 2 == 0)
        st.add(r, af)
    return st


def exp_one_perfect(content: Content, seed: int, n: int, atk: int, hp: int, salt: int) -> Stats:
    """Um unico gato (slot 0) com IV fixo no deck A; o resto, A e B, sorteado pelos pesos reais."""
    rng = Random(seed * 1000 + salt)
    st = Stats()
    for t in range(n):
        a, b = deck_of(content, rng), deck_of(content, rng)
        a[0] = with_iv(a[0], atk, hp)
        r, af = run_duel(content, rng, a, b, t % 2 == 0)
        st.add(r, af)
    return st


def fixed_iv(v: int) -> Variant:
    return lambda c, rng: with_iv(c, v, v)


def real_iv(content: Content) -> Variant:
    ivs = sorted(int(k) for k in content.rules["iv_weights"])
    w = [content.rules["iv_weights"][str(i)] for i in ivs]
    return lambda c, rng: with_iv(c, rng.choices(ivs, w)[0], rng.choices(ivs, w)[0])


def nature_iv3(nat: str) -> Variant:
    return lambda c, rng: with_iv(replace(c, nature=nat), 3, 3)


# ------------------------------------------------------------ relatorio
HEAD = ("| Cenario | Duelos | Vitoria de A | IC 95% | Quem comeca vence | Turnos medios | Turnos max |\n"
        "|---|---|---|---|---|---|---|")


def row(label: str, st: Stats) -> str:
    lo, hi = wilson(st.wins_a, st.decided)
    fw = pct(st.first_wins / st.decided) if st.decided else "-"
    return (f"| {label} | {st.decided} | {pct(st.rate)} | {pct(lo)} a {pct(hi)} | {fw} | "
            f"{sum(st.turns) / max(1, len(st.turns)):.1f} | {max(st.turns, default=0)} |")


def build_report(content: Content, seed: int, n: int) -> tuple[str, int]:
    allst: list[Stats] = []
    base = exp_baseline(content, seed, n)
    races = exp_races(content, seed, n)
    rr_n = max(50, n // 5)
    rr = exp_round_robin(content, seed, rr_n)
    allst += [base, *races.values(), *rr.values()]

    iv_defs: list[tuple[str, Variant, Variant]] = [
        ("IV 5/5 (A) vs IV 1/1 (B)", fixed_iv(5), fixed_iv(1)),
        ("IV 3/3 (A) vs IV 1/1 (B)", fixed_iv(3), fixed_iv(1)),
        ("IV 5/5 (A) vs IV 3/3 (B)", fixed_iv(5), fixed_iv(3)),
        ("IV 3/3 (A) vs IV 3/3 (B) [controle]", fixed_iv(3), fixed_iv(3)),
        ("IV sorteado real (A) vs IV 5/5 (B)", real_iv(content), fixed_iv(5)),
        ("IV sorteado real (A) vs IV 1/1 (B)", real_iv(content), fixed_iv(1)),
    ]
    iv_res = []
    for k, (label, va, vb) in enumerate(iv_defs):
        iv_res.append((label, exp_paired(content, seed, n, 200 + k, va, vb)))
    one5 = exp_one_perfect(content, seed, n, 5, 5, 300)
    one1 = exp_one_perfect(content, seed, n, 1, 1, 301)
    nat_ids = list(content.natures)
    nat_res = []
    k = 0
    for i, x in enumerate(nat_ids):
        for y in nat_ids[i + 1:]:
            nx, ny = content.natures[x], content.natures[y]
            s = exp_paired(content, seed, n, 400 + k, nature_iv3(x), nature_iv3(y))
            nat_res.append((f"{nx['nome']} (A) vs {ny['nome']} (B), IV 3/3", s))
            k += 1
    allst += [s for _, s in iv_res] + [one5, one1] + [s for _, s in nat_res]

    tot = sum(s.n for s in allst)
    turns = sorted(t for s in allst for t in s.turns)
    dead = sum(s.deadlocks for s in allst)
    capped = sum(s.capped for s in allst)
    errs = sum(s.errors for s in allst)

    wins = {b: 0 for b in content.breeds}
    games = {b: 0 for b in content.breeds}
    for (x, y), s in rr.items():
        wins[x] += s.wins_a
        wins[y] += s.decided - s.wins_a
        games[x] += s.decided
        games[y] += s.decided

    md = [f"# Simulacao de balanceamento (seed {seed}, {n} duelos por experimento)\n",
          f"IA simples dos dois lados. Teto de seguranca: {TURN_CAP} turnos somados (so no simulador). "
          f"Round-robin: {rr_n} duelos por par. \"Turnos\" = soma dos turnos dos dois lados. "
          "A = lado player, B = lado enemy.\n",
          "## 1. Metricas gerais\n",
          f"- Duelos totais: {tot}",
          f"- Turnos: media {sum(turns) / len(turns):.1f}, mediana {turns[len(turns) // 2]}, maximo {turns[-1]}",
          f"- Terminaram por impasse (Deadlock): {dead} ({pct(dead / tot)})",
          f"- Atingiram o teto de seguranca: {capped} ({pct(capped / tot)})",
          f"- Duelos com excecao: {errs}\n",
          "## 2. Vantagem de comecar (dado)\n",
          "Misto vs misto, mesma distribuicao; o dado decide quem comeca. 'Quem comeca vence' = vantagem de iniciar (50% = nenhuma).\n",
          HEAD, row("Misto vs misto (dado)", base),
          "\n## 3. Taxa de vitoria por raca\n",
          "A = 12 gatos de uma so raca; B = deck misto aleatorio. IV/natureza/sexo pelos pesos reais; o dado decide quem comeca.\n",
          HEAD]
    md += [row(f"{content.breeds[b]['nome']} vs misto", s) for b, s in races.items()]
    md += ["\n### Round-robin mono-raca (quem comeca alterna)\n", HEAD]
    md += [row(f"{content.breeds[x]['nome']} vs {content.breeds[y]['nome']}", s) for (x, y), s in rr.items()]
    md.append("\nTaxa agregada no round-robin: " + "; ".join(
        f"{content.breeds[b]['nome']} {pct(wins[b] / games[b])}" for b in wins) + ".\n")
    md += ["## 4. Efeito do IV\n",
           "Decks mistos sorteados independentemente para A e B; so os IVs sao sobrescritos (raca/sexo/natureza seguem o sorteio). "
           "O controle 3/3 vs 3/3 mostra o ruido de base. Quem comeca alterna.\n", HEAD]
    md += [row(label, s) for label, s in iv_res]
    md += [row("1 gato IV 5/5 no deck A (resto real) vs B real", one5),
           row("1 gato IV 1/1 no deck A (resto real) vs B real", one1)]
    md += ["\n## 5. Efeito da natureza (IV 3/3 fixo, decks mistos)\n", HEAD]
    md += [row(label, s) for label, s in nat_res]

    obs = []
    for b, s in races.items():
        if not 0.40 <= s.rate <= 0.60:
            obs.append(f"- {content.breeds[b]['nome']} vs misto: {pct(s.rate)} (fora de 40% a 60%).")
    for b in wins:
        r = wins[b] / games[b]
        if not 0.40 <= r <= 0.60:
            obs.append(f"- {content.breeds[b]['nome']} no round-robin: {pct(r)} (fora de 40% a 60%).")
    for label, s in iv_res:
        obs.append(f"- {label}: A vence {pct(s.rate)}.")
    obs.append(f"- Misto vs misto: quem comeca vence {pct(base.first_wins / max(1, base.decided))}.")
    md += ["\n## 6. Indicadores (leitura no relatorio da tarefa)\n"] + obs
    return "\n".join(md) + "\n", errs


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sim.run")
    ap.add_argument("--duelos", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--variante", default=None,
                    help="nome de uma variante de sim/variantes.py (aplicada em memoria)")
    ap.add_argument("--saida", type=Path, default=ROOT / "sim" / "ultimo_resultado.md",
                    help="onde gravar a saida bruta em Markdown")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    content = load_content(ROOT / "data")
    if args.variante:
        from sim.variantes import VARIANTES, aplicar
        content = aplicar(content, VARIANTES[args.variante])
    t0 = time.time()
    text, errs = build_report(content, args.seed, args.duelos)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(text, encoding="utf-8")
    print(text)
    print(f"[tempo {time.time() - t0:.1f}s; saida bruta em {args.saida}]")
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main())
