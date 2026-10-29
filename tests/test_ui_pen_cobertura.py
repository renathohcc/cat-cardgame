"""Cobertura extra do Criatorio animado (T9.12): controlador, geometria, assets de pen e loop real com --hora."""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from random import Random

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
import pytest

from ui.pen_controller import OBJ_HIT_H, OBJ_HIT_W, PenController, PenEntry
from ui.pen_geometry import FALLBACK_MAX_CATS, FALLBACK_ZONE_CAPS, ZONES, PenGeometry, load_geometry, parse_geometry, pen_limits

ROOT = Path(__file__).resolve().parent.parent
PEN = ROOT / "assets" / "pen"


def _json(name: str) -> dict:
    return json.loads((PEN / name).read_text(encoding="utf-8"))


def _cast(adultos: int, casais: int, filhotes: int) -> list[PenEntry]:
    es = [PenEntry(f"a{i:02d}", "siames", False, "deck" if i < 12 else "livre") for i in range(adultos)]
    for i in range(casais):
        es += [PenEntry(f"b{2 * i}", "persa", False, "breed", f"b{2 * i + 1}"),
               PenEntry(f"b{2 * i + 1}", "persa", False, "breed", f"b{2 * i}")]
    es += [PenEntry(f"k{i}", "persa", True, "filhote") for i in range(filhotes)]
    return es


# ------------------------------------------------------------------ controlador
def _rules() -> dict:
    return json.loads((ROOT / "data" / "rules.json").read_text(encoding="utf-8"))


def test_limites_do_rules_json_real_sao_10_6_6_e_16():
    meta = _rules()["meta"]
    assert pen_limits(_rules()) == (meta["pen_max_cats"], meta["pen_zone_caps"])
    assert pen_limits(_rules()) == (16, {"adultos": 10, "breed": 6, "filhotes": 6})


@pytest.mark.parametrize("rules", [None, {}, {"meta": {}}, {"meta": {"pen_zone_caps": "x", "pen_max_cats": 0}},
                                   {"meta": {"pen_zone_caps": {"adultos": -1, "breed": True}, "pen_max_cats": "9"}}])
def test_pen_limits_cai_no_fallback_quando_chave_falta_ou_invalida(rules):
    assert pen_limits(rules) == (FALLBACK_MAX_CATS, FALLBACK_ZONE_CAPS)


def test_pen_limits_fallback_e_por_chave():
    mx, caps = pen_limits({"meta": {"pen_max_cats": 8, "pen_zone_caps": {"adultos": 4}}})
    assert mx == 8 and caps == {"adultos": 4, "breed": FALLBACK_ZONE_CAPS["breed"], "filhotes": FALLBACK_ZONE_CAPS["filhotes"]}


def test_limites_por_zona_10_adultos_3_casais_6_filhotes():
    _, caps = pen_limits(_rules())
    assert caps == {"adultos": 10, "breed": 6, "filhotes": 6}
    pen = PenController(Random(1), PenGeometry(), 99, zone_caps=caps)
    pen.sync(_cast(25, 5, 9))
    por_zona = {z: [i for i in pen.shown if pen.entries[i].zone == z] for z in ZONES}
    assert len(por_zona["adultos"]) == 10
    assert len(por_zona["breed"]) == 6
    assert len(por_zona["filhotes"]) == 6
    for cid in por_zona["breed"]:                      # casal sempre inteiro
        assert pen.entries[cid].partner in por_zona["breed"]


def test_total_respeita_o_maximo_e_breed_tem_prioridade():
    pen = PenController(Random(2), PenGeometry(), 12)
    pen.sync(_cast(25, 3, 6))
    tags = [pen.entries[i].tag for i in pen.shown]
    assert len(tags) == 12
    assert tags.count("breed") == 6 and tags.count("filhote") == 6      # breed + filhotes antes dos adultos
    assert "deck" not in tags and "livre" not in tags


def test_deck_entra_antes_dos_outros_adultos():
    pen = PenController(Random(3), PenGeometry(), 99)
    pen.sync(_cast(20, 0, 0))
    tags = [pen.entries[i].tag for i in pen.shown]
    assert tags.count("deck") == 10 and tags.count("livre") == 0


def test_rotacao_60s_troca_o_elenco_e_mantem_limites():
    pen = PenController(Random(4), PenGeometry(), 99)
    pen.sync(_cast(25, 5, 9))
    antes = set(pen.shown)
    pen.advance(50)
    assert set(pen.shown) == antes
    pen.advance(15)
    assert set(pen.shown) != antes
    c = pen.counts()
    assert c["adultos"][0] == 10 and c["breed"][0] == 3 and c["filhotes"][0] == 6


