"""Audio da UI: efeitos por cue, musica por contexto, volumes, mudo e preferencias.

Pensado para a UI chamar so `audio.sfx("ui_click")` / `audio.music("duelo")`:
  - o `AudioManager` le `data/audio.json`, escolhe variacoes com um `random.Random` injetado,
    aplica cooldown por cue com relogio injetavel e cuida da troca de musica (fade);
  - o mixer fica atras de um `Backend`: `PygameBackend` (real, init protegido) ou `NullBackend`
    (silencio). Sem dispositivo de audio, sem arquivo ou com qualquer erro, tudo vira no-op;
  - o gerenciador padrao do modulo e silencioso (testes/capturas); os apps instalam o real
    com `setup()`. Nada de threads; a troca de musica anda em `update()` (chamado por quadro).
Variaveis de ambiente: CHAOSCATS_AUDIO=off (sem audio) | fail (simula falha do mixer).
"""
from __future__ import annotations

import json
import os
import random
import time
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any, Protocol

ROOT = Path(__file__).resolve().parent.parent
CATALOG_PATH = ROOT / "data" / "audio.json"
AUDIO_DIR = ROOT / "assets" / "audio"
PREFS_NAME = "prefs.json"
# Pasta unica das preferencias (a mesma do save padrao do jogo), em todos os modos.
PREFS_DIR = ROOT / "saves"
RETRY_MS = 2000
VOLUME_STEP = 0.1
FADE_MS = 600
FADE_OUT_MS = 300


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


# ------------------------------------------------------------------ backends
class Backend(Protocol):
    available: bool

    def load_sound(self, path: Path) -> Any | None: ...
    def play_sound(self, sound: Any, volume: float) -> None: ...
    def music_start(self, path: Path, loop: bool, volume: float, fade_ms: int) -> bool: ...
    def music_stop(self) -> None: ...
    def music_set_volume(self, volume: float) -> None: ...


class NullBackend:
    """Silencio total: nada carrega, nada toca."""
    available = False

    def load_sound(self, path: Path) -> Any | None:
        return None

    def play_sound(self, sound: Any, volume: float) -> None:
        return None

    def music_start(self, path: Path, loop: bool, volume: float, fade_ms: int) -> bool:
        return False

    def music_stop(self) -> None:
        return None

    def music_set_volume(self, volume: float) -> None:
        return None


class PygameBackend:
    """pygame.mixer com init protegido: se falhar, `available` fica False e tudo e no-op."""

    def __init__(self) -> None:
        self.available = False
        self._pg: Any = None
        self.disabled = os.environ.get("CHAOSCATS_AUDIO", "").lower() == "off"
        self.try_init()

    def try_init(self) -> bool:
        """(Re)tenta iniciar o mixer; nunca levanta. Devolve `available`."""
        if self.available:
            return True
        mode = os.environ.get("CHAOSCATS_AUDIO", "").lower()
        try:
            if mode == "off":
                self.disabled = True
                return False
            if mode == "fail":
                raise RuntimeError("falha de mixer simulada")
            import pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            self._pg = pygame
            self.available = bool(pygame.mixer.get_init())
        except Exception:  # noqa: BLE001 - sem dispositivo/driver: o jogo segue mudo
            self.available = False
        return self.available

    def load_sound(self, path: Path) -> Any | None:
        if not self.available or not path.is_file():
            return None
        try:
            return self._pg.mixer.Sound(str(path))
        except Exception:  # noqa: BLE001
            return None

    def play_sound(self, sound: Any, volume: float) -> None:
        try:
            sound.set_volume(_clamp(volume))
            sound.play()
        except Exception:  # noqa: BLE001
            pass

    def music_start(self, path: Path, loop: bool, volume: float, fade_ms: int) -> bool:
        if not self.available or not path.is_file():
            return False
        try:
            m = self._pg.mixer.music
            m.load(str(path))
            m.set_volume(_clamp(volume))
            m.play(-1 if loop else 0, 0.0, fade_ms)
            return True
        except Exception:  # noqa: BLE001
            return False

    def music_stop(self) -> None:
        if self.available:
            try:
                self._pg.mixer.music.stop()
            except Exception:  # noqa: BLE001
                pass

    def music_set_volume(self, volume: float) -> None:
        if self.available:
            try:
                self._pg.mixer.music.set_volume(_clamp(volume))
            except Exception:  # noqa: BLE001
                pass


