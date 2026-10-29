"""Layout do duelo em coordenadas internas 960x540 (W, H em ui/theme.py) e teste de clique.

Geometria (a arte do tabuleiro final deve respeitar estes retangulos; ver reports/T8.2):
    lider inimigo   y   2..58 (placa pintada x372..628, retrato 64x56 em x448)      campo inimigo  y  62..186      (5 cartas 120x124, passo 128)
    campo jogador   y 194..318     lider jogador  y 322..378
    faixa da mao    y 382..540     (cartas em y 398..522 + arco; nada mais invade esta faixa)
    colunas laterais: esquerda x 4..156 (turno, info, registro, mensagem);
                      direita x 804..956 (baralho inimigo, FIM DE TURNO, baralho, energia).
"""
from __future__ import annotations

import pygame

from ui.theme import H, W

CARD_W, CARD_H = 120, 124
PITCH = 128                      # distancia entre cartas no campo
SLOTS = 5
MAIN_W = (SLOTS - 1) * PITCH + CARD_W        # 632
FIELD_X = (W - MAIN_W) // 2                  # 164

ENEMY_LEADER_Y = 2
ENEMY_FIELD_Y = 62
PLAYER_FIELD_Y = 194
PLAYER_LEADER_Y = 322
LEADER_W, LEADER_H = 64, 56      # recorte do retrato 64x64 no medalhao pintado (x448..511)
CENTER_Y = (ENEMY_FIELD_Y + CARD_H + PLAYER_FIELD_Y) // 2   # 190: faixa entre os campos

HAND_STRIP_Y = 382               # a faixa da mao comeca aqui (abaixo do lider do jogador)
HAND_Y = 398                     # topo das cartas da mao (em repouso, centro do arco)
HAND_X0, HAND_X1 = 12, 772       # a mao nunca passa de x=772 (energia/botoes ficam a direita)
HAND_ARC = 8                     # as pontas da mao descem ate 8 px (leque)
HOVER_RISE = 16                  # a carta em hover/selecionada sobe isto

LEFT_X, LEFT_W = 6, 150          # recortes pintados em board_noturno.png (x6..155 / x802..955)
RIGHT_X, RIGHT_W = 802, 154


def slot_rect(side: str, n: int) -> pygame.Rect:
    y = ENEMY_FIELD_Y if side == "enemy" else PLAYER_FIELD_Y
    return pygame.Rect(FIELD_X + n * PITCH, y, CARD_W, CARD_H)


def field_rect(side: str) -> pygame.Rect:
    """Faixa do campo (5 slots) de um lado."""
    y = ENEMY_FIELD_Y if side == "enemy" else PLAYER_FIELD_Y
    return pygame.Rect(FIELD_X, y, MAIN_W, CARD_H)


