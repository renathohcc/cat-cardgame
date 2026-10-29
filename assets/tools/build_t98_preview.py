"""T9.8: previews (le de T98_OUT se definido) (cena com gatos + carta/tabuleiro noturno, 4 periodos, objetos 4x). Uso: python build_t97_preview.py"""
import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
import build_t98_layout as L  # noqa: E402
import build_t98_lib as B  # noqa: E402

PEN, REP = B.OUT, os.path.join(L.ROOT, "reports", "arte")
PENR = L.PEN                      # gatos sempre da pasta real
BREEDS = ["vira-lata", "siames", "persa", "sphynx", "maine-coon"]


def sheet(js):
    j = json.load(open(os.path.join(PEN, js)))
    return j, Image.open(os.path.join(PEN, j["image"])).convert("RGBA")


def fr(sh, meta, an, i=0):
    w, h = meta["frame"]
    m = meta["anims"][an]
    return sh.crop(((i % m["frames"]) * w, m["row"] * h, (i % m["frames"] + 1) * w, (m["row"] + 1) * h))


def cat_frame(cj, cs, breed, anim, i=0):
    a = cj["anims"][breed][anim]
    return cs.crop(((i % a["frames"]) * 64, a["row"] * 64, (i % a["frames"] + 1) * 64, (a["row"] + 1) * 64))


