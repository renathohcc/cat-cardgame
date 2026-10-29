"""T10.6 - gera os CANDIDATOS de audio em assets/audio/_candidatos/<cue>/<cand>.ogg (nao toca nos arquivos de producao).

Ferramenta de desenvolvimento. Requer numpy, scipy, soundfile, pyloudnorm. Uso: python assets/tools/build_audio_candidates.py
Reusa o pipeline de build_audio.py (mono 44,1 kHz, -16 LUFS sfx; estereo -20 LUFS musica; limitador; Vorbis).
Receitas de sfx: src (relativo a _src), a/b (trecho em s), speed, glide=(r0,r1) (pitch deslizante), hp, lp, max, gain_db,
start/offset; ou synth="..." (sintetizado por script, sem fonte externa); ou mix=[(receita, atraso_s), ...].
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfilt

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_audio as B  # noqa: E402

OUT = B.AUDIO / "_candidatos"
SR = B.SR_SFX
BSB = "bsb/"
OP = "oga_pop/"


def highpass(x: np.ndarray, hz: float) -> np.ndarray:
    return sosfilt(butter(2, hz / (SR / 2), btype="high", output="sos"), x, axis=0).astype("float32")


def glide(x: np.ndarray, r0: float, r1: float) -> np.ndarray:
    """Pitch deslizante: taxa de leitura vai linearmente de r0 a r1 (r<1 = mais grave/lento)."""
    n_out = int(len(x) / ((r0 + r1) / 2))
    rate = np.linspace(r0, r1, n_out)
    pos = np.cumsum(rate)
    pos = pos[pos < len(x) - 1]
    return np.interp(pos, np.arange(len(x)), x[:, 0]).astype("float32")[:, None]


def env_exp(n: int, tau: float, attack: float = 0.004) -> np.ndarray:
    t = np.arange(n) / SR
    e = np.exp(-t / tau)
    a = int(attack * SR)
    e[:a] *= np.linspace(0, 1, a)
    return e.astype("float32")


def synth(kind: str, seed: int = 1) -> np.ndarray:
    rng = np.random.default_rng(seed)
    t = lambda d: np.arange(int(d * SR)) / SR  # noqa: E731
    if kind.startswith("poof"):
        # sopro de ruido filtrado (puff) + 'bloop' tonal macio descendente
        hi = 1.0 if kind == "poof" else 1.25
        n = int(0.45 * SR)
        noise = rng.standard_normal(n).astype("float32")
        sos = butter(2, [350 * hi / (SR / 2), 2600 * hi / (SR / 2)], btype="band", output="sos")
        puff = sosfilt(sos, noise) * env_exp(n, 0.07, 0.006)
        d = 0.3
        tt = t(d)
        f = (620 if kind == "poof" else 760) * np.exp(-tt * 3.2)
        ph = 2 * np.pi * np.cumsum(f) / SR
        blip = (np.sin(ph) + 0.25 * np.sin(2 * ph)) * env_exp(len(tt), 0.09, 0.004)
        out = np.zeros(int(0.55 * SR), "float32")
        out[:n] += puff * 1.2
        out[: len(blip)] += blip.astype("float32") * 0.55
        return out[:, None]
    if kind == "blip":  # 'pet': dois toques tonais macios, subindo
        out = np.zeros(int(0.42 * SR), "float32")
        for off, fr in ((0.0, 660.0), (0.11, 880.0)):
            tt = t(0.22)
            s = np.sin(2 * np.pi * fr * tt) + 0.2 * np.sin(2 * np.pi * 2 * fr * tt)
            s = (s * env_exp(len(tt), 0.07, 0.006)).astype("float32")
            i = int(off * SR)
            out[i:i + len(s)] += s
        return out[:, None]
    if kind == "blip2":  # um 'bip' redondo com leve vibrato
        tt = t(0.3)
        f = 740 * (1 + 0.012 * np.sin(2 * np.pi * 14 * tt))
        s = np.sin(2 * np.pi * np.cumsum(f) / SR) * env_exp(len(tt), 0.1, 0.008)
        return s.astype("float32")[:, None]
    if kind == "falling":  # 3 notas macias descendo (queda suave)
        out = np.zeros(int(0.75 * SR), "float32")
        for off, fr in ((0.0, 784.0), (0.14, 659.0), (0.28, 523.0)):
            tt = t(0.35)
            s = (np.sin(2 * np.pi * fr * tt) + 0.15 * np.sin(2 * np.pi * 2 * fr * tt)) * env_exp(len(tt), 0.1, 0.006)
            i = int(off * SR)
            out[i:i + len(s)] += s.astype("float32")
        return out[:, None]
    if kind == "purr":  # ronronar suave: ruido passa-faixa modulado em ~25 Hz
        d = 1.9
        tt = t(d)
        noise = rng.standard_normal(len(tt)).astype("float32")
        sos = butter(2, [70 / (SR / 2), 700 / (SR / 2)], btype="band", output="sos")
        body = sosfilt(sos, noise)
        am = 0.55 + 0.45 * np.sin(2 * np.pi * 25 * tt) ** 2
        hum = np.sin(2 * np.pi * 110 * tt) * 0.25
        s = (body * am + hum * am).astype("float32")
        s *= np.minimum(1, np.minimum(tt / 0.25, (d - tt) / 0.4)).astype("float32")
        return s[:, None]
    raise ValueError(kind)


def render(r: dict) -> np.ndarray:
    if "mix" in r:
        parts = []
        for sub, off in r["mix"]:
            p = B.trim_silence(render(sub))
            p = p / max(float(np.abs(p).max()), 1e-6) * 0.5 * 10 ** (sub.get("gain_db", 0) / 20)  # picos casados
            parts.append((p.astype("float32"), off))
        n = max(int(off * SR) + len(p) for p, off in parts)
        out = np.zeros((n, 1), "float32")
        for p, off in parts:
            out[int(off * SR): int(off * SR) + len(p)] += p
        return out
    if "synth" in r:
        x = synth(r["synth"], r.get("seed", 1))
    else:
        x = B.read(r["src"], SR).mean(axis=1, keepdims=True)
        a, b = r.get("a"), r.get("b")
        if a is not None or b is not None:
            x = x[int((a or 0) * SR): int(b * SR) if b else None]
        x = B.trim_silence(x)
        if r.get("glide"):
            x = glide(x, *r["glide"])
        x = B.change_speed(x, r.get("speed", 1.0))
    if r.get("hp"):
        x = highpass(x, r["hp"])
    if r.get("lp"):
        x = B.lowpass(x, r["lp"], SR)
    x = x[: int(min(r.get("max", 2.0), 2.0) * SR)]
    return x


def build_sfx(r: dict) -> np.ndarray:
    x = render(r)
    x = B.trim_silence(x)
    tail = min(0.12, 0.25 * len(x) / SR)
    x = B.fade(x, 0.003, tail, SR)
    if len(x) < int(0.06 * SR):
        x = np.concatenate([x, np.zeros((int(0.06 * SR) - len(x), 1), "float32")])
    g = B.loudness_gain(x, SR, B.SFX_LUFS + r.get("gain_db", 0.0))
    return B.limit(x * g, B.PEAK_SFX)


def build_music(r: dict) -> np.ndarray:
    sr = B.SR_MUS
    x = B.read(r["src"], sr)
    if x.shape[1] == 1:
        x = np.repeat(x, 2, axis=1)
    x = B.trim_silence(x, -55.0, 0.0, sr)
    if r.get("max"):
        x = x[: int(r["max"] * sr)]
    if r.get("lp"):
        x = B.lowpass(x, r["lp"], sr)
    xf = int(r.get("xf", 1.0) * sr)
    out = x
    for _ in range(r.get("reps", 1) - 1):
        out = B._xfade(out, x, xf)
    head, tail = out[:xf], out[-xf:]
    t = np.linspace(0, 1, xf, dtype="float32")[:, None]
    body = out[:-xf].copy()
    body[:xf] = head * np.sin(t * np.pi / 2) + tail * np.cos(t * np.pi / 2)
    g = B.loudness_gain(body, sr, r.get("lufs", B.MUS_LUFS))
    return B.limit(body * g, B.PEAK_MUS)


HZ = "oga_cand/relaxing/Relaxing Instrumentals/"

# ---- musica -------------------------------------------------------------------------------------------------------
MUSIC: dict[str, dict[str, dict]] = {
    "mapa_run": {
        "cozy_guitar": dict(src="oga_cand/cozy/cozy3.ogg", xf=2.0),
        "explor_guitar": dict(src="oga_cand/exploration/sound.wav", reps=4, xf=1.0),
        "lofi_boredom": dict(src=HZ + "03 HoliznaCC0 - Boredom.ogg", max=170, xf=4.0),
    },
}

# ---- sfx ----------------------------------------------------------------------------------------------------------
MEOW = dict(hp=180, lp=9000)
SFX: dict[str, dict[str, dict]] = {
    "meow_1": {
        "bsb_pequeno1": dict(src=BSB + "0494.wav", **MEOW),
        "bsb_mewing_a": dict(src=BSB + "0098.wav", a=0.05, b=0.75, **MEOW),
        "lab_sintetico": dict(src="oga_cand/labchirp/meowing_cat.mp3", hp=150, lp=9000, gain_db=-1),
    },
    "meow_2": {
        "bsb_mewing_b": dict(src=BSB + "0098.wav", a=1.0, b=1.8, **MEOW),
        "bsb_pequeno3": dict(src=BSB + "1473.wav", **MEOW),
        "boca_1": dict(src=BSB + "0926.wav", a=2.1, b=3.2, **MEOW),
    },
    "meow_3": {
        "bsb_cat1_longo": dict(src=BSB + "1889.wav", a=1.2, b=2.8, max=1.6, **MEOW),
        "bsb_mewing_c": dict(src=BSB + "0098.wav", a=2.1, b=2.75, speed=0.95, **MEOW),
        "boca_4": dict(src=BSB + "0926.wav", a=5.5, b=6.6, **MEOW),
    },
    "meow_4": {
        "bsb_mewing_d": dict(src=BSB + "0098.wav", a=3.1, b=3.8, speed=1.08, **MEOW),
        "boca_7": dict(src=BSB + "0926.wav", a=7.5, b=8.5, speed=1.05, **MEOW),
        "baby_meow": dict(src="oga_baby/Meow.ogg", **MEOW),
    },
    "kitten_mew": {
        "bsb_pequeno1_agudo": dict(src=BSB + "0494.wav", speed=1.45, **MEOW),
        "baby_agudo": dict(src="oga_baby/Meow.ogg", speed=1.2, **MEOW),
        "lab_agudo": dict(src="oga_cand/labchirp/meowing_cat.mp3", speed=1.6, hp=200, lp=10000),
    },
    "purr": {
        "bsb_ronronar": dict(src=BSB + "0436.wav", a=3.0, b=4.9, hp=60, lp=3500, gain_db=-3),
        "bsb_ronronar_suave": dict(src=BSB + "0436.wav", a=5.5, b=7.4, hp=60, lp=1800, gain_db=-3),
        "sintetizado": dict(synth="purr", gain_db=-4),
    },
    "pet": {
        "sint_blip": dict(synth="blip", gain_db=-3),
        "pop_fofo": dict(src=OP + "pop5.wav", lp=5000, gain_db=-2),
        "ronronar_curto": dict(src=BSB + "0436.wav", a=2.0, b=2.9, hp=60, lp=2500, gain_db=-3),
    },
    "pet_2": {
        "sint_blip2": dict(synth="blip2", gain_db=-3),
        "pop_fofo_2": dict(src=OP + "pop3.wav", lp=5000, speed=0.9, gain_db=-2),
        "ronronar_curto_2": dict(src=BSB + "0436.wav", a=6.0, b=6.9, hp=60, lp=2500, gain_db=-3),
    },
    "cat_death": {
        "sint_poof": dict(synth="poof", gain_db=-1),
        "poof_miadinho": dict(mix=[(dict(synth="poof", seed=3), 0.0),
                                   (dict(src=BSB + "0494.wav", glide=(1.25, 0.8), hp=200, lp=7000, max=0.5, gain_db=-4), 0.12)]),
        "pop_queda": dict(mix=[(dict(src=OP + "pop5.wav", lp=6000), 0.0),
                               (dict(synth="falling", gain_db=-6), 0.06)]),
    },
    "cat_death_2": {
        "sint_poof_2": dict(synth="poof2", seed=2, gain_db=-1),
        "poof_miadinho_2": dict(mix=[(dict(synth="poof2", seed=5), 0.0),
                                     (dict(src=BSB + "1473.wav", glide=(1.2, 0.75), hp=200, lp=7000, max=0.55, gain_db=-4), 0.1)]),
        "pop_queda_2": dict(mix=[(dict(src=OP + "pop3.wav", lp=6000), 0.0),
                                 (dict(synth="falling", gain_db=-6), 0.05)]),
    },
}


def main() -> int:
    only = set(sys.argv[1:])
    for cue, cands in MUSIC.items():
        if only and cue not in only:
            continue
        for c, r in cands.items():
            B.write(OUT / cue / f"{c}.ogg", build_music(r), B.SR_MUS)
            print("music", cue, c)
    for cue, cands in SFX.items():
        if only and cue not in only:
            continue
        for c, r in cands.items():
            B.write(OUT / cue / f"{c}.ogg", build_sfx(r), SR)
            print("sfx", cue, c)
    return 0


if __name__ == "__main__":
    sys.exit(main())
