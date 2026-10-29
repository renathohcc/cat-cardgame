"""Logica do tooltip das cartas de duelo (sem janela, testavel): que elemento esta sob o mouse,
quais linhas mostrar, como quebrar o texto e onde posicionar dentro da tela interna 960x540.
O desenho fica em render.draw_tooltip."""
from __future__ import annotations

import pygame

from core.types import Card, FieldCat
from ui import font, layout as L, text as T
from ui.controller import Controller
from ui.theme import C, H, KEYWORD_COLOR, NATURE_COLOR, W

Seg = tuple  # (texto, cor) | ("*stars", n) | ("*wrap", texto, cor)
TIP_W = 330
MARGIN = 6
PAD = 12                # margem interna da caixa (9-slice tem borda de 8 px)
LINE_H = 14             # fonte bitmap: maiusculas de 10 px
TITLE_H = 28           # a primeira linha (nome) e desenhada maior (escala 2)


def hover_elem(ctrl: Controller, mouse: tuple[int, int], dragging: bool = False) -> tuple | None:
    """Carta/lider sob o mouse que merece tooltip, ou None (fora do jogo, arrastando, vazio)."""
    if dragging or ctrl.phase != "play":
        return None
    sh = ctrl.shown
    n_hand = len(sh.me.hand)
    elem = L.hit_test(mouse, n_hand, confirm=ctrl.confirming)
    if elem is None:
        return None
    if elem[0] == "hand":
        return elem if elem[1] < n_hand else None
    if elem[0] == "slot":
        return elem if T.side_view(sh, elem[1]).field[elem[2]] is not None else None
    if elem[0] == "leader":
        return elem if leader_tooltip(ctrl, elem[1]) else None
    return None


def tooltip_lines(ctrl: Controller, card: Card, fc: FieldCat | None, side: str) -> list[list[Seg]]:
    content = ctrl.content
    atk = fc.atk if fc else card.atk
    hp = fc.hp if fc else card.hp
    hpm = fc.hp_max if fc else card.hp
    lines: list[list[Seg]] = [[(T.label(card), C["text"])]]
    if card.kind == "effect":
        lines.append([("CARTA DE EFEITO", C["effect"])])
        lines.append([("Custo ", C["dim"]), (str(card.cost), C["cost"])])
        lines.append([])
        lines.extend([[("*wrap", s, C["text"])] for s in T.card_sentences(card)])
        if card.text:
            lines.append([])
            lines.append([("*wrap", card.text, C["dim"])])
        return lines
    if card.kind == "special":
        lines.append([("ESPÍRITO", C["special"])])
        lines.append([("Só existe nesta run", C["dim"])])
    if card.cat_name and card.breed_name:
        lines.append([(f"Raça: {card.breed_name}", C["dim"])])
    lines.append([("Custo ", C["dim"]), (str(card.cost), C["cost"]), ("   ATK ", C["dim"]),
                  (str(atk), C["buff"] if fc and fc.atk_bonus_turn else C["atk"]),
                  ("   HP ", C["dim"]), (f"{hp}/{hpm}", C["hp"])])
    if fc is not None and fc.atk_bonus_turn:
        lines.append([("*wrap", f"ATK +{fc.atk_bonus_turn} até o fim do turno", C["buff"])])
    if card.nature:
        nat = content.natures.get(card.nature, {})
        lines.append([("Natureza: ", C["dim"]),
                      (nat.get("nome", card.nature), NATURE_COLOR.get(card.nature, C["text"]))])
        if nat:
            lines.append([(f"{nat.get('atk', 0):+d} ATK, {nat.get('hp', 0):+d} HP", C["dim"])])
    if card.sex:
        lines.append([("Sexo: ", C["dim"]),
                      (T.SEX_NAME[card.sex], C["male"] if card.sex == "M" else C["female"])])
    if card.iv_atk is not None:
        lines.append([("IV ATK ", C["atk"]), ("*stars", card.iv_atk), (f" {card.iv_atk}/5", C["dim"])])
        lines.append([("IV HP  ", C["hp"]), ("*stars", card.iv_hp), (f" {card.iv_hp}/5", C["dim"])])
    if card.kind == "special":
        lines.append([])
        sentences = T.card_sentences(card)
        if sentences:
            lines.append([("Ao entrar:", C["special"])])
            lines.extend([[("*wrap", s, C["text"])] for s in sentences])
        else:
            lines.append([("Sem efeito ao entrar", C["dim"])])
    if card.text:
        lines.append([])
        lines.append([("*wrap", card.text, C["dim"])])
    kws = fc.keywords if fc else card.keywords
    for k in kws:
        nome, texto = ctrl.keyword_text(k)
        lines.append([])
        lines.append([(nome, KEYWORD_COLOR.get(k, C["text"]))])
        lines.append([("*wrap", texto)])
        if k == "primeira-patada" and fc is not None:
            ok = fc.first_strike_available
            lines.append([("*wrap", "Pronta: dano dobrado no próximo ataque" if ok else "Já usada neste gato",
                           C["good"] if ok else C["dim"])])
    if fc is not None:
        key, txt = ctrl.cat_status(side, fc)
        if txt:
            lines.append([])
            lines.append([("*wrap", txt, C["ready"] if key == "ready" else C["warn"])])
    return lines


