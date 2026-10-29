# Build do Chaoscats

Tudo roda a partir da raiz do repo, num venv **fora do repo** (ex.: `%TEMP%\chaoscats-build`):

```
python -m venv %TEMP%\chaoscats-build
%TEMP%\chaoscats-build\Scripts\pip install -r build\requirements-build.txt
```

## PC (Windows, PyInstaller --onedir, sem console)

```
%TEMP%\chaoscats-build\Scripts\python build\build_pc.py
```
Saida: `build/out/pc/dist/Chaoscats/Chaoscats.exe` (distribuir a pasta `Chaoscats/` inteira).
Save e prefs ficam em `%APPDATA%\Chaoscats\` (`CHAOSCATS_HOME` troca a pasta). Flags do jogo passam direto
(`Chaoscats.exe --hora 22:00`). `CHAOSCATS_CONSOLE=1` antes do build gera uma versao com console para depurar;
`CHAOSCATS_AUDIO=off` desliga o audio em execucao.

## Navegador (pygbag)

```
%TEMP%\chaoscats-build\Scripts\python build\build_web.py           # so gera
%TEMP%\chaoscats-build\Scripts\python build\build_web.py --serve   # gera e serve em http://localhost:8000
```
Pacote publicavel: `build/out/web/app/build/web/` (index.html + app.apk). Precisa de internet (o runtime
WebAssembly e o wheel do pygame-ce vem de pygame-web.github.io). **Nao** abra o index.html com
`python -m http.server`: os wheels sao pedidos em `/cdn/` e so o servidor do proprio pygbag atende.

`build/stage.py` faz a copia filtrada (sem `_*`, `assets/tools`, reports, docs, tests, sim, saves).
`build/web/main.py` e `build/web/jsonschema.py` entram so no pacote web (ver `reports/T11.0-build.md`).
