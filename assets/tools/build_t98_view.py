"""utilitario T9.8: contact sheet 4x de PNGs. uso: build_t98_view.py out.png bg_hex a.png b.png ..."""
import sys
from PIL import Image
out, bg, *fs = sys.argv[1:]
k = 4
ims = [Image.open(f).convert("RGBA") for f in fs]
W = sum(i.width for i in ims) * k + 10 * len(ims)
H = max(i.height for i in ims) * k
s = Image.new("RGBA", (W, H), tuple(int(bg[i:i + 2], 16) for i in (1, 3, 5)) + (255,))
x = 0
for i in ims:
    s.alpha_composite(i.resize((i.width * k, i.height * k), 0), (x, 0))
    x += i.width * k + 10
s.save(out)
