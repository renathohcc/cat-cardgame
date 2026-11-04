"""T9.6: layout do quintal (fonte unica: bg, objetos, pen.json, previews)."""
import os

from PIL import Image

PANEL = [736, 16, 208, 508]
PERIODS = ["amanhecer", "dia", "entardecer", "noite"]
TINT = {"dia": [255, 255, 255], "amanhecer": [255, 226, 214], "entardecer": [255, 196, 160], "noite": [118, 138, 206]}

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(ROOT, "assets", "pen", "_src96")

# portoes Pixellab colados no fundo: arquivo -> (centro x, base y)
GATES = {"obj_portao_grande.png": (358, 508), "obj_portao_pequeno2.png": (587, 252)}
# lampioes/lanternas existentes no fundo (para brilho a noite e ambient 'lanterna')
LAMPS = [(88, 16), (56, 466), (482, 20), (681, 22), (453, 512), (708, 508), (100, 132), (168, 106)]

RECTS = {"adultos": [48, 98, 392, 370], "breed": [480, 100, 212, 124], "filhotes": [474, 310, 218, 190]}

LAYER = {"cama_almofada": "floor", "cama_cesto": "floor", "cama_pedra": "floor", "cama_casal": "floor",
         "viveiro_cesto": "floor", "novelo": "floor", "tigela": "floor", "tigela_racao": "floor",
         "ratinho": "sorted", "arranhador": "sorted", "bola_filhote": "sorted", "casinha": "sorted",
         "banco_arvore": "sorted", "tunel_filhote": "sorted", "casinha_filhote": "sorted"}
SRCNAME = {"cama_almofada": "cama_almofada", "cama_cesto": "cama_cesto", "cama_pedra": "cama_pedra",
           "cama_casal": "cama_casal", "viveiro_cesto": "viveiro_cesto2", "novelo": "novelo", "ratinho": "ratinho",
           "arranhador": "arranhador", "bola_filhote": "bola", "tunel_filhote": "tunel", "tigela": "tigela",
           "tigela_racao": "tigela_racao", "casinha_filhote": "casinha_filhote"}


def sprite(kind):
    """sprite recortado (bbox) do objeto Pixellab."""
    im = Image.open(os.path.join(SRC, "obj_%s.png" % SRCNAME[kind])).convert("RGBA")
    return im.crop(im.getbbox())


def obj(kind, x, y, slots=None, use=None):
    o = {"kind": kind, "x": x, "y": y, "layer": LAYER[kind], "slots": slots or []}
    if use:
        o["slot_use"] = use
    return o


def bed_slot(kind):
    h = sprite(kind).height
    return [[0, -round(h * 0.36)]]


def couple_slots(kind):
    s = sprite(kind)
    dy = -round(s.height * 0.38)
    dx = round(s.width * 0.2)
    return [[-dx, dy], [dx, dy]]


def kit_slots(kind):
    s = sprite(kind)
    dy = -round(s.height * 0.36)
    dx = round(s.width * 0.18)
    return [[-dx, dy], [dx, dy]]


TOY = [[-24, 0]]
ZONES = {
    "adultos": {"rect": RECTS["adultos"], "objects": [
        obj("casinha", 132, 186, [[-14, -80], [28, -8]], "sleep"),     # slot 0 telhado (sleep), slot 1 rampa (play)
        obj("banco_arvore", 300, 160, [[0, -26]], "sleep"),
        obj("cama_cesto", 110, 316, bed_slot("cama_cesto"), "sleep"),
        obj("cama_almofada", 372, 214, bed_slot("cama_almofada"), "sleep"),
        obj("cama_pedra", 300, 330, bed_slot("cama_pedra"), "sleep"),
        obj("cama_pedra", 160, 392, bed_slot("cama_pedra"), "sleep"),
        obj("cama_almofada", 392, 410, bed_slot("cama_almofada"), "sleep"),
        obj("novelo", 190, 270, TOY, "play"),
        obj("novelo", 330, 270, TOY, "play"),
        obj("ratinho", 262, 255, TOY, "play"),
        obj("arranhador", 410, 330, [[-26, 0]], "play"),
        obj("arranhador", 210, 205, [[-26, 0]], "play"),
    ]},
    "breed": {"rect": RECTS["breed"], "objects": [
        obj("cama_casal", 538, 168, couple_slots("cama_casal"), "sleep"),
        obj("cama_casal", 646, 168, couple_slots("cama_casal"), "sleep"),
    ]},
    "filhotes": {"rect": RECTS["filhotes"], "objects": [
        obj("viveiro_cesto", 538, 372, kit_slots("viveiro_cesto"), "sleep"),
        obj("viveiro_cesto", 538, 456, kit_slots("viveiro_cesto"), "sleep"),
        obj("bola_filhote", 600, 372, [[-16, 0]], "play"),
        obj("bola_filhote", 590, 428, [[-16, 0]], "play"),
        obj("tunel_filhote", 648, 484, [[-46, 4]], "play"),
        obj("tigela", 504, 500),
        obj("tigela_racao", 552, 502),
        obj("casinha_filhote", 656, 396),
    ]},
}


def pond_water():
    """(cx, cy) do centro da agua da lagoa (detectado no bg)."""
    return (258, 405)


AMBIENT = [
    {"kind": "lagoa", "x": 0, "y": 0},   # preenchido em build_t96_objects (centro detectado no bg)
    {"kind": "borboleta", "x": 220, "y": 270, "phase": 0, "periods": ["dia", "amanhecer"]},
    {"kind": "borboleta", "x": 560, "y": 400, "phase": 4, "periods": ["dia", "amanhecer"]},
    {"kind": "vagalumes", "x": 150, "y": 270, "phase": 0, "periods": ["entardecer", "noite"]},
    {"kind": "vagalumes", "x": 330, "y": 330, "phase": 3, "periods": ["entardecer", "noite"]},
    {"kind": "vagalumes", "x": 590, "y": 400, "phase": 5, "periods": ["entardecer", "noite"]},
    {"kind": "folhas", "x": 320, "y": 100, "phase": 0},
    {"kind": "folhas", "x": 60, "y": 190, "phase": 4},
    {"kind": "folhas", "x": 640, "y": 120, "phase": 2},
] + [{"kind": "lanterna", "x": x, "y": y} for x, y in LAMPS]
