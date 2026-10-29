"""Testes do hub da UI (T5.4, Fase 5a), sem janela: HubController, CollectionController, layout_hub
e uma smoke de renderizacao headless das cenas.

Escritos a partir de reports/T5.3-ui-colecao.md e das regras do Renatho (2026-10-28). O estado
final e conferido na API publica do core (`read_save`, `available_cats`, `cat_stats`).
"""
from __future__ import annotations

import dataclasses
import json
import os
from itertools import combinations
from pathlib import Path
from random import Random

import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame

from core import cat_stats, new_game, read_save, save_to_dict, write_save
from ui import layout_hub as LH
from ui.controller import load_game_content
from ui.hub_controller import HubController
from ui.render import UIState
from ui.render_hub import draw_hub_frame
from ui.scenes_hub import HUB_SCENES, make
from ui.theme import H, W

SEED = 7


@pytest.fixture(scope="module")
def content():
    return load_game_content()


def hub_disco(content, tmp_path: Path, seed: int = SEED) -> tuple[HubController, Path]:
    p = tmp_path / "saves" / "save.json"
    return HubController(content, p, seed, ai_delay=0.0), p


def hub_com_save(content, tmp_path: Path) -> tuple[HubController, Path]:
    """Hub com save valido em disco, ainda no menu."""
    p = tmp_path / "save.json"
    write_save(new_game(content, Random(SEED)), p)
    return HubController(content, p, SEED, ai_delay=0.0), p


def entrar_colecao(h: HubController) -> None:
    h.click(("menu", "continue"))
    assert h.mode == "colecao"


def save_grande(content, n: int = 30):
    """Save com n gatos adultos: os 12 do new_game mais copias com ids novos."""
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


def hub_grande(content, n: int = 30) -> HubController:
    h = HubController(content, None, SEED, ai_delay=0.0)
    h.adopt_save(save_grande(content, n))
    h.mode = "colecao"
    return h


def clicar_linha(h: HubController, cat_id: str) -> None:
    h.click(("row", cat_id))


# ------------------------------------------------------------------ menu
def test_sem_save_continuar_desabilitado_e_novo_jogo_disponivel(content, tmp_path):
    h, p = hub_disco(content, tmp_path)
    assert h.mode == "menu" and not p.exists()
    assert h.menu_enabled() == {"continue": False, "new_game": True, "quit": True}
    h.click(("menu", "continue"))
    assert h.mode == "menu"


def test_novo_jogo_sem_save_nao_pede_confirmacao_e_grava(content, tmp_path):
    h, p = hub_disco(content, tmp_path)
    h.click(("menu", "new_game"))
    assert not h.confirm_new and h.mode == "colecao"
    assert p.exists()
    s = read_save(p, content)
    assert len(s.cats) == len(h.save.cats) and s.deck == h.save.deck


def test_continuar_com_save_valido_abre_colecao(content, tmp_path):
    h, _ = hub_com_save(content, tmp_path)
    assert h.can_continue and h.menu_enabled()["continue"]
    entrar_colecao(h)
    assert h.col.deck_count == 12


def test_novo_jogo_com_save_pede_confirmacao(content, tmp_path):
    h, p = hub_com_save(content, tmp_path)
    antes = p.read_bytes()
    h.click(("menu", "new_game"))
    assert h.confirm_new and h.mode == "menu"
    assert p.read_bytes() == antes


def test_cancelar_confirmacao_mantem_save(content, tmp_path):
    h, p = hub_com_save(content, tmp_path)
    antes = p.read_bytes()
    h.click(("menu", "new_game"))
    h.click(("confirm_no",))
    assert not h.confirm_new and h.mode == "menu" and p.read_bytes() == antes


def test_esc_na_confirmacao_cancela(content, tmp_path):
    h, p = hub_com_save(content, tmp_path)
    h.click(("menu", "new_game"))
    h.key_escape()
    assert not h.confirm_new and h.mode == "menu"


def test_confirmar_novo_jogo_substitui_o_save_em_disco(content, tmp_path):
    h, p = hub_com_save(content, tmp_path)
    antes = read_save(p, content)
    h2 = HubController(content, p, SEED + 100, ai_delay=0.0)
    h2.click(("menu", "new_game"))
    h2.click(("confirm_yes",))
    assert h2.mode == "colecao" and not h2.confirm_new
    depois = read_save(p, content)
    assert save_to_dict(depois) == save_to_dict(h2.save)
    assert save_to_dict(depois) != save_to_dict(antes)


def test_cliques_no_menu_ignoram_itens_quando_a_confirmacao_esta_aberta(content, tmp_path):
    h, _ = hub_com_save(content, tmp_path)
    h.click(("menu", "new_game"))
    h.click(("menu", "quit"))
    h.click(("menu", "continue"))
    assert not h.wants_quit and h.mode == "menu" and h.confirm_new


