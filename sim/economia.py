"""Simulador de economia da Fase 10a (T13.2): carreiras de runs com a IA, compras e ritmo.

Uso:
  python -m sim.economia --runs 200 --seed 1 [--carreiras 50] [--politica ambas]
                         [--mapa aleatorio|elite] [--saida reports/T13.2-economia-sim.md]

`--runs` = runs por carreira; `--carreiras` = quantos jogadores simulados. Deterministico por seed
(cada carreira usa um `Random` proprio derivado de (seed, politica, indice); sem horario no relatorio).
Nao escreve em `sim/ultimo_resultado.md` (que e a saida do `sim.run`).

Jogador simulado (simples, de proposito):
- Runs: deck dos 12 melhores (`sim.balanceamento.escolher_deck`), duelos pela IA, mapa e draft
  aleatorios (ou `--mapa elite`: prefere elite). Fim de run: close_run -> advance_after_run ->
  create_adoption (um so fechamento, como a UI).
- Adocao: adota tudo; com gatil cheio doa o mais fraco entre o novo e a colecao (nunca doa a unica
  gata/gato de uma raca enquanto o Prestigio 3 nao saiu); gatil acima do limite doa ate voltar.
- Breed: mantem os casais permitidos abertos com o melhor macho e a melhor femea; usa racao do estoque
  (Escolha > Veloz > Fofa).
- Compras: politica `area` = junta moedas para a proxima area (na ordem) e so gasta em racao e
  decoracao quando a area esta travada por Prestigio ou nao ha mais area; politica `barato` = sempre
  o item mais barato acessivel (area da vez, racao, decoracao). Racao so e comprada com o estoque vazio.
"""
from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from random import Random
from statistics import mean, median

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core import (Cat, Content, IvChoice, adopt, advance_after_run, available_cats,  # noqa: E402
                  buy_decoration, buy_ration, can_adopt, can_start_breed, close_run,
                  couples_allowed, create_adoption, donate_cat, donate_offer,
                  kennel_over_limit, kennel_slots, load_content, new_game, new_run_from_save,
                  next_area, occupied, prestige_level, ration_stock, rations_catalog,
                  room_candidates, set_deck, start_breed, unlock_area, available_decorations)
from sim import balanceamento as B  # noqa: E402

POLITICAS = ("area", "barato")
AREAS_N = 6


@dataclass
class RunLog:
    idx: int
    result: str
    nodes: int
    run_coins: int                       # moedas da run (nos + bonus), de close_run
    first_win: bool
    donation_coins: int = 0              # moedas de doacao deste fechamento (gatil cheio etc.)
    spent: int = 0
    events: list[str] = field(default_factory=list)   # area:k, prestigio:n, racao:id, deco:id
    prestige: int = 1
    coins_after: int = 0
    kennel_full: bool = False
    slots: int = 18
    occupied: int = 0
    breeds: int = 0                      # racas que contam para o marco do P3


@dataclass
class Career:
    politica: str
    logs: list[RunLog] = field(default_factory=list)
    stuck_from: dict[int, int] = field(default_factory=dict)   # area k -> 1a run em que ficou presa
    cats_final: int = 0


# ------------------------------------------------------------ jogar a run
def jogar_run(run, rng: Random, mapa: str) -> None:
    while run.status != "finished":
        if run.status == "map":
            nos = run.available_nodes()
            if mapa == "elite":
                nos = sorted(nos, key=lambda n: n["tipo"] != "elite") or nos
                escolha = nos[0]
            else:
                escolha = rng.choice(nos)
            run.choose_node(escolha["id"])
        elif run.status == "duel":
            duel = run.start_duel(rng)
            vencedor, _ = B.jogar_duelo(duel, rng)
            if vencedor is None:
                run.abandon()
            else:
                run.finish_duel(duel)
        else:
            run.pick_draft(rng.randrange(len(run.draft_options)))


