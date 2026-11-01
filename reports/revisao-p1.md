# Revisao da Fase P1 (T12.6)

Revisor independente, somente leitura. `python -m pytest -q` (Python do sistema): **3290 passed, 2 xpassed, 44 warnings** em 233 s. Os 2 xpassed sao os xfail dos bugs da T12.5 (entrada do chefe e fade), ja corrigidos na T12.5b; falta so tirar a marca. Nenhum teste falhou.

## Recomendacao
**Pode passar o portao**, com os itens medios abaixo registrados como divida (nenhum quebra regra do GDD).

## Achados

### Alta
Nenhum.

### Media
1. **Numeros magicos de duracao/animacao ainda em `ui/`** (viola "todo tempo em `data/`"): `ui/controller.py:43` `AI_DELAY = 0.5`; `:44` e `:222` `INTRO_TIME = 2.4` (duplica `boss_intro.duration`, e o `:222` ainda o devolve em algum caminho); `:242`, `:969`, `:1038` `over_t` 0.8; `:775-817` vidas de Fx (0.6, 0.4, 0.95, 0.8, 0.32, 0.36, 0.5, e `+0.05` em `:877`); `ui/render_fx.py:168` (0.22), `:200-223` (0.3, 0.45, 0.6 da entrada do chefe), `:72`, `:83`; `ui/anim.py:11` `IMPACT_FRAC`, `:97` `dur=0.08` do foco da mao, `:88-91`. Parte vem de antes da P1, mas as da P1 (foco da mao, entrada do chefe, impacto) deviam estar no JSON.
2. **`docs/CONTRATOS.md` nao documenta `preview_attack`/`preview_card`** (grep sem resultado). API publica nova do `core` sem contrato; o texto sugerido esta em `reports/T12.1-preview.md`. Decisao do Renatho (docs e dele).
3. **Mudanca de comportamento do Esc** (Criatorio e mapa abrem a pausa em vez de ir ao menu / abrir "Abandonar?"): coerente e documentada em `T12.4`, mas muda fluxo existente; precisa de OK do Renatho.
4. **`apply_action` refatorado em `_validate/_do_action/_after_action`** (`core/duel.py:282-312`): ordem identica a antes (validar, agir, `_stall_scan`, `_check_deadlock`, `duel.log.extend`). Sem divergencia achada e coberto pela suite (3290 verdes, mais comparacao prévia x real em `tests/test_preview_core.py`). Marco como media so porque e o unico ponto onde regra poderia ter mudado em silencio; o diff nao mostra mudanca.
5. **Lacunas de teste que importam**: sem teste de pixel da investida, do poof, da entrada do chefe, do hover da mao nem de `keep_clear`; impasse por estagnacao na previa so implicito; Esc do hub em run testado por atribuicao manual de `hub.mode`. Sao testes que passariam mesmo se o efeito sumisse.

### Baixa
6. `ui/controller.py` tem 1078 linhas (limite pratico estourado; cresceu com a P1). `ui/render.py` 822, `ui/pen_controller.py` 600. Dividir antes da proxima fase de UI.
7. Loops `app.py`, `app_run.py`, `app_hub.py` ainda repetem o tratamento de eventos de mouse/arrastar; so F11/mudo/pausa foram para `Shell`. Divida reconhecida em T12.4.
8. Codigo morto: `Transition._cur` (`ui/transition.py:27, 51`) nunca e usado; `pass` solto em `ui/controller.py` (`dismiss_dice`, apos `self.ai_t = 0.0`); constante `INTRO_TIME` (ver 1).
9. `core/duel.py` `_cat_before` usa `assert isinstance(action, PlayCat)` em codigo de producao; se um evento apontar slot vazio fora de PlayCat, vira AssertionError em vez de `IllegalAction`. Nao ocorreu em 103 mil previas, mas e fragil.
10. `app.py`: `press` pode ficar velho se a pausa abrir com o botao pressionado (MOUSEUP e consumido pelo `Shell`). Efeito: no maximo um clique fantasma raro ao voltar.
11. Entrada do chefe mostra retrato e nome, **sem fala** (a proposta dizia "com fala curta"). Registrado em T12.3 como "Sem falas".
12. `errors.reraise_mode` depende de `"pytest" in sys.modules`; ok, mas qualquer ferramenta que importe pytest em producao desligaria a tela de falha. Aceitavel.

