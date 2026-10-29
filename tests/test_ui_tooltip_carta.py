"""Tooltip, carta de duelo, badges e marca de Provocar (T8.6). Headless, sem sorteio nao controlado.

Escritos a partir de reports/T7.3, T8.2, T8.3 e T8.5. O estado do duelo e montado so pela API
publica de `tests/duel_helpers` e do controlador da UI.
"""
from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
import pytest

from core.types import Card
from duel_helpers import duel, fc, load, mk
from ui import layout as L
from ui import render, sprites, tooltip as TIP
from ui.controller import Controller
from ui.render import UIState, draw_card, draw_frame, draw_taunt_mark, keyword_badges, effect_badges
from ui.theme import H, W

PLAYER, ENEMY = "player", "enemy"
TELA = pygame.Rect(0, 0, W, H)


@pytest.fixture(scope="module")
def content():
    return load()


def ctrl_with(content, seed: int = 1, enemy_id: str | None = None, **kw) -> Controller:
    c = Controller(content, seed, ai_delay=0.0, enemy_id=enemy_id)
    c.duel = duel(content, **kw)
    c.phase = "play"
    c.beats.clear()
    c.cur = None
    c.fx = []
    c.toast = None
    c.banner = None
    c.refresh()
    return c


def gato(**kw) -> Card:
    base = dict(kind="cat", ref="g1", name="g1", cost=2, atk=3, hp=4, keywords=(), breed="siames",
                breed_name="Siamês", cat_name="Mimi", sex="F", nature="bravo", iv_atk=4, iv_hp=2)
    base.update(kw)
    return Card(**base)


def efeito(**kw) -> Card:
    base = dict(kind="effect", ref="arranhao-certeiro", name="Arranhão Certeiro", cost=1,
                actions=({"tipo": "dano", "valor": 2, "alvo": "gato_inimigo"},))
    base.update(kw)
    return Card(**base)


def espirito(**kw) -> Card:
    base = dict(kind="special", ref="sombra-miuda", name="Sombra Miúda", cost=3, atk=2, hp=2,
                keywords=("investida",), text="Uma sombra.")
    base.update(kw)
    return Card(**base)


def texto(lines) -> str:
    out = []
    for segs in lines:
        parts = []
        for s in segs:
            if not s:
                continue
            parts.append(str(s[1]) if s[0] == "*wrap" else ("" if s[0] == "*stars" else str(s[0])))
        out.append("".join(parts))
    return "\n".join(out)


# ------------------------------------------------------------------ hover_elem
def test_hover_em_slot_vazio_nao_mostra_tooltip(content):
    c = ctrl_with(content, player_hand=[mk(1, 1)])
    for side in (PLAYER, ENEMY):
        assert TIP.hover_elem(c, L.slot_rect(side, 2).center) is None


def test_hover_em_gato_do_campo_devolve_o_slot(content):
    c = ctrl_with(content, player_field={2: fc(2, 3)}, enemy_field={4: fc(1, 1)})
    assert TIP.hover_elem(c, L.slot_rect(PLAYER, 2).center) == ("slot", PLAYER, 2)
    assert TIP.hover_elem(c, L.slot_rect(ENEMY, 4).center) == ("slot", ENEMY, 4)


def test_hover_enquanto_arrasta_nao_mostra_tooltip(content):
    c = ctrl_with(content, player_hand=[mk(1, 1)], player_field={2: fc(2, 3)})
    assert TIP.hover_elem(c, L.slot_rect(PLAYER, 2).center, dragging=True) is None
    assert TIP.hover_elem(c, L.hand_rect(0, 1).center, dragging=True) is None


def test_hover_na_fase_do_dado_nao_mostra_tooltip(content):
    c = ctrl_with(content, player_hand=[mk(1, 1)], player_field={2: fc(2, 3)})
    c.phase = "dice"
    assert TIP.hover_elem(c, L.slot_rect(PLAYER, 2).center) is None
    assert TIP.hover_elem(c, L.hand_rect(0, 1).center) is None


