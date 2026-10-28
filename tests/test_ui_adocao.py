"""Testes da UI de Adocao pos-run, doacao e backup do NOVO JOGO (T5.10), sem janela.

Escritos a partir de reports/T5.9-ui-adocao.md e do pedido do Renatho. Estado final conferido
na API publica do core (`read_save`, `donation_value`, `has_pending_adoption`).
"""
from __future__ import annotations

import dataclasses
import os
from itertools import combinations
from pathlib import Path
from random import Random
from types import SimpleNamespace

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

import ui.hub_controller as hub_mod
from core import (create_adoption, donation_value, has_pending_adoption, new_game, read_save,
                  write_save)
from ui import layout_hub as LH
from ui.controller import load_game_content
from ui.hub_controller import HubController
from ui.render import UIState
from ui.render_hub import draw_hub_frame
from ui.scenes_hub import make
from ui.theme import H, W

SEED = 7
SEM_GATOS = "Nenhum gato para adotar desta vez"
MANTER_12 = "Precisa manter 12 adultos disponíveis."


@pytest.fixture(scope="module")
def content():
    return load_game_content()


# ------------------------------------------------------------------ helpers
def montar_oferta(content, save, n: int, ivs: list[tuple[int, int]] | None = None) -> list[str]:
    """Poe uma oferta pendente de exatamente n gatos (clones com ids novos) no save."""
    create_adoption(content, save, Random(SEED), "vitoria", 6)
    assert has_pending_adoption(save)
    base = save.pending_adoption["cats"][0]
    cats = []
    for i in range(n):
        c = dataclasses.replace(base)
        c.id = f"c-{save.next_cat_id:06d}"
        save.next_cat_id += 1
        c.iv_atk, c.iv_hp = (ivs[i] if ivs else (2, 2))
        cats.append(c)
    save.pending_adoption["cats"] = cats
    return [c.id for c in cats]


def hub_com_oferta(content, tmp_path: Path, n: int, ivs=None, *, abrir: bool = True):
    p = tmp_path / "save.json"
    s = new_game(content, Random(SEED))
    ids = montar_oferta(content, s, n, ivs)
    write_save(s, p)
    h = HubController(content, p, SEED, ai_delay=0.0)
    if abrir:
        h.click(("menu", "continue"))
        assert h.mode == "adocao"
    return h, p, ids


def hub_memoria_com_oferta(content, n: int, ivs=None) -> HubController:
    h = HubController(content, None, SEED, ai_delay=0.0)
    h.adopt_save(new_game(content, Random(SEED)))
    montar_oferta(content, h.save, n, ivs)
    assert h.open_pending_adoption()
    return h


def revelar_todos(h: HubController) -> None:
    h.click(("reveal_all",))


def save_grande(content, n: int):
    s = new_game(content, Random(SEED))
    base = list(s.cats)
    i = 0
    while len(s.cats) < n:
        c = dataclasses.replace(base[i % len(base)])
        c.id = f"c-{s.next_cat_id:06d}"
        s.next_cat_id += 1
        s.cats.append(c)
        i += 1
    return s


def caminho_invalido(tmp_path: Path) -> Path:
    arq = tmp_path / "arquivo"
    arq.write_text("x")
    return arq / "sub" / "save.json"


class RunFalsa:
    """Run encerrada (so o que o hub le); o hub chama click/update/hit nela."""
    def __init__(self, result, nodes, abandoned=False):
        self.screen = "finished"
        self.run = SimpleNamespace(result=result, nodes_cleared=nodes)
        self.abandoned = abandoned
        self.end_line = None

    def click(self, elem): ...
    def update(self, dt): ...


def espiar(monkeypatch):
    chamadas = {"write": 0, "create": []}
    real_write, real_create = hub_mod.write_save, hub_mod.create_adoption

    def write(*a, **k):
        chamadas["write"] += 1
        return real_write(*a, **k)

    def create(content, save, rng, result, nodes):
        chamadas["create"].append((result, nodes))
        return real_create(content, save, rng, result, nodes)

    monkeypatch.setattr(hub_mod, "write_save", write)
    monkeypatch.setattr(hub_mod, "create_adoption", create)
    return chamadas


