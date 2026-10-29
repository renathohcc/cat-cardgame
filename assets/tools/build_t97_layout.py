"""T9.7: layout do quintal em grade de 16 px (fonte unica: bg, objetos, pen.json, preview, check)."""
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PEN = os.path.join(ROOT, "assets", "pen")
T = 16
W, H = 960, 540
PANEL = [736, 16, 208, 508]
PERIODS = ["amanhecer", "dia", "entardecer", "noite"]
TINT = {"dia": [255, 255, 255], "amanhecer": [255, 226, 214], "entardecer": [255, 196, 160], "noite": [118, 138, 206]}

# cercas: aneis de 1 tile (col/linha da cerca em tiles); interior = dentro do anel
# (c0, r0, c1, r1) inclusivos do anel
RINGS = {"adultos": (2, 3, 27, 30), "breed": (30, 3, 44, 15), "filhotes": (30, 18, 44, 30)}
# vaos de 2 tiles: zona -> (lado, primeiro tile do vao)
GATES = {"adultos": ("E", 16), "breed": ("S", 36), "filhotes": ("N", 36)}
# caminho: vertical x 448..480 (tiles 28-29), horizontal y 256..288 (tiles 16-17)
PATH_V = (28, 29)
PATH_H = (16, 17)
PATH_H_END_X = 740            # termina atras do painel da UI


def interior(zone):
    c0, r0, c1, r1 = RINGS[zone]
    return ((c0 + 1) * T, (r0 + 1) * T, (c1 - c0 - 1) * T, (r1 - r0 - 1) * T)       # x, y, w, h


RECTS = {z: list(interior(z)) for z in RINGS}

SIZE = {"cama_almofada": (64, 40), "cama_cesto": (56, 36), "cama_pedra": (48, 32), "cama_casal": (88, 44),
        "viveiro_cesto": (56, 36), "banco_arvore": (72, 40), "casinha": (64, 64), "novelo": (16, 16),
        "ratinho": (20, 12), "arranhador": (40, 72), "bola_filhote": (16, 16), "tunel_filhote": (80, 40),
        "tigela": (20, 12), "tigela_racao": (20, 12), "casinha_filhote": (64, 64)}
LAYER = {"cama_almofada": "floor", "cama_cesto": "floor", "cama_pedra": "floor", "cama_casal": "floor",
         "viveiro_cesto": "floor", "novelo": "floor", "tigela": "floor", "tigela_racao": "floor",
         "ratinho": "sorted", "arranhador": "sorted", "bola_filhote": "sorted", "casinha": "sorted",
         "banco_arvore": "sorted", "tunel_filhote": "sorted", "casinha_filhote": "sorted"}
ORDER = ["cama_almofada", "cama_cesto", "cama_pedra", "cama_casal", "viveiro_cesto", "banco_arvore", "casinha",
         "novelo", "ratinho", "arranhador", "bola_filhote", "tunel_filhote", "tigela", "tigela_racao", "casinha_filhote"]


def bed_slot(kind):
    return [[0, -round(SIZE[kind][1] * 0.32)]]


def obj(kind, x, y, slots=None, use=None):
    o = {"kind": kind, "x": x, "y": y, "layer": LAYER[kind], "slots": slots if slots is not None else []}
    if use:
        o["slot_use"] = use
    return o


TOY = [[-22, 0]]
ZONES = {
    "adultos": {"rect": RECTS["adultos"], "objects": [
        obj("casinha", 104, 156, [[0, -48], [44, -2]], "sleep"),
        obj("banco_arvore", 240, 130, [[0, -22]], "sleep"),
        obj("arranhador", 356, 150, [[-26, 0]], "play"),
        obj("cama_almofada", 100, 270, bed_slot("cama_almofada"), "sleep"),
        obj("novelo", 190, 262, TOY, "play"),
        obj("cama_cesto", 272, 292, bed_slot("cama_cesto"), "sleep"),
        obj("ratinho", 330, 240, [[-24, 0]], "play"),
        obj("cama_pedra", 100, 384, bed_slot("cama_pedra"), "sleep"),
        obj("novelo", 200, 372, TOY, "play"),
        obj("cama_almofada", 300, 400, bed_slot("cama_almofada"), "sleep"),
        obj("arranhador", 392, 374, [[-26, 0]], "play"),
        obj("cama_pedra", 148, 452, bed_slot("cama_pedra"), "sleep"),
        obj("tigela", 340, 464),
        obj("tigela_racao", 372, 464),
    ]},
    "breed": {"rect": RECTS["breed"], "objects": [
        obj("cama_casal", 552, 136, [[-20, -14], [20, -14]], "sleep"),
        obj("cama_casal", 652, 204, [[-20, -14], [20, -14]], "sleep"),
    ]},
    "filhotes": {"rect": RECTS["filhotes"], "objects": [
        obj("viveiro_cesto", 540, 372, [[-13, -10], [13, -10]], "sleep"),
        obj("viveiro_cesto", 540, 452, [[-13, -10], [13, -10]], "sleep"),
        obj("bola_filhote", 622, 372, [[-16, 0]], "play"),
        obj("bola_filhote", 592, 424, [[-16, 0]], "play"),
        obj("tunel_filhote", 644, 468, [[-46, 4]], "play"),
        obj("tigela", 516, 474),
        obj("tigela_racao", 556, 474),
        obj("casinha_filhote", 668, 404),
    ]},
}

# lanternas (ambient 'lanterna'): (x, y) = pe do poste; a cabeca fica em (x+4, y-28)
LAMPS = [(440, 46), (488, 46), (440, 526), (488, 526)]

AMBIENT = [
    {"kind": "borboleta", "x": 210, "y": 210, "phase": 0, "periods": ["dia", "amanhecer"]},
    {"kind": "borboleta", "x": 570, "y": 410, "phase": 4, "periods": ["dia", "amanhecer"]},
    {"kind": "vagalumes", "x": 150, "y": 250, "phase": 0, "periods": ["entardecer", "noite"]},
    {"kind": "vagalumes", "x": 330, "y": 330, "phase": 3, "periods": ["entardecer", "noite"]},
    {"kind": "vagalumes", "x": 590, "y": 400, "phase": 5, "periods": ["entardecer", "noite"]},
    {"kind": "folhas", "x": 320, "y": 100, "phase": 0},
    {"kind": "folhas", "x": 60, "y": 190, "phase": 4},
    {"kind": "folhas", "x": 640, "y": 120, "phase": 2},
] + [{"kind": "lanterna", "x": x, "y": y} for x, y in LAMPS]
