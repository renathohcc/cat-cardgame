"""Fluxo real da economia na UI (Fase 10a, T13.5): save v1 em disco -> migracao -> `save.v1.bak` ->
runs jogadas pela IA -> fim de run com moedas -> comprar area -> reabrir o save.

Tambem cobre a UI diante de aviso de backup falho (pendencia da T13.1c). Headless (SDL dummy);
o save e a pasta sao temporarios, `saves/save.json` real nunca e tocado."""
from __future__ import annotations

import json
from random import Random

import pytest

from core import kennel_slots, occupied, read_save
from core import save as core_save
from ui.scenes_run import autoplay
from ui_eco_helpers import (area_def, buy_area_at_yard, draw_texts, game_content, new_hub, to_result, write_v1)


@pytest.fixture(scope="module")
def c():
    return game_content()


def versao(p) -> int:
    return json.loads(p.read_text("utf-8"))["schema_version"]


def jogar_uma_run(h, seed: int) -> None:
    """Inicia a run pelo botao do cercado, joga com a IA ate o fim e volta ao cercado."""
    assert h.mode == "cercado"
    h.click(("pen_btn", "start"))
    assert h.mode == "run"
    autoplay(h.rc, Random(seed))
    h.update(0.0)                                  # o hub percebe o fim da run
    assert h.rc is None and h.summary is not None
    to_result(h)
    if h.mode == "resultado":
        h.click(("result_back",))
    assert h.mode == "cercado"


def test_fluxo_completo_v1_migracao_backup_run_moedas_compra_e_reabrir(c, tmp_path):
    p = tmp_path / "saves" / "save.json"
    original = write_v1(p, c, coins=0)
    bak = p.with_name("save.v1.bak")
    price = area_def(c, 0)["price"]

    # 1. abrir o v1: migra em memoria, nada e escrito ainda
    h = new_hub(p)
    assert h.can_continue and h.load_error is None and h.save.migrated_from == 1
    assert p.read_bytes() == original and not bak.exists()
    h.click(("menu", "continue"))
    assert h.mode == "cercado" and h.save.prestige == 1 and h.save.coins == 0

    # 2. primeira run: o primeiro save grava v2 e cria o backup do v1
    jogar_uma_run(h, 1)
    assert h.summary.settlement.counted
    assert versao(p) == 2 and bak.read_bytes() == original and versao(bak) == 1

    # 3. mais runs ate juntar o preco da area; o backup nunca muda
    n = 1
    while h.save.coins < price and n < 15:
        n += 1
        jogar_uma_run(h, n)
        assert bak.read_bytes() == original
    assert h.save.coins >= price, "a IA deveria juntar o preco da 1a area em poucas runs"
    assert h.save.lifetime["runs_completed"] >= 1

    # 4. fim de run deu moedas e o dinheiro e o do save em disco
    em_disco = read_save(p, c)
    assert em_disco.coins == h.save.coins

    # 5. comprar a area pelo quintal
    moedas, vagas = h.save.coins, kennel_slots(c, h.save)
    buy_area_at_yard(h, area_def(c, 0)["id"])
    assert area_def(c, 0)["id"] in h.save.areas_unlocked
    assert h.save.coins == moedas - price
    assert kennel_slots(c, h.save) == vagas + area_def(c, 0)["slots_bonus"]
    assert f"{occupied(h.save)}/{kennel_slots(c, h.save)}" in draw_texts(h)

    # 6. reabrir o save: tudo continua la, ja em v2, backup intacto
    h2 = new_hub(p)
    s2 = h2.save
    assert h2.can_continue and s2.migrated_from is None
    assert area_def(c, 0)["id"] in s2.areas_unlocked and s2.coins == moedas - price
    assert kennel_slots(c, s2) == vagas + area_def(c, 0)["slots_bonus"]
    assert s2.lifetime == h.save.lifetime and s2.prestige == h.save.prestige
    assert len(s2.cats) == len(h.save.cats) and s2.deck == h.save.deck
    h2.click(("menu", "continue"))
    assert f"{occupied(s2)}/{kennel_slots(c, s2)}" in draw_texts(h2)
    assert h2.shop.area(area_def(c, 0)["id"]).done
    assert bak.read_bytes() == original and versao(bak) == 1


