"""T10.2 - converte os arquivos brutos de assets/audio/_src nos OGG finais do manifesto data/audio.json.

Ferramenta de desenvolvimento (nao e dependencia do jogo). Requer: numpy, scipy, soundfile (libsndfile com Vorbis),
pyloudnorm.  Uso:  python assets/tools/build_audio.py   (idempotente; reescreve sfx/ e music/)

Cada receita descreve: fonte(s), ganho de loudness alvo, filtro passa-baixa, mudanca de velocidade/pitch,
duracao maxima e (musica) quantas repeticoes + loop sem clique por crossfade do final sobre o inicio.
"""
from __future__ import annotations

import json
import sys
from math import gcd
from pathlib import Path

import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy.signal import butter, resample_poly, sosfilt

ROOT = Path(__file__).resolve().parents[2]
AUDIO = ROOT / "assets" / "audio"
SRC = AUDIO / "_src"
SR_SFX = 44100
SR_MUS = 44100

SFX_LUFS = -16.0
MUS_LUFS = -20.0
PEAK_SFX = 0.84   # ~ -1.5 dB (margem para o overshoot do Vorbis)
PEAK_MUS = 0.84

K = "kenney_interface/Audio/"
KR = "kenney_rpg/OGG/"
KU = "kenney_ui/"
RD = "oga_rd100/"
CM = "oga_cure/"
MG = "oga_magic/"
CAT = "oga/"

# nome do arquivo final (sem extensao) -> receita
# chaves: src (str | list p/ sequencia), speed (1.0=original; >1 mais agudo/curto), lp (Hz), max (s),
#         gain_db (offset sobre o alvo), start (s), seq_gap (s)
SFX: dict[str, dict] = {
    "ui_click": dict(src=KU + "click1.wav", lp=9000),
    "ui_click_2": dict(src=KU + "click3.wav", lp=9000),
    "ui_hover": dict(src=KU + "rollover2.wav", lp=8000, gain_db=-5),
    "ui_back": dict(src=K + "back_002.ogg", lp=9000),
    "ui_denied": dict(src=K + "error_001.ogg", speed=0.85, lp=4500, gain_db=-2),
    "coin": dict(src=KR + "handleCoins2.ogg", lp=9000),
    "coin_2": dict(src=KR + "handleCoins.ogg", lp=9000, max=0.7),
    "ui_open_modal": dict(src=K + "open_002.ogg", lp=9000),
    "card_draw": dict(src=KR + "bookFlip3.ogg", lp=8000),
    "card_draw_2": dict(src=KR + "bookFlip2.ogg", lp=8000, max=0.4),
    "card_play_cat": dict(src=KR + "bookPlace2.ogg", lp=7000),
    "card_play_effect": dict(src=MG + "magical_5.ogg", lp=9000, max=0.9, gain_db=-2),
    "card_play_spirit": dict(src=CM + "Cure2.wav", speed=0.9, lp=6000, max=1.0, gain_db=-2),
    "attack_swing": dict(src=KR + "cloth4.ogg", speed=1.3, lp=7000),
    "attack_swing_2": dict(src=KR + "cloth2.ogg", speed=1.4, lp=7000),
    "attack_hit": dict(src=RD + "hit_01.ogg", lp=5000),
    "attack_hit_2": dict(src=RD + "hit_02.ogg", lp=5000),
    "leader_hit": dict(src=RD + "slam_04.ogg", lp=4500, gain_db=1),
    "cat_death": dict(src=CAT + "cat_softmew.wav", speed=0.8, lp=7000, max=1.2),
    "cat_death_2": dict(src=CAT + "Meow.ogg", speed=0.7, lp=7000),
    "buff": dict(src=MG + "magical_1_0.ogg", lp=9000, max=1.0, gain_db=-2),
    "heal": dict(src=CM + "Cure1.wav", lp=9000, max=1.4, gain_db=-2),
    "shield_protected": dict(src=RD + "bell_02.ogg", speed=1.1, lp=7000),
    "turn_start_player": dict(src=K + "confirmation_001.ogg", lp=9000),
    "turn_start_enemy": dict(src=K + "bong_001.ogg", speed=0.7, lp=6000),
    "energy_up": dict(src=K + "pluck_002.ogg", speed=1.25, lp=9000),
    "duel_victory": dict(src="oga_music/winfretless_0.ogg", lp=9000, max=2.0),
    "duel_defeat": dict(src=RD + "gong_02.ogg", speed=0.9, lp=3500, max=1.6, gain_db=-2),
    "node_select": dict(src=K + "select_003.ogg", lp=9000),
    "draft_pick": dict(src=K + "confirmation_003.ogg", lp=9000),
    "rest": dict(src=CM + "Cure6.wav", speed=0.95, lp=5000, max=2.0, gain_db=-3),
    "adopt": dict(src=CAT + "cat_mewpurr.wav", lp=8000, max=1.5),
    "breed_start": dict(src=MG + "magical_3.ogg", lp=6000, max=1.6, gain_db=-3),
    "kitten_born": dict(src=[CAT + "kitten_mew-1_0.ogg", K + "glass_003.ogg"], speed=1.2, lp=9000, seq_gap=0.05),
    "level_up": dict(src=MG + "magical_7_0.ogg", lp=9000, max=1.6),
    "meow_1": dict(src=CAT + "Meow.ogg", lp=8000),
    "meow_2": dict(src=CAT + "cat_mewfood.wav", lp=8000, max=1.1),
    "meow_3": dict(src=CAT + "cat_softmew.wav", lp=8000, max=1.5),
    "meow_4": dict(src=CAT + "cat_mewpurr2.wav", lp=8000, max=1.7),
    "kitten_mew": dict(src=CAT + "kitten_mew-1_0.ogg", lp=9000),
    "purr": dict(src=CAT + "cat_purrsleepy_loop.wav", lp=6000, max=1.9, start=0.6, gain_db=-3),
    "bed_settle": dict(src=KR + "cloth1.ogg", lp=3500, gain_db=-2),
    "pet": dict(src=KR + "handleSmallLeather.ogg", lp=3500, gain_db=-3),
    "pet_2": dict(src=CAT + "cat_purractive_loop.wav", lp=5000, max=0.9, start=0.5, gain_db=-3),
}

