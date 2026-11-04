"""T9.2: layout do cercado (zonas, objetos, ambiente). Fonte unica para bg, pen.json e previews."""
PANEL = [736, 16, 208, 508]
WALK = [48, 96, 664, 372]
RECTS = {"adultos": [48, 96, 440, 372], "breed": [496, 96, 216, 180], "filhotes": [496, 288, 216, 180]}

# layer: floor = desenhar abaixo de todos os gatos; sorted = ordenar por y junto com os gatos
LAYER = {"cama_almofada": "floor", "cama_cesto": "floor", "cama_pedra": "floor", "cama_casal": "floor",
         "viveiro_cesto": "floor", "novelo": "floor", "ratinho": "sorted", "pena": "sorted",
         "arranhador": "sorted", "bola_filhote": "sorted", "casinha": "sorted"}


def obj(kind, x, y, slots, use=None):
    o = {"kind": kind, "x": x, "y": y, "layer": LAYER[kind], "slots": slots}
    if use:
        o["slot_use"] = use
    return o


BED = [[0, -8]]
TOY = [[-24, 0]]
ZONES = {
    "adultos": {"rect": RECTS["adultos"], "objects": [
        obj("cama_almofada", 100, 176, BED, "sleep"),
        obj("cama_cesto", 262, 158, BED, "sleep"),
        obj("cama_pedra", 408, 184, BED, "sleep"),
        obj("cama_cesto", 104, 432, BED, "sleep"),
        obj("cama_pedra", 276, 442, BED, "sleep"),
        obj("cama_almofada", 420, 424, BED, "sleep"),
        obj("novelo", 214, 292, TOY, "play"),
        obj("novelo", 372, 330, TOY, "play"),
        obj("ratinho", 330, 244, TOY, "play"),
        obj("pena", 160, 360, TOY, "play"),
        obj("arranhador", 452, 300, [[-26, 0]], "play"),
        obj("arranhador", 96, 290, [[-26, 0]], "play"),
        obj("casinha", 250, 400, [[0, 6]], "play"),
    ]},
    "breed": {"rect": RECTS["breed"], "objects": [
        obj("cama_casal", 552, 168, [[-20, -9], [20, -9]], "sleep"),
        obj("cama_casal", 656, 168, [[-20, -9], [20, -9]], "sleep"),
        obj("cama_casal", 604, 254, [[-20, -9], [20, -9]], "sleep"),
    ]},
    "filhotes": {"rect": RECTS["filhotes"], "objects": [
        obj("viveiro_cesto", 552, 356, [[-20, -7], [20, -7]], "sleep"),
        obj("viveiro_cesto", 656, 356, [[-20, -7], [20, -7]], "sleep"),
        obj("bola_filhote", 568, 436, [[-16, 0]], "play"),
        obj("bola_filhote", 650, 432, [[-16, 0]], "play"),
    ]},
}

AMBIENT = [
    {"kind": "lanterna", "x": 70, "y": 94}, {"kind": "lanterna", "x": 380, "y": 94},
    {"kind": "lanterna", "x": 690, "y": 94}, {"kind": "lanterna", "x": 30, "y": 288},
    {"kind": "lanterna", "x": 724, "y": 288}, {"kind": "lanterna", "x": 54, "y": 506},
    {"kind": "lanterna", "x": 700, "y": 506},
    {"kind": "vagalumes", "x": 150, "y": 220, "phase": 0}, {"kind": "vagalumes", "x": 330, "y": 400, "phase": 3},
    {"kind": "vagalumes", "x": 420, "y": 150, "phase": 5}, {"kind": "vagalumes", "x": 610, "y": 215, "phase": 2},
    {"kind": "vagalumes", "x": 650, "y": 420, "phase": 6}, {"kind": "vagalumes", "x": 220, "y": 515, "phase": 4},
    {"kind": "vagalumes", "x": 530, "y": 120, "phase": 1}, {"kind": "vagalumes", "x": 40, "y": 400, "phase": 7},
    {"kind": "estrela", "x": 90, "y": 52, "phase": 0}, {"kind": "estrela", "x": 250, "y": 52, "phase": 3},
    {"kind": "estrela", "x": 420, "y": 52, "phase": 5}, {"kind": "estrela", "x": 590, "y": 52, "phase": 2},
    {"kind": "estrela", "x": 740, "y": 52, "phase": 6}, {"kind": "estrela", "x": 860, "y": 52, "phase": 1},
    {"kind": "folhas", "x": 40, "y": 100, "phase": 0}, {"kind": "folhas", "x": 300, "y": 96, "phase": 4},
    {"kind": "folhas", "x": 560, "y": 96, "phase": 2}, {"kind": "folhas", "x": 22, "y": 330, "phase": 6},
    {"kind": "folhas", "x": 724, "y": 370, "phase": 3},
    {"kind": "arbusto", "x": 30, "y": 112, "phase": 0}, {"kind": "arbusto", "x": 714, "y": 114, "phase": 3},
    {"kind": "arbusto", "x": 28, "y": 470, "phase": 5}, {"kind": "arbusto", "x": 716, "y": 476, "phase": 2},
    {"kind": "arbusto", "x": 492, "y": 284, "phase": 4}, {"kind": "arbusto", "x": 492, "y": 106, "phase": 1},
    {"kind": "arbusto", "x": 492, "y": 470, "phase": 6},
    {"kind": "fonte", "x": 380, "y": 528},
]
GRAMA = [(60, 500), (120, 512), (300, 500), (450, 510), (560, 504), (640, 520), (24, 200), (28, 390),
         (722, 200), (724, 420), (160, 92), (480, 92), (600, 92), (260, 488), (500, 486)]
for i, (gx, gy) in enumerate(GRAMA):
    AMBIENT.append({"kind": "grama", "x": gx, "y": gy, "phase": i % 6})
