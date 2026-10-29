"""Fonte unica do jogo. TODA a UI desenha texto por aqui (`draw`, `render`, `width`, `wrap`, `fit`).

Backend padrao: fonte BITMAP `assets/fonts/chaoscats_16.png/json` (corpo, maiusculas de 10 px;
`scale` 1) e `chaoscats_32` (titulo; `scale` 2, 3+ = ampliacao inteira), sheet branco tingido por
BLEND_RGBA_MULT. Caractere ausente (& # @ ~ ^ ...) cai para a 5x7 ou para a letra base; nunca "?".

Fallback (se o bitmap faltar): fonte pixel 5x7 proporcional desenhada a mao (sem licenca externa), com acentos
compostos por Unicode (NFD): qualquer letra latina acentuada (a, c, e, i, n, o, u com agudo,
grave, circunflexo, til, trema, cedilha) sai sem "?". Caractere sem glifo e sem base conhecida
e ignorado (nunca vira "?").

Backend TTF/OTF (opcional): quando `theme.FONT_FILE` aponta para um arquivo em `assets/fonts/`
(e ele existe), o mesmo API passa a usar essa fonte (`FONT_PX` px, nitido, sem antialias; `scale`
multiplica o tamanho). Arquivo ausente = continua na fonte 5x7. Fonte bitmap (spritesheet de
glifos + JSON) entra aqui quando a arte entregar o formato.

Convencao: `draw(surf, text, x, y)` posiciona o TOPO DAS MAIUSCULAS em y. Maiusculas
tem 7 px de altura; descendentes vao ate y+8; acentos ficam em y-2..y-1.
"""
from __future__ import annotations

import json
import unicodedata
from pathlib import Path

import pygame

CAP_H = 7
LINE_H = 10          # passo recomendado entre linhas
_TOP = 2             # linhas de folga acima das maiusculas no bitmap do glifo
_BMP_H = 11