# ------------------------------------------------------------ colecao
def _soma(c: Cat) -> int:
    return c.iv_atk + c.iv_hp


def _marco_p3(content: Content) -> dict:
    return next(l["milestone"] for l in content.rules["prestige"]["levels"] if l["level"] == 3)


def _forte(content: Content, cat: Cat) -> bool:
    """Gato que conta para o marco do P3 (soma de IV lida de rules.json; sem o campo = qualquer)."""
    return _soma(cat) >= _marco_p3(content).get("min_iv_sum", 0)


def racas_do_marco(content: Content, cats) -> int:
    """Racas que contam para o marco do P3 (com gato forte, se o marco pedir soma de IV)."""
    return len({x.breed for x in cats if _forte(content, x)})


def _unica_da_raca(content: Content, save, cat: Cat) -> bool:
    """Doar este gato tiraria a raca do marco? (e o unico que a conta)"""
    if not _forte(content, cat):
        return False
    return sum(1 for x in save.cats if x.breed == cat.breed and _forte(content, x)) == 1


def _mais_fraco(content: Content, save, protege_raca: bool):
    cands = room_candidates(content, save)
    livres = [c for c in cands if not (protege_raca and _unica_da_raca(content, save, c))]
    pool = livres or cands
    return min(pool, key=lambda c: (_soma(c), c.stage != "kitten", c.id)) if pool else None


def tratar_adocao(content: Content, save, log: RunLog) -> int:
    """Adota a oferta; gatil cheio doa o mais fraco. Devolve moedas de doacao."""
    ganho = 0
    protege = prestige_level(content, save) < 3
    for g in list(save.pending_adoption["cats"] if save.pending_adoption else []):
        if can_adopt(content, save)[0]:
            adopt(content, save, g.id, enforce_capacity=True)
            continue
        log.kennel_full = True
        fraco = _mais_fraco(content, save, protege)
        raca_nova = _forte(content, g) and not any(
            x.breed == g.breed and _forte(content, x) for x in save.cats)
        novo_vale_mais = fraco is not None and (_soma(g) > _soma(fraco) or
                                                (protege and raca_nova))
        if novo_vale_mais:
            while not can_adopt(content, save)[0] and (fraco := _mais_fraco(content, save, protege)):
                ganho += donate_cat(content, save, fraco.id)
        if can_adopt(content, save)[0]:
            adopt(content, save, g.id, enforce_capacity=True)
        else:
            ganho += donate_offer(content, save, g.id)
    while kennel_over_limit(content, save):
        fraco = _mais_fraco(content, save, protege)
        if fraco is None:
            break
        ganho += donate_cat(content, save, fraco.id)
    return ganho


# ------------------------------------------------------------ breed
def _melhor_racao(save) -> str | None:
    for r in ("racao-escolha", "racao-veloz", "racao-fofa"):
        if ration_stock(save, r) > 0:
            return r
    return None


def _escolha(pai: Cat, mae: Cat) -> IvChoice:
    opcoes = [(pai.iv_atk, IvChoice("atk", "father")), (pai.iv_hp, IvChoice("hp", "father")),
              (mae.iv_atk, IvChoice("atk", "mother")), (mae.iv_hp, IvChoice("hp", "mother"))]
    return max(opcoes, key=lambda o: o[0])[1]


def iniciar_casais(content: Content, save) -> None:
    while len(save.breeding) < couples_allowed(content, save):
        disp = [c for c in available_cats(save) if c.stage == "adult"]
        machos = sorted((c for c in disp if c.sex == "M"), key=lambda c: (-_soma(c), c.id))
        femeas = sorted((c for c in disp if c.sex == "F"), key=lambda c: (-_soma(c), c.id))
        if not machos or not femeas:
            return
        pai, mae = machos[0], femeas[0]
        ration = _melhor_racao(save)
        choice = _escolha(pai, mae) if ration == "racao-escolha" else None
        if not can_start_breed(content, save, pai.id, mae.id, ration, choice)[0]:
            return
        start_breed(content, save, pai.id, mae.id, ration, choice, enforce_limits=True)


