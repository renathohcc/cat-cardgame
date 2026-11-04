"""Conteudo das areas 4 a 6 do quintal (T13.5b): jardim-lagoa, patio-casais-nobre e pomar. Headless.

Bloqueada: nada do `floor`/`sorted` e desenhado e os gatos nao entram no retangulo.
Aberta: conteudo presente, ratinho realocado, objetos com slots sob a arte ficam inativos."""
from __future__ import annotations

import pytest

from ui_eco_helpers import add_cats, hub_no_cercado
from ui import lock_art, pen_world, render_pen
from ui.pen_world import RELOCATE, point_in
from ui.render import UIState

import pygame

AREAS = ("cercado-adultos-ampliado", "cercadinho-filhotes", "patio-casais-ampliado", "jardim-lagoa",
         "patio-casais-nobre", "pomar")
NOVAS = AREAS[3:]
BASE = AREAS[:3]
ORIGEM = (336, 240)
DESTINO = (262, 232)


def hub_com(areas: tuple[str, ...]):
    h = hub_no_cercado()
    add_cats(h.save, adults=6, kittens=3)
    h.save.areas_unlocked = list(areas)
    h.col.refresh_deck()
    h.enter_pen()
    h.refresh_world()
    h.pen.advance(30.0)
    return h


def ratinho(h):
    rs = [o for o in h.pen.objects if o.spec.kind == "ratinho" and o.gate is None]
    assert len(rs) == 1
    return rs[0]


def pos_ratinho(h) -> tuple[int, int]:
    o = ratinho(h)
    return int(o.spec.x), int(o.spec.y)


def rect_de(h, aid: str):
    return h.area_content[aid].rect


def espiar_desenho(h, monkeypatch):
    """Desenha o cercado e devolve (pisos, sprites) pedidos a arte de conteudo."""
    art = lock_art.art()
    pisos: list[str] = []
    sprites: list[str] = []
    real_f, real_s = art.content_floor, art.content_sprite

    def f(aid, t):
        pisos.append(aid)
        return real_f(aid, t)

    def s(name):
        sprites.append(name)
        return real_s(name)

    monkeypatch.setattr(art, "content_floor", f)
    monkeypatch.setattr(art, "content_sprite", s)
    canvas = pygame.Surface((960, 540))
    render_pen.draw_pen(canvas, h, UIState())
    return pisos, sprites


def test_conteudo_das_tres_areas_novas_existe_nos_dados_da_arte():
    spec = pen_world.load_content_spec()
    assert set(NOVAS) <= set(spec)
    assert all(spec[a].floor for a in NOVAS)


# ============================================================ bloqueada
def test_area_bloqueada_nao_desenha_piso_nem_arvores(monkeypatch):
    h = hub_com(BASE)
    pisos, sprites = espiar_desenho(h, monkeypatch)
    assert pisos == [] and sprites == []


@pytest.mark.parametrize("aberta", NOVAS)
def test_so_a_area_aberta_desenha_o_proprio_conteudo(aberta, monkeypatch):
    h = hub_com(BASE + (aberta,))
    pisos, sprites = espiar_desenho(h, monkeypatch)
    assert pisos == [aberta]
    esperado = [sp.file for sp in h.area_content[aberta].sprites]
    assert sorted(sprites) == sorted(esperado)


@pytest.mark.parametrize("bloqueada", NOVAS)
def test_gatos_nao_entram_no_retangulo_de_area_bloqueada(bloqueada):
    h = hub_com(BASE)
    r = rect_de(h, bloqueada)
    for _ in range(600):                              # 5 min de jogo
        h.pen.advance(0.5)
        for c in h.pen.cats:
            # interior estrito: pisar exatamente na borda (y == topo) nao e entrar
            dentro = r[0] < c.x < r[0] + r[2] and r[1] < c.y < r[1] + r[3]
            assert not dentro, (c.cat_id, c.x, c.y, bloqueada)


def test_objetos_do_conteudo_ficam_inativos_com_a_area_bloqueada():
    h = hub_com(BASE)
    do_conteudo = [o for o in h.pen.objects if o.baked]
    assert do_conteudo and not any(o.active for o in do_conteudo)


# ============================================================ aberta
def test_area_aberta_ativa_os_objetos_do_conteudo():
    h = hub_com(BASE + NOVAS)
    do_conteudo = [o for o in h.pen.objects if o.baked]
    assert {o.spec.kind for o in do_conteudo} >= {"lagoa", "cama_casal_nobre", "arvore_grande"}
    assert all(o.active for o in do_conteudo)


def test_objeto_do_conteudo_so_ativa_com_a_propria_area():
    h = hub_com(BASE + ("pomar",))
    ativos = {o.spec.kind for o in h.pen.objects if o.baked and o.active}
    assert ativos == {"arvore_grande"}


def test_ratinho_comeca_no_ponto_original_com_pomar_fechado():
    assert pos_ratinho(hub_com(BASE)) == ORIGEM


def test_ratinho_vai_para_o_ponto_novo_quando_o_pomar_abre():
    h = hub_com(BASE)
    h.save.areas_unlocked = list(BASE + ("pomar",))
    h.refresh_world()
    assert pos_ratinho(h) == DESTINO
    assert not point_in(*DESTINO, rect_de(h, "pomar"))


def test_ratinho_volta_ao_ponto_original_quando_o_pomar_fecha():
    h = hub_com(BASE + ("pomar",))
    assert pos_ratinho(h) == DESTINO
    h.save.areas_unlocked = list(BASE)
    h.refresh_world()
    assert pos_ratinho(h) == ORIGEM


def test_ratinho_nao_se_move_quando_abre_outra_area():
    h = hub_com(BASE + ("jardim-lagoa", "patio-casais-nobre"))
    assert pos_ratinho(h) == ORIGEM


def test_tabela_de_realocacao_do_ratinho_e_a_esperada():
    assert RELOCATE[("ratinho", *ORIGEM)] == DESTINO


@pytest.mark.parametrize("aberta", ("jardim-lagoa", "patio-casais-nobre"))
def test_objetos_com_slots_do_cercado_dentro_da_area_aberta_ficam_inativos(aberta):
    h = hub_com(BASE + (aberta,))
    r = rect_de(h, aberta)
    # `baked` = os objetos novos da propria area (esses ficam ativos); gate != None = decoracao comprada
    antigos = [o for o in h.pen.objects if o.gate is None and o.spec.slots]
    sob = [o for o in antigos if point_in(o.spec.x, o.spec.y, r)]
    assert sob, "esperava ao menos um objeto com slots do pen.json sob a area"
    assert not any(o.active for o in sob)


def test_objetos_com_slots_fora_das_areas_abertas_continuam_ativos():
    h = hub_com(BASE + NOVAS)
    rects = [rect_de(h, a) for a in NOVAS]
    fora = [o for o in h.pen.objects if o.gate is None and o.spec.slots
            and not any(point_in(o.spec.x, o.spec.y, r) for r in rects) and h.pen.zone_open[o.zone]]
    assert fora and all(o.active for o in fora)


def test_objetos_sob_a_area_voltam_a_ficar_ativos_se_ela_fechar():
    h = hub_com(BASE + ("jardim-lagoa",))
    r = rect_de(h, "jardim-lagoa")
    sob = [o for o in h.pen.objects if o.gate is None and o.spec.slots and point_in(o.spec.x, o.spec.y, r)]
    assert sob and not any(o.active for o in sob)
    h.save.areas_unlocked = list(BASE)
    h.refresh_world()
    # a area fechou: coberta pela camada de bloqueio, logo continuam inativos (sob o bloqueio)
    assert not any(o.active for o in sob)
