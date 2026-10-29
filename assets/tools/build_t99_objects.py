"""T9.9: objects.png/json/ambient/pen.json com TAPETES planos no lugar das camas-tigela (T9.8 para o resto).
T99_BEDS=old mantem as camas da T9.8 (para comparar). Uso: python assets/tools/build_t99_objects.py"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
import build_t98_lib as B  # noqa: E402

MAP = {"cama_teal_L": "tapete_teal", "cama_cesto_L": "tapete_cesto", "cama_cinza_L": "tapete_cinza",
       "cama_casal_L": "tapete_casal", "viveiro_L": "tapete_viveiro"}
NEW = os.environ.get("T99_BEDS", "old") != "old"
# T9.11: T99_BED_SHADOW=0 (padrao) remove a sombra de contato so das camas; =1 devolve a sombra da T9.8/T9.9
BED_SHADOW = os.environ.get("T99_BED_SHADOW", "0") != "0"
_orig = B.clean_sprite


def _clean(name, pal=None):
    if NEW and name in MAP:
        a = np.asarray(Image.open(os.path.join(B.PEN, "_src99", MAP[name] + ".png")).convert("RGBA")).copy()
        return a
    return _orig(name, pal)


B.clean_sprite = _clean
import build_t98_layout as L  # noqa: E402
import build_t98_objects as OB  # noqa: E402

BED_W = {L.SIZE[k][0] for k in ("cama_almofada", "cama_cesto", "cama_pedra", "cama_casal", "viveiro_cesto")}
_shadow = OB.contact_shadow


def flat_shadow(dst, w, dx=0):
    """tapete: sombra de contato curta e colada embaixo (so ~3 px abaixo da borda), alinhada ao eixo vertical."""
    if not BED_SHADOW and w in BED_W:
        return  # camas sem sombra (larguras das camas nao colidem com outros objetos)
    if not NEW or w not in BED_W:
        return _shadow(dst, w, dx)
    yy, xx = np.mgrid[0:OB.FH, 0:OB.FW]
    cy = OB.BY - 2
    for k, (ww, hh, al) in enumerate(((w + 4, 7, 120), (w + 8, 9, 50))):
        m = ((xx + 0.5 - OB.CX) / (ww / 2.0)) ** 2 + ((yy + 0.5 - cy) / (hh / 2.0)) ** 2 <= 1.0
        if k == 1:
            m &= dst[..., 3] == 0
        dst[m & (dst[..., 3] < al)] = (*B.OUTLINE, al)


OB.contact_shadow = flat_shadow

if __name__ == "__main__":
    os.makedirs(B.OUT, exist_ok=True)
    OB.O97.L.PEN = B.OUT
    OB.build_objects()
    OB.O97.build_ambient()
    OB.write_pen()
    print("objetos ok", "tapetes" if NEW else "camas T9.8", {k: L.SIZE[k] for k in ("cama_almofada", "cama_casal")})
