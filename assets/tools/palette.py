"""Paleta base do Vira-lata (proposta). Gera palette.png usado como paleta forçada no Pixellab."""
from PIL import Image
PAL = {
 "outline": "#3b2a38", "fur_dark": "#b86a3a", "fur": "#d98f4e", "fur_light": "#f0b878",
 "pattern": "#8f4a2c", "belly": "#f6e3c8", "pink": "#f09aa8", "eye": "#ffd84a", "pupil": "#2a1c2a", "white": "#ffffff",
}
def rgb(h): return tuple(int(h[i:i+2],16) for i in (1,3,5))
if __name__ == "__main__":
    im = Image.new("RGB",(len(PAL)*4,4))
    for i,h in enumerate(PAL.values()):
        for x in range(4):
            for y in range(4): im.putpixel((i*4+x,y),rgb(h))
    im.save("palette.png")