# ------------------------------------------------------------------ fim da run
@pytest.mark.parametrize("result,nodes,abandono,esperado", [
    ("vitoria", 6, False, "vitoria"),
    ("derrota", 4, False, "derrota"),
    ("derrota", 4, True, "abandono"),
])
def test_fim_da_run_cria_oferta_e_grava_uma_unica_vez(content, tmp_path, monkeypatch,
                                                      result, nodes, abandono, esperado):
    h = HubController(content, tmp_path / "save.json", SEED, ai_delay=0.0)
    h.click(("menu", "new_game"))
    chamadas = espiar(monkeypatch)
    h.rc, h.mode = RunFalsa(result, nodes, abandono), "run"
    h.click(None)
    assert chamadas["create"] == [(esperado, nodes)]
    assert chamadas["write"] == 1
    assert h.mode == "adocao" and h.rc is None
    s = read_save(tmp_path / "save.json", content)
    assert has_pending_adoption(s)
    assert s.pending_adoption["result"] == esperado and s.pending_adoption["nodes_cleared"] == nodes


def test_abandono_real_chama_create_adoption_com_abandono(content, tmp_path, monkeypatch):
    h = HubController(content, tmp_path / "save.json", SEED, ai_delay=0.0)
    h.click(("menu", "new_game"))
    h.click(("start",))
    chamadas = espiar(monkeypatch)
    h.key_escape()
    h.click(("quit_yes",))
    assert chamadas["create"] and chamadas["create"][0][0] == "abandono"
    assert chamadas["write"] == 1


def test_oferta_com_zero_gatos_mostra_aviso_e_volta_a_colecao(content, tmp_path):
    h = HubController(content, tmp_path / "save.json", SEED, ai_delay=0.0)
    h.click(("menu", "new_game"))
    h.click(("start",))
    h.key_escape()
    h.click(("quit_yes",))                    # 0 nos vencidos: sem gatos
    assert h.mode == "resultado"
    assert SEM_GATOS in h.result_detail
    assert not has_pending_adoption(read_save(tmp_path / "save.json", content))
    draw_hub_frame(pygame.Surface((W, H)), h, UIState())
    h.click(h.hit(LH.result_button().center))
    assert h.mode == "colecao"


# ------------------------------------------------------------------ revelar, paginar
def test_cartoes_comecam_escondidos_e_revelar_um_libera_so_ele(content):
    h = hub_memoria_com_oferta(content, 3)
    a = h.adopt
    ids = a.visible_ids()
    assert a.revealed == set() and not a.all_revealed()
    assert h.hit(LH.adopt_card(1).center) == ("reveal", ids[1])
    h.click(h.hit(LH.adopt_card(1).center))
    assert a.revealed == {ids[1]}
    assert h.hit(LH.adopt_buttons(1)["adopt"].center) == ("adopt", ids[1])
    assert h.hit(LH.adopt_buttons(1)["donate"].center) == ("donate", ids[1])
    assert h.hit(LH.adopt_card(0).center) == ("reveal", ids[0])


def test_adotar_ou_doar_cartao_escondido_e_ignorado(content):
    h = hub_memoria_com_oferta(content, 2)
    cid = h.adopt.visible_ids()[0]
    n = len(h.save.cats)
    h.click(("adopt", cid))
    h.click(("donate", cid))
    assert len(h.save.cats) == n and h.save.coins == 0 and len(h.adopt.cats()) == 2


def test_revelar_todos(content):
    h = hub_memoria_com_oferta(content, 6)
    revelar_todos(h)
    assert h.adopt.all_revealed()
    assert h.hit(LH.adopt_nav()["reveal_all"].center) == ("reveal_all",)