def test_hover_fora_de_tudo_e_none(content):
    c = ctrl_with(content, player_hand=[mk(1, 1)])
    assert TIP.hover_elem(c, (-50, -50)) is None
    assert TIP.hover_elem(c, (3, 3)) is None


def test_hover_na_mao_devolve_a_carta_para_1_a_7_cartas(content):
    for n in range(1, 8):
        c = ctrl_with(content, player_hand=[mk(1, 1, name=f"c{n}-{i}") for i in range(n)])
        for i in range(n):
            e = TIP.hover_elem(c, L.hand_rect(i, n).center)
            assert e is not None and e[0] == "hand" and 0 <= e[1] < n


def test_hover_na_ponta_da_mao_com_7_cartas_pega_a_carta_do_proprio_indice(content):
    c = ctrl_with(content, player_hand=[mk(1, 1, name=f"x{i}") for i in range(7)])
    assert TIP.hover_elem(c, L.hand_rect(0, 7).topleft) == ("hand", 0)
    assert TIP.hover_elem(c, (L.hand_rect(6, 7).right - 1, L.hand_rect(6, 7).bottom - 1)) == ("hand", 6)


def test_hover_no_lider_do_jogador_nao_tem_tooltip_e_no_inimigo_com_id_tem(content):
    c = ctrl_with(content, enemy_id="tonho-sem-sorte")
    assert TIP.hover_elem(c, L.leader_rect(PLAYER).center) is None
    e = TIP.hover_elem(c, L.leader_rect(ENEMY).center)
    assert e == ("leader", ENEMY)
    lines, side, anchor = TIP.lines_for(c, e)
    assert "Tonho" in texto(lines) and side == ENEMY


def test_hover_no_lider_inimigo_sem_identidade_nem_regra_e_none(content):
    c = ctrl_with(content)
    assert c.enemy is None
    assert TIP.hover_elem(c, L.leader_rect(ENEMY).center) is None


# ------------------------------------------------------------------ tooltip_lines
def test_tooltip_do_gato_mostra_natureza_sexo_e_iv(content):
    c = ctrl_with(content)
    t = texto(TIP.tooltip_lines(c, gato(), None, PLAYER))
    assert "Mimi" in t and "Natureza" in t and "Bravo" in t
    assert "Sexo" in t and "Fêmea" in t.replace("Femea", "Fêmea")
    assert "IV ATK" in t and "4/5" in t and "IV HP" in t and "2/5" in t
    assert "Raça: Siamês" in t


def test_tooltip_do_gato_macho_e_de_cada_natureza(content):
    c = ctrl_with(content)
    for nat in ("calmo", "bravo", "agitado"):
        t = texto(TIP.tooltip_lines(c, gato(nature=nat, sex="M"), None, PLAYER))
        assert content.natures[nat]["nome"] in t
        assert "Macho" in t


def test_tooltip_do_gato_sem_iv_nem_natureza_nao_quebra_e_nao_cita_iv(content):
    c = ctrl_with(content)
    t = texto(TIP.tooltip_lines(c, mk(2, 2), None, PLAYER))
    assert "IV" not in t and "Natureza" not in t


def test_tooltip_inclui_texto_das_keywords(content):
    c = ctrl_with(content)
    t = texto(TIP.tooltip_lines(c, gato(keywords=("provocar", "investida")), None, PLAYER))
    assert "Provocar" in t and "Investida" in t
    assert content.keywords["provocar"]["texto"][:20] in t


def test_tooltip_do_campo_usa_os_status_atuais(content):
    c = ctrl_with(content)
    f = fc(5, 2, hp_max=6)
    f.card = gato(atk=3, hp=6)
    t = texto(TIP.tooltip_lines(c, f.card, f, PLAYER))
    assert "ATK 5" in t and "2/6" in t


def test_tooltip_de_efeito_e_de_espirito(content):
    c = ctrl_with(content)
    t = texto(TIP.tooltip_lines(c, efeito(), None, PLAYER))
    assert "CARTA DE EFEITO" in t and "Custo" in t
    t = texto(TIP.tooltip_lines(c, espirito(), None, PLAYER))
    assert "ESPÍRITO" in t and "Só existe nesta run" in t


