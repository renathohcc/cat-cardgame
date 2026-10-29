"""Separa um sprite de paleta forcada em camadas por cor e gera pelagens (palette swap) + preview.
Uso: python assets/tools/split_layers.py"""
from pathlib import Path
from PIL import Image, ImageDraw
ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT/"assets/cats/_proposta"; PREV = ROOT/"reports/arte"
def h(s): return tuple(int(s[i:i+2],16) for i in (1,3,5))
LAYERS = {  # camada -> cores (rgb) do vira-lata base
 "contorno": ["#3b2a38","#2a1c2a"], "pelagem": ["#b86a3a","#d98f4e","#f0b878"],
 "padrao": ["#8f4a2c"], "peito_focinho": ["#f6e3c8"], "nariz_orelha": ["#f09aa8"], "olhos": ["#ffd84a","#ffffff"]}
COATS = {  # pelagem (sombra, base, luz, padrao, peito)
 "laranja": None,
 "cinza":   ["#5f6878","#8c95a6","#b9c1cf","#454c5c","#e8ecf2"],
 "preto":   ["#26222e","#3c3646","#585066","#1a1720","#6a6278"],
 "creme":   ["#c9a77a","#e6c99a","#f6e3c2","#a9835a","#fff6e6"]}
def split(im, name):
    out = {}
    for ln, cols in LAYERS.items():
        rgb = {h(c) for c in cols}; l = Image.new("RGBA", im.size, (0,0,0,0))
        for x in range(im.width):
            for y in range(im.height):
                p = im.getpixel((x,y))
                if p[3] and p[:3] in rgb: l.putpixel((x,y), p)
        l.save(SRC/f"{name}_camada_{ln}.png"); out[ln] = l
    return out
def recolor(im, coat):
    src = [h(c) for c in ["#b86a3a","#d98f4e","#f0b878","#8f4a2c","#f6e3c8"]]; dst = [h(c) for c in COATS[coat]]
    m = dict(zip(src,dst)); o = im.copy()
    for x in range(im.width):
        for y in range(im.height):
            p = im.getpixel((x,y))
            if p[3] and p[:3] in m: o.putpixel((x,y), m[p[:3]]+(255,))
    return o
def card(w=62,h_=62):
    c = Image.new("RGBA",(w,h_),(0,0,0,0)); d = ImageDraw.Draw(c)
    d.rectangle([0,0,w-1,h_-1], fill=(52,58,86), outline=(110,120,156))
    d.rectangle([3,3,w-4,h_-17], fill=(243,233,214))   # janela da arte (cream)
    d.rectangle([3,h_-14,w-4,h_-4], fill=(34,40,62))    # faixa custo/ATK/HP
    return c
if __name__ == "__main__":
    PREV.mkdir(parents=True, exist_ok=True)
    sprites = {n: Image.open(SRC/f"{n}.png").convert("RGBA") for n in ["A_48_capa","B_32_sentado","C_64_espada"]}
    for n, im in sprites.items(): split(im, n)
    for c in COATS:
        if COATS[c]: recolor(sprites["A_48_capa"], c).save(SRC/f"A_48_capa_pelagem_{c}.png")
    # preview 1: tres estilos em cartas 62x62 (escala 4x)
    S = 4; sheet = Image.new("RGBA",(62*3*S+16*S, 62*S+8*S),(24,28,44,255)); x = 4*S
    for n, im in sprites.items():
        cd = card(); im2 = im if im.width<=56 else im.resize((56,56),Image.NEAREST) if False else im
        cd.alpha_composite(im, ((62-im.width)//2, 3+max(0,(42-im.height)//2) - max(0,(im.height-42)//2)))
        sheet.alpha_composite(cd.resize((62*S,62*S),Image.NEAREST),(x,4*S)); x += 66*S
    sheet.save(PREV/"preview_estilos_carta_4x.png")
    # preview 2: pelagens (variante A) + camadas
    base = sprites["A_48_capa"]; items = [("laranja",base)]+[(c,recolor(base,c)) for c in COATS if COATS[c]]
    S = 4; sh = Image.new("RGBA",(48*S*5+6*S*5, 48*S*2+3*S*3),(243,233,214,255)); 
    for i,(n,im) in enumerate(items): sh.alpha_composite(im.resize((48*S,48*S),Image.NEAREST),(3*S+i*54*S,3*S))
    for i,ln in enumerate(LAYERS):
        l = Image.open(SRC/f"A_48_capa_camada_{ln}.png"); bg = Image.new("RGBA",l.size,(120,120,130,255)); bg.alpha_composite(l)
        if i<5: sh.alpha_composite(bg.resize((48*S,48*S),Image.NEAREST),(3*S+i*54*S,48*S+6*S))
    sh.save(PREV/"preview_pelagens_e_camadas_4x.png")