# ------------------------------------------------------------------ catalogo e prefs
def load_catalog(path: Path = CATALOG_PATH) -> dict:
    """Le data/audio.json; qualquer problema vira catalogo vazio (jogo mudo)."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def read_prefs(path: Path | None) -> dict:
    """Leitura tolerante: ausente/corrompido/valores invalidos -> {} (usa os padroes)."""
    if path is None:
        return {}
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}
    if not isinstance(raw, dict):
        return {}
    out: dict = {}
    for key in ("music", "sfx"):
        v = raw.get(key)
        if isinstance(v, (int, float)) and not isinstance(v, bool) and v == v:
            out[key] = _clamp(v)
    if isinstance(raw.get("muted"), bool):
        out["muted"] = raw["muted"]
    return out


def write_prefs(path: Path | None, prefs: dict) -> bool:
    """Escrita atomica (tmp + replace). Devolve False se nao deu (sem derrubar o jogo)."""
    if path is None:
        return False
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps({"version": 1, **prefs}, indent=2), encoding="utf-8")
        os.replace(tmp, path)
        return True
    except Exception:  # noqa: BLE001
        return False


def default_clock_ms() -> float:
    return time.monotonic() * 1000.0


# ------------------------------------------------------------------ gerenciador
class AudioManager:
    def __init__(self, backend: Backend | None = None, catalog: dict | None = None,
                 audio_dir: Path = AUDIO_DIR, rng: random.Random | None = None,
                 clock_ms: Callable[[], float] = default_clock_ms,
                 prefs_path: Path | None = None,
                 prefs_fallbacks: tuple[Path, ...] = ()) -> None:
        self.backend: Backend = backend or NullBackend()
        self.catalog = load_catalog() if catalog is None else catalog
        self.audio_dir = Path(audio_dir)
        self.rng = rng or random.Random()
        self.clock_ms = clock_ms
        self.prefs_path = Path(prefs_path) if prefs_path is not None else None
        vols = self.catalog.get("volumes", {})
        self.default_music = _clamp(vols.get("musica", 0.7))
        self.default_sfx = _clamp(vols.get("efeitos", 0.8))
        self.music_volume = self.default_music
        self.sfx_volume = self.default_sfx
        self.muted = False
        self.requests: Counter[str] = Counter()     # cues pedidos (mesmo em cooldown/silencio)
        self.total_requests = 0
        self.context: str | None = None
        self.track: str | None = None               # faixa alvo
        self.playing: str | None = None             # faixa realmente tocando
        self._last_ms: dict[str, float] = {}
        self._cache: dict[str, Any | None] = {}
        self._fade_out_until: float | None = None   # musica atual sumindo antes de trocar
        self._last_retry_ms: float | None = None
        prefs: dict = {}
        if self.prefs_path is None or not self.prefs_path.is_file():
            for old in prefs_fallbacks:         # caminho antigo: so leitura
                prefs = read_prefs(old)
                if prefs:
                    break
        else:
            prefs = read_prefs(self.prefs_path)
        self.apply_prefs(prefs)

    # -------------------------------------------------------------- mixer tardio
    def retry_backend(self) -> bool:
        """Tenta iniciar o mixer (ex.: navegador so libera audio apos um gesto).
        Limitado a 1 tentativa a cada RETRY_MS; ao iniciar, retoma a musica do contexto."""
        be = self.backend
        if be.available or getattr(be, "disabled", True) or not hasattr(be, "try_init"):
            return False
        now = self.clock_ms()
        if self._last_retry_ms is not None and now - self._last_retry_ms < RETRY_MS:
            return False
        self._last_retry_ms = now
        if not be.try_init():
            return False
        self._cache.clear()
        if self.track is not None and self._fade_out_until is None:
            self._start_track()
        return True

    # -------------------------------------------------------------- prefs
    def apply_prefs(self, prefs: dict) -> None:
        self.music_volume = prefs.get("music", self.music_volume)
        self.sfx_volume = prefs.get("sfx", self.sfx_volume)
        self.muted = prefs.get("muted", self.muted)
        self._apply_music_volume()

    def save_prefs(self) -> bool:
        return write_prefs(self.prefs_path, {"music": round(self.music_volume, 2),
                                             "sfx": round(self.sfx_volume, 2), "muted": self.muted})

    # -------------------------------------------------------------- volumes
    def volume_of(self, which: str) -> float:
        return self.music_volume if which == "musica" else self.sfx_volume

    def set_volume(self, which: str, value: float) -> None:
        v = round(_clamp(value), 2)
        if which == "musica":
            self.music_volume = v
        else:
            self.sfx_volume = v
        self._apply_music_volume()
        self.save_prefs()

    def adjust_volume(self, which: str, steps: int) -> float:
        """Soma `steps` passos de 10% (arredonda para o multiplo de 10%)."""
        cur = round(self.volume_of(which) / VOLUME_STEP)
        self.set_volume(which, (cur + steps) * VOLUME_STEP)
        return self.volume_of(which)

    def set_muted(self, muted: bool) -> None:
        self.muted = bool(muted)
        self._apply_music_volume()
        self.save_prefs()

    def toggle_mute(self) -> bool:
        self.set_muted(not self.muted)
        return self.muted

    def _track_volume(self) -> float:
        if self.muted:
            return 0.0
        base = self.catalog.get("music", {}).get(self.playing or "", {}).get("volume", 1.0)
        return _clamp(self.music_volume * base)

    def _apply_music_volume(self) -> None:
        if self._fade_out_until is None:
            self.backend.music_set_volume(self._track_volume())

    # -------------------------------------------------------------- efeitos
    def _sound(self, rel: str) -> Any | None:
        if rel not in self._cache:
            self._cache[rel] = self.backend.load_sound(self.audio_dir / rel)
        return self._cache[rel]

    def play(self, cue: str) -> bool:
        """Toca o cue (variacao sorteada). Devolve True se mandou tocar de fato."""
        self.requests[cue] += 1
        self.total_requests += 1
        spec = self.catalog.get("sfx", {}).get(cue)
        if not spec or not spec.get("files"):
            return False
        now = self.clock_ms()
        cd = spec.get("cooldown_ms", 0)
        last = self._last_ms.get(cue)
        if cd and last is not None and now - last < cd:
            return False
        self._last_ms[cue] = now
        files = list(spec["files"])
        first = self.rng.randrange(len(files))
        if self.muted or not self.backend.available:
            return False
        for rel in files[first:] + files[:first]:       # se a variacao falta, tenta a outra
            snd = self._sound(rel)
            if snd is not None:
                self.backend.play_sound(snd, self.sfx_volume * _clamp(spec.get("volume", 1.0)))
                return True
        return False

    # -------------------------------------------------------------- musica
    def music_for(self, context: str) -> str | None:
        return self.catalog.get("contexts", {}).get(context)

    def set_context(self, context: str) -> None:
        """Pede a musica do contexto. Mesma faixa ja tocando/pedida: nao faz nada."""
        self.context = context
        track = self.music_for(context)
        if track is None or track == self.track:
            return
        self.track = track
        if self.playing is None:
            self._start_track()
        elif self._fade_out_until is None:
            self._fade_out_until = self.clock_ms() + FADE_OUT_MS

    def _start_track(self) -> None:
        self._fade_out_until = None
        spec = self.catalog.get("music", {}).get(self.track or "")
        self.playing = None
        if not spec:
            return
        self.playing = self.track
        ok = self.backend.music_start(self.audio_dir / spec["file"], bool(spec.get("loop", True)),
                                      self._track_volume(), FADE_MS)
        if not ok:
            self.playing = None

    def stop_music(self) -> None:
        self.track = self.playing = self.context = None
        self._fade_out_until = None
        self.backend.music_stop()

    def update(self, dt: float = 0.0) -> None:
        """Anda a troca de musica (fade-out da atual, depois fade-in da nova)."""
        if self._fade_out_until is None:
            return
        left = self._fade_out_until - self.clock_ms()
        if left > 0:
            frac = left / FADE_OUT_MS
            self.backend.music_set_volume(self._track_volume() * frac)
            return
        self.backend.music_stop()
        self.playing = None
        self._start_track()


# ------------------------------------------------------------------ gerenciador global
_current: AudioManager = AudioManager()


def manager() -> AudioManager:
    return _current


def install(mgr: AudioManager) -> AudioManager:
    global _current
    _current = mgr
    return mgr


def setup(prefs_dir: Path | str | None = PREFS_DIR,
          legacy_dirs: tuple[Path | str, ...] = ()) -> AudioManager:
    """Instala o gerenciador real (mixer protegido); prefs em `<prefs_dir>/prefs.json`
    (padrao: PREFS_DIR, igual em todos os modos). `legacy_dirs`: pastas antigas lidas se faltar."""
    path = Path(prefs_dir) / PREFS_NAME if prefs_dir is not None else None
    old = tuple(Path(d) / PREFS_NAME for d in legacy_dirs)
    return install(AudioManager(PygameBackend(), prefs_path=path, prefs_fallbacks=old))


def on_event(ev: Any) -> None:
    """Chamar para cada evento pygame: no 1o clique/tecla (e a cada ~2 s) tenta o mixer de novo."""
    if getattr(ev, "type", None) in _GESTURES:
        _current.retry_backend()


_GESTURES = {1025, 768, 1792}   # MOUSEBUTTONDOWN, KEYDOWN, FINGERDOWN


def sfx(cue: str) -> None:
    _current.play(cue)


def music(context: str) -> None:
    _current.set_context(context)


def update(dt: float = 0.0) -> None:
    _current.update(dt)


# ------------------------------------------------------------------ hover
NO_HOVER = {"pen_floor", "pen_obj", "pen_cat", "row", "slot", "hand", "leader", "none", "scroll"}


class HoverSound:
    """Toca ui_hover quando o mouse passa a apontar para outro botao."""

    def __init__(self) -> None:
        self.last: tuple | None = None

    def update(self, elem: tuple | None) -> None:
        if elem == self.last:
            return
        self.last = elem
        if elem is not None and elem[0] not in NO_HOVER:
            sfx("ui_hover")


def handle_key(key: int, typing: bool = False) -> bool:
    """Tecla M alterna o mudo (exceto digitando texto). Recebe o codigo da tecla (pygame.K_m = 109)."""
    if key == 109 and not typing:
        _current.toggle_mute()
        return True
    return False
