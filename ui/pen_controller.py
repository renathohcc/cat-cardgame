"""Cercado vivo do Criatorio: tres zonas (adultos, casais em breed, filhotes), gatos e objetos.

Pura (sem pygame), tempo por `dt`, sorteio so com o `Random` injetado. Sem regra de jogo: decide onde
cada gato anda, dorme ou brinca. Cada gato vive SO na sua zona. Posicao (x, y) = PES do gato.

Objetos (camas, novelo...) tem slots; um gato por slot. O gato reserva um slot livre compativel, anda
ate la e usa (dorme/brinca) ate cansar. Casais em breed dormem juntos no `cama_casal` (2 slots).
Elenco por zona: `zone_caps`, total `max_cats` (vindos de rules.meta); o que nao cabe e sorteado e rotacionado a cada 60 s.
"""
from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from random import Random

from ui import daycycle
from ui.pen_geometry import BED_KINDS, FALLBACK_MAX_CATS, FALLBACK_ZONE_CAPS, MOVER_KINDS, ZONES, ObjectSpec, PenGeometry

ROTATE_S = 60.0
WALK_SPEED = 30.0            # px/s
KITTEN_SPEED = 38.0
FADE_S = 0.6
REACT_S = 1.8
HEART_TTL = 1.4
SEP_RX, SEP_RY = 38.0, 15.0  # elipse de separacao entre gatos
PARTNER_RX = 30.0
HIT_W, HIT_H = 40, 44
OBJ_HIT_W, OBJ_HIT_H = 56, 30
OBJ_POKE_S = 2.5
LOVE_EVERY = 3.0


@dataclass
class PenEntry:
    cat_id: str
    breed: str
    kitten: bool = False
    tag: str = "livre"            # breed | filhote | deck | livre
    partner: str | None = None

    @property
    def zone(self) -> str:
        if self.tag == "breed":
            return "breed"
        return "filhotes" if self.kitten or self.tag == "filhote" else "adultos"


@dataclass
class PenCat:
    cat_id: str
    breed: str
    kitten: bool
    tag: str
    partner: str | None
    x: float
    y: float
    zone: str = "adultos"
    state: str = "idle"
    timer: float = 2.0
    tx: float = 0.0
    ty: float = 0.0
    goal: str | None = None       # o que fazer ao chegar: "sleep" | "play" | None
    obj: int | None = None        # indice do objeto reservado
    slot: int | None = None       # indice do slot reservado
    facing: int = 1               # +1 direita, -1 esquerda
    t: float = 0.0                # relogio de animacao
    fade: float = 0.0             # 0..1 (aparecendo); leaving -> desce
    leaving: bool = False
    hearts_left: int = 0
    heart_cd: float = 0.0
    love_cd: float = LOVE_EVERY

    @property
    def anim(self) -> str:
        if self.state in ("walk", "sleep", "play"):
            return self.state
        return "idle"


@dataclass
class PenObject:
    spec: ObjectSpec
    zone: str
    index: int
    occ: dict[int, str] = field(default_factory=dict)     # slot -> cat_id
    t: float = 0.0
    ox: float = 0.0
    oy: float = 0.0
    boost: float = 0.0            # >0: anima "use" mesmo sem gato (clique)
    rect: tuple[float, float, float, float] | None = None     # zona (x0, y0, x1, y1): limita os slots
    oneshot: str | None = None    # cama: "enter" (gato deita) | "exit" (gato levanta), tocado uma vez
    oneshot_t: float = 0.0
    sleepers: int = 0

    @property
    def is_bed(self) -> bool:
        return self.spec.kind in BED_KINDS

    @property
    def kind(self) -> str:
        return self.spec.kind

    @property
    def using(self) -> bool:
        return bool(self.occ) or self.boost > 0

    def slot_pos(self, slot: int) -> tuple[float, float]:
        dx, dy = self.spec.slots[slot]
        x, y = self.spec.x + dx, self.spec.y + dy
        if self.rect is not None:
            x0, y0, x1, y1 = self.rect
            x, y = min(max(x, x0 + 8), x1 - 8), min(y, y1)      # offset negativo (telhado, banco) e livre
        return x, y


@dataclass
class Heart:
    x: float
    y: float
    age: float = 0.0
    ttl: float = HEART_TTL


