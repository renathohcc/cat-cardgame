"""Desenho das telas da mini-run em 960x540 nativo (mapa, draft, fim, confirmacao)."""
from __future__ import annotations

import pygame

from core.types import Card
from ui import font, layout_run as LR, skin, sprites, text as T, widgets as Wd
from ui.render import UIState, draw_frame, gem, mix_c, pulse, text_fit
from ui.run_controller import RunController
from ui.theme import ART_BG, C, H, KEYWORD_LONG, NODE_COLOR, NODE_LONG, NODE_NAME, W
from ui.widgets import WHITE, button, panel

DARK = C["dark"]
mix = mix_c


# ------------------------------------------------------------------ icones dos nos
def draw_node_icon(surf: pygame.Surface, tipo: str, cx: int, cy: int, col: tuple[int, int, int],
                   k: int = 2) -> None:
    if tipo in ("batalha", "elite"):
        pygame.draw.line(surf, col, (cx - 6 * k, cy - 6 * k), (cx + 6 * k, cy + 6 * k), 2 * k)
        pygame.draw.line(surf, col, (cx + 6 * k, cy - 6 * k), (cx - 6 * k, cy + 6 * k), 2 * k)
        if tipo == "elite":
            pygame.draw.circle(surf, col, (cx, cy), 10 * k, 2)
    elif tipo == "descanso":
        pygame.draw.circle(surf, col, (cx, cy), 7 * k)
        pygame.draw.circle(surf, C["slot"], (cx + 4 * k, cy - 3 * k), 6 * k)
    elif tipo == "chefe":
        pts = [(cx - 8 * k, cy + 6 * k), (cx - 8 * k, cy - 5 * k), (cx - 4 * k, cy), (cx, cy - 7 * k),
               (cx + 4 * k, cy), (cx + 8 * k, cy - 5 * k), (cx + 8 * k, cy + 6 * k)]
        pygame.draw.polygon(surf, col, pts)


def draw_check(surf: pygame.Surface, r: pygame.Rect, col, lost: bool = False) -> None:
    x, y = r.right - 24, r.y + 8
    if lost:
        pygame.draw.line(surf, col, (x, y), (x + 12, y + 12), 4)
        pygame.draw.line(surf, col, (x + 12, y), (x, y + 12), 4)
    else:
        pygame.draw.lines(surf, col, False, [(x, y + 7), (x + 4, y + 12), (x + 14, y)], 4)


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
                    col, w = C["text"], 4
                elif reach:
                    col, w = C["panel_edge"], 4
                else:
                    col, w = C["slot_edge"], 2
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
    pygame.draw.rect(surf, fill, r, border_radius=8)
    if st == "available":
        k = pulse(ui.t, 5.0)
        pygame.draw.rect(surf, mix(base, WHITE, 0.3 + 0.4 * k), r.inflate(8, 8), 2, border_radius=11)
        pygame.draw.rect(surf, base, r, 3, border_radius=8)
    elif st == "current":
        pygame.draw.rect(surf, WHITE, r.inflate(8, 8), 3, border_radius=11)
        pygame.draw.rect(surf, base, r, 3, border_radius=8)
    else:
        pygame.draw.rect(surf, col, r, 2, border_radius=8)
    draw_node_icon(surf, tipo, r.centerx, r.y + 34, col)
    font.draw(surf, NODE_NAME[tipo], r.centerx, r.bottom - 24, mix(C["text"], C["bg"], fade), 1, "center")
    if st == "done":
        draw_check(surf, r, C["good"])
    elif st == "lost":
        draw_check(surf, r, C["bad"], lost=True)


def deck_text(rc: RunController) -> str:
    s = rc.deck_summary()
    return f"{rc.deck_summary_text()}  ({s['total']} cartas)"