def test_wrap_lines_expande_o_wrap_e_respeita_a_largura(content):
    from ui import font
    longo = "palavra " * 60
    out = TIP.wrap_lines([[("*wrap", longo, (255, 255, 255))], [("curta", (1, 2, 3))]])
    assert len(out) > 3
    for segs in out[:-1]:
        assert font.width(segs[0][0]) <= TIP.TIP_W - 2 * TIP.PAD
    assert out[-1] == [("curta", (1, 2, 3))]


def test_box_height_aceita_inteiro_e_lista_e_conta_o_titulo():
    assert TIP.box_height(3) == 2 * TIP.PAD + 3 * TIP.LINE_H
    com_titulo = [[("Nome", (1, 1, 1))], [("a", (1, 1, 1))]]
    sem_titulo = [[("a", (1, 1, 1)), ("b", (1, 1, 1))], [("c", (1, 1, 1))]]
    assert TIP.box_height(com_titulo) == TIP.box_height(sem_titulo) + (TIP.TITLE_H - TIP.LINE_H)
    assert TIP.box_height([]) == 2 * TIP.PAD


# ------------------------------------------------------------------ place
@pytest.mark.parametrize("h", [40, 150, 300, 480])
def test_place_de_slots_fica_dentro_da_tela(h):
    for side in (PLAYER, ENEMY):
        for n in range(5):
            r = TIP.place("slot", L.slot_rect(side, n), h)
            assert TELA.contains(r), (side, n, r)
            assert r.size == (TIP.TIP_W, h)


@pytest.mark.parametrize("h", [40, 150, 300, 480])
def test_place_da_mao_de_1_a_7_cartas_fica_dentro_da_tela(h):
    for n in range(1, 8):
        for i in range(n):
            r = TIP.place("hand", L.hand_hit_rect(i, n), h)
            assert TELA.contains(r), (n, i, r)


@pytest.mark.parametrize("h", [40, 150, 300])
def test_place_do_lider_fica_dentro_da_tela(h):
    for side in (PLAYER, ENEMY):
        assert TELA.contains(TIP.place("leader", L.leader_rect(side), h))


def test_place_da_mao_fica_acima_da_carta_quando_cabe():
    anchor = L.hand_hit_rect(3, 7)
    r = TIP.place("hand", anchor, 120)
    assert r.bottom <= anchor.y


def test_place_do_campo_nao_cobre_o_slot_ancora():
    for n in range(5):
        a = L.slot_rect(PLAYER, n)
        assert not TIP.place("slot", a, 200).colliderect(a)


def test_place_aceita_largura_customizada():
    r = TIP.place("slot", L.slot_rect(PLAYER, 4), 100, w=200)
    assert r.w == 200 and TELA.contains(r)


def test_lines_for_de_todos_os_elementos_cabe_na_tela(content):
    c = ctrl_with(content, enemy_id="berenice-da-matilha",
                  player_hand=[mk(1, 1, name=f"m{i}") for i in range(7)],
                  player_field={n: fc(2, 2, kw=("provocar", "robusto")) for n in range(5)},
                  enemy_field={n: fc(1, 3, kw=("investida",)) for n in range(5)})
    elems = [("hand", i) for i in range(7)] + [("slot", s, n) for s in (PLAYER, ENEMY) for n in range(5)]
    elems.append(("leader", ENEMY))
    for e in elems:
        got = TIP.lines_for(c, e)
        assert got is not None, e
        lines, side, anchor = got
        assert TELA.contains(TIP.place(e[0], anchor, TIP.box_height(lines))), e


def test_lines_for_de_indice_invalido_ou_slot_vazio_e_none(content):
    c = ctrl_with(content, player_hand=[mk(1, 1)])
    assert TIP.lines_for(c, ("hand", 5)) is None
    assert TIP.lines_for(c, ("slot", PLAYER, 0)) is None
    assert TIP.lines_for(c, ("outro", 1)) is None


# ------------------------------------------------------------------ draw_card
def desenha(card: Card, atk=3, hp=4, hp_max=4, kws=(), **kw) -> pygame.Surface:
    surf = pygame.Surface((160, 160))
    surf.fill((0, 0, 0))
    r = pygame.Rect(20, 16, 120, 124)
    draw_card(surf, r, card, atk, hp, hp_max, kws, **kw)
    return surf


