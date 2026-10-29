"""Testes do layout da UI (retangulos 960x540, hit test, mouse -> coordenadas internas).

Nao abre janela: `pygame.Rect` funciona sem display. Escritos a partir do comportamento
descrito em reports/T2.1-ui-duelo.md (resolucao interna 480x270, escala inteira maxima
que cabe, janela centralizada com barras).
"""
from __future__ import annotations

from itertools import combinations

import pygame
import pytest

from ui import layout as L

from ui.theme import H, W  # resolucao interna (T8.2: 960x540)

HAND_MAX = 7          # data/rules.json: duel.hand_max


def fixed_rects() -> dict[str, pygame.Rect]:
    r = {f"slot-{s}-{n}": L.slot_rect(s, n) for s in ("enemy", "player") for n in range(5)}
    r.update({f"leader-{s}": L.leader_rect(s) for s in ("enemy", "player")})
    r.update({"pass": L.pass_rect(), "turn": L.turn_rect(), "info": L.info_rect(),
              "log": L.log_rect(), "energy": L.energy_rect(), "message": L.message_rect(),
              "enemy_pile": L.enemy_pile_rect(), "pile": L.pile_rect()})
    r.update({f"taunt-{s}": L.leader_taunt_rect(s) for s in ("enemy", "player")})
    return r


def window_for(scale: int, extra: tuple[int, int] = (0, 0)) -> tuple[int, int]:
    return W * scale + extra[0], H * scale + extra[1]