def test_reabrir_depois_da_migracao_e_gravar_de_novo_nao_recria_backup(c, tmp_path):
    p = tmp_path / "save.json"
    original = write_v1(p, c)
    h = new_hub(p)
    h.click(("menu", "continue"))
    assert h.persist() is None
    h2 = new_hub(p)
    h2.click(("menu", "continue"))
    h2.save.coins += 5
    assert h2.persist() is None
    assert p.with_name("save.v1.bak").read_bytes() == original
    assert sorted(f.name for f in tmp_path.iterdir()) == ["save.json", "save.v1.bak"]


def test_novo_jogo_sobre_v1_migrado_nao_perde_o_backup_v1(c, tmp_path):
    """O `.bak` do Novo Jogo (independente) nao pode apagar o `save.v1.bak`."""
    p = tmp_path / "save.json"
    original = write_v1(p, c)
    h = new_hub(p)
    h.click(("menu", "continue"))
    h.persist()                                              # v1 -> v2, cria save.v1.bak
    h.mode = "menu"
    h.click(("menu", "new_game"))
    h.click(("confirm_yes",))
    assert p.with_name("save.v1.bak").read_bytes() == original


def test_v1_com_moedas_e_gatos_chega_integro_na_ui(c, tmp_path):
    p = tmp_path / "save.json"
    write_v1(p, c, coins=9)
    h = new_hub(p)
    h.click(("menu", "continue"))
    assert h.save.coins == 9 and len(h.save.cats) == 12 and len(h.save.deck) == 12
    assert "9" in draw_texts(h)
    assert f"{occupied(h.save)}/{kennel_slots(c, h.save)}" in draw_texts(h)


# ====================================================================== AVISO DE BACKUP FALHO NA UI
def falha_no_backup(monkeypatch) -> None:
    def quebra(*a, **k):
        raise PermissionError("disco somente leitura")
    monkeypatch.setattr(core_save.shutil, "copyfile", quebra)


def textos_de_aviso(h) -> list[str]:
    toasts = [h.toast, h.shop.toast if h.shop else None, h.col.toast if h.col else None]
    return [t.text for t in toasts if t is not None]


def test_backup_falho_nao_derruba_a_ui_e_o_save_v2_e_gravado(c, tmp_path, monkeypatch):
    p = tmp_path / "save.json"
    write_v1(p, c)
    falha_no_backup(monkeypatch)
    h = new_hub(p)
    h.click(("menu", "continue"))
    h.save.coins = area_def(c, 0)["price"]
    buy_area_at_yard(h, area_def(c, 0)["id"])
    assert area_def(c, 0)["id"] in h.save.areas_unlocked          # a compra vale
    assert versao(p) == 2 and read_save(p, c).coins == 0           # e o save novo foi gravado
    assert not p.with_name("save.v1.bak").exists()
    draw_texts(h)                                                 # tela segue desenhando


def test_backup_falho_do_v1_avisa_o_jogador_na_ui(c, tmp_path, monkeypatch):
    p = tmp_path / "save.json"
    write_v1(p, c)
    falha_no_backup(monkeypatch)
    h = new_hub(p)
    h.click(("menu", "continue"))
    erro = h.persist()
    avisos = textos_de_aviso(h)
    assert erro or any("backup" in t.lower() for t in avisos)


def test_backup_falho_do_v1_aparece_em_toast_depois_de_comprar_area(c, tmp_path, monkeypatch):
    p = tmp_path / "save.json"
    write_v1(p, c)
    falha_no_backup(monkeypatch)
    h = new_hub(p)
    h.click(("menu", "continue"))
    h.save.coins = area_def(c, 0)["price"]
    buy_area_at_yard(h, area_def(c, 0)["id"])
    assert any("backup" in t.lower() for t in textos_de_aviso(h))