def leader_tooltip(ctrl: Controller, side: str) -> list[list[Seg]] | None:
    sv = T.side_view(ctrl.shown, side)
    if side != "enemy" or (ctrl.enemy is None and not sv.rule):
        return None
    lines: list[list[Seg]] = []
    if ctrl.enemy is not None:
        lines.append([(ctrl.enemy["nome"], C["text"])])
        lines.append([({"batalha": "Batalha", "elite": "Elite", "chefe": "Chefe"}.get(
            ctrl.enemy.get("tipo", ""), ""), C["warn"])])
    if sv.rule:
        lines.append([])
        lines.append([("*wrap", "Regra própria: " + T.rule_name(sv.rule), C["warn"])])
        lines.append([("*wrap", T.rule_text(sv.rule), C["text"])])
    return lines


def wrap_lines(lines: list[list[Seg]], width: int = TIP_W) -> list[list[Seg]]:
    """Expande os segmentos "*wrap" em linhas que cabem em `width`."""
    out: list[list[Seg]] = []
    for segs in lines:
        if segs and segs[0][0] == "*wrap":
            col = segs[0][2] if len(segs[0]) > 2 else C["dim"]
            for ln in font.wrap(segs[0][1], width - 2 * PAD):
                out.append([(ln, col)])
        else:
            out.append(segs)
    return out


def lines_for(ctrl: Controller, elem: tuple) -> tuple[list[list[Seg]], str, pygame.Rect] | None:
    """(linhas ja quebradas, lado, ancora) do elemento, ou None se nao ha o que mostrar."""
    sh = ctrl.shown
    if elem[0] == "leader":
        raw = leader_tooltip(ctrl, elem[1])
        return (wrap_lines(raw), elem[1], L.leader_rect(elem[1])) if raw else None
    if elem[0] == "hand":
        if elem[1] >= len(sh.me.hand):
            return None
        card = sh.me.hand[elem[1]]
        raw = tooltip_lines(ctrl, card, None, "player")
        return wrap_lines(raw), "player", L.hand_hit_rect(elem[1], len(sh.me.hand))
    if elem[0] == "slot":
        fc = T.side_view(sh, elem[1]).field[elem[2]]
        if fc is None:
            return None
        return (wrap_lines(tooltip_lines(ctrl, fc.card, fc, elem[1])), elem[1],
                L.slot_rect(elem[1], elem[2]))
    return None


def is_title(k: int, segs: list[Seg]) -> bool:
    """Primeira linha com um unico segmento de texto = titulo (nome da carta)."""
    return k == 0 and len(segs) == 1 and segs[0][0] not in ("*stars", "*wrap")


def box_height(lines: "int | list[list[Seg]]") -> int:
    """Altura da caixa para as linhas (ou para N linhas comuns)."""
    if isinstance(lines, int):
        return 2 * PAD + LINE_H * lines
    extra = TITLE_H - LINE_H if lines and is_title(0, lines[0]) else 0
    return 2 * PAD + LINE_H * len(lines) + extra


def place(kind: str, anchor: pygame.Rect, h: int, w: int = TIP_W) -> pygame.Rect:
    """Retangulo do tooltip, sempre dentro de 960x540. Mao: acima da carta; campo: ao lado;
    lider: abaixo. Se nao couber no lugar preferido, tenta o oposto e por fim limita."""
    if kind == "hand":
        x = anchor.centerx - w // 2
        y = anchor.y - h - 6
        if y < MARGIN:                       # nao cabe acima: ao lado da carta
            x = anchor.right + 6 if anchor.right + 6 + w <= W - MARGIN else anchor.x - w - 6
            y = H - h - MARGIN
    elif kind == "leader":
        x, y = anchor.x + 8, anchor.bottom + 8
    else:
        x = anchor.right + 8
        if x + w > W - MARGIN:
            x = anchor.x - w - 8
        y = anchor.y
    x = max(MARGIN, min(W - w - MARGIN, x))
    y = max(MARGIN, min(H - h - MARGIN, y))
    return pygame.Rect(x, y, w, h)
