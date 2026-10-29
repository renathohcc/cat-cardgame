"""Garante que a raiz do repositorio esta no sys.path (`import core` com `pytest` simples)."""
import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parent.parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def pytest_configure(config) -> None:
    config.addinivalue_line("markers", "slow: teste demorado (>20 s); roda por padrao, `-m 'not slow'` pula")


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def prefs_dir(tmp_path_factory, monkeypatch):
    """Isola as preferencias de audio: nenhum teste escreve em <repo>/saves/prefs.json.

    `audio.setup` leva PREFS_DIR como valor padrao (fixado na definicao), entao alem de trocar
    `audio.PREFS_DIR` ajustamos tambem o padrao da funcao."""
    try:
        from ui import audio
    except Exception:  # noqa: BLE001 - suites sem pygame/ui continuam rodando
        yield None
        return
    pasta = tmp_path_factory.mktemp("prefs_isoladas")
    monkeypatch.setattr(audio, "PREFS_DIR", pasta)
    monkeypatch.setattr(audio.setup, "__defaults__", (pasta, ()))
    yield pasta
