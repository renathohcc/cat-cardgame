"""T9.8: gera assets/pen/palette_pen.json (ate 48 cores): 32 cores da T9.7 + cores extras escolhidas
gulosamente nos sprites/tiles do Pixellab (as que mais destoam da paleta). Uso: python assets/tools/build_t98_palette.py"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import build_t97_lib as L97  # noqa: E402
import build_t98_lib as B  # noqa: E402

N = 48
base = dict(L97.PAL)
pal = [tuple(int(h[i:i + 2], 16) for i in (1, 3, 5)) for h in base.values()]
px = B.source_pixels()
cols, cnt = np.unique(px.reshape(-1, 3), axis=0, return_counts=True)
luma = (cols * np.array([0.299, 0.587, 0.114])).sum(1)
keep = luma >= 78
cols, cnt = cols[keep].astype(np.int32), cnt[keep]
w = np.array([2, 4, 3])
P = np.array(pal, np.int32)
extra = {}
while len(pal) < N:
    d = (((cols[:, None, :] - np.array(pal, np.int32)[None]) ** 2) * w).sum(-1).min(1)
    i = int((d * cnt).argmax())
    c = tuple(int(v) for v in cols[i])
    pal.append(c)
    extra[f"x{len(pal) - len(base)}"] = "#%02x%02x%02x" % c
out = dict(base)
out.update(extra)
with open(os.path.join(B.PEN, "palette_pen.json"), "w") as f:
    json.dump(out, f, indent=1)
print(len(out), extra)
