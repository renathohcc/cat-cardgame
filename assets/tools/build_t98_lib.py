"""T9.8: biblioteca comum (paleta PEN expandida, quantizacao, recorte). Sem resize: tudo 1:1.
Fontes cruas do Pixellab em assets/pen/_src98/."""
import json
import os

import numpy as np
from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PEN = os.path.join(ROOT, "assets", "pen")
SRC = os.path.join(PEN, "_src98")
OUT = os.environ.get("T98_OUT") or PEN          # T98_OUT=staging p/ previews antes de integrar
OUTLINE = (0x3B, 0x2A, 0x38)

# fontes que entram na paleta (sprites + tilesets + cerca)
SPRITES = ["cama_rosa_L", "cama_teal_L", "cama_cesto_L", "cama_cinza_L", "cama_casal_L", "viveiro_L", "banco_L",
           "casinha_L", "casinha_filhote_L", "arranhador_L", "tunel_b", "novelo", "ratinho", "bola", "tigela_agua",
           "tigela_racao", "arvore_a", "arvore_b", "arvore_peq1", "arvore_peq2", "moita_flor", "moita_b", "moita_c"]
TILESETS = ["ts_grass_dirt", "ts_grass_path", "ts_floor2", "ts_floor3"]


def load_rgba(path):
    im = Image.open(path).convert("RGBA")
    a = np.asarray(im).copy()
    a[..., 3] = np.where(a[..., 3] >= 128, 255, 0)
    a[a[..., 3] == 0] = 0
    return a


def source_pixels(tilesets=False):
    pool = []
    for n in SPRITES:
        p = os.path.join(SRC, n + ".png")
        if os.path.exists(p):
            a = load_rgba(p)
            pool.append(a[a[..., 3] > 0][:, :3])
    for n in (TILESETS if tilesets else []):
        p = os.path.join(SRC, n + ".png")
        if os.path.exists(p):
            a = load_rgba(p)
            pool.append(a[a[..., 3] > 0][:, :3])
    return np.concatenate(pool)


def palette_rgb():
    with open(os.path.join(PEN, "palette_pen.json")) as f:
        d = json.load(f)
    return [(k, tuple(int(v[i:i + 2], 16) for i in (1, 3, 5))) for k, v in d.items()]


def quantize(a, pal=None, outline_luma=78):
    """a: RGBA uint8 (alpha ja binario). Mapeia cada pixel ao mais proximo da paleta; muito escuro -> contorno."""
    pal = pal or palette_rgb()
    P = np.array([c for _, c in pal], np.int32)
    out = a.copy()
    m = a[..., 3] > 0
    px = a[m][:, :3].astype(np.int32)
    w = np.array([2, 4, 3])                                # ponderacao perceptual simples
    d = (((px[:, None, :] - P[None, :, :]) ** 2) * w).sum(-1)
    idx = d.argmin(1)
    res = P[idx].astype(np.uint8)
    luma = (px * np.array([0.299, 0.587, 0.114])).sum(1)
    res[luma < outline_luma] = OUTLINE
    out[m, :3] = res
    return out


def clean_sprite(name, pal=None):
    """carrega fonte crua, binariza alpha, quantiza na paleta, corta ao bbox. Retorna RGBA uint8."""
    a = quantize(load_rgba(os.path.join(SRC, name + ".png")), pal)
    a = fix_edges(a)
    ys, xs = np.nonzero(a[..., 3])
    return a[ys.min():ys.max() + 1, xs.min():xs.max() + 1].copy()


def halo_pixels(a):
    """pixels de borda (vizinho transparente 4-conexo) que NAO sao contorno: indicam halo/contorno ausente."""
    al = a[..., 3] > 0
    pad = np.pad(al, 1)
    edge = al & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
    notol = ~(a[..., :3] == np.array(OUTLINE)).all(-1)
    return int((edge & notol).sum()), int(edge.sum())


def fix_edges(a, luma_max=135):
    """pixels de borda escuros que nao sao o contorno (por quantizacao) viram contorno: evita halo/fio sem contorno."""
    al = a[..., 3] > 0
    pad = np.pad(al, 1)
    edge = al & ~(pad[:-2, 1:-1] & pad[2:, 1:-1] & pad[1:-1, :-2] & pad[1:-1, 2:])
    luma = (a[..., :3].astype(np.float32) * np.array([0.299, 0.587, 0.114])).sum(-1)
    m = edge & (luma < luma_max)
    a = a.copy()
    a[m, :3] = OUTLINE
    return a
