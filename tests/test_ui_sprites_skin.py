"""ui.sprites e ui.skin (T8.6): tamanhos, fallback sem arquivo, preferencia do sheet novo, 9-slice."""
from __future__ import annotations

import json
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
import pytest

from ui import skin, sprites
from ui.controller import Controller, load_game_content
from ui.render import UIState, draw_frame
from ui.theme import H, W

RACAS = ["vira-lata", "siames", "persa", "sphynx", "maine-coon"]


@pytest.fixture(autouse=True)
def caches_limpos():
    sprites.reset()
    skin.reset()
    yield
    sprites.reset()
    skin.reset()


@pytest.fixture
def raiz_falsa(tmp_path, monkeypatch):
    """Aponta sprites._ROOT para uma pasta temporaria (assets de mentira)."""
    monkeypatch.setattr(sprites, "_ROOT", tmp_path)
    sprites.reset()
    yield tmp_path
    monkeypatch.undo()
    sprites.reset()


def faz_sheet(raiz, pasta: str, nomes: list[str], lado: int, cor: tuple[int, int, int],
              json_name: str = "spritesheet.json") -> None:
    d = raiz / pasta
    d.mkdir(parents=True, exist_ok=True)
    img = pygame.Surface((lado * len(nomes), lado))
    img.fill(cor)
    pygame.image.save(img, str(d / "sheet.png"))
    (d / json_name).write_text(json.dumps({
        "image": "sheet.png", "size": [lado * len(nomes), lado],
        "sprites": {n: {"x": i * lado, "y": 0, "w": lado, "h": lado} for i, n in enumerate(nomes)}}),
        encoding="utf-8")


# ------------------------------------------------------------------ sprites com os assets reais
@pytest.mark.parametrize("raca", RACAS)
def test_gato_conhecido_vem_em_96(raca):
    s = sprites.get("cat", raca)
    assert s is not None and s.get_size() == (96, 96)


def test_especial_e_efeito_vem_em_96():
    assert sprites.get("special", "sombra-miuda").get_size() == (96, 96)
    assert sprites.get("effect", "arranhao-certeiro").get_size() == (96, 96)


def test_icone_vem_em_16_e_lider_em_96_e_128():
    assert sprites.get("icon", "provocar").get_size() == (16, 16)
    assert sprites.get("leader", "heroi").get_size() == (96, 96)
    assert sprites.get("leader128", "heroi").get_size() == (128, 128)


def test_tamanho_pedido_redimensiona_a_altura():
    for tam in (16, 48, 64, 128):
        s = sprites.get("cat", "siames", tam)
        assert s.get_height() == tam and s.get_width() == tam


def test_racas_desconhecidas_kinds_desconhecidos_e_nomes_vazios_devolvem_none():
    assert sprites.get("cat", "raca-que-nao-existe") is None
    assert sprites.get("monstro", "siames") is None
    assert sprites.get("cat", None) is None
    assert sprites.get("cat", "") is None
    assert sprites.get_cat("xyz") is None
    assert sprites.get("icon", "nao-existe") is None


def test_get_usa_cache_e_cache_por_tamanho():
    a = sprites.get("cat", "persa")
    assert sprites.get("cat", "persa") is a
    assert sprites.get("cat", "persa", 48) is not a


def test_get_cat_equivale_a_get_cat_kind():
    assert sprites.get_cat("persa").get_size() == sprites.get("cat", "persa").get_size()


def test_sprites_de_racas_diferentes_sao_diferentes():
    imgs = {pygame.image.tobytes(sprites.get("cat", r), "RGBA") for r in RACAS}
    assert len(imgs) == len(RACAS)


def test_draw_devolve_true_com_sprite_e_false_sem():
    surf = pygame.Surface((200, 200))
    assert sprites.draw(surf, "siames", 10, 10) is True
    assert sprites.draw(surf, "nao-existe", 10, 10) is False
    assert sprites.draw(surf, "heroi", 10, 10, kind="leader") is True


def test_draw_respeita_o_clip_e_restaura_o_clip_anterior():
    surf = pygame.Surface((200, 200))
    surf.fill((0, 0, 0))
    clip = pygame.Rect(10, 10, 20, 20)
    surf.set_clip(pygame.Rect(0, 0, 200, 200))
    sprites.draw(surf, "persa", 0, 0, clip=clip)
    assert surf.get_clip() == pygame.Rect(0, 0, 200, 200)
    fora = [surf.get_at((x, y))[:3] for x in range(200) for y in range(200) if not clip.collidepoint(x, y)]
    assert all(c == (0, 0, 0) for c in fora)