# (linha_inicial, *linhas). Linha 2 = topo das maiusculas; 4 = topo das minusculas.
_G: dict[str, tuple] = {
    "A": (2, ".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": (2, "####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (2, ".###.", "#...#", "#....", "#....", "#....", "#...#", ".###."),
    "D": (2, "####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": (2, "#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": (2, "#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (2, ".###.", "#...#", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": (2, "#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": (2, "###", ".#.", ".#.", ".#.", ".#.", ".#.", "###"),
    "J": (2, "..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": (2, "#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": (2, "#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": (2, "#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": (2, "#...#", "##..#", "#.#.#", "#..##", "#...#", "#...#", "#...#"),
    "O": (2, ".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": (2, "####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (2, ".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": (2, "####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (2, ".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": (2, "#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": (2, "#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": (2, "#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": (2, "#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": (2, "#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": (2, "#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": (2, "#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "a": (4, ".###.", "....#", ".####", "#...#", ".####"),
    "b": (2, "#....", "#....", "#.##.", "##..#", "#...#", "#...#", "####."),
    "c": (4, ".###.", "#...#", "#....", "#...#", ".###."),
    "d": (2, "....#", "....#", ".##.#", "#..##", "#...#", "#...#", ".####"),
    "e": (4, ".###.", "#...#", "#####", "#....", ".###."),
    "f": (2, "..##.", ".#..#", ".#...", "###..", ".#...", ".#...", ".#..."),
    "g": (4, ".####", "#...#", "#...#", ".####", "....#", "#...#", ".###."),
    "h": (2, "#....", "#....", "#.##.", "##..#", "#...#", "#...#", "#...#"),
    "i": (2, "#", ".", "#", "#", "#", "#", "#"),
    "ı": (4, "#", "#", "#", "#", "#"),   # i sem ponto (base para acento)
    "j": (2, "..#", "...", "..#", "..#", "..#", "..#", "..#", "#.#", ".##"),
    "k": (2, "#....", "#....", "#..#.", "#.#..", "##...", "#.#..", "#..#."),
    "l": (2, "#", "#", "#", "#", "#", "#", "#"),
    "m": (4, "##.#.", "#.#.#", "#.#.#", "#.#.#", "#.#.#"),
    "n": (4, "#.##.", "##..#", "#...#", "#...#", "#...#"),
    "o": (4, ".###.", "#...#", "#...#", "#...#", ".###."),
    "p": (4, "####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "q": (4, ".####", "#...#", "#...#", ".####", "....#", "....#", "....#"),
    "r": (4, "#.##.", "##..#", "#....", "#....", "#...."),
    "s": (4, ".####", "#....", ".###.", "....#", "####."),
    "t": (3, ".#.", "###", ".#.", ".#.", ".#.", ".##"),
    "u": (4, "#...#", "#...#", "#...#", "#..##", ".##.#"),
    "v": (4, "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "w": (4, "#...#", "#...#", "#.#.#", "#.#.#", ".#.#."),
    "x": (4, "#...#", ".#.#.", "..#..", ".#.#.", "#...#"),
    "y": (4, "#...#", "#...#", "#...#", ".####", "....#", "#...#", ".###."),
    "z": (4, "#####", "...#.", "..#..", ".#...", "#####"),
    "0": (2, ".###.", "#...#", "#..##", "#.#.#", "##..#", "#...#", ".###."),
    "1": (2, "..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (2, ".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": (2, ".###.", "#...#", "....#", "..##.", "....#", "#...#", ".###."),
    "4": (2, "...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": (2, "#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (2, ".###.", "#...#", "#....", "####.", "#...#", "#...#", ".###."),
    "7": (2, "#####", "....#", "...#.", "..#..", ".#...", ".#...", ".#..."),
    "8": (2, ".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (2, ".###.", "#...#", "#...#", ".####", "....#", "#...#", ".###."),
    ".": (8, "#"),
    ",": (8, ".#", "#."),
    ":": (5, "#", ".", ".", "#"),
    ";": (5, ".#", "..", "..", ".#", "#."),
    "-": (6, "###"),
    "+": (5, ".#.", "###", ".#."),
    "=": (5, "###", "...", "###"),
    "/": (2, "....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    "[": (2, "##", "#.", "#.", "#.", "#.", "#.", "##"),
    "]": (2, "##", ".#", ".#", ".#", ".#", ".#", "##"),
    "(": (2, "..#", ".#.", "#..", "#..", "#..", ".#.", "..#"),
    ")": (2, "#..", ".#.", "..#", "..#", "..#", ".#.", "#.."),
    "!": (2, "#", "#", "#", "#", "#", ".", "#"),
    "?": (2, ".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "%": (2, "##..#", "##.#.", "...#.", "..#..", ".#...", ".#.##", "#..##"),
    ">": (3, "#..", ".#.", "..#", ".#.", "#.."),
    "<": (3, "..#", ".#.", "#..", ".#.", "..#"),
    "'": (2, "#", "#"),
    '"': (2, "#.#", "#.#"),
    "*": (3, "#.#.#", ".###.", "#####", ".###.", "#.#.#"),
    "·": (6, "#"),
    "ı": (4, "#", "#", "#", "#", "#"),
    "_": (9, "#####"),
    "|": (2, "#", "#", "#", "#", "#", "#", "#", "#", "#"),
    "&": (2, ".##..", "#..#.", "#.#..", ".#...", "#.#.#", "#..#.", ".##.#"),
    "#": (2, ".#.#.", "#####", ".#.#.", ".#.#.", "#####", ".#.#."),
    "@": (2, ".###.", "#...#", "#.###", "#.#.#", "#.###", "#....", ".####"),
    "~": (5, ".#.#", "#.#."),
    "$": (2, "..#..", ".####", "#.#..", ".###.", "..#.#", "####.", "..#.."),
    "{": (2, "..#", ".#.", ".#.", "#..", ".#.", ".#.", "..#"),
    "}": (2, "#..", ".#.", ".#.", "..#", ".#.", ".#.", "#.."),
    "^": (2, ".#.", "#.#"),
    "`": (2, "#.", ".#"),
    "¡": (2, "#", ".", "#", "#", "#", "#", "#"),
    "¿": (2, "..#..", ".....", "..#..", "..#..", ".#...", "#...#", ".###."),
    "×": (4, "#...#", ".#.#.", "..#..", ".#.#.", "#...#"),
}

# marcas de acento: pixels (dx, dy) relativos ao topo da letra base
_MARKS = {
    "acute": [(3, -2), (2, -1)],
    "grave": [(1, -2), (2, -1)],
    "circ": [(2, -2), (1, -1), (3, -1)],
    "tilde": [(1, -1), (2, -2), (3, -2), (4, -1)],
    "uml": [(1, -2), (3, -2)],
    "cedil": [(2, 1), (1, 2)],
    "none": [],
}
_NFD_MARK = {"́": "acute", "̀": "grave", "̂": "circ", "̃": "tilde",
             "̈": "uml", "̧": "cedil", "̊": "uml", "̌": "circ",
             "̄": "acute", "̆": "circ", "̨": "cedil"}
_REPLACE = {"—": "-", "–": "-", "→": ">", "…": "...", "•": "·",
            "º": "o", "ª": "a"}
_SPACE_W = 3

_Glyph = tuple[list[tuple[int, int]], int]   # pixels, largura
_glyphs: dict[str, _Glyph] = {}
_cache: dict[tuple, pygame.Surface] = {}


def _build(ch: str) -> _Glyph:
    if ch in _G:
        top, rows = _G[ch][0], _G[ch][1:]
        px = [(x, top + r) for r, row in enumerate(rows) for x, c in enumerate(row) if c == "#"]
    elif _decompose(ch) is not None:
        base, mark = _decompose(ch)
        bpx, bw = _glyph(base)
        top = min(y for _, y in bpx)
        bottom = _TOP + CAP_H - 1
        shift = (bw - 5) // 2 if bw < 5 and mark != "cedil" else 0
        px = list(bpx)
        for dx, dy in _MARKS.get(mark, []):
            px.append((dx + shift, (bottom if mark == "cedil" else top) + dy))
    else:
        return [], 0                       # sem glifo e sem base: nada (nunca "?")
    w = max((x for x, _ in px), default=0) + 1
    return px, w


def _decompose(ch: str) -> tuple[str, str] | None:
    """(letra base, marca) de um caractere acentuado via NFD, se a base e a marca existem."""
    d = unicodedata.normalize("NFD", ch)
    if len(d) < 2 or d[0] not in _G and d[0] != "i":
        return None
    base = "ı" if d[0] == "i" else d[0]
    mark = next((_NFD_MARK[m] for m in d[1:] if m in _NFD_MARK), None)
    return (base, mark) if mark else (base, "none")


def _glyph(ch: str) -> _Glyph:
    g = _glyphs.get(ch)
    if g is None:
        g = _glyphs[ch] = _build(ch)
    return g


def _norm(text: str) -> str:
    return "".join(_REPLACE.get(c, c) for c in text)


# ------------------------------------------------------------------ backend TTF/OTF (opcional)
_FONTS_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
_ttf_path: Path | None = None
_ttf_px = 16
_ttf_fonts: dict[int, pygame.font.Font] = {}


def use_ttf(filename: str | None, px: int = 16) -> bool:
    """Liga (arquivo em assets/fonts/) ou desliga (None) o backend TTF/OTF. True se ficou ligado.
    Ajusta CAP_H/LINE_H para o tamanho novo; as telas leem `font.CAP_H` na hora de desenhar."""
    global _ttf_path, _ttf_px, CAP_H, LINE_H
    _ttf_fonts.clear()
    _cache.clear()
    path = (_FONTS_DIR / filename) if filename else None
    if path is None or not path.is_file():
        _ttf_path = None
        _default_metrics()
        return False
    _ttf_path, _ttf_px = path, px
    f = _ttf_font(1)
    CAP_H = f.metrics("H")[0][3]
    LINE_H = f.get_linesize()
    return True


def _ttf_font(scale: int) -> pygame.font.Font:
    f = _ttf_fonts.get(scale)
    if f is None:
        if not pygame.font.get_init():
            pygame.font.init()
        f = _ttf_fonts[scale] = pygame.font.Font(str(_ttf_path), _ttf_px * scale)
    return f


def _ttf_top(scale: int) -> int:
    """Linhas do bitmap acima do topo das maiusculas (para `draw` alinhar pelo topo)."""
    f = _ttf_font(scale)
    return f.get_ascent() - f.metrics("H")[0][3]


def _auto_ttf() -> None:
    from ui import theme
    if getattr(theme, "FONT_FILE", None):
        use_ttf(theme.FONT_FILE, getattr(theme, "FONT_PX", 16))


# ------------------------------------------------------------------ backend bitmap (assets/fonts)
class _Bitmap:
    def __init__(self, stem: str) -> None:
        d = json.loads((_FONTS_DIR / f"{stem}.json").read_text(encoding="utf-8"))
        img = pygame.image.load(str(_FONTS_DIR / d["image"]))
        self.sheet = img.convert_alpha() if pygame.display.get_surface() else img
        self.cell = int(d["cell_height"])
        self.space = int(d["space"])
        self.glyphs: dict[str, tuple[pygame.Rect, int]] = {
            ch: (pygame.Rect(g["x"], g["y"], g["w"], g["h"]), int(g["adv"]))
            for ch, g in d["glyphs"].items()}
        h = self.glyphs["H"][0]
        rows = [y for y in range(h.h)
                if any(self.sheet.get_at((h.x + x, h.y + y))[3] > 0 for x in range(h.w))]
        self.top, self.cap = rows[0], rows[-1] - rows[0] + 1


_bmp: dict[int, _Bitmap] = {}          # 1 = corpo (16), 2 = titulo (32)
_fb_cache: dict[str, pygame.Surface | None] = {}
_BMP_SUBST = {"—": "-", "–": "-", "º": "o", "ª": "a"}


def _default_metrics() -> None:
    """CAP_H/LINE_H do backend ativo (as telas leem `font.CAP_H` na hora de desenhar)."""
    global CAP_H, LINE_H
    if _ttf_path is not None:
        return
    if 1 in _bmp:
        CAP_H, LINE_H = _bmp[1].cap, _bmp[1].cap + 4
    else:
        CAP_H, LINE_H = 7, 10


def use_bitmap(enabled: bool = True) -> bool:
    """(Re)carrega os sheets bitmap de assets/fonts. True se o corpo (16) ficou ativo; se faltar
    (ou `enabled` False) a fonte 5x7 continua valendo."""
    _bmp.clear()
    _cache.clear()
    _fb_cache.clear()
    if enabled:
        try:
            _bmp[1] = _Bitmap("chaoscats_16")
        except Exception:
            _bmp.clear()
        if _bmp:
            try:
                _bmp[2] = _Bitmap("chaoscats_32")
            except Exception:
                pass
    _default_metrics()
    return bool(_bmp)


def _bmp_for(scale: int) -> tuple[_Bitmap, int]:
    """(sheet, ampliacao inteira): escala par usa o sheet de titulo (32) se existir."""
    if scale % 2 == 0 and 2 in _bmp:
        return _bmp[2], scale // 2
    return _bmp[1], scale


def _fb_glyph(ch: str, bm: _Bitmap) -> pygame.Surface | None:
    """Glifo 5x7 (branco) para o que o sheet nao tem (& # ...). None se nem a 5x7 tem."""
    key = f"{bm.cell}{ch}"
    if key not in _fb_cache:
        px, w = _glyph(ch)
        surf = None
        if px:
            k = max(1, bm.cell // 16)
            top = min(y for _, y in px)
            surf = pygame.Surface((w * k, 9 * k), pygame.SRCALPHA)
            for gx, gy in px:
                surf.fill((255, 255, 255), (gx * k, (gy - top) * k, k, k))
        _fb_cache[key] = surf
    return _fb_cache[key]


def _resolve(ch: str, bm: _Bitmap) -> str | None:
    """Caractere do sheet que representa `ch` (ele mesmo, substituto ou base sem acento) ou None."""
    if ch in bm.glyphs:
        return ch
    sub = _BMP_SUBST.get(ch)
    if sub and sub in bm.glyphs:
        return sub
    base = unicodedata.normalize("NFD", ch)[:1]
    if base != ch and base in bm.glyphs:
        return base
    return None


def _prep(text: str) -> str:
    return text.replace("…", "...")


def _bmp_layout(text: str, bm: _Bitmap) -> tuple[list[tuple[str, int, bool]], int]:
    """([(char, x, no_sheet)], largura). Sem glifo em lugar nenhum = ignora (nunca '?')."""
    out: list[tuple[str, int, bool]] = []
    x = end = 0
    for ch in _prep(text):
        if ch == " ":
            x += bm.space
            continue
        rc = _resolve(ch, bm)
        if rc is not None:
            r, adv = bm.glyphs[rc]
            out.append((rc, x, False))
            end = x + r.w
            x += adv
            continue
        g = _fb_glyph(ch, bm)
        if g is not None:
            out.append((ch, x, True))
            end = x + g.get_width()
            x += g.get_width() + 2 * max(1, bm.cell // 16)
    return out, end


def width(text: str, scale: int = 1) -> int:
    if _ttf_path is not None:
        return _ttf_font(scale).size(text)[0]
    if _bmp:
        bm, k = _bmp_for(scale)
        return _bmp_layout(text, bm)[1] * k
    text = _norm(text)
    w = 0
    for ch in text:
        w += (_SPACE_W if ch == " " else _glyph(ch)[1]) + 1
    return max(0, w - 1) * scale


def advance(text: str, scale: int = 1) -> int:
    """Largura ate o ponto de escrita seguinte, contando espacos no fim (para encadear trechos)."""
    return width(text + ".", scale) - width(".", scale)


def _top(scale: int) -> int:
    """Linhas do bitmap acima do topo das maiusculas."""
    if _ttf_path is not None:
        return _ttf_top(scale)
    if _bmp:
        bm, k = _bmp_for(scale)
        return bm.top * k
    return _TOP * scale


def _render_bmp(text: str, color: tuple[int, int, int], scale: int) -> pygame.Surface:
    bm, k = _bmp_for(scale)
    lay, w = _bmp_layout(text, bm)
    surf = pygame.Surface((max(1, w), bm.cell), pygame.SRCALPHA)
    for ch, x, fb in lay:
        if not fb:
            surf.blit(bm.sheet, (x, 0), bm.glyphs[ch][0])
        else:
            g = _fb_glyph(ch, bm)
            if g is not None:
                surf.blit(g, (x, bm.top + max(0, (bm.cap - 7 * max(1, bm.cell // 16)) // 2)))
    surf.fill((*color, 255), special_flags=pygame.BLEND_RGBA_MULT)
    if k != 1:
        surf = pygame.transform.scale(surf, (surf.get_width() * k, surf.get_height() * k))
    return surf


def render(text: str, color: tuple[int, int, int], scale: int = 1) -> pygame.Surface:
    """Surface com o texto (fundo transparente); o topo das maiusculas fica em `_top(scale)`."""
    key = (text, color, scale)
    s = _cache.get(key)
    if s is not None:
        return s
    if len(_cache) > 4000:
        _cache.clear()
    if _ttf_path is not None:
        s = _ttf_font(scale).render(text or " ", False, color)
    elif _bmp:
        s = _render_bmp(text, color, scale)
    else:
        text = _norm(text)
        w = max(1, width(text))
        s = pygame.Surface((w * scale, _BMP_H * scale), pygame.SRCALPHA)
        x = 0
        for ch in text:
            if ch == " ":
                x += _SPACE_W + 1
                continue
            px, gw = _glyph(ch)
            for (gx, gy) in px:
                s.fill(color, ((x + gx) * scale, gy * scale, scale, scale))
            x += gw + 1
    _cache[key] = s
    return s


def draw(surf: pygame.Surface, text: str, x: int, y: int, color: tuple[int, int, int],
         scale: int = 1, align: str = "left") -> int:
    """Desenha com o topo das maiusculas em y. Retorna a largura desenhada."""
    img = render(text, color, scale)
    w = img.get_width()
    if align == "center":
        x -= w // 2
    elif align == "right":
        x -= w
    surf.blit(img, (x, y - _top(scale)))
    return w


def wrap(text: str, max_w: int, scale: int = 1) -> list[str]:
    """Quebra por palavras para caber em max_w pixels."""
    lines: list[str] = []
    cur = ""
    for word in text.split():
        trial = word if not cur else cur + " " + word
        if width(trial, scale) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines or [""]


def fit(text: str, max_w: int, scale: int = 1) -> str:
    """Corta o texto com '.' no fim para caber em max_w."""
    if width(text, scale) <= max_w:
        return text
    while text and width(text + ".", scale) > max_w:
        text = text[:-1]
    return text + "."


use_bitmap()
_auto_ttf()
