"""`data/ui_timing.json`, `ui/timing.py` e `ui/anim.py` (T12.5, a partir de T12.0 a T12.3)."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, validate
from jsonschema.exceptions import ValidationError

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
SCHEMA = json.loads((DATA / "schemas" / "ui_timing.schema.json").read_text(encoding="utf-8"))
TIMING = json.loads((DATA / "ui_timing.json").read_text(encoding="utf-8"))
EX = DATA / "schemas" / "examples"


def invalido(**mudancas) -> dict:
    d = copy.deepcopy(TIMING)
    for caminho, valor in mudancas.items():
        *pais, folha = caminho.split("__")
        alvo = d
        for p in pais:
            alvo = alvo[p]
        alvo[folha] = valor
    return d


# ------------------------------------------------------------------ dados
def test_ui_timing_json_valida_no_schema():
    validate(TIMING, SCHEMA)


def test_schema_ui_timing_e_um_schema_valido():
    Draft202012Validator.check_schema(SCHEMA)


def test_exemplo_valido_passa_no_schema():
    validate(json.loads((EX / "ui_timing.example.json").read_text(encoding="utf-8")), SCHEMA)


@pytest.mark.parametrize("arq", sorted(p.name for p in (EX / "invalid").glob("ui_timing.invalid_*.json")))
def test_exemplos_invalidos_de_ui_timing_falham(arq):
    with pytest.raises(ValidationError):
        validate(json.loads((EX / "invalid" / arq).read_text(encoding="utf-8")), SCHEMA)


def test_existem_os_quatro_exemplos_invalidos_pedidos():
    nomes = {p.stem for p in (EX / "invalid").glob("ui_timing.invalid_*.json")}
    assert len(nomes) >= 4


def test_boss_intro_duration_existe_e_e_positiva():
    assert TIMING["boss_intro"]["duration"] > 0


def test_enemy_speed_default_esta_nas_opcoes():
    es = TIMING["enemy_speed"]
    assert es["default"] in es["options"]
    assert set(es["options"]) >= {"1x", "2x", "rapido"}
    assert all(v > 0 for v in es["options"].values())


@pytest.mark.parametrize("mud", [
    {"lunge__reach": 1.5},
    {"lunge__duration": -0.1},
    {"breathing__period": 0},
    {"poof__particles": 3.5},
    {"hitstop__normal": "rapido"},
    {"extra": 1},
    {"hand__chave_nova": 1},
])
def test_schema_rejeita_valores_fora_da_regra(mud):
    with pytest.raises(ValidationError):
        validate(invalido(**mud), SCHEMA)


def test_schema_rejeita_bloco_ausente():
    d = copy.deepcopy(TIMING)
    del d["boss_intro"]
    with pytest.raises(ValidationError):
        validate(d, SCHEMA)


def test_check_ui_timing_acusa_default_fora_das_opcoes(capsys):
    sys.path.insert(0, str(DATA))
    try:
        import validate_data
    finally:
        sys.path.remove(str(DATA))
    assert validate_data.check_ui_timing({"ui_timing": TIMING}) == 0
    ruim = invalido(enemy_speed__default="3x")
    assert validate_data.check_ui_timing({"ui_timing": ruim}) == 1
    assert validate_data.check_ui_timing({}) == 1


def test_validate_data_passa_com_ui_timing():
    r = subprocess.run([sys.executable, str(DATA / "validate_data.py")], cwd=ROOT,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ui_timing" in r.stdout


# ------------------------------------------------------------------ ui/timing.py
@pytest.fixture
def tm():
    from ui import timing
    yield timing
    timing.use(None)


def test_timing_le_os_valores_do_arquivo(tm):
    t = tm.load()
    assert t.lunge.duration == TIMING["lunge"]["duration"]
    assert t.beats["Attacked"] == TIMING["beats"]["Attacked"]
    assert t.boss_intro.duration == TIMING["boss_intro"]["duration"]
    assert t.enemy_speed.options.as_dict() == TIMING["enemy_speed"]["options"]


def test_padroes_do_codigo_batem_com_o_arquivo(tm):
    """Fallback e JSON não podem divergir: o jogador não vê diferença se o arquivo faltar."""
    assert tm.load(Path("nao/existe.json")).as_dict() == tm.load().as_dict()


def test_arquivo_ausente_usa_so_os_padroes(tm, tmp_path):
    t = tm.load(tmp_path / "nada.json")
    assert t.lunge.reach == tm.DEFAULTS["lunge"]["reach"]


@pytest.mark.parametrize("conteudo", ["", "{quebrado", "[1, 2]", "null", "42", '"texto"'])
def test_arquivo_corrompido_ou_de_tipo_errado_cai_nos_padroes(tm, tmp_path, conteudo):
    p = tmp_path / "t.json"
    p.write_text(conteudo, encoding="utf-8")
    assert tm.load(p).as_dict() == tm.Timing().as_dict()


def test_fallback_por_chave_quando_falta_so_uma(tm, tmp_path):
    p = tmp_path / "t.json"
    p.write_text(json.dumps({"lunge": {"duration": 0.9}, "hitstop": {"normal": 0.2}}), encoding="utf-8")
    t = tm.load(p)
    assert t.lunge.duration == 0.9                                  # valor do arquivo
    assert t.lunge.reach == tm.DEFAULTS["lunge"]["reach"]           # faltou: padrão da chave
    assert t.hitstop.normal == 0.2 and t.hitstop.lethal == tm.DEFAULTS["hitstop"]["lethal"]
    assert t.beats["Deadlock"] == tm.DEFAULTS["beats"]["Deadlock"]  # bloco inteiro ausente


@pytest.mark.parametrize("raw, caminho", [
    ({"lunge": {"reach": 1.5}}, ("lunge", "reach")),
    ({"lunge": {"duration": -1}}, ("lunge", "duration")),
    ({"breathing": {"period": 0}}, ("breathing", "period")),
    ({"boss_intro": {"duration": 0}}, ("boss_intro", "duration")),
    ({"hitstop": {"normal": "x"}}, ("hitstop", "normal")),
    ({"hitstop": {"normal": True}}, ("hitstop", "normal")),
    ({"poof": {"particles": 2.5}}, ("poof", "particles")),
    ({"lunge": "texto"}, ("lunge", "duration")),
])
def test_valor_invalido_cai_no_padrao_da_chave(tm, raw, caminho):
    t = tm.Timing(raw)
    atual = t.as_dict()
    padrao = tm.DEFAULTS
    for k in caminho:
        atual, padrao = atual[k], padrao[k]
    assert atual == padrao


def test_chave_desconhecida_e_ignorada(tm):
    assert "novo" not in tm.Timing({"novo": {"x": 1}}).as_dict()


def test_enemy_speed_default_fora_das_opcoes_vira_uma_opcao_valida(tm):
    t = tm.Timing({"enemy_speed": {"options": {"a": 1.0, "b": 0.5}, "default": "zzz"}})
    assert t.enemy_speed.default in t.enemy_speed.options.as_dict()


def test_enemy_speed_opcoes_invalidas_usam_as_padrao(tm):
    t = tm.Timing({"enemy_speed": {"options": {"a": -1}, "default": "1x"}})
    assert t.enemy_speed.options.as_dict() == tm.DEFAULTS["enemy_speed"]["options"]


def test_acesso_por_atributo_e_por_chave(tm):
    t = tm.Timing()
    assert t.lunge.duration == t.lunge["duration"] == t["lunge"]["duration"]
    with pytest.raises(AttributeError):
        t.lunge.nao_existe


def test_use_injeta_e_none_recarrega(tm):
    tm.use(tm.Timing({"lunge": {"duration": 0.77}}))
    assert tm.current().lunge.duration == 0.77
    tm.use(None)
    assert tm.current().lunge.duration == TIMING["lunge"]["duration"]


def test_timing_nao_compartilha_estado_mutavel_com_os_padroes(tm):
    t = tm.Timing()
    t.as_dict()["lunge"]["duration"] = 99
    assert tm.Timing().lunge.duration == tm.DEFAULTS["lunge"]["duration"]


# ------------------------------------------------------------------ ui/anim.py
@pytest.fixture
def tmg():
    from ui.timing import Timing
    return Timing()


def test_clamp_e_easings_nos_limites():
    from ui import anim
    assert anim.clamp01(-5) == 0.0 and anim.clamp01(7) == 1.0 and anim.clamp01(0.3) == 0.3
    for f in (anim.ease_out, anim.ease_in_out):
        assert f(0) == 0.0 and f(1) == 1.0
        assert f(-3) == 0.0 and f(9) == 1.0               # fora do intervalo é limitado


def test_easings_sao_monotonicos_e_ficam_em_0_1():
    from ui import anim
    pts = [i / 200 for i in range(201)]
    for f in (anim.ease_out, anim.ease_in_out):
        v = [f(u) for u in pts]
        assert all(b >= a for a, b in zip(v, v[1:]))
        assert all(0.0 <= x <= 1.0 for x in v)


def test_ease_out_comeca_rapido_e_ease_in_out_e_simetrico():
    from ui import anim
    assert anim.ease_out(0.1) > 0.1
    assert anim.ease_in_out(0.5) == pytest.approx(0.5)
    assert anim.ease_in_out(0.2) == pytest.approx(1 - anim.ease_in_out(0.8))


def test_impacto_da_investida_e_fracao_da_duracao():
    from ui import anim
    assert anim.impact_time(0.4) == pytest.approx(0.4 * anim.IMPACT_FRAC)
    assert anim.impact_time(0) == 0


def test_investida_comeca_em_zero_chega_ao_alcance_no_impacto_e_volta_a_zero():
    from ui import anim
    dur, reach = 0.25, 0.85
    assert anim.lunge_fraction(0, dur, reach) == 0.0
    assert anim.lunge_fraction(anim.impact_time(dur), dur, reach) == pytest.approx(reach)
    assert anim.lunge_fraction(dur, dur, reach) == pytest.approx(0.0)
    assert anim.lunge_fraction(dur * 5, dur, reach) == pytest.approx(0.0)      # depois do fim
    assert anim.lunge_fraction(-1, dur, reach) == 0.0


def test_investida_sobe_ate_o_impacto_e_desce_depois():
    from ui import anim
    dur, reach = 0.3, 1.0
    imp = anim.impact_time(dur)
    subida = [anim.lunge_fraction(imp * i / 50, dur, reach) for i in range(51)]
    descida = [anim.lunge_fraction(imp + (dur - imp) * i / 50, dur, reach) for i in range(51)]
    assert all(b >= a for a, b in zip(subida, subida[1:]))
    assert all(b <= a for a, b in zip(descida, descida[1:]))
    assert all(0 <= x <= reach + 1e-9 for x in subida + descida)


def test_investida_com_duracao_zero_nao_divide_por_zero():
    from ui import anim
    assert anim.lunge_fraction(0.1, 0, 0.8) == pytest.approx(0.0)


def test_lunge_offset_e_inteiro_e_vai_na_direcao_do_alvo():
    from ui import anim
    dx, dy = anim.lunge_offset((100, 100), (200, 60), anim.impact_time(0.25), 0.25, 0.85)
    assert isinstance(dx, int) and isinstance(dy, int)
    assert dx == 85 and dy == -34
    assert anim.lunge_offset((10, 10), (10, 10), 0.1, 0.25, 0.85) == (0, 0)


def test_respiracao_fica_dentro_da_amplitude_e_e_periodica():
    from ui import anim
    vals = {anim.breath_offset(t / 10, "player", 2, 1, 2.4) for t in range(100)}
    assert vals <= {-1, 0, 1} and len(vals) > 1
    assert anim.breath_offset(0.7, "enemy", 3, 2, 2.4) == anim.breath_offset(0.7 + 2.4, "enemy", 3, 2, 2.4)
    assert all(anim.breath_offset(t / 7, "player", 0, 0, 2.4) == 0 for t in range(30))


def test_fase_da_respiracao_e_deterministica_e_varia_por_slot_e_lado():
    from ui import anim
    fases = {anim.breath_phase(s, n) for s in ("player", "enemy") for n in range(5)}
    assert len(fases) == 10
    assert anim.breath_phase("player", 3) == anim.breath_phase("player", 3)


def test_tremor_decai_ate_zero_e_para_no_fim():
    from ui import anim
    assert anim.shake_offset(5, 0.25, 0.25) == (0, 0)
    assert anim.shake_offset(5, 0.25, 9) == (0, 0)
    assert anim.shake_offset(5, 0, 0) == (0, 0)
    assert anim.shake_offset(0, 0.25, 0.05) == (0, 0)
    amp = [max(map(abs, anim.shake_offset(6, 0.4, i * 0.001 + 0.0))) for i in range(0, 400, 40)]
    assert max(amp) <= 6
    assert all(isinstance(v, int) for v in anim.shake_offset(5, 0.25, 0.03))
    tarde = max(max(map(abs, anim.shake_offset(6, 0.4, 0.39 + i * 0.0001))) for i in range(10))
    assert tarde <= 1


def test_estilo_do_numero_de_dano_normal_vs_grande_vs_cura(tmg):
    from ui import anim
    thr = tmg.damage_number.big_threshold
    pequeno = anim.damage_style(thr - 1, 1.0, tmg.damage_number.life, tmg, True)
    grande = anim.damage_style(thr, 1.0, tmg.damage_number.life, tmg, True)
    cura = anim.damage_style(thr + 4, 1.0, tmg.damage_number.life, tmg, False)
    assert pequeno[2] == 0.0 and grande[2] == 1.0 and cura[2] == 0.0       # só dano alto esquenta
    assert grande[0] > pequeno[0]
    assert cura[0] == pequeno[0]


def test_numero_de_dano_surge_grande_encolhe_e_sobe(tmg):
    from ui import anim
    dn = tmg.damage_number
    s0, r0, _ = anim.damage_style(3, 0.0, dn.life, tmg, True)
    s1, r1, _ = anim.damage_style(3, dn.pop_time * 2, dn.life, tmg, True)
    s2, r2, _ = anim.damage_style(3, dn.life, dn.life, tmg, True)
    assert s0 >= s1 >= 1
    assert r0 == 0 and r0 <= r1 <= r2 == dn.rise
    assert isinstance(s0, int) and isinstance(r1, int)


def test_poof_e_deterministico_e_as_particulas_encolhem(tmg):
    from ui import anim
    a = anim.poof_particles(3, 0.2, tmg)
    assert a == anim.poof_particles(3, 0.2, tmg)
    assert len(a) == tmg.poof.particles
    assert a != anim.poof_particles(4, 0.2, tmg)
    inicio = anim.poof_particles(3, 0.0, tmg)
    assert all(dx == 0 for dx, _, _, _ in inicio)
    fim = anim.poof_particles(3, tmg.poof.life, tmg)
    assert all(t in (0, 1) for *_, t in a)
    assert sum(s for _, _, s, _ in fim) < sum(s for _, _, s, _ in inicio)
    assert all(s >= 1 for _, _, s, _ in a + inicio + fim)


def test_funcoes_de_anim_nao_usam_o_random_global(monkeypatch, tmg):
    import random

    from ui import anim

    def boom(*a, **k):
        raise AssertionError("sorteio proibido em ui/anim")

    for nome in ("random", "randint", "choice", "uniform", "shuffle", "randrange"):
        monkeypatch.setattr(random, nome, boom)
    anim.poof_particles(1, 0.1, tmg)
    anim.damage_style(4, 0.1, 1.0, tmg, True)
    anim.shake_offset(3, 0.2, 0.05)
    anim.breath_offset(1.0, "player", 1, 1, 2.4)


def test_hover_da_mao_e_afastamento_das_vizinhas():
    from ui import anim
    assert anim.hand_hover_factor(5.0, 5.0) == 0.0
    assert anim.hand_hover_factor(6.0, 5.0) == 1.0
    assert anim.hand_hover_factor(5.0, 5.0, dur=0) == 1.0
    assert anim.spread_dx(2, 2, 10) == 0
    assert anim.spread_dx(3, 2, 10) == 10 and anim.spread_dx(1, 2, 10) == -10
    assert anim.spread_dx(4, 2, 10) == 5 and anim.spread_dx(0, 2, 10) == -5
    assert anim.spread_dx(6, 2, 10) == 0


def test_cristais_de_energia_acendem_e_apagam_um_a_um():
    from ui import anim
    acesos = [anim.gems_lit("on", i * 0.06, 0.06, 4, 0) for i in range(8)]
    assert acesos[0] == 0 and acesos[-1] == 4
    assert all(b >= a for a, b in zip(acesos, acesos[1:]))
    assert max(acesos) == 4
    apagados = [anim.gems_lit("off", i * 0.06, 0.06, 5, 2) for i in range(8)]
    assert apagados[0] == 5 and apagados[-1] == 2
    assert all(b <= a for a, b in zip(apagados, apagados[1:]))
    assert anim.gems_lit("on", 0.0, 0, 3, 0) == 3             # sem intervalo: já completo
