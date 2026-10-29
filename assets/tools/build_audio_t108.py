"""T10.8 - regrava os sfx `adopt` e `kitten_born` combinando com os novos sons de gato (BigSoundBank CC0 + Kenney CC0).

Requer numpy/scipy/soundfile/pyloudnorm. Uso: python assets/tools/build_audio_t108.py
Escreve assets/audio/sfx/{adopt,kitten_born}.ogg, registra em audio_overrides.json e troca as linhas de assets/audio/CREDITS.md.
Depois rode `python assets/tools/apply_audio_candidates.py --recomendado` para regenerar a secao de LICENSES.md (idempotente).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_audio as B  # noqa: E402
import build_audio_candidates as C  # noqa: E402

BSB, K = "bsb/", B.K
MEOW = dict(hp=180, lp=9000)
RECIPES = {
    # miado de filhote (s1473) + ronronar suave (s0436) logo depois, sobrepostos
    "adopt": dict(mix=[(dict(src=BSB + "1473.wav", speed=0.95, max=1.0, **MEOW), 0.0),
                       (dict(src=BSB + "0436.wav", a=6.0, b=7.0, hp=60, lp=1800, gain_db=-5), 0.35)]),
    # miado agudo (s0494 x1.7) + brilho de vidro curto (Kenney)
    "kitten_born": dict(mix=[(dict(src=BSB + "0494.wav", speed=1.7, **MEOW), 0.0),
                             (dict(src=K + "glass_003.ogg", lp=9000, max=0.5, gain_db=-8), 0.14)]),
}
META = {
    "adopt": dict(fonte="BigSoundBank - Little meow of a cat #3 (s1473); BigSoundBank - Cat Purr (s0436)",
                  autor="Joseph Sardin", url="https://bigsoundbank.com/little-meow-of-a-cat-3-s1473.html; https://bigsoundbank.com/cat-purr-s0436.html",
                  licenca="CC0 (pagina: 'CC0 (public domain)')", sintetizado=False,
                  alt="mono 44,1 kHz, aparado, -16 LUFS; miado s1473 (x0,95, passa-alta 180/passa-baixa 9000 Hz) + ronronar s0436 trecho 6.0-7.0 s (passa-faixa 60-1800 Hz) a 0,35 s"),
    "kitten_born": dict(fonte="BigSoundBank - Little Meow of a Cat #1 (s0494); Kenney - Interface Sounds (glass_003)",
                        autor="Joseph Sardin; Kenney", url="https://bigsoundbank.com/little-meow-of-a-cat-s0494.html; https://opengameart.org/content/interface-sounds",
                        licenca="CC0 (pagina: 'CC0 (public domain)'); CC0 1.0", sintetizado=False,
                        alt="mono 44,1 kHz, aparado, -16 LUFS; miado s0494 x1,7 (passa-alta 180/passa-baixa 9000 Hz) + brilho glass_003 a 0,14 s"),
}


def main() -> int:
    root = B.ROOT
    ovr_p = root / "assets" / "tools" / "audio_overrides.json"
    ovr = json.loads(ovr_p.read_text(encoding="utf-8"))
    cp = root / "assets" / "audio" / "CREDITS.md"
    credits = cp.read_text(encoding="utf-8").splitlines()
    for cue, r in RECIPES.items():
        B.write(root / "assets" / "audio" / "sfx" / f"{cue}.ogg", C.build_sfx(r), B.SR_SFX)
        m = META[cue]
        row = (f"| sfx/{cue}.ogg | {m['fonte']} ({m['url']}) | {m['autor']} | {m['licenca']} | {m['alt']} (T10.8) |")
        credits = [row if ln.startswith(f"| sfx/{cue}.ogg |") else ln for ln in credits]
        ovr[cue] = dict(candidato="t10_8", fonte=m["fonte"], autor=m["autor"], url=m["url"], licenca=m["licenca"], sintetizado=m["sintetizado"])
        print("ok", cue)
    cp.write_text("\n".join(credits) + "\n", encoding="utf-8")
    ovr_p.write_text(json.dumps(ovr, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
