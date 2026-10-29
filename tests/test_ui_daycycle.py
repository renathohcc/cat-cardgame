"""T9.5: ciclo do dia, camas one-shot, ordenacao do telhado e formato novo da arte do quintal."""
from __future__ import annotations

import json
import os
from datetime import datetime
from random import Random

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
import pytest

from ui import daycycle as D
from ui.pen_controller import PenController, PenEntry
from ui.pen_geometry import PenGeometry, load_geometry, parse_geometry
from ui.pen_sprites import PenArt
from ui.render import UIState
from ui.render_hub import draw_hub_frame
from ui.scenes_hub import make


def at(h: int, m: int = 0) -> datetime:
    return datetime(2026, 1, 1, h, m)


@pytest.mark.parametrize("h,m,period", [(0, 0, "noite"), (4, 30, "noite"), (6, 30, "amanhecer"), (12, 0, "dia"),
                                        (18, 15, "entardecer"), (22, 0, "noite"), (23, 59, "noite")])
def test_periodo_pela_hora(h, m, period):
    st = D.day_state(at(h, m))
    assert st.period == period and st.mix == 0.0 and st.next == period


def test_crossfade_de_30_min_centrado_na_fronteira():
    a, b, c = D.day_state(at(7, 44)), D.day_state(at(8, 0)), D.day_state(at(8, 16))
    assert (a.period, a.mix) == ("amanhecer", 0.0)
    assert (b.period, b.next) == ("amanhecer", "dia") and 0.45 < b.mix < 0.55
    assert (c.period, c.mix) == ("dia", 0.0)
    n = D.day_state(at(19, 30))
    assert (n.period, n.next) == ("entardecer", "noite") and 0.45 < n.mix < 0.55
    w = D.day_state(at(5, 0))                      # fronteira da madrugada: noite -> amanhecer
    assert (w.period, w.next) == ("noite", "amanhecer")
    mixes = [D.day_state(465.0 + i).mix for i in range(30)]       # 07:45 .. 08:14
    assert mixes == sorted(mixes) and mixes[0] == 0.0 and mixes[-1] > 0.99


def test_lanternas_e_atividade_por_periodo():
    assert D.day_state(at(12)).lit == 0.0 and D.day_state(at(6, 30)).lit == 0.0
    assert D.day_state(at(18, 15)).lit == 1.0 and D.day_state(at(22)).lit == 1.0
    assert 0.0 < D.day_state(at(17, 0)).lit < 1.0
    assert D.day_state(at(22)).activity()[0] > D.day_state(at(12)).activity()[0]
    assert D.day_state(at(12)).activity()[1] > D.day_state(at(22)).activity()[1]
    st = D.day_state(at(22))
    assert st.weight_of(None) == 1.0 and st.weight_of(["noite"]) == 1.0 and st.weight_of(["dia"]) == 0.0


def test_parse_hora():
    assert D.parse_hora("06:30").hour == 6 and D.fixed_clock("22:05")().minute == 5
    with pytest.raises(ValueError):
        D.parse_hora("abc")


def test_controlador_recalcula_a_cada_30s_com_relogio_injetado():
    now = [at(12)]
    pen = PenController(Random(1), PenGeometry(), 16, lambda: now[0])
    assert pen.day.period == "dia"
    now[0] = at(22)
    pen.update(10)
    assert pen.day.period == "dia"
    pen.update(21)
    assert pen.day.period == "noite"


def _fracao_dormindo(hora: datetime) -> float:
    pen = PenController(Random(5), PenGeometry(), 16, lambda: hora)
    pen.sync([PenEntry(f"a{i:02d}", "siames", False, "livre") for i in range(10)])
    dorme = total = 0
    for _ in range(4000):
        pen.update(0.2)
        for c in pen.cats:
            total += 1
            dorme += c.state == "sleep"
    return dorme / total


def test_gatos_dormem_mais_a_noite_que_de_dia():
    assert _fracao_dormindo(at(22)) > _fracao_dormindo(at(12)) * 1.4