## Itens abertos conhecidos, classificados
| Item | Classe | Nota |
| --- | --- | --- |
| Botoes do duelo e painel de volume do menu no estilo antigo | baixa (polimento) | migrar precisa de decisao de arte (9-slice); entrar na P2 |
| Tooltip da mao cobrindo parte do Lider | baixa | a carta ampliada ja respeita `keep_clear`; so o tooltip cobre |
| `poof_miadinho` inexistente, usa `cat_death` | baixa | cue novo e tarefa do agente de audio/dados |
| `big_threshold` usa `>=`, proposta diz "acima de" | baixa, decidir | `ui/anim.py:71`. Com 5 o valor atual (5) conta como grande; decidir se vale 5 ou 6 |
| Esc no Criatorio/mapa abre a pausa | media | ver achado 3 |
| Texto de `preview_*` fora do CONTRATOS | media | ver achado 2 |

## Conferencias por item
1. **Regras intactas**: `git diff` de `core/` so adiciona previa e divide `apply_action`; nenhuma regra do GDD tocada. `docs/` nao foi alterado (so propostas novas). OK.
2. **Pureza**: `grep` em `core/` sem `pygame`, sem `ui`, sem `random` global. Previa roda em `deepcopy` (rng incluido) e os testes conferem duelo e `rng.getstate()` intactos. `preview_card` devolve `None` se o efeito usar sorteio. OK.
3. **Dados**: `ui_timing.json` + schema estrito (`additionalProperties:false`), 1 exemplo valido e 4 invalidos, `check_ui_timing`, fallback por chave em `ui/timing.py` (arquivo ausente/corrompido/valor invalido). Boa. Ressalva: achado 1. Os `DEFAULTS` duplicam o JSON (dois lugares para afinar); um teste confere igualdade.
4. **Robustez**: pausa congela `ctrl.update`, `ui.t` e o mouse (`app.py:109-113`, `shell.sync`); fade e intro pulaveis e o evento segue para o jogo (`Shell.handle`); precedencia do Esc documentada e testada; `write_prefs` mescla e e atomico; prefs antigas/corrompidas caem no padrao; `errors.log_exception` nunca levanta e retorna sem gravar no emscripten. Sem dependencia nova. OK.
5. **Determinismo**: tremor, hitstop e velocidade do inimigo so mexem em `dt` e desenho; a IA usa `ai_rng` proprio e as acoes nao dependem do tempo. Testes: tremor on/off e 1x/2x/rapido dao o mesmo vencedor e HP.
6. Codigo: ver 6 a 8.
7. Testes: 241 novos, nao vacuos (comparam previa com `apply_action`). Ver 5.

## O que esta bom
- Previa sem segunda implementacao das regras (mesmo `_do_action` numa copia), validada em 103 mil casos e por testes a mao das regras do GDD.
- `ui/timing.py`: fallback seguro por chave, injetavel nos testes, sem RNG nem thread (compativel com pygbag).
- Pausa, opcoes, prefs e log de erros com tratamento de falha em todo I/O.
- Os dois bugs achados pelo testador (intro e fade) foram corrigidos e verificados.
- Pastas respeitadas: `core/` (agente core), `data/`, `tests/`, `ui/`, relatorios por tarefa presentes (T12.0 a T12.5b).

## O que falta decidir pelo Renatho
1. Confirmar Esc abrindo a pausa no Criatorio e no mapa; e SAIR DO JOGO pedir confirmacao so dentro da run.
2. `big_threshold`: `>=` (atual) ou "acima de".
3. Incluir `preview_*` em `docs/CONTRATOS.md`.
4. Entrada do chefe com fala ou sem fala (a proposta pedia fala).
5. Botoes antigos do duelo e painel de volume: P2 ou ja na P1?
