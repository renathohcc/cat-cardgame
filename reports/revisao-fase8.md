# Revisao Fase 8 (Som e musica, T10.0 a T10.3)

Revisor independente, somente leitura. `python -m pytest -q`: **3041 passed** (35 warnings, 216 s), igual ao esperado.

## Recomendacao: PODE passar o portao, com 2 ajustes de higiene antes do commit (B1, B2). Nenhum bloqueio de regra.

## Bloqueantes (antes do commit/portao)
- B1. `assets/audio/_src/` (22 MB de brutos) nao esta no `.gitignore` (`.gitignore` so ignora .venv, saves, etc.) e aparece como `?? assets/audio/`. Um `git add` normal leva os 22 MB ao repositorio. Pedir ao orquestrador/Renatho para adicionar `assets/audio/_src/` ao `.gitignore` (arquivo da raiz, fora da pasta do agente de arte). Total de `assets/audio` = 29 MB; sem `_src` = ~7 MB (sfx 496 KB, music 6,5 MB), aceitavel.
- B2. Pendencia legal ja registrada, nao resolvida: autoria/licenca CC0 de 14+ autores do OpenGameArt nao verificada (`assets/LICENSES.md:63`, `assets/audio/CREDITS.md`). Nao bloqueia o portao da fase, mas e bloqueante para lancamento na Steam. Alem disso, ninguem ouviu os arquivos (T10.2): a escolha foi so numerica.

## Importantes
- I1. Web/pygbag (Fase 9): `PygameBackend.__init__` (`ui/audio.py:70-85`) faz `pygame.mixer.init()` uma unica vez, em `audio.setup()` no inicio de `run()` (`ui/app.py:49`, `ui/app_hub.py:36`, `ui/app_run.py:36`). No navegador o audio so inicia apos gesto do usuario; se o init falhar ali, `available` fica False para sempre (sem retentativa) e a sessao inteira fica muda. Sugestao Fase 9: tentar `mixer.init` de novo no primeiro clique/tecla se `available` for False (lazy init), ou garantir a tela "clique para iniciar" do pygbag antes do `setup`. Nada disso foi testado no web.
- I2. Web: `music.play(loops, 0.0, fade_ms)` e `music.set_volume` por quadro durante o fade (`audio.py:109, 325`), alem de `mixer.music.load` de OGG de 64-143 s (6,5 MB baixados no carregamento): verificar no pygbag (suporte a fade_ms e tempo de carga). Como mitigacao, o fade pode ser feito so por set_volume. `saves/` (prefs) no web: `Path(__file__).parent.parent / "saves"` (`ui/app.py:49`, `app_run.py:36` via DEFAULT_SAVE) precisa ser area gravavel/IDBFS; falha de escrita ja e silenciosa (`audio.py:170`), mas o volume nao persistiria.
- I3. Jingle vs cue: no fim de duelo dentro da run, `duel_victory`/`duel_defeat` (`ui/controller.py:853`) tocam ao mesmo tempo em que `audio_context` muda para `fim_*` e a faixa `vitoria`/`derrota` entra (fade-out 300 ms, depois jingle 600 ms fade-in). Na pratica o cue de ~2 s sobrepoe o inicio do jingle de 8-12 s; e musical e provavelmente confuso. Nao ha teste de sobreposicao. Decisao de design/audio do Renatho (o T10.2 ja alertou).
- I4. Prefs divergem de pasta: `app_hub` grava ao lado do save (`app_hub.py:36`), `app.py`/`app_run.py` em `<repo>/saves` (`app.py:49`, `app_run.py:36`). Com `--save` customizado, o volume nao e compartilhado entre modos. Menor, mas inconsistente.
- I5. `PenController.sounds` (`ui/pen_controller.py:135,311,364,590`, drenado em `ui/hub_controller.py:323-330, 351, 609`): fora do cercado nada e acumulado pelo `update` (so roda em modo cercado, `hub_controller.py:348-351`) e o `del self.sounds[:-16]` limita a fila, entao nao ha vazamento de memoria. Resta o efeito ja citado em T10.3: sons de clique (`pet`, `purr`) enfileirados e nao tocados se o modo mudar no mesmo quadro; no `_drain_pen_sounds` o descarte fora do cercado (linha 328) na verdade esvazia a fila (`self.pen.sounds = []`), entao o relato do T10.3 ("podem tocar ao voltar") so vale se ninguem drenar: ocorre no `update` do hub, apenas em cercado. Impacto desprezivel; o relatorio e a implementacao divergem, ajustar a nota.
- I6. Teste fraco de cobertura (T10.3 admite): `coin`, `adopt`, `breed_start`, `kitten_born`, `level_up`, `shield_protected`, `duelo_chefe` real sem teste de fluxo. A logica `_sound_after` (`hub_controller.py:300-321`) e heuristica por diferenca de estado (sobe moedas -> coin, etc.), fragil a mudancas de UI; so e testada nos caminhos curtos.