class PenController:
    def __init__(self, rng: Random, geo: PenGeometry | None = None, max_cats: int = FALLBACK_MAX_CATS,
                 clock: Callable[[], datetime] | None = None, zone_caps: dict[str, int] | None = None) -> None:
        self.rng = rng
        self.clock = clock                    # None = meio-dia fixo (deterministico); o jogo passa datetime.now
        self.day = daycycle.day_state(clock() if clock else None)
        self._day_acc = 0.0
        self.geo = geo or PenGeometry()
        self.max_cats = max_cats
        self.zone_caps = dict(zone_caps or FALLBACK_ZONE_CAPS)
        ax, ay, aw, ah = self.geo.walk_area
        self.area = (float(ax), float(ay), float(ax + aw), float(ay + ah))      # uniao das zonas
        self.rects = {z: (float(r[0]), float(r[1]), float(r[0] + r[2]), float(r[1] + r[3]))
                      for z, r in ((z, self.geo.zones[z].rect) for z in ZONES)}
        self.objects: list[PenObject] = []
        for z in ZONES:
            for spec in self.geo.zones[z].objects:
                self.objects.append(PenObject(spec, z, len(self.objects), rect=self.rects[z]))
        self.cats: list[PenCat] = []
        self.hearts: list[Heart] = []
        self.entries: dict[str, PenEntry] = {}
        self.shown: list[str] = []
        self.held: str | None = None          # gato parado (ficha aberta)
        self.rotate_clock = 0.0
        self.time = 0.0

    # ------------------------------------------------------------ elenco
    def sync(self, entries: list[PenEntry], rotate: bool = False) -> None:
        """Atualiza o elenco: quem sai some com fade, quem entra nasce numa posicao sorteada."""
        self.entries = {e.cat_id: e for e in entries}
        self.shown = self._choose(entries, rotate)
        want = set(self.shown)
        for c in self.cats:
            if c.leaving:
                continue
            if c.cat_id not in want or self.entries[c.cat_id].zone != c.zone:
                c.leaving = True                      # saiu, ou mudou de zona (some e reaparece la)
                self._release(c)
            else:
                e = self.entries[c.cat_id]
                c.breed, c.kitten, c.tag, c.partner = e.breed, e.kitten, e.tag, e.partner
        live = {c.cat_id for c in self.cats if not c.leaving}
        for cid in self.shown:
            if cid not in live:
                self.cats.append(self._spawn(self.entries[cid]))

    def _pick_tier(self, units: list[tuple[str, ...]], room: int, rotate: bool) -> list[tuple[str, ...]]:
        if sum(len(u) for u in units) <= room:
            return units
        prev = set(self.shown)
        keep = [u for u in units if u[0] in prev]
        dropped: list[tuple[str, ...]] = []
        pinned = [u for u in keep if self.held in u]          # ficha aberta: nunca sai na rotacao
        rot = [u for u in keep if u not in pinned]
        if rotate and rot:
            dropped = self.rng.sample(rot, math.ceil(len(rot) / 2))
            keep = [u for u in keep if u not in dropped]
        keep = pinned + [u for u in keep if u not in pinned]      # ficha aberta tem prioridade de vaga
        out: list[tuple[str, ...]] = []
        used = 0
        for u in keep:
            if used + len(u) <= room:
                out.append(u)
                used += len(u)
        pool = sorted((u for u in units if u not in out and u not in dropped), key=lambda u: u[0])
        if used + sum(len(u) for u in pool) < room:
            pool = sorted((u for u in units if u not in out), key=lambda u: u[0])
        self.rng.shuffle(pool)
        for u in pool:
            if used + len(u) <= room:
                out.append(u)
                used += len(u)
        return out

    @staticmethod
    def _units(entries: list[PenEntry], zone: str) -> list[tuple[str, ...]]:
        """Unidades de sorteio da zona: casais (par inteiro) em breed, individuos nas demais."""
        mine = [e for e in entries if e.zone == zone]
        ids = {e.cat_id for e in mine}
        out: list[tuple[str, ...]] = []
        seen: set[str] = set()
        for e in mine:
            if e.cat_id in seen:
                continue
            if zone == "breed" and e.partner in ids:
                out.append(tuple(sorted((e.cat_id, e.partner))))
                seen.update((e.cat_id, e.partner))
            else:
                out.append((e.cat_id,))
                seen.add(e.cat_id)
        return out

    def _choose(self, entries: list[PenEntry], rotate: bool) -> list[str]:
        chosen: list[str] = []
        for zone in ("breed", "filhotes", "adultos"):
            room = min(self.zone_caps[zone], self.max_cats - len(chosen))
            if room <= 0:
                continue
            units = self._units(entries, zone)
            if zone == "adultos":
                deck = {e.cat_id for e in entries if e.tag == "deck"}
                tiers = [[u for u in units if u[0] in deck], [u for u in units if u[0] not in deck]]
            else:
                tiers = [units]
            for tier in tiers:
                got = self._pick_tier(tier, room, rotate)
                ids = [i for u in got for i in u]
                chosen += ids
                room -= len(ids)
        return chosen

    def counts(self) -> dict[str, tuple[int, int]]:
        """Por zona: (em cena, total). CASAIS conta casais; as demais, gatos."""
        out: dict[str, tuple[int, int]] = {}
        for z in ZONES:
            tot = [e for e in self.entries.values() if e.zone == z]
            sh = [i for i in self.shown if self.entries[i].zone == z]
            out[z] = (len(sh) // 2, len(tot) // 2) if z == "breed" else (len(sh), len(tot))
        return out

    def _spawn(self, e: PenEntry) -> PenCat:
        x0, y0, x1, y1 = self.rects[e.zone]
        c = PenCat(e.cat_id, e.breed, e.kitten, e.tag, e.partner,
                   self.rng.uniform(x0 + 16, max(x0 + 17, x1 - 16)), self.rng.uniform(y0 + 30, max(y0 + 31, y1)),
                   zone=e.zone, timer=self.rng.uniform(0.5, 3.0), facing=self.rng.choice((-1, 1)))
        c.t = self.rng.uniform(0, 4)
        c.love_cd = self.rng.uniform(1.0, LOVE_EVERY)
        return c

    def cat(self, cat_id: str) -> PenCat | None:
        for c in self.cats:
            if c.cat_id == cat_id and not c.leaving:
                return c
        return None

    def ordered(self) -> list[PenCat]:
        """Ordem de desenho: do fundo (y menor) para a frente."""
        return sorted(self.cats, key=lambda c: (self.sort_y(c), c.cat_id))

    def sort_y(self, c: PenCat) -> float:
        """Chave de profundidade: gato ancorado num slot acima da base do objeto (telhado, banco)
        e desenhado DEPOIS do objeto, entao nunca fica escondido atras dele."""
        if self._anchored(c):
            return max(c.y, self.objects[c.obj].spec.y + 0.01)
        return c.y

    # ------------------------------------------------------------ entrada
    def rect_of(self, c: PenCat) -> tuple[int, int, int, int]:
        return (int(c.x) - HIT_W // 2, int(c.y) - HIT_H, HIT_W, HIT_H)

    def hit(self, pos: tuple[int, int]) -> str | None:
        """Id do gato sob `pos` (o da frente, se houver varios)."""
        px, py = pos
        for c in sorted((c for c in self.cats if not c.leaving), key=lambda c: (-c.y, c.cat_id)):
            x, y, w, h = self.rect_of(c)
            if x <= px < x + w and y <= py < y + h:
                return c.cat_id
        return None

    def hit_object(self, pos: tuple[int, int]) -> int | None:
        """Indice do objeto sob `pos` (o da frente)."""
        px, py = pos
        for o in sorted(self.objects, key=lambda o: -o.spec.y):
            if not o.spec.slots:                       # decorativo (tigela, casinha_filhote): nao clicavel
                continue
            x, y = o.spec.x + o.ox, o.spec.y + o.oy
            if x - OBJ_HIT_W / 2 <= px < x + OBJ_HIT_W / 2 and y - OBJ_HIT_H <= py < y + 4:
                return o.index
        return None

    def poke(self, cat_id: str) -> bool:
        """Clique no gato: acorda, para um instante e solta coracoes."""
        c = self.cat(cat_id)
        if c is None:
            return False
        self._release(c)
        c.state, c.timer, c.goal = "react", REACT_S, None
        c.hearts_left, c.heart_cd = 3, 0.0
        return True

    def poke_object(self, index: int) -> bool:
        """Clique no objeto: ele anima e o gato livre mais proximo vem brincar (se for de brincar)."""
        if not 0 <= index < len(self.objects):
            return False
        o = self.objects[index]
        o.boost = OBJ_POKE_S
        if o.spec.slot_use != "play":
            return True
        free = [i for i in range(len(o.spec.slots)) if i not in o.occ]
        cands = [c for c in self.cats if not c.leaving and c.zone == o.zone and c.cat_id != self.held
                 and c.state in ("idle", "walk") and c.obj is None]
        if free and cands:
            c = min(cands, key=lambda c: (math.hypot(c.x - o.spec.x, c.y - o.spec.y), c.cat_id))
            self._reserve(c, o, free[0], "play")
        return True

    def hold(self, cat_id: str | None) -> None:
        self.held = cat_id
        c = self.cat(cat_id) if cat_id else None
        if c is not None:
            self._release(c)
            c.state, c.timer, c.goal = "react", 0.5, None

    # ------------------------------------------------------------ tempo
    def advance(self, seconds: float, step: float = 1 / 30) -> None:
        """Simula `seconds` em passos fixos (screenshots deterministicos)."""
        n = int(seconds / step)
        for _ in range(n):
            self.update(step)
        rest = seconds - n * step
        if rest > 1e-9:
            self.update(rest)

    def update(self, dt: float) -> None:
        self.time += dt
        self._day_acc += dt
        if self._day_acc >= daycycle.RECALC_S:
            self.refresh_day()
        if self.entries:
            self.rotate_clock += dt
            if self.rotate_clock >= ROTATE_S:
                self.rotate_clock = 0.0
                self.sync(list(self.entries.values()), rotate=True)
        for c in self.cats:
            self._step(c, dt)
        self.cats = [c for c in self.cats if not (c.leaving and c.fade <= 0.0)]
        self._separate()
        self._objects(dt)
        self._hearts(dt)

    def refresh_day(self) -> None:
        """Recalcula o periodo do dia pelo relogio (chamado a cada ~30 s)."""
        self._day_acc = 0.0
        self.day = daycycle.day_state(self.clock() if self.clock else None)

    def _step(self, c: PenCat, dt: float) -> None:
        c.t += dt
        if c.leaving:
            c.fade = max(0.0, c.fade - dt / FADE_S)
            return
        c.fade = min(1.0, c.fade + dt / FADE_S)
        if c.hearts_left > 0:
            c.heart_cd -= dt
            if c.heart_cd <= 0:
                c.hearts_left -= 1
                c.heart_cd = 0.35
                self.hearts.append(Heart(c.x + self.rng.uniform(-8, 8), c.y - 40))
        self._love(c, dt)
        if c.cat_id == self.held:
            c.state, c.timer = "react", 0.5
            return
        c.timer -= dt
        if c.state == "walk":
            self._walk(c, dt)
        elif c.timer <= 0:
            self._next(c)

    def _love(self, c: PenCat, dt: float) -> None:
        """Casais soltam coracoes entre si de tempos em tempos (so o de menor id, para nao dobrar)."""
        mate = self.cat(c.partner) if c.partner and c.zone == "breed" else None
        if mate is None or c.cat_id > mate.cat_id:
            return
        c.love_cd -= dt
        if c.love_cd <= 0:
            c.love_cd = LOVE_EVERY + self.rng.uniform(0, 1.5)
            if math.hypot(c.x - mate.x, c.y - mate.y) < 70:
                self.hearts.append(Heart((c.x + mate.x) / 2, min(c.y, mate.y) - 40))

    def _walk(self, c: PenCat, dt: float) -> None:
        sp = (KITTEN_SPEED if c.kitten else WALK_SPEED) * dt
        dx, dy = c.tx - c.x, c.ty - c.y
        d = math.hypot(dx, dy)
        if d <= sp + 0.5 or c.timer <= 0:
            if d <= sp + 0.5:
                c.x, c.y = c.tx, c.ty
            self._arrive(c, d <= sp + 0.5)
            return
        c.x += dx / d * sp
        c.y += dy / d * sp
        if abs(dx) > 0.5:
            c.facing = 1 if dx > 0 else -1

    def _arrive(self, c: PenCat, reached: bool) -> None:
        goal, c.goal = c.goal, None
        if goal and reached and c.obj is not None:
            self._face_slot(c)
            if goal == "sleep":
                c.state, c.timer = "sleep", self.rng.uniform(8, 18)
            else:
                c.state, c.timer = "play", self.rng.uniform(4, 9)
            return
        self._release(c)
        c.state, c.timer = "idle", self.rng.uniform(1.5, 4.0)

    def _face_slot(self, c: PenCat) -> None:
        """Brinquedo: slot a esquerda, gato olha a direita. Casal: o segundo gato espelha."""
        o = self.objects[c.obj]
        if o.kind == "cama_casal":
            c.facing = 1 if c.slot == 0 else -1
        elif o.spec.slot_use == "play" and o.spec.slots[c.slot][0] != 0:
            c.facing = 1 if o.spec.slots[c.slot][0] < 0 else -1

    # ------------------------------------------------------------ slots
    def _release(self, c: PenCat) -> None:
        if c.obj is not None:
            occ = self.objects[c.obj].occ
            for k in [k for k, v in occ.items() if v == c.cat_id]:
                del occ[k]
        c.obj = c.slot = None

    def _free_slots(self, c: PenCat, use: str) -> list[tuple[int, int]]:
        return [(o.index, s) for o in self.objects if o.zone == c.zone and o.spec.slot_use == use
                for s in range(len(o.spec.slots)) if s not in o.occ]

    def _reserve(self, c: PenCat, o: PenObject, slot: int, goal: str) -> None:
        self._release(c)
        o.occ[slot] = c.cat_id
        c.obj, c.slot = o.index, slot
        x, y = o.slot_pos(slot)
        self._go(c, x, y, goal, clamp=False)

    def _couple_bed(self, c: PenCat, mate: PenCat) -> PenObject | None:
        if mate.state not in ("idle", "walk") or mate.goal or mate.obj is not None or mate.cat_id == self.held:
            return None
        beds = [o for o in self.objects if o.zone == c.zone and o.spec.slot_use == "sleep"
                and o.kind == "cama_casal" and len(o.spec.slots) >= 2 and not o.occ]
        return self.rng.choice(beds) if beds else None

    # ------------------------------------------------------------ decisao
    def _next(self, c: PenCat) -> None:
        """Escolhe o proximo estado (sorteio ponderado com o rng injetado)."""
        self._release(c)
        mate = self.cat(c.partner) if c.partner and c.zone == "breed" else None
        follower = mate is not None and c.cat_id > mate.cat_id
        sleep_k, play_k = self.day.activity()          # a noite dorme mais, de dia brinca mais
        opts: list[tuple[str, float]] = [("idle", 2.5), ("walk", 5.0 if not c.kitten else 6.0)]
        bed = None
        sleep_free = self._free_slots(c, "sleep")
        play_free = self._free_slots(c, "play")
        if mate is not None:
            if not follower:
                bed = self._couple_bed(c, mate)
                if bed is not None:
                    opts.append(("couple", 2.5 * sleep_k))
        else:
            if sleep_free:
                opts.append(("sleep", (1.2 if not c.kitten else 2.0) * sleep_k))
            if play_free:
                opts.append(("play", (1.0 if not c.kitten else 3.5) * play_k))
        total = sum(w for _, w in opts)
        r = self.rng.uniform(0, total)
        pick = opts[-1][0]
        for name, w in opts:
            r -= w
            if r <= 0:
                pick = name
                break
        if pick == "idle":
            c.state, c.timer = "idle", self.rng.uniform(1.5, 4.0)
        elif pick == "walk":
            self._go(c, *self._wander_target(c), None)
        elif pick == "couple" and bed is not None and mate is not None:
            self._release(mate)
            self._reserve(c, bed, 0, "sleep")
            self._reserve(mate, bed, 1, "sleep")
        else:
            oi, si = self.rng.choice(sleep_free if pick == "sleep" else play_free)
            self._reserve(c, self.objects[oi], si, pick)

    def _wander_target(self, c: PenCat) -> tuple[float, float]:
        mate = self.cat(c.partner) if c.partner else None
        if mate is not None and mate.state != "sleep" and self.rng.random() < 0.65:
            return mate.x + self.rng.choice((-1, 1)) * self.rng.uniform(30, 50), mate.y + self.rng.uniform(-8, 8)
        x0, y0, x1, y1 = self.rects[c.zone]
        return self.rng.uniform(x0 + 16, x1 - 16), self.rng.uniform(y0 + 30, y1)

    def _go(self, c: PenCat, x: float, y: float, goal: str | None, clamp: bool = True) -> None:
        if clamp:
            x0, y0, x1, y1 = self.rects[c.zone]
            x, y = min(max(x, x0), x1), min(max(y, y0 + 26), y1)
        c.tx, c.ty = x, y
        c.goal, c.state, c.timer = goal, "walk", 14.0

    # ------------------------------------------------------------ separacao
    @staticmethod
    def _anchored(c: PenCat) -> bool:
        return c.obj is not None and c.state in ("sleep", "play")

    def _separate(self) -> None:
        cats = [c for c in self.cats if not c.leaving]
        for _ in range(3):
            for i in range(len(cats)):
                for j in range(i + 1, len(cats)):
                    if cats[i].zone == cats[j].zone:
                        self._push(cats[i], cats[j])
        for c in cats:
            if not self._anchored(c):
                x0, y0, x1, y1 = self.rects[c.zone]
                c.x, c.y = min(max(c.x, x0), x1), min(max(c.y, y0 + 26), y1)

    def _push(self, a: PenCat, b: PenCat) -> None:
        mates = a.partner == b.cat_id or b.partner == a.cat_id
        rx = PARTNER_RX if mates else SEP_RX
        dx, dy = a.x - b.x, a.y - b.y
        if dx == 0 and dy == 0:                           # sobrepostos exatos: desempate deterministico
            dx = 1.0 if a.cat_id < b.cat_id else -1.0
        d = math.hypot(dx / rx, dy / SEP_RY)
        if d >= 1.0:
            return
        over = (1.0 - d) * 0.6
        ux, uy = dx / rx / max(d, 1e-6), dy / SEP_RY / max(d, 1e-6)
        mx, my = ux * rx * over, uy * SEP_RY * over
        a_fixed = self._anchored(a) or a.cat_id == self.held
        b_fixed = self._anchored(b) or b.cat_id == self.held
        if a_fixed and b_fixed:
            return
        ka, kb = (0.0, 2.0) if a_fixed else ((2.0, 0.0) if b_fixed else (1.0, 1.0))
        a.x += mx * ka
        a.y += my * ka
        b.x -= mx * kb
        b.y -= my * kb

    # ------------------------------------------------------------ objetos e efeitos
    def _objects(self, dt: float) -> None:
        """Relogio dos objetos; novelo/ratinho/bola se mexem de leve enquanto alguem brinca."""
        for o in self.objects:
            o.t += dt
            moving = o.kind in MOVER_KINDS and o.using
            tx = math.sin(o.t * 1.9 + o.index) * 9 if moving else 0.0
            ty = math.cos(o.t * 1.4 + o.index * 2) * 3 if moving else 0.0
            k = min(1.0, dt * 4)
            o.ox += (tx - o.ox) * k
            o.oy += (ty - o.oy) * k
            o.boost = max(0.0, o.boost - dt)
            self._bed_oneshot(o, dt)

    def _bed_oneshot(self, o: PenObject, dt: float) -> None:
        """Cama: dispara `enter` quando o 1o gato comeca a deitar e `exit` quando o ultimo levanta."""
        if not o.is_bed:
            return
        n = sum(1 for c in self.cats if c.obj == o.index and c.state == "sleep" and not c.leaving)
        if n > 0 and o.sleepers == 0:
            o.oneshot, o.oneshot_t = "enter", 0.0
        elif n == 0 and o.sleepers > 0:
            o.oneshot, o.oneshot_t = "exit", 0.0
        o.sleepers = n
        o.oneshot_t += dt

    def _hearts(self, dt: float) -> None:
        for h in self.hearts:
            h.age += dt
            h.y -= 14 * dt
        self.hearts = [h for h in self.hearts if h.age < h.ttl]