def expected_transform(win: tuple[int, int]) -> tuple[int, int, int]:
    """Especificacao: maior escala inteira que cabe, imagem centralizada."""
    scale = max(1, min(win[0] // W, win[1] // H))
    return scale, (win[0] - W * scale) // 2, (win[1] - H * scale) // 2


# ---------------------------------------------------------------- sobreposicao
def test_slots_lideres_e_paineis_nao_se_sobrepoem():
    for (na, a), (nb, b) in combinations(fixed_rects().items(), 2):
        assert not a.colliderect(b), f"{na} {a} sobrepoe {nb} {b}"


@pytest.mark.parametrize("n", range(1, HAND_MAX + 1))
def test_cartas_da_mao_nao_se_sobrepoem_entre_si_nem_com_o_resto(n):
    hand = [L.hand_rect(i, n) for i in range(n)]
    if n <= 6:                          # com 7 cartas a mao e um leque (cartas se sobrepoem entre si)
        for a, b in combinations(hand, 2):
            assert not a.colliderect(b)
    for name, other in fixed_rects().items():
        for i in range(n):
            for h in (hand[i], L.hand_hit_rect(i, n)):          # em repouso e com a subida do hover
                assert not h.colliderect(other), f"mao {i}/{n} sobrepoe {name}"


@pytest.mark.parametrize("n", range(1, HAND_MAX + 1))
def test_mao_cabe_dentro_da_tela(n):
    screen = pygame.Rect(0, 0, W, H)
    for i in range(n):
        assert screen.contains(L.hand_rect(i, n))


def test_todos_os_retangulos_ficam_dentro_da_tela_interna():
    screen = pygame.Rect(0, 0, W, H)
    for name, r in fixed_rects().items():
        assert screen.contains(r), f"{name} {r} fora de 480x270"


def test_botoes_do_painel_final_nao_se_sobrepoem_e_ficam_dentro_do_painel():
    panel = L.final_panel()
    b = L.final_buttons()
    assert set(b) == {"again", "repeat"}
    assert not b["again"].colliderect(b["repeat"])
    for r in b.values():
        assert panel.contains(r)


# ---------------------------------------------------------------- hit test
def test_centro_de_cada_elemento_devolve_o_proprio_elemento():
    for side in ("enemy", "player"):
        for n in range(5):
            assert L.hit_test(L.slot_rect(side, n).center, 0) == ("slot", side, n)
        assert L.hit_test(L.leader_rect(side).center, 0) == ("leader", side)
    assert L.hit_test(L.pass_rect().center, 0) == ("pass",)


@pytest.mark.parametrize("n", range(1, HAND_MAX + 1))
def test_hit_test_da_mao_acerta_a_carta_certa(n):
    for i in range(n):
        assert L.hit_test(L.hand_rect(i, n).center, n) == ("hand", i)


def test_clicar_fora_de_tudo_nao_devolve_elemento():
    assert L.hit_test((-5, -5), 5) is None
    assert L.hit_test((W + 10, H + 10), 5) is None
    assert L.hit_test((L.info_rect().x + 2, L.info_rect().y + 2), 5) is None   # painel de info


def test_painel_final_so_responde_aos_botoes():
    for name, r in L.final_buttons().items():
        assert L.hit_test(r.center, 5, final=True) == (name,)
    assert L.hit_test(L.pass_rect().center, 5, final=True) is None
    assert L.hit_test(L.slot_rect("player", 0).center, 5, final=True) is None


def test_rect_of_devolve_o_retangulo_do_elemento():
    assert L.rect_of(("slot", "enemy", 3)) == L.slot_rect("enemy", 3)
    assert L.rect_of(("leader", "player")) == L.leader_rect("player")
    assert L.rect_of(("hand", 2), 4) == L.hand_rect(2, 4)
    assert L.rect_of(("pass",)) == L.pass_rect()


# ---------------------------------------------------------------- mouse -> interno
@pytest.mark.parametrize("scale", [1, 2, 3, 4])
def test_janela_em_escala_inteira_exata_converte_para_480x270(scale):
    win = window_for(scale)
    assert L.to_internal((0, 0), win) == (0, 0)
    assert L.to_internal((W * scale - 1, H * scale - 1), win) == (W - 1, H - 1)
    for ix, iy in [(0, 0), (1, 1), (100, 50), (240, 135), (479, 269)]:
        for dx in range(scale):          # qualquer pixel do bloco cai na mesma coordenada interna
            assert L.to_internal((ix * scale + dx, iy * scale + dx), win) == (ix, iy)


@pytest.mark.parametrize("scale", [1, 2, 3, 4])
@pytest.mark.parametrize("extra", [(200, 100), (0, 99), (101, 0), (37, 53)])
def test_janela_com_barras_centraliza_e_converte(scale, extra):
    win = window_for(scale, extra)
    s, ox, oy = expected_transform(win)
    assert s == scale
    assert L.view_transform(win) == (s, ox, oy)
    for ix, iy in [(0, 0), (7, 9), (240, 135), (479, 269)]:
        pos = (ox + ix * s + s // 2, oy + iy * s + s // 2)
        assert L.to_internal(pos, win) == (ix, iy)


@pytest.mark.parametrize("win", [(1920, 1080), (1920, 1000), (1440, 1200), (2560, 810),
                                 (1000, 1000), (1700, 600), (960, 540), (961, 541)])
def test_proporcoes_diferentes_usam_a_maior_escala_inteira_que_cabe(win):
    s, ox, oy = expected_transform(win)
    assert L.view_transform(win) == (s, ox, oy)
    assert max(1, s) * W <= win[0] and max(1, s) * H <= win[1]
    assert W * (s + 1) > win[0] or H * (s + 1) > win[1]
    # imagem centralizada: sobra igual dos dois lados (diferenca de no maximo 1 px)
    assert abs(ox - (win[0] - W * s - ox)) <= 1
    assert abs(oy - (win[1] - H * s - oy)) <= 1


def test_janela_menor_que_o_canvas_nao_quebra_e_usa_escala_1():
    s, _, _ = L.view_transform((300, 200))
    assert s == 1
    assert isinstance(L.to_internal((10, 10), (300, 200)), tuple)


@pytest.mark.parametrize("win", [(480, 270), (960, 540), (1440, 810), (1920, 1080),
                                 (1920, 1000), (1600, 1200), (800, 1000)])
def test_clique_no_centro_de_cada_elemento_pela_janela_acerta_o_elemento(win):
    s, ox, oy = expected_transform(win)
    targets = [(("slot", "player", 2), L.slot_rect("player", 2)),
               (("slot", "enemy", 4), L.slot_rect("enemy", 4)),
               (("leader", "enemy"), L.leader_rect("enemy")),
               (("pass",), L.pass_rect()),
               (("hand", 1), L.hand_rect(1, 3))]
    for elem, rect in targets:
        mouse = (ox + rect.centerx * s + s // 2, oy + rect.centery * s + s // 2)
        assert L.hit_test(L.to_internal(mouse, win), 3) == elem


def test_clique_nas_barras_nao_acerta_elemento():
    win = (1920, 1000)          # barras laterais de 240 px
    assert L.hit_test(L.to_internal((10, 500), win), 5) is None
    assert L.hit_test(L.to_internal((1915, 500), win), 5) is None


# ---------------------------------------------------------------- confirmacao de "Passar turno"
def test_botoes_sim_e_nao_ficam_na_tela_dentro_do_botao_passar_e_sem_se_sobrepor():
    screen = pygame.Rect(0, 0, W, H)
    yes, no = L.pass_yes_rect(), L.pass_no_rect()
    assert screen.contains(yes) and screen.contains(no)
    assert not yes.colliderect(no)
    assert yes.w > 0 and no.w > 0
    assert L.pass_rect().contains(yes) and L.pass_rect().contains(no)


def test_botoes_sim_e_nao_nao_sobrepoem_outros_elementos():
    for name, r in fixed_rects().items():
        if name == "pass":
            continue
        assert not L.pass_yes_rect().colliderect(r), f"sim sobrepoe {name}"
        assert not L.pass_no_rect().colliderect(r), f"nao sobrepoe {name}"
    for n in range(1, HAND_MAX + 1):
        for i in range(n):
            h = L.hand_rect(i, n)
            assert not L.pass_yes_rect().colliderect(h)
            assert not L.pass_no_rect().colliderect(h)


@pytest.mark.parametrize("scale", [1, 2, 3, 4])
def test_hit_test_com_confirmacao_devolve_sim_e_nao_em_todas_as_escalas(scale):
    win = window_for(scale)
    for rect, esperado in [(L.pass_yes_rect(), ("pass_yes",)), (L.pass_no_rect(), ("pass_no",))]:
        mouse = (rect.centerx * scale + scale // 2, rect.centery * scale + scale // 2)
        assert L.hit_test(L.to_internal(mouse, win), 3, confirm=True) == esperado


def test_sim_e_nao_so_existem_com_confirm_true():
    assert L.hit_test(L.pass_yes_rect().center, 3) == ("pass",)
    assert L.hit_test(L.pass_no_rect().center, 3) == ("pass",)


def test_rect_of_conhece_sim_e_nao():
    assert L.rect_of(("pass_yes",)) == L.pass_yes_rect()
    assert L.rect_of(("pass_no",)) == L.pass_no_rect()


def test_painel_final_ignora_a_confirmacao():
    assert L.hit_test(L.pass_yes_rect().center, 3, final=True, confirm=True) is None
