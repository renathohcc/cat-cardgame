"""Matematica das animacoes do duelo (investida, respiracao, tremor, numeros, poof, mao, energia).

Funcoes puras: recebem tempos/estado e devolvem numeros inteiros ou arredondados (pixel art
nitida, nada de interpolar imagem). Nenhum sorteio: tudo e derivado de ids/slots/indices.
As intensidades vem de `ui.timing.Timing`.
"""
from __future__ import annotations

import math

IMPACT_FRAC = 0.55            # fracao da investida em que a carta bate no alvo
SHAKE_HZ = (61.0, 47.0)       # frequencias do tremor (x, y)
BIG_HOT = (255, 190, 60)      # cor para a qual o dano alto aquece


def clamp01(u: float) -> float:
    return 0.0 if u < 0.0 else 1.0 if u > 1.0 else u


def ease_out(u: float) -> float:
    u = clamp01(u)
    return 1.0 - (1.0 - u) ** 3


def ease_in_out(u: float) -> float:
    u = clamp01(u)
    return 3 * u * u - 2 * u * u * u


def impact_time(lunge_duration: float) -> float:
    """Instante (s) em que a investida toca o alvo."""
    return lunge_duration * IMPACT_FRAC


def lunge_fraction(age: float, duration: float, reach: float) -> float:
    """Fracao do caminho ate o alvo: sobe (ease-out) ate o impacto e volta (ease-in-out)."""
    p = clamp01(age / duration) if duration > 0 else 1.0
    if p < IMPACT_FRAC:
        return reach * ease_out(p / IMPACT_FRAC)
    return reach * (1.0 - ease_in_out((p - IMPACT_FRAC) / (1.0 - IMPACT_FRAC)))


def lunge_offset(src: tuple[int, int], dst: tuple[int, int], age: float, duration: float,
                 reach: float) -> tuple[int, int]:
    f = lunge_fraction(age, duration, reach)
    return round((dst[0] - src[0]) * f), round((dst[1] - src[1]) * f)


def breath_phase(side: str, slot: int) -> float:
    """Fase propria do gato em campo (0..2pi), derivada do lado e do slot."""
    return ((slot * 37 + (0 if side == "player" else 19)) % 100) / 100.0 * 2 * math.pi


def breath_offset(t: float, side: str, slot: int, amplitude: float, period: float) -> int:
    return round(amplitude * math.sin(2 * math.pi * t / period + breath_phase(side, slot)))


def shake_offset(amplitude: float, duration: float, age: float) -> tuple[int, int]:
    """Deslocamento inteiro do quadro: oscilacao que decai ate zero em `duration`."""
    if duration <= 0 or age >= duration:
        return 0, 0
    decay = 1.0 - age / duration
    return (round(amplitude * decay * math.sin(age * SHAKE_HZ[0])),
            round(amplitude * decay * math.cos(age * SHAKE_HZ[1])))


def damage_style(amount: int, age: float, life: float, tm, damage: bool) -> tuple[int, int, float]:
    """(escala de fonte inteira, subida em px, calor 0..1) do numero flutuante.
    Surge com `pop_scale` x o tamanho base e encolhe em `pop_time`; sobe `rise` px."""
    dn = tm.damage_number
    big = damage and amount >= dn.big_threshold
    base = dn.big_scale if big else 2
    pop = dn.pop_time
    grow = dn.pop_scale - (dn.pop_scale - 1.0) * clamp01(age / pop) if pop > 0 else 1.0
    scale = max(1, round(base * grow))
    rise = round(dn.rise * ease_out(age / life)) if life > 0 else 0
    return scale, rise, 1.0 if big else 0.0


def poof_particles(slot_key: int, age: float, tm) -> list[tuple[int, int, int, int]]:
    """Particulas (dx, dy, tamanho, tipo) a partir do centro do gato. tipo 0 = pelo, 1 = fumaca.
    Angulo pelo angulo aureo, velocidade variada por indice: determinista, sem RNG."""
    pf = tm.poof
    k = clamp01(age / pf.life) if pf.life > 0 else 1.0
    out = []
    for i in range(int(pf.particles)):
        ang = (i + slot_key) * 2.399963
        spd = pf.speed * (0.45 + 0.55 * ((i * 7) % 5) / 4.0)
        d = spd * ease_out(k) * pf.life
        dx = round(math.cos(ang) * d)
        dy = round(math.sin(ang) * d * 0.8 - 18 * k)
        size = max(1, round((6 if i % 3 else 9) * (1.0 - k)))
        out.append((dx, dy, size, i % 2))
    return out


def hand_hover_factor(t: float, since: float, dur: float = 0.08) -> float:
    return ease_out((t - since) / dur) if dur > 0 else 1.0


def spread_dx(i: int, hover_i: int, spread: float) -> int:
    """Quanto a carta i se afasta da carta em foco: vizinhas 1x, as de 2 passos meio."""
    d = i - hover_i
    if d == 0 or abs(d) > 2:
        return 0
    return round((spread if abs(d) == 1 else spread / 2) * (1 if d > 0 else -1))


def gems_lit(mode: str, age: float, stagger: float, a: int, b: int) -> int:
    """Cristais acesos durante a animacao. `on`: a = energia final; acende um a um de 0.
    `off`: a = energia antes, b = depois; apaga um a um ate b."""
    steps = int(age / stagger) + 1 if stagger > 0 else 10**6
    if mode == "on":
        return min(a, steps - 1)
    return max(b, a - (steps - 1))