def scene(bg="pen_bg_dia.png", tint=(255, 255, 255)):
    im = Image.open(os.path.join(PEN, bg)).convert("RGBA")
    layer = Image.new("RGBA", im.size, (0, 0, 0, 0))
    oj, os_ = sheet("objects.json")
    cj = json.load(open(os.path.join(PENR, "cats_pen.json")))
    cs = Image.open(os.path.join(PENR, "cats_pen.png")).convert("RGBA")
    pen = json.load(open(os.path.join(PEN, "pen.json")))
    items = []
    n = 0
    for zn, z in pen["zones"].items():
        for o in z["objects"]:
            meta = oj["objects"][o["kind"]]
            ax, ay = meta["anchor"]
            idx = "enter" if "enter" in meta["anims"] and o["slots"] else "idle"
            f = fr(os_, meta, idx, 99)
            items.append((0 if o["layer"] == "floor" else 1, o["y"], f, (o["x"] - ax, o["y"] - ay), None))
            for s, (dx, dy) in enumerate(o["slots"]):
                if s % 2 == 1 and zn == "adultos":
                    continue
                kit = zn == "filhotes"
                b = BREEDS[n % 5]
                n += 1
                sid = b + ("_filhote" if kit else "")
                anim = "sleep" if o.get("slot_use") == "sleep" else "play"
                cf = cat_frame(cj, cs, sid, anim, 6 if anim == "sleep" else 2)
                sx, sy = o["x"] + dx, o["y"] + dy
                items.append((2, o["y"] + 0.5, cf, (sx - 32, sy - 62), None))
    for x, y, b, a in [(300, 210, "siames", "idle"), (180, 330, "maine-coon", "walk"), (440 - 60, 420, "persa", "idle"),
                       (230, 120, "vira-lata", "walk"), (560, 270 + 0, "sphynx", "idle")]:
        pass
    for x, y, b, a, kit in [(290, 214, "siames", "idle", False), (200, 330, "maine-coon", "walk", False),
                            (330, 440, "persa", "idle", False), (180, 190, "vira-lata", "walk", False),
                            (600, 330, "sphynx_filhote", "walk", True), (640, 140, "persa", "idle", False)]:
        sid = b
        cf = cat_frame(cj, cs, sid, a, 2)
        items.append((2, y, cf, (x - 32, y - 62), None))
    items.sort(key=lambda t: (t[0] == 2 and 1 or t[0], t[1]) if t[0] != 0 else (0, 0))
    floor = [i for i in items if i[0] == 0]
    rest = sorted([i for i in items if i[0] != 0], key=lambda t: t[1])
    for it in floor + rest:
        spr = it[2]
        if tint != (255, 255, 255):
            r, g, b, a = spr.split()
            spr = Image.merge("RGBA", (r.point(lambda v: v * tint[0] // 255), g.point(lambda v: v * tint[1] // 255),
                                       b.point(lambda v: v * tint[2] // 255), a))
        layer.alpha_composite(spr, it[3])
    im.alpha_composite(layer)
    return im


def compose():
    sc = scene()
    inicio = Image.open(os.path.join(L.ROOT, "reports", "ui", "inicio.png")).convert("RGBA")
    strip = inicio.crop((0, 380, 960, 540))
    out = Image.new("RGBA", (960, 540 + 160), (16, 20, 38, 255))
    out.alpha_composite(sc, (0, 0))
    out.alpha_composite(strip, (0, 540))
    out.convert("RGB").save(os.path.join(REP, "preview_pen_v6_cena.png"))


def periodos():
    names = ["amanhecer", "dia", "entardecer", "noite"]
    out = Image.new("RGB", (960, 540))
    for i, n in enumerate(names):
        sc = scene(f"pen_bg_{n}.png", tuple(L.TINT[n]))
        out.paste(sc.convert("RGB").resize((480, 270), Image.NEAREST), ((i % 2) * 480, (i // 2) * 270))
        ImageDraw.Draw(out).text(((i % 2) * 480 + 6, (i // 2) * 270 + 4), n, fill=(255, 255, 255))
    out.save(os.path.join(REP, "preview_pen_v6_periodos.png"))


def objetos():
    oj, os_ = sheet("objects.json")
    names = list(oj["objects"])
    cell = 140
    out = Image.new("RGBA", (5 * cell, 3 * 110), (121, 180, 90, 255))
    for i, n in enumerate(names):
        f = fr(os_, oj["objects"][n], "idle", 0)
        out.alpha_composite(f.crop((0, 0, 128, 96)), ((i % 5) * cell + 6, (i // 5) * 110 + 8))
    out = out.resize((out.width * 2, out.height * 2), Image.NEAREST)
    out.convert("RGB").save(os.path.join(REP, "preview_pen_v6_objetos.png"))


if __name__ == "__main__":
    compose()
    periodos()
    objetos()
    print("previews ok")


def tilesets():
    """tilesets quantizados (sheets 4x4 de 16 px, 6x) + sprites de cerca/vegetacao."""
    import build_t98_bg as G
    out = Image.new("RGB", (1100, 640), (24, 22, 34))
    x = 8
    for n, kw in (("ts_grass_dirt", {"other": "dirt"}), ("ts_grass_path", {"other": "path"}), ("ts_floor3", {"floor": True})):
        ts = G.load_ts(n, **kw)
        sh = Image.new("RGBA", (64, 64))
        meta = json.load(open(os.path.join(B.SRC, n + ".json")))["tileset_data"]["tiles"]
        for t in meta:
            c = t["corners"]
            key = tuple(c[k] == "lower" for k in ("NW", "NE", "SW", "SE"))
            bb = t["bounding_box"]
            sh.paste(Image.fromarray(ts[key], "RGBA"), (bb["x"], bb["y"]))
        out.paste(sh.resize((352, 352), Image.NEAREST).convert("RGB"), (x, 8))
        x += 362
    y = 380
    x = 8
    for n in ("cerca_h", "cerca_v", "poste_portao", "arvore_a", "arvore_b", "arvore_peq1", "arvore_peq2", "moita_flor",
              "moita_b", "moita_c"):
        a = G.spr(n)
        im = Image.fromarray(a, "RGBA")
        k = 3
        im = im.resize((im.width * k, im.height * k), Image.NEAREST)
        bg = Image.new("RGBA", im.size, (121, 180, 90, 255))
        bg.alpha_composite(im)
        out.paste(bg.convert("RGB"), (x, y))
        x += im.width + 8
    out.save(os.path.join(REP, "preview_pen_v6_tilesets.png"))


if __name__ == "__main__":
    tilesets()
