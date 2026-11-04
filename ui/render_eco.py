"""Pecas de desenho da economia (10a): moeda, Prestigio, loja, painel da area, selo e barra de meta.

So desenho; o estado vem de `ShopController`/`HubController`. Icones 16x16 de `ui.lock_art`.
Todas as duracoes vem de `ui.timing` (`economy.*`).
"""
from __future__ import annotations

import pygame

from ui import font, layout_shop as LS, lock_art, timing as timing_mod, widgets as Wd
from ui.render import mix_c, pulse, text_fit
from ui.shop_controller import TAB_NAME, AreaRow, DecoRow, RationRow, ShopController, milestone_text
from ui.theme import C, H, W
from ui.widgets import WHITE, button, panel

GOOD_BTN = (46, 120, 80)
RATION_ICON = {"racao-fofa": "racao_fofa", "racao-veloz": "racao_veloz", "racao-escolha": "racao_escolha"}


def eco() -> object:
    return timing_mod.current().economy


def icon(surf: pygame.Surface, name: str, x: int, y: int, scale: int = 1) -> None:
    img = lock_art.art().icon(name)
    if scale != 1:
        img = pygame.transform.scale(img, (img.get_width() * scale, img.get_height() * scale))
    surf.blit(img, (x, y))


def icon_text(surf: pygame.Surface, name: str, x: int, y: int, text: str, color=None, scale: int = 1) -> int:
    """Icone 16x16 + texto alinhado ao meio. Devolve o x logo depois."""
    icon(surf, name, x, y + font.CAP_H * scale // 2 - 8)
    w = font.draw(surf, text, x + 19, y, color or C["text"], scale)
    return x + 19 + w


def coins_text(surf: pygame.Surface, x: int, y: int, n: int, color=None, align: str = "left") -> None:
    txt = str(n)
    w = 19 + font.width(txt, 1)
    x0 = x - w if align == "right" else x
    icon_text(surf, "moeda", x0, y, txt, color or C["warn"])


def faltam(n: int) -> str:
    return "Falta 1 moeda" if n == 1 else f"Faltam {n} moedas"


# ------------------------------------------------------------------ Prestigio
def prestige_bar(surf: pygame.Surface, r: pygame.Rect, level: int, info, show_text: bool = True) -> None:
    """"PRESTIGIO n" + barra ate o proximo marco (do core: `prestige_info`)."""
    icon(surf, "prestigio", r.x, r.y - 3)
    font.draw(surf, f"PRESTÍGIO {level}", r.x + 19, r.y, C["effect"], 1)
    bar = pygame.Rect(r.x, r.y + 18, r.w, 8)
    pygame.draw.rect(surf, C["dark"], bar, border_radius=3)
    if info.next_level is None:
        frac, note = 1.0, "Nível máximo"
    elif info.locked:
        frac, note = 0.0, f"Nível {info.next_level}: travado por enquanto"
    else:
        cur, tgt = info.current or 0, info.target or 1
        frac = max(0.0, min(1.0, cur / tgt))
        note = f"Nível {info.next_level}: {milestone_text(info.milestone)} ({cur}/{tgt})"
    if frac > 0:
        pygame.draw.rect(surf, C["effect"], (bar.x, bar.y, max(3, round(bar.w * frac)), bar.h), border_radius=3)
    pygame.draw.rect(surf, C["panel_edge"], bar, 1, border_radius=3)
    if show_text:
        Wd.wrap_lines(surf, note, r.x, r.y + 30, r.w, C["dim"], 1, 2, 13)


# ------------------------------------------------------------------ cabecalho da loja
def _header(surf: pygame.Surface, sc: ShopController) -> None:
    Wd.title(surf, "LOJA DO CRIATÓRIO", 24, 16, C["warn"], 2)
    r = LS.header_stats()
    coins_text(surf, r.right, r.y + 4, sc.coins, align="right")
    info = sc.stats()["info"]
    prestige_bar(surf, pygame.Rect(r.x + 60, r.y + 28, r.w - 60, 30), sc.level(), info, show_text=False)
    if info.next_level is not None:
        note = "travado por enquanto" if info.locked else milestone_text(info.milestone)
        text_fit(surf, f"Próximo: {note}", r.right, r.y + 58, C["dim"], r.w, "right")


def _tabs(surf: pygame.Surface, sc: ShopController, ui) -> None:
    for i, t in enumerate(LS.TABS):
        r = LS.tab_rect(i)
        on = sc.tab == t
        button(surf, r, TAB_NAME[t], ui.mouse, base=C["button"] if on else C["card"],
               edge=WHITE if on else C["panel_edge"])


# ------------------------------------------------------------------ abas
def _state_color(ok: bool) -> tuple:
    return C["good"] if ok else C["bad"]


def _area_row(surf: pygame.Surface, row: AreaRow, i: int, ui) -> None:
    r = LS.area_row(i)
    fill = (40, 72, 60) if row.done else C["slot"]
    if r.collidepoint(ui.mouse) and not row.done:
        fill = mix_c(fill, WHITE, 0.1)
    pygame.draw.rect(surf, fill, r, border_radius=4)
    pygame.draw.rect(surf, C["good"] if row.done else (WHITE if row.can_buy else C["slot_edge"]), r, 1, border_radius=4)
    font.draw(surf, f"{i + 1}", r.x + 14, r.centery - font.CAP_H // 2, C["dim"], 1)
    text_fit(surf, row.name, r.x + 36, r.y + 6, C["text"] if not row.done else C["good"], 300, "left")
    chips = [f"+{row.slots_bonus} vagas"] + row.effects
    font.draw(surf, font.fit(" · ".join(chips), 420), r.x + 36, r.y + 28, C["dim"], 1)
    x = r.x + 470
    if not row.done:
        x = icon_text(surf, "moeda", x, r.y + 8, str(row.price), C["warn"] if row.missing_coins == 0 else C["bad"])
        icon_text(surf, "prestigio", r.x + 470, r.y + 28, f"Prestígio {row.prestige}",
                  C["effect"] if row.missing_prestige == 0 else C["bad"])
        font.draw(surf, font.fit(row.short(), 136), r.x + 600, r.y + 18, C["bad"] if row.reason() else C["good"], 1)
    b = LS.area_button(i)
    button(surf, b, "VER NO QUINTAL" if not row.done else "COMPRADA", ui.mouse, enabled=not row.done,
           base=GOOD_BTN if row.can_buy else C["card"])


def _ration_card(surf: pygame.Surface, row: RationRow, i: int, ui) -> None:
    r = LS.ration_card(i)
    panel(surf, r, WHITE if row.can_buy else None)
    icon(surf, RATION_ICON.get(row.id, "racao_fofa"), r.x + 14, r.y + 14, 3)
    font.draw(surf, font.fit(row.name, r.w - 90), r.x + 76, r.y + 24, C["warn"], 1)
    y = r.y + 70
    y = Wd.wrap_lines(surf, row.description, r.x + 14, y, r.w - 28, C["text"], 1, 3, 15) + 8
    icon_text(surf, "moeda", r.x + 14, y, f"Preço {row.price}", C["warn"])
    y += 24
    icon_text(surf, "prestigio", r.x + 14, y, f"Exige Prestígio {row.prestige}", C["effect"] if row.prestige_ok else C["bad"])
    y += 24
    font.draw(surf, f"Em estoque: {row.stock}", r.x + 14, y, C["good"] if row.stock else C["dim"], 1)
    y += 22
    if row.reason():
        Wd.wrap_lines(surf, row.reason(), r.x + 14, y, r.w - 28, C["bad"], 1, 2, 14)
    button(surf, LS.ration_button(i), row.button(), ui.mouse, enabled=row.can_buy, base=GOOD_BTN)


def _deco_card(surf: pygame.Surface, row: DecoRow, i: int, ui) -> None:
    r = LS.deco_card(i)
    owned = row.state == "owned"
    pygame.draw.rect(surf, (40, 72, 60) if owned else C["slot"], r, border_radius=4)
    pygame.draw.rect(surf, C["good"] if owned else (WHITE if row.can_buy else C["slot_edge"]), r, 1, border_radius=4)
    icon(surf, "decoracao_vaso" if i % 2 == 0 else "decoracao_pincel", r.x + 10, r.centery - 16, 2)
    tw = LS.deco_button(i).x - r.x - 62
    font.draw(surf, font.fit(row.name, tw), r.x + 54, r.y + 6, C["text"], 1)
    font.draw(surf, font.fit(row.description, tw), r.x + 54, r.y + 22, C["dim"], 1)
    x = icon_text(surf, "moeda", r.x + 54, r.y + 40, str(row.price), C["warn"])
    hint = row.reason() or f"Área: {row.area_name}"
    font.draw(surf, font.fit(hint, r.x + tw + 54 - x - 12), x + 12, r.y + 40, C["bad"] if row.reason() else C["dim"], 1)
    button(surf, LS.deco_button(i), row.button(), ui.mouse, enabled=row.can_buy, base=GOOD_BTN)


def draw_shop(surf: pygame.Surface, sc: ShopController, ui) -> None:
    _header(surf, sc)
    _tabs(surf, sc, ui)
    if sc.tab == "areas":
        for i, row in enumerate(sc.areas()):
            _area_row(surf, row, i, ui)
        font.draw(surf, "As áreas são compradas na placa, no quintal. Escolha uma para ir até lá.",
                  24, LS.area_row(6).y + 4, C["dim"], 1)
    elif sc.tab == "racoes":
        for i, row in enumerate(sc.rations()):
            _ration_card(surf, row, i, ui)
        font.draw(surf, f"{Wd.RATION_RULE.capitalize()}, escolhida na tela do BREED.", 24, LS.ration_card(0).bottom + 12, C["dim"], 1)
    else:
        for i, row in enumerate(sc.decorations()):
            _deco_card(surf, row, i, ui)
    button(surf, LS.back_button(), "VOLTAR (ESC)", ui.mouse, base=C["card"])
    Wd.toast(surf, sc.toast)


# ------------------------------------------------------------------ painel de compra da area
def draw_area_panel(surf: pygame.Surface, sc: ShopController, area_id: str, ui) -> None:
    row = sc.area(area_id)
    if row is None:
        return
    p = LS.area_panel()
    Wd.modal(surf, p, row.name.upper())
    x, w = p.x + 24, p.w - 48
    y = Wd.wrap_lines(surf, row.description, x, p.y + 56, w, C["text"], 1, 3, 16) + 6
    font.draw(surf, "O QUE ABRE", x, y, C["dim"], 1)
    y += 18
    for line in [f"+{row.slots_bonus} vagas no gatil"] + row.effects:
        font.draw(surf, "+ " + line, x + 4, y, C["good"], 1)
        y += 17
    y += 8
    icon_text(surf, "moeda", x, y, f"Preço: {row.price}", C["warn"])
    icon_text(surf, "moeda", x + w // 2, y, f"Seu saldo: {sc.coins}", C["good"] if sc.coins >= row.price else C["bad"])
    y += 24
    ok_p = row.missing_prestige == 0
    icon_text(surf, "prestigio" if ok_p else "cadeado", x, y, f"Exige Prestígio {row.prestige}",
              C["effect"] if ok_p else C["bad"])
    icon_text(surf, "prestigio", x + w // 2, y, f"Seu Prestígio: {sc.level()}", C["effect"])
    y += 26
    if row.reason():
        Wd.wrap_lines(surf, row.reason(), x, y, w, C["bad"], 1, 2, 15)
    elif row.can_buy:
        font.draw(surf, "Pode comprar agora!", x, y, C["good"], 1)
    b = LS.area_panel_buttons()
    button(surf, b["area_buy"], "COMPRAR" if row.can_buy else (row.reason() or "COMPRADA"), ui.mouse,
           enabled=row.can_buy, base=GOOD_BTN, scale=2)
    button(surf, b["area_close"], "FECHAR", ui.mouse, base=C["card"])
    Wd.toast(surf, sc.toast)


# ------------------------------------------------------------------ selo de Prestigio
def draw_seal(surf: pygame.Surface, level: int, age: float) -> None:
    """Selo no topo da tela quando o nivel sobe: pop de escala, segura e some."""
    e = eco()
    total, pop = e.seal_time, e.seal_pop
    if age >= total:
        return
    k = min(1.0, age / pop)
    scale = 1.0 + 0.5 * (1.0 - k) ** 2
    fade = max(1e-6, e.seal_fade)
    alpha = 255 if age < total - fade else int(255 * max(0.0, (total - age) / fade))
    box = pygame.Surface((300, 92), pygame.SRCALPHA)
    pygame.draw.rect(box, (14, 16, 26, 235), box.get_rect(), border_radius=8)
    pygame.draw.rect(box, mix_c(C["effect"], WHITE, 0.4 * pulse(age, 5.0)), box.get_rect(), 3, border_radius=8)
    ico = pygame.transform.scale(lock_art.art().icon("prestigio"), (48, 48))
    box.blit(ico, (16, 22))
    font.draw(box, "PRESTÍGIO SUBIU!", 80, 20, C["warn"], 1)
    font.draw(box, f"Nível {level}", 80, 42, C["effect"], 2)
    box.set_alpha(alpha)
    if scale != 1.0:
        box = pygame.transform.scale(box, (round(300 * scale), round(92 * scale)))
        box.set_alpha(alpha)
    surf.blit(box, box.get_rect(midbottom=(W // 2, H - 6)))


# ------------------------------------------------------------------ barra de proxima meta
def draw_goal_bar(surf: pygame.Surface, r: pygame.Rect, goal: dict | None, coins: int, age: float = 99.0) -> None:
    """"Faltam X moedas para [item]": o item acessivel mais barato ainda nao comprado (core: next_goal)."""
    panel(surf, r)
    font.draw(surf, "PRÓXIMA META", r.x + 12, r.y + 6, C["dim"], 1)
    if goal is None:
        font.draw(surf, "Tudo comprado por enquanto!", r.centerx, r.y + 30, C["good"], 1, "center")
        return
    miss, price = goal["missing"], goal["price"]
    line = (f"Você já pode comprar: {goal['name']}!" if miss == 0
            else f"{faltam(miss)} para {goal['name']}")
    col = C["good"] if miss == 0 else C["text"]
    lines = font.wrap(line, r.w - 24)
    if len(lines) > 2:                                   # nunca corta o nome do item: tudo em no maximo 2 linhas
        lines = [lines[0], " ".join(lines[1:])]
    for k, ln in enumerate(lines):
        font.draw(surf, ln, r.centerx, r.y + (22 if len(lines) > 1 else 26) + k * 11, col, 1, "center")
    bar = pygame.Rect(r.x + 14, r.y + 52, r.w - 28, 14)
    pygame.draw.rect(surf, C["dark"], bar, border_radius=4)
    frac = min(1.0, coins / price) if price else 1.0
    fill_t = max(1e-6, eco().goal_fill)
    frac *= min(1.0, age / fill_t)
    if frac > 0:
        pygame.draw.rect(surf, C["good"] if miss == 0 else C["warn"], (bar.x, bar.y, max(4, round(bar.w * frac)), bar.h),
                         border_radius=4)
    pygame.draw.rect(surf, C["panel_edge"], bar, 1, border_radius=4)
    font.draw(surf, f"{coins}/{price}", bar.centerx, bar.y + 2, WHITE, 1, "center")