# ------------------------------------------------------------ compras
def _area_acessivel(content: Content, save):
    area = next_area(content, save)
    if area is None:
        return None, "fim"
    if prestige_level(content, save) < area["prestige_required"]:
        return area, "prestigio"
    return area, "ok"


def _candidatos(content: Content, save, area, estado: str, so_extras: bool):
    """Itens acessiveis como (preco, tipo, id)."""
    itens: list[tuple[int, str, str]] = []
    if area is not None and estado == "ok" and not so_extras:
        itens.append((area["price"], "area", area["id"]))
    for d in available_decorations(content, save):
        itens.append((d["price"], "deco", d["id"]))
    catalogo = rations_catalog(content, save)
    if not any(r["stock"] for r in catalogo):        # nao acumula estoque
        itens += [(r["price"], "racao", r["id"]) for r in catalogo if r["prestige_ok"]]
    return sorted(itens)


def comprar(content: Content, save, politica: str, log: RunLog, indice_area: dict[str, int]) -> None:
    """Compra em laco ate nao poder mais (segue a politica)."""
    while True:
        area, estado = _area_acessivel(content, save)
        if politica == "area":
            if estado == "ok":
                alvo = ("area", area["id"], area["price"])
            else:     # area travada ou inexistente: gasta nos extras
                extras = _candidatos(content, save, area, estado, True)
                if not extras:
                    return
                preco, tipo, ident = extras[0]
                alvo = (tipo, ident, preco)
        else:
            itens = _candidatos(content, save, area, estado, False)
            if not itens:
                return
            preco, tipo, ident = itens[0]
            alvo = (tipo, ident, preco)
        tipo, ident, preco = alvo
        if save.coins < preco:
            return
        if tipo == "area":
            unlock_area(content, save, ident)
            log.events.append(f"area:{indice_area[ident]}")
        elif tipo == "deco":
            buy_decoration(content, save, ident)
            log.events.append(f"deco:{ident}")
        else:
            buy_ration(content, save, ident)
            log.events.append(f"racao:{ident}")
        log.spent += preco


# ------------------------------------------------------------ carreira
def jogar_carreira(content: Content, seed: int, indice: int, n_runs: int, politica: str,
                   mapa: str) -> Career:
    rng = Random(f"economia/{seed}/{politica}/{indice}")
    save = new_game(content, rng)
    ordem = {a["id"]: a["order"] for a in content.shop["areas"]}
    car = Career(politica)
    ultimo_prestigio = prestige_level(content, save)
    for i in range(1, n_runs + 1):
        escolhidos = B.escolher_deck(content, available_cats(save))
        set_deck(content, save, [c.id for c in escolhidos])
        run = new_run_from_save(content, save, rng)
        jogar_run(run, rng, mapa)
        r = close_run(content, save, run)
        advance_after_run(content, save, rng, run.nodes_cleared)
        create_adoption(content, save, rng, run.result, run.nodes_cleared)
        log = RunLog(i, run.result, run.nodes_cleared, r.coins, r.first_league_win)
        log.donation_coins = tratar_adocao(content, save, log)
        comprar(content, save, politica, log, ordem)
        iniciar_casais(content, save)
        nivel = prestige_level(content, save)
        for n in range(ultimo_prestigio + 1, nivel + 1):
            log.events.append(f"prestigio:{n}")
        ultimo_prestigio = nivel
        area, estado = _area_acessivel(content, save)
        if estado == "prestigio":
            car.stuck_from.setdefault(ordem[area["id"]], i)
        log.prestige, log.coins_after = nivel, save.coins
        log.slots, log.occupied = kennel_slots(content, save), occupied(save)
        log.breeds = racas_do_marco(content, save.cats)
        car.logs.append(log)
    car.cats_final = len(save.cats)
    return car


