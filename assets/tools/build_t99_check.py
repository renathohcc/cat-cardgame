"""T9.9: check = T9.8 (grade, zonas, sobreposicao, paleta PEN, tamanhos) com os tapetes aplicados. Uso: python build_t99_check.py"""
import os
import runpy
import sys

sys.path.insert(0, os.path.dirname(__file__))
import build_t99_objects  # noqa: F401,E402  (aplica o patch dos tapetes antes do layout)

runpy.run_path(os.path.join(os.path.dirname(__file__), "build_t98_check.py"), run_name="__main__")
