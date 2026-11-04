"""T9.6: pen.json + previews (periodos, cena com gatos, objetos 4x). Uso: python assets/tools/build_t94_preview.py [pen|periodos|cena|objetos]"""
import json
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))
import build_t96_layout as L  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PEN = os.path.join(ROOT, "assets", "pen")
REP = os.path.join(ROOT, "reports", "arte")


def ambient():
    import build_t96_objects as O
    m, bb = O.water_mask()
    cx, cy = (bb[0] + bb[2]) // 2, (bb[1] + bb[3]) // 2
    out = []
    for a in L.AMBIENT:
        a = dict(a)
        if a["kind"] == "lagoa":
            a["x"], a["y"] = cx, cy + 26
        out.append(a)
    return out


def write_pen():
    pen = {
        "bg": "pen_bg_dia.png",
        "bg_periods": {"amanhecer": "pen_bg_amanhecer.png", "dia": "pen_bg_dia.png",
                       "entardecer": "pen_bg_entardecer.png", "noite": "pen_bg_noite.png"},
        "period_tint": L.TINT,
        "lantern_on_periods": ["entardecer", "noite"],
        "walk_area": [48, 100, 650, 400],
        "panel": L.PANEL,
        "anchors": "x,y = centro-base do objeto (ancora no json do sheet); slots = offsets (dx,dy) do centro-base do gato; "
                   "layer floor = abaixo de todos os gatos, sorted = ordenar por y; gato em slot e desenhado SEMPRE depois do objeto. "
                   "zones.*.rect = [x,y,w,h]",
        "zones": L.ZONES,
        "ambient": ambient(),
    }
    with open(os.path.join(PEN, "pen.json"), "w") as f:
        json.dump(pen, f, indent=1)


def sheet(js):
    j = json.load(open(os.path.join(PEN, js)))
    return j, Image.open(os.path.join(PEN, j["image"])).convert("RGBA")


def fr(sh, meta, an, i):
    w, hh = meta["frame"]
    m = meta["anims"][an]
    i %= m["frames"]
    return sh.crop((i * w, m["row"] * hh, (i + 1) * w, (m["row"] + 1) * hh))


