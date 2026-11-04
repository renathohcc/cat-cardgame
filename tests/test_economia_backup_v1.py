"""Backup do save v1 na migracao e Prestigio a partir do nivel guardado (pendencias da T13.1c).

Fonte: `reports/T13.1c-backup-migracao.md`. Regra: ao gravar sobre um arquivo v1, o original vai para
`<nome>.v1.bak` (o primeiro v1 vale, nunca sobrescreve); falha no backup nao impede o save e vira aviso.
Nenhum teste toca `saves/save.json` real: tudo em pasta temporaria."""
from __future__ import annotations

import json
import shutil
from random import Random

import pytest

from core import (SaveData, new_game, prestige_info, prestige_level, read_save, save_to_dict, update_prestige,
                  write_save)
from core import save as core_save
from economia_helpers import ROOT, content as _content, set_strong_breeds
from ui_eco_helpers import v1_dict


@pytest.fixture(scope="module")
def c():
    return _content()


def grava_v1(path, c, seed: int = 3, coins: int = 4) -> bytes:
    s = new_game(c, Random(seed))
    s.coins = coins
    path.write_text(json.dumps(v1_dict(s), ensure_ascii=False, indent=2), encoding="utf-8")
    return path.read_bytes()


def versao(path) -> int:
    return json.loads(path.read_text("utf-8"))["schema_version"]


# ====================================================================== BACKUP
def test_gravar_sobre_v1_cria_save_v1_bak_identico_ao_original(c, tmp_path):
    p = tmp_path / "save.json"
    original = grava_v1(p, c)
    s = read_save(p, c)
    assert s.migrated_from == 1
    assert write_save(s, p) is None
    bak = tmp_path / "save.v1.bak"
    assert bak.read_bytes() == original and versao(bak) == 1
    assert versao(p) == 2


def test_apenas_ler_um_v1_nao_cria_backup_nem_altera_o_arquivo(c, tmp_path):
    p = tmp_path / "save.json"
    original = grava_v1(p, c)
    read_save(p, c)
    assert p.read_bytes() == original and not (tmp_path / "save.v1.bak").exists()


def test_segunda_gravacao_nao_toca_no_backup(c, tmp_path):
    p = tmp_path / "save.json"
    original = grava_v1(p, c)
    s = read_save(p, c)
    write_save(s, p)
    s.coins += 50
    assert write_save(s, p) is None
    assert (tmp_path / "save.v1.bak").read_bytes() == original
    assert read_save(p, c).coins == 54


def test_backup_existente_nunca_e_sobrescrito_por_outro_v1(c, tmp_path):
    p = tmp_path / "save.json"
    bak = tmp_path / "save.v1.bak"
    bak.write_bytes(b"backup mais antigo")
    grava_v1(p, c)
    write_save(read_save(p, c), p)
    assert bak.read_bytes() == b"backup mais antigo"
    assert not list(tmp_path.glob("*.v1.1.bak"))              # sem copias numeradas
    assert versao(p) == 2                                      # mas o save novo foi gravado


def test_v1_gravado_de_novo_por_cima_de_v2_nao_gera_backup_a_toa(c, tmp_path):
    p = tmp_path / "save.json"
    write_save(new_game(c, Random(1)), p)                       # v2 desde o inicio
    write_save(new_game(c, Random(2)), p)
    assert not (tmp_path / "save.v1.bak").exists()


def test_primeira_gravacao_sem_arquivo_nao_cria_backup(c, tmp_path):
    p = tmp_path / "pasta" / "save.json"
    assert write_save(new_game(c, Random(1)), p) is None
    assert p.exists() and not list(p.parent.glob("*.bak"))


def test_backup_usa_o_nome_do_arquivo_como_base(c, tmp_path):
    p = tmp_path / "meu_jogo.json"
    original = grava_v1(p, c)
    write_save(read_save(p, c), p)
    assert (tmp_path / "meu_jogo.v1.bak").read_bytes() == original


