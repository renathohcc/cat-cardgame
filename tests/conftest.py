"""Garante que a raiz do repositorio esta no sys.path (`import core` com `pytest` simples)."""
import sys
from pathlib import Path

ROOT = str(Path(__file__).resolve().parent.parent)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def pytest_configure(config) -> None:
    config.addinivalue_line("markers", "slow: teste demorado (>20 s); roda por padrao, `-m 'not slow'` pula")
