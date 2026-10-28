"""Rodada de balanceamento do nucleo (T6.0): Siames, naturezas, peso dos IVs e gato perfeito por breed.

Uso:
  python -m sim.balanceamento --lista
  python -m sim.balanceamento --tema siames natureza iv breed --duelos 1000 --seeds 1 2 3 --jobs 6 \
      --saida reports/balanceamento_rodada2.md

Tudo roda em memoria (copia profunda do Content; data/ nunca e alterado) e e deterministico por seed:
cada tarefa usa `random.Random` proprio, derivado de (seed, tema, rotulo). Variantes de um mesmo tema
compartilham os mesmos sorteios de decks (comparacao pareada). IA simples (`core.ai`) dos dois lados.
"""
from __future__ import annotations

import argparse
import copy
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path
from random import Random
from statistics import median
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import Cat, Content, load_content, roll_cat  # noqa: E402
from core.adoption import adopt, create_adoption  # noqa: E402
from core.ai import choose_action  # noqa: E402
from core.breeding import advance_after_run, can_breed, start_breed  # noqa: E402
from core.collection import autofill_deck, available_cats, cat_stats, set_deck  # noqa: E402
from core.duel import apply_action, is_over, new_duel  # noqa: E402
from core.run import new_run, new_run_from_save  # noqa: E402
from core.save import SaveData, format_cat_id, new_game, register_dex  # noqa: E402
from core.types import CatPlayed, DeckSpec  # noqa: E402
from sim import run as R  # noqa: E402

TEMAS = ("siames", "natureza", "iv", "breed", "deck")
ESTRATEGIAS = ("nenhuma", "simples", "otima")
Patch = dict[str, Any]


# ------------------------------------------------------------------ utilitarios
def wl(w: int = 0, n: int = 0) -> dict[str, int]:
    return {"w": w, "n": n}


def somar(a: Any, b: Any) -> Any:
    """Soma recursiva: numeros somam, dicts unem chave a chave, listas concatenam."""
    if isinstance(a, dict) and isinstance(b, dict):
        out = dict(a)
        for k, v in b.items():
            out[k] = somar(out[k], v) if k in out else copy.deepcopy(v)
        return out
    if isinstance(a, list) and isinstance(b, list):
        return a + b
    return a + b


def taxa(d: dict[str, int]) -> float:
    return d["w"] / d["n"] if d["n"] else float("nan")


def fmt(d: dict[str, int]) -> str:
    return R.pct(taxa(d)) if d["n"] else "-"


def aplicar_patch(content: Content, patch: Patch) -> Content:
    """Copia profunda do conteudo com `patch` aplicado:
    {"breeds": {id: {campo: v}}, "natures": {id: {campo: v}}, "rules": {secao: {k: v}}}.
    `iv_weights` em rules e substituido por inteiro."""
    breeds = copy.deepcopy(content.breeds)
    for bid, campos in patch.get("breeds", {}).items():
        breeds[bid].update(copy.deepcopy(campos))
    natures = copy.deepcopy(content.natures)
    for nid, campos in patch.get("natures", {}).items():
        natures[nid].update(campos)
    rules = copy.deepcopy(content.rules)
    for sec, kv in patch.get("rules", {}).items():
        if sec == "iv_weights":
            rules[sec] = {str(k): v for k, v in kv.items()}
        else:
            rules[sec].update(kv)
    enemies = copy.deepcopy(content.enemies)
    d = int(patch.get("hp_iv_div", 1))
    if d > 1:
        for en in enemies.values():
            for e in en["deck"]:
                if "iv_hp" in e:
                    e["iv_hp"] = 1 + (e["iv_hp"] - 1) // d
    return replace(content, breeds=breeds, natures=natures, rules=rules, enemies=enemies)


def _rng(*partes: object) -> Random:
    return Random("/".join(str(p) for p in partes))


def jogar_duelo(duel, rng: Random) -> tuple[str | None, int]:
    """Joga um duelo ate o fim com a IA dos dois lados. Devolve (vencedor|None, turnos somados)."""
    acoes = 0
    while is_over(duel) is None:
        total = sum(s.turns_taken for s in duel.sides.values())
        acoes += 1
        if total >= R.TURN_CAP or acoes > R.MAX_ACTIONS:
            return None, total
        apply_action(duel, choose_action(duel, duel.turn_side, rng))
    return is_over(duel), sum(s.turns_taken for s in duel.sides.values())


def jogar_run(content: Content, rng: Random, run) -> tuple[str, int]:
    """Joga uma run inteira com a IA. Mapa e draft escolhidos ao acaso (rng). (resultado, nos vencidos)."""
    while run.status != "finished":
        if run.status == "map":
            run.choose_node(rng.choice(run.available_nodes())["id"])
        elif run.status == "duel":
            duel = run.start_duel(rng)
            w, _ = jogar_duelo(duel, rng)
            if w is None:
                run.abandon()
            else:
                run.finish_duel(duel)
        else:
            run.pick_draft(rng.randrange(len(run.draft_options)))
    return run.result, run.nodes_cleared


def deck_perfil(content: Content, rng: Random, perfil: str, n: int = R.DECK) -> list[Cat]:
    """`n` gatos adultos com IV conforme o perfil: real, '1/1'..'5/5', 'med23' (cada IV 2 ou 3)."""
    out = []
    for i in range(n):
        c = roll_cat(content, rng)
        if perfil == "med23":
            c = R.with_iv(c, rng.choice((2, 3)), rng.choice((2, 3)))
        elif perfil != "real":
            a, h = perfil.split("/")
            c = R.with_iv(c, int(a), int(h))
        out.append(replace(c, id=f"p-{i}"))
    return out


def escolher_deck(content: Content, cats: list[Cat], cap: int = 3, score=None) -> list[Cat]:
    """Deck de um jogador razoavel: maiores ATK*HP finais, no maximo `cap` gatos por raca
    (o cap sobe se faltar raca). Obs.: ate T6.5 o `autofill_deck` do core usava ATK+HP sem limite e rendia bem menos; hoje equivale a esta politica."""
    score = score or (lambda st: st.atk * st.hp)
    ordem = sorted(cats, key=lambda x: (-score(cat_stats(content, x)), x.id))
    for k in range(cap, len(ordem) + 1):
        out: list[Cat] = []
        cont: Counter = Counter()
        for x in ordem:
            if cont[x.breed] < k:
                out.append(x)
                cont[x.breed] += 1
            if len(out) == R.DECK:
                return out
    return ordem[: R.DECK]