def test_determinismo_por_seed_posicoes_e_estados():
    def snap(seed: int):
        pen = PenController(Random(seed), PenGeometry(), 16)
        pen.sync(_cast(14, 2, 4))
        pen.advance(120)
        return [(c.cat_id, round(c.x, 3), round(c.y, 3), c.state) for c in pen.cats], list(pen.shown)
    assert snap(7) == snap(7)
    assert snap(7) != snap(8)


def test_hold_deixa_o_gato_imovel_e_libera_depois():
    pen = PenController(Random(5), PenGeometry(), 6)
    pen.sync(_cast(6, 0, 0))
    cid = pen.cats[0].cat_id
    pen.hold(cid)
    c = pen.cat(cid)
    p = (c.x, c.y)
    pen.advance(20)
    assert (c.x, c.y) == p
    pen.hold(None)
    pen.advance(40)
    assert (c.x, c.y) != p


def test_dois_gatos_nunca_no_mesmo_slot_em_10_min():
    pen = PenController(Random(9), PenGeometry(), 16)
    pen.sync(_cast(14, 2, 4))
    for _ in range(6000):
        pen.update(0.1)
        taken = [(c.obj, c.slot) for c in pen.cats if c.obj is not None and not c.leaving]
        assert len(taken) == len(set(taken))


def test_sem_objetos_nunca_dorme_nem_brinca():
    geo = parse_geometry({"zones": {"adultos": {"rect": [0, 0, 300, 300], "objects": []}}})
    pen = PenController(Random(1), geo, 6)
    pen.sync(_cast(5, 0, 0))
    vistos = set()
    for _ in range(3000):
        pen.update(0.1)
        vistos |= {c.state for c in pen.cats}
    assert not vistos & {"play", "sleep"}


def test_remover_gato_faz_fade_e_some():
    pen = PenController(Random(1), PenGeometry(), 8)
    es = _cast(5, 0, 0)
    pen.sync(es)
    pen.advance(3)
    pen.sync(es[1:])
    c = pen.cat(es[0].cat_id)
    assert c is None or c.leaving
    pen.advance(3)
    assert all(c.cat_id != es[0].cat_id for c in pen.cats)


def test_casal_so_dorme_junto_na_cama_de_casal_da_zona_breed():
    pen = PenController(Random(11), load_geometry(), 16)
    pen.sync(_cast(0, 2, 0))
    juntos = False
    for _ in range(5000):
        pen.update(0.1)
        for o in pen.objects:
            if len(o.occ) == 2:
                assert o.kind == "cama_casal" and o.zone == "breed"
                a, b = o.occ.values()
                assert pen.entries[a].partner == b
                juntos = True
    assert juntos


def test_gatos_do_json_real_ficam_na_zona_em_5_min():
    pen = PenController(Random(12), load_geometry(), 16)
    pen.sync(_cast(14, 2, 4))
    for _ in range(3000):
        pen.update(0.1)
        for c in pen.cats:
            x0, y0, x1, y1 = pen.rects[c.zone]
            assert x0 <= c.x <= x1 and y0 - 100 <= c.y <= y1      # slots de telhado/banco sobem acima do topo


# ------------------------------------------------------------------ geometria
def test_zonas_do_json_real_nao_se_sobrepoem_e_ficam_antes_do_painel():
    g = load_geometry()
    rs = [g.zones[z].rect for z in ZONES]
    for i, a in enumerate(rs):
        assert a[0] >= 0 and a[1] >= 0 and a[0] + a[2] <= g.panel[0] and a[1] + a[3] <= 540
        for b in rs[i + 1:]:
            assert a[0] + a[2] <= b[0] or b[0] + b[2] <= a[0] or a[1] + a[3] <= b[1] or b[1] + b[3] <= a[1]


def test_objetos_do_json_real_estao_dentro_da_sua_zona():
    g = load_geometry()
    for z in ZONES:
        x, y, w, h = g.zones[z].rect
        for o in g.zones[z].objects:
            assert x <= o.x <= x + w and y <= o.y <= y + h, (z, o.kind)