def draw_map(surf: pygame.Surface, rc: RunController, ui: UIState) -> None:
    r = rc.run
    Wd.title(surf, "MAPA DA RUN", 24, 20, C["text"], 2)
    font.draw(surf, f"Seed {rc.seed}", W - 24, 26, C["dim"], 1, "right")
    for li in range(len(r.layers)):
        x = LR.node_rect(li, 0, 1, len(r.layers)).centerx
        font.draw(surf, f"CAMADA {li + 1}", x, 84, C["text"] if li == r.layer else C["dim"], 1, "center")
    draw_connections(surf, rc)
    hover: tuple[dict, pygame.Rect] | None = None
    rects = dict(rc.node_rects())
    for li, layer in enumerate(r.layers):
        for n in layer["nodes"]:
            nr = rects[n["id"]]
            draw_node(surf, rc, li, n, nr, ui)
            if nr.collidepoint(ui.mouse):
                hover = (n, nr)
    p = LR.map_info_rect()
    panel(surf, p)
    font.draw(surf, "DECK DA RUN", p.x + 14, p.y + 8, C["warn"], 1)
    font.draw(surf, f"Nós vencidos: {r.nodes_cleared}   Camada {r.layer + 1}/{len(r.layers)}",
              p.right - 14, p.y + 8, C["text"], 1, "right")
    text_fit(surf, deck_text(rc), p.x + 14, p.y + 28, C["text"], p.w - 28, "left")
    font.draw(surf, font.fit(rc.hint(), p.w - 28), p.x + 14, p.y + 50, C["dim"])
    button(surf, LR.abandon_rect(), "ABANDONAR", ui.mouse, base=(110, 50, 60))
    if hover and not rc.quit_confirm:
        draw_tip(surf, node_tip(rc, hover[0]), hover[1], NODE_COLOR[hover[0]["tipo"]])


