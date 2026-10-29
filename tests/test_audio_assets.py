"""Contrato dos arquivos de audio (T10.3): manifesto data/audio.json x assets/audio.

Le os OGG por conta propria (cabecalho Vorbis) para checar canais e duracao sem depender de
bibliotecas extras; abre cada arquivo com pygame.mixer sob SDL_AUDIODRIVER=dummy.
"""
from __future__ import annotations

import json
import os
import re
import struct
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
import pytest

ROOT = Path(__file__).resolve().parent.parent
AUDIO_DIR = ROOT / "assets" / "audio"
CATALOG = json.loads((ROOT / "data" / "audio.json").read_text(encoding="utf-8"))
SFX = {f: cue for cue, s in CATALOG["sfx"].items() for f in s["files"]}
MUSIC = {m["file"]: name for name, m in CATALOG["music"].items()}
ALL_FILES = sorted([*SFX, *MUSIC])
MAX_SFX_S = 2.5


def ogg_info(path: Path) -> tuple[int, int, float]:
    """(canais, taxa, duracao em s) de um OGG Vorbis, lendo o cabecalho e o ultimo granule."""
    data = path.read_bytes()
    i = data.index(b"\x01vorbis")
    channels = data[i + 11]
    rate = struct.unpack("<I", data[i + 12:i + 16])[0]
    j = data.rindex(b"OggS")
    granule = struct.unpack("<q", data[j + 6:j + 14])[0]
    return channels, rate, granule / rate


@pytest.fixture(scope="module")
def mixer():
    pygame.mixer.init()
    yield pygame.mixer
    pygame.mixer.quit()


def test_manifesto_nao_esta_vazio_e_todo_arquivo_existe():
    assert len(ALL_FILES) >= 40
    faltando = [f for f in ALL_FILES if not (AUDIO_DIR / f).is_file()]
    assert faltando == []


def test_nenhum_caminho_sai_de_assets_audio():
    raiz = AUDIO_DIR.resolve()
    for rel in ALL_FILES:
        assert ".." not in Path(rel).parts and not Path(rel).is_absolute() and "\\" not in rel and ":" not in rel, rel
        assert (AUDIO_DIR / rel).resolve().is_relative_to(raiz), rel
        assert rel.startswith(("sfx/", "music/")) and rel.endswith(".ogg"), rel


@pytest.mark.parametrize("rel", sorted(SFX))
def test_sfx_e_mono_e_tem_no_maximo_2_5_segundos(rel):
    canais, _, dur = ogg_info(AUDIO_DIR / rel)
    assert canais == 1, f"{rel}: {canais} canais"
    assert 0 < dur <= MAX_SFX_S, f"{rel}: {dur:.2f}s"


@pytest.mark.parametrize("rel", sorted(MUSIC))
def test_musica_e_estereo_e_nao_e_curta_demais(rel):
    canais, _, dur = ogg_info(AUDIO_DIR / rel)
    assert canais == 2, f"{rel}: {canais} canais"
    assert dur >= 5, f"{rel}: {dur:.1f}s"


@pytest.mark.parametrize("rel", sorted(SFX))
def test_sfx_abre_com_pygame_mixer_sound_dummy(mixer, rel):
    snd = mixer.Sound(str(AUDIO_DIR / rel))
    assert snd.get_length() > 0


@pytest.mark.parametrize("rel", sorted(MUSIC))
def test_musica_abre_com_pygame_mixer_music_dummy(mixer, rel):
    mixer.music.load(str(AUDIO_DIR / rel))
    mixer.music.unload()


def test_creditos_citam_todos_os_arquivos_do_manifesto():
    texto = (AUDIO_DIR / "CREDITS.md").read_text(encoding="utf-8")
    sem_credito = [f for f in ALL_FILES if f not in texto]
    assert sem_credito == []


def test_creditos_declaram_licenca_para_cada_arquivo():
    linhas = (AUDIO_DIR / "CREDITS.md").read_text(encoding="utf-8").splitlines()
    for rel in ALL_FILES:
        linha = next(ln for ln in linhas if ln.lstrip("| ").startswith(rel))
        assert "CC0" in linha, rel


def test_manifesto_referencia_so_cues_do_catalogo_e_faixas_existentes():
    assert set(CATALOG["contexts"].values()) <= set(CATALOG["music"])
    for name, spec in CATALOG["sfx"].items():
        assert spec["files"], name
        assert all(f.startswith("sfx/") for f in spec["files"]), name
        assert 0 <= spec["volume"] <= 1 and spec["cooldown_ms"] >= 0, name


def test_todo_cue_citado_no_codigo_da_ui_existe_no_catalogo():
    usados: set[str] = set()
    for py in (ROOT / "ui").glob("*.py"):
        usados |= set(re.findall(r'audio\.sfx\(\s*"([a-z0-9_]+)"', py.read_text(encoding="utf-8")))
    assert usados
    assert usados - set(CATALOG["sfx"]) == set()


def test_todo_contexto_citado_no_codigo_da_ui_existe_no_catalogo():
    usados: set[str] = set()
    for py in (ROOT / "ui").glob("*.py"):
        src = py.read_text(encoding="utf-8")
        usados |= set(re.findall(r'audio\.music\(\s*"([a-z0-9_]+)"', src))
        usados |= set(re.findall(r'return\s+"((?:fim_|criatorio_|duelo|mapa|menu|colecao|breed|adocao)[a-z_]*)"', src))
    assert usados - set(CATALOG["contexts"]) == set()


def test_meows_do_cercado_estao_no_catalogo():
    from ui.pen_controller import MEOWS
    assert set(MEOWS) <= set(CATALOG["sfx"]) and {"kitten_mew", "pet", "purr", "bed_settle"} <= set(CATALOG["sfx"])


def test_arquivos_em_sfx_e_music_estao_todos_no_manifesto():
    em_disco = {p.relative_to(AUDIO_DIR).as_posix() for sub in ("sfx", "music") for p in (AUDIO_DIR / sub).glob("*.ogg")}
    assert em_disco - set(ALL_FILES) == set()
