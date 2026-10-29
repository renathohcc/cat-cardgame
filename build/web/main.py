# /// script
# dependencies = [
# ]
# ///
"""Entrada do navegador (pygbag). Copiado para build/out/web/app/main.py por build_web.py."""
import asyncio
import random
import sys
from functools import partial
from pathlib import Path

import pygame  # noqa: F401  (o pygbag so baixa o wheel do pygame-ce se main.py importar pygame no topo)

EMSCRIPTEN = sys.platform == "emscripten"
# /data e a area persistente (IndexedDB) do pygbag; fora do navegador usa a pasta local.
HOME = Path("/data/data/chaoscats") if EMSCRIPTEN else Path(__file__).resolve().parent / "_user"


def _block_sdl2_window() -> None:
    """pygame._sdl2.video.Window.from_display_module() causa um trap de WebAssembly ("function signature
    mismatch", nao capturavel por try/except) no pygbag. ui/display.py o chama dentro de try/except Exception;
    aqui trocamos por um modulo falso que levanta ImportError normal. (Pedido de correcao em ui/: reports/T11.0.)"""
    import types

    fake = types.ModuleType("pygame._sdl2.video")

    def __getattr__(name: str):
        raise ImportError(name)

    fake.__getattr__ = __getattr__
    sys.modules["pygame._sdl2.video"] = fake


FILES = ("save.json", "prefs.json")


def _storage():
    """localStorage do navegador (o /data do pygbag nao sobreviveu a recarregar a pagina nos testes)."""
    import platform

    return platform.window.localStorage


def _restore() -> None:
    st = _storage()
    for name in FILES:
        val = st.getItem("chaoscats/" + name)
        if val:
            (HOME / name).write_text(str(val), encoding="utf-8")


async def _mirror() -> None:
    """A cada ~1 s copia save.json/prefs.json para o localStorage quando mudam."""
    st, last = _storage(), {}
    while True:
        for name in FILES:
            f = HOME / name
            if f.exists():
                txt = f.read_text(encoding="utf-8")
                if last.get(name) != txt:
                    st.setItem("chaoscats/" + name, txt)
                    last[name] = txt
        await asyncio.sleep(1.0)


async def main() -> None:
    HOME.mkdir(parents=True, exist_ok=True)
    if EMSCRIPTEN:
        _block_sdl2_window()
        try:
            _restore()
            asyncio.ensure_future(_mirror())
        except Exception as e:  # noqa: BLE001 - sem localStorage (modo privado): joga sem persistir
            print("sem localStorage:", e)
    from ui import audio
    from ui.app_hub import run

    audio.setup = partial(audio.setup, prefs_dir=HOME)
    await run(random.randrange(1, 10**6), HOME / "save.json")


asyncio.run(main())