@pytest.mark.parametrize("n,paginas,primeira", [(1, 1, 1), (4, 1, 4), (5, 2, 4), (9, 3, 4)])
def test_paginacao_4_por_pagina(content, n, paginas, primeira):
    h = hub_memoria_com_oferta(content, n)
    a = h.adopt
    assert a.pages == paginas and a.paged == (paginas > 1)
    assert len(a.visible()) == primeira
    ids = [c.id for c in a.cats()]
    vistos = list(a.visible_ids())
    for _ in range(paginas - 1):
        h.click(("page", 1))
        vistos += a.visible_ids()
    assert vistos == ids
    h.click(("page", 1))                      # nao passa da ultima
    assert a.page == paginas - 1
    for _ in range(paginas + 2):
        h.click(("page", -1))
    assert a.page == 0
    h.scroll(1)
    assert a.page == (1 if paginas > 1 else 0)


def test_botoes_de_pagina_so_respondem_com_mais_de_uma_pagina(content):
    h4 = hub_memoria_com_oferta(content, 4)
    assert h4.hit(LH.adopt_nav()["next"].center) is None
    h5 = hub_memoria_com_oferta(content, 5)
    assert h5.hit(LH.adopt_nav()["next"].center) == ("page", 1)
    assert h5.hit(LH.adopt_nav()["prev"].center) == ("page", -1)


# ------------------------------------------------------------------ adotar e doar
def test_adotar_coloca_na_colecao_e_regrava_o_save(content, tmp_path):
    h, p, ids = hub_com_oferta(content, tmp_path, 3)
    antes = len(read_save(p, content).cats)
    revelar_todos(h)
    h.click(("adopt", ids[0]))
    s = read_save(p, content)
    assert len(s.cats) == antes + 1 and ids[0] in {c.id for c in s.cats}
    assert [c.id for c in s.pending_adoption["cats"]] == ids[1:]
    assert h.mode == "adocao"


def test_doar_soma_moedas_igual_ao_valor_e_regrava_o_save(content, tmp_path):
    h, p, ids = hub_com_oferta(content, tmp_path, 3, ivs=[(5, 5), (1, 1), (3, 2)])
    cats = {c.id: c for c in h.save.pending_adoption["cats"]}
    revelar_todos(h)
    total = 0
    for cid in ids[:2]:
        v = donation_value(content, cats[cid])
        assert v > 0
        h.click(("donate", cid))
        total += v
        s = read_save(p, content)
        assert s.coins == total and h.adopt.coins == total
        assert cid not in {c.id for c in s.cats}
    assert f"+{donation_value(content, cats[ids[1]])}" in h.adopt.toast.text
    assert len(read_save(p, content).pending_adoption["cats"]) == 1


def test_valor_de_doacao_cresce_com_o_iv(content):
    h = hub_memoria_com_oferta(content, 2, ivs=[(5, 5), (1, 1)])
    a, b = h.adopt.cats()
    assert h.adopt.value_of(a) > h.adopt.value_of(b) == donation_value(content, b)


def test_terminar_todos_volta_a_colecao_sem_oferta_pendente(content, tmp_path):
    h, p, ids = hub_com_oferta(content, tmp_path, 2)
    revelar_todos(h)
    h.click(("adopt", ids[0]))
    h.click(("donate", ids[1]))
    assert h.mode == "colecao" and h.adopt is None
    s = read_save(p, content)
    assert s.pending_adoption is None and not has_pending_adoption(s)
    assert not h.save_summary().endswith("(adoção pendente)")


def test_oferta_de_5_decidida_nas_duas_paginas(content, tmp_path):
    h, p, ids = hub_com_oferta(content, tmp_path, 5)
    revelar_todos(h)
    for cid in ids:
        h.click(("adopt", cid))
    assert h.mode == "colecao"
    assert len(read_save(p, content).cats) == 12 + 5


# ------------------------------------------------------------------ destaque de IV
@pytest.mark.parametrize("ivs,tier", [
    ((5, 5), "perfeito"), ((4, 4), "alto"), ((5, 3), "alto"), ((3, 4), ""), ((1, 1), ""),
    ((5, 4), "alto")])