def test_slots_ficam_dentro_da_zona_em_x_e_nao_abaixo_da_base():
    pen = PenController(Random(1), load_geometry(), 16)
    for o in pen.objects:
        x0, y0, x1, y1 = pen.rects[o.zone]
        for s in range(len(o.spec.slots)):
            sx, sy = o.slot_pos(s)
            assert x0 <= sx <= x1 and sy <= y1, (o.kind, s)


def test_slot_de_um_objeto_nao_cai_no_hitbox_de_outro_com_slots():
    pen = PenController(Random(1), load_geometry(), 16)
    for o in pen.objects:
        for s in range(len(o.spec.slots)):
            sx, sy = o.slot_pos(s)
            for p in pen.objects:
                if p is o or p.zone != o.zone or not p.spec.slots:
                    continue
                dentro = abs(sx - p.spec.x) <= OBJ_HIT_W / 2 and 0 <= p.spec.y - sy <= OBJ_HIT_H
                assert not dentro, (o.kind, o.index, p.kind, p.index)


# ------------------------------------------------------------------ assets de pen
@pytest.mark.parametrize("name", ["pen.json", "objects.json", "ambient.json", "cats_pen.json", "fx.json", "palette_pen.json"])
def test_json_de_pen_e_valido(name):
    assert isinstance(_json(name), dict)


def test_frames_de_objects_e_ambient_dentro_da_imagem():
    pygame.init()
    for nome in ("objects.json", "ambient.json"):
        meta = _json(nome)
        img = pygame.image.load(str(PEN / meta["image"]))
        assert list(img.get_size()) == meta["size"]
        for kind, spec in meta["objects"].items():
            fw, fh = spec["frame"]
            ax, ay = spec["anchor"]
            assert 0 <= ax <= fw and 0 <= ay <= fh, (nome, kind)
            for an, a in spec["anims"].items():
                assert (a["row"] + 1) * fh <= img.get_height(), (nome, kind, an)
                assert a["frames"] * fw <= img.get_width(), (nome, kind, an)


def test_frames_de_cats_pen_dentro_da_imagem_e_com_as_4_anims():
    pygame.init()
    meta = _json("cats_pen.json")
    img = pygame.image.load(str(PEN / meta["image"]))
    assert list(img.get_size()) == meta["size"]
    fw, fh = meta["frame"]
    assert meta["anims"]
    for raca, anims in meta["anims"].items():
        assert {"idle", "walk", "sleep", "play"} <= set(anims), raca
        for an, a in anims.items():
            assert (a["row"] + 1) * fh <= img.get_height() and a["frames"] * fw <= img.get_width(), (raca, an)


def test_cats_pen_cobre_todas_as_racas_do_jogo_adulto_e_filhote():
    racas = {b["id"] for b in json.loads((ROOT / "data" / "breeds.json").read_text(encoding="utf-8"))["breeds"]}
    chaves = set(_json("cats_pen.json")["anims"])
    assert racas <= chaves and {r + "_filhote" for r in racas} <= chaves


def test_anims_one_shot_das_camas_sao_loop_false_e_idle_estatico():
    objs = _json("objects.json")["objects"]
    camas = [k for k in objs if k.startswith("cama_") or k == "viveiro_cesto"]
    assert len(camas) == 5
    for k in camas:
        an = objs[k]["anims"]
        assert an["enter"]["loop"] is False and an["exit"]["loop"] is False, k
        assert an["idle"]["frames"] == 1, k


def test_objetos_e_ambiente_do_pen_json_existem_nas_artes():
    objs = set(_json("objects.json")["objects"])
    pen = _json("pen.json")
    for z in pen["zones"].values():
        for o in z["objects"]:
            assert o["kind"] in objs, o["kind"]
    amb = set(_json("ambient.json")["objects"])
    for a in pen.get("ambient", []):
        assert a["kind"] in amb, a["kind"]


def _paleta() -> set[tuple[int, int, int]]:
    out = set()
    for v in _json("palette_pen.json").values():
        v = v.lstrip("#")
        out.add(tuple(int(v[i:i + 2], 16) for i in (0, 2, 4)))
    return out


def _cores_fora(path: Path) -> set[tuple[int, int, int]]:
    img = pygame.image.load(str(path))
    cores = {tuple(img.get_at((x, y)))[:3] for x in range(img.get_width()) for y in range(img.get_height())
             if img.get_at((x, y)).a > 0}      # imagem sem convert: alpha original
    return cores - _paleta()