# ------------------------------------------------------------------ fallback / sheets falsos
def test_sem_nenhum_arquivo_tudo_devolve_none(raiz_falsa):
    assert sprites.get("cat", "siames") is None
    assert sprites.get("icon", "provocar") is None
    assert sprites.get("leader128", "heroi") is None
    assert sprites.draw(pygame.Surface((10, 10)), "siames", 0, 0) is False


def test_json_corrompido_devolve_none_sem_levantar(raiz_falsa):
    (raiz_falsa / "cats96").mkdir()
    (raiz_falsa / "cats96" / "spritesheet.json").write_text("{ isto nao e json", encoding="utf-8")
    assert sprites.get("cat", "siames") is None


def test_png_ausente_com_json_valido_devolve_none(raiz_falsa):
    (raiz_falsa / "cats96").mkdir()
    (raiz_falsa / "cats96" / "spritesheet.json").write_text(json.dumps(
        {"image": "nao-existe.png", "size": [96, 96],
         "sprites": {"siames": {"x": 0, "y": 0, "w": 96, "h": 96}}}), encoding="utf-8")
    assert sprites.get("cat", "siames") is None


def test_fallback_do_sheet_antigo_48_e_ampliado_2x_para_96(raiz_falsa):
    faz_sheet(raiz_falsa, "cats", ["x"], 48, (200, 0, 0))
    s = sprites.get("cat", "x")
    assert s.get_size() == (96, 96) and s.get_at((50, 50))[:3] == (200, 0, 0)


def test_fallback_de_icone_9_e_ampliado_para_18(raiz_falsa):
    faz_sheet(raiz_falsa, "icons", ["provocar"], 9, (0, 200, 0))
    assert sprites.get("icon", "provocar").get_size() == (18, 18)


def test_sheet_novo_tem_preferencia_sobre_o_antigo(raiz_falsa):
    faz_sheet(raiz_falsa, "cats", ["x"], 48, (200, 0, 0))
    faz_sheet(raiz_falsa, "cats96", ["x"], 96, (0, 0, 200))
    s = sprites.get("cat", "x")
    assert s.get_size() == (96, 96) and s.get_at((10, 10))[:3] == (0, 0, 200)


def test_sheet_novo_sem_o_nome_cai_para_o_antigo(raiz_falsa):
    faz_sheet(raiz_falsa, "cats", ["so-antigo"], 48, (200, 0, 0))
    faz_sheet(raiz_falsa, "cats96", ["outro"], 96, (0, 0, 200))
    assert sprites.get("cat", "so-antigo").get_at((5, 5))[:3] == (200, 0, 0)


def test_lider128_cai_para_o_sheet_de_96_quando_falta_o_128(raiz_falsa):
    faz_sheet(raiz_falsa, "leaders", ["heroi"], 96, (9, 9, 9))
    assert sprites.get("leader128", "heroi").get_size() == (96, 96)


def test_retangulo_fora_da_imagem_devolve_none_sem_levantar(raiz_falsa):
    faz_sheet(raiz_falsa, "cats96", ["ok"], 96, (1, 1, 1))
    d = raiz_falsa / "cats96" / "spritesheet.json"
    j = json.loads(d.read_text())
    j["sprites"]["fora"] = {"x": 500, "y": 0, "w": 96, "h": 96}
    d.write_text(json.dumps(j))
    sprites.reset()
    assert sprites.get("cat", "fora") is None
    assert sprites.get("cat", "ok") is not None


# ------------------------------------------------------------------ skin
PECAS = {"energia_cheia": (24, 24), "energia_vazia": (24, 24), "hp_lider": (40, 40),
         "botao_fim_turno_normal": (152, 64), "botao_fim_turno_hover": (152, 64),
         "botao_fim_turno_desabilitado": (152, 64)}


@pytest.mark.parametrize("nome,tam", PECAS.items())
def test_peca_do_tema_tem_o_tamanho_nativo(nome, tam):
    p = skin.piece(nome)
    assert p is not None and p.get_size() == tam


def test_peca_inexistente_e_none_e_blit_false():
    assert skin.piece("nao-existe") is None
    assert skin.blit(pygame.Surface((50, 50)), "nao-existe", (0, 0)) is False


