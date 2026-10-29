"""T10.6 - promove candidatos de audio para producao.

Uso:
  python assets/tools/apply_audio_candidates.py meow_1=bsb_pequeno1 mapa_run=cozy_guitar ...
  python assets/tools/apply_audio_candidates.py --recomendado        # aplica todos os marcados RECOMENDADO
  python assets/tools/apply_audio_candidates.py --listar
  python assets/tools/apply_audio_candidates.py --dry-run ...

Copia assets/audio/_candidatos/<cue>/<cand>.ogg para o caminho final (sfx/<cue>.ogg ou music/<cue>.ogg), troca a linha do cue em
assets/audio/CREDITS.md, atualiza a secao "Audio (T10.6)" de assets/LICENSES.md e registra o cue em assets/tools/audio_overrides.json
(build_audio.py passa a ignorar esse cue para nao regravar o antigo). Requer so a biblioteca padrao. Rode antes check_audio_candidates.py
se tiver mexido nos candidatos. Depois rode `python assets/tools/check_audio.py` e `python -m pytest -q`.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
AUDIO = ROOT / "assets" / "audio"
CAND = AUDIO / "_candidatos"
OVR = ROOT / "assets" / "tools" / "audio_overrides.json"
LIC = ROOT / "assets" / "LICENSES.md"
HEAD = "## Audio (T10.6, substituicoes)"


def main(argv: list[str]) -> int:
    meta = json.loads((CAND / "candidatos.json").read_text(encoding="utf-8"))
    dry = "--dry-run" in argv
    args = [a for a in argv if not a.startswith("--")]
    if "--listar" in argv:
        for cue, cs in meta.items():
            print(cue, ":", ", ".join(f"{n}{' *' if 'RECOMENDADO' in d['recomendacao'] else ''}" for n, d in cs.items()))
        return 0
    pairs: list[tuple[str, str]] = []
    if "--recomendado" in argv:
        pairs += [(cue, n) for cue, cs in meta.items() for n, d in cs.items() if d["recomendacao"].startswith("RECOMENDADO")]
    for a in args:
        if "=" not in a:
            print("formato invalido (use cue=candidato):", a)
            return 2
        pairs.append(tuple(a.split("=", 1)))  # type: ignore[arg-type]
    if not pairs:
        print(__doc__)
        return 2
    chosen: dict[str, str] = dict(pairs)  # ultimo vence
    for cue, cand in chosen.items():
        if cue not in meta or cand not in meta[cue]:
            print("candidato inexistente:", cue, cand)
            return 2
    ovr = json.loads(OVR.read_text(encoding="utf-8")) if OVR.exists() else {}
    credits = (AUDIO / "CREDITS.md").read_text(encoding="utf-8").splitlines()
    for cue, cand in chosen.items():
        d = meta[cue][cand]
        src, dst = CAND / cue / f"{cand}.ogg", AUDIO / d["final"]
        print(f"{cue}: {cand} -> {d['final']}" + (" (dry-run)" if dry else ""))
        if dry:
            continue
        shutil.copyfile(src, dst)
        row = (f"| {d['final']} | {d['fonte']} ({d['url']}) | {d['autor']} | {d['licenca']} | "
               f"{d['alteracoes']}{'; contem trecho sintetizado por script' if d['sintetizado'] else ''} (candidato {cand}, T10.6) |")
        credits = [row if ln.startswith(f"| {d['final']} |") else ln for ln in credits]
        ovr[cue] = dict(candidato=cand, fonte=d["fonte"], autor=d["autor"], url=d["url"], licenca=d["licenca"], sintetizado=d["sintetizado"])
    if dry:
        return 0
    (AUDIO / "CREDITS.md").write_text("\n".join(credits) + "\n", encoding="utf-8")
    OVR.write_text(json.dumps(ovr, ensure_ascii=False, indent=1), encoding="utf-8")
    # LICENSES.md: reescreve a secao T10.6 com tudo que ja foi aplicado
    autores = sorted({a.strip() for v in ovr.values() for a in v["autor"].split(";")})
    fontes = sorted({f.strip() for v in ovr.values() for f in v["fonte"].split(";")})
    sec = [HEAD,
           f"- Substituidos por candidatos ({', '.join(sorted(ovr))}); todos CC0 / dominio publico ou sintetizados por script (sem amostras externas). Nenhuma atribuicao obrigatoria.",
           f"- Fontes: {'; '.join(fontes)}. Autores: {'; '.join(autores)}.",
           "- Detalhe por arquivo em `assets/audio/CREDITS.md`; licencas lidas nas paginas das fontes em 2026-10-29. Candidatos nao usados continuam em `assets/audio/_candidatos/` (nao entram no build).", ""]
    txt = LIC.read_text(encoding="utf-8")
    if HEAD in txt:
        i = txt.index(HEAD)
        j = txt.find("\n## ", i + 1)
        txt = txt[:i] + "\n".join(sec) + ("\n" + txt[j + 1:] if j != -1 else "")
    else:
        txt = txt.rstrip("\n") + "\n\n" + "\n".join(sec)
    LIC.write_text(txt, encoding="utf-8")
    print("CREDITS.md, LICENSES.md e audio_overrides.json atualizados. Rode check_audio.py e pytest.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
