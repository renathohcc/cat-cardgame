# Revisao da Fase 7 (Criatorio animado, T9.0 a T9.12)

Revisor independente, somente leitura. Data: 2026-10-29.

## Resultado do pytest (rodado de verdade)
- `python -m pytest -q` completo: **2847 passed, 33 warnings, 194 s**. Zero falhas, zero pulados.
- Warnings: DeprecationWarning de `Window.from_display_module()` em `ui/display.py:58,94` (pygame-ce). Nao e da Fase 7.
- Teste manual extra: `HubController(clock=datetime.now)` entrando no cercado, 2000 `update` e um draw: sem crash (periodo "dia", 10 gatos em cena).

## Recomendacao: PODE PASSAR O PORTAO, apos 2 ajustes de higiene antes do commit
Nenhum bloqueante de comportamento. Os dois itens bloqueantes abaixo sao de dados (rules.json) e de higiene do repositorio.

## Divergencias e achados

### Bloqueante (antes do commit/portao)
1. **Limites do cercado nao estao em `data/`.** `ui/pen_geometry.py:19` (`PEN_MAX_CATS = 16`) e `:24` (`ZONE_CAP = {"adultos": 10, "breed": 6, "filhotes": 6}`) estao hardcoded. `ui/hub_controller.py:129` le `rules.meta.pen_max_cats`, mas `data/rules.json` (bloco `meta`) nao tem a chave; `reports/T9.1-ui-criatorio-animado.md:27` ja pedia isso ao orquestrador/dados e nao foi feito. `ZONE_CAP` (10 adultos / 3 casais / 6 filhotes) nao tem como vir de JSON. Regra do CLAUDE.md: numeros de design nao ficam no codigo. Acao: agente dados adiciona `meta.pen_max_cats` e `meta.pen_zone_cap` em `data/rules.json` (+ schema) e a UI passa a ler. `tests/test_ui_pen_cobertura.py:39` trava `ZONE_CAP` literal e deve passar a comparar com o JSON. Os valores 10/3/6/16 vem do PLAN.md:105 (Renatho: "ate ~16"), nao do GDD; o GDD nao fixa numero, entao nao ha contradicao com ele.
2. **Arquivos soltos entrando no commit** (lista na secao propria): ~4 MB de backups de arte (`assets/pen/_v3.._v7`), originais crus (`_src*`), ~12 MB de previews em `reports/arte` e `reports/ui`, e `sim/ultimo_resultado.md` (nao e da Fase 7). Decidir antes do `git add`.

