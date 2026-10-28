"""Desenho das telas da mini-run (retangulos e texto; paleta em theme.py). Sem regra de jogo."""
from __future__ import annotations

import pygame

from core.types import Card
from ui import font, layout as L, layout_run as LR, text as T
from ui.controller import Controller
from ui.render import UIState, border, draw_frame, outlined, pill, pulse, tint
from ui.run_controller import RunController
from ui.theme import C, H, KEYWORD_COLOR, KEYWORD_LONG, NODE_COLOR, NODE_LONG, NODE_NAME, W

DARK = C["dark"]


def mix(a: tuple[int, int, int], b: tuple[int, int, int], k: float) -> tuple[int, int, int]:
    """Mistura a->b (k=0 devolve a)."""
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))  # type: ignore[return-value]


# ------------------------------------------------------------------ icones dos nos
def draw_node_icon(surf: pygame.Surface, tipo: str, cx: int, cy: int, col: tuple[int, int, int]) -> None:
    if tipo in ("batalha", "elite"):
        pygame.draw.line(surf, col, (cx - 6, cy - 6), (cx + 6, cy + 6), 2)
        pygame.draw.line(surf, col, (cx + 6, cy - 6), (cx - 6, cy + 6), 2)
        if tipo == "elite":
            pygame.draw.circle(surf, col, (cx, cy), 9, 1)
    elif tipo == "descanso":
        pygame.draw.circle(surf, col, (cx, cy), 7)
        pygame.draw.circle(surf, C["panel"], (cx + 4, cy - 3), 6)
    elif tipo == "chefe":
        pts = [(cx - 8, cy + 6), (cx - 8, cy - 5), (cx - 4, cy), (cx, cy - 7), (cx + 4, cy),
               (cx + 8, cy - 5), (cx + 8, cy + 6)]
        pygame.draw.polygon(surf, col, pts)


def draw_check(surf: pygame.Surface, r: pygame.Rect, col, lost: bool = False) -> None:
    x, y = r.right - 11, r.y + 3
    if lost:
        pygame.draw.line(surf, col, (x, y), (x + 6, y + 6), 2)
        pygame.draw.line(surf, col, (x + 6, y), (x, y + 6), 2)
    else:
        pygame.draw.lines(surf, col, False, [(x, y + 3), (x + 2, y + 6), (x + 7, y)], 2)


# ------------------------------------------------------------------ mapa
def draw_connections(surf: pygame.Surface, rc: RunController) -> None:
    rects = dict(rc.node_rects())
    layers = rc.run.layers
    for li in range(len(layers) - 1):
        for a in layers[li]["nodes"]:
            for b in layers[li + 1]["nodes"]:
                ra, rb = rects[a["id"]], rects[b["id"]]
                walked = a["id"] in rc.visited and b["id"] in rc.visited
                reach = (rc.run.status == "map" and li + 1 == rc.run.layer
                         and bool(rc.visited) and rc.visited[-1] == a["id"])
                if walked:
                    col, w = C["text"], 2
                elif reach:
                    col, w = C["panel_edge"], 2
                else:
                    col, w = C["slot_edge"], 1
                pygame.draw.line(surf, col, ra.midright, rb.midleft, w)


def node_tip(rc: RunController, node: dict) -> list[tuple[str, tuple]]:
    tipo = node["tipo"]
    lines: list[tuple[str, tuple]] = [(rc.node_title(node), C["text"]),
                                      (NODE_LONG[tipo], NODE_COLOR[tipo])]
    e = rc.enemy_of(node)
    if e:
        lines.append((f"Deck do inimigo: {sum(d.get('qtd', 1) for d in e['deck'])} cartas", C["dim"]))
        win = {"batalha": "Vença para ganhar 1 carta (1 de 3).",
               "elite": "Vença: 2 escolhas (1 de 3, duas vezes).",
               "chefe": "Vença para encerrar a run."}[tipo]
        lines.append((win, C["dim"]))
    else:
        lines.append(("Descanso: 1 carta entre 2.", C["dim"]))
    return lines


