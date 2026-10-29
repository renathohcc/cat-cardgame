"""Formato dos spritesheet.json em assets/ (T8.6): imagem existe, retangulos dentro do `size`,
nomes cobrem os ids de data/. Somente leitura de arquivos; so o pygame le o tamanho do PNG."""
from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
import pytest

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
DATA = ROOT / "data"
SHEETS = sorted(ASSETS.glob("*/spritesheet*.json"))


def ids(arquivo: str, chave: str) -> set[str]:
    return {x["id"] for x in json.loads((DATA / arquivo).read_text(encoding="utf-8"))[chave]}


def nomes(pasta: str, nome_json: str = "spritesheet.json") -> set[str]:
    return set(json.loads((ASSETS / pasta / nome_json).read_text(encoding="utf-8"))["sprites"])


def rel(p: Path) -> str:
    return str(p.relative_to(ASSETS)).replace("\\", "/")


def test_existem_sheets_para_todos_os_tipos():
    pastas = {p.parent.name for p in SHEETS}
    assert {"cats", "cats96", "specials", "specials96", "effects", "effects96",
            "icons", "icons16", "leaders"} <= pastas


@pytest.mark.parametrize("path", SHEETS, ids=rel)
def test_sheet_tem_imagem_existente_e_retangulos_dentro_do_size(path):
    d = json.loads(path.read_text(encoding="utf-8"))
    assert set(d) >= {"image", "size", "sprites"}
    png = path.parent / d["image"]
    assert png.is_file(), f"{png.name} nao existe"
    w, h = d["size"]
    assert pygame.image.load(str(png)).get_size() == (w, h), "size do json difere do PNG"
    assert d["sprites"], "sheet vazio"
    for nome, r in d["sprites"].items():
        assert set(r) >= {"x", "y", "w", "h"}, nome
        assert r["w"] > 0 and r["h"] > 0, nome
        assert r["x"] >= 0 and r["y"] >= 0, nome
        assert r["x"] + r["w"] <= w and r["y"] + r["h"] <= h, f"{nome} fora do sheet"


@pytest.mark.parametrize("path", SHEETS, ids=rel)
def test_sprites_do_sheet_nao_se_sobrepoem_e_tem_tamanho_uniforme(path):
    sp = json.loads(path.read_text(encoding="utf-8"))["sprites"]
    rects = [(n, pygame.Rect(r["x"], r["y"], r["w"], r["h"])) for n, r in sp.items()]
    assert len({(r.w, r.h) for _, r in rects}) == 1, "tamanhos misturados"
    for i, (na, a) in enumerate(rects):
        for nb, b in rects[i + 1:]:
            assert not a.colliderect(b), f"{na} sobrepoe {nb}"


@pytest.mark.parametrize("pasta,tam", [("cats", 48), ("cats96", 96), ("specials", 48), ("specials96", 96),
                                       ("effects", 48), ("effects96", 96), ("icons", 9), ("icons16", 16)])
def test_tamanho_de_cada_sprite_do_sheet(pasta, tam):
    sp = json.loads((ASSETS / pasta / "spritesheet.json").read_text(encoding="utf-8"))["sprites"]
    assert all(r["w"] == tam and r["h"] == tam for r in sp.values())


@pytest.mark.parametrize("pasta", ["cats", "cats96"])
def test_sheet_de_gatos_tem_todas_as_racas(pasta):
    assert ids("breeds.json", "breeds") <= nomes(pasta)


@pytest.mark.parametrize("pasta", ["specials", "specials96"])
def test_sheet_de_especiais_tem_todos_os_gatos_especiais(pasta):
    assert ids("specials.json", "specials") <= nomes(pasta)


@pytest.mark.parametrize("pasta", ["effects", "effects96"])
def test_sheet_de_efeitos_tem_todas_as_cartas_de_efeito(pasta):
    assert ids("effects.json", "effects") <= nomes(pasta)


@pytest.mark.parametrize("nome_json", ["spritesheet.json", "spritesheet128.json"])
def test_sheet_de_lideres_tem_inimigos_e_heroi(nome_json):
    assert ids("enemies.json", "enemies") | {"heroi"} <= nomes("leaders", nome_json)


def test_lideres_128_tem_128_de_lado():
    sp = json.loads((ASSETS / "leaders" / "spritesheet128.json").read_text(encoding="utf-8"))["sprites"]
    assert all(r["w"] == 128 and r["h"] == 128 for r in sp.values())


@pytest.mark.parametrize("pasta", ["icons", "icons16"])
def test_sheet_de_icones_tem_keywords_e_acoes_de_efeito(pasta):
    kws = ids("keywords.json", "keywords")
    tipos = {a["tipo"] for e in json.loads((DATA / "effects.json").read_text(encoding="utf-8"))["effects"]
             for a in e["acoes"]}
    esperado = kws | {f"acao-{t}" for t in tipos}
    assert esperado <= nomes(pasta), esperado - nomes(pasta)


def test_pecas_do_tema_noturno_existem_e_tem_o_tamanho_declarado():
    meta = json.loads((ASSETS / "ui" / "noturno" / "ui.json").read_text(encoding="utf-8"))["pieces"]
    assert meta
    for nome, info in meta.items():
        png = ASSETS / "ui" / info["file"]
        assert png.is_file(), nome
        assert pygame.image.load(str(png)).get_size() == (info["w"], info["h"]), nome
        if "nine_slice" in info:
            l, t, r, b = info["nine_slice"]
            assert l + r < info["w"] and t + b < info["h"], f"{nome}: 9-slice maior que a peca"


def test_tabuleiro_noturno_e_960x540():
    img = pygame.image.load(str(ASSETS / "board" / "final" / "board_noturno.png"))
    assert img.get_size() == (960, 540)


@pytest.mark.parametrize("stem", ["chaoscats_16", "chaoscats_32"])
def test_fonte_bitmap_json_aponta_para_png_e_glifos_dentro_da_imagem(stem):
    d = json.loads((ASSETS / "fonts" / f"{stem}.json").read_text(encoding="utf-8"))
    img = pygame.image.load(str(ASSETS / "fonts" / d["image"]))
    w, h = img.get_size()
    assert d["glyphs"]
    for ch, g in d["glyphs"].items():
        assert g["x"] >= 0 and g["y"] >= 0 and g["x"] + g["w"] <= w and g["y"] + g["h"] <= h, repr(ch)
    for ch in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789":
        assert ch in d["glyphs"], ch
