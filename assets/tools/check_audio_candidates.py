"""T10.6 - valida os candidatos de audio e gera: assets/audio/_candidatos/CREDITS.md + candidatos.json,
reports/audio/pre_escuta_candidatos.html e reports/audio/PRE_ESCUTA_CANDIDATOS.md.

Requer numpy, soundfile, pyloudnorm (dev). Uso: python assets/tools/check_audio_candidates.py
O que o apply_audio_candidates.py usa para copiar/creditar esta em candidatos.json (gerado aqui).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pyloudnorm as pyln
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_audio_candidates as C  # noqa: E402

ROOT = C.B.ROOT
AUDIO = C.B.AUDIO
CAND = AUDIO / "_candidatos"
REP = ROOT / "reports" / "audio"
CC0 = "CC0 1.0"

# prefixo de caminho em _src -> (fonte, url, autor, licenca)
SOURCES: dict[str, tuple[str, str, str, str]] = {
    "bsb/0098": ("BigSoundBank - Small mewing of a cat (s0098)", "https://bigsoundbank.com/small-mewing-of-a-cat-s0098.html", "Joseph Sardin", "CC0 (pagina: 'CC0 (public domain)')"),
    "bsb/0494": ("BigSoundBank - Little Meow of a Cat #1 (s0494)", "https://bigsoundbank.com/little-meow-of-a-cat-s0494.html", "Joseph Sardin", "CC0 (pagina: 'CC0 (public domain)')"),
    "bsb/0926": ("BigSoundBank - Cat Meow Made with Mouth (s0926)", "https://bigsoundbank.com/cat-meow-made-with-mouth-s0926.html", "Joseph Sardin", "CC0 (pagina: 'CC0 (public domain)')"),
    "bsb/1473": ("BigSoundBank - Little meow of a cat #3 (s1473)", "https://bigsoundbank.com/little-meow-of-a-cat-3-s1473.html", "Joseph Sardin", "CC0 (pagina: 'CC0 (public domain)')"),
    "bsb/1889": ("BigSoundBank - Meow cat #1 (s1889)", "https://bigsoundbank.com/meow-cat-1-s1889.html", "Joseph Sardin", "CC0 (pagina: 'CC0 (public domain)')"),
    "bsb/0436": ("BigSoundBank - Cat Purr (s0436)", "https://bigsoundbank.com/cat-purr-s0436.html", "Joseph Sardin", "CC0 (pagina: 'CC0 (public domain)')"),
    "oga_cand/labchirp": ("Meowing Cat Made in LabChirp (OpenGameArt)", "https://opengameart.org/content/meowing-cat-made-in-labchirp", "Traceletz", CC0),
    "oga_baby": ("Baby Animals - Sounds Pack (OpenGameArt) `Meow.ogg`", "https://opengameart.org/content/baby-animals-sounds-pack", "Technopeasant (compilacao; origem de cada som e freesound CC0 nao identificada por arquivo)", "CC0 1.0 (declarado na pagina; origem individual nao verificada)"),
    "oga_pop": ("Pop sounds (OpenGameArt)", "https://opengameart.org/content/pop-sounds-0", "EZduzziteh", CC0),
    "oga_cand/cozy": ("Cozy Puzzle In-Game 3 (OpenGameArt)", "https://opengameart.org/content/cozy-puzzle-in-game-3", "MintoDog", CC0),
    "oga_cand/exploration": ("Exploration (OpenGameArt)", "https://opengameart.org/content/exploration-0", "johnclark", CC0),
    "oga_cand/relaxing": ("Relaxing Instrumentals (Collection) (OpenGameArt) 'Boredom'", "https://opengameart.org/content/relaxing-instrumentals-collection", "Holizna", CC0),
}
SYNTH = ("Sintetizado por script (assets/tools/build_audio_candidates.py), sem amostras externas", "-", "projeto Chaoscats", "CC0 / sem terceiros")

# nota de carater + recomendacao (SEM escuta humana; baseada em descricao da fonte, duracao, centroide espectral e processamento)
NOTES: dict[str, dict[str, tuple[str, str]]] = {
    "mapa_run": {
        "cozy_guitar": ("violao acustico + baixo, 'cozy/relax' pelas tags da fonte; loop de 122 s, ritmo ~108 bpm", "RECOMENDADO (1a escolha)"),
        "explor_guitar": ("violao acustico em E maior, 'chill/aventura'; trecho original so tem 21 s, repetido 4x (81 s): repeticao audivel", "reserva"),
        "lofi_boredom": ("lo-fi instrumental da colecao Holizna ('Boredom'), 166 s, faixa nao feita para loop (costura de 4 s por crossfade); estilo exato nao confirmado", "alternativa se quiser tom lo-fi; ouvir antes"),
    },
    "meow_1": {
        "bsb_pequeno1": ("miadinho curto (0,46 s), gravacao limpa (piso de ruido ~-33 dB), timbre medio", "RECOMENDADO"),
        "bsb_mewing_a": ("1o de 4 miados da mesma gravacao silenciosa (piso de ruido muito baixo), 0,6 s", "boa alternativa"),
        "lab_sintetico": ("miado 'cartoon' de sintetizador (LabChirp), 1,1 s: limpo mas eletronico, mais 'jogo retro' que gato real", "reserva (tom diferente)"),
    },
    "meow_2": {
        "bsb_mewing_b": ("2o miado da gravacao s0098, 0,7 s, claro", "RECOMENDADO"),
        "bsb_pequeno3": ("miadinho #3 do Sardin, 0,9 s, mais grave/suave", "boa alternativa"),
        "boca_1": ("'miado feito com a boca' (imitacao humana), 1,1 s: tende a soar cartoon/divertido, nao gato real", "reserva (gosto)"),
    },
    "meow_3": {
        "bsb_cat1_longo": ("miado mais longo (1,5 s) do 'Meow cat #1', gravacao muito limpa (piso ~-81 dB)", "RECOMENDADO"),
        "bsb_mewing_c": ("3o miado de s0098, 0,5 s, levemente mais grave", "alternativa curta"),
        "boca_4": ("imitacao com a boca, 1,1 s", "reserva (gosto)"),
    },
    "meow_4": {
        "bsb_mewing_d": ("4o miado de s0098, 0,5 s, +8% de tom (mais fofo)", "RECOMENDADO"),
        "boca_7": ("imitacao com a boca, 0,95 s", "reserva (gosto)"),
        "baby_meow": ("miado de filhote do Baby Animals Pack (0,9 s), agudo; proveniencia individual nao verificada", "alternativa; usar tambem como pack B"),
    },
    "kitten_mew": {
        "bsb_pequeno1_agudo": ("meow #1 do Sardin a +45% de tom, 0,32 s: agudo e delicado, pode soar 'chipmunk' se exagerado", "RECOMENDADO (testar)"),
        "baby_agudo": ("miado de filhote do pack Baby Animals a +20% de tom, 0,77 s", "alternativa mais natural"),
        "lab_agudo": ("miado sintetico +60% de tom, 0,67 s, bem 'cartoon', baixo volume original", "reserva"),
    },
    "purr": {
        "bsb_ronronar": ("ronronar real (Sardin, 'Cat Purr'), trecho de 1,9 s, passa-baixa 3,5 kHz", "boa"),
        "bsb_ronronar_suave": ("mesma gravacao, outro trecho, passa-baixa 1,8 kHz: mais abafado e suave", "RECOMENDADO"),
        "sintetizado": ("ruido passa-faixa modulado a 25 Hz + 110 Hz: limpo, sem ruido de fundo, mas artificial", "fallback se o real incomodar"),
    },
    "pet": {
        "sint_blip": ("dois toques tonais macios subindo (660->880 Hz), 0,35 s; sinteticos, 'carinho' de jogo", "RECOMENDADO"),
        "pop_fofo": ("'pop' vocal de bolha do pack EZduzziteh, 0,4 s, passa-baixa", "alternativa"),
        "ronronar_curto": ("0,9 s de ronronar real, abafado", "alternativa mais realista"),
    },
    "pet_2": {
        "sint_blip2": ("bip redondo com vibrato leve, 0,3 s; sintetico", "alternativa"),
        "pop_fofo_2": ("pop curto (0,14 s) a -10% de tom", "reserva"),
        "ronronar_curto_2": ("outro trecho de 0,9 s do ronronar real", "RECOMENDADO (como variacao de pet)"),
    },
    "cat_death": {
        "sint_poof": ("'puff' de ruido filtrado + bloop tonal descendente, 0,42 s; 100% sintetizado, sem miado", "boa, a mais neutra"),
        "poof_miadinho": ("puff sintetizado + miadinho do Sardin com pitch caindo (derrota fofa), 0,55 s", "RECOMENDADO"),
        "pop_queda": ("pop vocal (EZduzziteh) + 3 notas macias descendo, 0,7 s: 'queda' suave", "alternativa"),
    },
    "cat_death_2": {
        "sint_poof_2": ("variacao do puff sintetizado, mais agudo, 0,41 s", "boa"),
        "poof_miadinho_2": ("puff + miadinho #3 do Sardin com pitch caindo, 0,65 s", "RECOMENDADO"),
        "pop_queda_2": ("pop curto + notas descendo, 0,7 s", "alternativa"),
    },
}


def recipe_srcs(r: dict) -> list[str]:
    if "mix" in r:
        return [s for sub, _ in r["mix"] for s in recipe_srcs(sub)]
    if "synth" in r:
        return ["SYNTH"]
    return [r["src"]]


def src_key(path: str) -> str:
    if path == "SYNTH":
        return "SYNTH"
    for k in SOURCES:
        if path.startswith(k):
            return k
    raise KeyError(path)


def describe_edit(r: dict, music: bool) -> str:
    if music:
        s = ["estereo 44,1 kHz", "aparado", "-20 LUFS"]
        if r.get("max"):
            s.append(f"corte {r['max']} s")
        if r.get("reps", 1) > 1:
            s.append(f"{r['reps']} repeticoes com crossfade")
        s.append(f"costura de loop (crossfade {r.get('xf', 1.0)} s)")
        return ", ".join(s)
    s = ["mono 44,1 kHz", "aparado", f"{C.B.SFX_LUFS + r.get('gain_db', 0):.0f} LUFS"]
    if "mix" in r:
        s.append("mistura de " + " + ".join(
            ("sintetizado" if "synth" in sub else Path(sub["src"]).name) for sub, _ in r["mix"]))
    elif "synth" in r:
        s.append(f"sintese '{r['synth']}'")
    else:
        if r.get("a") is not None:
            s.append(f"trecho {r['a']}-{r.get('b')} s")
        if r.get("speed"):
            s.append(f"velocidade/tom x{r['speed']}")
        if r.get("glide"):
            s.append(f"tom deslizante {r['glide'][0]}->{r['glide'][1]}")
    for k, nm in (("hp", "passa-alta"), ("lp", "passa-baixa")):
        if r.get(k):
            s.append(f"{nm} {r[k]} Hz")
    return ", ".join(s)


def measure(p: Path) -> dict:
    x, sr = sf.read(str(p), always_2d=True)
    pad = x if len(x) >= int(0.8 * sr) else np.concatenate([x, np.zeros((int(0.8 * sr) - len(x), x.shape[1]))])
    return dict(dur=len(x) / sr, ch=x.shape[1], peak=float(np.abs(x).max()), lufs=float(pyln.Meter(sr).integrated_loudness(pad)))


def final_rel(cue: str) -> str:
    return f"music/{cue}.ogg" if cue in C.MUSIC else f"sfx/{cue}.ogg"


def main() -> int:
    prod_credit = {}
    cp = AUDIO / "CREDITS.md"
    for line in cp.read_text(encoding="utf-8").splitlines():
        c = [s.strip() for s in line.strip().strip("|").split("|")]
        if len(c) >= 5 and c[0].startswith(("sfx/", "music/")):
            prod_credit[c[0]] = c[1]
    meta: dict[str, dict] = {}
    errs: list[str] = []
    rows = []
    for cue, cands in {**C.MUSIC, **C.SFX}.items():
        music = cue in C.MUSIC
        for name, r in cands.items():
            p = CAND / cue / f"{name}.ogg"
            if not p.exists():
                errs.append(f"FALTA {p}")
                continue
            m = measure(p)
            if m["peak"] >= 0.99:
                errs.append(f"{cue}/{name}: clipping")
            if m["ch"] != (2 if music else 1):
                errs.append(f"{cue}/{name}: canais {m['ch']}")
            if music and not 60 <= m["dur"] <= 180:
                errs.append(f"{cue}/{name}: duracao {m['dur']:.1f}s fora de 60-180 (musica)")
            if not music and not 0.05 <= m["dur"] <= 2.0:
                errs.append(f"{cue}/{name}: duracao {m['dur']:.2f}s")
            keys = list(dict.fromkeys(src_key(s) for s in recipe_srcs(r)))
            srcs = [SYNTH if k == "SYNTH" else SOURCES[k] for k in keys]
            note, rec = NOTES[cue][name]
            meta.setdefault(cue, {})[name] = dict(
                final=final_rel(cue), file=f"_candidatos/{cue}/{name}.ogg",
                fonte="; ".join(s[0] for s in srcs), url="; ".join(s[1] for s in srcs if s[1] != "-") or "-",
                autor="; ".join(dict.fromkeys(s[2] for s in srcs)), licenca="; ".join(dict.fromkeys(s[3] for s in srcs)),
                alteracoes=describe_edit(r, music), sintetizado=("SYNTH" in keys), nota=note, recomendacao=rec, **{k: round(v, 3) for k, v in m.items() if k != "ch"})
            rows.append((cue, name))
    (CAND / "candidatos.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")

    cr = ["# Creditos dos candidatos de audio (T10.6)", "",
          "Candidatos **ainda nao** em producao (`assets/audio/sfx|music` intactos). Todos CC0 / dominio publico / sintetizados por script; nenhuma atribuicao obrigatoria.",
          "Brutos em `assets/audio/_src/` (bsb, oga_baby, oga_pop, oga_cand). Licencas lidas nas paginas das fontes em 2026-10-29. Reconstrucao: `assets/tools/build_audio_candidates.py`.",
          "Para trocar: `python assets/tools/apply_audio_candidates.py <cue>=<candidato> ...` (ver `reports/T10.6-audio-candidatos.md`).", "",
          "| candidato | fonte | URL | autor | licenca | alteracoes |", "|---|---|---|---|---|---|"]
    for cue, name in rows:
        d = meta[cue][name]
        cr.append(f"| {cue}/{name}.ogg{' (SINTETIZADO)' if d['sintetizado'] else ''} | {d['fonte']} | {d['url']} | {d['autor']} | {d['licenca']} | {d['alteracoes']} |")
    (CAND / "CREDITS.md").write_text("\n".join(cr) + "\n", encoding="utf-8")

    REP.mkdir(parents=True, exist_ok=True)
    md = ["# Pre-escuta dos candidatos de audio (T10.6)", "",
          "Abra `reports/audio/pre_escuta_candidatos.html` no navegador: por cue, o arquivo **atual de producao** e depois os candidatos. "
          "**Ninguem ouviu** nada (so analise numerica e descricao das fontes); as notas descrevem a intencao e a recomendacao e podem estar erradas.", "",
          "Comando para trocar: `python assets/tools/apply_audio_candidates.py meow_1=bsb_pequeno1 ...` ou `--recomendado` (ver T10.6).", ""]
    html = ["<!doctype html><meta charset=utf-8><title>Pre-escuta de candidatos Chaoscats</title>",
            "<style>body{font-family:sans-serif;max-width:780px;margin:2em auto;background:#1b1b2a;color:#eee}h2{margin-top:1.6em;border-bottom:1px solid #445}"
            "div{margin:.6em 0}code{color:#9cf}audio{width:100%}small{color:#aaa}.atual{border-left:4px solid #e90;padding-left:8px}"
            ".rec{color:#9f9}</style>", "<h1>Pre-escuta: candidatos de audio</h1>",
            "<p>Laranja = arquivo atual de producao. Nenhum foi ouvido por quem gerou.</p>"]
    for cue in {**C.MUSIC, **C.SFX}:
        fin = final_rel(cue)
        pm = measure(AUDIO / fin)
        md += [f"## {cue}", "", f"Atual: `{fin}` ({pm['dur']:.2f} s, {pm['lufs']:.1f} LUFS). Fonte atual: {prod_credit.get(fin, '?')}.", "",
               "| candidato | dur (s) | LUFS | fonte / autor | nota | recomendacao |", "|---|---|---|---|---|---|"]
        html += [f"<h2>{cue}</h2>", f"<div class=atual><code>atual: {fin}</code> <small>{pm['dur']:.2f}s, {pm['lufs']:.1f} LUFS. {prod_credit.get(fin, '')}</small>"
                 f"<br><audio controls preload=none src=\"../../assets/audio/{fin}\"></audio></div>"]
        for name, d in meta[cue].items():
            tag = " [SINTETIZADO]" if d["sintetizado"] else ""
            md.append(f"| `{name}`{tag} | {d['dur']:.2f} | {d['lufs']:.1f} | {d['fonte']} ({d['autor']}) | {d['nota']} | {d['recomendacao']} |")
            html.append(f"<div><code>{name}</code>{tag} <small>{d['dur']:.2f}s, {d['lufs']:.1f} LUFS. {d['nota']}.</small> "
                        f"<span class=rec>{d['recomendacao']}</span><br><audio controls preload=none src=\"../../assets/audio/{d['file']}\"></audio></div>")
        md.append("")
    (REP / "PRE_ESCUTA_CANDIDATOS.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (REP / "pre_escuta_candidatos.html").write_text("\n".join(html) + "\n", encoding="utf-8")
    print("candidatos:", len(rows), "erros:", len(errs))
    for e in errs:
        print(" ", e)
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