def _geo_cama():
    return parse_geometry({"zones": {"adultos": {"rect": [0, 0, 300, 300], "objects": [
        {"kind": "cama_cesto", "x": 150, "y": 150, "layer": "floor", "slots": [[0, -8]], "slot_use": "sleep"}]}}})


def test_cama_toca_enter_e_exit_uma_vez_cada():
    pen = PenController(Random(3), _geo_cama(), 4)
    pen.sync([PenEntry("a", "siames", False, "livre")])
    bed = pen.objects[0]
    vistos: list = []
    for _ in range(4000):
        pen.update(0.1)
        if not vistos or vistos[-1] != bed.oneshot:
            vistos.append(bed.oneshot)
        if bed.oneshot == "exit":
            break
    assert vistos[0] is None and "enter" in vistos and vistos[-1] == "exit"
    assert vistos.count("enter") == 1 and vistos.index("enter") < vistos.index("exit")


def test_cama_desenha_idle_estatico_e_oneshot_com_arte(tmp_path):
    pygame.init()
    sheet = pygame.Surface((32, 48), pygame.SRCALPHA)
    for r, col in enumerate(((255, 0, 0), (0, 255, 0), (0, 0, 255))):
        sheet.fill((*col, 255), pygame.Rect(0, r * 16, 16, 16))
    sheet.fill((9, 9, 9, 255), pygame.Rect(16, 16, 16, 16))
    pygame.image.save(sheet, str(tmp_path / "objects.png"))
    (tmp_path / "objects.json").write_text(json.dumps({"image": "objects.png", "objects": {"cama_cesto": {
        "frame": [16, 16], "anims": {"idle": {"row": 0, "frames": 1, "fps": 1},
                                     "enter": {"row": 1, "frames": 2, "fps": 4},
                                     "exit": {"row": 2, "frames": 1, "fps": 4}}}}}))
    art = PenArt(tmp_path)
    from ui.render_pen import bed_frame
    bed = PenController(Random(1), _geo_cama(), 4).objects[0]
    assert bed_frame(art, bed).get_at((1, 1))[:3] == (255, 0, 0)
    bed.oneshot, bed.oneshot_t, bed.sleepers = "enter", 0.0, 1
    assert bed_frame(art, bed).get_at((1, 1))[:3] == (0, 255, 0)
    bed.oneshot_t = 0.3
    assert bed_frame(art, bed).get_at((1, 1))[:3] == (9, 9, 9)
    bed.oneshot_t = 5.0                                # ocupada: segura o ultimo quadro do enter
    assert bed_frame(art, bed).get_at((1, 1))[:3] == (9, 9, 9)
    bed.sleepers, bed.oneshot, bed.oneshot_t = 0, "exit", 0.0
    assert bed_frame(art, bed).get_at((1, 1))[:3] == (0, 0, 255)
    bed.oneshot_t = 0.5                                # exit acabou: idle
    assert bed_frame(art, bed).get_at((1, 1))[:3] == (255, 0, 0)
    assert art.anim_duration("cama_cesto", "enter") == 0.5 and art.anim_duration("cama_cesto", "nada") == 0.0


def test_gato_no_telhado_e_desenhado_depois_da_casinha():
    geo = parse_geometry({"zones": {"adultos": {"rect": [0, 0, 300, 300], "objects": [
        {"kind": "casinha", "x": 150, "y": 200, "slots": [[0, -40], [0, 8]], "slot_use": "sleep"}]}}})
    pen = PenController(Random(3), geo, 4)
    pen.sync([PenEntry("a", "siames", False, "livre")])
    vistos = 0
    for _ in range(6000):
        pen.update(0.1)
        c = pen.cats[0]
        if c.state == "sleep" and c.slot == 0:
            assert c.y < 200 and pen.sort_y(c) > 200
            vistos += 1
    assert vistos > 0


