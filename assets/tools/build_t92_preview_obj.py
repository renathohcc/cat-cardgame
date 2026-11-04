"""T9.2: preview de todas as anims de objetos e ambiente a 3x, legendadas (quadros recortados pela uniao dos bboxes)."""
import json
import os

from PIL import Image, ImageDraw

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PEN = os.path.join(ROOT, "assets", "pen")
OUTP = os.path.join(ROOT, "reports", "arte", "preview_pen_v2_objetos.png")


def main():
    S = 3
    blocks = []
    for js, png in (("objects.json", "objects.png"), ("ambient.json", "ambient.png")):
        j = json.load(open(os.path.join(PEN, js)))
        sheet = Image.open(os.path.join(PEN, png)).convert("RGBA")
        for k, v in j["objects"].items():
            fw, fh = v["frame"]
            for an, m in v["anims"].items():
                frs = [sheet.crop((f * fw, m["row"] * fh, (f + 1) * fw, (m["row"] + 1) * fh)) for f in range(m["frames"])]
                bb = None
                for fr in frs:
                    b = fr.getbbox()
                    if b:
                        bb = b if bb is None else (min(bb[0], b[0]), min(bb[1], b[1]), max(bb[2], b[2]), max(bb[3], b[3]))
                bb = (max(bb[0] - 2, 0), max(bb[1] - 2, 0), min(bb[2] + 2, fw), min(bb[3] + 2, fh))
                blocks.append((f"{k} / {an}  ({m['frames']} quadros, {m['fps']} fps)", [f.crop(bb) for f in frs], bb))
    colw = 4 * 96 * S + 20
    ncol = 2
    heights = [0] * ncol
    place = []
    for lab, frs, bb in blocks:
        w, hh = bb[2] - bb[0], bb[3] - bb[1]
        per = max(1, (colw - 8) // (w * S + 6))
        rows = (len(frs) + per - 1) // per
        c = heights.index(min(heights))
        place.append((c, heights[c], per))
        heights[c] += 16 + rows * (hh * S + 6) + 6
    img = Image.new("RGBA", (ncol * colw, max(heights) + 8), (42, 51, 80, 255))
    d = ImageDraw.Draw(img)
    for (lab, frs, bb), (c, y0, per) in zip(blocks, place):
        w, hh = bb[2] - bb[0], bb[3] - bb[1]
        x0 = c * colw + 8
        d.text((x0, y0 + 2), lab, fill=(255, 255, 255, 255))
        for f, fr in enumerate(frs):
            bx = x0 + (f % per) * (w * S + 6)
            by = y0 + 16 + (f // per) * (hh * S + 6)
            d.rectangle((bx, by, bx + w * S - 1, by + hh * S - 1), fill=(30, 38, 62, 255))
            img.alpha_composite(fr.resize((w * S, hh * S), Image.NEAREST), (bx, by))
    img.convert("RGB").save(OUTP)
    print(img.size)


if __name__ == "__main__":
    main()