def test_sair_pede_encerramento(content, tmp_path):
    h, _ = hub_disco(content, tmp_path)
    h.click(("menu", "quit"))
    assert h.wants_quit


def test_hub_em_memoria_nao_grava_nada(content, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    h = HubController(content, None, SEED, ai_delay=0.0)
    h.click(("menu", "new_game"))
    h.col.complete()
    assert list(tmp_path.iterdir()) == []


# ------------------------------------------------------------------ save corrompido
def _lixo(p: Path) -> None:
    p.write_bytes(b"\x00\xff\xfe isto nao e json \x80")


def _truncado(p: Path, content) -> None:
    txt = json.dumps(save_to_dict(new_game(content, Random(SEED))))
    p.write_text(txt[: len(txt) // 2], encoding="utf-8")


def _schema_errado(p: Path, content) -> None:
    d = save_to_dict(new_game(content, Random(SEED)))
    d["cats"][0]["iv_atk"] = 99
    p.write_text(json.dumps(d), encoding="utf-8")


def _tipo_errado(p: Path, content) -> None:
    p.write_text(json.dumps({"schema_version": 1, "cats": "nao-lista"}), encoding="utf-8")


def _json_lista(p: Path, content) -> None:
    p.write_text("[1, 2, 3]", encoding="utf-8")


CORRUPCOES = [
    pytest.param(lambda p, c: _lixo(p), id="lixo"),
    pytest.param(_truncado, id="json_truncado"),
    pytest.param(_schema_errado, id="iv_fora_da_faixa"),
    pytest.param(_tipo_errado, id="campos_com_tipo_errado"),
    pytest.param(_json_lista, id="raiz_nao_objeto"),
    pytest.param(lambda p, c: p.write_text("", encoding="utf-8"), id="arquivo_vazio"),
]


@pytest.mark.parametrize("corromper", CORRUPCOES)
def test_save_corrompido_nao_derruba_e_so_permite_novo_jogo(content, tmp_path, corromper):
    p = tmp_path / "save.json"
    corromper(p, content)
    h = HubController(content, p, SEED, ai_delay=0.0)
    assert h.mode == "menu" and h.load_error
    assert not h.can_continue
    assert h.menu_enabled()["continue"] is False and h.menu_enabled()["new_game"]
    assert "orromp" in h.save_summary()
    h.click(("menu", "continue"))
    assert h.mode == "menu"
    # nada impede de desenhar o menu com o aviso
    draw_hub_frame(pygame.Surface((W, H)), h, UIState())


@pytest.mark.parametrize("corromper", CORRUPCOES)
def test_novo_jogo_sobre_save_corrompido_recria_o_save(content, tmp_path, corromper):
    p = tmp_path / "save.json"
    corromper(p, content)
    h = HubController(content, p, SEED, ai_delay=0.0)
    h.click(("menu", "new_game"))
    if h.confirm_new:
        h.click(("confirm_yes",))
    assert h.mode == "colecao" and h.load_error is None
    assert len(read_save(p, content).cats) == len(h.save.cats)


def test_save_corrompido_e_preservado_ate_confirmar_novo_jogo(content, tmp_path):
    p = tmp_path / "save.json"
    _lixo(p)
    antes = p.read_bytes()
    h = HubController(content, p, SEED, ai_delay=0.0)
    h.click(("menu", "new_game"))
    if h.confirm_new:
        assert p.read_bytes() == antes
        h.click(("confirm_no",))
        assert p.read_bytes() == antes


# ------------------------------------------------------------------ falha de gravacao
def caminho_invalido(tmp_path: Path) -> Path:
    arq = tmp_path / "arquivo"
    arq.write_text("x")
    return arq / "sub" / "save.json"      # pai e um arquivo: impossivel criar/gravar


def test_falha_de_gravacao_no_novo_jogo_vira_aviso_sem_excecao(content, tmp_path):
    h = HubController(content, caminho_invalido(tmp_path), SEED, ai_delay=0.0)
    h.click(("menu", "new_game"))
    assert h.mode == "colecao"
    assert h.col.toast is not None and "salvar" in h.col.toast.text.lower()


def test_falha_de_gravacao_ao_mudar_deck_e_renomear_nao_levanta(content, tmp_path):
    h = HubController(content, caminho_invalido(tmp_path), SEED, ai_delay=0.0)
    h.click(("menu", "new_game"))
    h.col.toast = None
    h.col.clear()
    assert h.col.toast is not None and "salvar" in h.col.toast.text.lower()
    h.col.toast = None
    h.col.begin_rename()
    h.col.type_text("Mingau")
    h.col.confirm_rename()
    assert h.col.toast is not None and "salvar" in h.col.toast.text.lower()
    assert h.col.selected_cat().name == "Mingau"      # o estado em memoria segue valido


def test_falha_de_gravacao_com_arquivo_somente_leitura(content, tmp_path):
    h, p = hub_com_save(content, tmp_path)
    entrar_colecao(h)
    p.chmod(0o444)
    try:
        h.col.clear()          # em Windows, chmod leitura pode ou nao bloquear: so nao pode levantar
    finally:
        p.chmod(0o666)
    assert h.col.deck_count == 0


def test_persist_devolve_texto_de_erro(content, tmp_path):
    h = HubController(content, caminho_invalido(tmp_path), SEED, ai_delay=0.0)
    h.adopt_save(new_game(content, Random(SEED)))
    err = h.persist()
    assert isinstance(err, str) and err


def test_falha_de_gravacao_no_fim_da_run_vira_aviso(content, tmp_path):
    h = HubController(content, caminho_invalido(tmp_path), SEED, ai_delay=0.0)
    h.click(("menu", "new_game"))
    h.click(("start",))
    h.key_escape()
    h.click(("quit_yes",))
    assert h.mode == "resultado"
    assert h.toast is not None and "salvar" in h.toast.text.lower()


# ------------------------------------------------------------------ deck
def test_clicar_na_linha_desmarca_e_marca_no_deck(content):
    h = hub_grande(content, 14)
    col = h.col
    assert col.deck_count == 12 and col.deck_text == "Deck 12/12"
    cid = col.save.deck[0]
    clicar_linha(h, cid)
    assert col.deck_count == 11 and col.deck_text == "Deck 11/12" and cid not in col.picked
    clicar_linha(h, cid)
    assert col.deck_count == 12 and cid in col.picked


def test_deck_cheio_nao_aceita_o_13o_gato(content):
    h = hub_grande(content, 14)
    fora = next(c.id for c in h.col.save.cats if c.id not in h.col.picked)
    clicar_linha(h, fora)
    assert h.col.deck_count == 12 and fora not in h.col.picked
    assert h.col.toast is not None


def test_limpar_zera_o_deck(content):
    h = hub_grande(content, 14)
    h.click(("clear",))
    assert h.col.deck_count == 0 and h.col.save.deck == []
    assert not h.col.can_start


def test_completar_usa_autofill_deck(content):
    from core import autofill_deck
    h = hub_grande(content, 20)
    h.click(("clear",))
    parcial = [h.col.rows()[3].cat.id, h.col.rows()[7].cat.id]
    for cid in parcial:
        clicar_linha(h, cid)
    esperado = autofill_deck(content, h.col.save, list(h.col.picked))
    h.click(("complete",))
    assert h.col.picked == esperado and len(esperado) == 12
    assert set(parcial) <= set(h.col.picked)
    assert h.col.save.deck == esperado


def test_iniciar_run_so_com_exatamente_12(content):
    h = hub_grande(content, 14)
    h.click(("clear",))
    for r in h.col.rows()[:11]:
        clicar_linha(h, r.cat.id)
    assert h.col.deck_count == 11 and not h.col.can_start
    h.click(("start",))
    assert h.mode == "colecao" and h.col.toast is not None
    clicar_linha(h, h.col.rows()[11].cat.id)
    assert h.col.can_start
    h.click(("start",))
    assert h.mode == "run" and h.rc is not None


def test_iniciar_run_com_deck_vazio_nao_inicia(content):
    h = hub_grande(content, 14)
    h.click(("clear",))
    h.click(("start",))
    assert h.mode == "colecao"


def test_filhote_e_gato_em_descanso_nao_entram_no_deck(content):
    h = hub_grande(content, 14)
    col = h.col
    livres = [c for c in col.save.cats if c.id not in col.picked]
    livres[0].stage = "kitten"
    livres[1].rest_runs_left = 2
    clicar_linha(h, livres[0].id)
    clicar_linha(h, livres[1].id)
    assert livres[0].id not in col.picked and livres[1].id not in col.picked
    h.click(("clear",))
    h.click(("complete",))
    assert livres[0].id not in col.picked and livres[1].id not in col.picked


def test_deck_parcial_persiste_e_recarrega(content, tmp_path):
    h, p = hub_com_save(content, tmp_path)
    entrar_colecao(h)
    h.click(("clear",))
    escolhidos = [r.cat.id for r in h.col.rows()[:5]]
    for cid in escolhidos:
        clicar_linha(h, cid)
    assert read_save(p, content).deck == escolhidos
    h2 = HubController(content, p, SEED, ai_delay=0.0)
    assert h2.can_continue
    entrar_colecao(h2)
    assert h2.col.picked == escolhidos and h2.col.deck_text == "Deck 5/12"
    assert not h2.col.can_start


def test_mudar_deck_grava_o_arquivo_a_cada_clique(content, tmp_path):
    h, p = hub_com_save(content, tmp_path)
    entrar_colecao(h)
    cid = h.col.save.deck[0]
    clicar_linha(h, cid)
    assert cid not in read_save(p, content).deck
    clicar_linha(h, cid)
    assert cid in read_save(p, content).deck
    h.click(("clear",))
    assert read_save(p, content).deck == []
    h.click(("complete",))
    assert len(read_save(p, content).deck) == 12


def test_save_com_deck_invalido_ignora_ids_inexistentes_e_repetidos(content):
    s = new_game(content, Random(SEED))
    s.deck = [s.cats[0].id, s.cats[0].id, "c-999999", s.cats[1].id]
    h = HubController(content, None, SEED)
    h.adopt_save(s)
    assert h.col.picked == [s.cats[0].id, s.cats[1].id]


# ------------------------------------------------------------------ renomear
def renomear(h: HubController, texto: str) -> None:
    h.click(("rename",))
    h.text_input(texto)
    h.key_enter()


def test_renomear_confirma_com_enter_e_grava_no_arquivo(content, tmp_path):
    h, p = hub_com_save(content, tmp_path)
    entrar_colecao(h)
    cid = h.col.selected
    h.click(("rename",))
    assert h.editing_text
    h.text_input("Mingau")
    h.key_enter()
    assert not h.editing_text
    assert h.col.selected_cat().name == "Mingau"
    s = read_save(p, content)
    assert next(c for c in s.cats if c.id == cid).name == "Mingau"


def test_renomear_aceita_acentos(content, tmp_path):
    h, p = hub_com_save(content, tmp_path)
    entrar_colecao(h)
    renomear(h, "Pelúcia Çã")
    cid = h.col.selected
    assert next(c for c in read_save(p, content).cats if c.id == cid).name == "Pelúcia Çã"


def test_renomear_backspace_apaga_ultimo_caractere(content):
    h = hub_grande(content, 12)
    h.click(("rename",))
    h.text_input("Abcd")
    h.backspace()
    assert h.col.edit == "Abc"
    for _ in range(10):
        h.backspace()
    assert h.col.edit == ""


def test_renomear_limita_em_16_caracteres(content):
    h = hub_grande(content, 12)
    h.click(("rename",))
    h.text_input("x" * 40)
    assert len(h.col.edit) == 16 and h.col.edit_counter() == "16/16"
    h.key_enter()
    assert len(h.col.selected_cat().name) == 16


def test_renomear_esc_cancela_sem_alterar_nem_gravar(content, tmp_path):
    h, p = hub_com_save(content, tmp_path)
    entrar_colecao(h)
    antes = p.read_bytes()
    nome_antes = h.col.selected_cat().name
    h.click(("rename",))
    h.text_input("Descartado")
    h.key_escape()
    assert not h.editing_text and h.mode == "colecao"
    assert h.col.selected_cat().name == nome_antes
    assert p.read_bytes() == antes


def test_renomear_vazio_volta_ao_nome_padrao(content, tmp_path):
    h, p = hub_com_save(content, tmp_path)
    entrar_colecao(h)
    cid = h.col.selected
    renomear(h, "Mingau")
    h.click(("rename",))
    for _ in range(20):
        h.backspace()
    h.key_enter()
    assert h.col.selected_cat().name is None
    assert h.col.row_of(h.col.selected_cat()).label == h.col.row_of(h.col.selected_cat()).breed
    assert next(c for c in read_save(p, content).cats if c.id == cid).name is None


def test_renomear_so_espacos_vira_nome_padrao(content):
    h = hub_grande(content, 12)
    renomear(h, "   ")
    assert h.col.selected_cat().name is None


def test_renomear_pelos_botoes_confirmar_e_cancelar(content):
    h = hub_grande(content, 12)
    h.click(("rename",))
    h.text_input("Bola")
    h.click(("rename_cancel",))
    assert h.col.selected_cat().name is None and not h.editing_text
    h.click(("rename",))
    h.text_input("Bola")
    h.click(("rename_ok",))
    assert h.col.selected_cat().name == "Bola"


def test_renomear_bloqueia_cliques_na_lista_e_texto_fora_da_edicao_e_ignorado(content):
    h = hub_grande(content, 14)
    pick_antes = list(h.col.picked)
    h.text_input("abc")                       # sem edicao aberta: nada
    assert h.col.edit is None
    h.click(("rename",))
    clicar_linha(h, h.col.save.deck[0])
    h.click(("clear",))
    assert h.col.picked == pick_antes and h.editing_text


def test_renomear_ignora_caracteres_nao_imprimiveis(content):
    h = hub_grande(content, 12)
    h.click(("rename",))
    h.text_input("a\n\t\x00b")
    assert h.col.edit == "ab"


def test_renomear_comeca_com_o_nome_atual(content):
    h = hub_grande(content, 12)
    renomear(h, "Mingau")
    h.click(("rename",))
    assert h.col.edit == "Mingau"


def test_nome_com_acento_fora_da_fonte_nao_quebra(content, tmp_path):
    h, p = hub_com_save(content, tmp_path)
    entrar_colecao(h)
    nome = "Mãe ñandú ïë €☃"[:16]
    renomear(h, nome)
    assert h.col.selected_cat().name == nome.strip()
    surf = pygame.Surface((W, H))
    draw_hub_frame(surf, h, UIState(t=0.2))           # lista + detalhe
    h.click(("rename",))
    draw_hub_frame(surf, h, UIState(t=0.2))           # campo de edicao
    h.key_escape()
    assert next(c for c in read_save(p, content).cats
                if c.id == h.col.selected).name == nome.strip()


def test_renomear_sem_gato_selecionado_avisa(content):
    h = HubController(content, None, SEED)
    s = new_game(content, Random(SEED))
    s.cats, s.deck = [], []
    h.adopt_save(s)
    h.mode = "colecao"
    h.click(("rename",))
    assert not h.editing_text and h.col.toast is not None


# ------------------------------------------------------------------ ordenacao, filtro, rolagem
def test_ordenacao_por_poder_e_decrescente_em_atk_mais_hp(content):
    h = hub_grande(content, 30)
    h.click(("sort", "poder"))
    pod = [r.stats.atk + r.stats.hp for r in h.col.rows()]
    assert pod == sorted(pod, reverse=True)


def test_ordenacao_por_raca_agrupa_e_por_nome_e_alfabetica(content):
    h = hub_grande(content, 30)
    h.click(("sort", "raca"))
    racas = [r.breed for r in h.col.rows()]
    assert racas == sorted(racas)
    for i, r in enumerate(h.col.save.cats):
        if i % 3 == 0:
            r.name = f"Gato{i:02d}"
    h.click(("sort", "nome"))
    nomes = [r.label.lower() for r in h.col.rows()]
    assert nomes == sorted(nomes)


@pytest.mark.parametrize("chave", ["poder", "raca", "nome"])
def test_ordenacao_e_deterministica_e_nao_perde_gatos(content, chave):
    h = hub_grande(content, 30)
    h.click(("sort", chave))
    a = [r.cat.id for r in h.col.rows()]
    b = [r.cat.id for r in h.col.rows()]
    h2 = hub_grande(content, 30)
    h2.click(("sort", chave))
    assert a == b == [r.cat.id for r in h2.col.rows()]
    assert sorted(a) == sorted(c.id for c in h.col.save.cats)


def test_filtro_de_raca_cicla_por_todas_as_racas_presentes_e_volta_a_todas(content):
    h = hub_grande(content, 30)
    presentes = {c.breed for c in h.col.save.cats}
    vistos = []
    for _ in range(len(presentes)):
        h.click(("filter",))
        assert h.col.filter_breed in presentes
        vistos.append(h.col.filter_breed)
        assert {r.cat.breed for r in h.col.rows()} == {h.col.filter_breed}
    assert set(vistos) == presentes
    h.click(("filter",))
    assert h.col.filter_breed is None
    assert len(h.col.rows()) == 30


def test_filtro_e_ordenacao_zeram_a_rolagem(content):
    h = hub_grande(content, 30)
    h.scroll(5)
    assert h.col.scroll == 5
    h.click(("sort", "nome"))
    assert h.col.scroll == 0
    h.scroll(5)
    h.click(("filter",))
    assert h.col.scroll == 0


def test_filtro_nao_altera_o_deck(content):
    h = hub_grande(content, 30)
    antes = list(h.col.picked)
    h.click(("filter",))
    assert h.col.picked == antes


def test_rolagem_com_30_gatos_mostra_as_linhas_visiveis_e_limita_nas_pontas(content):
    n = LH.ROWS_VISIBLE
    h = hub_grande(content, 30)
    col = h.col
    assert len(col.visible_rows()) == n
    assert col.max_scroll() == 30 - n
    h.scroll(-3)
    assert col.scroll == 0
    h.scroll(5)
    assert col.scroll == 5
    h.scroll(1000)
    assert col.scroll == 30 - n
    ult = col.visible_rows()
    assert len(ult) == n and ult[-1].cat.id == col.rows()[-1].cat.id
    h.click(("scroll", -1))
    assert col.scroll == 30 - n - 1
    h.click(("scroll", 1))
    h.click(("scroll", 1))
    assert col.scroll == 30 - n


def test_rolagem_muda_as_linhas_visiveis_e_clique_acerta_o_gato_certo(content):
    h = hub_grande(content, 30)
    col = h.col
    todas = [r.cat.id for r in col.rows()]
    n = LH.ROWS_VISIBLE
    assert col.visible_ids() == todas[:n]
    h.scroll(10)
    assert col.visible_ids() == todas[10:10 + n]
    for i in (0, n - 1):
        elem = h.hit(LH.row_rect(i).center)
        assert elem == ("row", todas[10 + i])
    alvo = todas[10]
    antes = alvo in col.picked
    h.click(h.hit(LH.row_rect(0).center))
    assert (alvo in col.picked) != antes


def test_botoes_de_rolagem_por_hit_test(content):
    h = hub_grande(content, 30)
    assert h.hit(LH.scroll_down_rect().center) == ("scroll", 1)
    assert h.hit(LH.scroll_up_rect().center) == ("scroll", -1)
    h.click(h.hit(LH.scroll_down_rect().center))
    assert h.col.scroll == 1


def test_sem_rolagem_quando_cabe_nas_linhas_visiveis(content):
    h = hub_grande(content, 12)
    total = len(h.col.rows())
    assert h.col.max_scroll() == max(0, total - LH.ROWS_VISIBLE)
    h.col.filter_breed = "inexistente"          # lista vazia cabe sempre
    assert h.col.max_scroll() == 0
    h.scroll(5)
    assert h.col.scroll == 0


def test_rolagem_ignorada_durante_a_edicao(content):
    h = hub_grande(content, 30)
    h.click(("rename",))
    h.scroll(5)
    assert h.col.scroll == 0


def test_rolagem_se_ajusta_quando_o_filtro_reduz_a_lista(content):
    h = hub_grande(content, 30)
    h.scroll(16)
    h.click(("filter",))
    assert h.col.scroll <= h.col.max_scroll()
    assert len(h.col.visible_rows()) <= LH.ROWS_VISIBLE


def test_lista_vazia_com_filtro_sem_gatos_nao_quebra(content):
    h = hub_grande(content, 12)
    h.col.filter_breed = "inexistente"
    assert h.col.rows() == [] and h.col.visible_rows() == []
    draw_hub_frame(pygame.Surface((W, H)), h, UIState())


def test_save_com_30_gatos_renderiza_e_persiste(content, tmp_path):
    p = tmp_path / "save.json"
    write_save(save_grande(content, 30), p)
    h = HubController(content, p, SEED, ai_delay=0.0)
    entrar_colecao(h)
    assert len(h.col.rows()) == 30
    h.scroll(16)
    draw_hub_frame(pygame.Surface((W, H)), h, UIState(t=0.1))


def test_estatisticas_da_linha_vem_do_core(content):
    h = hub_grande(content, 12)
    for r in h.col.rows():
        assert r.stats == cat_stats(content, r.cat)


# ------------------------------------------------------------------ fim da run
def iniciar_run(h: HubController) -> None:
    h.click(("menu", "new_game"))
    if h.confirm_new:
        h.click(("confirm_yes",))
    h.click(("start",))
    assert h.mode == "run"


def abandonar(h: HubController) -> None:
    h.key_escape()
    h.click(("quit_yes",))


def test_abandonar_a_run_mostra_resultado_e_volta_a_colecao(content, tmp_path):
    h, p = hub_disco(content, tmp_path)
    iniciar_run(h)
    abandonar(h)
    assert h.mode == "resultado" and h.rc is None
    assert h.result_text == "Run encerrada: derrota, nós vencidos 0"
    assert h.result_detail and "abandon" in h.result_detail[0]
    h.click(h.hit(LH.result_button().center))
    assert h.mode == "colecao"
    assert h.col.deck_count == 12


@pytest.mark.parametrize("como", ["enter", "esc"])
def test_resultado_volta_a_colecao_por_teclado(content, tmp_path, como):
    h, _ = hub_disco(content, tmp_path)
    iniciar_run(h)
    abandonar(h)
    (h.key_enter if como == "enter" else h.key_escape)()
    assert h.mode == "colecao"


def test_fim_da_run_grava_o_save(content, tmp_path):
    h, p = hub_disco(content, tmp_path)
    iniciar_run(h)
    p.unlink()
    abandonar(h)
    assert p.exists()
    assert len(read_save(p, content).cats) >= 12


def test_esc_no_mapa_pede_confirmacao_antes_de_abandonar(content, tmp_path):
    h, _ = hub_disco(content, tmp_path)
    iniciar_run(h)
    h.key_escape()
    assert h.mode == "run"
    h.click(("quit_no",))
    assert h.mode == "run"


def test_nova_run_usa_semente_diferente_e_funciona_em_sequencia(content, tmp_path):
    h, _ = hub_disco(content, tmp_path)
    iniciar_run(h)
    abandonar(h)
    h.key_enter()
    h.click(("start",))
    assert h.mode == "run" and h.runs_started == 2


def test_esc_na_colecao_volta_ao_menu_e_esc_na_edicao_so_cancela(content):
    h = hub_grande(content, 12)
    h.click(("rename",))
    h.key_escape()
    assert h.mode == "colecao" and not h.editing_text
    h.key_escape()
    assert h.mode == "menu"
    h.click(("menu", "continue"))
    assert h.mode == "colecao"


# ------------------------------------------------------------------ layout
TELA = pygame.Rect(0, 0, W, H)


def test_tela_interna_e_960x540_nativa():
    from ui import theme
    assert (theme.W, theme.H) == (960, 540)
    assert (W, H) == (960, 540)
    assert not hasattr(theme, "LW") and not hasattr(theme, "LH")


def rects_menu() -> dict[str, pygame.Rect]:
    d = {f"menu_{i}": LH.menu_button(i) for i in range(len(LH.MENU_ITEMS))}
    return d


def rects_confirm() -> dict[str, pygame.Rect]:
    return dict(LH.confirm_buttons())


def rects_colecao() -> dict[str, pygame.Rect]:
    d = {f"row_{i}": LH.row_rect(i) for i in range(LH.ROWS_VISIBLE)}
    d |= {"scroll_up": LH.scroll_up_rect(), "scroll_down": LH.scroll_down_rect()}
    d |= {f"sort_{i}": LH.sort_button(i) for i in range(3)}
    d |= {"filter": LH.filter_button(), "detail": LH.detail_panel()}
    d |= dict(LH.action_buttons())
    return d


def rects_renomear() -> dict[str, pygame.Rect]:
    d = dict(LH.rename_buttons())
    d["input"] = LH.rename_input()
    return d


def sem_sobreposicao(rs: dict[str, pygame.Rect]) -> None:
    for (na, a), (nb, b) in combinations(rs.items(), 2):
        assert not a.colliderect(b), f"{na} {a} sobrepoe {nb} {b}"


@pytest.mark.parametrize("nome,fn", [
    ("menu", rects_menu), ("confirmacao", rects_confirm), ("colecao", rects_colecao),
    ("renomear", rects_renomear)])
def test_layout_retangulos_dentro_da_tela_e_sem_sobreposicao(nome, fn):
    rs = fn()
    for n, r in rs.items():
        assert TELA.contains(r) and r.w > 0 and r.h > 0, f"{nome}/{n} fora da tela: {r}"
    sem_sobreposicao(rs)


def test_layout_paineis_dentro_da_tela_e_botoes_dentro_dos_paineis():
    for r in (LH.confirm_panel(), LH.rename_panel(), LH.menu_info_rect(), LH.result_button()):
        assert TELA.contains(r)
    for r in LH.confirm_buttons().values():
        assert LH.confirm_panel().contains(r)
    for r in (*LH.rename_buttons().values(), LH.rename_input()):
        assert LH.rename_panel().contains(r)
    assert LH.detail_panel().contains(LH.rename_button())
    # os botoes do menu nao invadem a area de informacao do save
    for i in range(3):
        assert not LH.menu_button(i).colliderect(LH.menu_info_rect())


def test_layout_botao_renomear_nao_sobrepoe_acoes():
    rb = LH.rename_button()
    for r in LH.action_buttons().values():
        assert not rb.colliderect(r)


def test_layout_da_lista_nao_invade_o_painel_de_detalhe():
    d = LH.detail_panel()
    for i in range(LH.ROWS_VISIBLE):
        assert not LH.row_rect(i).colliderect(d)
    assert not LH.scroll_up_rect().colliderect(d)


def test_hit_test_menu(content):
    h = HubController(content, None, SEED)
    for i, item in enumerate(LH.MENU_ITEMS):
        assert h.hit(LH.menu_button(i).center) == ("menu", item)
        r = LH.menu_button(i)
        assert h.hit(r.topleft) == ("menu", item)
        assert h.hit((r.right, r.centery)) is None
    assert h.hit((0, 0)) is None


def test_hit_test_confirmacao_so_responde_pelos_dois_botoes(content):
    h = HubController(content, None, SEED)
    h.confirm_new = True
    b = LH.confirm_buttons()
    assert h.hit(b["confirm_yes"].center) == ("confirm_yes",)
    assert h.hit(b["confirm_no"].center) == ("confirm_no",)
    assert h.hit(LH.menu_button(0).center) is None


def test_hit_test_colecao(content):
    h = hub_grande(content, 14)
    ids = h.col.visible_ids()
    assert h.hit(LH.row_rect(0).center) == ("row", ids[0])
    last = LH.ROWS_VISIBLE - 1
    assert h.hit(LH.row_rect(last).center) == ("row", ids[last])
    for i, k in enumerate(LH.SORT_KEYS):
        assert h.hit(LH.sort_button(i).center) == ("sort", k)
    assert h.hit(LH.filter_button().center) == ("filter",)
    assert h.hit(LH.rename_button().center) == ("rename",)
    for nome, r in LH.action_buttons().items():
        assert h.hit(r.center) == (nome,)
    assert h.hit((W - 1, H - 1)) is None


def test_hit_test_linha_vazia_nao_responde_com_poucos_gatos(content):
    h = hub_grande(content, 12)
    n = LH.ROWS_VISIBLE
    assert len(h.col.visible_ids()) == min(12, n)
    if n > 12:
        assert h.hit(LH.row_rect(n - 1).center) is None
    assert h.hit(LH.row_rect(min(12, n) - 1).center) == ("row", h.col.visible_ids()[min(12, n) - 1])
    assert h.hit((W - 1, H - 1)) is None


def test_hit_test_renomear(content):
    h = hub_grande(content, 12)
    h.click(("rename",))
    b = LH.rename_buttons()
    assert h.hit(b["rename_ok"].center) == ("rename_ok",)
    assert h.hit(b["rename_cancel"].center) == ("rename_cancel",)
    assert h.hit(LH.row_rect(0).center) is None
    assert h.hit(LH.action_buttons()["clear"].center) is None


def test_hit_test_resultado(content):
    h = hub_grande(content, 12)
    h.mode = "resultado"
    assert h.hit(LH.result_button().center) == ("result_back",)
    assert h.hit((0, 0)) is None


# ------------------------------------------------------------------ renderizacao (smoke)
@pytest.mark.parametrize("cena", HUB_SCENES)
def test_cena_renderiza_headless_e_desenha_algo(cena):
    assert set(HUB_SCENES) == {"menu", "menu_confirmar", "menu_corrompido", "colecao",
                               "colecao_deck", "renomear", "resultado", "adocao",
                               "adocao_vazia", "doar_confirmar"}
    hub, ui = make(SEED, cena)
    surf = pygame.Surface((W, H))
    surf.fill((0, 0, 0))
    draw_hub_frame(surf, hub, ui)
    cores = {surf.get_at((x, y))[:3] for x in range(0, W, 7) for y in range(0, H, 7)}
    assert len(cores) > 4, f"cena {cena} parece vazia"


@pytest.mark.parametrize("cena", HUB_SCENES)
def test_cena_e_deterministica_por_seed(cena):
    def quadro() -> bytes:
        hub, ui = make(SEED, cena)
        surf = pygame.Surface((W, H))
        draw_hub_frame(surf, hub, ui)
        return pygame.image.tobytes(surf, "RGB")
    assert quadro() == quadro()


def test_cena_desconhecida_e_recusada():
    with pytest.raises(SystemExit):
        make(SEED, "nao_existe")


def test_cena_menu_corrompido_tem_estado_coerente():
    hub, _ = make(SEED, "menu_corrompido")
    assert hub.load_error and not hub.can_continue and hub.has_file


def test_render_do_menu_sem_save_com_caminho_e_com_toast(content, tmp_path):
    h, _ = hub_disco(content, tmp_path)
    h.say("Teste de aviso")
    draw_hub_frame(pygame.Surface((W, H)), h, UIState())
    h.update(10.0)
    assert h.toast is None


def test_render_da_run_dentro_do_hub(content, tmp_path):
    h, _ = hub_disco(content, tmp_path)
    iniciar_run(h)
    draw_hub_frame(pygame.Surface((W, H)), h, UIState(t=0.1))
    h.update(0.1)


def test_render_da_colecao_com_nomes_longos_e_filhotes(content):
    h = hub_grande(content, 30)
    for i, c in enumerate(h.col.save.cats):
        c.name = "W" * 16 if i % 2 else None
    h.col.save.cats[3].stage = "kitten"
    h.col.save.cats[4].rest_runs_left = 3
    draw_hub_frame(pygame.Surface((W, H)), h, UIState(t=0.1))