def draw_node(surf: pygame.Surface, rc: RunController, layer: int, node: dict, r: pygame.Rect,
              ui: UIState) -> None:
    st = rc.node_state(layer, node)
    tipo = node["tipo"]
    base = NODE_COLOR[tipo]
    fade = {"future": 0.45, "done": 0.6, "skipped": 0.78, "lost": 0.45,
            "available": 0.0, "current": 0.0}[st]
    col = mix(base, C["bg"], fade)
    fill = C["slot"] if st != "current" else mix(base, C["bg"], 0.65)
    pygame.draw.rect(surf, fill, r)
    if st == "available":
        k = pulse(ui.t, 5.0)
        border(surf, r.inflate(4, 4), mix(base, (255, 255, 255), 0.3 + 0.4 * k), 1)
        border(surf, r, base, 2)
    elif st == "current":
        border(surf, r.inflate(4, 4), (255, 255, 255), 2)
        border(surf, r, base, 2)
    else:
        border(surf, r, col, 1)
    draw_node_icon(surf, tipo, r.centerx, r.y + 14, col)
    font.draw(surf, NODE_NAME[tipo], r.centerx, r.bottom - 11, mix(C["text"], C["bg"], fade), 1, "center")
    if st == "done":
        draw_check(surf, r, C["good"])
    elif st == "lost":
        draw_check(surf, r, C["bad"], lost=True)


def draw_deck_line(surf: pygame.Surface, rc: RunController, x: int, y: int, w: int) -> None:
    s = rc.deck_summary()
    font.draw(surf, "DECK DA RUN", x, y, C["warn"])
    font.draw(surf, font.fit(f"{rc.deck_summary_text()}  ({s['total']} cartas)", w), x, y + 11, C["text"])


def draw_map(surf: pygame.Surface, rc: RunController, ui: UIState) -> None:
    r = rc.run
    outlined(surf, "MAPA DA RUN", 8, 8, C["text"], 2, "left")
    font.draw(surf, f"Seed {rc.seed}", W - 8, 12, C["dim"], 1, "right")
    for li in range(len(r.layers)):
        x = LR.node_rect(li, 0, 1, len(r.layers)).centerx
        font.draw(surf, f"CAMADA {li + 1}", x, 30, C["text"] if li == r.layer else C["dim"], 1, "center")
    draw_connections(surf, rc)
    hover: tuple[dict, pygame.Rect] | None = None
    rects = dict(rc.node_rects())
    for li, layer in enumerate(r.layers):
        for n in layer["nodes"]:
            nr = rects[n["id"]]
            draw_node(surf, rc, li, n, nr, ui)
            if nr.collidepoint(ui.mouse):
                hover = (n, nr)
    # painel inferior
    p = LR.map_info_rect()
    pygame.draw.rect(surf, C["panel"], p)
    border(surf, p, C["panel_edge"], 1)
    draw_deck_line(surf, rc, p.x + 6, p.y + 6, p.w - 12)
    font.draw(surf, f"Nós vencidos: {r.nodes_cleared}   Camada {r.layer + 1}/{len(r.layers)}",
              p.x + 6, p.y + 30, C["text"])
    font.draw(surf, font.fit(rc.hint(), p.w - 12), p.x + 6, p.y + 46, C["dim"])
    ab = LR.abandon_rect()
    hot = ab.collidepoint(ui.mouse)
    pygame.draw.rect(surf, (150, 60, 60) if hot else (96, 44, 52), ab)
    border(surf, ab, (255, 200, 200), 1)
    font.draw(surf, "ABANDONAR", ab.centerx, ab.y + 8, (255, 255, 255), 1, "center")
    font.draw(surf, "ESC: abandonar a run", W - 8, 252, C["dim"], 1, "right")
    if hover and not rc.quit_confirm:
        draw_tip(surf, node_tip(rc, hover[0]), hover[1], NODE_COLOR[hover[0]["tipo"]])


