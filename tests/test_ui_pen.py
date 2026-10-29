"""Testes basicos do Criatorio animado (T9.1): loader de arte, maquina de estados e fluxo do hub."""
from __future__ import annotations

import json
import os
from random import Random

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
import pytest

from ui import layout_pen as LP
from ui.pen_controller import PenController, PenEntry
from ui.pen_geometry import PenGeometry, load_geometry, parse_geometry
from ui.pen_sprites import PenArt
from ui.render import UIState
from ui.render_hub import draw_hub_frame
from ui.scenes_hub import PEN_SCENES, make


def entries(n: int, tag: str = "livre") -> list[PenEntry]:
    return [PenEntry(f"c{i:03d}", "siames", False, tag) for i in range(n)]


def test_loader_com_spritesheet_sintetico(tmp_path):
    pygame.init()
    sheet = pygame.Surface((128, 64), pygame.SRCALPHA)
    sheet.fill((0, 0, 0, 0))
    sheet.fill((255, 0, 0, 255), pygame.Rect(0, 0, 64, 64))         # idle f0 = vermelho
    sheet.fill((0, 255, 0, 255), pygame.Rect(64, 0, 64, 64))        # idle f1 = verde
    pygame.image.save(sheet, str(tmp_path / "cats_pen.png"))
    (tmp_path / "cats_pen.json").write_text(json.dumps({
        "image": "cats_pen.png", "size": [128, 64], "frame": [64, 64],
        "anims": {"siames": {"idle": {"row": 0, "frames": 2, "fps": 2}}}}), encoding="utf-8")
    art = PenArt(tmp_path)
    assert art.has_art("siames") and not art.has_art("persa") and not art.has_art("siames", True)
    assert art.frame("siames", False, "idle", 0.0).get_at((5, 5))[:3] == (255, 0, 0)
    assert art.frame("siames", False, "idle", 0.5).get_at((5, 5))[:3] == (0, 255, 0)
    assert art.frame("siames", False, "walk", 0.0).get_at((5, 5))[:3] == (255, 0, 0)    # cai no idle
    assert art.frame("siames", False, "idle", 0.0, flip=True).get_size() == (64, 64)
    assert art.frame("persa", False, "walk", 0.1).get_size() == (64, 64)               # fallback


def test_loader_sem_arte_usa_fallback(tmp_path):
    pygame.init()
    art = PenArt(tmp_path)
    assert art.sheet is None and art.bg is None and art.fx("heart") is None
    for anim in ("idle", "walk", "sleep", "play"):
        assert art.frame("siames", False, anim, 0.3).get_size() == (64, 64)
        assert art.frame("raca-que-nao-existe", True, anim, 0.3).get_size() == (64, 64)
    assert art.geo.walk_area == (48, 96, 664, 372)


def test_geometria_json_invalido_cai_no_padrao():
    assert parse_geometry({"walk_area": "x"}).walk_area == (48, 96, 664, 372)
    g = parse_geometry({"zones": {"breed": {"rect": [1, 2, 30, 40]}}})
    assert g.zones["breed"].rect == (1, 2, 30, 40)
    assert g.zones["adultos"].rect == (48, 96, 440, 372) and g.zones["adultos"].objects == []
    assert load_geometry().panel == (736, 16, 208, 508)


def test_maximo_16_e_prioridade_breed_filhote_deck():
    pen = PenController(Random(1), PenGeometry(), 16)
    es = [PenEntry(f"k{i}", "persa", True, "filhote") for i in range(2)] + \
         [PenEntry(f"b{i}", "persa", False, "breed", f"b{i ^ 1}") for i in range(4)] + \
         [PenEntry(f"d{i}", "siames", False, "deck") for i in range(12)] + \
         [PenEntry(f"l{i}", "siames", False, "livre") for i in range(6)]
    pen.sync(es)
    ids = {c.cat_id for c in pen.cats}
    assert len(ids) == 16
    assert {"k0", "k1", "b0", "b1", "b2", "b3"} <= ids
    assert not any(i.startswith("l") for i in ids)


def test_rotacao_a_cada_60s_deterministica_por_seed():
    def corre(seed: int) -> list[str]:
        pen = PenController(Random(seed), PenGeometry(), 16)
        pen.sync(entries(30))
        a = list(pen.shown)
        pen.advance(61)
        assert pen.shown != a and len(pen.shown) == 10     # adultos: ate 10 por zona
        return pen.shown
    assert corre(5) == corre(5)


