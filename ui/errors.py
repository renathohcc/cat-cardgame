"""Log de erros em arquivo e tela de falha amigavel (T12.4).

`log_exception` grava o traceback com data em `errors.log`, na mesma pasta dos saves/prefs
(`audio.PREFS_DIR`). Rotacao simples: passando de ~200 KB o arquivo vira `errors.old.log`
(sobrescreve o antigo) e comeca outro. Qualquer falha de escrita (disco cheio, web/pygbag sem
sistema de arquivos) e ignorada em silencio: o log nunca derruba o jogo.

`guarded(coro)` envolve um loop async: excecao nao tratada e gravada, o jogo mostra uma mensagem
curta (qualquer tecla/clique fecha) e termina sem traceback seco. Em testes (pytest carregado) ou
com `CHAOSCATS_DEBUG=1` a excecao e relancada depois de gravada.
"""
from __future__ import annotations

import asyncio
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

import pygame

from ui import audio, font
from ui.theme import C, H, W

LOG_NAME = "errors.log"
OLD_NAME = "errors.old.log"
MAX_BYTES = 200 * 1024
SHOW_SECONDS = 60.0


def log_path() -> Path:
    return Path(audio.PREFS_DIR) / LOG_NAME


def _rotate(p: Path) -> None:
    try:
        if p.exists() and p.stat().st_size > MAX_BYTES:
            os.replace(p, p.with_name(OLD_NAME))
    except OSError:
        pass


def log_exception(exc: BaseException, where: str = "", path: Path | None = None) -> bool:
    """Acrescenta o traceback ao log. Devolve False se nao deu para gravar (nunca levanta)."""
    if sys.platform == "emscripten" and path is None:
        return False
    try:
        p = Path(path) if path is not None else log_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        _rotate(p)
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        head = f"=== {stamp} {where}".rstrip() + " ===\n"
        body = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        with p.open("a", encoding="utf-8") as f:
            f.write(head + body + "\n")
        return True
    except Exception:  # noqa: BLE001 - log nunca derruba o jogo
        return False


def reraise_mode() -> bool:
    return "pytest" in sys.modules or bool(os.environ.get("CHAOSCATS_DEBUG"))


def draw_crash(surf: pygame.Surface, exc: BaseException, logged: bool) -> None:
    surf.fill(C["bg"])
    r = pygame.Rect(W // 2 - 300, H // 2 - 110, 600, 220)
    pygame.draw.rect(surf, C["panel"], r, border_radius=8)
    pygame.draw.rect(surf, C["bad"], r, 3, border_radius=8)
    font.draw(surf, "ALGO DEU ERRADO", r.centerx, r.y + 22, C["bad"], 2, "center")
    font.draw(surf, "O jogo precisa fechar.", r.centerx, r.y + 70, C["text"], 1, "center")
    where = f"Detalhes em {LOG_NAME}" if logged else "Não consegui gravar o log de erro."
    font.draw(surf, where, r.centerx, r.y + 92, C["dim"], 1, "center")
    msg = f"{type(exc).__name__}: {exc}".replace("\n", " ")
    font.draw(surf, font.fit(msg, r.w - 40), r.centerx, r.y + 124, C["warn"], 1, "center")
    font.draw(surf, "Pressione qualquer tecla ou clique para sair", r.centerx, r.bottom - 30, C["text"], 1, "center")


async def crash_screen(exc: BaseException, logged: bool) -> None:
    """Mostra a falha ate uma tecla/clique/fechar (ou SHOW_SECONDS). Nunca levanta."""
    try:
        canvas = pygame.Surface((W, H))
        draw_crash(canvas, exc, logged)
        clock = pygame.time.Clock()
        waited = 0.0
        while waited < SHOW_SECONDS:
            waited += clock.tick(30) / 1000.0
            if any(ev.type in (pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN) for ev in pygame.event.get()):
                break
            surf = pygame.display.get_surface()
            if surf is not None:
                from ui.display import render_scaled
                render_scaled(canvas, surf)
                pygame.display.flip()
            await asyncio.sleep(0)
    except Exception:  # noqa: BLE001
        pass


async def guarded(coro, where: str = "loop") -> None:
    """Executa o loop; excecao nao tratada vira log + tela de falha (ou relanca em modo debug)."""
    try:
        await coro
    except Exception as e:  # noqa: BLE001
        logged = log_exception(e, where)
        if reraise_mode():
            raise
        await crash_screen(e, logged)
        try:
            pygame.quit()
        except Exception:  # noqa: BLE001
            pass
