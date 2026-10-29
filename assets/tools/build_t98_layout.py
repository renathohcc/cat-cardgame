"""T9.8: layout do quintal (mesma grade/zonas/caminhos da T9.7) com os sprites do Pixellab: tamanhos reais (bbox limpo),
posicoes e slots reajustados. Fonte unica para bg, objetos, pen.json e check."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from build_t97_layout import (AMBIENT, GATES, H, LAMPS, PANEL, PATH_H, PATH_H_END_X, PATH_V, PEN, PERIODS, RECTS,  # noqa: E402,F401
                              RINGS, ROOT, T, TINT, W, interior)
import build_t98_lib as B  # noqa: E402

# kind (contrato da UI) -> sprite fonte do Pixellab
SRC = {"cama_almofada": "cama_teal_L", "cama_cesto": "cama_cesto_L", "cama_pedra": "cama_cinza_L",
       "cama_casal": "cama_casal_L", "viveiro_cesto": "viveiro_L", "banco_arvore": "banco_L", "casinha": "casinha_L",
       "novelo": "novelo", "ratinho": "ratinho", "arranhador": "arranhador_L", "bola_filhote": "bola",
       "tunel_filhote": "tunel_b", "tigela": "tigela_agua", "tigela_racao": "tigela_racao",
       "casinha_filhote": "casinha_filhote_L"}
LAYER = {"cama_almofada": "floor", "cama_cesto": "floor", "cama_pedra": "floor", "cama_casal": "floor",
         "viveiro_cesto": "floor", "novelo": "floor", "tigela": "floor", "tigela_racao": "floor",
         "ratinho": "sorted", "arranhador": "sorted", "bola_filhote": "sorted", "casinha": "sorted",
         "banco_arvore": "sorted", "tunel_filhote": "sorted", "casinha_filhote": "sorted"}
ORDER = ["cama_almofada", "cama_cesto", "cama_pedra", "cama_casal", "viveiro_cesto", "banco_arvore", "casinha",
         "novelo", "ratinho", "arranhador", "bola_filhote", "tunel_filhote", "tigela", "tigela_racao", "casinha_filhote"]


def _sizes():
    out = {}
    for k, s in SRC.items():
        a = B.clean_sprite(s)
        out[k] = (a.shape[1], a.shape[0])
    return out


SIZE = _sizes()


def bed_slot(kind):
    return [[0, -round(SIZE[kind][1] * 0.40)]]


def obj(kind, x, y, slots=None, use=None):
    o = {"kind": kind, "x": x, "y": y, "layer": LAYER[kind], "slots": slots if slots is not None else []}
    if use:
        o["slot_use"] = use
    return o


TOY = [[-20, 0]]
ZONES = {
    "adultos": {"rect": RECTS["adultos"], "objects": [
        obj("casinha", 104, 162, [[0, -44], [48, -2]], "sleep"),
        obj("banco_arvore", 232, 140, [[0, -16]], "sleep"),
        obj("arranhador", 356, 150, [[-30, 0]], "play"),
        obj("cama_almofada", 100, 278, bed_slot("cama_almofada"), "sleep"),
        obj("novelo", 184, 268, TOY, "play"),
        obj("cama_cesto", 262, 306, bed_slot("cama_cesto"), "sleep"),
        obj("ratinho", 336, 240, [[-22, 0]], "play"),
        obj("cama_pedra", 100, 392, bed_slot("cama_pedra"), "sleep"),
        obj("novelo", 190, 380, TOY, "play"),
        obj("cama_almofada", 292, 414, bed_slot("cama_almofada"), "sleep"),
        obj("arranhador", 396, 380, [[-30, 0]], "play"),
        obj("cama_pedra", 150, 462, bed_slot("cama_pedra"), "sleep"),
        obj("tigela", 336, 468),
        obj("tigela_racao", 372, 468),
    ]},
    "breed": {"rect": RECTS["breed"], "objects": [
        obj("cama_casal", 552, 140, [[-20, -12], [20, -12]], "sleep"),
        obj("cama_casal", 654, 214, [[-20, -12], [20, -12]], "sleep"),
    ]},
    "filhotes": {"rect": RECTS["filhotes"], "objects": [
        obj("viveiro_cesto", 540, 374, [[-12, -9], [12, -9]], "sleep"),
        obj("viveiro_cesto", 540, 460, [[-12, -9], [12, -9]], "sleep"),
        obj("bola_filhote", 618, 376, [[-14, 0]], "play"),
        obj("bola_filhote", 596, 428, [[-14, 0]], "play"),
        obj("tunel_filhote", 652, 470, [[-52, 2]], "play"),
        obj("tigela", 512, 480),
        obj("tigela_racao", 538, 480),
        obj("casinha_filhote", 668, 408),
    ]},
}