### Importante
3. **Codigo morto em `ui/render_pen.py:316-318`**: `row = hub.col.row_of(cat)` nunca usado e expressao `font.draw(... STATE_COLOR[row.state] ...) if False else None` (`STATE_COLOR` nao existe nem e importado; so nao quebra porque o ramo nunca roda). Remover.
4. **Codigo morto em `ui/pen_geometry.py`**: `sleep_spots`/`play_spots` (`:17-18`, `:136-137`, `:192-193`), `DEFAULT_SLEEP/PLAY`: nenhum uso fora do modulo (grep em `ui/`). Resquicio da T9.1.
5. **Render muda estado**: `ui/render_pen.py:310` (`hub.col.selected = cat.id` dentro de `draw_ficha`); ja e setado em `hub_controller.open_ficha`. Remover do render.
6. **Gato com a ficha aberta pode ser sorteado para sair na rotacao de 60 s.** `PenController._pick_tier` (`ui/pen_controller.py:171-194`) nao protege `self.held`. A ficha segue aberta, o gato some com fade e `ficha_rect` cai em x=0. Nao e crash, mas e estranho e nao ha teste. Sugestao: `held` sempre em `keep`.
7. **Deck de 12 adultos esgota a zona de adultos (cap 10).** `_choose` (`pen_controller.py:221-225`) prioriza o deck; com deck cheio os adultos fora do deck nunca aparecem e a rotacao so alterna entre os do deck. Pode ser a intencao ("deck em destaque", PLAN.md:105), mas na pratica a colecao nao usada nunca aparece. Duvida de design para o Renatho; nao decidi.
8. **`sync` a cada 0.5 s consome RNG.** `hub_controller.py:511-515` chama `pen.sync(...)`, que em overflow faz `self.rng.shuffle(pool)` (`pen_controller.py:189`) mesmo sem mudanca. Determinismo por seed segue (testes e cenas usam passo fixo), mas ao vivo o fluxo do RNG depende da taxa de quadros. Risco baixo.
9. **Loop real nao exercita o cercado com `datetime.now`.** `tests/test_ui_loops_reais.py:30-33`: com `hora=None` o hub fica em `menu` (nunca chama `enter_pen`), entao `PenController(clock=datetime.now)` + desenho nao e coberto no loop. Verifiquei manualmente que funciona, mas falta o teste que pegaria o bug de clock antigo. Sugestao ao agente testes: clicar Continuar com save e `clock=datetime.now`, N quadros.
10. **Pasta alheia alterada.** Segundo `reports/T9.1`, a UI editou `tests/test_ui_hub.py`, `test_ui_breed.py`, `test_ui_adocao.py` (pasta do agente testes). Os ajustes sao legitimos (Continuar agora vai ao cercado), mas contrariam "so altera a propria pasta". Registrar como excecao.
11. **PLAN.md sem checklist T9.0-T9.12**: so duas notas de decisao (linhas ~105-107); a linha 47 ainda descreve "Fase 7 - Balanceamento e polimento", contradizendo a nova ordem 7 Criatorio / 8 Build / 9 Conteudo. Orquestrador deve registrar tarefas e fechamento.
12. **Licencas Pixellab (`assets/LICENSES.md`)**: seguem pendentes as verificacoes da T8.7 (uso comercial no plano usado; disclosure de IA na Steam), agora ampliadas: T9.0 (`cats_pen.png`, gatos pen e filhotes) e T9.8 (~213 geracoes: camas, casinhas, banco, arranhador, tunel, cerca, arvores, tilesets) sao arte de IA no repositorio; originais em `assets/pen/_src*` (`_src98/LOG.md` com ids). Textos desatualizados: T9.0 e T9.2 citam `pen_bg.png` e `pen.json` "por script", mas hoje so existem `pen_bg_{amanhecer,dia,entardecer,noite}.png`, derivados de tiles Pixellab (T9.8) e recoloridos (T9.9); T9.4 e T9.7 ("sem IA") descrevem versoes substituidas e confundem auditoria. `_referencia_renatho.webp` esta em `assets/pen/`: se for imagem de terceiros, nao deve ir ao repo publico/build. Acao: Renatho confirma termos; arte consolida o LICENSES no estado final.

### Menor
13. `ui/render_pen.py:221` usa `-61` fixo (64-3) em vez de `frame_size`. `HIT_W/HIT_H` (`pen_controller.py:29`) e `OBJ_HIT_W/H` (`:30`) fixos: 56x30 serve mal a `cama_casal` (mais larga) e objetos altos; gato tem prioridade no clique, entao o erro e raro. Hit-test de gato (40x44 acima dos pes, o mais a frente por `-y`, desempate por id) esta correto.
14. `render_pen.py:97` expressao com numero magico sem comentario. `pen_sprites.py:165` e `:237` limpam o cache inteiro ao passar de 4000/2000 (soluco de quadro raro). `WALK_SPEED`, `ROTATE_S` e pesos de `_next` ficam no codigo: sao de apresentacao, aceitavel.
15. `hub_controller.pen_label` assume `self.col` nao nulo (sempre setado em `enter_pen`).
16. Dependencias: `assets/tools/*.py` (36 untracked) usam Pillow/numpy; conferir que estao so em requirements-dev (pendencia herdada da T8.7).
17. Duvidas abertas para o Renatho nos relatorios T9.7, T9.8, T9.9, T9.11 (ex.: camas sem sombra); o portao deve apresenta-las.

