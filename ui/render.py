"""Desenho do duelo (retangulos e texto, paleta em theme.py). Nao tem regra de jogo."""
from __future__ import annotations

import math
from dataclasses import dataclass

import pygame

from core.types import Card, FieldCat
from ui import font, layout as L, text as T
from ui.controller import Controller
from ui.theme import (
    BREED_COLOR, C, DEFAULT_BREED_COLOR, H, KEYWORD_COLOR, KEYWORD_LONG, KEYWORD_SHORT,
    NATURE_COLOR, W,
)

DARK = C["dark"]


@dataclass
class UIState:
    mouse: tuple[int, int] = (-100, -100)
    drag: tuple[tuple, tuple[int, int]] | None = None   # (elem origem, posicao)
    t: float = 0.0


# ------------------------------------------------------------------ primitivas
_star_cache: dict[tuple, pygame.Surface] = {}
_STAR = ("..#..", ".###.", "#####", ".###.", ".#.#.")


def star(color: tuple[int, int, int]) -> pygame.Surface:
    s = _star_cache.get(color)
    if s is None:
        s = pygame.Surface((5, 5), pygame.SRCALPHA)
        for y, row in enumerate(_STAR):
            for x, c in enumerate(row):
                if c == "#":
                    s.set_at((x, y), color)
        _star_cache[color] = s
    return s


def stars(surf: pygame.Surface, x: int, y: int, n: int | None, pitch: int = 6) -> None:
    for i in range(5):
        on = n is not None and i < n
        surf.blit(star(C["star_on"] if on else C["star_off"]), (x + i * pitch, y))


def tint(surf: pygame.Surface, rect: pygame.Rect, color: tuple[int, int, int], alpha: int) -> None:
    if alpha <= 0:
        return
    ov = pygame.Surface(rect.size, pygame.SRCALPHA)
    ov.fill((*color, max(0, min(255, alpha))))
    surf.blit(ov, rect.topleft)


def border(surf: pygame.Surface, rect: pygame.Rect, color: tuple[int, int, int], w: int = 1) -> None:
    pygame.draw.rect(surf, color, rect, w)


def pulse(t: float, speed: float = 6.0) -> float:
    return 0.5 + 0.5 * math.sin(t * speed)


def outlined(surf: pygame.Surface, txt: str, x: int, y: int, color, scale: int = 1,
             align: str = "center") -> None:
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        font.draw(surf, txt, x + dx, y + dy, DARK, scale, align)
    font.draw(surf, txt, x, y, color, scale, align)


def pill(surf: pygame.Surface, rect: pygame.Rect, alpha: int = 200) -> None:
    tint(surf, rect, DARK, alpha)


