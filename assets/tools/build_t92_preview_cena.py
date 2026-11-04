"""T9.2: preview da cena a 1x: cenario + ambiente + objetos + gatos em varios estados (montado por script)."""
import json
import os
import sys

from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PEN = os.path.join(ROOT, "assets", "pen")
OUTP = os.path.join(ROOT, "reports", "arte", "preview_pen_v2_cena.png")


def sheet(js, png):
    return json.load(open(os.path.join(PEN, js))), Image.open(os.path.join(PEN, png)).convert("RGBA")


def crop(sh, meta, an, f):
    fw, fh = meta["frame"]
    m = meta["anims"][an]
    return sh.crop((f * fw, m["row"] * fh, (f + 1) * fw, (m["row"] + 1) * fh)), m


def main(frame=0):
    bg = Image.open(os.path.join(PEN, "pen_bg.png")).convert("RGBA")
    pen = json.load(open(os.path.join(PEN, "pen.json")))
    oj, osh = sheet("objects.json", "objects.png")
    aj, ash = sheet("ambient.json", "ambient.png")
    cj, csh = sheet("cats_pen.json", "cats_pen.png")
    cats = cj["anims"]

    def cat(cid, an, f):
        m = cats[cid][an]
        return csh.crop((f % m["frames"] * 64, m["row"] * 64, f % m["frames"] * 64 + 64, m["row"] * 64 + 64))

    def put_cat(layerlist, cid, an, x, y, f, flip=False):
        im = cat(cid, an, f)
        if flip:
            im = im.transpose(Image.FLIP_LEFT_RIGHT)
        layerlist.append((y, im, (x - 32, y - 61)))

    ambient_items = pen["ambient"]
    img = bg.copy()

    def draw_amb(kinds):
        for a in ambient_items:
            if a["kind"] in kinds:
                meta = aj["objects"][a["kind"]]
                fr, m = crop(ash, meta, "idle", (frame + a.get("phase", 0)) % meta["anims"]["idle"]["frames"])
                img.alpha_composite(fr, (a["x"] - 32, a["y"] - 60))

    draw_amb({"estrela", "folhas"})
    floor, sorted_ = [], []
    cat_plan = {  # (zona, indice objeto, slot) -> (id, anim, flip)
        ("adultos", 0, 0): ("persa", "sleep", False), ("adultos", 1, 0): ("siames", "sleep", False),
        ("adultos", 3, 0): ("vira-lata", "sleep", True), ("adultos", 6, 0): ("vira-lata", "play", False),
        ("adultos", 8, 0): ("siames", "play", False), ("adultos", 10, 0): ("maine-coon", "play", True),
        ("breed", 0, 0): ("siames", "sleep", False), ("breed", 0, 1): ("persa", "sleep", True),
        ("breed", 1, 0): ("vira-lata", "sleep", False), ("breed", 1, 1): ("maine-coon", "sleep", True),
        ("filhotes", 0, 0): ("siames_filhote", "sleep", False), ("filhotes", 0, 1): ("vira-lata_filhote", "sleep", True),
        ("filhotes", 1, 0): ("persa_filhote", "sleep", False),
        ("filhotes", 2, 0): ("vira-lata_filhote", "play", False), ("filhotes", 3, 0): ("sphynx_filhote", "play", False),
    }
    for zn, z in pen["zones"].items():
        for i, o in enumerate(z["objects"]):
            used = any(k[0] == zn and k[1] == i for k in cat_plan)
            meta = oj["objects"][o["kind"]]
            an = "use" if used else "idle"
            n = meta["anims"][an]["frames"]
            fr, _ = crop(osh, meta, an, (frame + i) % n)
            item = (o["y"], fr, (o["x"] - 48, o["y"] - 60))
            (floor if o["layer"] == "floor" else sorted_).append(item)
            for si, (dx, dy) in enumerate(o["slots"]):
                p = cat_plan.get((zn, i, si))
                if p:
                    put_cat(sorted_, p[0], p[1], o["x"] + dx, o["y"] + dy, frame + si * 3, p[2])
    for y, im, pos in floor:
        img.alpha_composite(im, pos)
    # gatos soltos andando
    put_cat(sorted_, "sphynx", "walk", 360, 220, frame, False)
    put_cat(sorted_, "maine-coon", "idle", 190, 250, frame, False)
    put_cat(sorted_, "persa", "walk", 330, 410, frame, True)
    put_cat(sorted_, "siames", "idle", 60, 380, frame, False)
    sorted_.sort(key=lambda t: t[0])
    for y, im, pos in sorted_:
        img.alpha_composite(im, pos)
    draw_amb({"grama", "arbusto", "fonte", "lanterna", "vagalumes"})
    img.convert("RGB").save(OUTP)


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 0)