# ------------------------------------------------------------ estatistica
def percentil(vals: list[float], p: float) -> float:
    if not vals:
        return float("nan")
    v = sorted(vals)
    k = (len(v) - 1) * p / 100
    lo, hi = int(k), min(int(k) + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)


def resumo_valores(vals: list[float]) -> str:
    if not vals:
        return "-"
    return (f"{mean(vals):.1f} | {median(vals):.1f} | {percentil(vals, 10):.1f} | "
            f"{percentil(vals, 90):.1f}")


def primeira_run(car: Career, evento: str) -> int | None:
    for lg in car.logs:
        if evento in lg.events:
            return lg.idx
    return None


def _rotulo_idx(vals: list[int | None], total: int) -> str:
    ok = [v for v in vals if v is not None]
    if not ok:
        return f"0% | - | - | -"
    return (f"{100 * len(ok) / total:.0f}% | {median(ok):.1f} | {percentil(ok, 10):.1f} | "
            f"{percentil(ok, 90):.1f}")


JANELAS = ((1, 5), (6, 10), (11, 15), (16, 25), (26, 50), (51, 100), (101, 10_000))


def eventos_relevantes(lg: RunLog, com_deco: bool) -> int:
    """Desbloqueios permanentes: area e Prestigio (+ decoracao). Racao e consumivel: fica fora."""
    tipos = ("area", "prestigio", "deco") if com_deco else ("area", "prestigio")
    return sum(1 for e in lg.events if e.split(":")[0] in tipos)


def ritmo(careers: list[Career], n_runs: int, com_deco: bool) -> list[tuple[str, float, float]]:
    """Por janela: (rotulo, runs por evento, % das runs com >= 1 evento)."""
    out = []
    for a, b in JANELAS:
        if a > n_runs:
            break
        b = min(b, n_runs)
        runs = [lg for c in careers for lg in c.logs if a <= lg.idx <= b]
        ev = sum(eventos_relevantes(lg, com_deco) for lg in runs)
        com = sum(1 for lg in runs if eventos_relevantes(lg, com_deco))
        out.append((f"{a}-{b}", len(runs) / ev if ev else float("inf"),
                    100 * com / len(runs)))
    return out


def _fmt_ritmo(v: float) -> str:
    return "sem eventos" if v == float("inf") else f"{v:.1f}"


