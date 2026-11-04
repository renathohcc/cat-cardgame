"""Painel "gatil cheio" da Adocao: escolher quem doar para abrir vaga, ou doar o gato novo."""
from __future__ import annotations

import pygame

from ui import font, layout_adopt as LA, sprites, widgets as Wd
from ui.adoption_controller import AdoptionController
from ui.render import UIState, mix_c
from ui.render_eco import coins_text
from ui.theme import C
from ui.widgets import WHITE, button

DANGER = (150, 60, 60)
DONATE = (120, 86, 28)


def _row(surf: pygame.Surface, ad: AdoptionController, cat, i: int, ui: UIState) -> None:
    r = LA.room_row(i)
    sel = ad.room_sel == cat.id
    fill = (46, 62, 90) if sel else C["slot"]
    if r.collidepoint(ui.mouse):
        fill = mix_c(fill, WHITE, 0.12)
    pygame.draw.rect(surf, fill, r, border_radius=4)
    pygame.draw.rect(surf, WHITE if sel else C["slot_edge"], r, 2 if sel else 1, border_radius=4)
    spr = sprites.get("cat", cat.breed, 24 if cat.stage == "kitten" else 32)
    if spr is not None:
        surf.blit(spr, spr.get_rect(center=(r.x + 22, r.centery)))
    label = cat.name or ad.breed_name(cat)
    font.draw(surf, font.fit(label, 150), r.x + 44, r.y + 5, C["text"], 1)
    sub = ad.breed_name(cat) if cat.name else ad.nature_name(cat)
    font.draw(surf, font.fit(sub + (" (filhote)" if cat.stage == "kitten" else ""), 150),
              r.x + 44, r.y + 22, Wd.breed_color(cat.breed) if cat.name else C["dim"], 1)
    Wd.stars(surf, r.x + 210, r.y + 8, cat.iv_atk, 1)
    Wd.stars(surf, r.x + 210, r.y + 24, cat.iv_hp, 1)
    coins_text(surf, r.right - 8, r.centery - font.CAP_H // 2, ad.value_of(cat), C["warn"], "right")


def draw_room(surf: pygame.Surface, ad: AdoptionController, ui: UIState) -> None:
    p = LA.room_panel()
    Wd.modal(surf, p, ad.room_title(), C["warn"])
    new = ad.room_new_cat()
    name = ad.breed_name(new) if new else "o gato novo"
    x, w = p.x + 24, p.w - 48
    font.draw(surf, ad.slots_text, p.right - 24, p.y + 56, C["bad"], 1, "right")
    Wd.wrap_lines(surf, f"Não há vaga para adotar {name}. Doe um gato da coleção para abrir espaço, "
                        f"ou doe o gato novo. Nada é perdido sozinho.", x, p.y + 56, w - 120, C["text"], 1, 3, 16)
    cats = ad.room_cats()
    font.draw(surf, f"DA SUA COLEÇÃO ({len(cats)} podem ser doados)", p.x + 44, p.y + 112, C["dim"], 1)
    vis = ad.room_visible()
    for i, c in enumerate(vis):
        _row(surf, ad, c, i, ui)
    if not cats:
        Wd.wrap_lines(surf, f"Nenhum gato da coleção pode ser doado agora: é preciso manter {ad.deck_size} adultos disponíveis "
                            "e fora do breed.", p.x + 52, p.y + 150, 420, C["warn"], 1, 4, 16)
    Wd.arrow(surf, LA.room_scroll_button(-1), True, ad.room_scroll > 0, ui.mouse)
    Wd.arrow(surf, LA.room_scroll_button(1), False, ad.room_scroll + LA.ROOM_ROWS < len(cats), ui.mouse)
    if new is not None:
        nx = p.x + 504
        font.draw(surf, "GATO NOVO", nx, p.y + 112, C["dim"], 1)
        spr = sprites.get("cat", new.breed, 32)
        if spr is not None:
            surf.blit(spr, spr.get_rect(center=(nx + 18, p.y + 150)))
        font.draw(surf, font.fit(name, 150), nx + 44, p.y + 134, Wd.breed_color(new.breed), 1)
        Wd.stars(surf, nx + 44, p.y + 154, new.iv_atk, 1)
        Wd.stars(surf, nx + 44 + 36, p.y + 154, new.iv_hp, 1)
        font.draw(surf, "ATK / HP", nx + 44 + 80, p.y + 152, C["dim"], 1)
    b = LA.room_buttons()
    sel = next((c for c in cats if c.id == ad.room_sel), None)
    button(surf, b["room_donate"], f"DOAR ESTE +{ad.value_of(sel)}" if sel else "ESCOLHA UM GATO", ui.mouse,
           enabled=sel is not None, base=DONATE)
    button(surf, b["room_donate_new"], f"DOAR O NOVO +{ad.value_of(new)}" if new else "DOAR O NOVO", ui.mouse,
           base=DANGER)
    button(surf, b["room_cancel"], "CANCELAR", ui.mouse, base=C["card"])
    if ad.room_msg:
        Wd.wrap_lines(surf, ad.room_msg, p.x + 504, p.y + 186, p.w - 524, C["warn"], 1, 2, 14)
    Wd.toast(surf, ad.toast, p.bottom + 4)
