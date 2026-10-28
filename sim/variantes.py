"""Variantes de balanceamento rodadas em memoria (nunca editam data/).

Uso: python -m sim.variantes --duelos 1000 --seed 1 [--variante nome ...] [--jobs 4] [--lista]

Cada variante = custos de raca + sobrescritas de rules["duel"] (suportadas pelo core)
+ "handicap" assimetrico emulado dentro do simulador (precisa de core para virar regra).
"""
from __future__ import annotations

import argparse
import copy
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import Content, load_content  # noqa: E402
from sim import run as R  # noqa: E402


@dataclass(frozen=True)
class Variante:
    nome: str
    desc: str
    custos: dict[str, int] = field(default_factory=dict)       # id da raca -> custo
    regras: dict[str, object] = field(default_factory=dict)    # chaves de rules["duel"]
    handicap: dict[str, int] = field(default_factory=dict)     # emulado no sim (precisa de core)

    @property
    def precisa_core(self) -> bool:
        return bool(self.handicap)


def aplicar(content: Content, v: Variante) -> Content:
    """Copia profunda do conteudo com a variante aplicada. O original e os arquivos ficam intactos."""
    breeds = copy.deepcopy(content.breeds)
    for bid, custo in v.custos.items():
        if bid not in breeds:
            raise KeyError(f"raca desconhecida: {bid}")
        breeds[bid]["custo"] = custo
    rules = copy.deepcopy(content.rules)
    for k, val in v.regras.items():
        if k not in rules["duel"]:
            raise KeyError(f"regra desconhecida: {k}")
        rules["duel"][k] = val
    extras = dict(content.extras)
    if v.handicap:
        extras["sim_handicap"] = dict(v.handicap)
    return replace(content, breeds=breeds, rules=rules, extras=extras)


def _mk(nome, desc, custos=None, regras=None, handicap=None) -> Variante:
    return Variante(nome, desc, custos or {}, regras or {}, handicap or {})


A = {"second_turn1_energy_bonus": 1}      # (a) 2o jogador: energia 3 no 1o turno
A2 = {"second_energy_bonus_all": 1}       # (a') 2o jogador: +1 energia em todos os turnos
B = {"second_extra_cards": 1}             # (b) 2o jogador: mao inicial 5 vs 4
C = {"first_turn1_energy_penalty": 1}     # (c) 1o jogador: energia 1 no 1o turno
MC4, MC3 = {"maine-coon": 4}, {"maine-coon": 3}