# ------------------------------------------------------------ relatorio
def render_politica(content: Content, careers: list[Career], n_runs: int) -> list[str]:
    total = len(careers)
    logs = [lg for c in careers for lg in c.logs]
    vit = [lg for lg in logs if lg.result == "vitoria"]
    der = [lg for lg in logs if lg.result != "vitoria"]
    est = [lg.run_coins for lg in vit if not lg.first_win]       # vitoria sem o bonus unico
    md = [f"**{careers[0].politica}** ({total} carreiras x {n_runs} runs = {len(logs)} runs; "
          f"vitorias {100 * len(vit) / len(logs):.1f}%)\n"]
    md += ["| Moedas por run | media | mediana | p10 | p90 |", "| --- | --- | --- | --- | --- |"]
    linhas = [("Todas (nos + bonus)", [lg.run_coins for lg in logs]),
              ("Vitoria (com o bonus de +20 quando e a 1a)", [lg.run_coins for lg in vit]),
              ("Vitoria estavel (sem o bonus unico)", est),
              ("Derrota/abandono", [lg.run_coins for lg in der]),
              ("Doacoes por run (gatil cheio)", [lg.donation_coins for lg in logs]),
              ("Total de entrada por run (run + doacao)",
               [lg.run_coins + lg.donation_coins for lg in logs]),
              ("  so em runs de vitoria", [lg.run_coins + lg.donation_coins for lg in vit]),
              ("  so em runs de derrota", [lg.run_coins + lg.donation_coins for lg in der])]
    md += [f"| {nome} | {resumo_valores(v)} |" for nome, v in linhas]
    cheio = sum(1 for lg in logs if lg.kennel_full) / len(logs)
    md.append(f"\nRuns em que a adocao encontrou o gatil cheio: {100 * cheio:.0f}%. "
              f"Colecao final media: {mean(c.cats_final for c in careers):.1f} gatos.\n")

    md += ["Runs ate cada marco (por carreira; % = carreiras que chegaram dentro de "
           f"{n_runs} runs).\n", "| Marco | alcancou | mediana | p10 | p90 |",
           "| --- | --- | --- | --- | --- |"]
    for k in range(1, AREAS_N + 1):
        a = next(x for x in content.shop["areas"] if x["order"] == k)
        vals = [primeira_run(c, f"area:{k}") for c in careers]
        md.append(f"| Area {k} - {a['name']} ({a['price']} moedas, P{a['prestige_required']}) "
                  f"| {_rotulo_idx(vals, total)} |")
    for n in (2, 3):
        md.append(f"| Prestigio {n} | "
                  f"{_rotulo_idx([primeira_run(c, f'prestigio:{n}') for c in careers], total)} |")
    md.append("| Colecao com as racas do marco do Prestigio 3 (gato forte em cada) | "
              + _rotulo_idx([next((lg.idx for lg in c.logs if lg.breeds >= _marco_p3(content)['count']), None)
                             for c in careers], total) + " |")
    esgot = []
    for c in careers:
        compra = [lg.idx for lg in c.logs if any(e.startswith(("area:", "deco:")) for e in lg.events)]
        esgot.append(max(compra) if compra else None)
    md.append(f"| Ultima compra de area/decoracao | {_rotulo_idx(esgot, total)} |")

    presas = []
    for k in (5, 6):
        vals = [c.stuck_from.get(k) for c in careers]
        if any(v is not None for v in vals):
            presas.append(f"- Area {k} (Prestigio {k - 1}, travado na 10a): fica presa em "
                          f"{100 * sum(v is not None for v in vals) / total:.0f}% das carreiras, "
                          f"a partir da run {median([v for v in vals if v]):.0f} (mediana).")
    md += ["", *(presas or ["- Areas 5 e 6: nao ficaram presas dentro do horizonte."])]

    md += ["", "Ritmo de desbloqueios (runs por evento; menor = mais frequente). "
           "Meta da especificacao: 1 a 2 no comeco, 4 a 6 depois de ~15 runs. Racao e consumivel "
           "e nao conta como desbloqueio.\n",
           "| Janela de runs | area ou Prestigio | % das runs com evento | + decoracoes | "
           "% das runs com evento |", "| --- | --- | --- | --- | --- |"]
    so, todos = ritmo(careers, n_runs, False), ritmo(careers, n_runs, True)
    for (j, r1, p1), (_, r2, p2) in zip(so, todos):
        md.append(f"| {j} | {_fmt_ritmo(r1)} | {p1:.0f}% | {_fmt_ritmo(r2)} | {p2:.0f}% |")
    racoes = sum(1 for lg in logs for e in lg.events if e.startswith("racao:"))
    md.append(f"\nRacoes compradas: {racoes / len(logs):.2f} por run (consumo, nao desbloqueio).\n")

    media_geral = mean(lg.run_coins + lg.donation_coins for lg in logs)
    media_vit = mean(est) if est else float("nan")
    md += ["", "Custo das racoes em runs de ganho (preco / moedas medias).\n",
           f"| Racao | preco | Prestigio | runs medias (entrada {media_geral:.1f}) | "
           f"vitorias estaveis (media {media_vit:.1f}) |", "| --- | --- | --- | --- | --- |"]
    for r in content.shop["rations"]:
        md.append(f"| {r['name']} | {r['price']} | {r['prestige_required']} | "
                  f"{r['price'] / media_geral:.1f} | {r['price'] / media_vit:.1f} |")
    uso = Counter(e for c in careers for lg in c.logs for e in lg.events if e.startswith("racao"))
    md.append("\nRacoes compradas no total: " + (", ".join(
        f"{k.split(':')[1]} {v}" for k, v in sorted(uso.items())) or "nenhuma") + ".")
    md += ["", "Entrada acumulada (run + doacao) e gasto acumulado, mediana das carreiras.\n",
           "| Ate a run | moedas ganhas | moedas gastas |", "| --- | --- | --- |"]
    for k in (1, 2, 3, 5, 8, 10, 15, 20, 30, 50):
        if k > n_runs:
            break
        ganho = [sum(lg.run_coins + lg.donation_coins for lg in c.logs[:k]) for c in careers]
        gasto = [sum(lg.spent for lg in c.logs[:k]) for c in careers]
        md.append(f"| {k} | {median(ganho):.0f} | {median(gasto):.0f} |")
    return md


