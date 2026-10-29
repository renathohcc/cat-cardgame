"""Testes de ui/display.py: escala fracionaria, mouse -> interno, render e fullscreen (SDL dummy)."""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from ui import display
from ui.display import Display, dest_rect, inside, render_scaled, to_internal
from ui.theme import H, W

JANELAS = [(480, 270), (960, 540), (1440, 810), (1920, 1080), (2560, 1440),
           (1366, 768), (1000, 300), (300, 1000), (100, 50), (1, 1)]


@pytest.fixture
def tela():
    pygame.display.init()
    yield
    pygame.display.quit()


# ---------------- dest_rect ----------------

@pytest.mark.parametrize("win", JANELAS)
def test_dest_rect_fica_dentro_da_janela(win):
    x, y, w, h = dest_rect(win)
    assert x >= 0 and y >= 0 and w >= 1 and h >= 1
    assert x + w <= win[0] and y + h <= win[1]


@pytest.mark.parametrize("win", [j for j in JANELAS if min(j) >= 50])
def test_dest_rect_mantem_proporcao_16_9(win):
    _, _, w, h = dest_rect(win)
    assert abs(w - h * W / H) <= 1 or abs(h - w * H / W) <= 1


@pytest.mark.parametrize("win", JANELAS)
def test_dest_rect_centralizado(win):
    x, y, w, h = dest_rect(win)
    assert abs(x - (win[0] - x - w)) <= 1
    assert abs(y - (win[1] - y - h)) <= 1


@pytest.mark.parametrize("win", [j for j in JANELAS if min(j) >= 50])
def test_dest_rect_usa_maior_escala_possivel(win):
    _, _, w, h = dest_rect(win)
    # encosta em pelo menos um eixo (tolerancia de 1px) e nao cabe um canvas maior
    assert w >= win[0] - 1 or h >= win[1] - 1
    assert win[0] * H // W <= h + 1 or win[1] * W // H <= w + 1


@pytest.mark.parametrize("mult", [1, 2, 3, 4, 5])
def test_dest_rect_escala_inteira_preenche_exato(mult):
    assert dest_rect((W * mult, H * mult)) == (0, 0, W * mult, H * mult)


def test_dest_rect_janela_larga_tem_faixas_laterais():
    x, y, w, h = dest_rect((1000, 300))
    assert y == 0 and h == 300 and x > 0


def test_dest_rect_janela_alta_tem_faixas_em_cima_e_embaixo():
    x, y, w, h = dest_rect((300, 1000))
    assert x == 0 and w == 300 and y > 0


# ---------------- to_internal / inside ----------------

@pytest.mark.parametrize("win", [(480, 270), (960, 540), (1920, 1080), (1366, 768), (1000, 300), (300, 1000)])
def test_canto_superior_esquerdo_mapeia_para_origem(win):
    x, y, _, _ = dest_rect(win)
    assert to_internal((x, y), win) == (0, 0)


@pytest.mark.parametrize("win", [(480, 270), (960, 540), (1920, 1080), (1366, 768), (1000, 300), (300, 1000)])
def test_canto_inferior_direito_mapeia_para_perto_do_fim(win):
    x, y, w, h = dest_rect(win)
    ix, iy = to_internal((x + w - 1, y + h - 1), win)
    tol = 2 + int(W / w)                   # janela menor que o canvas: 1 px da janela = varios internos
    assert W - 1 - tol <= ix <= W - 1
    assert H - 1 - tol <= iy <= H - 1


