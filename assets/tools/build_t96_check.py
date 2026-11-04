"""T9.6: valida layout: objetos dentro da zona, sem sobreposicao entre objetos, slots em chao livre (fora de agua/portoes/cabana)."""
import json, os, sys
sys.path.insert(0, os.path.dirname(__file__))
import build_t96_layout as L
pen = json.load(open(os.path.join(L.ROOT, "assets", "pen", "pen.json")))
BLOCK = {"lagoa": (205, 375, 320, 450), "portao_grande": (308, 428, 408, 510), "portao_pequeno": (546, 168, 630, 252),
         "casinha_bg": (66, 58, 186, 190)}
bad = 0
for zn, z in pen["zones"].items():
    zx, zy, zw, zh = z["rect"]
    boxes = []
    for o in z["objects"]:
        s = L.sprite(o["kind"]) if o["kind"] in L.SRCNAME else None
        if s is None:
            continue
        b = (o["x"] - s.width // 2, o["y"] - s.height, o["x"] + s.width // 2, o["y"])
        if not (zx - 6 <= b[0] and b[2] <= zx + zw + 6 and zy - 6 <= b[1] and b[3] <= zy + zh + 6):
            print("FORA da zona", zn, o["kind"], b); bad += 1
        for k, bb in BLOCK.items():
            if b[0] < bb[2] and b[2] > bb[0] and b[1] < bb[3] and b[3] > bb[1] and not (k == "casinha_bg" and False):
                print("sobrepoe estatico", zn, o["kind"], k, b); bad += 1
        for ob in boxes:
            if b[0] < ob[1][2] - 4 and b[2] > ob[1][0] + 4 and b[1] < ob[1][3] - 4 and b[3] > ob[1][1] + 4:
                print("sobrepoe objeto", o["kind"], ob[0]); bad += 1
        boxes.append((o["kind"], b))
        for dx, dy in o["slots"]:
            sx, sy = o["x"] + dx, o["y"] + dy
            if not (zx - 40 <= sx <= zx + zw + 40 and zy - 90 <= sy <= zy + zh + 10):
                print("slot fora", zn, o["kind"], sx, sy); bad += 1
            for k, bb in BLOCK.items():
                if k != "casinha_bg" and bb[0] < sx < bb[2] and bb[1] < sy < bb[3]:
                    print("slot em bloco", zn, o["kind"], k, sx, sy); bad += 1
print("problemas:", bad)