## Menores
- M1. Mapeamento `colecao/breed/adocao -> faixas` e `shield_protected` para "Provocar bloqueia" sao escolhas dos agentes (T10.0, T10.1), nao do GDD. Marcar para o Renatho aprovar. GDD nao diz nada sobre audio (nao ha regra do GDD violada nem exigida).
- M2. `data/audio.json`: schema nao checa contexts apontando para faixas inexistentes (T10.0 ja cita); `version` em vez de `schema_version`.
- M3. `audio.py:365` `NO_HOVER` e `handle_key` (`audio.py:384`) usam constante magica 109 em vez de `pygame.K_m` (de proposito, para nao importar pygame; comentario cobre).
- M4. `AudioManager.__init__` cria `random.Random()` sem seed (`audio.py:187`) quando nao injetado; os apps nao injetam, entao o sorteio de variacao nao e reproduzivel em producao (so afeta som; os testes injetam). Aceitavel, nao toca no RNG de jogo.
- M5. Codigo morto: `Backend.music_set_volume` ok; `HoverSound`/`volume_of` usados; `NullBackend` usado como padrao. Nao encontrei codigo morto relevante. Dependencias de dev (numpy, scipy, soundfile, pyloudnorm) fora do `requirements.txt` e registradas no T10.2 e no LICENSES, conforme CLAUDE.md.
- M6. Musicas curtas repetidas (menu_dia 25 s x3 etc.) e chiptune em `mapa_run`: qualidade, decisao do Renatho.

## Conferencias que estao OK
- `core/` nao importa pygame nem audio (grep em `core/`: so docstring em `core/__init__.py:1`).
- Sorteio: variacao de sfx usa `self.rng` injetavel (`audio.py:275`); cercado usa `audio_rng` proprio (`pen_controller.py:134`, semeado `seed*53+11` em `hub_controller.py:146`), separado de `self.rng` do comportamento; o miado so consome `audio_rng`, entao o determinismo do cercado nao muda. Nenhum `random` global.
- Fallback silencioso: arquivo ausente (`is_file`, `try/except`), mixer falhando/`CHAOSCATS_AUDIO=off|fail`, sem dispositivo (`available False`), catalogo ausente/corrompido (`load_catalog` -> `{}`), prefs corrompidas (`read_prefs`), cue desconhecido (retorna False). Padrao do modulo e silencioso, testes nao tocam.
- Prefs: `saves/prefs.json`, fora do save e do core, escrita atomica tmp + `os.replace` (`audio.py:159-171`), leitura tolerante e com clamp; `saves/` esta no `.gitignore`.
- Tecla M: `audio.handle_key(key, typing)`; o hub passa `hub.editing_text` (`app_hub.py:67`, `hub_controller.py:554`, cobre renomear na colecao/cercado); duelo e run nao tem entrada de texto. `disp.handle_key` (fullscreen) tem prioridade.
- Licencas: CREDITS.md cita os 51 arquivos finais com fonte, autor, CC0, alteracoes (teste `test_audio_assets` cobre); secao Audio em `assets/LICENSES.md:60-63` com a pendencia de verificar autoria.
- Formato OGG Vorbis (compativel com pygbag); sfx mono pequenos, 51/51 existem.
- Pastas: audio em `ui/`, `data/`, `assets/`, `tests/` por donos corretos; relatorios T10.0 a T10.3 presentes. Nao encontrei alteracao de pasta alheia nos relatorios.
- Testes: `tests/test_ui_audio.py` e `tests/test_audio_assets.py` testam comportamento real (cooldown, variacao, troca de faixa, prefs round-trip, M com `editing_text`, arquivos).