_LISTA = [
    _mk("base", "Dados atuais"),
    # --- vantagem de quem comeca
    _mk("a-seg-e3", "2o jogador com energia 3 no 1o turno", handicap=A),
    _mk("a2-seg-e+1", "2o jogador com +1 energia em todo turno", handicap=A2),
    _mk("b-seg-mao5", "2o jogador com mao inicial 5 (1o com 4)", handicap=B),
    _mk("c-prim-e1", "1o jogador com energia 1 no 1o turno", handicap=C),
    _mk("ab", "a + b", handicap={**A, **B}),
    _mk("ac", "a + c", handicap={**A, **C}),
    _mk("bc", "b + c", handicap={**B, **C}),
    _mk("abc", "a + b + c", handicap={**A, **B, **C}),
    _mk("d-sem-compra-1o", "Sem compra no 1o turno (ambos)", regras={"draw_on_first_turn": False}),
    _mk("d-mao5-ambos", "Mao inicial 5 para ambos", regras={"initial_hand": 5}),
    _mk("d-energia3-ambos", "Energia inicial 3 para ambos", regras={"energy_start": 3}),
    _mk("a-k2", "2o jogador +1 energia nos 2 primeiros turnos",
        handicap={"second_turn1_energy_bonus": 1, "second_bonus_turns": 2}),
    _mk("a-k3", "2o jogador +1 energia nos 3 primeiros turnos",
        handicap={"second_turn1_energy_bonus": 1, "second_bonus_turns": 3}),
    _mk("e-lider+2", "2o jogador com Lider +2 HP", handicap={"second_leader_hp_bonus": 2}),
    _mk("e-lider+4", "2o jogador com Lider +4 HP", handicap={"second_leader_hp_bonus": 4}),
    _mk("a-lider+2", "a + Lider do 2o +2 HP", handicap={**A, "second_leader_hp_bonus": 2}),
    _mk("c-lider+2", "c + Lider do 2o +2 HP", handicap={**C, "second_leader_hp_bonus": 2}),
    # --- custos (energia como hoje)
    _mk("mc4", "Maine Coon custo 4", custos=MC4),
    _mk("mc3", "Maine Coon custo 3", custos=MC3),
    _mk("siames4", "Siames custo 4", custos={"siames": 4}),
    _mk("persa2", "Persa custo 2", custos={"persa": 2}),
    _mk("sphynx2", "Sphynx custo 2", custos={"sphynx": 2}),
    _mk("sphynx4", "Sphynx custo 4", custos={"sphynx": 4}),
    _mk("vira1", "Vira-lata custo 1", custos={"vira-lata": 1}),
    _mk("custos1", "Maine Coon 4, Siames 4, Persa 2",
        custos={"maine-coon": 4, "siames": 4, "persa": 2}),
    _mk("custos2", "Maine Coon 3, Siames 4, Persa 2",
        custos={"maine-coon": 3, "siames": 4, "persa": 2}),
    _mk("custos3", "Maine Coon 4, Siames 4, Persa 2, Sphynx 2",
        custos={"maine-coon": 4, "siames": 4, "persa": 2, "sphynx": 2}),
    _mk("custos4", "Maine Coon 3, Siames 4, Persa 2, Sphynx 2, Vira-lata 1",
        custos={"maine-coon": 3, "siames": 4, "persa": 2, "sphynx": 2, "vira-lata": 1}),
    # --- pacotes de custos (energia como hoje) para a 2a rodada
    _mk("pacote-A", "Persa 2, Maine Coon 4; 1o jogador com energia 1 no 1o turno",
        custos={"persa": 2, "maine-coon": 4}, handicap=C),
    _mk("pacote-B", "Persa 2, Maine Coon 3; 2o jogador +1 energia nos 2 primeiros turnos",
        custos={"persa": 2, "maine-coon": 3}, handicap={"second_turn1_energy_bonus": 1, "second_bonus_turns": 2}),
    _mk("pacote-C", "Siames 4, Persa 2, Maine Coon 3 (Vira-lata 2, Sphynx 3 iguais); 2o jogador +1 energia nos 2 primeiros turnos",
        custos={"siames": 4, "persa": 2, "maine-coon": 3}, handicap={"second_turn1_energy_bonus": 1, "second_bonus_turns": 2}),
    _mk("pacote-A2", "Persa 2, Maine Coon 4; 2o jogador +1 energia nos 3 primeiros turnos",
        custos={"persa": 2, "maine-coon": 4}, handicap={"second_turn1_energy_bonus": 1, "second_bonus_turns": 3}),
    _mk("pacote-B2", "Persa 2, Maine Coon 3; 2o jogador +1 energia nos 3 primeiros turnos",
        custos={"persa": 2, "maine-coon": 3}, handicap={"second_turn1_energy_bonus": 1, "second_bonus_turns": 3}),
    _mk("pacote-B3", "Persa 2, Maine Coon 3; 1o jogador energia 1 no 1o turno",
        custos={"persa": 2, "maine-coon": 3}, handicap=C),
    _mk("pacote-C2", "Siames 4, Persa 2, Maine Coon 3; 2o jogador +1 energia nos 3 primeiros turnos",
        custos={"siames": 4, "persa": 2, "maine-coon": 3}, handicap={"second_turn1_energy_bonus": 1, "second_bonus_turns": 3}),
    _mk("pacote-C3", "Siames 4, Persa 2, Maine Coon 3; 1o jogador energia 1 no 1o turno",
        custos={"siames": 4, "persa": 2, "maine-coon": 3}, handicap=C),
    _mk("p-persa2-mc4", "Persa 2, Maine Coon 4", custos={"persa": 2, "maine-coon": 4}),
    _mk("p-persa2-mc3", "Persa 2, Maine Coon 3", custos={"persa": 2, "maine-coon": 3}),
    _mk("p-persa2-mc4-vira3", "Persa 2, Maine Coon 4, Vira-lata 3 (sem Siames 4)",
        custos={"persa": 2, "maine-coon": 4, "vira-lata": 3}),
    _mk("p-persa2-mc3-sph4", "Persa 2, Maine Coon 3, Sphynx 4",
        custos={"persa": 2, "maine-coon": 3, "sphynx": 4}),
    _mk("p-persa2-mc3-sph4-vira1", "Persa 2, Maine Coon 3, Sphynx 4, Vira-lata 1",
        custos={"persa": 2, "maine-coon": 3, "sphynx": 4, "vira-lata": 1}),
]
VARIANTES: dict[str, Variante] = {v.nome: v for v in _LISTA}


def registrar(v: Variante) -> None:
    VARIANTES[v.nome] = v


