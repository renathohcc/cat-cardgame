"""Testes do audio da UI (T10.3): AudioManager com backend/relogio/RNG falsos, prefs, tecla M,
contexto de musica, ganchos nos controladores, menu de volume e loop headless.

Escritos a partir de reports/T10.0 e T10.1 e de data/audio.json (so a API publica de ui.audio).
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from random import Random
from types import SimpleNamespace

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

import pygame
import pytest

from core import new_game
from ui import audio
from ui import layout_hub as LH
from ui.audio import AudioManager, NullBackend, PygameBackend, read_prefs, write_prefs
from ui.controller import Controller, load_game_content
from ui.daycycle import fixed_clock
from ui.hub_controller import HubController
from ui.pen_controller import MEOWS, PenController, PenEntry
from ui.render import UIState
from ui.render_hub import draw_hub_frame
from ui.run_controller import RunController
from ui.theme import H, W

CATALOG = json.loads((Path(__file__).resolve().parent.parent / "data" / "audio.json").read_text(encoding="utf-8"))


class FakeBackend:
    """Registra tudo que o manager manda tocar. `missing` = nomes de arquivo que 'nao existem'."""

    def __init__(self, available: bool = True, missing: tuple[str, ...] = ()) -> None:
        self.available = available
        self.missing = set(missing)
        self.played: list[tuple[str, float]] = []
        self.starts: list[tuple[str, bool, float, int]] = []
        self.stops = 0
        self.volumes: list[float] = []

    def load_sound(self, path: Path):
        return None if path.name in self.missing else path.name

    def play_sound(self, sound, volume: float) -> None:
        self.played.append((sound, volume))

    def music_start(self, path: Path, loop: bool, volume: float, fade_ms: int) -> bool:
        self.starts.append((path.name, loop, volume, fade_ms))
        return True

    def music_stop(self) -> None:
        self.stops += 1

    def music_set_volume(self, volume: float) -> None:
        self.volumes.append(volume)


class Clock:
    def __init__(self) -> None:
        self.t = 0.0

    def __call__(self) -> float:
        return self.t


def small_catalog() -> dict:
    return {
        "version": 1, "volumes": {"musica": 0.7, "efeitos": 0.8},
        "sfx": {
            "um": {"files": ["sfx/um.ogg"], "volume": 0.5, "cooldown_ms": 100},
            "var": {"files": ["sfx/var.ogg", "sfx/var_2.ogg"], "volume": 1.0, "cooldown_ms": 0},
            "livre": {"files": ["sfx/livre.ogg"], "volume": 1.0, "cooldown_ms": 0},
        },
        "music": {
            "a": {"file": "music/a.ogg", "volume": 1.0, "loop": True},
            "b": {"file": "music/b.ogg", "volume": 0.5, "loop": True},
            "jingle": {"file": "music/jingle.ogg", "volume": 1.0, "loop": False},
        },
        "contexts": {"x": "a", "y": "a", "z": "b", "fim": "jingle"},
    }


def mk(backend=None, clock=None, seed=1, prefs=None, catalog=None) -> AudioManager:
    return AudioManager(backend or FakeBackend(), small_catalog() if catalog is None else catalog,
                        Path("audio"), Random(seed), clock or Clock(), prefs)


@pytest.fixture(autouse=True)
def restaura_manager(monkeypatch):
    """Cada teste comeca com o manager global silencioso e o restaura no fim."""
    monkeypatch.setattr(audio, "_current", AudioManager(NullBackend(), CATALOG, rng=Random(0)))
    monkeypatch.delenv("CHAOSCATS_AUDIO", raising=False)


# ------------------------------------------------------------------ cooldown e variacao
def test_cooldown_bloqueia_repeticao_dentro_da_janela_pelo_relogio_injetado():
    be, clk = FakeBackend(), Clock()
    m = mk(be, clk)
    assert m.play("um") is True
    clk.t = 99
    assert m.play("um") is False
    clk.t = 100
    assert m.play("um") is True
    assert len(be.played) == 2
    assert m.requests["um"] == 3 and m.total_requests == 3     # pedidos contam mesmo em cooldown


def test_cooldown_e_por_cue_nao_global():
    be, clk = FakeBackend(), Clock()
    m = mk(be, clk)
    assert m.play("um") and m.play("livre")
    assert m.play("livre")                                      # cooldown 0: sempre toca


def test_volume_do_efeito_e_volume_do_cue_vezes_o_do_usuario():
    be = FakeBackend()
    m = mk(be)
    m.set_volume("efeitos", 0.6)
    m.play("um")
    assert be.played[0][1] == pytest.approx(0.6 * 0.5)


def test_variacao_sorteada_e_deterministica_por_seed():
    def seq(seed: int) -> list[str]:
        be = FakeBackend()
        m = mk(be, seed=seed)
        for _ in range(40):
            m.play("var")
        return [n for n, _ in be.played]
    assert seq(3) == seq(3)
    assert set(seq(3)) == {"var.ogg", "var_2.ogg"}              # as duas variacoes aparecem
    assert seq(3) != seq(4)


def test_cue_desconhecido_e_silencioso_e_contado():
    be = FakeBackend()
    m = mk(be)
    assert m.play("nao_existe") is False
    assert be.played == [] and m.requests["nao_existe"] == 1


# ------------------------------------------------------------------ arquivo ausente / mixer falhando
def test_arquivo_ausente_cai_em_silencio_sem_excecao():
    be = FakeBackend(missing=("um.ogg",))
    m = mk(be)
    assert m.play("um") is False and be.played == []


def test_variacao_ausente_toca_a_outra():
    be = FakeBackend(missing=("var.ogg",))
    m = mk(be)
    for _ in range(10):
        assert m.play("var") is True
    assert {n for n, _ in be.played} == {"var_2.ogg"}


def test_catalogo_real_com_pasta_vazia_nao_levanta(tmp_path):
    m = AudioManager(PygameBackend(), CATALOG, tmp_path, Random(1))
    for cue in CATALOG["sfx"]:
        assert m.play(cue) is False
    m.set_context("duelo")
    m.update()
    assert m.playing is None


@pytest.mark.parametrize("modo", ["off", "fail", "OFF", "Fail"])
def test_env_off_ou_fail_deixa_backend_indisponivel_e_tudo_no_op(monkeypatch, modo):
    monkeypatch.setenv("CHAOSCATS_AUDIO", modo)
    be = PygameBackend()
    assert be.available is False
    m = AudioManager(be, CATALOG, audio.AUDIO_DIR, Random(1))
    assert m.play("ui_click") is False
    m.set_context("menu")
    m.update()
    m.adjust_volume("musica", 1)
    m.toggle_mute()
    assert m.playing is None


def test_mixer_que_levanta_excecao_no_init_vira_no_op(monkeypatch):
    def boom(*a, **k):
        raise pygame.error("sem dispositivo")
    monkeypatch.setattr(pygame.mixer, "get_init", lambda: None)
    monkeypatch.setattr(pygame.mixer, "init", boom)
    be = PygameBackend()
    assert be.available is False
    m = AudioManager(be, CATALOG, audio.AUDIO_DIR, Random(1))
    assert m.play("ui_click") is False
    m.set_context("duelo")
    m.update()
    assert m.playing is None


def test_backend_nulo_nao_quebra_nada():
    m = mk(NullBackend())
    assert m.play("um") is False
    m.set_context("x")
    m.update()
    assert m.requests["um"] == 1


def test_catalogo_ausente_ou_invalido_vira_mudo(tmp_path):
    assert audio.load_catalog(tmp_path / "nao.json") == {}
    ruim = tmp_path / "ruim.json"
    ruim.write_text("{ nao e json", encoding="utf-8")
    assert audio.load_catalog(ruim) == {}
    lista = tmp_path / "lista.json"
    lista.write_text("[1, 2]", encoding="utf-8")
    assert audio.load_catalog(lista) == {}
    m = AudioManager(FakeBackend(), {}, Path("a"), Random(1))
    assert m.play("ui_click") is False
    m.set_context("menu")


# ------------------------------------------------------------------ musica
def test_primeiro_contexto_inicia_a_faixa_com_fade_in():
    be = FakeBackend()
    m = mk(be)
    m.set_context("x")
    assert be.starts == [("a.ogg", True, pytest.approx(0.7), audio.FADE_MS)]
    assert m.playing == "a"


def test_mesmo_contexto_ou_contextos_com_a_mesma_faixa_nao_reiniciam():
    be, clk = FakeBackend(), Clock()
    m = mk(be, clk)
    m.set_context("x")
    m.set_context("x")
    m.set_context("y")                       # outro contexto, mesma faixa "a"
    clk.t = 5000
    m.update()
    assert len(be.starts) == 1 and be.stops == 0


def test_troca_de_faixa_faz_fade_out_e_depois_inicia_a_nova():
    be, clk = FakeBackend(), Clock()
    m = mk(be, clk)
    m.set_context("x")
    m.set_context("z")
    assert len(be.starts) == 1                              # ainda nao trocou
    clk.t = audio.FADE_OUT_MS / 2
    m.update()
    assert len(be.starts) == 1 and be.volumes[-1] < 0.7     # volume descendo
    clk.t = audio.FADE_OUT_MS
    m.update()
    assert be.stops == 1 and be.starts[-1][0] == "b.ogg" and m.playing == "b"
    assert be.starts[-1][2] == pytest.approx(0.7 * 0.5)     # volume da faixa aplicado


def test_jingle_toca_sem_loop():
    be = FakeBackend()
    m = mk(be)
    m.set_context("fim")
    assert be.starts[0][:2] == ("jingle.ogg", False)


def test_contexto_desconhecido_nao_muda_a_musica():
    be = FakeBackend()
    m = mk(be)
    m.set_context("x")
    m.set_context("nada")
    assert len(be.starts) == 1 and be.stops == 0 and m.playing == "a"


def test_faixa_ausente_nao_deixa_playing_falso():
    class SemMusica(FakeBackend):
        def music_start(self, *a, **k):
            return False
    m = mk(SemMusica())
    m.set_context("x")
    assert m.playing is None


def test_stop_music_limpa_estado():
    be = FakeBackend()
    m = mk(be)
    m.set_context("x")
    m.stop_music()
    assert be.stops == 1 and m.playing is None and m.track is None


# ------------------------------------------------------------------ volumes e mudo
def test_volume_anda_em_passos_de_10_por_cento_e_trava_em_0_e_1():
    m = mk()
    assert m.volume_of("musica") == pytest.approx(0.7)
    assert m.adjust_volume("musica", 1) == pytest.approx(0.8)
    assert m.adjust_volume("musica", -3) == pytest.approx(0.5)
    for _ in range(20):
        m.adjust_volume("efeitos", 1)
    assert m.volume_of("efeitos") == 1.0
    for _ in range(20):
        m.adjust_volume("efeitos", -1)
    assert m.volume_of("efeitos") == 0.0
    assert m.volume_of("musica") == pytest.approx(0.5)      # outro canal intacto


def test_set_volume_limita_a_faixa_0_1():
    m = mk()
    m.set_volume("musica", 5)
    assert m.volume_of("musica") == 1.0
    m.set_volume("musica", -2)
    assert m.volume_of("musica") == 0.0


def test_ajuste_de_volume_da_musica_chega_ao_backend():
    be = FakeBackend()
    m = mk(be)
    m.set_context("x")
    m.set_volume("musica", 0.3)
    assert be.volumes[-1] == pytest.approx(0.3)


def test_mudo_silencia_efeitos_e_musica_e_desmutar_restaura():
    be = FakeBackend()
    m = mk(be)
    m.set_context("x")
    assert m.toggle_mute() is True
    assert be.volumes[-1] == 0.0
    assert m.play("livre") is False and be.played == []
    assert m.requests["livre"] == 1
    assert m.toggle_mute() is False
    assert be.volumes[-1] == pytest.approx(0.7)
    assert m.play("livre") is True


def test_mudo_nao_impede_trocar_o_contexto():
    m = mk(FakeBackend(), Clock())
    be = m.backend
    m.set_muted(True)
    m.set_context("z")
    assert m.playing == "b" and be.starts[-1][2] == 0.0


# ------------------------------------------------------------------ prefs
def test_prefs_persistem_volumes_e_mudo_entre_instancias(tmp_path):
    p = tmp_path / "prefs.json"
    m = mk(prefs=p)
    m.set_volume("musica", 0.3)
    m.adjust_volume("efeitos", -2)
    m.set_muted(True)
    m2 = mk(prefs=p)
    assert m2.volume_of("musica") == pytest.approx(0.3)
    assert m2.volume_of("efeitos") == pytest.approx(0.6)
    assert m2.muted is True


def test_prefs_arquivo_tem_formato_esperado_e_nao_deixa_tmp(tmp_path):
    p = tmp_path / "sub" / "prefs.json"
    m = mk(prefs=p)
    m.set_volume("musica", 0.4)
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data == {"version": 1, "music": 0.4, "sfx": 0.8, "muted": False}
    assert [f.name for f in p.parent.iterdir()] == ["prefs.json"]


def test_prefs_ausente_usa_padroes(tmp_path):
    m = mk(prefs=tmp_path / "nada.json")
    assert (m.music_volume, m.sfx_volume, m.muted) == (0.7, 0.8, False)


@pytest.mark.parametrize("conteudo", ["", "{ quebrado", "[]", "null", "42", '"x"', "\x00\x01"])
def test_prefs_corrompido_e_tolerado(tmp_path, conteudo):
    p = tmp_path / "prefs.json"
    p.write_text(conteudo, encoding="utf-8")
    assert read_prefs(p) == {}
    m = mk(prefs=p)
    assert (m.music_volume, m.sfx_volume, m.muted) == (0.7, 0.8, False)


def test_prefs_bytes_invalidos_sao_tolerados(tmp_path):
    p = tmp_path / "prefs.json"
    p.write_bytes(b"\xff\xfe\x00garbage")
    assert read_prefs(p) == {}


def test_prefs_valores_invalidos_sao_ignorados_ou_limitados(tmp_path):
    p = tmp_path / "prefs.json"
    p.write_text(json.dumps({"music": "alto", "sfx": 7, "muted": "sim"}), encoding="utf-8")
    assert read_prefs(p) == {"sfx": 1.0}
    p.write_text(json.dumps({"music": True, "sfx": -1, "muted": True}), encoding="utf-8")
    assert read_prefs(p) == {"sfx": 0.0, "muted": True}


def test_prefs_escrita_atomica_preserva_o_arquivo_se_a_troca_falhar(tmp_path, monkeypatch):
    p = tmp_path / "prefs.json"
    assert write_prefs(p, {"music": 0.2, "sfx": 0.2, "muted": False})
    antes = p.read_text(encoding="utf-8")

    def boom(*a, **k):
        raise OSError("disco cheio")
    monkeypatch.setattr(os, "replace", boom)
    assert write_prefs(p, {"music": 0.9, "sfx": 0.9, "muted": True}) is False
    assert p.read_text(encoding="utf-8") == antes
    assert json.loads(antes)["music"] == 0.2


def test_prefs_sem_caminho_ou_caminho_impossivel_nao_derruba(tmp_path):
    assert write_prefs(None, {"music": 1}) is False
    bloqueio = tmp_path / "arquivo"
    bloqueio.write_text("x", encoding="utf-8")
    m = mk(prefs=bloqueio / "prefs.json")            # "pasta" e um arquivo
    m.set_volume("musica", 0.1)
    m.toggle_mute()
    assert m.volume_of("musica") == pytest.approx(0.1)


# ------------------------------------------------------------------ tecla M
def test_tecla_m_alterna_o_mudo_do_manager_global():
    m = audio.install(mk())
    assert audio.handle_key(pygame.K_m) is True and m.muted
    assert audio.handle_key(pygame.K_m) is True and not m.muted


def test_tecla_m_nao_alterna_digitando_nome():
    m = audio.install(mk())
    assert audio.handle_key(pygame.K_m, typing=True) is False
    assert not m.muted


def test_outras_teclas_nao_mexem_no_mudo():
    m = audio.install(mk())
    assert audio.handle_key(pygame.K_n) is False and audio.handle_key(pygame.K_ESCAPE) is False
    assert not m.muted


def hub_com_save(hora: str | None = None) -> HubController:
    content = load_game_content()
    h = HubController(content, None, 5, ai_delay=0.0, clock=fixed_clock(hora) if hora else None)
    h.adopt_save(new_game(content, Random(5)))
    return h


def test_tecla_m_no_hub_respeita_editing_text_ao_renomear():
    h = hub_com_save()
    m = audio.install(mk())
    h.enter_pen()
    h.click(("pen_btn", "colecao"))
    assert h.mode == "colecao" and not h.editing_text
    assert audio.handle_key(pygame.K_m, h.editing_text) is True       # fora da digitacao: alterna
    h.col.click(("rename",))
    assert h.editing_text
    antes = m.muted
    assert audio.handle_key(pygame.K_m, h.editing_text) is False      # digitando: nao alterna
    assert m.muted == antes


# ------------------------------------------------------------------ contexto de musica
def test_catalogo_real_mapeia_todos_os_contextos_para_faixas_existentes():
    for ctx, track in CATALOG["contexts"].items():
        assert track in CATALOG["music"], ctx


def test_contexto_do_hub_por_modo():
    h = hub_com_save()
    assert h.audio_context() == "menu"
    h.enter_pen()
    h.click(("pen_btn", "colecao"))
    assert h.audio_context() == "colecao"
    h.mode = "criatorio"
    assert h.audio_context() == "breed"
    h.mode = "adocao"
    assert h.audio_context() == "adocao"


@pytest.mark.parametrize("hora, esperado, faixa", [("12:00", "criatorio_dia", "menu_dia"),
                                                    ("23:30", "criatorio_noite", "menu_noite")])
def test_cercado_escolhe_musica_pelo_periodo_do_dia(hora, esperado, faixa):
    h = hub_com_save(hora)
    h.enter_pen()
    assert h.mode == "cercado"
    assert h.audio_context() == esperado
    assert CATALOG["contexts"][esperado] == faixa


def test_contexto_do_hub_fim_de_run_usa_jingle_de_vitoria_ou_derrota():
    h = hub_com_save()
    h.mode = "resultado"
    h.result_win = True
    assert h.audio_context() == "fim_vitoria"
    h.result_win = False
    assert h.audio_context() == "fim_derrota"
    h.end_jingle, h.mode, h.result_win = True, "novidades", True
    assert h.audio_context() == "fim_vitoria"


def test_contexto_da_run_mapa_duelo_e_fim():
    rc = RunController(load_game_content(), 1, ai_delay=0.0)
    assert rc.audio_context() == "mapa"
    rc.click(("node", "c1-batalha"))
    assert rc.screen == "duel" and rc.audio_context() == "duelo"
    rc.abandon()
    assert rc.screen == "finished" and rc.audio_context() == "fim_derrota"


def test_contexto_da_run_em_duelo_de_chefe():
    falso = SimpleNamespace(screen="duel", run=SimpleNamespace(node={"tipo": "chefe"}, result=None))
    assert RunController.audio_context(falso) == "duelo_chefe"
    falso.run.node = {"tipo": "batalha"}
    assert RunController.audio_context(falso) == "duelo"
    falso.screen, falso.run.result = "finished", "vitoria"
    assert RunController.audio_context(falso) == "fim_vitoria"


def test_hub_em_run_delega_o_contexto_para_a_run():
    h = hub_com_save()
    h.start_run()
    assert h.mode == "run"
    assert h.audio_context() == h.rc.audio_context() == "mapa"


# ------------------------------------------------------------------ ganchos
def play_duel(seed: int, ai_seed: int) -> dict:
    from core.ai import choose_action
    mgr = audio.install(mk(NullBackend(), catalog=CATALOG))
    c = Controller(load_game_content(), seed, ai_delay=0.0)
    rng = Random(ai_seed)
    for _ in range(6000):
        if c.over:
            break
        if c.can_act():
            c._do(choose_action(c.duel, "player", rng))
        c.update(5.0)
    assert c.over
    return dict(mgr.requests)


def test_gancho_duelo_completo_pede_sons_de_turno_carta_ataque_e_fim():
    r = play_duel(1, 2)
    for cue in ("turn_start_player", "turn_start_enemy", "card_draw", "card_play_cat", "attack_swing", "attack_hit"):
        assert r[cue] > 0, cue
    assert r.get("duel_victory", 0) + r.get("duel_defeat", 0) == 1
    assert all(cue in CATALOG["sfx"] for cue in r)


def test_gancho_duelo_seed_igual_pede_sons_iguais():
    assert play_duel(3, 4) == play_duel(3, 4)


def test_gancho_run_node_select_e_no_indisponivel():
    mgr = audio.install(mk(NullBackend(), catalog=CATALOG))
    rc = RunController(load_game_content(), 1, ai_delay=0.0)
    rc.click(("node", "c6-chefe"))                 # indisponivel
    assert mgr.requests["ui_denied"] >= 1
    rc.click(("node", "c1-batalha"))
    assert mgr.requests["node_select"] == 1


def test_gancho_run_abandonar_pede_modal_e_cancelar_volta():
    mgr = audio.install(mk(NullBackend(), catalog=CATALOG))
    rc = RunController(load_game_content(), 1, ai_delay=0.0)
    rc.click(("abandon",))
    assert mgr.requests["ui_open_modal"] == 1
    rc.click(("quit_no",))
    assert mgr.requests["ui_back"] == 1


def test_gancho_meta_abrir_colecao_voltar_e_esc():
    mgr = audio.install(mk(NullBackend(), catalog=CATALOG))
    h = hub_com_save()
    h.enter_pen()
    h.click(("pen_btn", "colecao"))
    assert mgr.requests["ui_click"] == 1
    h.click(("back",))
    assert mgr.requests["ui_back"] == 1 and h.mode == "cercado"
    h.key_escape()
    assert mgr.requests["ui_back"] == 2 and h.mode == "menu"


def test_gancho_cercado_poke_pede_pet_e_purr_via_hub():
    mgr = audio.install(mk(NullBackend(), catalog=CATALOG))
    h = hub_com_save("12:00")
    h.enter_pen()
    h.pen.poke(h.pen.cats[0].cat_id)
    h.update(0.05)
    assert mgr.requests["pet"] == 1 and mgr.requests["purr"] == 1
    assert h.pen.sounds == []                      # o hub esvazia a fila


def test_gancho_cercado_nao_toca_sons_do_cercado_fora_dele():
    mgr = audio.install(mk(NullBackend(), catalog=CATALOG))
    h = hub_com_save("12:00")
    h.enter_pen()
    h.pen.poke(h.pen.cats[0].cat_id)
    h.mode = "menu"
    h.update(0.05)
    assert mgr.requests["pet"] == 0 and mgr.requests["purr"] == 0


def entradas(n: int, kitten: bool = False) -> list[PenEntry]:
    return [PenEntry(f"c{i:03d}", "siames", kitten, "livre") for i in range(n)]


def miados(seed_audio: int, kitten: bool = False, segundos: int = 200) -> list[str]:
    pen = PenController(Random(1), audio_rng=Random(seed_audio))
    pen.sync(entradas(4, kitten))
    out: list[str] = []
    for _ in range(segundos * 30):
        pen.update(1 / 30)
        out += pen.sounds
        pen.sounds.clear()
    return out


def test_pen_sounds_deterministico_por_seed_de_audio_e_so_usa_cues_do_catalogo():
    a = miados(9)
    assert a == miados(9) and len(a) >= 5
    assert set(a) <= set(MEOWS) | {"bed_settle"}
    assert set(a) & set(MEOWS)
    assert a != miados(10)
    assert all(cue in CATALOG["sfx"] for cue in a)


def test_pen_filhotes_usam_o_miado_de_filhote():
    sons = miados(9, kitten=True)
    assert "kitten_mew" in sons and set(sons) <= {"kitten_mew", "bed_settle"}


def test_pen_sounds_nao_altera_a_sequencia_de_movimento_com_a_mesma_seed():
    def rodar(seed_audio: int, esvaziar: bool) -> list[tuple]:
        pen = PenController(Random(42), audio_rng=Random(seed_audio))
        pen.sync(entradas(5))
        for _ in range(60 * 30):
            pen.update(1 / 30)
            if esvaziar:
                pen.sounds.clear()
        return [(c.cat_id, round(c.x, 6), round(c.y, 6), c.state) for c in pen.cats]
    base = rodar(1, True)
    assert rodar(2, True) == base                  # outro RNG de audio, mesmo movimento
    assert rodar(3, False) == base                 # nao esvaziar a fila tambem nao muda nada


# ------------------------------------------------------------------ menu de volume
def test_hit_test_dos_botoes_menos_mais_barra_e_mudo():
    for i, which in enumerate(("musica", "efeitos")):
        assert LH.hit_test(LH.vol_minus(i).center, "menu") == ("vol", which, -1)
        assert LH.hit_test(LH.vol_plus(i).center, "menu") == ("vol", which, 1)
    assert LH.hit_test(LH.mute_button().center, "menu") == ("mute",)
    assert LH.hit_test((0, 0), "menu") is None


def test_hit_test_da_barra_devolve_valor_em_passos_de_10_por_cento():
    bar = LH.vol_bar(1)
    assert LH.hit_test((bar.x, bar.centery), "menu") == ("vol_set", "efeitos", 0.0)
    assert LH.hit_test((bar.right - 1, bar.centery), "menu") == ("vol_set", "efeitos", 1.0)
    for x in range(bar.x, bar.right):
        kind, which, v = LH.hit_test((x, bar.centery), "menu")
        assert kind == "vol_set" and which == "efeitos" and 0.0 <= v <= 1.0
        assert round(v * 10) == pytest.approx(v * 10)


def test_menu_nao_devolve_volume_com_a_confirmacao_aberta():
    assert LH.hit_test(LH.mute_button().center, "menu", confirm=True) is None


def test_clique_no_menu_ajusta_volume_e_mudo_do_manager():
    m = audio.install(mk(catalog=CATALOG))
    h = hub_com_save()
    h.click(("vol", "musica", -1))
    assert m.volume_of("musica") == pytest.approx(0.6)
    h.click(("vol", "efeitos", 1))
    assert m.volume_of("efeitos") == pytest.approx(0.9)
    bar = LH.vol_bar(0)
    h.click(h.hit((bar.x, bar.centery)))
    assert m.volume_of("musica") == 0.0
    h.click(h.hit(LH.mute_button().center))
    assert m.muted is True
    h.click(("mute",))
    assert m.muted is False


@pytest.mark.parametrize("mudo", [False, True])
def test_render_do_menu_com_painel_de_volume_nao_quebra(mudo):
    pygame.init()
    m = audio.install(mk(catalog=CATALOG))
    m.set_muted(mudo)
    m.set_volume("musica", 0.0)
    h = hub_com_save()
    surf, ui = pygame.Surface((W, H)), UIState()
    for _ in range(3):
        h.update(1 / 60)
        draw_hub_frame(surf, h, ui)
    h.confirm_new = True
    draw_hub_frame(surf, h, ui)


# ------------------------------------------------------------------ loop headless com audio ligado
def _loop(monkeypatch, tmp_path, quadros: int, tecla_m_no_quadro: int | None = None) -> int:
    from ui.app_hub import run
    frames = [0]
    real_flip = pygame.display.flip

    def flip() -> None:
        real_flip()
        frames[0] += 1
        if frames[0] == tecla_m_no_quadro:
            pygame.event.post(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_m, mod=0, unicode="m", scancode=16))
        if frames[0] >= quadros:
            pygame.event.post(pygame.event.Event(pygame.QUIT))

    monkeypatch.setattr(pygame.display, "flip", flip)
    asyncio.run(run(1, tmp_path / "save.json", None, "12:00"))
    return frames[0]


def test_loop_headless_do_hub_com_audio_dummy_toca_musica_e_tecla_m_persiste(monkeypatch, tmp_path, prefs_dir):
    # save customizado em tmp_path/save.json; prefs antigas ao lado dele (legado) sao lidas
    # porque PREFS_DIR (isolado em tmp) ainda nao tem prefs.json
    (tmp_path / "prefs.json").write_text(json.dumps({"version": 1, "music": 0.3, "sfx": 0.4, "muted": False}),
                                         encoding="utf-8")
    assert _loop(monkeypatch, tmp_path, 8, tecla_m_no_quadro=3) >= 8
    mgr = audio.manager()
    assert isinstance(mgr.backend, PygameBackend)
    assert mgr.track == "menu_dia"
    assert mgr.muted is True                                   # a tecla M chegou ao manager
    assert mgr.music_volume == 0.3 and mgr.sfx_volume == 0.4   # veio do legado
    novo = json.loads((prefs_dir / "prefs.json").read_text(encoding="utf-8"))
    assert novo["muted"] is True and novo["music"] == 0.3      # escrita sempre no caminho novo
    legado = json.loads((tmp_path / "prefs.json").read_text(encoding="utf-8"))
    assert legado["muted"] is False                            # legado intocado


def test_loop_headless_com_mixer_falhando_segue_rodando(monkeypatch, tmp_path):
    monkeypatch.setenv("CHAOSCATS_AUDIO", "fail")
    assert _loop(monkeypatch, tmp_path, 5) >= 5
    assert audio.manager().backend.available is False


# ------------------------------------------------------------------ mixer tardio (T10.5)
class LateBackend(FakeBackend):
    """Mixer que falha ate `ok` virar True; `try_init` registra as tentativas."""

    def __init__(self) -> None:
        super().__init__(available=False)
        self.disabled = False
        self.ok = False
        self.tries = 0

    def try_init(self) -> bool:
        self.tries += 1
        if self.ok:
            self.available = True
        return self.available


def test_retry_mixer_tardio_falha_na_primeira_e_funciona_no_clique():
    be, clk = LateBackend(), Clock()
    m = mk(be, clk)
    m.set_context("x")
    assert m.retry_backend() is False and be.tries == 1
    antes = len(be.starts)                                      # FakeBackend registra mesmo indisponivel
    be.ok = True
    clk.t = 2000
    assert m.retry_backend() is True
    assert len(be.starts) == antes + 1 and be.starts[-1][0] == "a.ogg"            # retomou a musica do contexto


def test_retry_respeita_intervalo_de_2s_com_relogio_injetado():
    be, clk = LateBackend(), Clock()
    m = mk(be, clk)
    m.retry_backend()
    clk.t = 1999
    m.retry_backend()
    assert be.tries == 1
    clk.t = 2000
    m.retry_backend()
    assert be.tries == 2


def test_retry_com_audio_off_nunca_tenta():
    be, clk = LateBackend(), Clock()
    be.disabled = True
    m = mk(be, clk)
    for i in range(5):
        clk.t = i * 10_000
        assert m.retry_backend() is False
    assert be.tries == 0


def test_retry_com_pygame_backend_off_nunca_tenta_e_fail_tenta_sem_erro(monkeypatch):
    monkeypatch.setenv("CHAOSCATS_AUDIO", "off")
    be = PygameBackend()
    assert be.available is False and be.disabled is True
    clk = Clock()
    m = mk(be, clk)
    assert m.retry_backend() is False
    monkeypatch.setenv("CHAOSCATS_AUDIO", "fail")
    be2 = PygameBackend()
    calls = []
    real = be2.try_init
    be2.try_init = lambda: (calls.append(1), real())[1]
    m2 = mk(be2, clk)
    for t in (0, 500, 2000, 2500, 4000):
        clk.t = t
        assert m2.retry_backend() is False
    assert len(calls) == 3                                      # t=0, 2000, 4000
    assert be2.available is False


def test_retry_limpa_cache_de_sons_para_carregar_com_mixer_novo():
    be, clk = LateBackend(), Clock()
    m = mk(be, clk)
    assert m.play("livre") is False                            # mixer indisponivel
    be.ok = True
    clk.t = 5000
    assert m.retry_backend() is True
    assert m.play("livre") is True


def test_on_event_so_age_em_clique_tecla_e_toque():
    be, clk = LateBackend(), Clock()
    audio.install(mk(be, clk))
    audio.on_event(SimpleNamespace(type=pygame.MOUSEMOTION))
    assert be.tries == 0
    audio.on_event(SimpleNamespace(type=pygame.MOUSEBUTTONDOWN))
    assert be.tries == 1
    clk.t = 3000
    audio.on_event(SimpleNamespace(type=pygame.KEYDOWN))
    assert be.tries == 2


# ------------------------------------------------------------------ prefs unificadas (T10.5)
def _grava(p: Path, **v) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"version": 1, **v}), encoding="utf-8")


def test_setup_sem_argumentos_usa_prefs_dir_isolado(prefs_dir):
    m = audio.setup()
    assert m.prefs_path == prefs_dir / "prefs.json"
    assert prefs_dir != audio.ROOT / "saves"


def test_prefs_legado_so_e_lido_se_o_novo_nao_existe(tmp_path, prefs_dir):
    legado = tmp_path / "antigo"
    _grava(legado / "prefs.json", music=0.2, sfx=0.3, muted=True)
    m = audio.setup(legacy_dirs=(legado,))
    assert (m.music_volume, m.sfx_volume, m.muted) == (0.2, 0.3, True)
    assert not (prefs_dir / "prefs.json").exists()             # leitura nao grava
    _grava(prefs_dir / "prefs.json", music=0.9, sfx=0.8, muted=False)
    m2 = audio.setup(legacy_dirs=(legado,))
    assert (m2.music_volume, m2.sfx_volume, m2.muted) == (0.9, 0.8, False)


def test_prefs_escreve_sempre_no_novo_e_nunca_no_legado(tmp_path, prefs_dir):
    legado = tmp_path / "antigo"
    _grava(legado / "prefs.json", music=0.2, sfx=0.3, muted=False)
    m = audio.setup(legacy_dirs=(legado,))
    m.set_volume("musica", 0.6)
    assert json.loads((prefs_dir / "prefs.json").read_text(encoding="utf-8"))["music"] == 0.6
    assert json.loads((legado / "prefs.json").read_text(encoding="utf-8"))["music"] == 0.2


def test_prefs_legado_corrompido_cai_nos_padroes(tmp_path, prefs_dir):
    legado = tmp_path / "antigo"
    legado.mkdir()
    (legado / "prefs.json").write_text("{lixo", encoding="utf-8")
    m = audio.setup(legacy_dirs=(legado,))
    assert m.music_volume == m.default_music and m.muted is False