def test_slots_ficam_dentro_da_zona_e_decor_nao_tem_slot():
    geo = parse_geometry({"zones": {"adultos": {"rect": [10, 10, 100, 100], "objects": [
        {"kind": "banco_arvore", "x": 15, "y": 12, "slots": [[-50, -90]], "slot_use": "sleep"},
        {"kind": "tigela", "x": 50, "y": 50, "slots": [[0, 0]]}]}}})
    pen = PenController(Random(1), geo, 4)
    b, t = pen.objects
    x, y = b.slot_pos(0)
    assert 10 <= x <= 110 and y == 12 - 90          # offset negativo da arte nao e limitado ao topo
    assert t.spec.slots == []
    pen.sync([PenEntry("a", "siames", False, "livre")])
    pen.advance(60)
    assert not t.occ


def test_json_real_slots_dentro_das_zonas():
    pen = PenController(Random(1), load_geometry(), 16)
    for o in pen.objects:
        x0, y0, x1, y1 = pen.rects[o.zone]
        for s in range(len(o.spec.slots)):
            x, y = o.slot_pos(s)
            assert x0 <= x <= x1 and y0 <= y <= y1


def test_geometria_periodos_de_fundo_e_ambient():
    g = parse_geometry({"bg_periods": {"dia": "a.png", "noite": "b.png", "x": "c.png"}, "ambient": [
        {"kind": "estrela", "x": 1, "y": 2, "periods": ["noite"]}, {"kind": "grama", "x": 3, "y": 4}], "zones": {}})
    assert g.bg_periods == {"dia": "a.png", "noite": "b.png"}
    assert g.ambient[0].periods == ("noite",) and g.ambient[1].periods is None


def test_fundo_por_periodo_e_fallback(tmp_path):
    pygame.init()
    for nome, col in (("dia", (200, 0, 0)), ("noite", (0, 0, 200))):
        s = pygame.Surface((960, 540))
        s.fill(col)
        pygame.image.save(s, str(tmp_path / f"bg_{nome}.png"))
    (tmp_path / "pen.json").write_text(json.dumps({"bg_periods": {"dia": "bg_dia.png", "noite": "bg_noite.png"},
                                                   "zones": {}}))
    art = PenArt(tmp_path)
    from ui.render_pen import draw_floor
    surf = pygame.Surface((960, 540))
    draw_floor(surf, art, D.day_state(at(12)))
    assert surf.get_at((5, 5))[:3] == (200, 0, 0)
    draw_floor(surf, art, D.day_state(at(22)))
    assert surf.get_at((5, 5))[:3] == (0, 0, 200)
    draw_floor(surf, art, D.day_state(at(19, 30)))              # meio do crossfade (sem fundo proprio: cai no bg)
    assert art.background("amanhecer") is not None


@pytest.mark.parametrize("hora", ["06:30", "12:00", "18:15", "22:00"])
def test_cena_desenha_em_todas_as_horas(hora):
    pygame.init()
    h, ui = make(3, "criatorio_hub", hora)
    assert h.pen.day.period == D.day_state(D.parse_hora(hora)).period
    surf = pygame.Surface((960, 540))
    draw_hub_frame(surf, h, UIState(t=0.2, mouse=ui.mouse))


def test_arte_real_tint_lanterna_e_slots():
    pygame.init()
    art = PenArt()
    assert set(art.geo.period_tint) == set(D.PERIODS) and art.geo.lantern_on == ("entardecer", "noite")
    assert art.tint_for(D.day_state(at(12))) == (255, 255, 255)
    assert art.tint_for(D.day_state(at(22))) == art.geo.period_tint["noite"]
    img = art.object_frame("cama_cesto", "idle", 0.0)
    assert img is not None and art.anchor("cama_cesto") == (64, 86) and art.anchor("lanterna", True) == (48, 60)
    assert art.tinted(img, (118, 138, 206)).get_size() == img.get_size()
    roof = next(o for o in PenController(Random(1), art.geo, 16).objects if o.kind == "casinha")
    assert roof.slot_pos(0)[1] < roof.spec.y - 40          # telhado nao e puxado para baixo
