# PyInstaller spec (Windows, onedir, sem console). Rode via build/build_pc.py (define CHAOSCATS_STAGE).
import os
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

HERE = Path(SPECPATH)
STAGE = Path(os.environ["CHAOSCATS_STAGE"])

datas = [(str(STAGE / "data"), "data"), (str(STAGE / "assets"), "assets")]
datas += collect_data_files("jsonschema_specifications") + collect_data_files("jsonschema")
hidden = collect_submodules("ui") + collect_submodules("core") + ["jsonschema_specifications"]

a = Analysis(
    [str(HERE / "launcher_pc.py")],
    pathex=[str(STAGE)],
    datas=datas,
    hiddenimports=hidden,
    excludes=["tkinter", "pytest", "PIL", "numpy", "unittest"],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Chaoscats", console=bool(os.environ.get("CHAOSCATS_CONSOLE")), upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name="Chaoscats", upx=False)
