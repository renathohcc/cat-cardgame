"""T8.0: monta spritesheets de gatos 96x96 e lideres (96 e 128) a partir de _src/ (PNGs gerados no Pixellab).
Uso: python assets/tools/build_t80.py   (gera pelagens do vira-lata por palette swap, sheets, JSON e previews)
Geracao no Pixellab: gatos = create_image_pixflux img2img (init = gato 48 aprovado em bicubico 96, strength 120);
lideres = create_image_pixflux texto (96 e 128), pixel art busto."""
import colorsys, json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
CATS, LEAD, OLD, PREV = ROOT/"assets/cats96", ROOT/"assets/leaders", ROOT/"assets/cats", ROOT/"reports/arte"
BREEDS = ["vira-lata", "siames", "persa", "sphynx", "maine-coon"]
COATS = {"cinza": ["#454c5c", "#8c95a6", "#b9c1cf", "#e8ecf2"],
         "preto": ["#1a1720", "#3c3646", "#585066", "#7a7290"],
         "creme": ["#a9835a", "#e6c99a", "#f6e3c2", "#fff6e6"]}
LEADERS = ["heroi", "tonho-sem-sorte", "irmaos-pimenta", "berenice-da-matilha", "madame-fifi-pelucia"]

def hx(s): return tuple(int(s[i:i+2], 16) for i in (1, 3, 5))
def lerp(a, b, t): return tuple(round(a[i]+(b[i]-a[i])*t) for i in range(3))
def ramp(r, t):
    t = max(0, min(1, t))*(len(r)-1); i = min(int(t), len(r)-2); return lerp(hx(r[i]), hx(r[i+1]), t-i)

def swap(im, name):
    r, out = COATS[name], im.copy(); px = out.load()
    for x in range(im.width):
        for y in range(im.height):
            R, G, B, A = px[x, y]
            if not A: continue
            h, l, s = colorsys.rgb_to_hls(R/255, G/255, B/255); hd = h*360
            if 12 <= hd <= 45 and s > .28 and .3 <= l <= .9: px[x, y] = ramp(r, (l-.3)/.55)+(A,)
            elif 20 <= hd <= 60 and s <= .28 and l > .8 and name != "creme": px[x, y] = ramp(r, .95)+(A,)
    return out

def sheet(files, cell, cols, out_png, out_json):
    rows = -(-len(files)//cols); im = Image.new("RGBA", (cols*cell, rows*cell), (0, 0, 0, 0)); spr = {}
    for i, (n, p) in enumerate(files):
        s = Image.open(p).convert("RGBA"); assert s.size == (cell, cell), (n, s.size)
        x, y = i % cols*cell, i//cols*cell; im.paste(s, (x, y)); spr[n] = {"x": x, "y": y, "w": cell, "h": cell}
    im.save(out_png); out_json.write_text(json.dumps({"image": out_png.name, "size": list(im.size), "sprites": spr}, indent=2))

def cloud(im, x, y, k):
    """Nuvem de azar do Tonho (T8.0b): desenhada por codigo; (x,y)=canto sup-esq, k=escala (.7 = 128px, .5 = 96px)."""
    from PIL import ImageDraw
    d = ImageDraw.Draw(im); O, SH, BA, LI, DR = "#3b2a38", "#6f7a90", "#9aa5ba", "#c6cfdf", "#6fb4e8"
    blobs = [(0, 10, 12, 20), (8, 4, 24, 18), (18, 6, 34, 20), (26, 11, 40, 21), (4, 12, 38, 22)]
    def S(v): return round(v*k)
    for col, g in ((O, 1), (BA, 0)):
        for a, b, c, e in blobs:
            d.ellipse([x+S(a)-g, y+S(b)-g, x+S(c)+g, y+S(e)+g], fill=col)
    d.ellipse([x+S(9), y+S(5), x+S(21), y+S(12)], fill=LI)
    d.chord([x+S(4), y+S(14), x+S(38), y+S(23)], 0, 180, fill=SH)
    for dx, dy in ((8, 27), (19, 31), (30, 27)):
        d.rectangle([x+S(dx), y+S(dy), x+S(dx)+max(1, S(1.5)), y+S(dy)+max(2, S(4))], fill=DR)
    return im

def main():
    # _src guarda as imagens geradas sem a nuvem do Tonho; `_out/` recebe a versao final (96 derivado do 128 por img2img)
    base = Image.open(CATS/"_src/vira-lata.png").convert("RGBA")
    for n in COATS: swap(base, n).save(CATS/f"_src/vira-lata_{n}.png")
    names = BREEDS+[f"vira-lata_{n}" for n in COATS]
    sheet([(n, CATS/f"_src/{n}.png") for n in names], 96, 4, CATS/"spritesheet.png", CATS/"spritesheet.json")
    for n in names: Image.open(CATS/f"_src/{n}.png").save(CATS/f"{n}.png")
    out = LEAD/"_out"; out.mkdir(exist_ok=True)
    for n in LEADERS:
        for sfx, k in (("", .5), ("_128", .7)):
            im = Image.open(LEAD/f"_src/{n}{sfx}.png").convert("RGBA")
            if n == "tonho-sem-sorte": cloud(im, 0, 0, k)
            im.save(out/f"{n}{sfx}.png")
    sheet([(n, out/f"{n}.png") for n in LEADERS], 96, 5, LEAD/"spritesheet.png", LEAD/"spritesheet.json")
    sheet([(n, out/f"{n}_128.png") for n in LEADERS], 128, 5, LEAD/"spritesheet128.png", LEAD/"spritesheet128.json")
    for n in LEADERS: Image.open(out/f"{n}.png").save(LEAD/f"{n}.png"); Image.open(out/f"{n}_128.png").save(LEAD/f"{n}_128.png")
    bg = (240, 230, 210, 255)
    c = Image.new("RGBA", (5*96*4, 2*96*4), bg)   # novo 96 (4x) em cima, antigo 48 (4x=192 -> mostrado 4x) embaixo
    for i, n in enumerate(BREEDS):
        a = Image.open(CATS/f"{n}.png").convert("RGBA").resize((384, 384), 0); c.paste(a, (i*384, 0), a)
        b = Image.open(OLD/f"{n}.png").convert("RGBA").resize((192, 192), 0); c.paste(b, (i*384+96, 384+96), b)
    c.save(PREV/"preview_gatos96_vs_48_4x.png")
    c = Image.new("RGBA", (5*128*3, 128*3+96*3), bg)
    for i, n in enumerate(LEADERS):
        a = Image.open(LEAD/f"{n}_128.png").convert("RGBA").resize((384, 384), 0); c.paste(a, (i*384, 0), a)
        b = Image.open(LEAD/f"{n}.png").convert("RGBA").resize((288, 288), 0); c.paste(b, (i*384+48, 384), b)
    c.save(PREV/"preview_lideres_4x.png")
    c = Image.new("RGBA", (4*96*4, 96*4), bg)
    for i, n in enumerate(["vira-lata", "vira-lata_cinza", "vira-lata_preto", "vira-lata_creme"]):
        a = Image.open(CATS/f"{n}.png").convert("RGBA").resize((384, 384), 0); c.paste(a, (i*384, 0), a)
    c.save(PREV/"preview_vira-lata_pelagens96_4x.png")

if __name__ == "__main__": main()
