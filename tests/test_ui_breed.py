"""Testes da UI do Criatorio, Novidades e fim de run com breed (T5.20), sem janela.

Escritos a partir de reports/T5.18-ui-breed.md e do pedido do Renatho; so API publica do core
e dos controllers. Estado final conferido por `read_save`.
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
from core import (RunAftermath, advance_after_run, available_cats, breeding_status, can_breed,
                  has_pending_adoption, new_game, read_save, start_breed, write_save)
from ui import font, layout_breed as LB
from ui.breed_controller import BreedController, NewsController
from ui.controller import load_game_content
from ui.hub_controller import SHORT_RUN_TEXT, HubController
from ui.render import UIState
from ui.render_hub import draw_hub_frame
from ui.scenes_hub import BREED_SCENES, make
from ui.theme import H, W

def _col(h) -> None:
    """O hub agora abre no cercado (Criatorio animado): segue o fluxo antigo (adocao pendente
    ou colecao) pelos botoes do painel."""
    if h.mode == "cercado":
        h.click(("pen_btn", "adocao" if h.adoption_pending else "colecao"))

SEED = 7
TELA = pygame.Rect(0, 0, W, H)


@pytest.fixture(scope="module")
def content():
    return load_game_content()


# ------------------------------------------------------------------ helpers
def save_com(content, n: int = 16):
    """n adultos (machos nos indices pares, femeas nos impares), deck = 12 primeiros."""
    s = new_game(content, Random(SEED))
    base = list(s.cats)
    i = 0
    while len(s.cats) < n:
        c = dataclasses.replace(base[i % len(base)])
        c.id = f"c-{s.next_cat_id:06d}"
        s.next_cat_id += 1
        s.cats.append(c)
        i += 1
    for k, c in enumerate(s.cats):
        c.sex = "M" if k % 2 == 0 else "F"
        c.rest_runs_left = 0
    s.deck = [c.id for c in s.cats][:12]
    return s


def casal(s) -> tuple[str, str]:
    m = next(c for c in s.cats if c.sex == "M")
    f = next(c for c in s.cats if c.sex == "F")
    return m.id, f.id


def controller(content, tmp_path: Path, n: int = 16):
    p = tmp_path / "save.json"
    s = save_com(content, n)
    write_save(s, p)
    bc = BreedController(content, s, persist=lambda: (write_save(s, p), None)[1])
    return bc, s, p


def escolher(bc: BreedController, m: str, f: str) -> None:
    bc.click(("row", "M", m))
    bc.click(("row", "F", f))


def hub_disco(content, tmp_path: Path, n: int = 16):
    p = tmp_path / "save.json"
    write_save(save_com(content, n), p)
    h = HubController(content, p, SEED, ai_delay=0.0)
    h.click(("menu", "continue"))
    _col(h)
    _col(h)
    assert h.mode == "colecao"
    return h, p


class RunFalsa:
    def __init__(self, result, nodes, abandoned=False):
        self.screen = "finished"
        self.run = SimpleNamespace(result=result, nodes_cleared=nodes)
        self.abandoned = abandoned
        self.end_line = None

    def click(self, elem): ...
    def update(self, dt): ...


def terminar_run(h: HubController, result="derrota", nodes=1):
    h.rc, h.mode = RunFalsa(result, nodes), "run"
    h.click(None)


def voltar_a_colecao(h: HubController) -> None:
    """Sai de novidades/adocao/resultado ate a colecao (adota o que for oferecido)."""
    for _ in range(40):
        if h.mode == "cercado":
            h.click(("pen_btn", "colecao"))
        if h.mode == "colecao":
            return
        if h.mode == "novidades":
            h.click(("news_continue",))
        elif h.mode == "adocao":
            h.click(("reveal_all",))
            h.click(("adopt", h.adopt.visible_ids()[0]))
        elif h.mode == "resultado":
            h.click(("result_back",))
    raise AssertionError(f"preso em {h.mode}")


def capturar_textos(monkeypatch) -> list[str]:
    textos: list[str] = []
    orig = font.draw

    def spy(surf, text, *a, **k):
        textos.append(text)
        return orig(surf, text, *a, **k)

    monkeypatch.setattr(font, "draw", spy)
    return textos


# ------------------------------------------------------------------ BreedController: listas
def test_listas_so_tem_adultos_disponiveis_do_sexo_certo(content, tmp_path):
    bc, s, _ = controller(content, tmp_path, 18)
    kit = dataclasses.replace(s.cats[0], id="c-000090", stage="kitten", sex="M", runs_as_kitten=0)
    s.cats.append(kit)
    s.next_cat_id = 91
    descanso = next(c for c in s.cats if c.sex == "F")
    descanso.rest_runs_left = 1
    m = [c.id for c in s.cats if c.sex == "M" and c.stage == "adult"][1]
    f = [c.id for c in s.cats if c.sex == "F" and c.rest_runs_left == 0][1]
    start_breed(content, s, m, f)
    machos = {r.cat.id for r in bc.rows("M")}
    femeas = {r.cat.id for r in bc.rows("F")}
    assert kit.id not in machos and m not in machos and f not in femeas
    assert descanso.id not in femeas
    assert all(r.cat.sex == "M" and r.cat.stage == "adult" for r in bc.rows("M"))
    assert all(r.cat.sex == "F" for r in bc.rows("F"))
    assert machos | femeas == {c.id for c in available_cats(s)}


def test_selecionar_macho_e_femea_e_clicar_de_novo_desmarca(content, tmp_path):
    bc, s, _ = controller(content, tmp_path)
    m, f = casal(s)
    assert bc.pair() is None
    bc.click(("row", "M", m))
    assert bc.selected("M").id == m and bc.pair() is None
    bc.click(("row", "F", f))
    assert bc.pair() is not None
    bc.click(("row", "M", m))
    assert bc.selected("M") is None


def test_clique_nas_linhas_pelo_hit_test(content, tmp_path):
    bc, s, _ = controller(content, tmp_path)
    for side in "MF":
        for i, cid in enumerate(bc.visible_ids(side)):
            assert bc.hit(LB.row_rect(side, i).center) == ("row", side, cid)
    assert bc.hit((0, 0)) is None


def test_iniciar_breed_habilitado_so_com_casal_aceito_pelo_core(content, tmp_path):
    bc, s, _ = controller(content, tmp_path)
    assert not bc.can_start and bc.verdict()[1]
    m, f = casal(s)
    escolher(bc, m, f)
    assert bc.can_start and bc.verdict() == can_breed(content, s, m, f) == (True, "")


def test_iniciar_breed_recusado_mostra_motivo_do_core_e_nao_grava(content, tmp_path):
    bc, s, p = controller(content, tmp_path, 13)         # 13 - 2 = 11 < 12
    m, f = casal(s)
    escolher(bc, m, f)
    ok, motivo = can_breed(content, s, m, f)
    assert not ok and not bc.can_start and bc.verdict() == (False, motivo)
    antes = p.read_bytes()
    bc.click(("start",))
    assert bc.toast is not None and bc.toast.text == motivo
    assert s.breeding == [] and p.read_bytes() == antes


def test_iniciar_breed_grava_e_o_save_relido_confere(content, tmp_path):
    bc, s, p = controller(content, tmp_path)
    m, f = casal(s)
    escolher(bc, m, f)
    bc.click(("start",))
    lido = read_save(p, content)
    assert lido.breeding == [{"male": m, "female": f, "runs_left": 2}]
    assert m not in lido.deck and f not in lido.deck
    assert bc.sel == {"M": None, "F": None}
    assert bc.toast is not None and bc.toast.kind == "info"


def test_iniciar_sem_casal_nao_faz_nada(content, tmp_path):
    bc, s, p = controller(content, tmp_path)
    antes = p.read_bytes()
    bc.click(("start",))
    assert s.breeding == [] and p.read_bytes() == antes and bc.toast is not None


# ------------------------------------------------------------------ raca provavel
def test_raca_provavel_60_mae_40_pai(content, tmp_path):
    bc, s, _ = controller(content, tmp_path)
    m, f = casal(s)
    pai = next(c for c in s.cats if c.id == m)
    mae = next(c for c in s.cats if c.id == f)
    pai.breed = next(b for b in content.breeds if b != mae.breed)
    escolher(bc, m, f)
    nome = lambda c: content.breeds[c.breed]["nome"]
    assert bc.breed_odds() == [(60, nome(mae)), (40, nome(pai))]


def test_raca_provavel_100_se_as_racas_sao_iguais(content, tmp_path):
    bc, s, _ = controller(content, tmp_path)
    m, f = casal(s)
    pai = next(c for c in s.cats if c.id == m)
    mae = next(c for c in s.cats if c.id == f)
    pai.breed = mae.breed
    escolher(bc, m, f)
    assert bc.breed_odds() == [(100, content.breeds[mae.breed]["nome"])]


def test_raca_provavel_vazia_sem_casal(content, tmp_path):
    bc, _, _ = controller(content, tmp_path)
    assert bc.breed_odds() == []


# ------------------------------------------------------------------ em breed e cancelar
def test_em_breed_lista_casal_com_runs_left(content, tmp_path):
    bc, s, _ = controller(content, tmp_path)
    m, f = casal(s)
    escolher(bc, m, f)
    bc.click(("start",))
    cs = bc.couples()
    assert len(cs) == 1 and (cs[0].male.id, cs[0].female.id) == (m, f) and cs[0].runs_left == 2
    advance_after_run(content, s, Random(1), 1)
    assert bc.couples()[0].runs_left == 1


def test_cancelar_antes_de_passar_run_funciona_e_grava(content, tmp_path):
    bc, s, p = controller(content, tmp_path)
    m, f = casal(s)
    escolher(bc, m, f)
    bc.click(("start",))
    assert bc.couples()[0].can_cancel
    assert bc.hit(LB.cancel_button(0).center) == ("cancel", m, f)
    bc.click(bc.hit(LB.cancel_button(0).center))
    lido = read_save(p, content)
    assert lido.breeding == [] and bc.couples() == []
    assert {m, f} <= {x.id for x in available_cats(lido)}


def test_cancelar_apos_run_com_no_vencido_e_recusado_com_motivo(content, tmp_path):
    bc, s, p = controller(content, tmp_path)
    m, f = casal(s)
    escolher(bc, m, f)
    bc.click(("start",))
    advance_after_run(content, s, Random(1), 2)
    write_save(s, p)
    c = bc.couples()[0]
    assert not c.can_cancel and c.why_not
    antes = p.read_bytes()
    bc.click(("cancel", m, f))
    assert bc.toast is not None and bc.toast.text == c.why_not and bc.toast.kind == "error"
    assert len(s.breeding) == 1 and p.read_bytes() == antes


def test_cancelar_apos_run_sem_nos_ainda_e_permitido(content, tmp_path):
    bc, s, _ = controller(content, tmp_path)
    escolher(bc, *casal(s))
    bc.click(("start",))
    advance_after_run(content, s, Random(1), 0)
    assert bc.couples()[0].can_cancel


def test_consulta_de_cancelamento_nao_altera_o_save(content, tmp_path):
    bc, s, _ = controller(content, tmp_path)
    escolher(bc, *casal(s))
    bc.click(("start",))
    antes = [dict(b) for b in s.breeding]
    bc.couples()
    bc.couples()
    assert s.breeding == antes


# ------------------------------------------------------------------ filhotes
def test_filhotes_listam_runs_que_faltam(content, tmp_path):
    bc, s, _ = controller(content, tmp_path)
    g = content.rules["breed"]["growth_runs"]
    for i in range(2):
        s.cats.append(dataclasses.replace(s.cats[0], id=f"c-{900 + i}", stage="kitten",
                                          runs_as_kitten=i))
    assert {c.id: n for c, n in bc.kittens()} == {"c-900": g, "c-901": g - 1}


def test_falha_de_gravacao_vira_aviso_e_nao_levanta(content):
    s = save_com(content)
    bc = BreedController(content, s, persist=lambda: "disco cheio")
    escolher(bc, *casal(s))
    bc.click(("start",))
    assert bc.toast is not None and "salvar" in bc.toast.text.lower()
    assert len(s.breeding) == 1


def test_falha_de_gravacao_ao_cancelar_vira_aviso(content):
    s = save_com(content)
    bc = BreedController(content, s, persist=lambda: "disco cheio")
    m, f = casal(s)
    escolher(bc, m, f)
    bc.click(("start",))
    bc.click(("cancel", m, f))
    assert "salvar" in bc.toast.text.lower() and s.breeding == []


# ------------------------------------------------------------------ colecao
def hub_com_casal_e_filhote(content, tmp_path):
    h, p = hub_disco(content, tmp_path)
    s = h.save
    m = [c.id for c in s.cats if c.sex == "M"][1]
    f = [c.id for c in s.cats if c.sex == "F"][1]
    kit = dataclasses.replace(s.cats[0], id="c-000500", stage="kitten", runs_as_kitten=0)
    s.cats.append(kit)
    s.next_cat_id = 501
    start_breed(content, s, m, f)
    h.col.refresh_deck()
    return h, p, m, f, kit.id


def test_colecao_mostra_estados_brd_e_filh_com_runs(content, tmp_path):
    h, p, m, f, k = hub_com_casal_e_filhote(content, tmp_path)
    rows = {r.cat.id: r for r in h.col.rows()}
    assert rows[m].state == "breed" and h.col.state_text(rows[m]) == "brd2"
    assert rows[f].state == "breed"
    assert rows[k].state == "filhote"
    assert h.col.state_text(rows[k]) == f"filh{content.rules['breed']['growth_runs']}"
    longo = h.col.state_long_text(rows[m])
    assert "2" in longo and "breed" in longo.lower()


def test_clicar_em_gato_em_breed_avisa_e_nao_entra_no_deck(content, tmp_path):
    h, p, m, f, k = hub_com_casal_e_filhote(content, tmp_path)
    antes = list(h.col.picked)
    h.click(("row", m))
    assert h.col.toast is not None and "breed" in h.col.toast.text.lower()
    assert m not in h.col.picked and h.col.picked == antes


def test_clicar_em_filhote_avisa_e_nao_entra_no_deck(content, tmp_path):
    h, p, m, f, k = hub_com_casal_e_filhote(content, tmp_path)
    antes = list(h.col.picked)
    h.click(("row", k))
    assert h.col.toast is not None and "filhote" in h.col.toast.text.lower()
    assert k not in h.col.picked and h.col.picked == antes
    assert k not in read_save(p, content).deck


def test_pais_saem_do_rascunho_do_deck_ao_voltar_do_criatorio(content, tmp_path):
    h, p = hub_disco(content, tmp_path)
    s = h.save
    sexo = {c.id: c.sex for c in s.cats}
    m = next(i for i in h.col.picked if sexo[i] == "M")
    f = next(i for i in h.col.picked if sexo[i] == "F")
    h.click(("breed",))
    assert h.mode == "criatorio"
    h.click(("row", "M", m))
    h.click(("row", "F", f))
    h.click(("start",))
    assert len(s.breeding) == 1
    h.click(("back",))
    _col(h)
    assert h.mode == "colecao"
    assert m not in h.col.picked and f not in h.col.picked
    assert h.col.deck_count == len(h.col.picked) == 10
    assert read_save(p, content).breeding[0]["male"] == m


def test_esc_no_criatorio_volta_a_colecao(content, tmp_path):
    h, _ = hub_disco(content, tmp_path)
    h.click(("breed",))
    h.key_escape()
    _col(h)
    assert h.mode == "colecao" and h.breed is None


# ------------------------------------------------------------------ fim de run
def test_fim_de_run_ordem_advance_create_um_write(content, tmp_path, monkeypatch):
    h, p = hub_disco(content, tmp_path)
    ev: list[str] = []
    ra, rc, rw = hub_mod.advance_after_run, hub_mod.create_adoption, hub_mod.write_save
    monkeypatch.setattr(hub_mod, "advance_after_run",
                        lambda *a, **k: (ev.append("advance"), ra(*a, **k))[1])
    monkeypatch.setattr(hub_mod, "create_adoption",
                        lambda *a, **k: (ev.append("create"), rc(*a, **k))[1])
    monkeypatch.setattr(hub_mod, "write_save",
                        lambda *a, **k: (ev.append("write"), rw(*a, **k))[1])
    terminar_run(h, "vitoria", 6)
    assert ev == ["advance", "create", "write"]
    assert has_pending_adoption(read_save(p, content))


def test_fim_de_run_passa_os_nos_vencidos_ao_advance(content, tmp_path, monkeypatch):
    h, _ = hub_disco(content, tmp_path)
    vistos = []
    ra = hub_mod.advance_after_run
    monkeypatch.setattr(hub_mod, "advance_after_run",
                        lambda c, s, rng, n: (vistos.append(n), ra(c, s, rng, n))[1])
    terminar_run(h, "derrota", 3)
    assert vistos == [3]


def preparar_breed(content, h) -> tuple[str, str]:
    m, f = casal(h.save)
    start_breed(content, h.save, m, f)
    h.persist()
    return m, f


def test_novidades_nao_aparece_sem_nascimento_nem_crescimento(content, tmp_path, monkeypatch):
    h, _ = hub_disco(content, tmp_path)
    monkeypatch.setattr(hub_mod, "create_adoption", lambda *a, **k: None)
    terminar_run(h, "derrota", 1)
    assert h.mode == "resultado" and h.news is None


def test_novidades_aparece_na_ninhada_e_nao_antes(content, tmp_path, monkeypatch):
    h, _ = hub_disco(content, tmp_path)
    monkeypatch.setattr(hub_mod, "create_adoption", lambda *a, **k: None)
    preparar_breed(content, h)
    terminar_run(h, "derrota", 1)
    assert h.mode == "resultado"
    terminar_run(h, "derrota", 1)
    assert h.mode == "novidades" and h.news.born and not h.news.empty


def test_continuar_das_novidades_vai_para_resultado_sem_oferta(content, tmp_path, monkeypatch):
    h, _ = hub_disco(content, tmp_path)
    monkeypatch.setattr(hub_mod, "create_adoption", lambda *a, **k: None)
    preparar_breed(content, h)
    terminar_run(h, "derrota", 1)
    terminar_run(h, "derrota", 1)
    assert h.hit(LB.news_button().center) == ("news_continue",)
    h.click(h.hit(LB.news_button().center))
    assert h.mode == "resultado" and h.news is None


def test_continuar_das_novidades_vai_para_adocao_com_oferta_pendente(content, tmp_path):
    h, p = hub_disco(content, tmp_path)
    preparar_breed(content, h)
    terminar_run(h, "derrota", 1)
    voltar_a_colecao(h)
    terminar_run(h, "vitoria", 6)
    assert h.mode == "novidades"
    h.click(("news_continue",))
    assert h.mode == "adocao" and h.adopt is not None
    assert has_pending_adoption(read_save(p, content))


@pytest.mark.parametrize("tecla", ["key_enter", "key_escape"])
def test_enter_e_esc_nas_novidades_tambem_continuam(content, tmp_path, monkeypatch, tecla):
    h, _ = hub_disco(content, tmp_path)
    monkeypatch.setattr(hub_mod, "create_adoption", lambda *a, **k: None)
    preparar_breed(content, h)
    terminar_run(h, "derrota", 1)
    terminar_run(h, "derrota", 1)
    assert h.mode == "novidades"
    getattr(h, tecla)()
    assert h.mode == "resultado"


def test_run_curta_aparece_abaixo_do_minimo_e_nao_com_um_no(content, tmp_path, monkeypatch):
    textos = capturar_textos(monkeypatch)
    h, _ = hub_disco(content, tmp_path)
    terminar_run(h, "derrota", 0)
    assert h.short_run and h.mode == "resultado"
    draw_hub_frame(pygame.Surface((W, H)), h, UIState())
    assert SHORT_RUN_TEXT in textos
    assert SHORT_RUN_TEXT == "Run curta: não conta para o breed"
    textos.clear()
    h.click(("result_back",))
    terminar_run(h, "derrota", 1)
    assert not h.short_run
    if h.mode == "resultado":
        draw_hub_frame(pygame.Surface((W, H)), h, UIState())
    assert SHORT_RUN_TEXT not in textos


def test_run_curta_vai_para_o_cabecalho_da_adocao(content, tmp_path):
    h, _ = hub_disco(content, tmp_path)
    terminar_run(h, "vitoria", 6)
    assert not h.short_run and h.adopt.note == ""
    h.key_escape()
    h.short_run = True
    h.click(("menu", "continue"))
    _col(h)
    assert h.adopt.note == SHORT_RUN_TEXT


def test_falha_de_gravacao_no_fim_da_run_com_nascimento_nao_levanta(content, tmp_path):
    (tmp_path / "arq").write_text("x")
    h = HubController(content, tmp_path / "arq" / "x" / "save.json", SEED, ai_delay=0.0)
    h.click(("menu", "new_game"))
    _col(h)
    h.save.cats.extend(save_com(content, 16).cats[12:])
    start_breed(content, h.save, *casal(h.save))
    terminar_run(h, "derrota", 1)
    terminar_run(h, "derrota", 1)
    assert h.mode == "novidades" and "salvar" in h.toast.text.lower()


# ------------------------------------------------------------------ NewsController
def test_news_vazio_e_titulos(content):
    s = save_com(content)
    n = NewsController(content, s, RunAftermath(born=[], grown=[], couples_done=[]))
    assert n.empty
    um = NewsController(content, s, RunAftermath(born=s.cats[:1], grown=[], couples_done=[]))
    tres = NewsController(content, s, RunAftermath(born=s.cats[:3], grown=s.cats[:2],
                                                   couples_done=[]))
    assert not um.empty and "1" in um.born_title() and "3" in tres.born_title()
    assert "2" in tres.grown_title() and len(tres.grown_labels()) == 2
    assert um.click(None) is None and um.click(("news_continue",)) == "done"


def test_news_nomes_do_casal_livre(content):
    s = save_com(content)
    m, f = casal(s)
    n = NewsController(content, s, RunAftermath(born=[], grown=s.cats[:1],
                                                couples_done=[(m, f), ("c-999999", f)]))
    assert len(n.couple_labels()) == 1            # id inexistente e ignorado


def test_news_destaque_de_iv(content):
    s = save_com(content)
    n = NewsController(content, s, RunAftermath(born=[], grown=[], couples_done=[]))
    a, b, c = s.cats[:3]
    a.iv_atk = a.iv_hp = 5
    b.iv_atk, b.iv_hp = 4, 4
    c.iv_atk, c.iv_hp = 3, 4
    assert (n.tier(a), n.tier(b), n.tier(c)) == ("perfeito", "alto", "")


# ------------------------------------------------------------------ fluxo completo
def test_fluxo_completo_duas_runs_nascem_filhotes_mais_duas_viram_adultos(content, tmp_path):
    h, p = hub_disco(content, tmp_path)
    preparar_breed(content, h)
    terminar_run(h, "derrota", 1)
    voltar_a_colecao(h)
    assert not any(c.stage == "kitten" for c in h.save.cats)
    terminar_run(h, "derrota", 1)
    assert h.mode == "novidades"
    nasceram = [c.id for c in h.news.born]
    assert 1 <= len(nasceram) <= 3
    voltar_a_colecao(h)
    s = read_save(p, content)
    assert {c.id for c in s.cats if c.stage == "kitten"} == set(nasceram) and s.breeding == []
    assert {c.id for c in available_cats(s)}.isdisjoint(nasceram)
    terminar_run(h, "derrota", 1)
    voltar_a_colecao(h)
    assert all(c.stage == "kitten" for c in read_save(p, content).cats if c.id in nasceram)
    terminar_run(h, "derrota", 1)
    assert h.mode == "novidades" and {c.id for c in h.news.grown} == set(nasceram)
    voltar_a_colecao(h)
    s = read_save(p, content)
    assert all(c.stage == "adult" for c in s.cats if c.id in nasceram)
    assert set(nasceram) <= {c.id for c in available_cats(s)}
    assert breeding_status(s) == []


def test_fluxo_run_de_zero_nos_nao_avanca_o_breed(content, tmp_path):
    h, p = hub_disco(content, tmp_path)
    preparar_breed(content, h)
    for _ in range(3):
        terminar_run(h, "derrota", 0)
        voltar_a_colecao(h)
    assert read_save(p, content).breeding[0]["runs_left"] == 2


# ------------------------------------------------------------------ layout
def rects_criatorio() -> dict[str, pygame.Rect]:
    d: dict[str, pygame.Rect] = {}
    for side in "MF":
        d[f"head_{side}"] = LB.list_header(side)
        for i in range(LB.ROWS):
            d[f"row_{side}{i}"] = LB.row_rect(side, i)
    d["panel_breed"], d["panel_kit"] = LB.breed_panel(), LB.kitten_panel()
    d["side"] = LB.side_panel()
    return d


def test_layout_criatorio_dentro_da_tela_e_sem_sobreposicao():
    rs = rects_criatorio()
    for nome, r in rs.items():
        assert TELA.contains(r) and r.w > 0 and r.h > 0, nome
    for (na, a), (nb, b) in combinations(rs.items(), 2):
        assert not a.colliderect(b), f"{na} sobrepoe {nb}"


def test_layout_criatorio_botoes_dentro_dos_seus_pais():
    for side in "MF":
        h = LB.list_header(side)
        a, b = LB.scroll_button(side, -1), LB.scroll_button(side, 1)
        assert h.contains(a) and h.contains(b) and not a.colliderect(b)
    cs = [LB.couple_rect(i) for i in range(LB.COUPLES_VISIBLE)]
    for i, c in enumerate(cs):
        assert LB.breed_panel().contains(c) and c.contains(LB.cancel_button(i))
    for a, b in combinations(cs, 2):
        assert not a.colliderect(b)
    bs = LB.action_buttons()
    assert all(LB.side_panel().contains(r) for r in bs.values())
    assert not bs["start"].colliderect(bs["back"])


def test_layout_novidades():
    assert TELA.contains(LB.news_button())
    assert LB.news_hit(LB.news_button().center) == ("news_continue",)
    assert LB.news_hit((0, 0)) is None


@pytest.mark.parametrize("cena", ["criatorio", "criatorio_casal", "criatorio_recusado"])
def test_hit_test_das_cenas_do_criatorio(cena):
    hub, ui = make(SEED, cena)
    assert hub.mode == "criatorio"
    bc = hub.breed
    for side in "MF":
        for i, cid in enumerate(bc.visible_ids(side)):
            assert hub.hit(LB.row_rect(side, i).center) == ("row", side, cid)
    assert hub.hit(LB.action_buttons()["start"].center) == ("start",)
    assert hub.hit(LB.action_buttons()["back"].center) == ("back",)
    assert hub.hit((0, 0)) is None
    for i, (m, f) in enumerate(bc.cancel_pairs()):
        assert hub.hit(LB.cancel_button(i).center) == ("cancel", m, f)


def test_cena_casal_habilita_e_cena_recusada_desabilita_o_inicio():
    hub, _ = make(SEED, "criatorio_casal")
    assert hub.breed.pair() is not None and hub.breed.can_start
    hub, _ = make(SEED, "criatorio_recusado")
    assert hub.breed.pair() is not None and not hub.breed.can_start
    assert hub.breed.verdict()[1]


def test_cena_novidades_hit_e_continuar():
    hub, _ = make(SEED, "novidades")
    assert hub.mode == "novidades" and not hub.news.empty
    assert hub.hit(LB.news_button().center) == ("news_continue",)
    hub.click(("news_continue",))
    assert hub.mode in ("resultado", "adocao")


# ------------------------------------------------------------------ renderizacao
def hash_cena(nome: str) -> bytes:
    hub, ui = make(SEED, nome)
    surf = pygame.Surface((W, H))
    draw_hub_frame(surf, hub, ui)
    return pygame.image.tobytes(surf, "RGB")


@pytest.mark.parametrize("cena", BREED_SCENES)
def test_cena_renderiza_igual_em_duas_execucoes(cena):
    a, b = hash_cena(cena), hash_cena(cena)
    assert a == b and len(a) == W * H * 3
    assert len(set(a)) > 4                    # nao e um quadro em branco


def test_cenas_do_breed_sao_diferentes_entre_si():
    assert len({hash_cena(c) for c in BREED_SCENES}) == len(BREED_SCENES)


def test_render_com_varios_estados_do_mouse_nao_quebra():
    hub, ui = make(SEED, "criatorio_casal")
    for pos in ((0, 0), LB.row_rect("M", 0).center, LB.action_buttons()["start"].center,
                LB.cancel_button(0).center):
        ui.mouse = pos
        draw_hub_frame(pygame.Surface((W, H)), hub, ui)