def test_destaque_de_iv(content, ivs, tier):
    h = hub_memoria_com_oferta(content, 1, ivs=[ivs])
    assert h.adopt.tier(h.adopt.cats()[0]) == tier


def test_render_da_adocao_com_destaques_nao_quebra(content):
    h = hub_memoria_com_oferta(content, 4, ivs=[(5, 5), (4, 4), (2, 1), (3, 4)])
    for t in (0.0, 0.4):
        revelar_todos(h)
        draw_hub_frame(pygame.Surface((W, H)), h, UIState(t=t))


# ------------------------------------------------------------------ falha de gravacao
def test_falha_de_gravacao_ao_adotar_vira_aviso(content, tmp_path):
    h = HubController(content, caminho_invalido(tmp_path), SEED, ai_delay=0.0)
    h.adopt_save(new_game(content, Random(SEED)))
    montar_oferta(content, h.save, 2)
    h.open_pending_adoption()
    revelar_todos(h)
    cid = h.adopt.visible_ids()[0]
    h.click(("adopt", cid))
    assert h.adopt.toast is not None and "salvar" in h.adopt.toast.text.lower()
    assert cid in {c.id for c in h.save.cats}


def test_falha_de_gravacao_ao_doar_vira_aviso(content, tmp_path):
    h = HubController(content, caminho_invalido(tmp_path), SEED, ai_delay=0.0)
    h.adopt_save(new_game(content, Random(SEED)))
    montar_oferta(content, h.save, 2)
    h.open_pending_adoption()
    revelar_todos(h)
    h.click(("donate", h.adopt.visible_ids()[0]))
    assert "salvar" in h.adopt.toast.text.lower() and h.save.coins > 0


def test_falha_de_gravacao_no_fim_da_run_com_oferta_nao_levanta(content, tmp_path):
    h = HubController(content, caminho_invalido(tmp_path), SEED, ai_delay=0.0)
    h.click(("menu", "new_game"))
    h.rc, h.mode = RunFalsa("vitoria", 6), "run"
    h.click(None)
    assert h.mode == "adocao" and "salvar" in h.toast.text.lower()


# ------------------------------------------------------------------ continuar, ESC, reabrir
def test_continuar_com_oferta_pendente_abre_a_adocao_antes_da_colecao(content, tmp_path):
    h, p, ids = hub_com_oferta(content, tmp_path, 3, abrir=False)
    assert "(adoção pendente)" in h.save_summary()
    h.click(("menu", "continue"))
    assert h.mode == "adocao" and h.adopt.visible_ids() == ids


def test_continuar_sem_oferta_abre_a_colecao(content, tmp_path):
    p = tmp_path / "save.json"
    write_save(new_game(content, Random(SEED)), p)
    h = HubController(content, p, SEED, ai_delay=0.0)
    h.click(("menu", "continue"))
    assert h.mode == "colecao" and h.adopt is None


def test_esc_na_adocao_volta_ao_menu_e_mantem_a_oferta(content, tmp_path):
    h, p, ids = hub_com_oferta(content, tmp_path, 3)
    revelar_todos(h)
    h.click(("adopt", ids[0]))
    h.key_escape()
    assert h.mode == "menu" and h.adopt is None
    assert [c.id for c in read_save(p, content).pending_adoption["cats"]] == ids[1:]
    h.click(("menu", "continue"))
    assert h.mode == "adocao" and h.adopt.visible_ids() == ids[1:]
    assert h.adopt.revealed == set()           # cartoes voltam escondidos


def test_fechar_e_reabrir_nao_resorteia_a_oferta(content, tmp_path):
    h, p, ids = hub_com_oferta(content, tmp_path, 4)
    antes = [dataclasses.asdict(c) for c in h.save.pending_adoption["cats"]]
    h.key_escape()
    h2 = HubController(content, p, SEED + 99, ai_delay=0.0)       # outra seed: nada muda
    h2.click(("menu", "continue"))
    assert h2.adopt.visible_ids() == ids
    assert [dataclasses.asdict(c) for c in h2.save.pending_adoption["cats"]] == antes
    assert h2.save.next_cat_id == h.save.next_cat_id