@pytest.fixture
def sem_sprites(monkeypatch):
    monkeypatch.setattr(sprites, "get", lambda *a, **k: None)


@pytest.mark.parametrize("fabrica", [gato, espirito, efeito])
def test_draw_card_com_sprite_nao_levanta_e_pinta(fabrica):
    surf = desenha(fabrica(), kws=("provocar",))
    assert len({surf.get_at((x, y))[:3] for x in range(20, 140, 3) for y in range(16, 140, 3)}) > 5


@pytest.mark.parametrize("fabrica", [gato, espirito, efeito])
def test_draw_card_sem_sprite_usa_silhueta_e_nao_levanta(fabrica, sem_sprites):
    surf = desenha(fabrica(), kws=("provocar",))
    assert len({surf.get_at((x, y))[:3] for x in range(20, 140, 3) for y in range(16, 140, 3)}) > 5


@pytest.mark.parametrize("fabrica", [gato, espirito, efeito])
def test_draw_card_com_e_sem_sprite_diferem(fabrica, monkeypatch):
    a = pygame.image.tobytes(desenha(fabrica()), "RGB")
    monkeypatch.setattr(sprites, "get", lambda *a_, **k: None)
    b = pygame.image.tobytes(desenha(fabrica()), "RGB")
    assert a != b


def test_draw_card_nao_exige_iv_nem_natureza_nem_sexo():
    nu = Card(kind="cat", ref="x", name="x", cost=1, atk=1, hp=1, breed="persa")
    assert nu.iv_atk is None
    desenha(nu)
    desenha(nu, kws=("provocar", "investida", "primeira-patada", "robusto"))


def test_draw_card_de_gato_de_raca_desconhecida_e_gato_sem_raca_nao_levanta():
    desenha(gato(breed="raca-inexistente"))
    desenha(gato(breed=None, breed_name=None, cat_name=None))


def test_draw_card_nao_mostra_iv_natureza_nem_sexo_na_carta():
    """A carta limpa nao depende do IV/natureza/sexo: mudar so isso nao muda um pixel."""
    a = pygame.image.tobytes(desenha(gato(iv_atk=1, iv_hp=1, nature="calmo", sex="M")), "RGB")
    b = pygame.image.tobytes(desenha(gato(iv_atk=5, iv_hp=5, nature="agitado", sex="F")), "RGB")
    assert a == b


def test_draw_card_machucado_e_com_buff_diferem_do_normal():
    normal = pygame.image.tobytes(desenha(gato(), 3, 4, 4), "RGB")
    machucado = pygame.image.tobytes(desenha(gato(), 3, 1, 4), "RGB")
    buff = pygame.image.tobytes(desenha(gato(), 5, 4, 4, atk_bonus=2), "RGB")
    assert len({normal, machucado, buff}) == 3


def test_draw_card_do_inimigo_difere_do_do_jogador():
    assert (pygame.image.tobytes(desenha(gato(), enemy=True), "RGB")
            != pygame.image.tobytes(desenha(gato()), "RGB"))


def test_draw_card_nao_pinta_fora_do_retangulo():
    surf = desenha(gato(), kws=("provocar", "investida", "primeira-patada", "robusto"))
    r = pygame.Rect(20, 16, 120, 124)
    for x in range(160):
        for y in range(160):
            if not r.collidepoint(x, y):
                assert surf.get_at((x, y))[:3] == (0, 0, 0), (x, y)


# ------------------------------------------------------------------ badges
KWS = ["provocar", "investida", "primeira-patada", "robusto"]


def test_uma_badge_por_keyword_na_mesma_ordem():
    for n in range(0, 5):
        b = keyword_badges(tuple(KWS[:n]))
        assert len(b) == n
        assert [x[0] for x in b] == KWS[:n]


def test_badge_de_keyword_tem_letra_e_cor():
    for item in keyword_badges(tuple(KWS)):
        icon, cor, letra = item
        assert len(cor) == 3 and letra


