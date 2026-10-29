"""Ciclo do dia do cercado, pela hora do computador. Puro (sem pygame), testavel.

Periodos: noite 19:30-05:00, amanhecer 05:00-08:00, dia 08:00-17:00, entardecer 17:00-19:30.
Nas fronteiras ha um crossfade de FADE_MIN minutos (centrado na fronteira). `DayState` diz o
periodo atual, o proximo e a mistura 0..1 entre eles.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

PERIODS = ("amanhecer", "dia", "entardecer", "noite")
# (minuto do dia em que o periodo COMECA, periodo)
BOUNDS = ((5 * 60, "amanhecer"), (8 * 60, "dia"), (17 * 60, "entardecer"), (19 * 60 + 30, "noite"))
FADE_MIN = 30.0                  # duracao do crossfade
RECALC_S = 30.0                  # a UI recalcula a cada ~30 s
LIT_PERIODS = ("entardecer", "noite")        # lanternas acesas
# multiplicadores de sorteio do gato: (dormir, brincar)
ACTIVITY = {"amanhecer": (1.0, 1.1), "dia": (0.6, 1.5), "entardecer": (1.3, 0.8), "noite": (3.0, 0.35)}
DEFAULT_MINUTE = 12 * 60         # sem relogio injetado: meio-dia (deterministico)


@dataclass(frozen=True)
class DayState:
    period: str
    next: str
    mix: float = 0.0             # 0 = so `period`, 1 = so `next`

    def weights(self) -> dict[str, float]:
        w = {p: 0.0 for p in PERIODS}
        w[self.period] += 1.0 - self.mix
        w[self.next] += self.mix
        return w

    @property
    def dominant(self) -> str:
        return self.next if self.mix >= 0.5 else self.period

    def weight_of(self, periods) -> float:
        """Peso (0..1) da soma dos periodos dados; `None`/vazio = todos."""
        if not periods:
            return 1.0
        w = self.weights()
        return min(1.0, sum(w.get(p, 0.0) for p in periods))

    @property
    def lit(self) -> float:
        """Intensidade 0..1 das lanternas (acesas so no entardecer e na noite)."""
        return self.weight_of(LIT_PERIODS)

    def activity(self) -> tuple[float, float]:
        """Multiplicadores (dormir, brincar), misturados pelo crossfade."""
        w = self.weights()
        return (sum(ACTIVITY[p][0] * v for p, v in w.items()), sum(ACTIVITY[p][1] * v for p, v in w.items()))


def minute_of(now: datetime) -> float:
    return now.hour * 60 + now.minute + now.second / 60.0


def period_at(minute: float) -> str:
    cur = BOUNDS[-1][1]
    for start, name in BOUNDS:
        if minute >= start:
            cur = name
    return cur


def _smooth(x: float) -> float:
    return x * x * (3 - 2 * x)


def day_state(now: datetime | float | None = None) -> DayState:
    """Estado do dia para um `datetime` local (ou minuto do dia). None = meio-dia."""
    m = DEFAULT_MINUTE if now is None else (minute_of(now) if isinstance(now, datetime) else float(now) % 1440)
    half = FADE_MIN / 2
    for i, (start, nxt) in enumerate(BOUNDS):
        prev = BOUNDS[i - 1][1]
        d = (m - start + 720) % 1440 - 720            # distancia assinada ate a fronteira
        if -half <= d < half:
            return DayState(prev, nxt, _smooth((d + half) / FADE_MIN))
    p = period_at(m)
    return DayState(p, p, 0.0)


def parse_hora(text: str) -> datetime:
    """'HH:MM' -> datetime de hoje com essa hora (para `--hora`)."""
    try:
        h, mi = (int(n) for n in text.strip().split(":"))
        return datetime(2000, 1, 1, h, mi)
    except (ValueError, TypeError) as e:
        raise ValueError(f"hora invalida: {text!r} (use HH:MM)") from e


def fixed_clock(text: str):
    """Relogio fixo para testes/capturas."""
    dt = parse_hora(text)
    return lambda: dt