def render(content: Content, resultados: dict[str, list[Career]], seed: int, n_runs: int,
           mapa: str) -> str:
    md = ["# T13.2 - Simulador de economia (Fase 10a)\n",
          f"Gerado por `python -m sim.economia --runs {n_runs} --seed {seed} --mapa {mapa}`. "
          "Jogador simulado: IA nos duelos, mapa/draft "
          f"{'aleatorios' if mapa == 'aleatorio' else 'priorizando elite'}, adota tudo, doa o "
          "mais fraco com o gatil cheio, mantem os casais abertos e compra pela politica abaixo. "
          "Areas 5 e 6 dependem de Prestigio 4 e 5, travados na 10a.\n"]
    for i, (pol, careers) in enumerate(resultados.items(), 1):
        md += [f"## {i}. Politica de compra `{pol}`\n", *render_politica(content, careers, n_runs), ""]
    return "\n".join(md) + "\n"


def what_if(content: Content, precos_areas: str | None, moedas_no: str | None) -> Content:
    """Copia do conteudo com precos/ganhos alterados (data/ nunca e tocado)."""
    import copy
    c = copy.deepcopy(content)
    if precos_areas:
        precos = [int(x) for x in precos_areas.split(",")]
        for a in c.shop["areas"]:
            a["price"] = precos[a["order"] - 1]
    if moedas_no:
        b, e, ch, bonus = (int(x) for x in moedas_no.split(","))
        eco = c.rules["economy"]
        eco.update(coins_battle_node=b, coins_elite_node=e, coins_boss_node=ch,
                   league1_first_win_bonus=bonus)
    return c


def rodar(content: Content, seed: int, carreiras: int, n_runs: int, politicas: list[str],
          mapa: str) -> dict[str, list[Career]]:
    return {p: [jogar_carreira(content, seed, i, n_runs, p, mapa) for i in range(carreiras)]
            for p in politicas}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m sim.economia")
    ap.add_argument("--runs", type=int, default=200, help="runs por carreira")
    ap.add_argument("--carreiras", type=int, default=50, help="jogadores simulados")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--politica", choices=(*POLITICAS, "ambas"), default="ambas")
    ap.add_argument("--mapa", choices=("aleatorio", "elite"), default="aleatorio")
    ap.add_argument("--saida", type=Path, default=ROOT / "reports" / "T13.2-economia-sim.md")
    ap.add_argument("--precos-areas", default=None,
                    help="what-if: 6 precos de area separados por virgula (so em memoria)")
    ap.add_argument("--moedas-no", default=None,
                    help="what-if: batalha,elite,chefe,bonus_liga1 (so em memoria)")
    args = ap.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    content = load_content(ROOT / "data")
    content = what_if(content, args.precos_areas, args.moedas_no)
    pols = list(POLITICAS) if args.politica == "ambas" else [args.politica]
    texto = render(content, rodar(content, args.seed, args.carreiras, args.runs, pols, args.mapa),
                   args.seed, args.runs, args.mapa)
    args.saida.parent.mkdir(parents=True, exist_ok=True)
    args.saida.write_text(texto, encoding="utf-8")
    print(texto)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
