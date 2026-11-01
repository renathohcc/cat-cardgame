"""Desenho do duelo em 960x540 (tabuleiro pintado + pecas de ui/skin.py, texto pela fonte bitmap).
Paleta em theme.py; nao tem regra de jogo. `scale` de fonte: 1 = corpo (maiusculas de 10 px), 2 = titulo."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import pygame

from core.types import Card, FieldCat
from ui import anim, icons, sprites, font, skin, layout as L, text as T, timing as timing_mod, tooltip as TIP
from ui.controller import Controller
from ui.theme import (
    ART_BG, BREED_COLOR, C, DEFAULT_BREED_COLOR, EFFECT_BADGE, H, KEYWORD_BADGE, KEYWORD_COLOR,
    NATURE_COLOR, W,
)

DARK = C["dark"]


@dataclass
class UIState:
    mouse: tuple[int, int] = (-100, -100)
    drag: tuple[tuple, tuple[int, int]] | None = None   # (elem origem, posicao)
    t: float = 0.0
    screen_shake: bool = True                  # tremor de tela (a tela de opcoes liga/desliga)
    hover_hand: int | None = None              # carta da mao em foco e desde quando (animacao)
    hover_since: float = 0.0
    # velocidade do turno inimigo: chave de enemy_speed.options (a tela de opcoes troca; os loops
    # copiam para `Controller.enemy_speed`)
    enemy_speed: str = field(default_factory=lambda: timing_mod.current().enemy_speed.default)


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


def stars_big(surf: pygame.Surface, x: int, y: int, n: int | None, k: int = 2) -> int:
    """5 estrelas de IV ampliadas k vezes (passo 6k px). Devolve a largura."""
    for i in range(5):
        on = n is not None and i < n
        img = star(C["star_on"] if on else C["star_off"])
        surf.blit(pygame.transform.scale(img, (5 * k, 5 * k)), (x + i * 6 * k, y))
    return 30 * k - k


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


# ------------------------------------------------------------------ texto adaptativo
def fit_scale(txt: str, max_w: int, top: int = 1) -> int:
    """Maior escala de fonte (top..1) em que `txt` cabe em max_w."""
    for sc in range(top, 1, -1):
        if font.width(txt, sc) <= max_w:
            return sc
    return 1


def text_fit(surf: pygame.Surface, txt: str, cx: int, y: int, color, max_w: int,
             align: str = "center", top: int = 1) -> None:
    """Texto na maior escala que cabe (se nem a 1 cabe, corta com '.'). `y` = topo das maiusculas."""
    sc = fit_scale(txt, max_w, top)
    font.draw(surf, font.fit(txt, max_w, sc), cx, y, color, sc, align)


def mix_c(a, b, k: float) -> tuple[int, int, int]:
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))  # type: ignore[return-value]


# ------------------------------------------------------------------ tabuleiro
_board: pygame.Surface | None = None


def board_surface() -> pygame.Surface:
    """Fundo do duelo: a arte pintada (assets/board/final/board_<tema>.png). Se faltar, um fundo
    simples de gradiente + faixas (fallback para testes headless e arte ausente)."""
    global _board
    if _board is None:
        art = skin.board()
        if art is not None and art.get_size() == (W, H):
            _board = art
            return _board
        b = pygame.Surface((W, H))
        top, bot = C["board_top"], C["board_bot"]
        for y in range(H):
            k = y / (H - 1)
            pygame.draw.line(b, tuple(int(top[i] + (bot[i] - top[i]) * k) for i in range(3)), (0, y), (W, y))
        for side in ("enemy", "player"):
            band = L.field_rect(side).inflate(24, 12)
            tint(b, band, (0, 0, 0), 55)
        tint(b, pygame.Rect(L.FIELD_X - 12, L.CENTER_Y, L.MAIN_W + 24, 1), (255, 255, 255), 16)
        tint(b, pygame.Rect(0, L.HAND_STRIP_Y, W, H - L.HAND_STRIP_Y), (0, 0, 0), 70)
        _board = b
    return _board


# ------------------------------------------------------------------ carta
_HEAD_COLOR = {"DANO": C["bad"], "CURA": C["good"], "ATK": C["buff"]}
ART = 96                      # janela de arte: sprite inteiro 96x96
BADGE = 22                    # caixa da badge (icone 18 + borda)


def head_color(head: str) -> tuple[int, int, int]:
    for key, col in _HEAD_COLOR.items():
        if key in head:
            return col
    return C["energy"]


def gem(surf: pygame.Surface, cx: int, cy: int, fill, txt: str, txt_col=(255, 255, 255),
        r: int = 13) -> None:
    """Emblema redondo (custo/ATK/HP) com contorno escuro, brilho e numero grande."""
    pygame.draw.circle(surf, DARK, (cx, cy), r + 1)
    pygame.draw.circle(surf, fill, (cx, cy), r)
    pygame.draw.circle(surf, tuple(min(255, c + 60) for c in fill), (cx - 4, cy - 5), 3)
    font.draw(surf, txt, cx, cy - font.CAP_H // 2, txt_col, 1, "center")


def diamond(surf: pygame.Surface, cx: int, cy: int, half: int, fill, edge=DARK) -> None:
    pts = [(cx, cy - half), (cx + half, cy), (cx, cy + half), (cx - half, cy)]
    pygame.draw.polygon(surf, fill, pts)
    pygame.draw.polygon(surf, edge, pts, 2)


Badge = tuple  # (nome do icone | None, cor, letra)


def badge(surf: pygame.Surface, x: int, y: int, item: Badge) -> None:
    icon, fill, letter = item
    box = pygame.Rect(x, y, BADGE, BADGE)
    pygame.draw.rect(surf, DARK, box, border_radius=4)
    spr = sprites.get("icon", icon) if icon else None
    if spr is not None:
        surf.blit(spr, spr.get_rect(center=box.center))
    else:                                    # sem icone: quadradinho colorido com a letra
        pygame.draw.rect(surf, fill, box.inflate(-4, -4), border_radius=3)
        font.draw(surf, letter, box.centerx, box.y + (BADGE - font.CAP_H) // 2, DARK, 1, "center")


def draw_badges(surf: pygame.Surface, r: pygame.Rect, items: list[Badge]) -> None:
    """Badges empilhadas na lateral direita da arte (no maximo 4)."""
    for i, it in enumerate(items[:4]):
        badge(surf, r.right - BADGE - 3, r.y + 4 + (BADGE + 2) * i, it)


def _placeholder_art(surf: pygame.Surface, r: pygame.Rect, kind: str, color) -> None:
    """Silhueta simples quando nao ha sprite (gato sem arte, Espirito, efeito)."""
    cx, cy = r.centerx, r.y + 52
    if kind == "effect":
        pts = [(cx, cy - 28), (cx + 8, cy - 8), (cx + 28, cy), (cx + 8, cy + 8),
               (cx, cy + 28), (cx - 8, cy + 8), (cx - 28, cy), (cx - 8, cy - 8)]
        pygame.draw.polygon(surf, color, pts)
    elif kind == "special":
        pygame.draw.circle(surf, color, (cx, cy - 8), 22)
        pygame.draw.rect(surf, color, (cx - 22, cy - 8, 46, 28))
        for k in range(3):
            pygame.draw.rect(surf, ART_BG["special"], (cx - 18 + k * 16, cy + 16, 8, 8))
        pygame.draw.rect(surf, DARK, (cx - 12, cy - 12, 6, 8))
        pygame.draw.rect(surf, DARK, (cx + 6, cy - 12, 6, 8))
    else:
        pygame.draw.circle(surf, color, (cx, cy + 4), 26)
        pygame.draw.polygon(surf, color, [(cx - 26, cy - 4), (cx - 24, cy - 28), (cx - 6, cy - 18)])
        pygame.draw.polygon(surf, color, [(cx + 26, cy - 4), (cx + 24, cy - 28), (cx + 6, cy - 18)])
        pygame.draw.rect(surf, DARK, (cx - 12, cy, 6, 6))
        pygame.draw.rect(surf, DARK, (cx + 6, cy, 6, 6))


def effect_badges(card: Card) -> list[Badge]:
    """Badges de efeito (um por tipo de acao, sem repetir)."""
    out: list[Badge] = []
    for act in card.actions:
        tipo = act.get("tipo")
        spec = EFFECT_BADGE.get(tipo)
        if spec:
            it = ("acao-" + tipo, spec[1], spec[0])
            if it not in out:
                out.append(it)
    return out


def keyword_badges(keywords: tuple[str, ...]) -> list[Badge]:
    return [(k, KEYWORD_COLOR.get(k, C["dim"]), KEYWORD_BADGE.get(k, k[:1].upper())) for k in keywords]


def _card_frame(surf: pygame.Surface, r: pygame.Rect, bg_key: str, body, band, name: str) -> pygame.Rect:
    """Fundo, janela de arte (96 de altura, sprite inteiro) e faixa do nome. Devolve a janela."""
    pygame.draw.rect(surf, body, r)
    art = pygame.Rect(r.x + 1, r.y + 1, r.w - 2, ART)
    pygame.draw.rect(surf, ART_BG[bg_key], art)
    strip = pygame.Rect(r.x + 1, r.y + 1 + ART, r.w - 2, r.h - 2 - ART)
    pygame.draw.rect(surf, band, strip)
    text_fit(surf, name, strip.centerx, strip.y + (strip.h - font.CAP_H * 2) // 2, DARK, strip.w - 8)
    return art


def _blit_art(surf: pygame.Surface, art: pygame.Rect, kind: str, name: str | None) -> bool:
    spr = sprites.get(kind, name)
    if spr is None:
        return False
    surf.blit(spr, (art.centerx - spr.get_width() // 2, art.y + (art.h - spr.get_height()) // 2))
    return True


def draw_effect_card(surf: pygame.Surface, r: pygame.Rect, card: Card, *, enemy: bool = False) -> None:
    art = _card_frame(surf, r, "effect", C["effect_bg"], C["effect"], card.name)
    if not _blit_art(surf, art, "effect", card.ref):
        _placeholder_art(surf, art, "effect", C["effect"])
    pr = pygame.Rect(0, 0, font.width("EFEITO", 1) + 12, font.CAP_H + 6)
    pr.midbottom = (art.centerx, art.bottom - 3)
    pill(surf, pr, 190)
    font.draw(surf, "EFEITO", pr.centerx, pr.y + 3, C["effect"], 1, "center")
    draw_badges(surf, art, effect_badges(card))
    gem(surf, r.x + 16, r.y + 16, C["cost"], str(card.cost))
    border(surf, r, C["effect"], 1)


def draw_card(surf: pygame.Surface, r: pygame.Rect, card: Card, atk: int, hp: int, hp_max: int,
              keywords: tuple[str, ...], *, enemy: bool = False, show_max: bool = True,
              atk_bonus: int = 0) -> None:
    """Carta limpa: arte 96x96 inteira, faixa do nome, gemas de custo/ATK/HP e badges de keyword.
    O resto (natureza, sexo, IV, textos) fica no tooltip."""
    if card.kind == "effect":
        draw_effect_card(surf, r, card, enemy=enemy)
        return
    special = card.kind == "special"
    body = C["special_bg"] if special else (C["card_enemy"] if enemy else C["card"])
    band = C["special"] if special else BREED_COLOR.get(card.breed or "", DEFAULT_BREED_COLOR)
    bg_key = "special" if special else ("enemy" if enemy else "card")
    art = _card_frame(surf, r, bg_key, body, band, T.label(card))
    if not _blit_art(surf, art, "special" if special else "cat", card.ref if special else card.breed):
        _placeholder_art(surf, art, "special" if special else "cat", band)
    badges = keyword_badges(keywords)
    if special and card.actions:
        badges = effect_badges(card)[:1] + badges
    draw_badges(surf, art, badges)
    gem(surf, r.x + 16, r.y + 16, C["cost"], str(card.cost))
    ay = art.bottom - 15
    if atk_bonus > 0:                # buff temporario de ATK: destaque dourado + seta
        gem(surf, r.x + 16, ay, C["buff"], str(atk), DARK)
        for k in range(4):
            pygame.draw.line(surf, C["buff"], (r.x + 16 - k * 2, ay - 18 - k * 2),
                             (r.x + 16 + k * 2, ay - 18 - k * 2), 2)
    else:
        gem(surf, r.x + 16, ay, C["atk"], str(atk))
    hurt = hp < hp_max
    gem(surf, r.right - 17, ay, (170, 120, 40) if hurt else C["hp"], str(hp),
        (255, 230, 120) if hurt else (255, 255, 255))
    border(surf, r, C["special"] if special else C["card_edge"], 1)


# ------------------------------------------------------------------ campo
def draw_drop_slot(surf: pygame.Surface, r: pygame.Rect, t: float) -> None:
    """Slot vazio jogavel: so um realce sutil (o campo vazio nao tem moldura)."""
    tint(surf, r, C["drop"], 40 + int(50 * pulse(t)))
    border(surf, r, C["drop"], 2)
    font.draw(surf, "JOGAR", r.centerx, r.centery - font.CAP_H // 2, (255, 255, 255), 1, "center")


def draw_empty_slot(surf: pygame.Surface, r: pygame.Rect, drop: bool, t: float) -> None:
    if drop:
        draw_drop_slot(surf, r, t)


def _state_pill(surf: pygame.Surface, r: pygame.Rect, txt: str, col, h: int = 22) -> None:
    sc = 1
    pr = pygame.Rect(0, 0, min(r.w - 4, font.width(txt, sc) + 12), h)
    pr.center = (r.centerx, r.y + 48)
    pill(surf, pr, 225)
    font.draw(surf, font.fit(txt, pr.w - 8, sc), pr.centerx, pr.y + (h - font.CAP_H * sc) // 2, col, sc, "center")


def _previewed(ctrl: Controller, ui: UIState, side: str, target: tuple) -> bool:
    """O mouse esta neste alvo e a previa dele esta na tela."""
    from ui import preview
    return (preview.hovered(ctrl, ui.mouse) == (side, target)
            and preview.current(ctrl, ui.mouse) is not None)


def draw_field_cat(surf: pygame.Surface, ctrl: Controller, side: str, n: int, ui: UIState,
                   off: tuple[int, int] = (0, 0)) -> None:
    """`off` = deslocamento da respiracao/investida (so o desenho; o clique usa o slot)."""
    sv = T.side_view(ctrl.shown, side)
    fc: FieldCat = sv.field[n]
    r = L.slot_rect(side, n).move(off)
    draw_card(surf, r, fc.card, fc.atk, fc.hp, fc.hp_max, fc.keywords, enemy=side == "enemy",
              atk_bonus=fc.atk_bonus_turn)
    status, _ = ctrl.cat_status(side, fc)
    if status in ("spent", "new", "wait"):
        tint(surf, r, DARK, 130)
        _state_pill(surf, r, {"spent": "JÁ ATACOU", "new": "ENTROU", "wait": "AGUARDA"}[status], C["dim"])
    if "provocar" in fc.keywords:
        border(surf, r, C["taunt"], 2)
    if status == "ready" and side == "player":
        border(surf, r.inflate(4, 4), C["ready"], 2)
        border(surf, r.inflate(8, 8), C["ready"] if pulse(ui.t) > 0.5 else (60, 150, 80), 1)
    if ctrl.sel == ("slot", n) and side == "player":
        border(surf, r.inflate(8, 8), C["select"], 3)
    label = ctrl.slot_target(side, n)
    if label:
        col = C["target"] if side == "enemy" else C["drop"]
        tint(surf, r, col, 50 + int(60 * pulse(ui.t)))
        border(surf, r.inflate(8, 8), col, 3)
        if not _previewed(ctrl, ui, side, ("slot", n)):     # a previa ocupa o lugar do rotulo
            _state_pill(surf, r, label, (255, 255, 255), 26)
    blocked = ctrl.target_blocked(side, n)
    if blocked:                                  # nao e alvo valido: apagado (escudo se Provocar)
        from ui import render_preview
        render_preview.draw_blocked_cat(surf, ctrl, side, n, blocked)


def draw_spirit_ghost(surf: pygame.Surface, card: Card, r: pygame.Rect) -> None:
    """Espirito posicionado, esperando o alvo do "ao entrar"."""
    draw_card(surf, r, card, card.atk, card.hp, card.hp, card.keywords)
    border(surf, r.inflate(8, 8), C["select"], 3)
    pr = pygame.Rect(r.x + 6, r.y + 32, r.w - 12, 38)
    pill(surf, pr, 235)
    font.draw(surf, "ESCOLHA", r.centerx, pr.y + 5, (255, 255, 255), 1, "center")
    font.draw(surf, "O ALVO", r.centerx, pr.y + 22, C["warn"], 1, "center")


def hp_color(hp: int, mx: int) -> tuple[int, int, int]:
    f = hp / mx if mx else 0
    if f > 0.5:
        return (40, 130, 78)
    if f > 0.25:
        return (160, 126, 30)
    return (160, 44, 44)


_TIPO_TAG = {"elite": "ELITE", "chefe": "CHEFE"}


def _leader_id(ctrl: Controller, side: str) -> str:
    return (ctrl.enemy_id or "inimigo") if side == "enemy" else "heroi"


def draw_leader_portrait(surf: pygame.Surface, ctrl: Controller, side: str, r: pygame.Rect) -> None:
    """Retrato do Lider no medalhao pintado: sprite 128 reduzido 2:1 (64x64) e recortado em 64x56.
    Sem sprite: inicial grande sobre fundo da cor do lado."""
    accent = C["enemy"] if side == "enemy" else C["player"]
    pygame.draw.rect(surf, mix_c(accent, DARK, 0.62), r)
    spr = sprites.get("leader128", _leader_id(ctrl, side), 64)
    if spr is not None:
        old = surf.get_clip()
        surf.set_clip(r)
        surf.blit(spr, (r.x + (r.w - spr.get_width()) // 2, r.y - 4))
        surf.set_clip(old)
    else:
        person = ctrl.enemy if side == "enemy" else None
        ini = (person["nome"][:1] if person else ("I" if side == "enemy" else "V")).upper()
        font.draw(surf, ini, r.centerx, r.centery - font.CAP_H, (255, 255, 255), 2, "center")
    pygame.draw.rect(surf, accent, r.inflate(2, 2), 1)


def draw_taunt_mark(surf: pygame.Surface, ctrl: Controller, side: str) -> None:
    """Escudo de Provocar ao lado da placa: o Lider esta protegido por um gato com Provocar."""
    sv = T.side_view(ctrl.shown, side)
    if not any(fc is not None and "provocar" in fc.keywords for fc in sv.field):
        return
    r = L.leader_taunt_rect(side)
    pill(surf, r, 200)
    border(surf, r, C["taunt"], 2)
    ico = sprites.get("icon", "provocar")
    if ico is not None:
        ico = pygame.transform.scale(ico, (ico.get_width() * 2, ico.get_height() * 2))
        surf.blit(ico, (r.x + 5, r.centery - ico.get_height() // 2))
    font.draw(surf, "PROTEGIDO", r.x + 42, r.y + 6, C["taunt"], 1)
    font.draw(surf, "PROVOCAR", r.x + 42, r.y + 22, C["taunt"], 1)


def rule_icon(rule: dict) -> str | None:
    """Nome do icone da regra propria (do tipo da acao); None cai na letra do badge."""
    act = rule.get("acao", rule.get("acoes"))
    if isinstance(act, list):
        act = act[0] if act else None
    tipo = act.get("tipo") if isinstance(act, dict) else None
    return f"acao-{tipo}" if tipo else None


def draw_rule_badge(surf: pygame.Surface, rule: dict, ui: UIState) -> None:
    """Icone da regra propria ao lado do retrato do inimigo (o tooltip explica a regra)."""
    r = L.rule_rect()
    badge(surf, r.x, r.y, (rule_icon(rule), C["warn"], "R"))
    border(surf, r.inflate(2, 2), C["warn"] if pulse(ui.t, 3) > 0.5 else mix_c(C["warn"], DARK, 0.5), 1)


def draw_leader(surf: pygame.Surface, ctrl: Controller, side: str, ui: UIState) -> None:
    r = L.leader_rect(side)
    sv = T.side_view(ctrl.shown, side)
    name_r = L.leader_name_rect(side)
    draw_leader_portrait(surf, ctrl, side, r)
    draw_taunt_mark(surf, ctrl, side)
    if ctrl.leader_blocked(side):
        from ui import render_preview
        render_preview.draw_blocked_leader(surf, side)
    if side == "enemy" and sv.rule:
        draw_rule_badge(surf, sv.rule, ui)
    tgt = ctrl.leader_target(side)
    cat_sel = side == "enemy" and ctrl.sel and ctrl.sel[0] == "slot"
    person = ctrl.enemy if side == "enemy" else None
    if tgt:
        tint(surf, r, C["target"] if side == "enemy" else C["drop"], 90 + int(100 * pulse(ui.t)))
        border(surf, r.inflate(6, 6), (255, 255, 255), 3)
        outlined(surf, "ATACAR LÍDER" if tgt == "attack" else "ALVO DO EFEITO",
                 name_r.right, name_r.centery - font.CAP_H // 2, (255, 255, 255), 1, "right")
    else:
        title = (person["nome"] if person else
                 ("LÍDER INIMIGO" if side == "enemy" else "SEU LÍDER"))
        sub, sub_col = None, C["warn"]
        if cat_sel and (person is None or ctrl.taunt_in_way()):
            sub, sub_col = "PROTEGIDO POR PROVOCAR", C["taunt"]
        elif sv.rule:
            sub = "Regra: " + T.rule_name(sv.rule)
        tag = _TIPO_TAG.get(person.get("tipo", "")) if person else None
        if sub and sub.startswith("Regra: "):
            sub = sub[7:]
        rows = 1 + (1 if tag else 0) + (1 if sub else 0)
        y0 = name_r.y + (name_r.h - (rows * 16 - 4)) // 2
        shade = pygame.Rect(name_r.x + 4, y0 - 3, name_r.w - 4, rows * 16 + 2)
        pill(surf, shade, 120)
        text_fit(surf, title, name_r.right - 4, y0, (255, 255, 255), name_r.w - 6, "right")
        y = y0 + 16
        if tag:
            chip = pygame.Rect(0, 0, font.width(tag) + 12, font.CAP_H + 5)
            chip.topright = (name_r.right - 4, y - 2)
            pygame.draw.rect(surf, C["warn"], chip, border_radius=3)
            font.draw(surf, tag, chip.centerx, chip.y + 3, DARK, 1, "center")
            y += 16
        if sub:
            font.draw(surf, font.fit(sub, name_r.w - 16), name_r.right - 4, y, sub_col, 1, "right")
    hp = L.leader_hp_rect(side)                          # HP na gema pintada (40x40)
    low = bool(sv.leader_hp_max) and sv.leader_hp / sv.leader_hp_max <= 0.25
    if not skin.blit(surf, "hp_lider", hp.topleft):
        diamond(surf, hp.centerx, hp.centery, 19, C["gem_hp"])
    if low:
        tint(surf, hp.inflate(-8, -8), (255, 60, 40), 90)
    font.draw(surf, str(sv.leader_hp), hp.centerx, hp.centery - font.CAP_H // 2, (255, 255, 255), 1, "center")
    font.draw(surf, f"/{sv.leader_hp_max}", hp.right + 6, hp.centery - font.CAP_H // 2, C["dim"], 1, "left")


# ------------------------------------------------------------------ painel
def draw_panel_box(surf: pygame.Surface, r: pygame.Rect) -> None:
    tint(surf, r, (10, 12, 22), 170)
    border(surf, r, C["panel_edge"], 1)


def draw_panel(surf: pygame.Surface, ctrl: Controller, ui: UIState) -> None:
    sh = ctrl.shown
    r = L.turn_rect()                                   # indicador de turno (recorte pintado)
    mine = sh.turn_side == "player"
    tint(surf, r, (40, 110, 70) if mine else (130, 50, 56), 200)
    border(surf, r, (90, 200, 130) if mine else (220, 100, 106), 1)
    n = T.side_view(sh, sh.turn_side).turns_taken
    font.draw(surf, "SEU TURNO" if mine else "INIMIGO JOGA", r.centerx, r.y + 5, (255, 255, 255), 1, "center")
    font.draw(surf, f"Turno {n}", r.centerx, r.y + 23, (210, 230, 220), 1, "center")
    r = L.info_rect()                                   # energia do inimigo
    o = sh.opponent
    te = ctrl.turn_energy["enemy"]
    font.draw(surf, "INIMIGO", r.x + 8, r.y + 6, C["dim"])
    font.draw(surf, f"Energia {o.energy}/{te}" if te else "Energia -", r.x + 8, r.y + 27, C["enemy"], 1)
    draw_log(surf, ctrl)
    draw_pile(surf, L.enemy_pile_rect(), o.deck_count, o.hand_count, "enemy")
    draw_pile(surf, L.pile_rect(), sh.me.deck_count, sh.me.hand_count, "player")
    draw_pass_button(surf, ctrl, ui)


def draw_pile(surf: pygame.Surface, r: pygame.Rect, deck: int, hand: int, side: str, title: str = "") -> None:
    """Baralho (pilha de cartas viradas) com contador de cartas no deck e na mao, na moldura de baralho."""
    accent = C["enemy"] if side == "enemy" else C["player"]
    fr = pygame.Rect(r.x + 1, r.y + (r.h - 76) // 2, 152, 76)
    if not skin.nine(surf, "baralho_moldura", fr):
        tint(surf, fr, (10, 12, 22), 170)
        border(surf, fr, C["panel_edge"], 1)
    for k in (2, 1, 0):
        c = pygame.Rect(fr.x + 14 + k * 3, fr.y + 8 - k * 2 + (0 if deck else 3), 40, 54)
        pygame.draw.rect(surf, C["dark"], c.inflate(2, 2), border_radius=5)
        pygame.draw.rect(surf, mix_c(accent, DARK, 0.55 + 0.1 * k), c, border_radius=4)
        pygame.draw.rect(surf, accent, c, 1, border_radius=4)
    if not deck:
        tint(surf, pygame.Rect(fr.x + 14, fr.y + 8, 46, 58), DARK, 150)
    cx = fr.x + 106
    font.draw(surf, str(deck), cx, fr.y + 8, (255, 255, 255), 2, "center")
    font.draw(surf, "baralho", cx, fr.y + 32, C["dim"], 1, "center")
    font.draw(surf, f"MÃO {hand}", cx, fr.y + 48, accent, 1, "center")


_LOG_COLOR = {"player": C["player"], "enemy": (255, 160, 160), "warn": C["warn"],
              "good": C["good"], "bad": C["bad"]}
LOG_LINE = 14
LOG_ICON_W = 18                # icone 16x16 + folga antes do texto


def log_rows(ctrl: Controller, width: int, cap: int) -> list[tuple[str, tuple, str | None, bool]]:
    """Ultimas linhas do registro ja quebradas: (texto, cor, icone na 1a linha, recuado)."""
    rows: list[tuple[str, tuple, str | None, bool]] = []
    for entry in reversed(ctrl.log[-20:]):               # do mais novo para o mais antigo
        txt, side = entry
        icon = getattr(entry, "icon", None)
        col = _LOG_COLOR.get(side, C["text"])
        lines = font.wrap(txt, width - (LOG_ICON_W if icon else 0))
        if len(rows) + len(lines) > cap:
            break
        rows = [(ln if icon or k == 0 else " " + ln, col, icon if k == 0 else None, bool(icon))
                for k, ln in enumerate(lines)] + rows
    return rows


def draw_log(surf: pygame.Surface, ctrl: Controller) -> None:
    r = L.log_rect()
    font.draw(surf, "REGISTRO", r.x + 8, r.y + 6, C["dim"])
    cap = (r.h - 26) // LOG_LINE
    for k, (ln, col, icon, indent) in enumerate(log_rows(ctrl, r.w - 18, cap)):
        y = r.y + 24 + k * LOG_LINE
        ico = icons.get(icon) if icon else None
        if ico is not None:
            surf.blit(ico, (r.x + 6, y - 3))
        font.draw(surf, ln, r.x + 8 + (LOG_ICON_W if indent else 0), y, col)


def draw_pass_button(surf: pygame.Surface, ctrl: Controller, ui: UIState) -> None:
    r = L.pass_rect()
    active = ctrl.can_act()
    if active and ctrl.confirming:
        font.draw(surf, "HÁ JOGADAS", r.centerx, r.y - 16, C["warn"], 1, "center")
        for rect, txt, fill, hot_fill in (
                (L.pass_yes_rect(), "PASSAR", (150, 70, 40), (190, 100, 50)),
                (L.pass_no_rect(), "NÃO", C["button_off"], C["button"])):
            hot = rect.collidepoint(ui.mouse)
            pygame.draw.rect(surf, hot_fill if hot else fill, rect, border_radius=8)
            border(surf, rect, (255, 255, 255), 3 if hot else 2)
            font.draw(surf, txt, rect.centerx, rect.centery - font.CAP_H // 2, (255, 255, 255), 1, "center")
        return
    hot = active and r.collidepoint(ui.mouse)
    calm = ctrl.pass_only                                # so resta passar: o botao respira
    name = "botao_fim_turno_" + ("desabilitado" if not active else "hover" if hot else "normal")
    if not skin.nine(surf, name, r):
        fill = C["button_off"] if not active else C["button_hot"] if hot else C["button"]
        pygame.draw.rect(surf, fill, r, border_radius=10)
        border(surf, r, C["panel_edge"], 2)
    k = pulse(ui.t, 4.0) if calm else 0.0
    if calm:
        tint(surf, r.inflate(-6, -6), (255, 255, 255), int(10 + 38 * k))
        border(surf, r.inflate(2 + round(2 * k), 2 + round(2 * k)), mix_c(C["ready"], (255, 255, 255), k), 2)
    col = (255, 255, 255) if active else C["dim"]
    if not active:
        font.draw(surf, "AGUARDE", r.centerx, r.centery - font.CAP_H // 2 - 2, col, 1, "center")
    else:
        font.draw(surf, "FIM DE TURNO", r.centerx, r.centery - font.CAP_H // 2 - 4, col, 1, "center")
        sub, sub_col = ("SEM JOGADAS", C["ready"]) if calm else ("[E / ESPAÇO]", (200, 235, 210))
        font.draw(surf, sub, r.centerx, r.centery + 8, sub_col, 1, "center")


# ------------------------------------------------------------------ energia e mensagens
def gems_state(ctrl: Controller, en: int) -> tuple[int, int]:
    """(cristais acesos, indice do que acabou de mudar) com a animacao um a um da energia."""
    for f in reversed(ctrl.fx):
        if f.kind == "gems":
            a, b = f.data
            lit = anim.gems_lit(f.color, f.age, ctrl.timing.energy.gem_stagger, a, b)
            return lit, (lit - 1 if f.color == "on" else lit)
    return en, -1


def draw_bar(surf: pygame.Surface, ctrl: Controller, ui: UIState) -> None:
    r = L.energy_rect()
    sh = ctrl.shown
    cap = ctrl.energy_cap
    tot = ctrl.turn_energy["player"]
    en = sh.me.energy
    font.draw(surf, "ENERGIA", r.x + 10, r.y + 4, C["dim"])
    font.draw(surf, f"{en}/{tot}", r.right - 10, r.y + 4, (170, 210, 255), 1, "right")
    lit, popped = gems_state(ctrl, en)
    step = 25
    gx = r.x + (r.w - ((cap - 1) * step + 24)) // 2
    for i in range(cap):
        gem_r = pygame.Rect(gx + i * step, r.y + 22, 24, 24)
        if i < lit:
            name = "energia_cheia"
        else:
            name = "energia_vazia"
        if not skin.blit(surf, name, gem_r.topleft):
            cx, cy = gem_r.center
            if i < lit:
                diamond(surf, cx, cy, 9, C["gem_energy"], (30, 70, 120))
            else:
                pts = [(cx, cy - 9), (cx + 9, cy), (cx, cy + 9), (cx - 9, cy)]
                pygame.draw.polygon(surf, C["cost"] if i < tot else C["star_off"], pts, 2 if i < tot else 1)
        if en <= i >= tot:                      # alem do total deste turno: escurece
            tint(surf, gem_r, DARK, 120)
        if i == popped:
            tint(surf, gem_r, (255, 255, 255), 110)
    m = L.message_rect()
    txt = ctrl.hint()
    for k, ln in enumerate(font.wrap(txt, m.w - 14)[:2]):
        font.draw(surf, ln, m.x + 7, m.y + 6 + k * 15, C["dim"])


def draw_toast(surf: pygame.Surface, ctrl: Controller) -> None:
    """Aviso passageiro (erro/dica de jogada) na faixa entre os campos: uma linha, sem cortar."""
    t = ctrl.toast
    if t is None:
        return
    fill, col = {"error": ((100, 36, 40), (255, 190, 190)), "warn": ((110, 84, 20), (255, 230, 150)),
                 "info": ((36, 64, 100), (200, 225, 255))}[t.kind]
    txt = font.fit(t.text, L.MAIN_W - 40)
    r = L.toast_rect(font.width(txt) + 32)
    pygame.draw.rect(surf, fill, r, border_radius=6)
    pygame.draw.rect(surf, col, r, 2, border_radius=6)
    font.draw(surf, txt, r.centerx, r.centery - font.CAP_H // 2, col, 1, "center")


# ------------------------------------------------------------------ tooltip
def draw_tooltip(surf: pygame.Surface, ctrl: Controller, elem: tuple) -> None:
    """Desenha o tooltip (linhas e posicao vem de ui.tooltip, testavel sem janela)."""
    got = TIP.lines_for(ctrl, elem)
    if got is None:
        return
    out, side, anchor = got
    tr = TIP.place(elem[0], anchor, TIP.box_height(out))
    if not skin.nine(surf, "tooltip", tr):
        pygame.draw.rect(surf, (16, 18, 30), tr, border_radius=6)
        border(surf, tr, C["player"] if side == "player" else C["enemy"], 2)
    y = tr.y + TIP.PAD
    for k, segs in enumerate(out):
        x = tr.x + TIP.PAD
        if TIP.is_title(k, segs):                                     # titulo maior
            text_fit(surf, segs[0][0], x, y, segs[0][1], tr.w - 2 * TIP.PAD, "left", top=2)
            y += TIP.TITLE_H
            continue
        for seg in segs:
            if seg[0] == "*stars":
                x += stars_big(surf, x, y, seg[1], 2) + 6
            else:
                font.draw(surf, seg[0], x, y, seg[1])
                x += font.advance(seg[0])
        y += TIP.LINE_H


# ------------------------------------------------------------------ overlays
def draw_dice(surf: pygame.Surface, ctrl: Controller, ui: UIState) -> None:
    tint(surf, pygame.Rect(0, 0, W, H), (8, 10, 20), 215)
    p = pygame.Rect(W // 2 - 300, 130, 600, 280)
    pygame.draw.rect(surf, C["panel"], p, border_radius=10)
    border(surf, p, C["warn"], 3)
    font.draw(surf, "O DADO DECIDE QUEM COMEÇA", p.centerx, p.y + 20, C["warn"], 1, "center")
    boxes = {"player": pygame.Rect(p.x + 40, p.y + 56, 240, 88),
             "enemy": pygame.Rect(p.right - 280, p.y + 56, 240, 88)}
    t = ctrl.dice_t
    rolling = t < 1.3
    winner = ctrl.first
    cur = ("player" if int(t * 10) % 2 == 0 else "enemy") if rolling else winner
    for side, b in boxes.items():
        lit = side == cur
        pygame.draw.rect(surf, (40, 110, 70) if side == "player" and lit else
                         (130, 50, 56) if lit else C["dark"], b, border_radius=8)
        border(surf, b, (255, 255, 255) if lit else C["panel_edge"], 3 if lit else 2)
        font.draw(surf, "VOCÊ" if side == "player" else "INIMIGO", b.centerx, b.centery - font.CAP_H,
                  (255, 255, 255) if lit else C["dim"], 2, "center")
    if not rolling:
        txt = "VOCÊ COMEÇA!" if winner == "player" else "O INIMIGO COMEÇA!"
        font.draw(surf, txt, p.centerx, p.y + 164, (255, 255, 255), 2, "center")
        font.draw(surf, "Quem começa não ataca no primeiro turno.", p.centerx, p.y + 220, C["dim"], 1, "center")
        font.draw(surf, "Clique ou ESPAÇO para jogar", p.centerx, p.y + 244, C["dim"], 1, "center")


def draw_final(surf: pygame.Surface, ctrl: Controller, ui: UIState) -> None:
    tint(surf, pygame.Rect(0, 0, W, H), (6, 8, 16), 170)
    p = L.final_panel()
    win = ctrl.duel.winner == "player"
    pygame.draw.rect(surf, C["panel"], p, border_radius=10)
    border(surf, p, C["good"] if win else C["bad"], 4)
    font.draw(surf, "VITÓRIA!" if win else "DERROTA", p.centerx, p.y + 20,
              C["good"] if win else C["bad"], 3, "center")
    y = p.y + 72
    for ln in ctrl.summary():
        for sub in font.wrap(ln, p.w - 48):
            font.draw(surf, sub, p.centerx, y, C["text"], 1, "center")
            y += 16
    if ctrl.final_line:                     # fala do inimigo-pessoa
        q = pygame.Rect(p.x + 24, p.y + 232, p.w - 48, 90)
        pygame.draw.rect(surf, C["dark"], q, border_radius=6)
        border(surf, q, C["panel_edge"], 1)
        font.draw(surf, ctrl.enemy_name(), q.x + 10, q.y + 8, C["enemy"], 1)
        for k, ln in enumerate(font.wrap('"' + ctrl.final_line + '"', q.w - 20)[:5]):
            font.draw(surf, ln, q.x + 10, q.y + 26 + k * 13, C["text"])
    if ctrl.run_mode:                       # dentro da run: so CONTINUAR
        r = L.continue_rect()
        hot = r.collidepoint(ui.mouse)
        pygame.draw.rect(surf, C["button_hot"] if hot else C["button"], r, border_radius=8)
        border(surf, r, (255, 255, 255), 2)
        font.draw(surf, "CONTINUAR", r.centerx, r.centery - font.CAP_H // 2, (255, 255, 255), 1, "center")
        boss = bool(ctrl.enemy and ctrl.enemy.get("tipo") == "chefe")
        nxt = ("Derrota: a run termina aqui." if not win else
               "Vitória sobre o chefe: a run termina." if boss else "Vitória: escolha uma carta.")
        font.draw(surf, nxt, p.centerx, p.bottom - 90, C["dim"], 1, "center")
        return
    for name, r in L.final_buttons().items():
        hot = r.collidepoint(ui.mouse)
        pygame.draw.rect(surf, C["button_hot"] if hot else C["button"], r, border_radius=8)
        border(surf, r, (255, 255, 255), 2)
        txt = "JOGAR DE NOVO" if name == "again" else f"REPETIR SEED {ctrl.seed}"
        text_fit(surf, txt, r.centerx, r.centery - font.CAP_H // 2, (255, 255, 255), r.w - 12)
    font.draw(surf, "Enter: jogar de novo   R: repetir seed", p.centerx, p.bottom - 90, C["dim"], 1, "center")


# ------------------------------------------------------------------ quadro completo
def draw_frame(surf: pygame.Surface, ctrl: Controller, ui: UIState) -> None:
    """Quadro completo; com tremor de tela (e `ui.screen_shake` ligado) desloca tudo em px inteiros."""
    from ui import render_fx
    render_fx.shaken(surf, ctrl, ui.screen_shake, lambda target: _draw_scene(target, ctrl, ui))


def _draw_field(surf: pygame.Surface, ctrl: Controller, ui: UIState, drop_slots: set[int]) -> None:
    from ui import render_fx
    sh = ctrl.shown
    offs = render_fx.field_offsets(ctrl, ui)
    hidden = render_fx.hidden_slots(ctrl)
    lunge = render_fx.lunging(ctrl)
    for side in ("enemy", "player"):
        for n in range(L.SLOTS):
            if T.side_view(sh, side).field[n] is None:
                ghost = ctrl.spirit_ghost() if side == "player" else None
                if ghost and ghost[0] == n:
                    draw_spirit_ghost(surf, ghost[1], L.slot_rect(side, n))
                    continue
                draw_empty_slot(surf, L.slot_rect(side, n), side == "player" and n in drop_slots, ui.t)
            elif (side, n) not in hidden and (side, n) not in lunge:
                draw_field_cat(surf, ctrl, side, n, ui, offs.get((side, n), (0, 0)))
    draw_leader(surf, ctrl, "player", ui)
    for side, n in sorted(lunge):                       # o atacante passa por cima de tudo
        if (side, n) in offs and T.side_view(sh, side).field[n] is not None:
            draw_field_cat(surf, ctrl, side, n, ui, offs[(side, n)])


def _draw_scene(surf: pygame.Surface, ctrl: Controller, ui: UIState) -> None:
    from ui import render_fx, render_hand, render_preview
    surf.blit(board_surface(), (0, 0))
    sh = ctrl.shown
    can = ctrl.can_act()
    sel = ctrl.sel
    drop_slots: set[int] = set()
    if can and sel and sel[0] == "hand":
        drop_slots = ctrl.playable.get(sel[1], set())
    draw_panel(surf, ctrl, ui)
    draw_bar(surf, ctrl, ui)
    draw_leader(surf, ctrl, "enemy", ui)
    _draw_field(surf, ctrl, ui, drop_slots)
    n_hand = len(sh.me.hand)
    hover = TIP.hover_elem(ctrl, ui.mouse, bool(ui.drag))
    dragged = render_hand.draw_hand(surf, ctrl, ui, hover)
    render_fx.draw_fx(surf, ctrl)
    if hover and hover[0] == "slot":
        border(surf, L.rect_of(hover, n_hand), (255, 255, 255), 2)
    previewing = render_preview.draw_preview(surf, ctrl, ui)       # resultado antes de confirmar
    if ui.drag and dragged is not None and dragged < n_hand:
        card = sh.me.hand[dragged]
        r = pygame.Rect(0, 0, L.CARD_W, L.CARD_H)
        r.center = ui.drag[1]
        draw_card(surf, r, card, card.atk, card.hp, card.hp, card.keywords)
        border(surf, r, C["select"], 3)
    elif ui.drag and ui.drag[0][0] == "slot":
        pygame.draw.circle(surf, (255, 255, 255), ui.drag[1], 10, 3)
        a = pygame.Vector2(L.slot_rect("player", ui.drag[0][2]).center)
        pygame.draw.line(surf, (255, 255, 255), a, ui.drag[1], 4)
    draw_toast(surf, ctrl)
    render_fx.draw_banner(surf, ctrl)
    if hover and not previewing:
        draw_tooltip(surf, ctrl, hover)
    if ctrl.intro:
        render_fx.draw_boss_intro(surf, ctrl)
    elif ctrl.phase == "dice":
        draw_dice(surf, ctrl, ui)
    elif ctrl.final_visible:
        draw_final(surf, ctrl, ui)