def test_save_corrompido_no_destino_nao_gera_backup_v1_e_grava_normalmente(c, tmp_path):
    p = tmp_path / "save.json"
    p.write_bytes(b"\x00 isto nao e json")
    assert write_save(new_game(c, Random(1)), p) is None
    assert versao(p) == 2 and not (tmp_path / "save.v1.bak").exists()


def test_backup_nao_deixa_temporarios_na_pasta(c, tmp_path):
    p = tmp_path / "save.json"
    grava_v1(p, c)
    write_save(read_save(p, c), p)
    assert sorted(f.name for f in tmp_path.iterdir()) == ["save.json", "save.v1.bak"]


def test_falha_no_backup_nao_impede_o_save_e_devolve_aviso(c, tmp_path, monkeypatch):
    p = tmp_path / "save.json"
    original = grava_v1(p, c)
    s = read_save(p, c)

    def quebra(*a, **k):
        raise PermissionError("disco somente leitura")

    monkeypatch.setattr(core_save.shutil, "copyfile", quebra)
    aviso = write_save(s, p)
    assert isinstance(aviso, str) and "backup" in aviso.lower()
    assert versao(p) == 2 and read_save(p, c).coins == s.coins       # o save novo foi gravado
    assert not (tmp_path / "save.v1.bak").exists()
    assert not list(tmp_path.glob("*.tmp"))
    assert original != p.read_bytes()


def test_copia_do_save_real_gera_backup_byte_a_byte(c, tmp_path):
    real = ROOT / "saves" / "save.json"
    if not real.exists():
        pytest.skip("sem saves/save.json local")
    p = tmp_path / "save.json"
    shutil.copyfile(real, p)
    original = p.read_bytes()
    antes = real.read_bytes()
    write_save(read_save(p, c), p)
    if json.loads(original.decode("utf-8")).get("schema_version") == 1:
        assert (tmp_path / "save.v1.bak").read_bytes() == original
    else:
        assert not (tmp_path / "save.v1.bak").exists()
    assert real.read_bytes() == antes                                # o save real nunca e tocado


# ====================================================================== PRESTIGIO A PARTIR DO NIVEL GUARDADO
def fortes(c, s: SaveData) -> SaveData:
    return set_strong_breeds(c, s)                                   # 5 racas, cada uma com soma de IV do marco


def test_nivel_guardado_2_sobe_para_3_com_5_racas_mesmo_sem_liga_no_progresso(c):
    s = new_game(c, Random(1))
    fortes(c, s)
    s.prestige = 2
    s.progress["leagues_cleared"] = 0
    assert update_prestige(c, s) == 3 and s.prestige == 3


def test_nivel_guardado_1_com_5_racas_mas_sem_liga_continua_1(c):
    s = new_game(c, Random(1))
    fortes(c, s)
    assert s.prestige == 1 and update_prestige(c, s) == 1


def test_nivel_guardado_nunca_desce_mesmo_sem_nenhum_marco(c):
    s = new_game(c, Random(1))
    s.prestige = 3
    assert update_prestige(c, s) == 3 and prestige_level(c, s) == 3


def test_nivel_guardado_sobrevive_ao_ciclo_gravar_e_ler(c, tmp_path):
    p = tmp_path / "save.json"
    s = new_game(c, Random(1))
    s.prestige = 2
    write_save(s, p)
    volta = read_save(p, c)
    assert volta.prestige == 2 and prestige_level(c, volta) == 2
    fortes(c, volta)
    assert update_prestige(c, volta) == 3


def test_info_do_nivel_guardado_aponta_o_marco_seguinte(c):
    s = new_game(c, Random(1))
    s.prestige = 2
    info = prestige_info(c, s)
    assert info.level == 2 and info.next_level == 3
    assert info.milestone["type"] == "distinct_breeds_min_iv"


def test_save_v1_migrado_comeca_no_prestigio_1(c, tmp_path):
    p = tmp_path / "save.json"
    grava_v1(p, c)
    s = read_save(p, c)
    assert s.prestige == 1 and save_to_dict(s)["schema_version"] == 2
