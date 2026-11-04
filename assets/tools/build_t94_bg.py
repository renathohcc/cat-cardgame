"""T9.4: cenario do quintal 960x540 em 4 periodos (mesma geometria). Pillow + numpy, sem IA.
Uso: python assets/tools/build_t94_bg.py   (gera pen_bg_*.png)"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(__file__))
import build_t94_layout as L  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PEN = os.path.join(ROOT, "assets", "pen")
W, H = 960, 540


def c(x, a=255):
    return tuple(int(x[i:i + 2], 16) for i in (1, 3, 5)) + (a,)


OUT = c("#3b2a38")
GR = [c(x) for x in ("#558540", "#61934a", "#6c9f52", "#79ab5a")]          # grama (escuro..claro)
GRL = [c(x) for x in ("#67994a", "#74a653", "#81b25c", "#8fbf66")]         # grama clara (filhotes)
DT = [c(x) for x in ("#c09058", "#cc9d64", "#d6aa72", "#deb77f")]          # terra
DTP = [c(x) for x in ("#b88858", "#c3935f", "#cd9f69", "#d6ab74")]         # patio
WOOD = [c(x) for x in ("#4e2f22", "#7a4c2e", "#9a6638", "#bc8650")]        # madeira
STONE = [c(x) for x in ("#6b6460", "#8f887e", "#aca597", "#c8c1b0")]
LEAF = [c(x) for x in ("#244a2c", "#356a38", "#4a8a44", "#6aa850", "#8ec462")]
LEAFO = c("#243628")
WHITE = [c(x) for x in ("#b8a98c", "#d8cdb2", "#efe6d0", "#fffaf0")]


def vnoise(w, h, scale, seed):
    r = np.random.default_rng(seed)
    g = r.random((h // scale + 3, w // scale + 3)).astype(np.float32)
    im = Image.fromarray((g * 255).astype(np.uint8)).resize(((w // scale + 3) * scale, (h // scale + 3) * scale), Image.BICUBIC)
    return np.asarray(im, dtype=np.float32)[:h, :w] / 255.0


def quant(v, pal, th):
    out = np.zeros(v.shape + (4,), np.uint8)
    idx = np.zeros(v.shape, int)
    for t in th:
        idx += (v > t)
    for i, col in enumerate(pal):
        out[idx == i] = col
    return out


class Scene:
    def __init__(self, shadow):
        self.sh = shadow  # (dx por altura, dy, escala x, forca)
        self.arr = np.zeros((H, W, 4), np.uint8)
        self.arr[..., 3] = 255
        self.casters = []
        self.rng = np.random.default_rng(7)

    def image(self):
        return Image.fromarray(self.arr, "RGBA")

    def commit(self, im):
        self.arr = np.asarray(im).copy()

    def draw(self):
        im = self.image()
        return im, ImageDraw.Draw(im)

    # ---------- chao ----------
    def ground(self):
        n = 0.55 * vnoise(W, H, 30, 1) + 0.45 * vnoise(W, H, 10, 2)
        n += 0.12 * vnoise(W, H, 4, 3)
        base = quant(n, GR, (0.40, 0.52, 0.64))
        lite = quant(n, GRL, (0.40, 0.52, 0.64))
        self.arr[...] = base
        fr = L.FILH_BOX
        m = np.zeros((H, W), bool)
        m[fr[1]:fr[1] + fr[3], fr[0]:fr[0] + fr[2]] = True
        self.arr[m] = lite[m]
        d_im, d = self.draw()
        for _ in range(520):
            x, y = int(self.rng.integers(0, 736)), int(self.rng.integers(96, 520))
            dark = GR[0] if self.rng.random() < .6 else GR[3]
            d.line((x, y, x, y - 2), fill=dark)
            d.point((x + 1, y - 1), fill=dark)
            d.point((x - 1, y - 1), fill=dark)
        self.commit(d_im)

    def dirt_mask(self, rects, rough=3):
        m = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(m)
        for r in rects:
            d.rectangle(r, fill=255)
        m = m.filter(ImageFilter.GaussianBlur(rough))
        a = np.asarray(m, np.float32) / 255
        a = a + (vnoise(W, H, 6, 11) - 0.5) * 0.7
        return a > 0.5

    def dirt(self, rects, pal=DT, seed=5):
        mk = self.dirt_mask(rects)
        n = 0.5 * vnoise(W, H, 14, seed) + 0.5 * vnoise(W, H, 5, seed + 1)
        col = quant(n, pal, (0.38, 0.55, 0.72))
        er = np.asarray(Image.fromarray((mk * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3))) > 0
        edge = mk & ~er
        self.arr[mk] = col[mk]
        self.arr[edge] = pal[0]
        d_im, d = self.draw()
        ys, xs = np.nonzero(mk)
        for i in self.rng.choice(len(xs), min(90, len(xs)), replace=False):
            x, y = int(xs[i]), int(ys[i])
            if 0 < x < 735:
                d.point((x, y), fill=pal[0])
                d.point((x + 1, y), fill=pal[1])
        self.commit(d_im)

    def shadows(self):
        dxh, dy, sx, k = self.sh
        m = Image.new("L", (W, H), 0)
        d = ImageDraw.Draw(m)
        for (cx, by, rx, ht) in self.casters:
            cxs = cx + dxh * ht
            d.ellipse((cxs - rx * sx, by + dy - rx * .35, cxs + rx * sx, by + dy + rx * .35), fill=255)
        a = np.asarray(m.filter(ImageFilter.GaussianBlur(0.8)), np.float32) / 255 * k
        for ch in range(3):
            self.arr[..., ch] = (self.arr[..., ch] * (1 - a * 0.55)).astype(np.uint8)

    # ---------- folhagem ----------
    def foliage(self, circles, seed=0, pal=LEAF, spots=1.0):
        rng = np.random.default_rng(abs(int(seed)))
        pad = 3
        x0 = int(max(min(cx - r for cx, cy, r in circles) - pad, 0))
        y0 = int(max(min(cy - r for cx, cy, r in circles) - pad, 0))
        x1 = int(min(max(cx + r for cx, cy, r in circles) + pad, W))
        y1 = int(min(max(cy + r for cx, cy, r in circles) + pad, H))
        w, h = x1 - x0, y1 - y0
        if w <= 0 or h <= 0:
            return
        mi = Image.new("L", (w, h), 0)
        md = ImageDraw.Draw(mi)
        for cx, cy, r in circles:
            md.ellipse((cx - r - x0, cy - r - y0, cx + r - x0, cy + r - y0), fill=255)
        m = np.asarray(mi) > 0
        dil = np.asarray(mi.filter(ImageFilter.MaxFilter(3))) > 0

        def sh(a, dx, dy):
            o = np.zeros_like(a)
            ys, xs = slice(max(dy, 0), h + min(dy, 0)), slice(max(dx, 0), w + min(dx, 0))
            yd, xd = slice(max(-dy, 0), h + min(-dy, 0)), slice(max(-dx, 0), w + min(-dx, 0))
            o[ys, xs] = a[yd, xd]
            return o
        light = m & ~sh(m, 3, 4)
        light2 = m & ~sh(m, 6, 8)
        dark = m & ~sh(m, -3, -4)
        dark2 = m & ~sh(m, -7, -8)
        out = np.zeros((h, w, 4), np.uint8)
        out[m] = pal[2]
        out[dark] = pal[1]
        out[dark2] = pal[0]
        out[light2 & m & ~dark] = pal[3]
        out[light & ~dark] = pal[4]
        mi2 = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        dd = ImageDraw.Draw(mi2)
        for cx, cy, r in circles:
            for _ in range(int(r * r / 14 * spots)):
                ang, rad = rng.random() * 6.283, math.sqrt(rng.random()) * (r - 3)
                px, py = cx - x0 + rad * math.cos(ang), cy - y0 + rad * math.sin(ang)
                up = (math.cos(ang) * -0.6 - math.sin(ang) * 0.8)
                if rng.random() < 0.5 + 0.4 * up:
                    col = pal[3] if rng.random() < .8 else pal[4]
                else:
                    col = pal[1]
                dd.ellipse((px - 2, py - 1, px + 2, py + 1), fill=col)
                dd.point((px, py - 2), fill=col)
        spot = np.asarray(mi2)
        sm = (spot[..., 3] > 0) & m & ~dark2
        out[sm] = spot[sm]
        out[dil & ~m] = LEAFO
        cur = self.arr[y0:y1, x0:x1]
        a = out[..., 3] > 0
        cur[a] = out[a]

    def tree(self, cx, by, s=1.0, seed=0):
        self.casters.append((cx, by + 2, 34 * s, 30 * s))
        d_im, d = self.draw()
        tw = int(8 * s)
        th = int(26 * s)
        d.rectangle((cx - tw // 2 - 1, by - th, cx + tw // 2 + 1, by), fill=OUT)
        d.rectangle((cx - tw // 2, by - th, cx + tw // 2, by - 1), fill=WOOD[2])
        d.rectangle((cx + tw // 4, by - th, cx + tw // 2, by - 1), fill=WOOD[1])
        d.rectangle((cx - tw // 2, by - th, cx - tw // 2 + 1, by - 1), fill=WOOD[3])
        d.polygon([(cx - tw // 2 - 4, by + 1), (cx - tw // 2, by - 6), (cx + tw // 2, by - 6), (cx + tw // 2 + 4, by + 1)], fill=WOOD[1], outline=OUT)
        self.commit(d_im)
        r = 20 * s
        cy = by - th - 16 * s
        cs = [(cx, cy - 8 * s, r * 1.15), (cx - 20 * s, cy + 4 * s, r * .85), (cx + 21 * s, cy + 3 * s, r * .9),
              (cx - 8 * s, cy + 10 * s, r * .8), (cx + 10 * s, cy + 12 * s, r * .75), (cx - 2 * s, cy - 20 * s, r * .75)]
        self.foliage([(int(a), int(b), int(r_)) for a, b, r_ in cs], seed)

    def bush(self, cx, by, s=1.0, seed=0, flowers=None):
        self.casters.append((cx, by, 18 * s, 8 * s))
        cs = [(cx, by - 12 * s, 12 * s), (cx - 12 * s, by - 7 * s, 9 * s), (cx + 12 * s, by - 7 * s, 9 * s),
              (cx - 4 * s, by - 5 * s, 9 * s), (cx + 5 * s, by - 5 * s, 9 * s)]
        self.foliage([(int(a), int(b), int(r_)) for a, b, r_ in cs], seed, spots=.8)
        if flowers:
            rng = np.random.default_rng(seed + 50)
            d_im, d = self.draw()
            for _ in range(7):
                fx, fy = cx + int(rng.integers(-14, 15) * s), by - int(rng.integers(4, 20) * s)
                d.point((fx, fy), fill=c(flowers))
                d.point((fx + 1, fy), fill=c(flowers))
                d.point((fx, fy - 1), fill=c("#fff6e0"))
            self.commit(d_im)

    def flowers(self, pts, cols=("#fff6e0", "#f4a0b4", "#f2d460", "#b49ae0")):
        d_im, d = self.draw()
        for i, (x, y) in enumerate(pts):
            col = c(cols[i % len(cols)])
            d.point((x, y + 2), fill=GR[0])
            d.point((x, y + 1), fill=GR[0])
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                d.point((x + dx, y + dy), fill=col)
            d.point((x, y), fill=c("#f2d460"))
        self.commit(d_im)

    # ---------- cercas ----------
    def pickets(self, x0, x1, yb, hgt=20, step=9, pal=WOOD, point=True, post_every=0):
        d_im, d = self.draw()
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rectangle((x0, yb + 1, x1, yb + 3), fill=(30, 40, 20, 70))
        d_im.alpha_composite(sh)
        d = ImageDraw.Draw(d_im)
        for ry in (yb - 5, yb - hgt + 6):
            d.rectangle((x0, ry - 1, x1, ry + 2), fill=OUT)
            d.rectangle((x0, ry, x1, ry + 1), fill=pal[1])
            d.line((x0, ry, x1, ry), fill=pal[2])
        x = x0 + 1
        i = 0
        while x + 5 <= x1:
            top = yb - hgt - (3 if (post_every and i % post_every == 0) else 0)
            d.rectangle((x, top + 2, x + 5, yb), fill=OUT)
            if point:
                d.polygon([(x, top + 3), (x + 2, top), (x + 3, top), (x + 5, top + 3)], fill=OUT)
            d.rectangle((x + 1, top + 3, x + 4, yb - 1), fill=pal[2])
            d.rectangle((x + 4, top + 3, x + 4, yb - 1), fill=pal[1])
            d.line((x + 1, top + 3, x + 1, yb - 1), fill=pal[3])
            if point:
                d.point((x + 2, top + 1), fill=pal[3])
                d.point((x + 3, top + 1), fill=pal[2])
            x += step
            i += 1
        self.commit(d_im)

    def wall_tall(self, x, y0, y1, w=12, gap=None):
        d_im, d = self.draw()
        sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sh)
        segs = [(y0, y1)] if not gap else [(y0, gap[0]), (gap[1], y1)]
        for a, b in segs:
            sd.rectangle((x + w + 3, a + 2, x + w + 8, b + 3), fill=(30, 40, 20, 60))
        d_im.alpha_composite(sh)
        d = ImageDraw.Draw(d_im)
        for a, b in segs:
            d.rectangle((x - 1, a, x + w, b), fill=OUT)
            d.rectangle((x, a, x + w - 1, b - 1), fill=WOOD[2])
            d.rectangle((x + w - 4, a, x + w - 1, b - 1), fill=WOOD[1])
            d.rectangle((x, a, x + 1, b - 1), fill=WOOD[3])
            y = a + 8
            while y < b:
                d.line((x, y, x + w - 1, y), fill=WOOD[0])
                d.line((x, y + 1, x + 2, y + 1), fill=WOOD[3])
                y += 12
            d.line((x + 5, a, x + 5, b - 1), fill=WOOD[1])
        ys = list(range(y0 + 2, y1 - 8, 52))
        for a, b in segs:
            ys += [a, b - 12]
        for py in ys:
            if gap and gap[0] - 4 < py < gap[1] - 8:
                continue
            d.rectangle((x - 3, py - 1, x + w + 2, py + 12), fill=OUT)
            d.rectangle((x - 2, py, x + w + 1, py + 10), fill=WOOD[3])
            d.rectangle((x + w - 2, py, x + w + 1, py + 10), fill=WOOD[2])
            d.line((x - 2, py + 10, x + w + 1, py + 10), fill=WOOD[1])
        self.commit(d_im)

    def stone_wall(self, box):
        x, y, w, h = box
        t = 12
        d_im, d = self.draw()

        def blocks(x0, y0, x1, y1, row_h=6):
            d.rectangle((x0, y0, x1, y1), fill=OUT)
            d.rectangle((x0 + 1, y0 + 1, x1 - 1, y1 - 1), fill=STONE[2])
            yy = y0 + 1
            r = 0
            while yy < y1:
                d.line((x0 + 1, yy, x1 - 1, yy), fill=STONE[1])
                xx = x0 + 3 + (r % 2) * 7
                while xx < x1:
                    d.line((xx, yy, xx, min(yy + row_h, y1 - 1)), fill=STONE[1])
                    xx += 14
                yy += row_h
                r += 1
            d.line((x0 + 1, y0 + 1, x1 - 1, y0 + 1), fill=STONE[3])
            d.line((x0 + 1, y1 - 1, x1 - 1, y1 - 1), fill=STONE[0])
        blocks(x, y, x + w, y + t)
        blocks(x, y + t, x + 9, y + h - 14)
        blocks(x + w - 9, y + t, x + w, y + h - 14)
        self.commit(d_im)

    def stone_front(self, box, gate_x=None, gate_w=44):
        x, y, w, h = box
        t = 14
        d_im, d = self.draw()
        yy = y + h - t
        segs = [(x, x + w)] if gate_x is None else [(x, gate_x), (gate_x + gate_w, x + w)]
        for a, b in segs:
            d.rectangle((a, yy, b, y + h), fill=OUT)
            d.rectangle((a + 1, yy + 1, b - 1, y + h - 1), fill=STONE[2])
            d.rectangle((a + 1, yy + 1, b - 1, yy + 3), fill=STONE[3])
            for r, ry in enumerate(range(yy + 4, y + h - 1, 5)):
                d.line((a + 1, ry, b - 1, ry), fill=STONE[1])
                for xx in range(a + 4 + (r % 2) * 7, b - 1, 14):
                    d.line((xx, ry, xx, min(ry + 4, y + h - 2)), fill=STONE[1])
            d.line((a + 1, y + h - 1, b - 1, y + h - 1), fill=STONE[0])
        self.commit(d_im)

    def planter(self, x, y, w=36, flower="#f4a0b4", seed=0):
        d_im, d = self.draw()
        rng = np.random.default_rng(seed)
        for i in range(w // 4):
            fx = x + 2 + i * 4 + int(rng.integers(0, 2))
            d.ellipse((fx - 2, y - 8 + int(rng.integers(0, 3)), fx + 3, y + 1), fill=LEAF[2], outline=LEAFO)
        for i in range(7):
            fx, fy = x + 3 + int(rng.integers(0, w - 6)), y - 8 + int(rng.integers(0, 6))
            col = c(flower) if i % 2 == 0 else c("#fff6e0")
            d.rectangle((fx, fy, fx + 1, fy + 1), fill=col)
            d.point((fx, fy), fill=c("#f2d460"))
        d.rectangle((x - 1, y, x + w, y + 11), fill=OUT)
        d.rectangle((x, y + 1, x + w - 1, y + 10), fill=WOOD[2])
        d.rectangle((x, y + 1, x + w - 1, y + 3), fill=WOOD[3])
        d.rectangle((x, y + 8, x + w - 1, y + 10), fill=WOOD[1])
        for px in range(x + 8, x + w - 2, 9):
            d.line((px, y + 4, px, y + 9), fill=WOOD[0])
        self.commit(d_im)

    def gate_arch(self, x, y, w=44, h=30):
        d_im, d = self.draw()
        d.rectangle((x - 1, y + 6, x + w, y + h), fill=OUT)
        d.pieslice((x - 1, y - 1, x + w, y + 22), 180, 360, fill=OUT)
        d.rectangle((x, y + 8, x + w - 1, y + h - 1), fill=WOOD[2])
        d.pieslice((x, y, x + w - 1, y + 20), 180, 360, fill=WOOD[2])
        for px in range(x + 3, x + w - 1, 6):
            d.line((px, y + 4 if abs(px - x - w // 2) < w // 2 - 4 else y + 10, px, y + h - 1), fill=WOOD[0])
        for px in range(x + 1, x + w - 1, 6):
            d.line((px, y + 6, px, y + h - 1), fill=WOOD[3])
        d.line((x, y + 12, x + w - 1, y + 12), fill=WOOD[0])
        d.line((x, y + h - 8, x + w - 1, y + h - 8), fill=WOOD[0])
        d.rectangle((x + w // 2 - 1, y + 14, x + w // 2 + 1, y + 16), fill=c("#e8c46a"))
        self.commit(d_im)

    def post_block(self, x, y, w=8, h=20, pal=STONE):
        d_im, d = self.draw()
        d.rectangle((x - 1, y - 1, x + w, y + h), fill=OUT)
        d.rectangle((x, y, x + w - 1, y + h - 1), fill=pal[2])
        d.rectangle((x, y, x + w - 1, y + 2), fill=pal[3])
        d.rectangle((x + w - 3, y + 3, x + w - 1, y + h - 1), fill=pal[1])
        self.commit(d_im)

    def pond(self, cx, cy, rx=46, ry=24):
        self.casters.append((cx, cy + ry, rx + 14, 4))
        d_im, d = self.draw()
        rimx, rimy = rx + 9, ry + 8
        d.ellipse((cx - rimx - 1, cy - rimy - 1, cx + rimx + 1, cy + rimy + 4), fill=OUT)
        d.ellipse((cx - rimx, cy - rimy, cx + rimx, cy + rimy + 3), fill=STONE[0])
        d.ellipse((cx - rimx + 1, cy - rimy + 1, cx + rimx - 1, cy + rimy), fill=STONE[2])
        rng = np.random.default_rng(3)
        for a in np.linspace(0, 2 * math.pi, 22, endpoint=False):
            px, py = cx + (rx + 5) * math.cos(a), cy + (ry + 4) * math.sin(a)
            r = int(rng.integers(4, 6))
            d.ellipse((px - r - 1, py - r + 1, px + r + 1, py + r + 3), fill=OUT)
            d.ellipse((px - r, py - r, px + r, py + r + 1), fill=STONE[1] if math.sin(a) > 0 else STONE[2])
            d.line((px - r + 1, py - r + 1, px + 1, py - r + 1), fill=STONE[3])
        d.ellipse((cx - rx - 1, cy - ry - 1, cx + rx + 1, cy + ry + 1), fill=c("#2a4a6a"))
        d.ellipse((cx - rx, cy - ry + 1, cx + rx, cy + ry), fill=c("#3f7fb0"))
        d.ellipse((cx - rx + 4, cy - ry + 3, cx + rx - 3, cy + ry - 4), fill=c("#4f95c4"))
        d.ellipse((cx - rx + 10, cy - ry + 5, cx + rx - 14, cy + ry - 10), fill=c("#6bb0d8"))
        for lx, ly in ((cx + 18, cy + 3), (cx - 22, cy + 8)):
            d.ellipse((lx - 6, ly - 3, lx + 6, ly + 3), fill=LEAFO)
            d.ellipse((lx - 5, ly - 2, lx + 5, ly + 2), fill=LEAF[3])
            d.line((lx, ly, lx + 5, ly - 1), fill=c("#4f95c4"))
        d.point((cx + 18, cy + 1), fill=c("#f4a0b4"))
        self.commit(d_im)

    def path_stones(self, pts):
        d_im, d = self.draw()
        for x, y in pts:
            d.ellipse((x - 6, y - 3, x + 6, y + 3), fill=OUT)
            d.ellipse((x - 5, y - 3, x + 5, y + 2), fill=STONE[2])
            d.line((x - 4, y - 2, x + 1, y - 2), fill=STONE[3])
        self.commit(d_im)

    def tuft_cluster(self, x, y, n=5, seed=0):
        rng = np.random.default_rng(seed)
        d_im, d = self.draw()
        for _ in range(n):
            gx, gy = x + int(rng.integers(-5, 6)), y + int(rng.integers(-2, 3))
            for k in range(3):
                d.line((gx + k - 1, gy, gx + (k - 1) * 2, gy - 5 - int(rng.integers(0, 3))), fill=GR[0] if k != 1 else GR[3])
        self.commit(d_im)


def build_scene(shadow):
    s = Scene(shadow)
    s.ground()
    s.dirt([(L.PATH_X[0], 80, L.PATH_X[1], 492), (L.PATH_X[0], 276, 735, 292), (222, 486, 244, 540)], DT, 21)
    cx, cy, cw, ch = L.CASAIS_BOX
    s.dirt([(cx + 6, cy + 10, cx + cw - 6, cy + ch - 8)], DTP, 31)
    s.path_stones([(584, 280), (598, 284), (612, 281)])
    rng = np.random.default_rng(2)
    for x in range(-10, 760, 46):
        s.foliage([(x + int(rng.integers(-4, 5)), 38 + int(rng.integers(-6, 7)), 24), (x + 18, 44, 20), (x - 14, 50, 18)], x)
    for x in range(-16, 760, 46):
        s.foliage([(x + 20, 14, 26)], x + 5)
    for y in range(80, 540, 52):
        s.foliage([(8, y, 24), (24, y + 20, 18), (-4, y + 24, 22)], y)
    for y in range(60, 540, 48):
        s.foliage([(752, y, 26), (734, y + 22, 22), (780, y + 16, 24)], y + 3)
    s.pickets(40, 450, 96, 22, 9, post_every=6)
    s.pickets(460, 740, 80, 22, 9, post_every=6)
    s.pickets(40, 450, 512, 20, 9, post_every=6)
    s.pickets(460, 740, 504, 20, 9, post_every=6)
    s.wall_tall(L.FENCE_X, 96, 508, 12, gap=L.GATE_Y)
    for gy in (L.GATE_Y[0] - 14, L.GATE_Y[1] - 2):
        s.post_block(L.FENCE_X - 3, gy, 16, 16, WOOD)
    s.stone_wall(L.CASAIS_BOX)
    s.stone_front(L.CASAIS_BOX, gate_x=cx + 98, gate_w=48)
    s.gate_arch(cx + 100, cy + ch - 28, 44, 26)
    s.post_block(cx + 90, cy + ch - 30, 9, 28)
    s.post_block(cx + 146, cy + ch - 30, 9, 28)
    s.planter(cx + 14, cy + 6, 40, "#f4a0b4", 1)
    s.planter(cx + 120, cy + 6, 40, "#f2d460", 2)
    s.planter(cx + 196, cy + 6, 36, "#fff6e0", 3)
    s.planter(cx + 22, cy + ch - 26, 36, "#f4a0b4", 4)
    s.planter(cx + 188, cy + ch - 26, 36, "#b49ae0", 5)
    fx, fy, fw, fh = L.FILH_BOX
    s.pickets(fx, fx + fw, fy + 14, 13, 10, pal=WHITE, point=False)
    s.pickets(fx, fx + fw, fy + fh, 13, 10, pal=WHITE, point=False)
    d_im, d = s.draw()
    for px in (fx, fx + fw - 4):
        d.rectangle((px - 1, fy + 4, px + 5, fy + fh), fill=OUT)
        d.rectangle((px, fy + 5, px + 4, fy + fh - 1), fill=WHITE[2])
        d.rectangle((px + 3, fy + 5, px + 4, fy + fh - 1), fill=WHITE[1])
        d.line((px, fy + 5, px, fy + fh - 1), fill=WHITE[3])
        for ry in range(fy + 20, fy + fh - 8, 30):
            d.rectangle((px - 1, ry, px + 5, ry + 8), fill=OUT)
            d.rectangle((px, ry + 1, px + 4, ry + 7), fill=WHITE[2])
    s.commit(d_im)
    s.post_block(204, 480, 9, 34, WOOD)
    s.post_block(250, 480, 9, 34, WOOD)
    s.gate_arch(212, 484, 36, 28)
    s.tree(*L.TREE, 1.45, 9)
    s.tree(52, 150, .62, 11)
    s.pond(L.POND[0], L.POND[1])
    s.bush(66, 262, 1.0, 4, "#c8a0e8")
    s.bush(418, 126, .9, 5, "#fff6e0")
    s.bush(418, 464, 1.0, 6, "#f4a0b4")
    s.bush(196, 470, .8, 7, "#b49ae0")
    s.bush(496, 306, .8, 8, "#f4a0b4")
    s.bush(716, 308, .8, 9, "#fff6e0")
    s.bush(716, 470, .8, 10, "#f2d460")
    s.flowers([(120, 150), (170, 262), (330, 240), (60, 400), (404, 392), (312, 340), (240, 270), (346, 130),
               (520, 400), (690, 396), (628, 340), (560, 330)])
    for i, (x, y) in enumerate([(150, 340), (80, 210), (350, 300), (230, 150), (320, 420), (390, 210), (580, 420), (690, 360)]):
        s.tuft_cluster(x, y, 4, i)
    s.shadows()
    return s


GRADE = {"dia": (1.0, 1.0, 1.0, (0, 0, 0)), "amanhecer": (0.85, 1.0, 1.05, (0.05, 0.02, 0.03)),
         "entardecer": (0.7, 0.95, 1.0, (0.06, 0.0, 0.05)), "noite": (0.45, 0.8, 1.2, (0.02, 0.035, 0.10))}


def grade(img, period):
    """dessatura parcial + tint por multiplicacao (igual a L.TINT para sprites) + levantar sombras."""
    a = np.asarray(img.convert("RGB"), np.float32) / 255.0
    sat, gam, gain, lift = GRADE[period]
    lum = (a * np.array([0.3, 0.59, 0.11], np.float32)).sum(-1, keepdims=True)
    a = lum + (a - lum) * sat
    a = np.clip(a, 0, 1) ** gam * gain
    t = np.array(L.TINT[period], np.float32) / 255.0
    out = a * t + np.array(lift, np.float32) * (1 - a)
    yy = np.linspace(0, 1, H)[:, None, None]
    xx = np.linspace(0, 1, W)[None, :, None]
    if period == "amanhecer":
        out = out + np.array([0.08, 0.03, 0.0]) * (1 - yy) + np.array([0.06, 0.03, 0.0]) * xx
    elif period == "entardecer":
        out = out + np.array([0.08, 0.02, -0.02]) * (1 - xx) + np.array([0.0, 0.0, 0.04]) * yy
    out = np.clip(out, 0, 1)
    f = np.clip((xx - 720 / W) / (30 / W), 0, 1)
    out = out * (1 - f * 0.45)
    return Image.fromarray((out * 255).astype(np.uint8), "RGB")


SHADOW = {"dia": (0.35, 6, 1.0, 0.6), "amanhecer": (-0.9, 3, 1.5, 0.8), "entardecer": (0.9, 3, 1.5, 0.85), "noite": (0.1, 5, 1.1, 0.5)}


def main(only=None):
    names = {"dia": "pen_bg_dia.png", "amanhecer": "pen_bg_amanhecer.png", "entardecer": "pen_bg_entardecer.png", "noite": "pen_bg_noite.png"}
    for per, fn in names.items():
        if only and per not in only:
            continue
        sc = build_scene(SHADOW[per])
        grade(sc.image(), per).save(os.path.join(PEN, fn))
        print(per)


if __name__ == "__main__":
    main(sys.argv[1:] or None)