# ------------------------------------------------------------------ doar na colecao
def hub_colecao_disco(content, tmp_path: Path, n_gatos: int):
    p = tmp_path / "save.json"
    write_save(save_grande(content, n_gatos), p)
    h = HubController(content, p, SEED, ai_delay=0.0)
    h.click(("menu", "continue"))
    assert h.mode == "colecao"
    return h, p


def test_doar_pede_confirmacao_e_nao_confirmar_nao_muda_nada(content, tmp_path):
    h, p = hub_colecao_disco(content, tmp_path, 14)
    antes = p.read_bytes()
    cid = h.col.selected
    h.click(("donate",))
    assert h.col.confirm_donate and "Doar" in h.col.donate_question()
    assert h.hit(LH.donate_buttons()["donate_no"].center) == ("donate_no",)
    h.click(("donate_no",))
    assert not h.col.confirm_donate and h.col.coins == 0
    assert cid in {c.id for c in h.save.cats} and p.read_bytes() == antes


def test_esc_fecha_a_confirmacao_de_doar_sem_voltar_ao_menu(content, tmp_path):
    h, _ = hub_colecao_disco(content, tmp_path, 14)
    h.click(("donate",))
    h.key_escape()
    assert not h.col.confirm_donate and h.mode == "colecao"


def test_confirmar_doacao_remove_gato_soma_moedas_e_grava(content, tmp_path):
    h, p = hub_colecao_disco(content, tmp_path, 14)
    cat = h.col.selected_cat()
    valor = donation_value(content, cat)
    h.click(("donate",))
    assert str(valor) in h.col.donate_question()
    h.click(h.hit(LH.donate_buttons()["donate_yes"].center))
    assert not h.col.confirm_donate and h.col.coins == valor
    s = read_save(p, content)
    assert s.coins == valor and len(s.cats) == 13 and cat.id not in {c.id for c in s.cats}
    assert h.col.selected != cat.id


def test_doar_gato_do_deck_tira_do_deck_e_grava_rascunho(content, tmp_path):
    h, p = hub_colecao_disco(content, tmp_path, 14)
    cid = h.col.save.deck[0]
    h.click(("row", cid))                       # seleciona e tira do deck
    h.click(("row", cid))                       # volta ao deck, selecionado
    assert cid in h.col.picked and h.col.selected == cid
    h.click(("donate",))
    h.click(("donate_yes",))
    assert cid not in h.col.picked and h.col.deck_count == 11
    s = read_save(p, content)
    assert cid not in s.deck and len(s.deck) == 11
    h2 = HubController(content, p, SEED, ai_delay=0.0)
    h2.click(("menu", "continue"))
    assert h2.col.picked == s.deck and h2.col.deck_text == "Deck 11/12"


def test_doacao_recusada_com_12_adultos(content, tmp_path):
    p = tmp_path / "save.json"
    write_save(new_game(content, Random(SEED)), p)
    h = HubController(content, p, SEED, ai_delay=0.0)
    h.click(("menu", "continue"))
    antes = p.read_bytes()
    h.click(("donate",))
    h.click(("donate_yes",))
    assert h.col.toast is not None and h.col.toast.text == MANTER_12
    assert len(h.save.cats) == 12 and h.col.coins == 0 and p.read_bytes() == antes


def test_doacao_na_colecao_sem_gato_selecionado_avisa(content):
    h = HubController(content, None, SEED)
    s = new_game(content, Random(SEED))
    s.cats, s.deck = [], []
    h.adopt_save(s)
    h.mode = "colecao"
    h.click(("donate",))
    assert not h.col.confirm_donate and h.col.toast is not None