def test_blit_desenha_a_peca_e_centraliza():
    surf = pygame.Surface((100, 100), pygame.SRCALPHA)
    assert skin.blit(surf, "energia_cheia", (0, 0)) is True
    assert pygame.mask.from_surface(surf, 1).count() > 0
    surf2 = pygame.Surface((100, 100), pygame.SRCALPHA)
    skin.blit(surf2, "energia_cheia", (50, 50), center=True)
    box = pygame.mask.from_surface(surf2, 1).get_bounding_rects()[0]
    assert box.left >= 38 and box.right <= 62 and box.top >= 38 and box.bottom <= 62


def test_nine_slice_desenha_dentro_do_retangulo_e_devolve_true():
    surf = pygame.Surface((400, 200), pygame.SRCALPHA)
    r = pygame.Rect(50, 40, 200, 50)
    assert skin.nine(surf, "botao_fim_turno_normal", r) is True
    box = pygame.mask.from_surface(surf, 1).get_bounding_rects()
    assert box
    uniao = box[0].unionall(box[1:])
    assert r.contains(uniao)
    assert uniao.width > 100            # esticou ate perto da largura pedida


def test_nine_slice_cobre_varios_tamanhos_sem_excecao():
    surf = pygame.Surface((500, 400), pygame.SRCALPHA)
    for w, h in ((200, 50), (330, 200), (152, 64), (20, 20), (4, 4), (500, 60)):
        assert skin.nine(surf, "tooltip", pygame.Rect(0, 0, w, h)) is True


def test_nine_slice_desconhecido_e_peca_sem_9slice_devolvem_false():
    surf = pygame.Surface((100, 100))
    assert skin.nine(surf, "inexistente", pygame.Rect(0, 0, 50, 50)) is False
    assert skin.nine(surf, "energia_cheia", pygame.Rect(0, 0, 50, 50)) is False


def test_nine_slice_mantem_cantos_nativos():
    """O canto superior esquerdo do 9-slice grande e o canto da peca original (nao e esticado)."""
    p = skin.piece("tooltip")
    surf = pygame.Surface((400, 300), pygame.SRCALPHA)
    skin.nine(surf, "tooltip", pygame.Rect(0, 0, 400, 300))
    for x, y in ((0, 0), (2, 3), (4, 4)):
        assert tuple(surf.get_at((x, y))) == tuple(p.get_at((x, y)))


def test_tabuleiro_e_960x540_e_fundo_de_tela_existe():
    b = skin.board()
    assert b is not None and b.get_size() == (W, H)
    bg = skin.screen_background((W, H))
    assert bg is not None and bg.get_size() == (W, H)
    assert skin.screen_background((W, H)) is bg            # cache
    assert skin.screen_background((320, 200)).get_size() == (320, 200)


def test_tema_inexistente_faz_tudo_devolver_none_ou_false():
    skin.THEME = "tema-que-nao-existe"
    try:
        skin.reset()
        assert skin.piece("energia_cheia") is None
        assert skin.blit(pygame.Surface((9, 9)), "energia_cheia", (0, 0)) is False
        assert skin.nine(pygame.Surface((90, 90)), "tooltip", pygame.Rect(0, 0, 50, 50)) is False
        assert skin.board() is None
        assert skin.screen_background((W, H)) is None
    finally:
        skin.THEME = "noturno"
        skin.reset()


def test_duelo_desenha_sem_o_tema_com_retangulos_de_paleta():
    skin.THEME = "tema-que-nao-existe"
    try:
        skin.reset()
        c = Controller(load_game_content(), 1, ai_delay=0.0)
        c.settle()
        surf = pygame.Surface((W, H))
        draw_frame(surf, c, UIState(t=0.2))
        assert len({surf.get_at((x, y))[:3] for x in range(0, W, 23) for y in range(0, H, 19)}) > 3
    finally:
        skin.THEME = "noturno"
        skin.reset()


def test_duelo_desenha_sem_nenhum_sprite_nem_fonte_bitmap(raiz_falsa):
    from ui import font
    font.use_bitmap(False)
    try:
        c = Controller(load_game_content(), 2, ai_delay=0.0)
        c.settle()
        surf = pygame.Surface((W, H))
        draw_frame(surf, c, UIState(t=0.2))
        draw_frame(surf, c, UIState(t=0.2, mouse=(300, 450)))
    finally:
        font.use_bitmap(True)
