"""Fonte da UI (T8.6): metricas, acentos sem '?', caractere ausente, fallback 5x7, cor e cache.

Escritos a partir de reports/T8.3 e T8.5 (secoes de testes pendentes). Headless.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
import pytest

from ui import font

ACENTOS = "ñ Ñ ç Ç ã õ ü ï á é í ó ú â ê ô à è"
AUSENTES = "& # @ ~ ^ ª º"


@pytest.fixture(autouse=True)
def restaura_fonte():
    yield
    font.use_ttf(None)
    font.use_bitmap(True)


def pixels(s: pygame.Surface) -> bytes:
    return pygame.image.tobytes(s, "RGBA")


def opacos(s: pygame.Surface) -> int:
    return pygame.mask.from_surface(s, 1).count()


# ------------------------------------------------------------------ bitmap
def test_bitmap_ativo_tem_maiuscula_de_10_e_linha_de_14():
    assert font.use_bitmap(True)
    assert font.CAP_H == 10 and font.LINE_H == 14


def test_largura_de_letra_e_positiva_e_cresce_com_o_texto():
    assert font.width("A") > 0
    assert font.width("AA") > font.width("A")
    assert font.width("") == 0


def test_escala_dois_e_mais_larga_que_escala_um():
    assert font.width("Chaoscats", 2) > font.width("Chaoscats", 1)
    assert font.width("Chaoscats", 3) > font.width("Chaoscats", 2)


def test_advance_conta_o_espaco_final_e_width_nao():
    assert font.advance("a ") > font.width("a ") or font.advance("a ") > font.width("a")
    assert font.advance("a") >= font.width("a")


@pytest.mark.parametrize("scale", [1, 2, 3])
def test_acentos_e_til_renderizam_sem_excecao_e_nao_sao_interrogacao(scale):
    interrog = pixels(font.render("?", (255, 255, 255), scale))
    for ch in ACENTOS.split():
        s = font.render(ch, (255, 255, 255), scale)
        assert font.width(ch, scale) > 0, ch
        assert opacos(s) > 0, ch
        assert pixels(s) != interrog, f"{ch!r} saiu como '?'"


def test_enhe_tem_til_e_difere_do_n_simples():
    assert pixels(font.render("ñ", (255, 255, 255))) != pixels(font.render("n", (255, 255, 255)))
    assert pixels(font.render("Ñ", (255, 255, 255))) != pixels(font.render("N", (255, 255, 255)))


@pytest.mark.parametrize("scale", [1, 2])
def test_i_trema_e_e_grave_diferem_das_letras_simples(scale):
    b = (255, 255, 255)
    for com, sem in (("ï", "i"), ("Ï", "I"), ("è", "e"), ("È", "E")):
        assert pixels(font.render(com, b, scale)) != pixels(font.render(sem, b, scale)), com


def test_enhe_na_fonte_5x7_tem_til_e_difere_do_n_simples():
    font.use_bitmap(False)
    assert pixels(font.render("ñ", (255, 255, 255))) != pixels(font.render("n", (255, 255, 255)))
    assert pixels(font.render("Ñ", (255, 255, 255))) != pixels(font.render("N", (255, 255, 255)))


def test_frase_portuguesa_completa_renderiza():
    s = font.render("Você não sabe: ação, coração, pingüim, ¿qué?", (255, 255, 255))
    assert s.get_width() > 50 and opacos(s) > 0


def test_caracteres_sem_glifo_proprio_nao_levantam_nem_viram_interrogacao():
    interrog = pixels(font.render("?", (255, 255, 255)))
    for ch in AUSENTES.split():
        s = font.render(ch, (255, 255, 255))
        assert pixels(s) != interrog, ch
        font.width(ch)


def test_emoji_tem_largura_zero_e_nao_desenha_nada():
    assert font.width("😀") == 0
    s = font.render("😀", (255, 255, 255))
    assert opacos(s) == 0
    surf = pygame.Surface((40, 20))
    surf.fill((0, 0, 0))
    before = pygame.image.tobytes(surf, "RGB")
    font.draw(surf, "😀", 2, 2, (255, 255, 255))
    assert pygame.image.tobytes(surf, "RGB") == before


def test_emoji_no_meio_do_texto_nao_muda_a_largura():
    assert font.width("a😀b") == font.width("ab")


# ------------------------------------------------------------------ cor e cache
def test_render_devolve_a_cor_pedida():
    cor = (200, 40, 90)
    s = font.render("HELLO", cor)
    achou = False
    for y in range(s.get_height()):
        for x in range(s.get_width()):
            r, g, b, a = s.get_at((x, y))
            if a > 0:
                assert r <= cor[0] and g <= cor[1] and b <= cor[2]
                achou = achou or (r, g, b) == cor
    assert achou, "nenhum pixel com a cor exata"


def test_cores_diferentes_dao_imagens_diferentes_e_o_cache_reusa_a_mesma():
    a1 = font.render("Gato", (255, 0, 0))
    a2 = font.render("Gato", (255, 0, 0))
    b = font.render("Gato", (0, 255, 0))
    assert a1 is a2
    assert b is not a1 and pixels(b) != pixels(a1)


def test_escala_diferente_nao_reaproveita_o_cache():
    assert font.render("Gato", (1, 2, 3), 1) is not font.render("Gato", (1, 2, 3), 2)


def test_draw_retorna_a_largura_e_alinha_pelo_topo_das_maiusculas():
    surf = pygame.Surface((200, 60), pygame.SRCALPHA)
    w = font.draw(surf, "HHH", 10, 20, (255, 255, 255))
    assert w == font.render("HHH", (255, 255, 255)).get_width()
    ys = [y for y in range(60) for x in range(200) if surf.get_at((x, y))[3] > 0]
    assert min(ys) == 20 and max(ys) == 20 + font.CAP_H - 1


def test_draw_alinha_centro_e_direita():
    surf = pygame.Surface((300, 40), pygame.SRCALPHA)
    w = font.width("HHH")
    font.draw(surf, "HHH", 150, 5, (255, 255, 255), 1, "right")
    xs = [x for x in range(300) for y in range(40) if surf.get_at((x, y))[3] > 0]
    assert max(xs) <= 150 and max(xs) >= 150 - 3
    assert min(xs) >= 150 - w - 1


def test_wrap_e_fit_respeitam_a_largura():
    for ln in font.wrap("um dois tres quatro cinco seis sete oito nove dez", 90):
        assert font.width(ln) <= 90
    assert font.width(font.fit("Arranhão Certeiro Supremo", 70)) <= 70
    assert font.fit("ok", 200) == "ok"


# ------------------------------------------------------------------ fallback 5x7
def test_sem_bitmap_volta_para_a_fonte_5x7():
    font.use_bitmap(False)
    assert font.CAP_H == 7
    assert font.width("A") > 0
    font.use_bitmap(True)
    assert font.CAP_H == 10


def test_fallback_5x7_acentos_sem_interrogacao_e_emoji_vazio():
    font.use_bitmap(False)
    interrog = pixels(font.render("?", (255, 255, 255)))
    for ch in ACENTOS.split():
        s = font.render(ch, (255, 255, 255))
        assert opacos(s) > 0, ch
        assert pixels(s) != interrog, ch
    assert font.width("😀") == 0
    assert opacos(font.render("😀", (255, 255, 255))) == 0


def test_fallback_5x7_ausentes_nao_levantam():
    font.use_bitmap(False)
    for ch in AUSENTES.split():
        font.render(ch, (255, 255, 255))
        font.width(ch)


def test_fallback_5x7_respeita_cor_e_escala():
    font.use_bitmap(False)
    s = font.render("A", (10, 200, 30), 2)
    cores = {tuple(s.get_at((x, y)))[:3] for x in range(s.get_width()) for y in range(s.get_height())
             if s.get_at((x, y))[3] > 0}
    assert cores == {(10, 200, 30)}
    assert font.width("A", 3) == 3 * font.width("A", 1)


def test_ttf_ausente_ou_none_mantem_a_fonte_atual():
    antes = font.CAP_H
    assert font.use_ttf(None) is False
    assert font.use_ttf("nao-existe.ttf") is False
    assert font.CAP_H == antes == 10
    assert font.width("A") > 0


def test_ttf_ausente_com_bitmap_desligado_mantem_5x7():
    font.use_bitmap(False)
    assert font.use_ttf("nao-existe.ttf") is False
    assert font.CAP_H == 7
