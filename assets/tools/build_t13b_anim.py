"""T13.3b: animacao de desbloqueio mais rica (mesmo contrato do unlock_anim.json: 8 quadros 96x96, 20 fps, 400 ms, sem loop,
origem no centro). Reaproveita tapumes/mato/folhas de build_t13_lock.build_anim e soma nuvens de poeira, anel de brilho e
estrelinhas. Alpha 0/255, so paleta PEN."""
from __future__ import annotations
import math, random, sys
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_t13_lock as L  # noqa: E402

C, O, CLEAR, FW, FH, NF = L.C, L.O, L.CLEAR, L.FW, L.FH, L.NF
def px(im, x, y, c):
    L.px(im, int(round(x)), int(round(y)), c)


def puff(im, x, y, r, f):
    """nuvem de poeira: miolo claro, sombra embaixo/direita, borda tracejada ao dissipar."""
    for yy in range(-r, r + 1):
        for xx in range(-r, r + 1):
            d2 = xx * xx + yy * yy
            if d2 > r * r:
                continue
            if f >= 6 and (xx + yy) % 2:
                continue
            if f >= 7 and (xx * 3 + yy) % 3:
                continue
            col = C["path_light"]
            if d2 > (r * .6) ** 2 and (xx + yy > 0):
                col = C["path"]
            if d2 > (r * .85) ** 2 and (xx + yy > r // 2):
                col = C["path_dark"]
            px(im, x + xx, y + yy, col)


def star(im, x, y, s, f):
    """brilho de 4 pontas."""
    px(im, x, y, C["cream_light"])
    for k in range(1, s + 1):
        c = C["yellow"] if k < s else C["cream_light"]
        for dx, dy in ((k, 0), (-k, 0), (0, k), (0, -k)):
            px(im, x + dx, y + dy, c)
    if s >= 2:
        for dx, dy in ((1, 1), (-1, -1), (1, -1), (-1, 1)):
            px(im, x + dx, y + dy, C["yellow"])


def ring(im, cx, cy, r, f):
    for a in range(0, 360, 4):
        x = cx + math.cos(math.radians(a)) * r
        y = cy + math.sin(math.radians(a)) * r * .75
        if (int(a / 4) + f) % 2 == 0:
            px(im, x, y, C["yellow"])
            if f <= 4:
                px(im, x + 1, y, C["cream_light"])


def build():
    base = L.build_anim()
    rng = random.Random(1304)
    cx, cy = FW // 2, FH // 2 + 8
    puffs = [(rng.uniform(0, 6.28), rng.uniform(8, 22), rng.randint(4, 7)) for _ in range(8)]
    stars = [(-24, -26, 3), (26, -18, 2), (-4, -36, 3), (12, -8, 2), (-32, -2, 2), (34, 6, 3), (0, -20, 2)]
    sheet = Image.new("RGBA", (FW * NF, FH), CLEAR)
    for f in range(NF):
        im = Image.new("RGBA", (FW, FH), CLEAR)
        if f >= 1:   # poeira por baixo
            k = (f - 1) / 6
            for a, dist, r in puffs:
                x = cx + math.cos(a) * dist * (.4 + 1.5 * k)
                y = cy + 6 + math.sin(a) * dist * .45 * (.5 + k) - 8 * k
                puff(im, int(x), int(y), int(r * (.6 + .9 * k)), f)
        im.alpha_composite(base.crop((f * FW, 0, (f + 1) * FW, FH)))
        if 3 <= f <= 6:
            ring(im, cx, cy - 6, 10 + 7 * (f - 3), f)
        for i, (dx, dy, s) in enumerate(stars):   # brilho breve (cintilam nos quadros 3 a 7)
            start = 3 + i % 3
            if start <= f <= 7:
                t = f - start
                size = s if t == 0 else max(1, s - t) if t < 3 else 0
                if size:
                    star(im, cx + dx, cy + dy, size, f)
        sheet.paste(im, (f * FW, 0))
    return sheet


if __name__ == "__main__":
    out = L.OUT / "unlock_anim.png"
    build().save(out)
    print("ok", out)