def test_keyword_desconhecida_ainda_gera_badge_com_inicial():
    assert keyword_badges(("zumbi",))[0][2] == "Z"


def test_badges_de_efeito_nao_repetem_tipos():
    card = efeito(actions=({"tipo": "dano", "valor": 1}, {"tipo": "dano", "valor": 2},
                           {"tipo": "cura", "valor": 1}))
    b = effect_badges(card)
    assert [x[0] for x in b] == ["acao-dano", "acao-cura"]
    assert effect_badges(efeito(actions=())) == []
    assert effect_badges(efeito(actions=({"tipo": "tipo-novo"},))) == []


def test_draw_badges_desenha_no_maximo_4_e_na_lateral_direita():
    surf = pygame.Surface((160, 160))
    surf.fill((0, 0, 0))
    art = pygame.Rect(20, 16, 118, 96)
    render.draw_badges(surf, art, keyword_badges(tuple(KWS)) + keyword_badges(("provocar",)))
    pintados = [(x, y) for x in range(160) for y in range(160) if surf.get_at((x, y))[:3] != (0, 0, 0)]
    assert pintados
    assert min(x for x, _ in pintados) >= art.right - render.BADGE - 3 - 1
    assert max(y for _, y in pintados) <= art.y + 4 + (render.BADGE + 2) * 4


def test_badge_sem_icone_cai_na_letra(sem_sprites):
    surf = pygame.Surface((40, 40))
    surf.fill((0, 0, 0))
    render.badge(surf, 5, 5, ("provocar", (200, 50, 50), "P"))
    assert (200, 50, 50) in {surf.get_at((x, y))[:3] for x in range(40) for y in range(40)}


# ------------------------------------------------------------------ marca de Provocar / rect
def mudou(antes: pygame.Surface, depois: pygame.Surface) -> bool:
    return pygame.image.tobytes(antes, "RGB") != pygame.image.tobytes(depois, "RGB")


def tela_preta() -> pygame.Surface:
    s = pygame.Surface((W, H))
    s.fill((0, 0, 0))
    return s


def test_marca_de_provocar_so_aparece_no_lado_que_tem_gato_com_provocar(content):
    c = ctrl_with(content, enemy_field={1: fc(1, 3, kw=("provocar",))}, player_field={2: fc(1, 1)})
    s = tela_preta()
    draw_taunt_mark(s, c, ENEMY)
    r = L.leader_taunt_rect(ENEMY)
    assert any(s.get_at((x, y))[:3] != (0, 0, 0) for x in range(r.x, r.right) for y in range(r.y, r.bottom))
    s = tela_preta()
    draw_taunt_mark(s, c, PLAYER)
    assert not mudou(s, tela_preta())


def test_marca_de_provocar_do_jogador_e_sem_provocar_nenhum(content):
    c = ctrl_with(content, player_field={0: fc(1, 3, kw=("provocar",))})
    s = tela_preta()
    draw_taunt_mark(s, c, PLAYER)
    assert mudou(s, tela_preta())
    s = tela_preta()
    draw_taunt_mark(s, c, ENEMY)
    assert not mudou(s, tela_preta())


def test_marca_de_provocar_nao_pinta_fora_do_seu_retangulo(content):
    c = ctrl_with(content, enemy_field={0: fc(1, 3, kw=("provocar",))})
    s = tela_preta()
    draw_taunt_mark(s, c, ENEMY)
    r = L.leader_taunt_rect(ENEMY)
    for x in range(0, W, 2):
        for y in range(0, H, 2):
            if not r.collidepoint(x, y):
                assert s.get_at((x, y))[:3] == (0, 0, 0), (x, y)


def test_marca_de_provocar_funciona_sem_icone(content, sem_sprites):
    c = ctrl_with(content, enemy_field={0: fc(1, 3, kw=("provocar",))})
    draw_taunt_mark(tela_preta(), c, ENEMY)


