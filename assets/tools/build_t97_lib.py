"""T9.7: biblioteca de desenho pixel (numpy) para o quintal. Tudo em grade 1:1, so cores da paleta PEN,
sem anti-aliasing, sem resize. Mascaras booleanas + sombreamento em 3 tons (luz cima-esquerda)."""
import numpy as np
from PIL import Image, ImageDraw

PAL = {
    "outline": "#3b2a38",
    "grass_dark": "#5c9650", "grass": "#79b45a", "grass_light": "#9ccd6c",
    "bush_dark": "#2f6a46", "bush": "#3f8a52", "bush_light": "#5fae5c",
    "dirt_dark": "#b98a5c", "dirt": "#d4a874", "dirt_light": "#e8c996",
    "path_dark": "#c9b085", "path": "#e4d2a6", "path_light": "#f3e6c4", "pebble": "#a79a8e",
    "wood_dark": "#683f33", "wood": "#a8663c", "wood_light": "#dc9a5c",
    "rose_dark": "#b4506c", "rose": "#e07890", "rose_light": "#f4a8b8",
    "teal_dark": "#2f6670", "teal": "#4a9496", "teal_light": "#86c4be",
    "cream_dark": "#d0aa78", "cream": "#f0d7a4", "cream_light": "#fbf3e2",
    "stone_dark": "#7a7088", "stone": "#a8a0b8", "stone_light": "#d4cee0",
    "yellow": "#ffd84a", "flower_pink": "#f09aa8", "flower_red": "#d9524a",
}


def rgb(name):
    h = PAL[name]
    return (int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16))


PAL_RGB = {rgb(k): k for k in PAL}


class Canvas:
    """Tela RGBA de pixels; `m` = mascara bool (H, W)."""

    def __init__(self, w, h, fill=None):
        self.w, self.h = w, h
        self.a = np.zeros((h, w, 4), np.uint8)
        if fill:
            self.a[:, :] = (*rgb(fill), 255)

    def blank(self):
        return np.zeros((self.h, self.w), bool)

    def paint(self, m, color, alpha=255):
        self.a[m] = (*rgb(color), alpha)

    def rect(self, x0, y0, x1, y1, color, alpha=255):
        """[x0,x1) x [y0,y1)"""
        x0, y0, x1, y1 = max(0, x0), max(0, y0), min(self.w, x1), min(self.h, y1)
        if x1 > x0 and y1 > y0:
            self.a[y0:y1, x0:x1] = (*rgb(color), alpha)

    def px(self, x, y, color, alpha=255):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.a[y, x] = (*rgb(color), alpha)

    def paste(self, other, x, y):
        """cola `other` (Canvas) em (x,y): pixels com alpha>0 substituem."""
        for yy in range(other.h):
            ty = y + yy
            if not 0 <= ty < self.h:
                continue
            row = other.a[yy]
            for xx in np.nonzero(row[:, 3])[0]:
                tx = x + int(xx)
                if 0 <= tx < self.w:
                    self.a[ty, tx] = row[xx]

    def image(self):
        return Image.fromarray(self.a, "RGBA")


# ------------------------------------------------------------------ mascaras
def m_rect(c, x, y, w, h):
    m = c.blank()
    m[max(0, y):max(0, y + h), max(0, x):max(0, x + w)] = True
    return m


def m_ell(c, x, y, w, h):
    """elipse inscrita no retangulo (x,y,w,h), sem AA."""
    yy, xx = np.mgrid[0:c.h, 0:c.w]
    cx, cy = x + w / 2.0, y + h / 2.0
    return (((xx + 0.5 - cx) / (w / 2.0)) ** 2 + ((yy + 0.5 - cy) / (h / 2.0)) ** 2) <= 1.0


def m_rrect(c, x, y, w, h, r):
    m = m_rect(c, x + r, y, w - 2 * r, h) | m_rect(c, x, y + r, w, h - 2 * r)
    for cx, cy in ((x, y), (x + w - 2 * r, y), (x, y + h - 2 * r), (x + w - 2 * r, y + h - 2 * r)):
        m |= m_ell(c, cx, cy, 2 * r, 2 * r)
    return m


def m_poly(c, pts):
    im = Image.new("L", (c.w, c.h), 0)
    ImageDraw.Draw(im).polygon(pts, fill=255)
    return np.asarray(im) > 0


def shift(m, dx, dy):
    out = np.zeros_like(m)
    h, w = m.shape
    xs0, xs1 = max(0, -dx), min(w, w - dx)
    ys0, ys1 = max(0, -dy), min(h, h - dy)
    if xs1 > xs0 and ys1 > ys0:
        out[ys0 + dy:ys1 + dy, xs0 + dx:xs1 + dx] = m[ys0:ys1, xs0:xs1]
    return out


def dilate(m):
    return m | shift(m, 1, 0) | shift(m, -1, 0) | shift(m, 0, 1) | shift(m, 0, -1)


def outline_of(m):
    return dilate(m) & ~m


def shaded(c, m, base, light, dark, depth=2, outline="outline", flip=False):
    """pinta `m` em 3 tons (luz cima-esquerda; flip inverte, p/ interiores) e contorno de 1 px."""
    lit = m & ~shift(m, depth, depth)
    shd = m & ~shift(m, -depth, -depth)
    if flip:
        lit, shd = shd, lit
    c.paint(m, base)
    c.paint(lit & ~shd, light)
    c.paint(shd, dark)
    if outline:
        c.paint(outline_of(m), outline)


def flat(c, m, color, outline="outline"):
    c.paint(m, color)
    if outline:
        c.paint(outline_of(m), outline)


def shadow(c, x, y, w, h, alpha=70):
    """sombra de contato (elipse achatada, cor do contorno com alpha): so onde ainda esta vazio."""
    m = m_ell(c, x, y, w, h) & (c.a[..., 3] == 0)
    c.paint(m, "outline", alpha)


def bitmap(c, x, y, rows, colors):
    """rows: lista de strings; cada caractere mapeia em `colors` ('.' = nada)."""
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch != "." and ch in colors:
                c.px(x + i, y + j, colors[ch])


def pal_check(arr):
    """cores RGB (alpha>0) fora da paleta."""
    a = np.asarray(arr)
    if a.shape[2] == 4:
        a = a[a[..., 3] > 0][:, :3]
    else:
        a = a.reshape(-1, 3)
    cols = {tuple(int(v) for v in t) for t in np.unique(a, axis=0)} if len(a) else set()
    return sorted(cols - set(PAL_RGB))