def draw_tip(surf: pygame.Surface, lines: list[tuple[str, tuple]], anchor: pygame.Rect,
             edge: tuple[int, int, int]) -> None:
    sc = 1
    w = min(520, max(font.width(t, sc) for t, _ in lines) + 28)
    h = 20 + 18 * len(lines)
    x = max(4, min(W - w - 4, anchor.centerx - w // 2))      # centrado no no, abaixo (ou acima)
    y = anchor.bottom + 10
    if y + h > LR.map_info_rect().y - 4:
        y = anchor.y - h - 10
    tr = pygame.Rect(x, y, w, h)
    if not skin.nine(surf, "tooltip", tr):
        pygame.draw.rect(surf, (16, 18, 30), tr, border_radius=6)
        pygame.draw.rect(surf, edge, tr, 2, border_radius=6)
    for k, (t, c) in enumerate(lines):
        font.draw(surf, font.fit(t, w - 24, sc), tr.x + 14, tr.y + 10 + k * 18, c, sc)


# ------------------------------------------------------------------ draft
def draw_draft_card(surf: pygame.Surface, rc: RunController, r: pygame.Rect, card: Card,
                    selected: bool, hot: bool) -> None:
    special = card.kind == "special"
    main = C["special"] if special else C["effect"]
    pygame.draw.rect(surf, C["special_bg"] if special else C["effect_bg"], r, border_radius=8)
    head = pygame.Rect(r.x + 2, r.y + 2, r.w - 4, 32)
    pygame.draw.rect(surf, main, head, border_top_left_radius=7, border_top_right_radius=7)
    text_fit(surf, card.name, head.centerx, head.centery - font.CAP_H // 2, DARK, head.w - 16, "center")
    font.draw(surf, "ESPÍRITO" if special else "CARTA DE EFEITO", r.x + 12, r.y + 48, main, 1)
    gem(surf, r.right - 28, r.y + 54, C["cost"], str(card.cost))
    art = pygame.Rect(r.x + 8, r.y + 74, r.w - 16, 100)
    pygame.draw.rect(surf, ART_BG["special" if special else "effect"], art)
    spr = sprites.get("special" if special else "effect", card.ref)
    if spr is not None:
        surf.blit(spr, spr.get_rect(center=art.center))
    else:
        font.draw(surf, "?", art.centerx, art.centery - 10, main, 2, "center")
    y = art.bottom + 8
    x, w = r.x + 12, r.w - 24
    if special:
        cx = Wd.stat_pill(surf, x, y, C["atk"], "ATK", str(card.atk), 62).right + 6
        Wd.stat_pill(surf, cx, y, C["hp"], "HP", str(card.hp), 62)
        y += 28
        if card.keywords:
            y = Wd.keyword_row(surf, x, y, r.right - 10,
                               [(k, KEYWORD_LONG.get(k, k.upper())) for k in card.keywords], 1) + 6
        else:
            y += 2
        sents = T.card_sentences(card)
        font.draw(surf, "Ao entrar:" if sents else "Sem efeito ao entrar.", x, y,
                  C["special"] if sents else C["dim"], 1)
        y += 18
    else:
        y += 2
        sents = T.card_sentences(card)
    for sn in sents:
        y = Wd.wrap_lines(surf, sn, x, y, w, C["text"], 1, 3, 14)
    if card.text and y < r.bottom - 40:
        y += 2
        lines = font.wrap('"' + card.text + '"', w, 1)
        room = max(0, (r.bottom - 34 - y) // 14)
        for k, ln in enumerate(lines[:room]):
            if k == room - 1 and len(lines) > room:
                ln = font.fit(ln + "...", w)
            font.draw(surf, ln, x, y, C["dim"], 1)
            y += 14
    owned = rc.draft_owned(card.ref)
    if owned:
        font.draw(surf, f"Já no deck: {owned}", x, r.bottom - 22, C["warn"], 1)
    if selected:
        pygame.draw.rect(surf, WHITE, r.inflate(10, 10), 3, border_radius=11)
    pygame.draw.rect(surf, main, r, 2, border_radius=8)
    if hot and not selected:
        pygame.draw.rect(surf, WHITE, r, 2, border_radius=8)


def draw_list(surf: pygame.Surface, label: str, items: list[tuple[str, int]], x: int, y: int,
              w: int, col, max_lines: int) -> int:
    """Rotulo + itens separados por virgula, quebrando linhas. Devolve o proximo y."""
    txt = ", ".join(f"{n}x {nome}" if n > 1 else nome for nome, n in items) or "nenhuma ainda"
    lines = font.wrap(f"{label}: {txt}", w)
    for k, ln in enumerate(lines[:max_lines]):
        if k == max_lines - 1 and len(lines) > max_lines:
            ln = font.fit(ln + " ...", w)
        font.draw(surf, ln, x, y, col)
        y += 14
    return y


def draw_deck_panel(surf: pygame.Surface, rc: RunController) -> None:
    p = LR.draft_deck_rect()
    panel(surf, p)
    s = rc.deck_summary()
    font.draw(surf, f"SEU DECK: {s['cats']} gatos + {s['cards']} carta{'' if s['cards'] == 1 else 's'}",
              p.x + 12, p.y + 7, C["warn"], 1)
    font.draw(surf, "ESC: desmarcar", p.right - 12, p.y + 7, C["dim"], 1, "right")
    y = draw_list(surf, "Efeitos", rc.deck_counts(False), p.x + 12, p.y + 25, p.w - 24, C["effect"], 2)
    draw_list(surf, "Espíritos", rc.deck_counts(True), p.x + 12, y + 1, p.w - 24, C["special"], 2)


def draw_draft(surf: pygame.Surface, rc: RunController, ui: UIState) -> None:
    descanso = rc.draft_from == "descanso"
    col = NODE_COLOR["descanso"] if descanso else C["good"]
    Wd.title(surf, rc.draft_title(), W // 2, 14, col, 2, "center")
    font.draw(surf, font.fit(rc.draft_subtitle(), W - 60), W // 2, 52, C["dim"], 1, "center")
    cards = rc.draft_cards()
    n = len(cards)
    for i, card in enumerate(cards):
        r = LR.draft_card_rect(i, n)
        sel = rc.draft_sel == i
        draw_draft_card(surf, rc, r, card, sel, r.collidepoint(ui.mouse))
        pr = LR.draft_pick_rect(i, n)
        if sel:
            button(surf, pr, "ESCOLHER", ui.mouse)
        else:
            font.draw(surf, "clique para selecionar", pr.centerx, pr.centery - font.CAP_H // 2, C["dim"], 1, "center")
    draw_deck_panel(surf, rc)


# ------------------------------------------------------------------ fim da run
def draw_finished(surf: pygame.Surface, rc: RunController, ui: UIState) -> None:
    win = rc.run.result == "vitoria"
    col = C["good"] if win else C["bad"]
    Wd.title(surf, "RUN COMPLETA!" if win else "FIM DA RUN", W // 2, 16, col, 3, "center")
    if win:
        sub = f"Você derrotou {rc.end_line[0]}." if rc.end_line else "Você chegou ao fim do mapa."
    else:
        sub = "Você abandonou a run." if rc.abandoned else "Você foi derrotado."
    font.draw(surf, font.fit(sub, W - 40), W // 2, 70, C["dim"], 1, "center")
    left = pygame.Rect(12, 108, 462, 196)
    right = pygame.Rect(486, 108, 462, 196)
    for box in (left, right):
        panel(surf, box)
    font.draw(surf, f"NÓS VENCIDOS: {rc.run.nodes_cleared}", left.x + 14, left.y + 10, C["warn"], 1)
    y = left.y + 34
    for txt, st in rc.path_lines()[:7]:
        mark = {"done": ("OK", C["good"]), "lost": ("X", C["bad"])}.get(st, ("-", C["dim"]))
        font.draw(surf, mark[0], left.x + 14, y, mark[1], 1)
        font.draw(surf, font.fit(txt, left.w - 70), left.x + 54, y, C["text"], 1)
        y += 22
    s = rc.deck_summary()
    font.draw(surf, f"CARTAS ESCOLHIDAS: {s['cards']}", right.x + 14, right.y + 10, C["warn"], 1)
    y = right.y + 34
    items = [(nm, n, C["effect"]) for nm, n in rc.deck_counts(False)] + \
            [(nm, n, C["special"]) for nm, n in rc.deck_counts(True)]
    if not items:
        font.draw(surf, "Nenhuma carta escolhida.", right.x + 14, y, C["dim"], 1)
    for k, (nm, n, c) in enumerate(items):
        if k >= 7:
            font.draw(surf, f"... e mais {len(items) - 7}", right.x + 14, y, C["dim"], 1)
            break
        font.draw(surf, font.fit(f"{n}x {nm}" if n > 1 else nm, right.w - 28), right.x + 14, y, c, 1)
        y += 22
    q = pygame.Rect(12, 314, W - 24, 150)
    panel(surf, q)
    if rc.end_line:
        who, line = rc.end_line
        Wd.leader_art(surf, rc.end_leader_id, pygame.Rect(q.x + 10, q.y + 10, 130, 130), C["enemy"])
        font.draw(surf, who, q.x + 160, q.y + 14, C["enemy"], 1)
        Wd.wrap_lines(surf, '"' + line + '"', q.x + 160, q.y + 38, q.w - 180, C["text"], 1, 6, 16)
    else:
        Wd.leader_art(surf, "heroi", pygame.Rect(q.x + 10, q.y + 10, 130, 130), C["player"])
        font.draw(surf, f"Seed da run: {rc.seed}", q.x + 160, q.y + 14, C["dim"], 1)
    for name, r in LR.end_buttons().items():
        button(surf, r, "NOVA RUN (ENTER)" if name == "new_run" else "SAIR (ESC)", ui.mouse,
               base=None if name == "new_run" else (110, 50, 60))


# ------------------------------------------------------------------ overlays
def draw_quit_confirm(surf: pygame.Surface, rc: RunController, ui: UIState) -> None:
    p = LR.quit_panel()
    Wd.modal(surf, p, "ABANDONAR A RUN?")
    font.draw(surf, "Conta como derrota.", p.centerx, p.y + 80, C["dim"], 1, "center")
    for name, r in LR.quit_buttons().items():
        yes = name == "quit_yes"
        button(surf, r, "SIM, ABANDONAR" if yes else "CONTINUAR", ui.mouse,
               base=(150, 60, 60) if yes else C["button"])


# ------------------------------------------------------------------ quadro completo
def draw_run_frame(surf: pygame.Surface, rc: RunController, ui: UIState) -> None:
    """Quadro 960x540 nativo: duelo ou mapa/draft/fim, mais os overlays (abandonar, aviso)."""
    s = rc.screen
    if s == "duel" and rc.duel_ctrl is not None:
        draw_frame(surf, rc.duel_ctrl, ui)
    else:
        Wd.fill_background(surf)
        if s == "map":
            draw_map(surf, rc, ui)
        elif s == "draft":
            draw_draft(surf, rc, ui)
        else:
            draw_finished(surf, rc, ui)
    if rc.quit_confirm:
        draw_quit_confirm(surf, rc, ui)
    Wd.toast(surf, rc.toast)