def test_marca_de_provocar_some_quando_o_gato_com_provocar_morre(content):
    c = ctrl_with(content, enemy_field={0: fc(1, 3, kw=("provocar",)), 1: fc(1, 1)})
    s = tela_preta()
    draw_taunt_mark(s, c, ENEMY)
    assert mudou(s, tela_preta())
    c.duel.sides[ENEMY].field[0] = None
    c.refresh()
    s = tela_preta()
    draw_taunt_mark(s, c, ENEMY)
    assert not mudou(s, tela_preta())


@pytest.mark.parametrize("side", [PLAYER, ENEMY])
def test_leader_taunt_rect_fica_a_direita_da_placa_e_nao_toca_nada(side):
    r = L.leader_taunt_rect(side)
    assert r.x >= 634 and TELA.contains(r)
    outros = [L.slot_rect(s, n) for s in (PLAYER, ENEMY) for n in range(5)]
    outros += [L.pass_rect(), L.turn_rect(), L.info_rect(), L.log_rect(), L.message_rect(),
               L.enemy_pile_rect(), L.pile_rect(), L.energy_rect(), L.leader_rect(side),
               L.leader_hp_rect(side), L.leader_name_rect(side)]
    for o in outros:
        assert not r.colliderect(o), o


@pytest.mark.parametrize("side", [PLAYER, ENEMY])
def test_leader_name_rect_fica_a_esquerda_da_placa(side):
    n = L.leader_name_rect(side)
    assert n.right <= 364 and n.x >= 0
    for s in (PLAYER, ENEMY):
        for k in range(5):
            assert not n.colliderect(L.slot_rect(s, k))


# ------------------------------------------------------------------ toast
def test_draw_toast_so_desenha_com_toast_e_cabe_na_faixa(content):
    c = ctrl_with(content)
    s = tela_preta()
    render.draw_toast(s, c)
    assert not mudou(s, tela_preta())
    from ui.controller import Toast
    c.toast = Toast("Energia insuficiente: faltam 2", "error")
    s = tela_preta()
    render.draw_toast(s, c)
    assert mudou(s, tela_preta())
    r = L.toast_rect(100)
    assert TELA.contains(r)
    ys = [y for x in range(W) for y in range(H) if s.get_at((x, y))[:3] != (0, 0, 0)]
    assert min(ys) >= r.y - 4 and max(ys) <= r.bottom + 4


@pytest.mark.parametrize("kind", ["error", "warn", "info"])
def test_draw_toast_aceita_todos_os_tipos_e_textos_longos(content, kind):
    from ui.controller import Toast
    c = ctrl_with(content)
    c.toast = Toast("texto muito comprido " * 12, kind)
    s = tela_preta()
    render.draw_toast(s, c)
    xs = [x for x in range(W) for y in range(0, H, 2) if s.get_at((x, y))[:3] != (0, 0, 0)]
    assert min(xs) >= 0 and max(xs) < W


def test_toast_rect_fica_entre_os_campos_e_centrado():
    for w in (40, 200, 620):
        r = L.toast_rect(w)
        assert r.w == w and abs(r.centerx - W // 2) <= 200 and TELA.contains(r)
        assert r.bottom <= L.slot_rect(PLAYER, 0).bottom and r.y >= L.slot_rect(ENEMY, 0).y


# ------------------------------------------------------------------ frames completos com hover
def test_draw_frame_com_mouse_sobre_cada_mao_slot_e_lider_nao_levanta(content):
    for n in (1, 4, 7):
        c = ctrl_with(content, enemy_id="irmaos-pimenta",
                      player_hand=[mk(1, 1, name=f"h{n}-{i}") for i in range(n)],
                      player_field={0: fc(2, 2, kw=("provocar",)), 3: fc(1, 1)},
                      enemy_field={1: fc(3, 3, kw=("robusto",))})
        canvas = pygame.Surface((W, H))
        pts = [L.hand_rect(i, n).center for i in range(n)] + [L.hand_rect(i, n).topleft for i in range(n)]
        pts += [L.leader_rect(s).center for s in (PLAYER, ENEMY)]
        pts += [L.slot_rect(s, k).center for s in (PLAYER, ENEMY) for k in range(5)]
        for p in pts:
            draw_frame(canvas, c, UIState(t=0.3, mouse=p))