def draw_tip(surf: pygame.Surface, lines: list[tuple[str, tuple]], anchor: pygame.Rect,
             edge: tuple[int, int, int]) -> None:
    w = max(font.width(t) for t, _ in lines) + 12
    h = 8 + 10 * len(lines)
    x = anchor.right + 6
    if x + w > W - 2:
        x = anchor.x - w - 6
    y = max(2, min(H - h - 2, anchor.centery - h // 2))
    tr = pygame.Rect(x, y, w, h)
    pygame.draw.rect(surf, (16, 18, 30), tr)
    border(surf, tr, edge, 1)
    for k, (t, c) in enumerate(lines):
        font.draw(surf, t, tr.x + 6, tr.y + 5 + k * 10, c)


# ------------------------------------------------------------------ draft
def draw_draft_card(surf: pygame.Surface, rc: RunController, r: pygame.Rect, card: Card,
                    selected: bool, hot: bool) -> None:
    special = card.kind == "special"
    main = C["special"] if special else C["effect"]
    pygame.draw.rect(surf, C["special_bg"] if special else C["effect_bg"], r)
    pygame.draw.rect(surf, main, (r.x + 1, r.y + 1, r.w - 2, 12))
    font.draw(surf, font.fit(card.name, r.w - 8), r.x + 4, r.y + 4, DARK)
    font.draw(surf, "ESPÍRITO" if special else "CARTA DE EFEITO", r.x + 4, r.y + 18, main)
    cost = pygame.Rect(r.right - 50, r.y + 16, 46, 11)
    pygame.draw.rect(surf, C["cost"], cost)
    font.draw(surf, f"CUSTO {card.cost}", cost.centerx, cost.y + 2, (255, 255, 255), 1, "center")
    y = r.y + 32
    if special:
        box = pygame.Rect(r.x + 4, y, 40, 11)
        pygame.draw.rect(surf, C["atk"], box)
        font.draw(surf, f"ATK {card.atk}", box.centerx, box.y + 2, (255, 255, 255), 1, "center")
        box = pygame.Rect(r.x + 48, y, 40, 11)
        pygame.draw.rect(surf, C["hp"], box)
        font.draw(surf, f"HP {card.hp}", box.centerx, box.y + 2, (255, 255, 255), 1, "center")
        cx = r.x + 92
        for k in card.keywords:
            txt = KEYWORD_LONG.get(k, k.upper())
            w = font.width(txt) + 4
            if cx + w > r.right - 2:
                break
            chip = pygame.Rect(cx, y, w, 11)
            pygame.draw.rect(surf, KEYWORD_COLOR.get(k, C["dim"]), chip)
            font.draw(surf, txt, chip.x + 2, chip.y + 2, DARK)
            cx += w + 2
        y += 15
        sents = T.card_sentences(card)
        if sents:
            font.draw(surf, "Ao entrar:", r.x + 4, y, C["special"])
            y += 10
        else:
            font.draw(surf, "Sem efeito ao entrar.", r.x + 4, y, C["dim"])
            y += 10
    else:
        sents = T.card_sentences(card)
    for s in sents:
        for ln in font.wrap(s, r.w - 8):
            font.draw(surf, ln, r.x + 4, y, C["text"])
            y += 9
    if card.text and y < r.bottom - 22:
        y += 3
        for ln in font.wrap('"' + card.text + '"', r.w - 8):
            if y > r.bottom - 22:
                break
            font.draw(surf, ln, r.x + 4, y, C["dim"])
            y += 9
    owned = rc.draft_owned(card.ref)
    if owned:
        font.draw(surf, f"Já no deck: {owned}", r.x + 4, r.bottom - 10, C["warn"])
    if selected:
        border(surf, r.inflate(4, 4), (255, 255, 255), 2)
    border(surf, r, main, 1)
    if hot and not selected:
        border(surf, r, (255, 255, 255), 1)


def draw_list(surf: pygame.Surface, label: str, items: list[tuple[str, int]], x: int, y: int,
              w: int, col, max_lines: int) -> int:
    """Rotulo + itens separados por virgula, quebrando linhas. Devolve o proximo y."""
    txt = ", ".join(f"{n}x {nome}" if n > 1 else nome for nome, n in items) or "nenhuma ainda"
    lines = font.wrap(f"{label}: {txt}", w)
    for k, ln in enumerate(lines[:max_lines]):
        if k == max_lines - 1 and len(lines) > max_lines:
            ln = font.fit(ln + " ...", w)
        font.draw(surf, ln, x, y, col if k or not items else col)
        y += 9
    return y


def draw_deck_panel(surf: pygame.Surface, rc: RunController) -> None:
    p = LR.draft_deck_rect()
    pygame.draw.rect(surf, C["panel"], p)
    border(surf, p, C["panel_edge"], 1)
    s = rc.deck_summary()
    font.draw(surf, f"SEU DECK: {s['cats']} gatos + {s['cards']} carta{'' if s['cards'] == 1 else 's'}", p.x + 6, p.y + 6, C["warn"])
    font.draw(surf, "ESC: desmarcar", p.right - 6, p.y + 6, C["dim"], 1, "right")
    y = draw_list(surf, "Efeitos", rc.deck_counts(False), p.x + 6, p.y + 20, p.w - 12, C["effect"], 3)
    draw_list(surf, "Espíritos", rc.deck_counts(True), p.x + 6, y + 3, p.w - 12, C["special"], 3)


def draw_draft(surf: pygame.Surface, rc: RunController, ui: UIState) -> None:
    descanso = rc.draft_from == "descanso"
    col = NODE_COLOR["descanso"] if descanso else C["good"]
    outlined(surf, rc.draft_title(), W // 2, 4, col, 1, "center")
    font.draw(surf, rc.draft_subtitle(), W // 2, 16, C["dim"], 1, "center")
    cards = rc.draft_cards()
    n = len(cards)
    for i, card in enumerate(cards):
        r = LR.draft_card_rect(i, n)
        sel = rc.draft_sel == i
        draw_draft_card(surf, rc, r, card, sel, r.collidepoint(ui.mouse))
        pr = LR.draft_pick_rect(i, n)
        if sel:
            hot = pr.collidepoint(ui.mouse)
            pygame.draw.rect(surf, C["button_hot"] if hot else C["button"], pr)
            border(surf, pr, (255, 255, 255), 1)
            font.draw(surf, "ESCOLHER", pr.centerx, pr.y + 6, (255, 255, 255), 1, "center")
        else:
            font.draw(surf, "clique para selecionar", pr.centerx, pr.y + 6, C["dim"], 1, "center")
    draw_deck_panel(surf, rc)


# ------------------------------------------------------------------ fim da run
def draw_finished(surf: pygame.Surface, rc: RunController, ui: UIState) -> None:
    win = rc.run.result == "vitoria"
    col = C["good"] if win else C["bad"]
    outlined(surf, "RUN COMPLETA!" if win else "FIM DA RUN", W // 2, 8, col, 3, "center")
    sub = (f"Você derrotou {rc.end_line[0]}." if rc.end_line else "Você chegou ao fim do mapa.")         if win else ("Você abandonou a run." if rc.abandoned else "Você foi derrotado.")
    font.draw(surf, sub, W // 2, 38, C["dim"], 1, "center")
    left = pygame.Rect(8, 52, 226, 100)
    right = pygame.Rect(246, 52, 226, 100)
    for box in (left, right):
        pygame.draw.rect(surf, C["panel"], box)
        border(surf, box, C["panel_edge"], 1)
    font.draw(surf, f"NÓS VENCIDOS: {rc.run.nodes_cleared}", left.x + 6, left.y + 6, C["warn"])
    y = left.y + 20
    for txt, st in rc.path_lines()[:7]:
        mark = {"done": ("OK", C["good"]), "lost": ("X", C["bad"])}.get(st, ("-", C["dim"]))
        font.draw(surf, mark[0], left.x + 6, y, mark[1])
        font.draw(surf, font.fit(txt, left.w - 30), left.x + 22, y, C["text"])
        y += 10
    s = rc.deck_summary()
    font.draw(surf, f"CARTAS ESCOLHIDAS: {s['cards']}", right.x + 6, right.y + 6, C["warn"])
    y = right.y + 20
    items = [(nm, n, C["effect"]) for nm, n in rc.deck_counts(False)] + \
            [(nm, n, C["special"]) for nm, n in rc.deck_counts(True)]
    if not items:
        font.draw(surf, "Nenhuma carta escolhida.", right.x + 6, y, C["dim"])
    for k, (nm, n, c) in enumerate(items):
        if k >= 7:
            font.draw(surf, f"... e mais {len(items) - 7}", right.x + 6, y, C["dim"])
            break
        font.draw(surf, font.fit(f"{n}x {nm}" if n > 1 else nm, right.w - 12), right.x + 6, y, c)
        y += 10
    q = pygame.Rect(8, 160, W - 16, 64)
    pygame.draw.rect(surf, DARK, q)
    border(surf, q, C["panel_edge"], 1)
    if rc.end_line:
        who, line = rc.end_line
        font.draw(surf, who, q.x + 6, q.y + 6, C["enemy"])
        for k, ln in enumerate(font.wrap('"' + line + '"', q.w - 12)[:4]):
            font.draw(surf, ln, q.x + 6, q.y + 18 + k * 10, C["text"])
    else:
        font.draw(surf, f"Seed da run: {rc.seed}", q.x + 6, q.y + 6, C["dim"])
    for name, r in LR.end_buttons().items():
        hot = r.collidepoint(ui.mouse)
        pygame.draw.rect(surf, C["button_hot"] if hot else C["button"], r)
        border(surf, r, (255, 255, 255), 1)
        font.draw(surf, "NOVA RUN" if name == "new_run" else "SAIR", r.centerx, r.y + 8,
                  (255, 255, 255), 1, "center")
    font.draw(surf, "Enter: nova run   ESC: sair", W // 2, 228, C["dim"], 1, "center")


# ------------------------------------------------------------------ overlays
def draw_quit_confirm(surf: pygame.Surface, rc: RunController, ui: UIState) -> None:
    tint(surf, pygame.Rect(0, 0, W, H), (6, 8, 16), 190)
    p = LR.quit_panel()
    pygame.draw.rect(surf, C["panel"], p)
    border(surf, p, C["warn"], 2)
    font.draw(surf, "ABANDONAR A RUN?", p.centerx, p.y + 10, C["warn"], 1, "center")
    font.draw(surf, "Conta como derrota.", p.centerx, p.y + 24, C["dim"], 1, "center")
    for name, r in LR.quit_buttons().items():
        hot = r.collidepoint(ui.mouse)
        yes = name == "quit_yes"
        base = (150, 60, 60) if yes else C["button"]
        pygame.draw.rect(surf, mix(base, (255, 255, 255), 0.25) if hot else base, r)
        border(surf, r, (255, 255, 255), 1)
        font.draw(surf, "SIM, ABANDONAR" if yes else "CONTINUAR", r.centerx, r.y + 8,
                  (255, 255, 255), 1, "center")


def draw_toast(surf: pygame.Surface, rc: RunController) -> None:
    t = rc.toast
    if t is None:
        return
    fill, col = {"error": ((100, 36, 40), (255, 190, 190)), "warn": ((110, 84, 20), (255, 230, 150)),
                 "info": ((36, 64, 100), (200, 225, 255))}[t.kind]
    m = pygame.Rect(60, 248, W - 120, 18)
    pygame.draw.rect(surf, fill, m)
    border(surf, m, col, 1)
    font.draw(surf, font.fit(t.text, m.w - 10), m.centerx, m.y + 6, col, 1, "center")


# ------------------------------------------------------------------ quadro completo
def draw_run_frame(surf: pygame.Surface, rc: RunController, ui: UIState) -> None:
    s = rc.screen
    if s == "duel" and rc.duel_ctrl is not None:
        draw_frame(surf, rc.duel_ctrl, ui)
    else:
        surf.fill(C["bg"])
        if s == "map":
            draw_map(surf, rc, ui)
        elif s == "draft":
            draw_draft(surf, rc, ui)
        else:
            draw_finished(surf, rc, ui)
    if rc.quit_confirm:
        draw_quit_confirm(surf, rc, ui)
    draw_toast(surf, rc)