def label_box(surf: pygame.Surface, rect: pygame.Rect, fill, txt: str, color=(255, 255, 255)) -> None:
    pygame.draw.rect(surf, fill, rect)
    font.draw(surf, txt, rect.centerx, rect.y + (rect.h - font.CAP_H) // 2, color, 1, "center")


# ------------------------------------------------------------------ carta
_HEAD_COLOR = {"DANO": C["bad"], "CURA": C["good"], "ATK": C["buff"]}


def head_color(head: str) -> tuple[int, int, int]:
    for key, col in _HEAD_COLOR.items():
        if key in head:
            return col
    return C["energy"]


def draw_effect_card(surf: pygame.Surface, r: pygame.Rect, card: Card, *, enemy: bool = False) -> None:
    pygame.draw.rect(surf, C["effect_bg"], r)
    pygame.draw.rect(surf, C["effect"], (r.x + 1, r.y + 1, r.w - 2, 11))
    font.draw(surf, font.fit(card.name, r.w - 6), r.x + 3, r.y + 3, DARK)
    y = r.y + 16
    for act in card.actions[:2]:
        head, tgt = T.action_short(act)
        font.draw(surf, font.fit(head, r.w - 6), r.x + 3, y, head_color(head))
        y += 9
        if tgt:
            font.draw(surf, font.fit(tgt, r.w - 6), r.x + 3, y, C["dim"])
            y += 9
        y += 2
    row_y = r.y + 51
    label_box(surf, pygame.Rect(r.x + 2, row_y, 15, 10), C["cost"], str(card.cost))
    label_box(surf, pygame.Rect(r.x + 19, row_y, r.w - 21, 10), C["effect"], "EFEITO", DARK)
    border(surf, r, C["effect"], 1)


def draw_card(surf: pygame.Surface, r: pygame.Rect, card: Card, atk: int, hp: int, hp_max: int,
              keywords: tuple[str, ...], *, enemy: bool = False, show_max: bool = True,
              atk_bonus: int = 0) -> None:
    if card.kind == "effect":
        draw_effect_card(surf, r, card, enemy=enemy)
        return
    special = card.kind == "special"
    pygame.draw.rect(surf, C["special_bg"] if special else
                     (C["card_enemy"] if enemy else C["card"]), r)
    # faixa do titulo (cor da raca; Espirito = dourado)
    bc = C["special"] if special else BREED_COLOR.get(card.breed or "", DEFAULT_BREED_COLOR)
    pygame.draw.rect(surf, bc, (r.x + 1, r.y + 1, r.w - 2, 11))
    title = font.fit(T.label(card), r.w - 6)
    font.draw(surf, title, r.x + 3, r.y + 3, DARK)
    # natureza e sexo (Espirito: etiqueta)
    y = r.y + 15
    if special:
        font.draw(surf, "ESPÍRITO", r.x + 3, y, C["special"])
    if card.nature:
        nat = card.nature.capitalize()
        w = font.draw(surf, nat, r.x + 3, y, NATURE_COLOR.get(card.nature, C["text"]))
        if card.sex:
            sc = C["male"] if card.sex == "M" else C["female"]
            font.draw(surf, card.sex, r.right - 4, y, sc, 1, "right")
    # keywords
    kws = list(keywords)
    if kws:
        names = KEYWORD_LONG if len(kws) == 1 else KEYWORD_SHORT
        cx = r.x + 3
        for k in kws:
            txt = names.get(k, k[:4].upper())
            w = font.width(txt) + 4
            chip = pygame.Rect(cx, r.y + 24, w, 10)
            pygame.draw.rect(surf, KEYWORD_COLOR.get(k, C["dim"]), chip)
            font.draw(surf, txt, chip.x + 2, chip.y + 2, DARK)
            cx += w + 2
    if special:                      # sem IV: status fixos e resumo do "ao entrar"
        lines = T.card_summary(card)[:2]
        if not lines:
            font.draw(surf, "SEM EFEITO", r.x + 3, r.y + 38, C["dim"])
        for k, ln in enumerate(lines):
            font.draw(surf, font.fit(ln, r.w - 6), r.x + 3, r.y + 35 + 8 * k,
                      head_color(ln) if k == 0 else C["dim"])
    else:                            # estrelas de IV
        pygame.draw.rect(surf, C["atk"], (r.x + 3, r.y + 37, 3, 5))
        stars(surf, r.x + 9, r.y + 37, card.iv_atk)
        pygame.draw.rect(surf, C["hp"], (r.x + 3, r.y + 44, 3, 5))
        stars(surf, r.x + 9, r.y + 44, card.iv_hp)
    # custo / ATK / HP
    row_y = r.y + 51
    cost = pygame.Rect(r.x + 2, row_y, 15, 10)
    atkb = pygame.Rect(r.x + 19, row_y, 15, 10)
    hpb = pygame.Rect(r.x + 36, row_y, r.w - 38, 10)
    label_box(surf, cost, C["cost"], str(card.cost))
    if atk_bonus > 0:                # buff temporario de ATK: destaque dourado + seta
        label_box(surf, atkb, C["buff"], str(atk), DARK)
        for k in range(3):
            pygame.draw.line(surf, C["buff"], (atkb.right - 3 - k, atkb.y - 1 - k),
                             (atkb.right - 3 + k, atkb.y - 1 - k))
    else:
        label_box(surf, atkb, C["atk"], str(atk))
    hp_txt = f"{hp}/{hp_max}" if show_max and font.width(f"{hp}/{hp_max}") <= hpb.w - 2 else str(hp)
    hp_col = (255, 255, 255) if hp >= hp_max else (255, 230, 120)
    label_box(surf, hpb, C["hp"] if hp >= hp_max else (170, 120, 40), hp_txt, hp_col)
    border(surf, r, C["special"] if special else C["card_edge"], 1)


# ------------------------------------------------------------------ campo
def draw_empty_slot(surf: pygame.Surface, r: pygame.Rect, drop: bool, t: float) -> None:
    pygame.draw.rect(surf, C["slot"], r)
    border(surf, r, C["slot_edge"], 1)
    if drop:
        a = 70 + int(70 * pulse(t))
        tint(surf, r, C["drop"], a)
        border(surf, r, C["drop"], 2)
        font.draw(surf, "JOGAR", r.centerx, r.centery - 8, (255, 255, 255), 1, "center")
        font.draw(surf, "AQUI", r.centerx, r.centery + 3, (255, 255, 255), 1, "center")


def draw_field_cat(surf: pygame.Surface, ctrl: Controller, side: str, n: int, ui: UIState,
                   *, hidden_fx: bool = False) -> None:
    sv = T.side_view(ctrl.shown, side)
    fc: FieldCat = sv.field[n]
    r = L.slot_rect(side, n)
    draw_card(surf, r, fc.card, fc.atk, fc.hp, fc.hp_max, fc.keywords, enemy=side == "enemy",
              atk_bonus=fc.atk_bonus_turn)
    status, _ = ctrl.cat_status(side, fc)
    if status in ("spent", "new", "wait"):
        tint(surf, r, DARK, 130)
        txt = {"spent": "JÁ ATACOU", "new": "ENTROU", "wait": "AGUARDA"}[status]
        w = font.width(txt) + 6
        pr = pygame.Rect(0, 0, w, 11)
        pr.center = r.center
        pill(surf, pr, 220)
        font.draw(surf, txt, r.centerx, pr.y + 2, C["dim"], 1, "center")
    if "provocar" in fc.keywords:
        border(surf, r, C["taunt"], 2)
    if status == "ready" and side == "player":
        border(surf, r.inflate(2, 2), C["ready"], 1)
        border(surf, r.inflate(4, 4), C["ready"] if pulse(ui.t) > 0.5 else (60, 150, 80), 1)
    if ctrl.sel == ("slot", n) and side == "player":
        border(surf, r.inflate(4, 4), C["select"], 2)
    label = ctrl.slot_target(side, n)
    if label:
        col = C["target"] if side == "enemy" else C["drop"]
        tint(surf, r, col, 50 + int(60 * pulse(ui.t)))
        border(surf, r.inflate(4, 4), col, 2)
        pr = pygame.Rect(0, 0, font.width(label) + 8, 11)
        pr.center = (r.centerx, r.y + 41)
        pill(surf, pr, 230)
        font.draw(surf, label, r.centerx, pr.y + 2, (255, 255, 255), 1, "center")


def draw_spirit_ghost(surf: pygame.Surface, card: Card, r: pygame.Rect) -> None:
    """Espirito posicionado, esperando o alvo do "ao entrar"."""
    draw_card(surf, r, card, card.atk, card.hp, card.hp, card.keywords)
    border(surf, r.inflate(4, 4), C["select"], 2)
    pr = pygame.Rect(r.x + 4, r.y + 36, r.w - 8, 20)
    pill(surf, pr, 235)
    font.draw(surf, "ESCOLHA", r.centerx, pr.y + 3, (255, 255, 255), 1, "center")
    font.draw(surf, "O ALVO", r.centerx, pr.y + 11, C["warn"], 1, "center")


def hp_color(hp: int, mx: int) -> tuple[int, int, int]:
    f = hp / mx if mx else 0
    if f > 0.5:
        return (40, 130, 78)
    if f > 0.25:
        return (160, 126, 30)
    return (160, 44, 44)


_TIPO_TAG = {"elite": "ELITE", "chefe": "CHEFE"}


def draw_leader(surf: pygame.Surface, ctrl: Controller, side: str, ui: UIState) -> None:
    r = L.leader_rect(side)
    sv = T.side_view(ctrl.shown, side)
    pygame.draw.rect(surf, C["dark"], r)
    frac = max(0.0, sv.leader_hp / sv.leader_hp_max) if sv.leader_hp_max else 0
    pygame.draw.rect(surf, hp_color(sv.leader_hp, sv.leader_hp_max),
                     (r.x, r.y, int(r.w * frac), r.h))
    tgt = ctrl.leader_target(side)
    cat_sel = side == "enemy" and ctrl.sel and ctrl.sel[0] == "slot"
    hp_txt = f"{sv.leader_hp}/{sv.leader_hp_max}"
    if tgt:
        a = 120 + int(120 * pulse(ui.t))
        tint(surf, r, C["target"] if side == "enemy" else C["drop"], a)
        border(surf, r, (255, 255, 255), 2)
        outlined(surf, "ATACAR LÍDER" if tgt == "attack" else "ALVO DO EFEITO",
                 r.centerx, r.y + 4, (255, 255, 255), 2)
        font.draw(surf, hp_txt, r.right - 5, r.y + 8, (255, 255, 255), 1, "right")
        return
    person = ctrl.enemy if side == "enemy" else None
    if person is None:
        name = "LÍDER INIMIGO" if side == "enemy" else "SEU LÍDER"
        font.draw(surf, name, r.x + 6, r.y + 8, (255, 255, 255))
        if cat_sel:
            font.draw(surf, "PROTEGIDO POR PROVOCAR", r.centerx, r.y + 8, C["taunt"], 1, "center")
    else:                                   # inimigo-pessoa: nome e regra propria em 2 linhas
        w = font.draw(surf, person["nome"], r.x + 6, r.y + 3, (255, 255, 255))
        tag = _TIPO_TAG.get(person.get("tipo", ""))
        if tag:
            chip = pygame.Rect(r.x + 12 + w, r.y + 2, font.width(tag) + 4, 9)
            pygame.draw.rect(surf, C["warn"], chip)
            font.draw(surf, tag, chip.x + 2, chip.y + 1, DARK)
        if cat_sel and ctrl.taunt_in_way():
            font.draw(surf, "PROTEGIDO POR PROVOCAR", r.x + 6, r.y + 13, C["taunt"])
        elif sv.rule:
            font.draw(surf, "Regra: " + T.rule_name(sv.rule), r.x + 6, r.y + 13, C["warn"])
    font.draw(surf, hp_txt, r.right - 6, r.y + 4, (255, 255, 255), 2, "right")
    border(surf, r, C["panel_edge"], 1)


# ------------------------------------------------------------------ mao
def draw_hand(surf: pygame.Surface, ctrl: Controller, ui: UIState) -> int | None:
    """Desenha a mao; devolve o indice da carta arrastada (para nao duplicar), se houver."""
    hand = ctrl.shown.me.hand
    n = len(hand)
    dragging = ui.drag[0][1] if ui.drag and ui.drag[0][0] == "hand" else None
    for i, card in enumerate(hand):
        if i == dragging:
            continue
        r = L.hand_rect(i, n)
        sel = ctrl.sel == ("hand", i)
        ok, why = ctrl.hand_state(i)
        if sel:
            r = r.move(0, -5)
        draw_card(surf, r, card, card.atk, card.hp, card.hp, card.keywords)
        if not ok:
            tint(surf, r, DARK, 150)
            lines = why
            h = 10 * len(lines) + 4
            pr = pygame.Rect(r.x + 3, r.centery - h // 2, r.w - 6, h)
            pill(surf, pr, 230)
            for k, ln in enumerate(lines):
                font.draw(surf, ln, r.centerx, pr.y + 3 + 10 * k, C["warn"], 1, "center")
        elif ctrl.can_act():
            border(surf, r, C["ready"], 1)
        if sel:
            border(surf, r.inflate(4, 4), C["select"], 2)
            if ctrl.needs_confirm():
                pr = pygame.Rect(r.x + 4, r.y + 40, r.w - 8, 20)
                pill(surf, pr, 235)
                font.draw(surf, "CLIQUE DE", r.centerx, pr.y + 3, (255, 255, 255), 1, "center")
                font.draw(surf, "NOVO: USAR", r.centerx, pr.y + 11, C["warn"], 1, "center")
    return dragging


# ------------------------------------------------------------------ painel
def draw_panel(surf: pygame.Surface, ctrl: Controller, ui: UIState) -> None:
    sh = ctrl.shown
    # indicador de turno
    r = L.turn_rect()
    mine = sh.turn_side == "player"
    pygame.draw.rect(surf, (40, 110, 70) if mine else (130, 50, 56), r)
    font.draw(surf, "SEU TURNO" if mine else "TURNO DO INIMIGO", r.centerx, r.y + 4,
              (255, 255, 255), 1, "center")
    started = "você" if ctrl.first == "player" else "inimigo"
    n = T.side_view(sh, sh.turn_side).turns_taken
    font.draw(surf, f"Turno {n} - {started} começou", r.centerx, r.y + 14,
              (210, 230, 220), 1, "center")
    # contadores
    r = L.info_rect()
    pygame.draw.rect(surf, C["panel"], r)
    border(surf, r, C["panel_edge"], 1)
    o = sh.opponent
    font.draw(surf, f"Inimigo: mão {o.hand_count}  deck {o.deck_count}", r.x + 5, r.y + 4, C["enemy"])
    te = ctrl.turn_energy["enemy"]
    font.draw(surf, f"Energia dele: {o.energy}/{te}" if te else "Energia dele: -", r.x + 5, r.y + 14,
              C["dim"])
    font.draw(surf, f"Você: mão {sh.me.hand_count}  deck {sh.me.deck_count}", r.x + 5, r.y + 24,
              C["player"])
    draw_log(surf, ctrl)
    draw_pass_button(surf, ctrl, ui)


_LOG_COLOR = {"player": C["player"], "enemy": (255, 160, 160), "warn": C["warn"],
              "good": C["good"], "bad": C["bad"]}


def draw_log(surf: pygame.Surface, ctrl: Controller) -> None:
    r = L.log_rect()
    pygame.draw.rect(surf, C["panel"], r)
    border(surf, r, C["panel_edge"], 1)
    font.draw(surf, "REGISTRO", r.x + 5, r.y + 3, C["dim"])
    cap = (r.h - 15) // 10
    rows: list[tuple[str, tuple]] = []
    for txt, side in reversed(ctrl.log[-14:]):           # do mais novo para o mais antigo
        col = _LOG_COLOR.get(side, C["text"])
        lines = font.wrap(txt, r.w - 12)
        if len(rows) + len(lines) > cap:
            break
        rows = [(ln if k == 0 else " " + ln, col) for k, ln in enumerate(lines)] + rows
    for k, (ln, col) in enumerate(rows):
        font.draw(surf, ln, r.x + 5, r.y + 15 + k * 10, col)


def draw_pass_button(surf: pygame.Surface, ctrl: Controller, ui: UIState) -> None:
    r = L.pass_rect()
    active = ctrl.can_act()
    if active and ctrl.confirming:
        for rect, txt, fill, hot_fill in (
                (L.pass_yes_rect(), "SIM, PASSAR", (150, 70, 40), (190, 100, 50)),
                (L.pass_no_rect(), "NÃO", C["button_off"], C["button"])):
            hot = rect.collidepoint(ui.mouse)
            pygame.draw.rect(surf, hot_fill if hot else fill, rect)
            border(surf, rect, (255, 255, 255), 2 if hot else 1)
            font.draw(surf, txt, rect.centerx, rect.y + 9, (255, 255, 255), 1, "center")
        return
    hot = active and L.pass_rect().collidepoint(ui.mouse)
    if not active:
        fill, txt, col = C["button_off"], "AGUARDE...", C["dim"]
    else:
        fill = C["button_hot"] if (hot or (ctrl.pass_only and pulse(ui.t, 7) > 0.5)) else C["button"]
        txt, col = "PASSAR TURNO", (255, 255, 255)
    pygame.draw.rect(surf, fill, r)
    border(surf, r, (255, 255, 255) if ctrl.pass_only and active else C["panel_edge"], 2 if ctrl.pass_only else 1)
    scale = 2 if font.width(txt, 2) <= r.w - 28 else 1
    if scale == 2:
        font.draw(surf, txt, r.centerx - 8, r.y + 6, col, 2, "center")
    else:
        font.draw(surf, txt, r.centerx - 8, r.y + 9, col, 1, "center")
    if active:
        font.draw(surf, "[E]", r.right - 4, r.y + 9, (220, 255, 230), 1, "right")


# ------------------------------------------------------------------ barra inferior
def draw_bar(surf: pygame.Surface, ctrl: Controller, ui: UIState) -> None:
    r = L.energy_rect()
    pygame.draw.rect(surf, C["panel"], r)
    border(surf, r, C["panel_edge"], 1)
    sh = ctrl.shown
    font.draw(surf, "ENERGIA", r.x + 4, r.y + 6, C["text"])
    cap = ctrl.energy_cap
    tot = ctrl.turn_energy["player"]
    en = sh.me.energy
    gx = r.x + 50
    for i in range(cap):
        g = pygame.Rect(gx + i * 10, r.y + 5, 8, 8)
        if i < en:
            pygame.draw.rect(surf, C["cost"], g)
            pygame.draw.rect(surf, (170, 210, 255), (g.x + 1, g.y + 1, 3, 2))
        elif i < tot:
            border(surf, g, C["cost"], 1)
        else:
            border(surf, g, C["star_off"], 1)
    font.draw(surf, f"{en}/{tot}", gx + cap * 10 + 4, r.y + 6, (170, 210, 255))
    m = L.message_rect()
    t = ctrl.toast
    if t is not None:
        fill, col = {"error": ((100, 36, 40), (255, 190, 190)), "warn": ((110, 84, 20), (255, 230, 150)),
                     "info": ((36, 64, 100), (200, 225, 255))}[t.kind]
        pygame.draw.rect(surf, fill, m)
        border(surf, m, col, 1)
        font.draw(surf, font.fit(t.text, m.w - 10), m.x + 5, m.y + 6, col)
    else:
        pygame.draw.rect(surf, C["panel"], m)
        border(surf, m, C["panel_edge"], 1)
        font.draw(surf, font.fit(ctrl.hint(), m.w - 10), m.x + 5, m.y + 6, C["dim"])


# ------------------------------------------------------------------ efeitos
def fx_rect(side: str, slot: int | None) -> pygame.Rect:
    return L.leader_rect(side) if slot is None else L.slot_rect(side, slot)


_FX_COLOR = {"bad": "bad", "good": "good", "buff": "buff", "dim": "dim", "energy": "energy"}


def draw_tag_fx(surf: pygame.Surface, f, k: float) -> None:
    r = L.energy_rect() if (f.card == "energy" and f.side == "player") else L.info_rect()
    outlined(surf, f.text, r.centerx, r.y - 4 - int(14 * k), C[_FX_COLOR.get(f.color, "good")], 1)


def draw_cast_fx(surf: pygame.Surface, f, k: float) -> None:
    w = font.width(f.text) + 14
    pr = pygame.Rect(0, 0, w, 13)
    pr.center = (L.FIELD_X + L.MAIN_W // 2, 91)
    col = C["player"] if f.side == "player" else C["enemy"]
    pill(surf, pr, int(235 * min(1.0, (1 - k) * 3)))
    border(surf, pr, col, 1)
    if k < 0.8:
        font.draw(surf, f.text, pr.centerx, pr.y + 3, (255, 255, 255), 1, "center")


def draw_fx(surf: pygame.Surface, ctrl: Controller) -> None:
    for f in ctrl.fx:
        k = f.age / f.life
        if f.kind == "tag":
            draw_tag_fx(surf, f, k)
            continue
        if f.kind == "cast":
            draw_cast_fx(surf, f, k)
            continue
        r = fx_rect(f.side, f.slot)
        if f.kind == "flash":
            col = (255, 255, 255) if f.color == "bad" else C["buff" if f.color == "buff" else "good"]
            tint(surf, r, col, int(200 * (1 - k)))
        elif f.kind == "float":
            col = C[_FX_COLOR.get(f.color, "good")]
            scale = 2 if f.slot is None else 2
            y = r.centery - 7 - int(18 * k)
            if f.slot is None:
                outlined(surf, f.text, r.centerx - 40 if f.side == "enemy" else r.centerx - 40,
                         r.y - 2 - int(6 * k), col, 3)
            else:
                outlined(surf, f.text, r.centerx, y, col, scale)
        elif f.kind == "line":
            r2 = fx_rect(f.to_side, f.to_slot)
            a, b = pygame.Vector2(r.center), pygame.Vector2(r2.center)
            head = a + (b - a) * min(1.0, k / 0.5)
            pygame.draw.line(surf, (255, 255, 255), a, head, 3)
            pygame.draw.line(surf, C["warn"], a, head, 1)
            pygame.draw.circle(surf, (255, 255, 255), (int(head.x), int(head.y)), 4)
        elif f.kind == "die":
            ghost = pygame.Surface(r.size, pygame.SRCALPHA)
            c: Card = f.card
            draw_card(ghost, ghost.get_rect(), c, c.atk, 0, c.hp, c.keywords, enemy=f.side == "enemy")
            ghost.set_alpha(int(255 * (1 - k)))
            surf.blit(ghost, r.topleft)
            tint(surf, r, C["bad"], int(120 * (1 - k)))
        elif f.kind == "enter":
            grow = int(8 * (1 - k))
            border(surf, r.inflate(grow, grow), (255, 255, 255), 2)


# ------------------------------------------------------------------ tooltip
Seg = tuple  # (texto, cor) ou ("*stars", n)


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
        lines.append([("ESPÍRITO", C["special"]), (" - só existe nesta run", C["dim"])])
    if card.cat_name and card.breed_name:
        lines.append([(f"Raça: {card.breed_name}", C["dim"])])
    lines.append([("Custo ", C["dim"]), (str(card.cost), C["cost"]), ("   ATK ", C["dim"]),
                  (str(atk), C["buff"] if fc and fc.atk_bonus_turn else C["atk"]),
                  ("   HP ", C["dim"]), (f"{hp}/{hpm}", C["hp"])])
    if fc is not None and fc.atk_bonus_turn:
        lines.append([(f"   ATK +{fc.atk_bonus_turn} até o fim do turno", C["buff"])])
    if card.nature:
        nat = content.natures.get(card.nature, {})
        lines.append([("Natureza: ", C["dim"]),
                      (nat.get("nome", card.nature), NATURE_COLOR.get(card.nature, C["text"]))])
        if nat:
            lines.append([(f"   {nat.get('atk', 0):+d} ATK, {nat.get('hp', 0):+d} HP", C["dim"])])
    if card.sex:
        lines.append([("Sexo: ", C["dim"]), (T.SEX_NAME[card.sex], C["male"] if card.sex == "M" else C["female"])])
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
            lines.append([("*wrap", card.text, C["dim"])])
    kws = fc.keywords if fc else card.keywords
    for k in kws:
        nome, texto = ctrl.keyword_text(k)
        lines.append([])
        lines.append([(nome, KEYWORD_COLOR.get(k, C["text"]))])
        lines.append([("*wrap", texto)])
        if k == "primeira-patada" and fc is not None:
            ok = fc.first_strike_available
            lines.append([("Pronta: dano dobrado no próximo ataque" if ok else "Já usada neste gato",
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
        lines.append([("Regra própria: " + T.rule_name(sv.rule), C["warn"])])
        lines.append([("*wrap", T.rule_text(sv.rule), C["text"])])
    return lines


def draw_tooltip(surf: pygame.Surface, ctrl: Controller, elem: tuple) -> None:
    sh = ctrl.shown
    if elem[0] == "leader":
        lines = leader_tooltip(ctrl, elem[1])
        if not lines:
            return
        card, fc, side, anchor = None, None, elem[1], L.leader_rect(elem[1])
    elif elem[0] == "hand":
        if elem[1] >= len(sh.me.hand):
            return
        card, fc, side = sh.me.hand[elem[1]], None, "player"
        anchor = L.hand_rect(elem[1], len(sh.me.hand))
    elif elem[0] == "slot":
        side = elem[1]
        fc = T.side_view(sh, side).field[elem[2]]
        if fc is None:
            return
        card, anchor = fc.card, L.slot_rect(side, elem[2])
    else:
        return
    tw = 168
    rows: list[tuple[str, tuple, int]] = []     # (kind, payload, ...)
    out: list[list] = []
    for segs in (lines if elem[0] == "leader" else tooltip_lines(ctrl, card, fc, side)):
        if segs and segs[0][0] == "*wrap":
            col = segs[0][2] if len(segs[0]) > 2 else C["dim"]
            for ln in font.wrap(segs[0][1], tw - 12):
                out.append([(ln, col)])
        else:
            out.append(segs)
    h = 8 + 10 * len(out)
    if elem[0] == "leader":
        x = max(2, min(W - tw - 2, anchor.x + 8))
        y = anchor.bottom + 4
    elif elem[0] == "hand":
        x = max(2, min(W - tw - 2, anchor.centerx - tw // 2))
        y = anchor.y - h - 6
    else:
        x = anchor.right + 6
        if x + tw > W - 2:
            x = anchor.x - tw - 6
        y = max(2, min(H - h - 2, anchor.y))
    tr = pygame.Rect(x, max(2, y), tw, h)
    pygame.draw.rect(surf, (16, 18, 30), tr)
    border(surf, tr, C["player"] if side == "player" else C["enemy"], 1)
    for k, segs in enumerate(out):
        cx, cy = tr.x + 6, tr.y + 5 + k * 10
        for seg in segs:
            if seg[0] == "*stars":
                stars(surf, cx, cy + 1, seg[1])
                cx += 31
            else:
                cx += font.draw(surf, seg[0], cx, cy, seg[1])


# ------------------------------------------------------------------ overlays
def draw_banner(surf: pygame.Surface, ctrl: Controller) -> None:
    if not ctrl.banner:
        return
    lines, _ = ctrl.banner
    big = len(lines) > 1
    scale = 3 if big else 2
    w = max(font.width(lines[0], scale), *(font.width(s) for s in lines[1:]), 0) + 24
    h = 8 + 8 * scale + (12 * (len(lines) - 1) if big else 0) + 8
    r = pygame.Rect(0, 0, w, h)
    r.center = (L.FIELD_X + L.MAIN_W // 2, 124)
    pill(surf, r, 225)
    border(surf, r, C["warn"], 2)
    font.draw(surf, lines[0], r.centerx, r.y + 8, C["warn"] if big else (255, 255, 255), scale, "center")
    for k, ln in enumerate(lines[1:]):
        font.draw(surf, ln, r.centerx, r.y + 14 + 8 * scale + k * 12, C["text"], 1, "center")


def draw_dice(surf: pygame.Surface, ctrl: Controller, ui: UIState) -> None:
    tint(surf, pygame.Rect(0, 0, W, H), (8, 10, 20), 215)
    p = pygame.Rect(90, 66, 300, 130)
    pygame.draw.rect(surf, C["panel"], p)
    border(surf, p, C["warn"], 2)
    font.draw(surf, "O DADO DECIDE QUEM COMEÇA", p.centerx, p.y + 10, C["warn"], 1, "center")
    boxes = {"player": pygame.Rect(p.x + 20, p.y + 30, 120, 44),
             "enemy": pygame.Rect(p.right - 140, p.y + 30, 120, 44)}
    t = ctrl.dice_t
    rolling = t < 1.3
    winner = ctrl.first
    cur = ("player" if int(t * 10) % 2 == 0 else "enemy") if rolling else winner
    for side, b in boxes.items():
        lit = side == cur
        pygame.draw.rect(surf, (40, 110, 70) if side == "player" and lit else
                         (130, 50, 56) if lit else C["dark"], b)
        border(surf, b, (255, 255, 255) if lit else C["panel_edge"], 2 if lit else 1)
        font.draw(surf, "VOCÊ" if side == "player" else "INIMIGO", b.centerx, b.y + 15,
                  (255, 255, 255) if lit else C["dim"], 2, "center")
    if not rolling:
        txt = "VOCÊ COMEÇA!" if winner == "player" else "O INIMIGO COMEÇA!"
        font.draw(surf, txt, p.centerx, p.y + 84, (255, 255, 255), 1, "center")
        font.draw(surf, "Quem começa não ataca no 1º turno.", p.centerx, p.y + 98, C["dim"], 1, "center")
        font.draw(surf, "Clique ou ESPAÇO para jogar", p.centerx, p.y + 108, C["dim"], 1, "center")


def draw_final(surf: pygame.Surface, ctrl: Controller, ui: UIState) -> None:
    tint(surf, pygame.Rect(0, 0, W, H), (6, 8, 16), 170)
    p = L.final_panel()
    win = ctrl.duel.winner == "player"
    pygame.draw.rect(surf, C["panel"], p)
    border(surf, p, C["good"] if win else C["bad"], 3)
    font.draw(surf, "VITÓRIA!" if win else "DERROTA", p.centerx, p.y + 10,
              C["good"] if win else C["bad"], 3, "center")
    for k, ln in enumerate(ctrl.summary()):
        font.draw(surf, font.fit(ln, p.w - 16), p.centerx, p.y + 40 + k * 11, C["text"], 1, "center")
    if ctrl.final_line:                     # fala do inimigo-pessoa
        q = pygame.Rect(p.x + 10, p.y + 100, p.w - 20, 50)
        pygame.draw.rect(surf, C["dark"], q)
        border(surf, q, C["panel_edge"], 1)
        font.draw(surf, ctrl.enemy_name(), q.x + 5, q.y + 4, C["enemy"])
        for k, ln in enumerate(font.wrap('"' + ctrl.final_line + '"', q.w - 10)[:3]):
            font.draw(surf, ln, q.x + 5, q.y + 15 + k * 10, C["text"])
    if ctrl.run_mode:                       # dentro da run: so CONTINUAR
        from ui import layout_run as LR
        r = LR.continue_rect()
        hot = r.collidepoint(ui.mouse)
        pygame.draw.rect(surf, C["button_hot"] if hot else C["button"], r)
        border(surf, r, (255, 255, 255), 1)
        font.draw(surf, "CONTINUAR", r.centerx, r.y + 8, (255, 255, 255), 1, "center")
        boss = bool(ctrl.enemy and ctrl.enemy.get("tipo") == "chefe")
        nxt = ("Derrota: a run termina aqui." if not win else
               "Vitória sobre o chefe: a run termina." if boss else "Vitória: escolha uma carta.")
        font.draw(surf, nxt, p.centerx, p.bottom - 44, C["dim"], 1, "center")
        return
    for name, r in L.final_buttons().items():
        hot = r.collidepoint(ui.mouse)
        pygame.draw.rect(surf, C["button_hot"] if hot else C["button"], r)
        border(surf, r, (255, 255, 255), 1)
        txt = "JOGAR DE NOVO" if name == "again" else f"REPETIR SEED {ctrl.seed}"
        font.draw(surf, font.fit(txt, r.w - 6), r.centerx, r.y + 8, (255, 255, 255), 1, "center")
    font.draw(surf, "Enter: jogar de novo   R: repetir seed", p.centerx, p.bottom - 44, C["dim"], 1, "center")


# ------------------------------------------------------------------ quadro completo
def draw_frame(surf: pygame.Surface, ctrl: Controller, ui: UIState) -> None:
    surf.fill(C["bg"])
    sh = ctrl.shown
    can = ctrl.can_act()
    sel = ctrl.sel
    drop_slots: set[int] = set()
    if can and sel and sel[0] == "hand":
        drop_slots = ctrl.playable.get(sel[1], set())
    draw_leader(surf, ctrl, "enemy", ui)
    for side in ("enemy", "player"):
        for n in range(L.SLOTS):
            if T.side_view(sh, side).field[n] is None:
                ghost = ctrl.spirit_ghost() if side == "player" else None
                if ghost and ghost[0] == n:
                    draw_spirit_ghost(surf, ghost[1], L.slot_rect(side, n))
                    continue
                draw_empty_slot(surf, L.slot_rect(side, n), side == "player" and n in drop_slots, ui.t)
            else:
                draw_field_cat(surf, ctrl, side, n, ui)
    draw_leader(surf, ctrl, "player", ui)
    dragged = draw_hand(surf, ctrl, ui)
    draw_panel(surf, ctrl, ui)
    draw_bar(surf, ctrl, ui)
    draw_fx(surf, ctrl)
    # borda de hover
    n_hand = len(sh.me.hand)
    hover = L.hit_test(ui.mouse, n_hand, confirm=ctrl.confirming) if ctrl.phase == "play" else None
    if hover and hover[0] in ("hand", "slot") and not ui.drag:
        r = L.rect_of(hover, n_hand)
        if hover[0] == "hand" and ctrl.sel == hover:
            r = r.move(0, -5)
        border(surf, r, (255, 255, 255), 1)
    if ui.drag and dragged is not None and dragged < n_hand:
        card = sh.me.hand[dragged]
        r = pygame.Rect(0, 0, L.CARD_W, L.CARD_H)
        r.center = ui.drag[1]
        draw_card(surf, r, card, card.atk, card.hp, card.hp, card.keywords)
        border(surf, r, C["select"], 2)
    elif ui.drag and ui.drag[0][0] == "slot":
        pygame.draw.circle(surf, (255, 255, 255), ui.drag[1], 5, 2)
        a = pygame.Vector2(L.slot_rect("player", ui.drag[0][2]).center)
        pygame.draw.line(surf, (255, 255, 255), a, ui.drag[1], 2)
    draw_banner(surf, ctrl)
    if hover and not ui.drag and ctrl.phase == "play":
        draw_tooltip(surf, ctrl, hover)
    if ctrl.phase == "dice":
        draw_dice(surf, ctrl, ui)
    elif ctrl.final_visible:
        draw_final(surf, ctrl, ui)