def periods():
    names = ["amanhecer", "dia", "entardecer", "noite"]
    im = Image.new("RGB", (960, 540), (20, 20, 20))
    for i, n in enumerate(names):
        b = Image.open(os.path.join(PEN, f"pen_bg_{n}.png")).convert("RGB").resize((480, 270), Image.BILINEAR)
        im.paste(b, ((i % 2) * 480, (i // 2) * 270))
        ImageDraw.Draw(im).text(((i % 2) * 480 + 6, (i // 2) * 270 + 4), n, fill=(255, 255, 255))
    im.save(os.path.join(REP, "preview_pen_v4_periodos.png"))


def cena(period="dia", frame=0, out="preview_pen_v4_cena.png"):
    pen = json.load(open(os.path.join(PEN, "pen.json")))
    oj, osh = sheet("objects.json")
    aj, ash = sheet("ambient.json")
    cj, csh = sheet("cats_pen.json")
    img = Image.open(os.path.join(PEN, pen["bg_periods"][period])).convert("RGBA")
    tint = tuple(pen["period_tint"][period])

    def tinted(im):
        if tint == (255, 255, 255):
            return im
        r, g, b, a = im.split()
        r = r.point(lambda v: v * tint[0] // 255)
        g = g.point(lambda v: v * tint[1] // 255)
        b = b.point(lambda v: v * tint[2] // 255)
        return Image.merge("RGBA", (r, g, b, a))

    def cat(cid, an, f, flip):
        m = cj["anims"][cid][an]
        f %= m["frames"]
        im = csh.crop((f * 64, m["row"] * 64, f * 64 + 64, m["row"] * 64 + 64))
        return tinted(im.transpose(Image.FLIP_LEFT_RIGHT) if flip else im)

    plan = {  # (zona, idx obj, slot) -> (gato, anim, flip, objeto_anim)
        ("adultos", 0, 0): ("maine-coon", "sleep", False, None), ("adultos", 0, 1): ("vira-lata", "play", False, None),
        ("adultos", 1, 0): ("siames", "sleep", False, None),
        ("adultos", 2, 0): ("persa", "sleep", False, "enter3"), ("adultos", 3, 0): ("vira-lata", "sleep", True, "enter3"),
        ("adultos", 4, 0): ("siames", "sleep", False, "enter3"),
        ("adultos", 7, 0): ("siames", "play", False, "use"), ("adultos", 10, 0): ("maine-coon", "play", True, "use"),
        ("breed", 0, 0): ("siames", "sleep", False, "enter3"), ("breed", 0, 1): ("persa", "sleep", True, "enter3"),
        ("breed", 1, 0): ("vira-lata", "sleep", False, "enter3"), ("breed", 1, 1): ("maine-coon", "sleep", True, "enter3"),
        ("filhotes", 0, 0): ("siames_filhote", "sleep", False, "enter3"), ("filhotes", 0, 1): ("vira-lata_filhote", "sleep", True, "enter3"),
        ("filhotes", 2, 0): ("vira-lata_filhote", "play", False, "use"), ("filhotes", 1, 0): ("persa_filhote", "sleep", False, "enter3"), ("filhotes", 4, 0): ("sphynx_filhote", "play", False, "use"),
    }
    floor, sorted_, top = [], [], []
    for zn, z in pen["zones"].items():
        for i, o in enumerate(z["objects"]):
            meta = oj["objects"][o["kind"]]
            an = "idle"
            used = [plan[k] for k in plan if k[0] == zn and k[1] == i]
            fi = 0
            if used and used[0][3] == "use" and "use" in meta["anims"]:
                an, fi = "use", frame
            elif used and used[0][3] == "enter3" and "enter" in meta["anims"]:
                an, fi = "enter", 3
            sp = tinted(fr(osh, meta, an, fi))
            (floor if o["layer"] == "floor" else sorted_).append((o["y"], sp, (o["x"] - meta["anchor"][0], o["y"] - meta["anchor"][1])))
            for si, (dx, dy) in enumerate(o["slots"]):
                p = plan.get((zn, i, si))
                if p:
                    top.append((o["y"] + dy + 1000 * (o["layer"] == "sorted" and dy < -20), cat(p[0], p[1], frame + si * 3, p[2]), (o["x"] + dx - 32, o["y"] + dy - 61)))
    walkers = [("sphynx", "walk", 330, 262, False), ("maine-coon", "idle", 200, 222, False),
               ("persa", "walk", 215, 335, True), ("siames", "idle", 90, 380, False),
               ("vira-lata", "walk", 520, 214, False), ("persa_filhote", "walk", 590, 330, True),
               ("maine-coon_filhote", "idle", 600, 410, False), ("siames", "walk", 600, 120, False)]
    loose = []
    for cid, an, x, y, fl in walkers:
        loose.append((y, cat(cid, an, frame, fl), (x - 32, y - 61)))
    for y, sp, pos in floor:
        img.alpha_composite(sp, pos)
    for y, sp, pos in sorted(sorted_ + loose, key=lambda t: t[0]):
        img.alpha_composite(sp, pos)
    for y, sp, pos in top:
        img.alpha_composite(sp, pos)
    for a in pen["ambient"]:
        if "periods" in a and period not in a["periods"]:
            continue
        meta = aj["objects"][a["kind"]]
        an = "idle"
        if a["kind"] == "lanterna":
            an = "on" if period in pen["lantern_on_periods"] else "off"
        sp = fr(ash, meta, an, frame + a.get("phase", 0))
        img.alpha_composite(tinted(sp) if a["kind"] != "vagalumes" else sp, (a["x"] - meta["anchor"][0], a["y"] - meta["anchor"][1]))
    img.convert("RGB").save(os.path.join(REP, out))
    if period == "dia":
        ref = Image.open(os.path.join(PEN, "_referencia_renatho.webp")).convert("RGB")
        rr = ref.resize((960, int(ref.height * 960 / ref.width)), Image.LANCZOS)
        both = Image.new("RGB", (960, 540 + rr.height + 8), (20, 20, 20))
        both.paste(img.convert("RGB"), (0, 0))
        both.paste(rr, (0, 548))
        both.save(os.path.join(REP, "preview_pen_v4_cena_vs_referencia.png"))


def objetos():
    oj, osh = sheet("objects.json")
    aj, ash = sheet("ambient.json")
    S = 4
    rows = []
    for src, sh in ((oj, osh), (aj, ash)):
        for kind, meta in src["objects"].items():
            for an, m in meta["anims"].items():
                frames = [fr(sh, meta, an, i) for i in range(m["frames"])]
                bb = None
                for f in frames:
                    b = f.getbbox()
                    if b:
                        bb = b if bb is None else (min(bb[0], b[0]), min(bb[1], b[1]), max(bb[2], b[2]), max(bb[3], b[3]))
                bb = bb or (0, 0, 8, 8)
                rows.append((f"{kind} / {an} ({m['frames']}q @{m['fps']}fps{'' if m.get('loop', True) else ', one-shot'})", [f.crop(bb) for f in frames], bb))
    colw = 130 * S // 2
    # layout: cada linha = legenda + quadros lado a lado com escala 2 se largura grande
    out_rows = []
    maxw = 1900
    for lab, frs, bb in rows:
        sc = S if (bb[2] - bb[0]) * S * len(frs) <= maxw else 2
        if (bb[2] - bb[0]) * sc * len(frs) > maxw:
            sc = 1
        w = (bb[2] - bb[0]) * sc
        hh = (bb[3] - bb[1]) * sc
        out_rows.append((lab, frs, sc, w, hh))
    total_h = sum(r[4] + 22 for r in out_rows) + 10
    img = Image.new("RGBA", (maxw + 20, total_h), (92, 130, 76, 255))
    d = ImageDraw.Draw(img)
    y = 6
    for lab, frs, sc, w, hh in out_rows:
        d.text((8, y), lab, fill=(255, 255, 255, 255))
        y += 16
        x = 8
        for f in frs:
            big = f.resize((f.width * sc, f.height * sc), Image.NEAREST)
            img.alpha_composite(big, (x, y))
            x += w + 4
        y += hh + 6
    img.convert("RGB").save(os.path.join(REP, "preview_pen_v4_objetos.png"))


if __name__ == "__main__":
    what = sys.argv[1:] or ["pen", "periodos", "cena", "objetos"]
    if "pen" in what:
        write_pen()
    if "periodos" in what:
        periods()
    if "cena" in what:
        cena()
    if "objetos" in what:
        objetos()