@pytest.mark.parametrize("win", [(480, 270), (960, 540), (1920, 1080), (1366, 768), (1000, 300)])
def test_centro_da_janela_mapeia_para_centro_interno(win):
    ix, iy = to_internal((win[0] // 2, win[1] // 2), win)
    assert abs(ix - W // 2) <= 2 and abs(iy - H // 2) <= 2


def test_ponto_na_faixa_preta_lateral_cai_fora():
    win = (1000, 300)
    assert not inside(to_internal((2, 150), win))
    assert not inside(to_internal((997, 150), win))


def test_ponto_na_faixa_preta_vertical_cai_fora():
    win = (300, 1000)
    assert not inside(to_internal((150, 2), win))
    assert not inside(to_internal((150, 997), win))


def test_escala_fracionaria_1366x768_cobre_canvas_inteiro():
    win = (1366, 768)
    x, y, w, h = dest_rect(win)
    vistos = {to_internal((px, y + h // 2), win)[0] for px in range(x, x + w)}
    assert min(vistos) == 0 and max(vistos) >= W - 2


def test_inside_limites():
    assert inside((0, 0)) and inside((W - 1, H - 1))
    assert not inside((-1, 0)) and not inside((0, -1))
    assert not inside((W, 0)) and not inside((0, H))


@pytest.mark.parametrize("win", [(480, 270), (960, 540), (1440, 810), (1366, 768), (2560, 1440), (1000, 300), (300, 1000)])
def test_ida_e_volta_interno_tela_interno_erro_menor_que_1px(win):
    x, y, w, h = dest_rect(win)
    for ix, iy in [(0, 0), (1, 1), (100, 50), (240, 135), (400, 200), (W - 1, H - 1)]:
        tx = x + ix * w / W
        ty = y + iy * h / H
        # ponto no centro do pixel interno
        cx = tx + w / W / 2
        cy = ty + h / H / 2
        bx, by = to_internal((int(cx), int(cy)), win)
        tol = max(1.0, W / w) + 1e-9      # janela menor que o canvas: erro de ate 1 px da janela
        assert abs(bx - ix) < tol and abs(by - iy) < tol


# ---------------- render_scaled ----------------

@pytest.mark.parametrize("win", [(480, 270), (1366, 768), (1000, 300), (300, 1000), (100, 50), (1, 1)])
def test_render_scaled_nao_levanta_e_mantem_tamanho(win):
    canvas = pygame.Surface((W, H))
    canvas.fill((200, 10, 10))
    screen = pygame.Surface(win)
    render_scaled(canvas, screen)
    assert screen.get_size() == win


def test_render_scaled_faixas_pretas_e_canvas_no_meio():
    canvas = pygame.Surface((W, H))
    canvas.fill((200, 10, 10))
    screen = pygame.Surface((1000, 300))
    screen.fill((9, 9, 9))
    render_scaled(canvas, screen)
    assert screen.get_at((0, 150))[:3] == (0, 0, 0)
    assert screen.get_at((999, 150))[:3] == (0, 0, 0)
    assert screen.get_at((500, 150))[:3] == (200, 10, 10)


def test_render_scaled_faixas_verticais_pretas():
    canvas = pygame.Surface((W, H))
    canvas.fill((200, 10, 10))
    screen = pygame.Surface((300, 1000))
    render_scaled(canvas, screen)
    assert screen.get_at((150, 0))[:3] == (0, 0, 0)
    assert screen.get_at((150, 999))[:3] == (0, 0, 0)
    assert screen.get_at((150, 500))[:3] == (200, 10, 10)


# ---------------- Display ----------------

def _key(key, mod=0):
    return pygame.event.Event(pygame.KEYDOWN, key=key, mod=mod)


def test_display_cria_janela_redimensionavel_no_tamanho_inicial(tela):
    d = Display("teste")
    assert d.size == display.START_SIZE
    assert not d.fullscreen
    assert "teste" in pygame.display.get_caption()[0]


def test_alternar_fullscreen_no_dummy_nao_levanta_e_volta(tela):
    d = Display()
    d.toggle_fullscreen()
    d.toggle_fullscreen()
    assert not d.fullscreen
    assert d.size == display.START_SIZE


def test_f11_alterna_e_consome_tecla(tela):
    d = Display()
    assert d.handle_key(_key(pygame.K_F11)) is True
    assert d.fullscreen is True
    assert d.handle_key(_key(pygame.K_F11)) is True
    assert d.fullscreen is False


@pytest.mark.parametrize("tecla", [pygame.K_RETURN, pygame.K_KP_ENTER])
def test_alt_enter_alterna(tela, tecla):
    d = Display()
    assert d.handle_key(_key(tecla, pygame.KMOD_ALT)) is True
    assert d.fullscreen is True


def test_enter_sem_alt_nao_alterna(tela):
    d = Display()
    assert d.handle_key(_key(pygame.K_RETURN, 0)) is False
    assert d.fullscreen is False


def test_esc_nao_alterna_nem_e_consumido(tela):
    d = Display()
    assert d.handle_key(_key(pygame.K_ESCAPE)) is False
    assert d.fullscreen is False
    d.toggle_fullscreen()
    assert d.handle_key(_key(pygame.K_ESCAPE)) is False
    assert d.fullscreen is True


def test_evento_que_nao_e_keydown_e_ignorado(tela):
    d = Display()
    ev = pygame.event.Event(pygame.KEYUP, key=pygame.K_F11, mod=0)
    assert d.handle_key(ev) is False
    assert not d.fullscreen


def test_falha_ao_entrar_em_fullscreen_continua_em_janela(tela, monkeypatch):
    d = Display()
    original = pygame.display.set_mode

    def quebrado(size, flags=0, *a, **k):
        if flags & pygame.FULLSCREEN:
            raise pygame.error("sem fullscreen")
        return original(size, flags, *a, **k)

    monkeypatch.setattr(pygame.display, "set_mode", quebrado)
    d.toggle_fullscreen()  # nao deve levantar
    assert d.fullscreen is False
    assert d.size == display.START_SIZE


def test_falha_total_ao_mudar_de_modo_nao_derruba(tela, monkeypatch):
    d = Display()

    def quebrado(*a, **k):
        raise pygame.error("falhou")

    monkeypatch.setattr(pygame.display, "set_mode", quebrado)
    d.toggle_fullscreen()
    assert d.fullscreen is False


def test_display_to_internal_usa_tamanho_real_da_superficie(tela):
    d = Display()
    x, y, _, _ = dest_rect(d.size)
    assert d.to_internal((x, y)) == (0, 0)