def test_contador_de_moedas_acumula_adocao_e_colecao(content, tmp_path):
    h, p, ids = hub_com_oferta(content, tmp_path, 2, ivs=[(5, 5), (5, 5)])
    revelar_todos(h)
    h.click(("adopt", ids[0]))
    valor_oferta = donation_value(content, h.adopt.cats()[0])
    h.click(("donate", ids[1]))
    assert h.mode == "colecao" and h.col.coins == valor_oferta
    cat = h.col.selected_cat()
    h.click(("donate",))
    h.click(("donate_yes",))
    assert h.col.coins == valor_oferta + donation_value(content, cat)
    assert read_save(p, content).coins == h.col.coins
    draw_hub_frame(pygame.Surface((W, H)), h, UIState())


# ------------------------------------------------------------------ layout
TELA = pygame.Rect(0, 0, W, H)


def rects_adocao(n_visiveis: int) -> dict[str, pygame.Rect]:
    d: dict[str, pygame.Rect] = {}
    for i in range(n_visiveis):
        d[f"card_{i}"] = LH.adopt_card(i)
    d |= {f"nav_{k}": r for k, r in LH.adopt_nav().items()}
    return d


@pytest.mark.parametrize("n", [1, 4, 8])
def test_layout_adocao_dentro_da_tela_e_sem_sobreposicao(content, n):
    h = hub_memoria_com_oferta(content, n)
    vis = len(h.adopt.visible())
    assert vis == min(n, LH.ADOPT_PER_PAGE)
    rs = rects_adocao(vis)
    for nome, r in rs.items():
        assert TELA.contains(r) and r.w > 0 and r.h > 0, f"{nome} fora da tela: {r}"
    for (na, a), (nb, b) in combinations(rs.items(), 2):
        assert not a.colliderect(b), f"{na} sobrepoe {nb}"
    for i in range(vis):
        bs = LH.adopt_buttons(i)
        assert not bs["adopt"].colliderect(bs["donate"])
        for nome, r in bs.items():
            assert LH.adopt_card(i).contains(r), f"{nome} do cartao {i} fora do cartao"


@pytest.mark.parametrize("n", [1, 4, 8])
def test_hit_test_dos_botoes_da_adocao(content, n):
    h = hub_memoria_com_oferta(content, n)
    revelar_todos(h)
    ids = h.adopt.visible_ids()
    for i, cid in enumerate(ids):
        for nome, r in LH.adopt_buttons(i).items():
            assert h.hit(r.center) == (nome, cid)
    assert h.hit((0, 0)) is None and h.hit((W - 1, H - 1)) is None
    if len(ids) < LH.ADOPT_PER_PAGE:
        assert h.hit(LH.adopt_card(len(ids)).center) is None


@pytest.mark.parametrize("n", [1, 4, 8])
def test_adocao_renderiza_em_todas_as_paginas(content, n):
    h = hub_memoria_com_oferta(content, n)
    for _ in range(h.adopt.pages):
        draw_hub_frame(pygame.Surface((W, H)), h, UIState(t=0.2))
        revelar_todos(h)
        draw_hub_frame(pygame.Surface((W, H)), h, UIState(t=0.2))
        h.click(("page", 1))


def test_layout_adocao_vazia_e_resultado():
    hub, ui = make(SEED, "adocao_vazia")
    assert hub.mode == "resultado" and SEM_GATOS in hub.result_detail
    assert TELA.contains(LH.result_button())
    assert hub.hit(LH.result_button().center) == ("result_back",)
    surf = pygame.Surface((W, H))
    draw_hub_frame(surf, hub, ui)
    hub.click(("result_back",))
    assert hub.mode == "colecao"


def test_layout_doar_confirmar():
    p = LH.donate_panel()
    bs = LH.donate_buttons()
    assert TELA.contains(p)
    for nome, r in bs.items():
        assert p.contains(r), nome
    assert not bs["donate_yes"].colliderect(bs["donate_no"])
    hub, ui = make(SEED, "doar_confirmar")
    assert hub.col.confirm_donate
    assert hub.hit(bs["donate_yes"].center) == ("donate_yes",)
    assert hub.hit(bs["donate_no"].center) == ("donate_no",)
    assert hub.hit(LH.row_rect(0).center) is None      # dialogo bloqueia o resto
    draw_hub_frame(pygame.Surface((W, H)), hub, ui)