## Verificacoes sem problema
- **Fronteiras**: `core/` nao importa pygame nem `ui` (grep). `ui/pen_controller.py`, `ui/daycycle.py` e `ui/pen_geometry.py` nao importam pygame (puros). O cercado so le `save.cats`, `save.breeding` e `col.state_of`; doar/renomear passam pelo `CollectionController` (modais existentes). Nenhuma regra alterada.
- **RNG injetado**: `PenController(rng, ...)` usa so `self.rng`; sem `import random` global. `HubController` cria `Random(self.seed*31+7)` (`hub_controller.py:139`). `Random()` sem seed so aparece nos pontos de entrada (`ui/__main__.py:38`, `ui/demo.py`), padrao ja existente.
- **Relogio injetavel**: `clock=None` = 12:00 fixo; `datetime.now` so passado em `app_hub.run` (`:42`); cenas e screenshots usam `fixed_clock`. Recalculo a cada 30 s simulados. Crossfade na virada da meia-noite tratado por modulo (`daycycle.py:79`) e testado em `test_ui_daycycle.py`.
- **Caps**: 10 adultos / 3 casais (par inteiro) / 6 filhotes, total 16, prioridade breed > filhotes > adultos (deck antes), rotacao a cada 60 s mantendo limites, com testes (`test_ui_pen_cobertura.py:41-81`). Com 3 casais e 6 filhotes sobram so 4 vagas de adultos pelo teto de 16.
- **Fallback sem assets**: sheet (`pen_sprites.py:226`, cats96 com bob ou circulo), objetos (`_object_shape`), ambiente (`_ambient_shape`), fx (coracao por codigo), fundo (`draw_floor`) e geometria (`load_geometry` com `except Exception` -> padroes). Testado em T9.12.
- **Hit-tests**: ordem ficha > painel > gato > objeto > chao; ficha absorve cliques (`layout_pen.py:62`); modal bloqueia (`hub_controller._hit_pen`); slot nao cai no hitbox de outro objeto (testado).
- **Bug de clock antigo**: sem sombreamento; em `app_hub.run` o `pygame.time.Clock` e `clock` e o relogio do dia e `now_fn`. `draw_pen` usa `pen.time` e `pen.day`, sem `datetime`.
- **Determinismo**: mesma seed gera mesma cena (`test_cenas_sao_deterministicas_e_desenham`); ordenacao com desempate por `cat_id`.
- **GDD**: filhote na zona propria por `stage == "kitten"` (GDD 101-106); sem compra de gatos; sem racao/decoracao (GDD 190-191 adiado; PLAN exclui); hub = Criatorio com acesso a Run, Colecao, Adocao, Breed (GDD 183).

## Arquivos soltos / que nao devem entrar no commit sem decisao
- `assets/pen/_v3`, `_v4` (1.5 MB), `_v5`, `_v6`, `_v7`: backups de arte (~4 MB).
- `assets/pen/_src` (2.1 MB), `_src96`, `_src98`, `_src99`: originais crus de IA; uteis como prova de origem, mas excluir do build.
- `assets/pen/_referencia_renatho.webp` (checar origem).
- `assets/tools/build_t90*.py a build_t99*.py` (36 scripts), muitos de versoes mortas (T9.4, T9.6, T9.7).
- `reports/arte/preview_pen_*.png` (~7.9 MB, 28 imagens) e `reports/ui/criatorio_*.png`, `quintal_*.png` (4.6 MB): manter so os finais (camas v8, cena v7, 4 quintais).
- `sim/ultimo_resultado.md`: nao e da Fase 7.
- Obrigatorios: `ui/daycycle.py`, `ui/layout_pen.py`, `ui/pen_controller.py`, `ui/pen_geometry.py`, `ui/pen_sprites.py`, `ui/render_pen.py`, `tests/test_ui_pen.py`, `tests/test_ui_pen_cobertura.py`, `tests/test_ui_daycycle.py`, `tests/test_ui_loops_reais.py`, arquivos finais de `assets/pen/` (png/json, PALETA_PEN, palette_pen.json), `reports/T9.*.md`, e os modificados (PLAN.md, assets/LICENSES.md, ui/*, tests/test_ui_adocao.py, test_ui_breed.py, test_ui_hub.py).

## Riscos
- Hardcode de caps (item 1) impede ajuste por dados.
- Peso do repo/build por `_src*`, `_v*` e previews; pygbag tem limite pratico de tamanho.
- Licenca/uso comercial de arte Pixellab nao confirmada (item 12).
- Performance: `_separate` e O(n^2) com 3 passadas sobre no maximo 16 gatos, desprezivel.

## O que esta bom
- Controlador do cercado puro, determinista, com relogio e RNG injetaveis e boa cobertura (33 testes novos, daycycle, loops reais).
- Fallback em todas as camadas de arte e geometria.
- Fluxo do hub (Continuar/ESC/adocao/breed/resultado para o cercado) coberto por testes reescritos.
- Suite completa verde (2847).