def mapa_hp(cat: Cat, d: int) -> Cat:
    """Emula um divisor de IV de HP (ainda inexistente no core): iv_hp' = 1 + (iv_hp-1)//d."""
    return cat if d <= 1 else replace(cat, iv_hp=1 + (cat.iv_hp - 1) // d)


def run_stats(content: Content, rng: Random, cats: list[Cat], acc: dict, chave: str = "geral") -> None:
    """Joga uma run com `cats` e acumula vitoria, nos vencidos e contagem de nos."""
    res, nos = jogar_run(content, rng, new_run(content, rng, cats))
    d = acc.setdefault(chave, {"run": wl(), "nos": 0, "chefe": wl()})
    d["run"] = somar(d["run"], wl(res == "vitoria", 1))
    d["nos"] += nos


# ------------------------------------------------------------------ tema 1: Siames
def _p(**campos: Any) -> Patch:
    return {"breeds": {"siames": campos}}


VAR_SIAMES: dict[str, tuple[str, Patch]] = {
    "base": ("dados atuais (desde 2026-10-28: Siames custo 3, ATK 3, HP 3, Investida; antes ATK 4)", {}),
    "custo4": ("Custo 4", _p(custo=4)),
    "atk3": ("ATK base 4 -> 3", _p(atk_base=3)),
    "hp4": ("HP base 3 -> 4 (nao e um nerf; referencia)", _p(hp_base=4)),
    "sem-investida": ("Remove Investida", _p(keywords=[])),
    "atk3-hp4": ("ATK 3, HP 4", _p(atk_base=3, hp_base=4)),
    "custo4-hp4": ("Custo 4, HP 4 (mantem ATK 4 e Investida)", _p(custo=4, hp_base=4)),
    "atk3-sem-inv": ("ATK 3 e sem Investida", _p(atk_base=3, keywords=[])),
    "atk3-hp2": ("ATK 3, HP 3 -> 2 (mais fragil)", _p(atk_base=3, hp_base=2)),
}


def _bin_copias(k: int) -> str:
    return "0-1" if k <= 1 else ("2-3" if k <= 3 else "4+")


def medir_siames(patch: Patch, seed: int, n: int, n_runs: int) -> dict:
    c = aplicar_patch(load_content(ROOT / "data"), patch)
    breeds = list(c.breeds)
    out: dict[str, Any] = {"rr": {b: wl() for b in breeds}, "marg": {}, "mono": {},
                           "uso": {b: {"jog": 0, "copias": 0} for b in breeds},
                           "bins": {b: {} for b in breeds}, "runbins": {b: {} for b in breeds},
                           "run": wl(), "nos": 0, "turnos": 0, "duelos": 0}
    for (x, y), s in R.exp_round_robin(c, seed, max(50, n // 5)).items():
        out["rr"][x] = somar(out["rr"][x], wl(s.wins_a, s.decided))
        out["rr"][y] = somar(out["rr"][y], wl(s.decided - s.wins_a, s.decided))
    out["marg"] = {b: wl(s.wins_a, s.decided) for b, s in R.exp_marginal(c, seed, n).items()}
    out["mono"] = {b: wl(s.wins_a, s.decided) for b, s in R.exp_races(c, seed, n).items()}
    # deck misto vs misto: uso e vitoria por numero de copias
    rng = _rng(seed, "siames-uso")
    for t in range(n):
        a, b = R.deck_of(c, rng), R.deck_of(c, rng)
        d = new_duel(c, rng, DeckSpec(a), DeckSpec(b), t % 2 == 0)
        w, tt = jogar_duelo(d, rng)
        out["turnos"] += tt
        out["duelos"] += 1
        plays = {"player": Counter(), "enemy": Counter()}
        for e in d.log:
            if isinstance(e, CatPlayed) and e.card.breed:
                plays[e.side][e.card.breed] += 1
        for side, deck in (("player", a), ("enemy", b)):
            cop = Counter(x.breed for x in deck)
            for br in breeds:
                out["uso"][br]["jog"] += plays[side][br]
                out["uso"][br]["copias"] += cop[br]
                if w is not None:
                    k = _bin_copias(cop[br])
                    out["bins"][br][k] = somar(out["bins"][br].get(k, wl()), wl(w == side, 1))
    # runs completas da IA com decks sorteados
    rng = _rng(seed, "siames-run")
    for _ in range(n_runs):
        cats = R.deck_of(c, rng)
        res, nos = jogar_run(c, rng, new_run(c, rng, cats))
        won = res == "vitoria"
        out["run"] = somar(out["run"], wl(won, 1))
        out["nos"] += nos
        cop = Counter(x.breed for x in cats)
        for br in breeds:
            k = _bin_copias(cop[br])
            out["runbins"][br][k] = somar(out["runbins"][br].get(k, wl()), wl(won, 1))
    return out


def render_siames(res: dict[str, dict], c: Content, seeds: list[int], n: int, n_runs: int) -> list[str]:
    breeds = list(c.breeds)
    nomes = [c.breeds[b]["nome"] for b in breeds]
    L = [f"## Tema 1: Siames (seeds {seeds}, {n} duelos por experimento por seed, {n_runs} runs por seed)\n",
         "Variantes (so em memoria):\n"]
    L += [f"- `{k}`: {VAR_SIAMES[k][0]}" for k in res]
    cab = "| Variante | " + " | ".join(nomes) + " |\n|---|" + "---|" * len(breeds)
    L += ["\n### 1.1 Vitoria por raca: round-robin mono-raca (quem comeca alterna)\n", cab]
    L += [f"| {k} | " + " | ".join(fmt(r["rr"][b]) for b in breeds) + " |" for k, r in res.items()]
    L += ["\n### 1.2 Vitoria por raca: deck realista (4 gatos da raca + 8 mistos) vs misto\n", cab]
    L += [f"| {k} | " + " | ".join(fmt(r["marg"][b]) for b in breeds) + " |" for k, r in res.items()]
    L += ["\n### 1.3 Vitoria por raca: deck mono-raca vs misto\n", cab]
    L += [f"| {k} | " + " | ".join(fmt(r["mono"][b]) for b in breeds) + " |" for k, r in res.items()]
    L += ["\n### 1.4 Uso: gatos da raca jogados por copia no deck (misto vs misto; 1,00 = joga toda copia que compra)\n"
          "Menor que o dos outros = a raca fica na mao (custo alto) ou o duelo acaba antes.\n", cab]
    L += [f"| {k} | " + " | ".join(
        f"{r['uso'][b]['jog'] / max(1, r['uso'][b]['copias']):.2f}" for b in breeds) + " |"
        for k, r in res.items()]
    L += ["\n### 1.5 Vitoria do deck misto por numero de copias da raca (0-1 / 2-3 / 4+; duelo IA vs IA)\n", cab]
    for k, r in res.items():
        cells = []
        for b in breeds:
            cells.append(" / ".join(fmt(r["bins"][b].get(x, wl())) for x in ("0-1", "2-3", "4+")))
        L.append(f"| {k} | " + " | ".join(cells) + " |")
    L += ["\n### 1.6 Runs completas da IA (deck inicial de 12 sorteados; mapa e draft ao acaso)\n",
          "Vitoria da run por numero de copias da raca no deck inicial (0-1 / 2-3 / 4+).\n",
          "| Variante | Run vence (todas) | Nos vencidos (media) | " + " | ".join(nomes) + " |",
          "|---|---|---|" + "---|" * len(breeds)]
    for k, r in res.items():
        cells = [" / ".join(fmt(r["runbins"][b].get(x, wl())) for x in ("0-1", "2-3", "4+")) for b in breeds]
        L.append(f"| {k} | {fmt(r['run'])} | {r['nos'] / max(1, r['run']['n']):.2f} | " + " | ".join(cells) + " |")
    return L


# ------------------------------------------------------------------ tema 2: naturezas
def _nat(**kv: tuple[int, int]) -> Patch:
    return {"natures": {k: {"atk": v[0], "hp": v[1]} for k, v in kv.items()}}


VAR_NAT: dict[str, tuple[str, Patch]] = {
    "base": ("dados atuais (desde 2026-10-28: Calmo 0/+1, Bravo +1/-1, Agitado +2/-2; antes Calmo -1/+1)", {}),
    "calmo0+1": ("Calmo 0/+1", _nat(calmo=(0, 1))),
    "calmo0+2": ("Calmo 0/+2", _nat(calmo=(0, 2))),
    "calmo-1+2": ("Calmo -1/+2", _nat(calmo=(-1, 2))),
    "calmo0+3": ("Calmo 0/+3", _nat(calmo=(0, 3))),
    "bravo+1-2": ("Bravo +1/-2", _nat(bravo=(1, -2))),
    "agitado+2-3": ("Agitado +2/-3", _nat(agitado=(2, -3))),
    "calmo0+2-bravo+1-2": ("Calmo 0/+2 e Bravo +1/-2", _nat(calmo=(0, 2), bravo=(1, -2))),
    "calmo0+2-agit+2-3": ("Calmo 0/+2 e Agitado +2/-3", _nat(calmo=(0, 2), agitado=(2, -3))),
    "calmo0+1-agit+2-3": ("Calmo 0/+1 e Agitado +2/-3", _nat(calmo=(0, 1), agitado=(2, -3))),
    "calmo0+2-agit+1-2": ("Calmo 0/+2 e Agitado +1/-2", _nat(calmo=(0, 2), agitado=(1, -2))),
}


def _nat_real(nat: str):
    return lambda c, rng: replace(c, nature=nat)


def medir_natureza(patch: Patch, seed: int, n: int) -> dict:
    c = aplicar_patch(load_content(ROOT / "data"), patch)
    ids = list(c.natures)
    out: dict[str, Any] = {"par3": {}, "parreal": {}, "mono": {}, "ref": {}}
    k = 0
    for i, x in enumerate(ids):
        for y in ids[i + 1:]:
            s3 = R.exp_paired(c, seed, n, 400 + k, R.nature_iv3(x), R.nature_iv3(y))
            sr = R.exp_paired(c, seed, n, 450 + k, _nat_real(x), _nat_real(y))
            out["par3"][f"{x}|{y}"] = wl(s3.wins_a, s3.decided)
            out["parreal"][f"{x}|{y}"] = wl(sr.wins_a, sr.decided)
            k += 1
    # deck so de uma natureza (IV real) vs deck misto
    for j, x in enumerate(ids):
        s = R.exp_paired(c, seed, n, 500 + j, _nat_real(x), lambda cat, rng: cat)
        out["mono"][x] = wl(s.wins_a, s.decided)
    # escala: valor de passos de IV (natureza aleatoria do sorteio, IV fixos)
    refs = {
        "+1 ATK (IV ATK 3 vs 1)": (lambda cat, rng: R.with_iv(cat, 3, 3), lambda cat, rng: R.with_iv(cat, 1, 3)),
        "+1 HP (IV HP 3 vs 2)": (lambda cat, rng: R.with_iv(cat, 3, 3), lambda cat, rng: R.with_iv(cat, 3, 2)),
        "+2 HP (IV HP 3 vs 1)": (lambda cat, rng: R.with_iv(cat, 3, 3), lambda cat, rng: R.with_iv(cat, 3, 1)),
        "+1 ATK -1 HP (3/2 vs 1/3)": (lambda cat, rng: R.with_iv(cat, 3, 2), lambda cat, rng: R.with_iv(cat, 1, 3)),
        "+2 ATK -2 HP (5/1 vs 1/3)": (lambda cat, rng: R.with_iv(cat, 5, 1), lambda cat, rng: R.with_iv(cat, 1, 3)),
        "IV 3/3 vs 2/2": (R.fixed_iv(3), R.fixed_iv(2)),
        "IV 4/4 vs 3/3": (R.fixed_iv(4), R.fixed_iv(3)),
    }
    for j, (nome, (va, vb)) in enumerate(refs.items()):
        s = R.exp_paired(c, seed, n, 600 + j, va, vb)
        out["ref"][nome] = wl(s.wins_a, s.decided)
    return out


def render_natureza(res: dict[str, dict], c: Content, seeds: list[int], n: int) -> list[str]:
    ids = list(c.natures)
    nm = {i: c.natures[i]["nome"] for i in ids}
    pares = [f"{x}|{y}" for i, x in enumerate(ids) for y in ids[i + 1:]]
    pn = [f"{nm[p.split('|')[0]]} x {nm[p.split('|')[1]]}" for p in pares]
    L = [f"## Tema 2: naturezas (seeds {seeds}, {n} duelos por celula por seed)\n", "Variantes:\n"]
    L += [f"- `{k}`: {VAR_NAT[k][0]}" for k in res]
    for chave, titulo in (("par3", "IV 3/3 fixo, decks mistos, natureza unica por deck (vitoria do primeiro)"),
                          ("parreal", "IV sorteado real, natureza unica por deck (vitoria do primeiro)")):
        L += [f"\n### {titulo}\n", "| Variante | " + " | ".join(pn) + " |", "|---|" + "---|" * len(pn)]
        L += [f"| {k} | " + " | ".join(fmt(r[chave][p]) for p in pares) + " |" for k, r in res.items()]
    L += ["\n### Deck 100% de uma natureza (IV real) vs deck misto\n",
          "| Variante | " + " | ".join(nm[i] for i in ids) + " |", "|---|" + "---|" * len(ids)]
    L += [f"| {k} | " + " | ".join(fmt(r["mono"][i]) for i in ids) + " |" for k, r in res.items()]
    base = next(iter(res.values()))
    L += ["\n### Escala: quanto vale cada ajuste de status (deck misto A vs B; A tem o beneficio; variante '"
          + next(iter(res)) + "')\n", "| Diferenca de status entre os decks | Vitoria de A |", "|---|---|"]
    L += [f"| {k} | {fmt(v)} |" for k, v in base["ref"].items()]
    return L


# ------------------------------------------------------------------ tema 3: IVs
VAR_IV: dict[str, tuple[str, Patch]] = {
    "base": ("Pesos 30/25/25/15/5, divisor de ATK 2 (dados atuais)", {}),
    "pesos-topo+": ("Pesos 25/25/25/15/10 (mais 5/5)", {"rules": {"iv_weights": {1: 25, 2: 25, 3: 25, 4: 15, 5: 10}}}),
    "pesos-baixos": ("Pesos 40/30/20/8/2 (mais raro)", {"rules": {"iv_weights": {1: 40, 2: 30, 3: 20, 4: 8, 5: 2}}}),
    "pesos-uniforme": ("Pesos 20/20/20/20/20 (uniforme)", {"rules": {"iv_weights": {1: 20, 2: 20, 3: 20, 4: 20, 5: 20}}}),
    "pesos-medianos": ("Pesos 15/30/30/20/5 (concentra no meio)", {"rules": {"iv_weights": {1: 15, 2: 30, 3: 30, 4: 20, 5: 5}}}),
    "div3": ("Divisor de ATK 3 (IV de ATK pesa menos)", {"rules": {"stats": {"atk_iv_divisor": 3}}}),
    "div4": ("Divisor de ATK 4", {"rules": {"stats": {"atk_iv_divisor": 4}}}),
    "div99": ("IV de ATK sem efeito (divisor 99); so IV de HP", {"rules": {"stats": {"atk_iv_divisor": 99}}}),
    "hpdiv2": ("IV de HP conta metade: HP = base + (IV-1)//2 (EMULADO no sim; o core nao tem esse divisor)",
               {"hp_iv_div": 2}),
    "hpdiv2-div3": ("hpdiv2 e divisor de ATK 3 (emulado)", {"hp_iv_div": 2, "rules": {"stats": {"atk_iv_divisor": 3}}}),
}
PERFIS = ("1/1", "med23", "3/3", "real", "4/4", "5/5")
CASOS_MONO = {"5/5 vs 1/1": ((5, 5), (1, 1)), "5/1 vs 1/1": ((5, 1), (1, 1)), "1/5 vs 1/1": ((1, 5), (1, 1)),
              "3/3 vs 1/1": ((3, 3), (1, 1)), "5/1 vs 1/5": ((5, 1), (1, 5))}


def medir_iv(patch: Patch, seed: int, n: int, n_runs: int, completo: bool) -> dict:
    c = aplicar_patch(load_content(ROOT / "data"), patch)
    breeds = list(c.breeds)
    hd = int(patch.get("hp_iv_div", 1))
    out: dict[str, Any] = {"runs": {}, "pool": {}, "duelo": {}, "mono": {}, "um": {}}
    acc: dict[str, Any] = {}
    for p in PERFIS:
        rng = _rng(seed, "iv-run", p)
        for _ in range(n_runs):
            run_stats(c, rng, [mapa_hp(x, hd) for x in deck_perfil(c, rng, p)], acc, p)
    out["runs"] = acc
    # colecao de 30 gatos do perfil; o jogador escolhe o deck (ATK*HP, maximo 3 por raca)
    accp: dict[str, Any] = {}
    for p in ("med23", "real", "4/4", "5/5"):
        rng = _rng(seed, "iv-pool", p)
        for _ in range(n_runs):
            pool = [mapa_hp(x, hd) for x in deck_perfil(c, rng, p, 30)]
            run_stats(c, rng, escolher_deck(c, pool), accp, p)
    out["pool"] = accp
    T = lambda v: (lambda x, r: mapa_hp(v(x, r), hd))  # noqa: E731
    # nivel de deck, decks mistos sorteados independentes (IV sobrescrito)
    for k, (nome, va, vb) in enumerate([("5/5 vs 1/1", R.fixed_iv(5), R.fixed_iv(1)),
                                        ("5/5 vs 3/3", R.fixed_iv(5), R.fixed_iv(3)),
                                        ("3/3 vs 1/1", R.fixed_iv(3), R.fixed_iv(1)),
                                        ("real vs 5/5", R.real_iv(c), R.fixed_iv(5)),
                                        ("real vs 1/1", R.real_iv(c), R.fixed_iv(1)),
                                        ("5/1 vs 1/5", lambda x, r: R.with_iv(x, 5, 1), lambda x, r: R.with_iv(x, 1, 5)),
                                        ("5/1 vs 1/1", lambda x, r: R.with_iv(x, 5, 1), R.fixed_iv(1)),
                                        ("1/5 vs 1/1", lambda x, r: R.with_iv(x, 1, 5), R.fixed_iv(1))]):
        s = R.exp_paired(c, seed, n, 700 + k, T(va), T(vb))
        out["duelo"][nome] = wl(s.wins_a, s.decided)
    if not completo:
        return out
    # mesma raca nos dois lados (mono-raca), quem comeca alterna
    for br in breeds:
        for nome, (iva, ivb) in CASOS_MONO.items():
            rng = _rng(seed, "iv-mono", br, nome)
            ww = wl()
            for t in range(max(50, n // 2)):
                a = [replace(R.with_iv(roll_cat(c, rng, br), *iva), id=f"a{i}") for i in range(R.DECK)]
                b = [replace(R.with_iv(roll_cat(c, rng, br), *ivb), id=f"b{i}") for i in range(R.DECK)]
                r, _ = R.run_duel(c, rng, a, b, t % 2 == 0)
                if r.winner:
                    ww = somar(ww, wl(r.winner == "player", 1))
            out["mono"][f"{br}|{nome}"] = ww
        # um unico gato da raca com IV 5/5 vs 1/1 (resto sorteado real)
        for nome, iv in (("5/5", (5, 5)), ("1/1", (1, 1))):
            rng = _rng(seed, "iv-um", br, nome)
            ww = wl()
            for t in range(n):
                a, b = R.deck_of(c, rng), R.deck_of(c, rng)
                a[0] = R.with_iv(replace(roll_cat(c, rng, br), id="c-0"), *iv)
                r, _ = R.run_duel(c, rng, a, b, t % 2 == 0)
                if r.winner:
                    ww = somar(ww, wl(r.winner == "player", 1))
            out["um"][f"{br}|{nome}"] = ww
    return out


def p55(c: Content) -> float:
    w = {int(k): v for k, v in c.rules["iv_weights"].items()}
    return (w.get(5, 0) / sum(w.values())) ** 2


def render_iv(res: dict[str, dict], seeds: list[int], n: int, n_runs: int) -> list[str]:
    c0 = load_content(ROOT / "data")
    breeds = list(c0.breeds)
    nomes = {b: c0.breeds[b]["nome"] for b in breeds}
    base = res.get("base") or next(iter(res.values()))
    L = [f"## Tema 3: peso dos IVs (seeds {seeds}, {n} duelos e {n_runs} runs por celula por seed)\n"]
    if base["mono"]:
        cs = list(CASOS_MONO)
        L += ["### 3.1 Mesma raca nos dois lados, deck mono-raca: IV de A vs IV de B (vitoria de A, quem comeca alterna)\n",
              "| Raca | " + " | ".join(cs) + " |", "|---|" + "---|" * len(cs)]
        for b in breeds:
            L.append(f"| {nomes[b]} | " + " | ".join(fmt(base["mono"][f"{b}|{x}"]) for x in cs) + " |")
        L.append("")
        L += ["### 3.1b Um unico gato da raca no slot 0 (5/5 vs 1/1), resto do deck sorteado real; B misto real\n",
              "| Raca | Com o gato 5/5 | Com o gato 1/1 | Diferenca (pontos) |", "|---|---|---|---|"]
        for b in breeds:
            a5, a1 = base["um"][b + "|5/5"], base["um"][b + "|1/1"]
            L.append(f"| {nomes[b]} | {fmt(a5)} | {fmt(a1)} | {100 * (taxa(a5) - taxa(a1)):+.1f} |")
    L += ["\n### 3.2 Deck misto inteiro com IV fixo (vitoria de A)\n",
          "| Confronto | " + " | ".join(res) + " |", "|---|" + "---|" * len(res)]
    for k in base["duelo"]:
        L.append(f"| {k} | " + " | ".join(fmt(r["duelo"][k]) for r in res.values()) + " |")
    L += ["\n### 3.3 Run completa da IA por perfil de colecao (vitoria da run / nos vencidos de 6 em media)\n",
          "Perfis: 1/1, med23 (cada IV 2 ou 3, o 'mediano'), 3/3, real (sorteio pelos pesos), 4/4, 5/5. "
          "Mapa e draft ao acaso, IA dos dois lados.\n",
          "| Variante | P(5/5 por gato) | " + " | ".join(PERFIS) + " |", "|---|---|" + "---|" * len(PERFIS)]
    for k, r in res.items():
        c = aplicar_patch(c0, VAR_IV[k][1])
        cells = []
        for p in PERFIS:
            d = r["runs"][p]
            cells.append(f"{fmt(d['run'])} ({d['nos'] / max(1, d['run']['n']):.1f})")
        L.append(f"| {k} | {R.pct(p55(c))} | " + " | ".join(cells) + " |")
    pp = ("med23", "real", "4/4", "5/5")
    L += ["\n### 3.4 Colecao de 30 gatos do perfil, deck de 12 escolhido pelo jogador (ATK*HP, no maximo 3 por raca)\n",
          "Mesmas runs da IA (mapa e draft ao acaso). Vitoria da run (nos vencidos em media).\n",
          "| Variante | " + " | ".join(pp) + " |", "|---|" + "---|" * len(pp)]
    for k, r in res.items():
        L.append(f"| {k} | " + " | ".join(
            f"{fmt(r['pool'][p]['run'])} ({r['pool'][p]['nos'] / max(1, r['pool'][p]['run']['n']):.1f})" for p in pp) + " |")
    return L


# ------------------------------------------------------------------ tema 4: breed e progressao da colecao
def tempo_por_raca(tempos: dict[str, int]):
    return lambda male, female: max(tempos[male.breed], tempos[female.breed])


VAR_BREED: dict[str, dict[str, Any]] = {
    "base": {"desc": "Mutacao 7%, ninhada 1-3, breed 2 runs (dados atuais)"},
    "mut0": {"desc": "Mutacao 0% (referencia)", "rules": {"breed": {"mutation_chance": 0.0}}},
    "mut3": {"desc": "Mutacao 3%", "rules": {"breed": {"mutation_chance": 0.03}}},
    "mut10": {"desc": "Mutacao 10%", "rules": {"breed": {"mutation_chance": 0.10}}},
    "ninhada1-2": {"desc": "Ninhada 1-2", "rules": {"breed": {"litter_max": 2}}},
    "ninhada1-4": {"desc": "Ninhada 1-4 (exemplo do GDD)", "rules": {"breed": {"litter_max": 4}}},
    "melhor-pai": {"desc": "Cada IV do filhote = o maior dos pais (+mutacao 7%)", "melhor_pai": True},
    "tempo3": {"desc": "Tempo de breed 3 runs", "rules": {"breed": {"base_runs": 3}}},
    "tempo4": {"desc": "Tempo de breed 4 runs", "rules": {"breed": {"base_runs": 4}}},
    "raras-lentas": {"desc": "Tempo por raca (casal = maior dos dois): Vira-lata 2, Persa 2, Siames 3, Sphynx 3, Maine Coon 4 "
                             "(raridade hipotetica, o GDD nao define)",
                     "tempos": {"vira-lata": 2, "persa": 2, "siames": 3, "sphynx": 3, "maine-coon": 4}},
    "mut3-melhor-pai": {"desc": "Melhor pai + mutacao 3%", "melhor_pai": True,
                        "rules": {"breed": {"mutation_chance": 0.03}}},
    "adocao-shift1": {"desc": "Adocao: cada no vencido desloca 1 peso de IV 1 para IV 5 (hoje 2)",
                      "rules": {"adoption": {"iv_shift_per_node": 1}}},
    "adocao-shift0": {"desc": "Adocao: sem deslocamento de pesos por no vencido (so os pesos base)",
                      "rules": {"adoption": {"iv_shift_per_node": 0}}},
}
SEM_BREED_EM = ("base", "adocao-shift1", "adocao-shift0")   # variantes que tambem rodam a estrategia 'nenhuma'


def _iv_filhote(rng: Random, m: int, f: int, mut: float, melhor: bool) -> int:
    pick = rng.random() < 0.5
    iv = max(m, f) if melhor else (m if pick else f)
    if rng.random() < mut:
        iv = min(5, iv + 1)
    return iv


def nascer_emulado(content: Content, save: SaveData, rng: Random, male: Cat, female: Cat,
                   melhor: bool) -> list[Cat]:
    """Ninhada com a regra do core (mesma ordem de sorteios), com opcao 'IV do melhor pai'."""
    cfg = content.rules["breed"]
    n = rng.randint(cfg["litter_min"], cfg["litter_max"])
    out = []
    for _ in range(n):
        breed = female.breed if rng.random() < cfg["mother_breed_chance"] else male.breed
        sex = rng.choice(("M", "F"))
        nature = rng.choice(list(content.natures))
        ia = _iv_filhote(rng, male.iv_atk, female.iv_atk, cfg["mutation_chance"], melhor)
        ih = _iv_filhote(rng, male.iv_hp, female.iv_hp, cfg["mutation_chance"], melhor)
        cat = Cat(id=format_cat_id(save.next_cat_id), breed=breed, sex=sex, nature=nature,
                  iv_atk=ia, iv_hp=ih, stage="kitten", rest_runs_left=0, runs_as_kitten=0)
        save.next_cat_id += 1
        save.cats.append(cat)
        register_dex(save, cat)
        out.append(cat)
    return out


def avancar(content: Content, save: SaveData, rng: Random, nos: int, melhor: bool):
    """advance_after_run do core; com `melhor`, os nascimentos do dia sao emulados aqui."""
    if not melhor:
        return advance_after_run(content, save, rng, nos)
    minimo = content.rules["breed"]["min_nodes_for_run_count"]
    if nos < minimo:
        return advance_after_run(content, save, rng, nos)
    por_nascer = [b for b in save.breeding if b["runs_left"] <= 1]
    save.breeding = [b for b in save.breeding if b["runs_left"] > 1]
    out = advance_after_run(content, save, rng, nos)
    by = {c.id: c for c in save.cats}
    for b in por_nascer:
        out.born += nascer_emulado(content, save, rng, by[b["male"]], by[b["female"]], True)
        out.couples_done.append((b["male"], b["female"]))
    return out


def _p_iv5(iv: int, mut: float) -> float:
    return 1.0 if iv == 5 else (mut if iv == 4 else 0.0)


def pontos_casal(m: Cat, f: Cat, mut: float, melhor: bool) -> tuple[float, float]:
    """(P(filhote 5/5), soma esperada dos IVs) para escolher casais."""
    if melhor:
        pa = max(_p_iv5(m.iv_atk, mut), _p_iv5(f.iv_atk, mut))
        ph = max(_p_iv5(m.iv_hp, mut), _p_iv5(f.iv_hp, mut))
        es = max(m.iv_atk, f.iv_atk) + max(m.iv_hp, f.iv_hp)
    else:
        pa = (_p_iv5(m.iv_atk, mut) + _p_iv5(f.iv_atk, mut)) / 2
        ph = (_p_iv5(m.iv_hp, mut) + _p_iv5(f.iv_hp, mut)) / 2
        es = (m.iv_atk + f.iv_atk + m.iv_hp + f.iv_hp) / 2
    return pa * ph, es


def iniciar_casais(content: Content, save: SaveData, estrategia: str, melhor: bool,
                   tempo_fn) -> None:
    """simples: um casal por vez, o macho e a femea de maior soma de IV.
    otima: ate 3 casais ao mesmo tempo, pares ordenados por P(5/5) e soma esperada."""
    limite = 1 if estrategia == "simples" else 3
    mut = content.rules["breed"]["mutation_chance"]
    while len(save.breeding) < limite:
        disp = [c for c in available_cats(save) if c.stage == "adult"]
        machos = sorted((c for c in disp if c.sex == "M"), key=lambda c: -(c.iv_atk + c.iv_hp))
        femeas = sorted((c for c in disp if c.sex == "F"), key=lambda c: -(c.iv_atk + c.iv_hp))
        if not machos or not femeas:
            return
        if estrategia == "simples":
            pares = [(machos[0], femeas[0])]
        else:
            pares = sorted(((m, f) for m in machos[:10] for f in femeas[:10]),
                           key=lambda p: pontos_casal(p[0], p[1], mut, melhor), reverse=True)
        for m, f in pares:
            if can_breed(content, save, m.id, f.id)[0]:
                start_breed(content, save, m.id, f.id)
                if tempo_fn:
                    save.breeding[-1]["runs_left"] = tempo_fn(m, f)
                break
        else:
            return


def jogar_jogador(content: Content, var: dict, estrategia: str, rng: Random, n_runs: int,
                  deck_pol: str = "razoavel") -> dict:
    """Um jogador: n_runs runs, adotando tudo e fazendo breed pela estrategia. Devolve metricas."""
    melhor = bool(var.get("melhor_pai"))
    tempos = var.get("tempos")
    tempo_fn = tempo_por_raca(tempos) if tempos else None
    save = new_game(content, rng)
    primeiro: dict[str, int | None] = {"p55": None, "p55_adocao": None, "p55_breed": None, "par55": None,
                                       "p54": None}
    nascido = set()
    hist = {"deck_soma": [], "win": [], "nos": [], "deck55": []}
    for r in range(1, n_runs + 1):
        if deck_pol == "autofill":   # o que o core sugere hoje (maior ATK*HP finais, max 3 por raca)
            set_deck(content, save, autofill_deck(content, save, []))
            deck = [c for c in save.cats if c.id in set(save.deck)]
        else:
            deck = escolher_deck(content, available_cats(save))
            set_deck(content, save, [c.id for c in deck])
        hist["deck_soma"].append(sum(c.iv_atk + c.iv_hp for c in deck) / len(deck))
        d55 = sum(1 for c in deck if c.iv_atk == 5 and c.iv_hp == 5)
        run = new_run_from_save(content, save, rng)
        res, nos = jogar_run(content, rng, run)
        hist["win"].append(res == "vitoria")
        hist["nos"].append(nos)
        hist["deck55"].append(d55)
        aft = avancar(content, save, rng, nos, melhor)
        nascido.update(c.id for c in aft.born)
        create_adoption(content, save, rng, res, nos)
        novos = list(save.pending_adoption["cats"]) if save.pending_adoption else []
        for c in novos:
            adopt(content, save, c.id)
        if estrategia != "nenhuma":
            iniciar_casais(content, save, estrategia, melhor, tempo_fn)
        perf = [c for c in save.cats if c.iv_atk == 5 and c.iv_hp == 5]
        if perf and primeiro["p55"] is None:
            primeiro["p55"] = r
        if any(c.id not in nascido for c in perf) and primeiro["p55_adocao"] is None:
            primeiro["p55_adocao"] = r
        if any(c.id in nascido for c in perf) and primeiro["p55_breed"] is None:
            primeiro["p55_breed"] = r
        if primeiro["par55"] is None and any(c.sex == "M" and c.stage == "adult" for c in perf) \
                and any(c.sex == "F" and c.stage == "adult" for c in perf):
            primeiro["par55"] = r
        if primeiro["p54"] is None and any(c.iv_atk + c.iv_hp >= 9 for c in save.cats):
            primeiro["p54"] = r
    final = {"n55": sum(1 for c in save.cats if c.iv_atk == 5 and c.iv_hp == 5),
             "cats": len(save.cats), "nascidos": len(nascido)}
    return {"primeiro": primeiro, "hist": hist, "final": final}


def medir_breed(nome: str, estrategia: str, seed: int, jogadores: int, n_runs: int,
                deck_pol: str = "razoavel") -> dict:
    var = VAR_BREED[nome]
    c = aplicar_patch(load_content(ROOT / "data"), {"rules": var.get("rules", {})})
    # mesmos jogadores iniciais entre variantes: o rng de cada jogador depende so de (seed, estrategia, indice)
    return {"jog": [jogar_jogador(c, var, estrategia, _rng(seed, estrategia, i), n_runs, deck_pol)
                    for i in range(jogadores)]}


def _pct_ate(vals: list[int | None], limite: int) -> float:
    return sum(1 for v in vals if v is not None and v <= limite) / max(1, len(vals))


def _med(vals: list[int | None]) -> str:
    ok = sorted(v for v in vals if v is not None)
    if len(ok) * 2 < len(vals):
        return f">{max(ok) if ok else '-'} (so {len(ok)}/{len(vals)})"
    pior = sorted(v if v is not None else 10**6 for v in vals)
    return str(pior[len(pior) // 2])


def _janela(jogs: list[dict], a: int, b: int) -> tuple[float, float]:
    """(vitoria da run, soma de IV media do deck) nas runs a..b (1-based)."""
    w = [x for j in jogs for x in j["hist"]["win"][a - 1:b]]
    s = [x for j in jogs for x in j["hist"]["deck_soma"][a - 1:b]]
    return sum(w) / max(1, len(w)), sum(s) / max(1, len(s))


def tabela_adocao() -> list[str]:
    """Chance de 5/5 por gato adotado e numero de gatos por run, conforme os nos vencidos (dados atuais)."""
    from core.adoption import adoption_count, adoption_weights
    c = load_content(ROOT / "data")
    L = ["| Nos vencidos | Gatos (derrota) | Gatos (vitoria) | P(IV 5) por IV | P(gato 5/5) |", "|---|---|---|---|---|"]
    for n in range(0, 7):
        w = adoption_weights(c, n)
        p5 = w[5] / sum(w.values())
        L.append(f"| {n} | {adoption_count(c, n, 'derrota')} | {adoption_count(c, n, 'vitoria')} | {R.pct(p5)} | {R.pct(p5 * p5)} |")
    return L


def render_breed(res: dict[tuple[str, str], dict], seeds: list[int], jogadores: int, n_runs: int,
                 deck: str = "razoavel") -> list[str]:
    pol = ("maior ATK*HP final com no maximo 3 gatos por raca (jogador razoavel)" if deck == "razoavel"
           else "`autofill_deck` do core (maior ATK*HP final, max 3 por raca)")
    L = [f"## Tema 4: gato perfeito por breed (seeds {seeds}, {jogadores} jogadores por seed, {n_runs} runs cada)\n",
         "Modelo: jogador novo (12 gatos sorteados) joga runs completas da IA (mapa e draft ao acaso), adota todos os gatos "
         f"oferecidos e monta o deck pelo {pol}. Estrategias: **nenhuma** = nunca faz "
         "breed (so adocao); **simples** = um casal por vez, o macho e a femea de maior soma de IV; **otima** = ate 3 casais ao "
         "mesmo tempo, escolhidos por P(filhote 5/5) e soma esperada. Nada e doado. Pais saem do deck durante o breed (como no jogo). "
         "Adocao com pity e deslocamento de pesos por nos vencidos (dados atuais):\n"]
    L += tabela_adocao()
    L += ["\nVariantes:\n"]
    L += [f"- `{k}`: {v['desc']}" for k, v in VAR_BREED.items() if any(kk[0] == k for kk in res)]
    for i, estr in enumerate(e for e in ESTRATEGIAS if any(kk[1] == e for kk in res)):
        L += [f"\n### 4.{2 * i + 1} Estrategia {estr}\n",
              "Colunas: jogadores com o 1o 5/5 de qualquer origem ate a run 30 / 100 e mediana da run; idem so por adocao (inclui os gatos "
              "iniciais); 1o par de pais 5/5 (macho e femea adultos) ate 30 / 100 e mediana; 5/5 nascidos de breed ate 100; "
              "deck inteiro de 12 gatos 5/5 (ate 100 e mediana); media de gatos 5/5 e de gatos na colecao na run 100.\n",
              "| Variante | 1o 5/5: ate 30 | ate 100 | mediana | so adocao: ate 30 | ate 100 | par 5/5: ate 30 | ate 100 | mediana | "
              "por breed (100) | deck 12x5/5: ate 100 | mediana | 5/5 medios (100) | gatos (100) |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for k in VAR_BREED:
            r = res.get((k, estr))
            if r is None:
                continue
            jg = r["jog"]
            pr = lambda key: [j["primeiro"][key] for j in jg]  # noqa: E731
            d12 = [next((i + 1 for i, v in enumerate(j["hist"]["deck55"]) if v >= R.DECK), None) for j in jg]
            L.append(f"| {k} | {R.pct(_pct_ate(pr('p55'), 30))} | {R.pct(_pct_ate(pr('p55'), 100))} | {_med(pr('p55'))} "
                     f"| {R.pct(_pct_ate(pr('p55_adocao'), 30))} | {R.pct(_pct_ate(pr('p55_adocao'), 100))} "
                     f"| {R.pct(_pct_ate(pr('par55'), 30))} | {R.pct(_pct_ate(pr('par55'), 100))} | {_med(pr('par55'))} "
                     f"| {R.pct(_pct_ate(pr('p55_breed'), 100))} | {R.pct(_pct_ate(d12, 100))} | {_med(d12)} "
                     f"| {sum(j['final']['n55'] for j in jg) / len(jg):.1f} | {sum(j['final']['cats'] for j in jg) / len(jg):.0f} |")
        L += [f"\n### 4.{2 * i + 2} Dificuldade ao longo da progressao ({estr})\n",
              "Vitoria da run da IA e soma media (IV ATK + IV HP) do deck, por janela de runs.\n",
              "| Variante | Runs 1-10 | 11-30 | 31-60 | 61-100 | Soma de IV do deck em 1-10 / 31-60 / 61-100 |", "|---|---|---|---|---|---|"]
        for k in VAR_BREED:
            r = res.get((k, estr))
            if r is None:
                continue
            ws = [_janela(r["jog"], a, b) for a, b in ((1, 10), (11, 30), (31, 60), (61, 100))]
            L.append(f"| {k} | " + " | ".join(R.pct(w[0]) for w in ws) + f" | {ws[0][1]:.1f} / {ws[2][1]:.1f} / {ws[3][1]:.1f} |")
    bins: dict[str, dict[str, int]] = {}
    for r in res.values():
        for j in r["jog"]:
            for w, d in zip(j["hist"]["win"], j["hist"]["deck55"]):
                k = "0-2" if d <= 2 else ("3-7" if d <= 7 else ("8-11" if d <= 11 else "12"))
                bins[k] = somar(bins.get(k, wl()), wl(w, 1))
    L += ["\n### 4.9 Efeito do 5/5 na dificuldade (todas as variantes e estrategias juntas)\n",
          "Vitoria da run por numero de gatos 5/5 no deck de 12 daquela run. Confunde: quem tem muitos 5/5 joga mais runs.\n",
          "| Gatos 5/5 no deck | Runs | Vitoria da run |", "|---|---|---|"]
    for k in ("0-2", "3-7", "8-11", "12"):
        if k in bins:
            L.append(f"| {k} | {bins[k]['n']} | {fmt(bins[k])} |")
    return L


# ------------------------------------------------------------------ tema 5: politica de deck
VAR_DECK: dict[str, tuple[str, Any]] = {
    "autofill-core": ("`autofill_deck` do core (hoje: maior ATK*HP finais, max 3 por raca, igual a atk*hp-cap3)", ("autofill", 12)),
    "aleatorio": ("12 gatos da colecao ao acaso", ("aleatorio", 12)),
    "atk+hp-cap3": ("maior ATK+HP, no maximo 3 por raca", (lambda st: st.atk + st.hp, 3)),
    "2atk+hp-livre": ("maior 2xATK+HP, sem limite por raca", (lambda st: 2 * st.atk + st.hp, 12)),
    "atk*hp-livre": ("maior ATK*HP, sem limite por raca", (None, 12)),
    "atk*hp-cap4": ("maior ATK*HP, no maximo 4 por raca", (None, 4)),
    "atk*hp-cap3": ("maior ATK*HP, no maximo 3 por raca (politica 'razoavel' do tema breed)", (None, 3)),
    "atk*hp-cap2": ("maior ATK*HP, no maximo 2 por raca", (None, 2)),
}


def _montar(content: Content, pool: list[Cat], pol: Any, rng: Random) -> list[Cat]:
    if pol[0] == "autofill":
        save = SaveData(cats=list(pool))
        by = {c.id: c for c in pool}
        return [by[i] for i in autofill_deck(content, save, [])]
    if pol[0] == "aleatorio":
        return rng.sample(pool, R.DECK)
    return escolher_deck(content, pool, pol[1], pol[0])


def medir_deck(chave: str, seed: int, n_runs: int) -> dict:
    c = load_content(ROOT / "data")
    pol = VAR_DECK[chave][1]
    out: dict[str, Any] = {}
    for perfil in ("med23", "real", "5/5"):
        rng = _rng(seed, "deck", perfil)   # as mesmas colecoes para todas as politicas
        acc: dict[str, Any] = {}
        for i in range(n_runs):
            pool = deck_perfil(c, rng, perfil, 30)
            r2 = _rng(seed, "deck-run", perfil, i)
            run_stats(c, r2, _montar(c, pool, pol, r2), acc, "g")
        out[perfil] = acc["g"]
    return out


def render_deck(res: dict[str, dict], seeds: list[int], n_runs: int) -> list[str]:
    L = [f"## Tema 5: como o deck de 12 e montado (seeds {seeds}, {n_runs} runs por celula por seed)" + "\n",
         "Coleção de 30 gatos do perfil (med23 = cada IV 2 ou 3; real = pesos atuais; 5/5), deck de 12 escolhido pela política, "
         "run completa da IA (mapa e draft ao acaso). Vitória da run (nós vencidos em média)." + "\n",
         "| Politica | med23 | real | 5/5 |", "|---|---|---|---|"]
    for k, r in res.items():
        L.append(f"| {k}: {VAR_DECK[k][0]} | " + " | ".join(
            f"{fmt(r[p]['run'])} ({r[p]['nos'] / max(1, r[p]['run']['n']):.1f})" for p in ("med23", "real", "5/5")) + " |")
    return L


# ------------------------------------------------------------------ execucao
def _tarefa(args: tuple) -> tuple[tuple, dict]:
    tema, chave, seed, n, n_runs, extra = args
    if tema == "siames":
        r = medir_siames(VAR_SIAMES[chave][1], seed, n, n_runs)
    elif tema == "natureza":
        r = medir_natureza(VAR_NAT[chave][1], seed, n)
    elif tema == "iv":
        r = medir_iv(VAR_IV[chave][1], seed, n, n_runs, completo=(chave == "base"))
    elif tema == "deck":
        r = medir_deck(chave, seed, n_runs)
    else:
        r = medir_breed(chave[0], chave[1], seed, extra[0], n_runs, extra[1])
    return (tema, chave, seed), r


def listar() -> str:
    L = ["Temas: " + ", ".join(TEMAS), ""]
    for tema, tab in (("siames", VAR_SIAMES), ("natureza", VAR_NAT), ("iv", VAR_IV)):
        L.append(f"[{tema}]")
        L += [f"  {k}: {v[0]}" for k, v in tab.items()]
    L.append("[deck]")
    L += [f"  {k}: {v[0]}" for k, v in VAR_DECK.items()]
    L.append("[breed] (estrategias: nenhuma = sem breed, simples, otima)")
    L += [f"  {k}: {v['desc']}" for k, v in VAR_BREED.items()]
    return "\n".join(L)


def construir(temas: list[str], seeds: list[int], n: int, n_runs: int, jogadores: int, n_runs_breed: int,
              jobs: int, filtro: list[str] | None = None, deck: str = "razoavel") -> str:
    tarefas = []
    sel = lambda k: filtro is None or k in filtro
    for t in temas:
        for seed in seeds:
            if t == "siames":
                tarefas += [(t, k, seed, n, n_runs, (0, deck)) for k in VAR_SIAMES if sel(k)]
            elif t == "natureza":
                tarefas += [(t, k, seed, n, n_runs, (0, deck)) for k in VAR_NAT if sel(k)]
            elif t == "iv":
                tarefas += [(t, k, seed, n, n_runs, (0, deck)) for k in VAR_IV if sel(k)]
            elif t == "deck":
                tarefas += [(t, k, seed, n, n_runs, (0, deck)) for k in VAR_DECK if sel(k)]
            elif t == "breed":
                tarefas += [(t, (k, e), seed, n, n_runs_breed, (jogadores, deck))
                            for k in VAR_BREED if sel(k) for e in ESTRATEGIAS
                            if e != "nenhuma" or k in SEM_BREED_EM]
    if jobs > 1:
        with ProcessPoolExecutor(jobs) as ex:
            pares = list(ex.map(_tarefa, tarefas, chunksize=1))
    else:
        pares = [_tarefa(t) for t in tarefas]
    agg: dict[tuple, dict] = {}
    for (tema, chave, _seed), r in pares:
        agg[(tema, chave)] = somar(agg[(tema, chave)], r) if (tema, chave) in agg else r
    c0 = load_content(ROOT / "data")
    md = [f"# Balanceamento, rodada 2 (T6.0): seeds {seeds}, {n} duelos por celula por seed\n",
          "IA simples dos dois lados; sem cartas de efeito nos duelos de decks (as runs incluem drafts de efeitos e Espiritos "
          "escolhidos ao acaso). Valem para essa IA, nao para um humano. Dados atuais = pacote B ja aplicado.\n"]
    for t in temas:
        if t == "siames":
            res = {k: agg[(t, k)] for k in VAR_SIAMES if (t, k) in agg}
            md += render_siames(res, c0, seeds, n, n_runs) + [""]
        elif t == "natureza":
            res = {k: agg[(t, k)] for k in VAR_NAT if (t, k) in agg}
            md += render_natureza(res, c0, seeds, n) + [""]
        elif t == "iv":
            res = {k: agg[(t, k)] for k in VAR_IV if (t, k) in agg}
            md += render_iv(res, seeds, n, n_runs) + [""]
        elif t == "deck":
            res = {k: agg[(t, k)] for k in VAR_DECK if (t, k) in agg}
            md += render_deck(res, seeds, n_runs) + [""]
        elif t == "breed":
            res = {k: v for (tt, k), v in agg.items() if tt == "breed"}
            md += render_breed(res, seeds, jogadores, n_runs_breed, deck) + [""]
    return "\n".join(md) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sim.balanceamento")
    ap.add_argument("--lista", action="store_true", help="lista temas e variantes")
    ap.add_argument("--tema", nargs="*", choices=TEMAS, default=list(TEMAS))
    ap.add_argument("--variante", nargs="*", help="filtra variantes pelo nome (vale para todos os temas)")
    ap.add_argument("--duelos", type=int, default=1000)
    ap.add_argument("--runs", type=int, default=300, help="runs completas por celula por seed (temas siames e iv)")
    ap.add_argument("--seeds", type=int, nargs="*", default=[1, 2, 3])
    ap.add_argument("--jogadores", type=int, default=20, help="jogadores simulados por seed (tema breed)")
    ap.add_argument("--runs-breed", type=int, default=100, help="runs por jogador (tema breed)")
    ap.add_argument("--deck", choices=("razoavel", "autofill"), default="razoavel",
                    help="como o jogador do tema breed monta o deck: razoavel (ATK*HP, max 3 por raca) ou autofill do core")
    ap.add_argument("--jobs", type=int, default=1)
    ap.add_argument("--saida", type=Path, default=None, help="grava o markdown aqui")
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if a.lista:
        print(listar())
        return 0
    t0 = time.time()
    texto = construir(a.tema, a.seeds, a.duelos, a.runs, a.jogadores, a.runs_breed, a.jobs, a.variante, a.deck)
    if a.saida:
        a.saida.parent.mkdir(parents=True, exist_ok=True)
        a.saida.write_text(texto, encoding="utf-8")
    print(texto)
    print(f"[tempo {time.time() - t0:.1f}s]", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