OM = "oga_music/"
# musica: reps = repeticoes do trecho; lp opcional; lufs; loop = costura final->inicio por crossfade
MUSIC: dict[str, dict] = {
    "menu_dia": dict(src=OM + "JRPG%20Piano.mp3", reps=3, loop=True, lufs=-20.0, xf=1.0),
    "menu_noite": dict(src=OM + "Heavenly%20Loop_0.ogg", reps=2, loop=True, lufs=-23.0, lp=3500, xf=1.5),
    "mapa_run": dict(src=OM + "the_arplands_0.ogg", reps=1, loop=True, lufs=-20.0, xf=1.0),
    "duelo": dict(src=OM + "rbl_0.mp3", reps=2, loop=True, lufs=-20.0, xf=1.0),
    "duelo_chefe": dict(src=OM + "boss_battle_loop_0.mp3", reps=1, loop=True, lufs=-20.0, xf=1.0),
    "vitoria": dict(src=OM + "Heavy_ConceptB.wav", reps=1, loop=False, lufs=-20.0, fade_out=1.0),
    "derrota": dict(src=OM + "Game%20over%20jingle_0.ogg", reps=1, loop=False, lufs=-20.0, fade_out=0.8),
}


def read(rel: str, sr: int) -> np.ndarray:
    """Le (src ja decodificado ou nao) -> float32 [n, ch] na taxa sr. Nomes com %20 sao tratados."""
    p = SRC / rel
    if not p.exists():
        p = SRC / rel.replace("%20", " ")
    x, fs = sf.read(str(p), always_2d=True, dtype="float32")
    if fs != sr:
        g = gcd(fs, sr)
        x = resample_poly(x, sr // g, fs // g, axis=0).astype("float32")
    return x


def lowpass(x: np.ndarray, hz: float, sr: int) -> np.ndarray:
    sos = butter(4, hz / (sr / 2), btype="low", output="sos")
    return sosfilt(sos, x, axis=0).astype("float32")


def change_speed(x: np.ndarray, f: float) -> np.ndarray:
    if abs(f - 1.0) < 1e-3:
        return x
    num, den = int(round(100 / f)), 100
    g = gcd(num, den)
    return resample_poly(x, num // g, den // g, axis=0).astype("float32")


def trim_silence(x: np.ndarray, thr_db: float = -50.0, keep_head: float = 0.002, sr: int = SR_SFX) -> np.ndarray:
    a = np.abs(x).max(axis=1)
    idx = np.where(a > 10 ** (thr_db / 20) * max(a.max(), 1e-9))[0]
    if len(idx) == 0:
        return x
    s = max(0, idx[0] - int(keep_head * sr))
    e = min(len(x), idx[-1] + int(0.02 * sr))
    return x[s:e]


def fade(x: np.ndarray, fin: float, fout: float, sr: int) -> np.ndarray:
    x = x.copy()
    ni, no = int(fin * sr), int(fout * sr)
    if ni:
        x[:ni] *= np.linspace(0, 1, ni, dtype="float32")[:, None]
    if no:
        x[-no:] *= np.linspace(1, 0, no, dtype="float32")[:, None]
    return x


def loudness_gain(x: np.ndarray, sr: int, target: float) -> float:
    pad = x
    if len(x) < int(0.8 * sr):  # medidor BS.1770 precisa de >= 0.4 s
        pad = np.concatenate([x, np.zeros((int(0.8 * sr) - len(x), x.shape[1]), "float32")])
    lufs = pyln.Meter(sr).integrated_loudness(pad)
    if not np.isfinite(lufs):
        return 1.0
    return 10 ** ((target - lufs) / 20)


def limit(x: np.ndarray, peak: float) -> np.ndarray:
    """Compressao suave nos picos (tanh) e depois escala para o pico alvo."""
    m = np.abs(x).max()
    if m <= peak:
        return x
    knee = peak * 0.7
    a = np.abs(x)
    over = a > knee
    y = x.copy()
    y[over] = np.sign(x[over]) * (knee + (peak - knee) * np.tanh((a[over] - knee) / (peak - knee)))
    return y * min(1.0, peak / np.abs(y).max())


def build_sfx(name: str, r: dict) -> np.ndarray:
    srcs = r["src"] if isinstance(r["src"], list) else [r["src"]]
    parts = []
    for s in srcs:
        x = read(s, SR_SFX).mean(axis=1, keepdims=True)  # mono
        x = trim_silence(x)
        if r.get("start"):
            x = x[int(r["start"] * SR_SFX):]
        x = change_speed(x, r.get("speed", 1.0)) if not isinstance(r["src"], list) or s == srcs[0] else x
        parts.append(x)
    gap = np.zeros((int(r.get("seq_gap", 0) * SR_SFX), 1), "float32")
    x = parts[0]
    for p in parts[1:]:
        x = np.concatenate([x, gap, p])
    if r.get("lp"):
        x = lowpass(x, r["lp"], SR_SFX)
    mx = r.get("max", 2.0)
    mx = min(mx, 2.0)
    if len(x) > int(mx * SR_SFX):
        x = x[: int(mx * SR_SFX)]
    x = trim_silence(x)
    tail = min(0.12, 0.25 * len(x) / SR_SFX)
    x = fade(x, 0.002, tail, SR_SFX)
    if len(x) < int(0.06 * SR_SFX):  # piso 0,05 s
        x = np.concatenate([x, np.zeros((int(0.06 * SR_SFX) - len(x), 1), "float32")])
    g = loudness_gain(x, SR_SFX, SFX_LUFS + r.get("gain_db", 0.0))
    return limit(x * g, PEAK_SFX)


def build_music(name: str, r: dict) -> np.ndarray:
    x = read(r["src"], SR_MUS)
    if x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    x = trim_silence(x, -55.0, 0.0, SR_MUS)
    if r.get("lp"):
        x = lowpass(x, r["lp"], SR_MUS)
    xf = int(r.get("xf", 1.0) * SR_MUS)
    if r["loop"]:
        base = x
        out = base
        for _ in range(r["reps"] - 1):  # junta repeticoes com crossfade de potencia constante
            out = _xfade(out, base, xf)
        # costura do fim sobre o inicio: o arquivo resultante e ciclico
        head, tail = out[:xf], out[-xf:]
        t = np.linspace(0, 1, xf, dtype="float32")[:, None]
        body = out[:-xf].copy()
        body[:xf] = head * np.sin(t * np.pi / 2) + tail * np.cos(t * np.pi / 2)
        out = body
    else:
        out = fade(x, 0.0, r.get("fade_out", 0.5), SR_MUS)
    g = loudness_gain(out, SR_MUS, r["lufs"])
    return limit(out * g, PEAK_MUS)


def _xfade(a: np.ndarray, b: np.ndarray, n: int) -> np.ndarray:
    t = np.linspace(0, 1, n, dtype="float32")[:, None]
    mid = a[-n:] * np.cos(t * np.pi / 2) + b[:n] * np.sin(t * np.pi / 2)
    return np.concatenate([a[:-n], mid, b[n:]])


def write(path: Path, x: np.ndarray, sr: int) -> None:
    """Grava OGG; se o pico decodificado passar de ~0,95 (overshoot do Vorbis), reduz o ganho e regrava."""
    for _ in range(6):
        _write(path, x, sr)
        peak = float(np.abs(sf.read(str(path), always_2d=True)[0]).max())
        if peak < 0.95:
            return
        x = x * (0.9 / peak)


def _write(path: Path, x: np.ndarray, sr: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # em blocos: escrever tudo de uma vez estoura a pilha do libsndfile no Windows
    with sf.SoundFile(str(path), "w", samplerate=sr, channels=x.shape[1], format="OGG", subtype="VORBIS") as f:
        for i in range(0, len(x), 16384):
            f.write(x[i:i + 16384])


def main() -> int:
    manifest = json.loads((ROOT / "data" / "audio.json").read_text(encoding="utf-8"))
    wanted = {Path(f).stem for c in manifest["sfx"].values() for f in c["files"]}
    wanted_m = {Path(c["file"]).stem for c in manifest["music"].values()}
    missing = (wanted - set(SFX)) | (wanted_m - set(MUSIC))
    if missing:
        print("sem receita:", sorted(missing))
    ovr_p = ROOT / "assets" / "tools" / "audio_overrides.json"  # cues trocados por candidatos (T10.6): nao regravar
    skip = set(json.loads(ovr_p.read_text(encoding="utf-8"))) if ovr_p.exists() else set()
    for name in skip:
        SFX.pop(name, None)
        MUSIC.pop(name, None)
    for name, r in SFX.items():
        try:
            write(AUDIO / "sfx" / f"{name}.ogg", build_sfx(name, r), SR_SFX)
        except Exception as e:  # noqa: BLE001 - relata e segue
            print("FALHA sfx", name, e)
    for name, r in MUSIC.items():
        try:
            write(AUDIO / "music" / f"{name}.ogg", build_music(name, r), SR_MUS)
        except Exception as e:  # noqa: BLE001
            print("FALHA music", name, e)
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
