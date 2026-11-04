"""T9.4: layout do quintal (fonte unica para bg, pen.json e previews)."""
PANEL = [736, 16, 208, 508]
PERIODS = ["amanhecer", "dia", "entardecer", "noite"]
# multiplicador de cor (RGB 0-255) que o bg usa e que a UI pode aplicar (BLEND_MULT) em objetos/gatos/ambiente
TINT = {"dia": [255, 255, 255], "amanhecer": [255, 226, 214], "entardecer": [255, 196, 160], "noite": [118, 138, 206]}

RECTS = {"adultos": [48, 118, 388, 350], "breed": [480, 124, 224, 132], "filhotes": [484, 312, 220, 148]}
POND = (128, 414)          # centro da agua da lagoa
TREE = (262, 176)          # base do tronco da arvore grande
FENCE_X = 436              # cerca alta de madeira (adultos | direita)
GATE_Y = (274, 314)        # portao da cerca alta
PATH_X = (452, 470)        # caminho de terra vertical
CASAIS_BOX = [468, 94, 252, 180]   # muretinha de pedra (x,y,w,h)
FILH_BOX = [470, 292, 250, 188]    # cercadinho branco

LAYER = {"cama_almofada": "floor", "cama_cesto": "floor", "cama_pedra": "floor", "cama_casal": "floor",
         "viveiro_cesto": "floor", "novelo": "floor", "tigela": "floor", "tigela_racao": "floor",
         "ratinho": "sorted", "arranhador": "sorted", "bola_filhote": "sorted", "casinha": "sorted",
         "banco_arvore": "sorted", "tunel_filhote": "sorted", "casinha_filhote": "sorted"}


def obj(kind, x, y, slots=None, use=None):
    o = {"kind": kind, "x": x, "y": y, "layer": LAYER[kind], "slots": slots or []}
    if use:
        o["slot_use"] = use
    return o


BED = [[0, -10]]
TOY = [[-24, 0]]
ZONES = {
    "adultos": {"rect": RECTS["adultos"], "objects": [
        obj("casinha", 118, 222, [[-6, -54], [-6, 10]], "sleep"),   # slot 0 telhado (sleep), slot 1 frente (play)
        obj("banco_arvore", 262, 214, [[0, -17]], "sleep"),
        obj("cama_cesto", 90, 316, BED, "sleep"),
        obj("cama_almofada", 372, 166, BED, "sleep"),
        obj("cama_pedra", 384, 340, BED, "sleep"),
        obj("cama_pedra", 226, 372, BED, "sleep"),
        obj("cama_almofada", 290, 446, BED, "sleep"),
        obj("novelo", 190, 296, TOY, "play"),
        obj("novelo", 290, 396, TOY, "play"),
        obj("ratinho", 318, 288, TOY, "play"),
        obj("arranhador", 402, 254, [[-26, 0]], "play"),
        obj("arranhador", 356, 444, [[-26, 0]], "play"),
    ]},
    "breed": {"rect": RECTS["breed"], "objects": [
        obj("cama_casal", 548, 190, [[-20, -10], [20, -10]], "sleep"),
        obj("cama_casal", 652, 190, [[-20, -10], [20, -10]], "sleep"),
        obj("cama_casal", 600, 244, [[-20, -10], [20, -10]], "sleep"),
    ]},
    "filhotes": {"rect": RECTS["filhotes"], "objects": [
        obj("viveiro_cesto", 548, 366, [[-18, -9], [18, -9]], "sleep"),
        obj("viveiro_cesto", 654, 366, [[-18, -9], [18, -9]], "sleep"),
        obj("bola_filhote", 590, 408, [[-16, 0]], "play"),
        obj("bola_filhote", 650, 402, [[-16, 0]], "play"),
        obj("tunel_filhote", 540, 444, [[-46, 4]], "play"),
        obj("tigela", 594, 456),
        obj("tigela_racao", 628, 456),
        obj("casinha_filhote", 670, 458),
    ]},
}

# ambiente: x,y = centro-base (ancora 48,60 do quadro 96x64)
AMBIENT = [
    {"kind": "lagoa", "x": POND[0], "y": POND[1] + 26},
    {"kind": "borboleta", "x": 200, "y": 270, "phase": 0, "periods": ["dia", "amanhecer"]},
    {"kind": "borboleta", "x": 560, "y": 330, "phase": 4, "periods": ["dia", "amanhecer"]},
    {"kind": "vagalumes", "x": 150, "y": 270, "phase": 0, "periods": ["entardecer", "noite"]},
    {"kind": "vagalumes", "x": 330, "y": 330, "phase": 3, "periods": ["entardecer", "noite"]},
    {"kind": "vagalumes", "x": 590, "y": 300, "phase": 5, "periods": ["entardecer", "noite"]},
    {"kind": "folhas", "x": 262, "y": 150, "phase": 0},
    {"kind": "folhas", "x": 60, "y": 190, "phase": 4},
    {"kind": "folhas", "x": 640, "y": 120, "phase": 2},
    {"kind": "lanterna", "x": 38, "y": 104},
    {"kind": "lanterna", "x": 444, "y": 98},
    {"kind": "lanterna", "x": 726, "y": 104},
    {"kind": "lanterna", "x": 38, "y": 490},
    {"kind": "lanterna", "x": 444, "y": 494},
]