def test_gatos_ficam_na_area_sem_se_empilhar():
    pen = PenController(Random(3), PenGeometry(), 16)
    pen.sync(entries(16))
    pen.advance(90)
    x0, y0, x1, y1 = pen.area
    live = [c for c in pen.cats if not c.leaving]
    assert all(x0 <= c.x <= x1 and y0 <= c.y <= y1 for c in live)
    dist = [abs(a.x - b.x) + abs(a.y - b.y) for i, a in enumerate(live) for b in live[i + 1:]]
    assert min(dist) > 4


def test_estados_e_virada_do_sprite():
    pen = PenController(Random(2), PenGeometry(), 16)
    pen.sync(entries(16))
    vistos, facings = set(), set()
    for _ in range(3000):
        pen.update(0.1)
        for c in pen.cats:
            vistos.add(c.state)
            facings.add(c.facing)
    assert {"idle", "walk", "sleep", "play"} <= vistos and facings == {-1, 1}


def test_poke_para_o_gato_e_solta_coracoes():
    pen = PenController(Random(2), PenGeometry(), 4)
    pen.sync(entries(4))
    cid = pen.cats[0].cat_id
    assert pen.poke(cid)
    c = pen.cat(cid)
    assert c.state == "react"
    pen.update(0.5)
    assert pen.hearts
    x, y = c.x, c.y
    pen.update(0.5)
    assert (c.x, c.y) == (x, y)


def test_hit_devolve_o_gato_da_frente():
    pen = PenController(Random(2), PenGeometry(), 2)
    pen.sync(entries(2))
    a, b = pen.cats
    a.x, a.y, b.x, b.y = 200, 200, 205, 210
    assert pen.hit((203, 195)) == b.cat_id
    assert pen.hit((5, 5)) is None


@pytest.fixture()
def hub():
    h, _ = make(3, "criatorio_hub")
    return h


def test_hub_abre_no_cercado_com_16_gatos(hub):
    assert hub.mode == "cercado"
    assert len([c for c in hub.pen.cats if not c.leaving]) == 16


def test_clique_abre_ficha_e_esc_fecha(hub):
    c = hub.pen.cats[0]
    elem = hub.hit((int(c.x), int(c.y) - 10))
    assert elem and elem[0] in ("pen_cat", "pen_btn", "pen_floor")
    hub.click(("pen_cat", c.cat_id))
    assert hub.ficha == c.cat_id and hub.pen.cat(c.cat_id).state == "react"
    hub.key_escape()
    assert hub.ficha is None and hub.mode == "cercado"
    hub.key_escape()
    assert hub.mode == "menu"


def test_botoes_do_painel(hub):
    assert "adocao" not in hub.pen_buttons()
    hub.click(("pen_btn", "colecao"))
    assert hub.mode == "colecao"
    hub.click(("back",))
    assert hub.mode == "cercado"
    hub.click(("pen_btn", "breed"))
    assert hub.mode == "criatorio"
    hub.key_escape()
    assert hub.mode == "cercado"


def test_adocao_pendente_destaca_e_volta_ao_cercado():
    h, _ = make(3, "criatorio_hub_adocao")
    assert "adocao" in h.pen_buttons()
    h.click(("pen_btn", "adocao"))
    assert h.mode == "adocao"
    h.key_escape()
    assert h.mode == "cercado" and h.adoption_pending


@pytest.mark.parametrize("name", PEN_SCENES)
def test_cenas_sao_deterministicas_e_desenham(name):
    pygame.init()
    shots = []
    for _ in range(2):
        h, ui = make(3, name)
        surf = pygame.Surface((960, 540))
        draw_hub_frame(surf, h, UIState(t=0.2, mouse=ui.mouse))
        shots.append(pygame.image.tostring(surf, "RGB"))
    assert shots[0] == shots[1]


def test_ficha_e_botoes_dentro_da_tela():
    for cx in (60, 650):
        r = LP.ficha_rect(cx)
        assert pygame.Rect(0, 0, 960, 540).contains(r) and not r.colliderect(LP.panel_rect())
    for n in LP.BUTTONS:
        assert LP.panel_rect().contains(LP.button_rect(n))


# ------------------------------------------------------------------ T9.3: zonas e objetos
def zoned() -> list[PenEntry]:
    return ([PenEntry(f"k{i}", "persa", True, "filhote") for i in range(4)]
            + [PenEntry(f"b{i}", "persa", False, "breed", f"b{i ^ 1}") for i in range(4)]
            + [PenEntry(f"a{i:02d}", "siames", False, "deck" if i < 6 else "livre") for i in range(14)])