# ------------------------------------------------------------------ medicao
def medir(content: Content, v: Variante, seed: int, n: int) -> dict:
    """Metricas resumidas de uma variante. Determinístico por (variante, seed, n)."""
    c = aplicar(content, v)
    base = R.exp_baseline(c, seed, 2 * n)
    races = R.exp_races(c, seed, n)
    rr = R.exp_round_robin(c, seed, max(50, n // 5))
    wins = {b: 0 for b in c.breeds}
    games = dict(wins)
    for (x, y), s in rr.items():
        wins[x] += s.wins_a
        wins[y] += s.decided - s.wins_a
        games[x] += s.decided
        games[y] += s.decided
    marg = R.exp_marginal(c, seed, n)
    iv51 = R.exp_paired(c, seed, n, 200, R.fixed_iv(5), R.fixed_iv(1))
    iv53 = R.exp_paired(c, seed, n, 202, R.fixed_iv(5), R.fixed_iv(3))
    one5 = R.exp_one_perfect(c, seed, n, 5, 5, 300)
    nat = {}
    ids = list(c.natures)
    k = 0
    for i, x in enumerate(ids):
        for y in ids[i + 1:]:
            nat[(x, y)] = R.exp_paired(c, seed, n, 400 + k, R.nature_iv3(x), R.nature_iv3(y)).rate
            k += 1
    allst = [base, *races.values(), *rr.values(), *marg.values(), iv51, iv53, one5]
    return {
        "first": base.first_wins / max(1, base.decided),
        "turns": sum(sum(s.turns) for s in allst) / max(1, sum(len(s.turns) for s in allst)),
        "mono": {b: s.rate for b, s in races.items()},
        "rr": {b: wins[b] / max(1, games[b]) for b in wins},
        "marg": {b: s.rate for b, s in marg.items()},
        "iv51": iv51.rate, "iv53": iv53.rate, "one5": one5.rate,
        "nat": nat,
        "errors": sum(s.errors for s in allst), "deadlocks": sum(s.deadlocks for s in allst),
        "duels": sum(s.n for s in allst),
    }


def _medir_job(args):
    nome, seed, n = args
    return nome, medir(load_content(ROOT / "data"), VARIANTES[nome], seed, n)


def tabela(content: Content, resultados: dict[str, dict]) -> str:
    breeds = list(content.breeds)
    nomes = [content.breeds[b]["nome"] for b in breeds]
    p = R.pct
    out = ["## Vantagem de quem comeca e duracao\n",
           "| Variante | O que muda | Core | 1o vence | Turnos medios |", "|---|---|---|---|---|"]
    for n, r in resultados.items():
        v = VARIANTES[n]
        out.append(f"| {n} | {v.desc} | {'precisa' if v.precisa_core else 'dados'} | {p(r['first'])} | {r['turns']:.1f} |")
    out += ["\n## Vitoria por raca (deck mono-raca vs misto / agregado no round-robin)\n",
            "| Variante | " + " | ".join(nomes) + " |", "|---|" + "---|" * len(breeds)]
    for n, r in resultados.items():
        cells = [f"{p(r['mono'][b])} / {p(r['rr'][b])}" for b in breeds]
        out.append(f"| {n} | " + " | ".join(cells) + " |")
    out += ["\n## Peso da raca num deck realista (4 gatos da raca + 8 mistos vs misto)\n",
            "| Variante | " + " | ".join(nomes) + " |", "|---|" + "---|" * len(breeds)]
    for n, r in resultados.items():
        out.append(f"| {n} | " + " | ".join(p(r['marg'][b]) for b in breeds) + " |")
    nat_keys = list(next(iter(resultados.values()))["nat"])
    cab = [f"{content.natures[x]['nome']} x {content.natures[y]['nome']}" for x, y in nat_keys]
    out += ["\n## Peso do IV e da natureza (vitoria de A)\n",
            "| Variante | IV 5/5 vs 1/1 | IV 5/5 vs 3/3 | 1 gato 5/5 | " + " | ".join(cab) + " |",
            "|---|---|---|---|" + "---|" * len(cab)]
    for n, r in resultados.items():
        out.append(f"| {n} | {p(r['iv51'])} | {p(r['iv53'])} | {p(r['one5'])} | "
                   + " | ".join(p(r['nat'][k]) for k in nat_keys) + " |")
    return "\n".join(out) + "\n"


def rodar(nomes: list[str], seed: int, n: int, jobs: int = 1) -> tuple[str, dict[str, dict]]:
    content = load_content(ROOT / "data")
    if jobs > 1:
        with ProcessPoolExecutor(jobs) as ex:
            res = dict(ex.map(_medir_job, [(nm, seed, n) for nm in nomes]))
    else:
        res = {nm: medir(content, VARIANTES[nm], seed, n) for nm in nomes}
    ordered = {nm: res[nm] for nm in nomes}
    cab = (f"# Variantes de balanceamento (seed {seed}, {n} duelos por experimento; "
           f"quem comeca medido com {2 * n})\n\n"
           "Valores 'a / b' = mono-raca vs misto / agregado round-robin. IA simples dos dois lados.\n\n")
    return cab + tabela(content, ordered), ordered


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sim.variantes")
    ap.add_argument("--duelos", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--variante", nargs="*", help="nomes (padrao: todas)")
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--lista", action="store_true")
    ap.add_argument("--saida", type=Path, default=ROOT / "sim" / "variantes_resultado.md")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.lista:
        for v in VARIANTES.values():
            print(f"{v.nome}: {v.desc}" + (" [precisa de core]" if v.precisa_core else ""))
        return 0
    nomes = args.variante or list(VARIANTES)
    t0 = time.time()
    texto, res = rodar(nomes, args.seed, args.duelos, args.jobs)
    args.saida.write_text(texto, encoding="utf-8")
    print(texto)
    print(f"[tempo {time.time() - t0:.1f}s]")
    return 1 if any(r["errors"] for r in res.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