def leader_rect(side: str) -> pygame.Rect:
    """Retrato do Lider (alvo de clique), centrado no seu lado."""
    y = ENEMY_LEADER_Y if side == "enemy" else PLAYER_LEADER_Y
    return pygame.Rect(W // 2 - LEADER_W // 2, y, LEADER_W, LEADER_H)


def leader_name_rect(side: str) -> pygame.Rect:
    """Area do nome/regra do Lider: faixa a esquerda da placa pintada (que comeca em x=372)."""
    r = leader_rect(side)
    return pygame.Rect(FIELD_X, r.y, 372 - 8 - FIELD_X, r.h)


def leader_hp_rect(side: str) -> pygame.Rect:
    """Recorte 40x40 pintado para a gema de HP do Lider (x540..579)."""
    r = leader_rect(side)
    return pygame.Rect(540, r.y + 8, 40, 40)


def leader_hp_center(side: str) -> tuple[int, int]:
    return leader_hp_rect(side).center


def leader_taunt_rect(side: str) -> pygame.Rect:
    """Indicador de Provocar (escudo + texto) a direita da placa do Lider (x634..)."""
    r = leader_rect(side)
    return pygame.Rect(634, r.y + 8, 160, 40)


def hand_pitch(n: int) -> int:
    if n <= 1:
        return PITCH
    return min(PITCH, (HAND_X1 - HAND_X0 - CARD_W) // (n - 1))


def hand_rect(i: int, n: int) -> pygame.Rect:
    """Carta `i` da mao de `n` (leque: pontas um pouco mais baixas). Cabe sempre em [12, 772]."""
    pitch = hand_pitch(n)
    total = (n - 1) * pitch + CARD_W
    x0 = HAND_X0 + (HAND_X1 - HAND_X0 - total) // 2
    k = 0.0 if n <= 1 else (2.0 * i / (n - 1) - 1.0)
    return pygame.Rect(x0 + i * pitch, HAND_Y + round(HAND_ARC * k * k), CARD_W, CARD_H)


def hand_hit_rect(i: int, n: int) -> pygame.Rect:
    """Area de clique/hover da carta da mao: inclui a subida do hover (sem tremer na borda)."""
    r = hand_rect(i, n)
    return pygame.Rect(r.x, r.y - HOVER_RISE, r.w, r.h + HOVER_RISE)


def pass_rect() -> pygame.Rect:
    """Botao FIM DE TURNO (lateral direita, na altura da faixa entre os campos)."""
    return pygame.Rect(RIGHT_X + 1, CENTER_Y - 32, 152, 64)


def pass_yes_rect() -> pygame.Rect:
    r = pass_rect()
    return pygame.Rect(r.x, r.y, r.w * 3 // 5 - 2, r.h)


def pass_no_rect() -> pygame.Rect:
    r = pass_rect()
    y = pass_yes_rect()
    return pygame.Rect(y.right + 4, r.y, r.right - y.right - 4, r.h)


def turn_rect() -> pygame.Rect:
    return pygame.Rect(LEFT_X, 6, LEFT_W, 40)


def info_rect() -> pygame.Rect:
    return pygame.Rect(LEFT_X, 50, LEFT_W, 50)


def log_rect() -> pygame.Rect:
    return pygame.Rect(LEFT_X, 104, LEFT_W, 228)


def message_rect() -> pygame.Rect:
    return pygame.Rect(LEFT_X, 336, LEFT_W, 42)


def enemy_pile_rect() -> pygame.Rect:
    """Baralho/mao do inimigo (canto superior direito, recorte pintado y6..85)."""
    return pygame.Rect(RIGHT_X, 6, RIGHT_W, 80)


def pile_rect() -> pygame.Rect:
    """Baralho do jogador com contador (recorte pintado y390..477)."""
    return pygame.Rect(RIGHT_X, 390, RIGHT_W, 88)


def energy_rect() -> pygame.Rect:
    """Faixa de energia (canto inferior direito, recorte pintado x778..955; gemas ate 7)."""
    return pygame.Rect(778, 486, 178, 50)


def toast_rect(width: int) -> pygame.Rect:
    """Faixa de aviso do duelo: centralizada na faixa entre os campos."""
    r = pygame.Rect(0, 0, width, 30)
    r.center = (W // 2, CENTER_Y)
    return r


def final_panel() -> pygame.Rect:
    return pygame.Rect(180, 60, 600, 420)


def final_buttons() -> dict[str, pygame.Rect]:
    p = final_panel()
    return {"again": pygame.Rect(p.x + 24, p.bottom - 64, 260, 44),
            "repeat": pygame.Rect(p.right - 284, p.bottom - 64, 260, 44)}


def continue_rect() -> pygame.Rect:
    """Botao CONTINUAR do painel final do duelo dentro da run."""
    p = final_panel()
    return pygame.Rect(p.centerx - 130, p.bottom - 64, 260, 44)


def hit_test(pos: tuple[int, int], n_hand: int, *, final: bool = False,
             confirm: bool = False) -> tuple | None:
    """Elemento sob `pos` (coordenadas internas) ou None."""
    if final:
        for name, r in final_buttons().items():
            if r.collidepoint(pos):
                return (name,)
        return None
    if confirm:
        if pass_yes_rect().collidepoint(pos):
            return ("pass_yes",)
        if pass_no_rect().collidepoint(pos):
            return ("pass_no",)
    if pass_rect().collidepoint(pos):
        return ("pass",)
    for side in ("enemy", "player"):
        if leader_rect(side).collidepoint(pos):
            return ("leader", side)
        for n in range(SLOTS):
            if slot_rect(side, n).collidepoint(pos):
                return ("slot", side, n)
    for i in range(n_hand - 1, -1, -1):
        if hand_hit_rect(i, n_hand).collidepoint(pos):
            return ("hand", i)
    return None


def rect_of(elem: tuple, n_hand: int = 0) -> pygame.Rect | None:
    if elem[0] == "slot":
        return slot_rect(elem[1], elem[2])
    if elem[0] == "leader":
        return leader_rect(elem[1])
    if elem[0] == "hand":
        return hand_rect(elem[1], n_hand)
    if elem[0] == "pass":
        return pass_rect()
    if elem[0] == "pass_yes":
        return pass_yes_rect()
    if elem[0] == "pass_no":
        return pass_no_rect()
    return None


def to_internal(pos: tuple[int, int], win_size: tuple[int, int]) -> tuple[int, int]:
    """Posicao do mouse na janela -> coordenadas internas (pode sair do intervalo)."""
    scale, ox, oy = view_transform(win_size)
    return ((pos[0] - ox) // scale, (pos[1] - oy) // scale)


def view_transform(win_size: tuple[int, int]) -> tuple[int, int, int]:
    """(escala inteira, offset x, offset y): a maior escala inteira que cabe, centralizada."""
    scale = max(1, min(win_size[0] // W, win_size[1] // H))
    return scale, (win_size[0] - W * scale) // 2, (win_size[1] - H * scale) // 2