def test_cada_gato_vive_so_na_sua_zona_e_nos_limites():
    pen = PenController(Random(4), PenGeometry(), 16)
    pen.sync(zoned())
    for _ in range(1200):
        pen.update(0.1)
        for c in pen.cats:
            if c.leaving:
                continue
            x0, y0, x1, y1 = pen.rects[c.zone]
            assert x0 <= c.x <= x1 and y0 <= c.y <= y1
    zones = {c.cat_id: c.zone for c in pen.cats}
    assert all(z == "filhotes" for i, z in zones.items() if i.startswith("k"))
    assert all(z == "breed" for i, z in zones.items() if i.startswith("b"))
    assert pen.counts() == {"adultos": (8, 14), "breed": (2, 2), "filhotes": (4, 4)}


def test_slots_unicos_e_objetos_animam_em_use():
    pen = PenController(Random(6), PenGeometry(), 16)
    pen.sync(zoned())
    usados = set()
    for _ in range(3000):
        pen.update(0.1)
        taken = [(c.obj, c.slot) for c in pen.cats if c.obj is not None and not c.leaving]
        assert len(taken) == len(set(taken))
        for o in pen.objects:
            assert all(pen.cat(v).obj == o.index for v in o.occ.values())
            if o.occ:
                assert o.using
                usados.add(o.kind)
    assert {"cama_casal", "viveiro_cesto"} <= usados and len(usados) >= 5


def test_casal_dorme_junto_na_cama_casal():
    pen = PenController(Random(8), PenGeometry(), 16)
    pen.sync([e for e in zoned() if e.tag == "breed"])
    juntos = False
    for _ in range(4000):
        pen.update(0.1)
        for o in pen.objects:
            if len(o.occ) == 2:
                assert {o.occ[0], o.occ[1]} in ({"b0", "b1"}, {"b2", "b3"})
                juntos = True
    assert juntos


def test_clique_no_objeto_anima_e_chama_um_gato():
    pen = PenController(Random(2), PenGeometry(), 16)
    pen.sync([e for e in zoned() if e.zone == "adultos"])
    pen.advance(0.5)
    o = next(o for o in pen.objects if o.kind == "novelo")
    assert pen.hit_object((int(o.spec.x), int(o.spec.y) - 5)) == o.index
    assert pen.poke_object(o.index) and o.boost > 0 and o.using and len(o.occ) == 1
    pen.advance(30)
    assert o.ox != 0.0 or o.oy != 0.0 or not o.occ       # novelo se mexe enquanto brincam


def test_sem_objetos_gatos_so_andam_e_mudanca_de_zona_reaparece():
    geo = parse_geometry({"zones": {}})
    pen = PenController(Random(1), geo, 16)
    pen.sync([PenEntry("a", "siames", False, "livre")])
    pen.advance(40)
    assert pen.cat("a").state in ("idle", "walk") and pen.cat("a").obj is None
    pen.sync([PenEntry("a", "siames", False, "breed")])
    pen.advance(2)
    assert pen.cat("a").zone == "breed" and len(pen.cats) == 1


def test_objetos_da_arte_nova_sao_lidos_e_animam(tmp_path):
    pygame.init()
    sheet = pygame.Surface((32, 32), pygame.SRCALPHA)
    sheet.fill((255, 0, 0, 255), pygame.Rect(0, 0, 16, 16))
    sheet.fill((0, 255, 0, 255), pygame.Rect(16, 0, 16, 16))
    sheet.fill((0, 0, 255, 255), pygame.Rect(0, 16, 16, 16))
    pygame.image.save(sheet, str(tmp_path / "objects.png"))
    (tmp_path / "objects.json").write_text(json.dumps({
        "image": "objects.png", "size": [32, 32], "objects": {"novelo": {"frame": [16, 16], "anims": {
            "idle": {"row": 0, "frames": 2, "fps": 2}, "use": {"row": 1, "frames": 1, "fps": 1}}}}}), encoding="utf-8")
    (tmp_path / "pen.json").write_text(json.dumps({"zones": {"adultos": {"rect": [0, 0, 100, 100], "objects": [
        {"kind": "novelo", "x": 50, "y": 50, "slots": [[10, 0]], "slot_use": "play"}]}}, "ambient": []}), encoding="utf-8")
    art = PenArt(tmp_path)
    assert art.object_frame("novelo", "idle", 0.0).get_at((2, 2))[:3] == (255, 0, 0)
    assert art.object_frame("novelo", "idle", 0.5).get_at((2, 2))[:3] == (0, 255, 0)
    assert art.object_frame("novelo", "use", 0.0).get_at((2, 2))[:3] == (0, 0, 255)
    assert art.object_frame("cama_casal", "idle", 0.0) is None
    o = art.geo.zones["adultos"].objects[0]
    assert (o.kind, o.slots, o.slot_use) == ("novelo", [(10.0, 0.0)], "play") and art.geo.ambient == []
