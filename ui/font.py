"""Fonte pixel unica do jogo (5x7 proporcional, desenhada a mao, sem licenca externa).

Cobre ASCII imprimivel basico e as vogais acentuadas do portugues. Troque este
modulo por uma fonte real quando a arte entregar uma; a API (`render`, `width`,
`wrap`) e o que as telas usam.

Convencao: `draw(surf, text, x, y)` posiciona o TOPO DAS MAIUSCULAS em y. Maiusculas
tem 7 px de altura; descendentes vao ate y+8; acentos ficam em y-2..y-1.
"""
from __future__ import annotations

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
}

# marcas de acento: pixels (dx, dy) relativos ao topo da letra base
_MARKS = {
    "acute": [(3, -2), (2, -1)],
    "grave": [(1, -2), (2, -1)],
    "circ": [(2, -2), (1, -1), (3, -1)],
    "tilde": [(1, -1), (2, -2), (3, -2), (4, -1)],
    "uml": [(1, -1), (3, -1)],
    "cedil": [(2, 1), (1, 2)],
}
_COMPOSED = {
    "á": ("a", "acute"), "à": ("a", "grave"), "â": ("a", "circ"), "ã": ("a", "tilde"),
    "é": ("e", "acute"), "ê": ("e", "circ"),
    "í": ("ı", "acute"),
    "ó": ("o", "acute"), "ô": ("o", "circ"), "õ": ("o", "tilde"),
    "ú": ("u", "acute"), "ü": ("u", "uml"), "ç": ("c", "cedil"),
    "Á": ("A", "acute"), "À": ("A", "grave"), "Â": ("A", "circ"), "Ã": ("A", "tilde"),
    "É": ("E", "acute"), "Ê": ("E", "circ"), "Í": ("I", "acute"),
    "Ó": ("O", "acute"), "Ô": ("O", "circ"), "Õ": ("O", "tilde"),
    "Ú": ("U", "acute"), "Ç": ("C", "cedil"),
}
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
    elif ch in _COMPOSED:
        base, mark = _COMPOSED[ch]
        bpx, bw = _glyph(base)
        top = min(y for _, y in bpx)
        bottom = _TOP + CAP_H - 1
        shift = (bw - 5) // 2 if bw < 5 and mark != "cedil" else 0
        px = list(bpx)
        for dx, dy in _MARKS[mark]:
            px.append((dx + shift, (bottom if mark == "cedil" else top) + dy))
    else:
        return _glyph("?")
    w = max((x for x, _ in px), default=0) + 1
    return px, w


def _glyph(ch: str) -> _Glyph:
    g = _glyphs.get(ch)
    if g is None:
        g = _glyphs[ch] = _build(ch)
    return g


def _norm(text: str) -> str:
    return "".join(_REPLACE.get(c, c) for c in text)


def width(text: str, scale: int = 1) -> int:
    text = _norm(text)
    w = 0
    for ch in text:
        w += (_SPACE_W if ch == " " else _glyph(ch)[1]) + 1
    return max(0, w - 1) * scale


def render(text: str, color: tuple[int, int, int], scale: int = 1) -> pygame.Surface:
    """Surface com o texto (fundo transparente). Topo das maiusculas em y=2*scale."""
    key = (text, color, scale)
    s = _cache.get(key)
    if s is not None:
        return s
    text = _norm(text)
    w = max(1, width(text))
    surf = pygame.Surface((w * scale, _BMP_H * scale), pygame.SRCALPHA)
    x = 0
    for ch in text:
        if ch == " ":
            x += _SPACE_W + 1
            continue
        px, gw = _glyph(ch)
        for (gx, gy) in px:
            surf.fill(color, ((x + gx) * scale, gy * scale, scale, scale))
        x += gw + 1
    if len(_cache) > 4000:
        _cache.clear()
    _cache[key] = surf
    return surf


def draw(surf: pygame.Surface, text: str, x: int, y: int, color: tuple[int, int, int],
         scale: int = 1, align: str = "left") -> int:
    """Desenha com o topo das maiusculas em y. Retorna a largura desenhada."""
    img = render(text, color, scale)
    w = img.get_width()
    if align == "center":
        x -= w // 2
    elif align == "right":
        x -= w
    surf.blit(img, (x, y - _TOP * scale))
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