def test_layout_botoes_renomear_e_doar_no_painel_de_detalhe():
    d = LH.detail_panel()
    assert d.contains(LH.rename_button()) and d.contains(LH.donate_button())
    assert not LH.rename_button().colliderect(LH.donate_button())
    for r in LH.action_buttons().values():
        assert not LH.donate_button().colliderect(r)


# ------------------------------------------------------------------ backup do NOVO JOGO (.bak)
def novo_jogo_confirmado(h: HubController) -> None:
    h.click(("menu", "new_game"))
    if h.confirm_new:
        h.click(("confirm_yes",))
    assert h.mode == "colecao"


def test_novo_jogo_sobre_save_existente_guarda_o_antigo_em_bak(content, tmp_path):
    p = tmp_path / "save.json"
    write_save(new_game(content, Random(SEED)), p)
    antigo = p.read_bytes()
    h = HubController(content, p, SEED + 100, ai_delay=0.0)
    novo_jogo_confirmado(h)
    bak = tmp_path / "save.json.bak"
    assert bak.exists() and bak.read_bytes() == antigo
    assert p.read_bytes() != antigo
    read_save(p, content)                      # o novo e valido


def test_novo_jogo_sobre_save_corrompido_guarda_o_lixo_em_bak(content, tmp_path):
    p = tmp_path / "save.json"
    lixo = b"\x00\xff isto nao e json \x80"
    p.write_bytes(lixo)
    h = HubController(content, p, SEED, ai_delay=0.0)
    novo_jogo_confirmado(h)
    assert (tmp_path / "save.json.bak").read_bytes() == lixo
    assert h.load_error is None and len(read_save(p, content).cats) == 12


def test_novo_jogo_sem_save_nao_cria_bak(content, tmp_path):
    p = tmp_path / "saves" / "save.json"
    h = HubController(content, p, SEED, ai_delay=0.0)
    novo_jogo_confirmado(h)
    assert not (p.parent / "save.json.bak").exists()


def test_novo_jogo_cancelado_nao_cria_bak(content, tmp_path):
    p = tmp_path / "save.json"
    write_save(new_game(content, Random(SEED)), p)
    h = HubController(content, p, SEED, ai_delay=0.0)
    h.click(("menu", "new_game"))
    h.click(("confirm_no",))
    assert not (tmp_path / "save.json.bak").exists()


def test_segundo_novo_jogo_substitui_o_bak_anterior(content, tmp_path):
    p = tmp_path / "save.json"
    write_save(new_game(content, Random(SEED)), p)
    h = HubController(content, p, SEED + 1, ai_delay=0.0)
    novo_jogo_confirmado(h)
    segundo = p.read_bytes()
    h2 = HubController(content, p, SEED + 2, ai_delay=0.0)
    novo_jogo_confirmado(h2)
    assert (tmp_path / "save.json.bak").read_bytes() == segundo


def test_falha_no_backup_nao_impede_o_jogo_novo(content, tmp_path):
    p = tmp_path / "save.json"
    write_save(new_game(content, Random(SEED)), p)
    antigo = p.read_bytes()
    (tmp_path / "save.json.bak").mkdir()       # destino do backup impossivel (e uma pasta)
    h = HubController(content, p, SEED + 100, ai_delay=0.0)
    novo_jogo_confirmado(h)
    s = read_save(p, content)
    assert len(s.cats) == 12 and p.read_bytes() != antigo
    assert h.col.toast is not None and "backup" in h.col.toast.text.lower()


def test_backup_save_devolve_none_em_memoria_e_sem_arquivo(content, tmp_path):
    assert HubController(content, None, SEED).backup_save() is None
    assert HubController(content, tmp_path / "nada.json", SEED).backup_save() is None
