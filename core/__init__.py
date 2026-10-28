"""Core do jogo: regras puras, sem pygame."""
from core.cats import cat_stats, roll_cat
from core.content import load_content
from core.run import Run, new_run
from core.types import Cat, Content, Stage, Stats

__all__ = ["load_content", "roll_cat", "cat_stats", "Cat", "Content", "Stage", "Stats", "Run", "new_run"]
