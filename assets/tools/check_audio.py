"""Valida os audios finais contra data/audio.json e gera reports/audio/PRE_ESCUTA.md + pre_escuta.html.

Requer numpy, soundfile, pyloudnorm (dev). Uso: python assets/tools/check_audio.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pyloudnorm as pyln
import soundfile as sf

ROOT = Path(__file__).resolve().parents[2]
AUDIO = ROOT / "assets" / "audio"
REP = ROOT / "reports" / "audio"

# nota de carater por arquivo (curada na T10.2; sem escuta humana, descreve a intencao/processamento)
NOTES_PATH = ROOT / "assets" / "tools" / "audio_notes.json"


def measure(p: Path) -> dict:
    x, sr = sf.read(str(p), always_2d=True)
    n = len(x)
    pad = x
    if n < int(0.8 * sr):
        pad = np.concatenate([x, np.zeros((int(0.8 * sr) - n, x.shape[1]))])
    lufs = pyln.Meter(sr).integrated_loudness(pad)
    return dict(dur=n / sr, ch=x.shape[1], sr=sr, peak=float(np.abs(x).max()), lufs=float(lufs))


def main() -> int:
    m = json.loads((ROOT / "data" / "audio.json").read_text(encoding="utf-8"))
    notes = json.loads(NOTES_PATH.read_text(encoding="utf-8")) if NOTES_PATH.exists() else {}
    credits = {}
    cp = AUDIO / "CREDITS.md"
    if cp.exists():
        for line in cp.read_text(encoding="utf-8").splitlines():
            c = [s.strip() for s in line.strip().strip("|").split("|")]
            if len(c) >= 5 and c[0].startswith(("sfx/", "music/")):
                credits[c[0]] = c[1]
    rows, errs = [], []

    def check(rel: str, kind: str, cue: str) -> None:
        p = AUDIO / rel
        if not p.exists():
            errs.append(f"FALTA {rel}")
            return
        r = measure(p)
        lo, hi = (0.05, 2.0) if kind == "sfx" else (0.0, 180.0)
        if kind == "music" and not (cue in ("vitoria", "derrota") or r["dur"] >= 60):
            errs.append(f"{rel}: duracao {r['dur']:.1f}s < 60")
        if not (lo <= r["dur"] <= hi):
            errs.append(f"{rel}: duracao {r['dur']:.2f}s fora de [{lo},{hi}]")
        if r["peak"] >= 0.99:
            errs.append(f"{rel}: pico {r['peak']:.3f} (clipping)")
        if r["ch"] != (1 if kind == "sfx" else 2):
            errs.append(f"{rel}: canais {r['ch']}")
        rows.append((cue, rel, r))

    for cue, c in m["sfx"].items():
        for f in c["files"]:
            check(f, "sfx", cue)
    for cue, c in m["music"].items():
        check(c["file"], "music", cue)

    # abre com pygame (driver dummy) se disponivel
    try:
        import os
        os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
        import pygame
        pygame.mixer.init()
        for _, rel, _ in rows:
            pygame.mixer.Sound(str(AUDIO / rel)) if rel.startswith("sfx/") else pygame.mixer.music.load(str(AUDIO / rel))
        print("pygame abriu", len(rows), "arquivos")
    except Exception as e:  # noqa: BLE001
        print("pygame indisponivel/erro:", e)

    REP.mkdir(parents=True, exist_ok=True)
    md = ["# Pre-escuta de audio (T10.2)", "",
          "Abra `reports/audio/pre_escuta.html` no navegador para ouvir tudo. Notas descrevem a intencao e o processamento; "
          "**ninguem ouviu** os arquivos ainda (gerados por script), entao o julgamento de gosto e seu.", "",
          "| cue | arquivo | dur (s) | LUFS | pico dB | fonte | nota |", "|---|---|---|---|---|---|---|"]
    html = ["<!doctype html><meta charset=utf-8><title>Pre-escuta Chaoscats</title>",
            "<style>body{font-family:sans-serif;max-width:760px;margin:2em auto;background:#1b1b2a;color:#eee}"
            "h2{margin-top:1.5em}div{margin:.6em 0}code{color:#9cf}audio{width:100%}small{color:#aaa}</style>",
            "<h1>Pre-escuta de audio</h1>"]
    last = None
    for cue, rel, r in rows:
        pk = 20 * np.log10(r["peak"])
        src = credits.get(rel, "")
        note = notes.get(rel, "")
        md.append(f"| {cue} | `{rel}` | {r['dur']:.2f} | {r['lufs']:.1f} | {pk:.1f} | {src} | {note} |")
        if cue != last:
            html.append(f"<h2>{cue}</h2>")
            last = cue
        html.append(f"<div><code>{rel}</code> <small>{r['dur']:.2f}s, {r['lufs']:.1f} LUFS. {note}</small>"
                    f"<br><audio controls preload=none src=\"../../assets/audio/{rel}\"></audio></div>")
    (REP / "PRE_ESCUTA.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (REP / "pre_escuta.html").write_text("\n".join(html) + "\n", encoding="utf-8")
    print("arquivos:", len(rows), "erros:", len(errs))
    for e in errs:
        print(" ", e)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