@pytest.mark.parametrize("nome", ["pen_bg_dia.png", "objects.png"])
def test_fundo_do_dia_e_objetos_so_usam_cores_da_paleta_do_pen(nome):
    pygame.init()
    fora = _cores_fora(PEN / nome)
    assert not fora, f"{len(fora)} cores fora da paleta: {sorted(fora)[:5]}"


@pytest.mark.parametrize("nome", ["pen_bg_noite.png", "pen_bg_amanhecer.png", "pen_bg_entardecer.png"])
def test_fundos_de_periodo_sao_o_fundo_do_dia_tingido_sem_novas_cores(nome):
    # PALETA_PEN.md: os fundos de periodo sao a paleta do dia multiplicada pelo tint (no maximo 1 cor por cor da paleta)
    pygame.init()
    def n(f):
        img = pygame.image.load(str(PEN / f))
        return len({tuple(img.get_at((x, y)))[:3] for x in range(img.get_width()) for y in range(img.get_height())
                    if img.get_at((x, y)).a > 0})
    assert n(nome) <= n("pen_bg_dia.png") + 4        # folga de arredondamento do tint
    assert pygame.image.load(str(PEN / nome)).get_size() == pygame.image.load(str(PEN / "pen_bg_dia.png")).get_size()


def test_rotulos_de_zona_nao_sao_desenhados():
    import ui.pen_geometry as pg
    import ui.render_pen as rp
    assert not hasattr(rp, "draw_zone_labels") and not hasattr(pg, "ZONE_LABEL")


# ------------------------------------------------------------------ loop real com --hora
def _brilho(surf: pygame.Surface) -> float:
    r, g, b = pygame.transform.smoothscale(surf, (1, 1)).get_at((0, 0))[:3]
    return (r + g + b) / 3


def _loop_hora(monkeypatch, hora: str) -> float:
    from ui.app_hub import run
    quadros, medidas = [0], []
    real_flip = pygame.display.flip

    def flip() -> None:
        real_flip()
        quadros[0] += 1
        if quadros[0] == 40:
            medidas.append(_brilho(pygame.display.get_surface().subsurface(pygame.Rect(48, 64, 384, 416)).copy()))
        if quadros[0] >= 40:
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    with monkeypatch.context() as m:
        m.setattr(pygame.display, "flip", flip)
        asyncio.run(run(3, None, "criatorio_hub", hora))
    assert quadros[0] >= 40 and medidas
    return medidas[0]


def test_loop_real_do_hub_com_hora_noite_e_mais_escura_que_meio_dia(monkeypatch):
    dia = _loop_hora(monkeypatch, "12:00")
    noite = _loop_hora(monkeypatch, "22:00")
    assert noite < dia


# ------------------------------------------------------------------ ficha aberta (held) na rotacao
def _rotacoes(seed: int, held: str | None, n: int = 6):
    pen = PenController(Random(seed), PenGeometry(), 99)
    es = _cast(25, 5, 9)
    pen.sync(es)
    if held:
        pen.hold(held)
    historico = []
    for _ in range(n):
        pen.advance(61)
        pen.sync(es, rotate=True)
        historico.append(sorted(pen.shown))
        if held:
            assert held in pen.shown
    return historico


def test_gato_com_ficha_aberta_nao_sai_na_rotacao_de_60s():
    pen = PenController(Random(21), PenGeometry(), 99)
    es = _cast(25, 5, 9)
    pen.sync(es)
    for cid in list(pen.shown):                       # vale para adulto, filhote e casal de breed
        pen.hold(cid)
        for _ in range(8):
            pen.sync(es, rotate=True)
            assert cid in pen.shown
            vivo = pen.cat(cid)
            assert vivo is not None and not vivo.leaving


def test_rotacao_com_held_e_deterministica_por_seed():
    held = "a03"
    pen0 = PenController(Random(30), PenGeometry(), 99)
    pen0.sync(_cast(25, 5, 9))
    if held not in pen0.shown:
        held = next(i for i in pen0.shown if pen0.entries[i].zone == "adultos")
    assert _rotacoes(30, held) == _rotacoes(30, held)
    assert _rotacoes(30, held) != _rotacoes(31, held)


def test_rotacao_com_held_ainda_troca_os_outros_gatos():
    pen = PenController(Random(40), PenGeometry(), 99)
    es = _cast(25, 5, 9)
    pen.sync(es)
    held = next(i for i in pen.shown if pen.entries[i].zone == "adultos")
    pen.hold(held)
    antes = set(pen.shown)
    pen.sync(es, rotate=True)
    assert held in pen.shown and set(pen.shown) != antes
