# CONTRATOS — formatos de dados e API pública do core

**Status: RASCUNHO v0.1 (aguardando aprovação do Renatho).** Nada aqui cria regra nova: todo número vem do GDD. Onde o GDD é omisso, o campo existe mas o valor está marcado `PENDENTE` e listado em "Dúvidas" no fim.

Convenções: JSON em UTF-8, `snake_case` nas chaves em inglês, textos de jogo em português, ids em `kebab-case` ASCII (ex.: `vira-lata`). Todo arquivo de `data/` tem `"schema_version": 1` e é validado por `data/schemas/<nome>.schema.json`.

---

## 1. Formatos JSON (`data/`)

### 1.1 Keyword — `data/keywords.json`

```json
{
  "schema_version": 1,
  "keywords": [
    {"id": "provocar", "nome": "Provocar", "texto": "O adversário precisa derrotar este gato antes de atacar o Líder."},
    {"id": "investida", "nome": "Investida", "texto": "Pode atacar no turno em que entra."},
    {"id": "primeira-patada", "nome": "Primeira Patada", "texto": "Causa dano dobrado no primeiro ataque."},
    {"id": "robusto", "nome": "Robusto", "texto": "Recupera 1 HP no fim de cada turno seu."}
  ]
}
```

O comportamento de cada keyword é código do `core`, indexado pelo `id`. O JSON só guarda id e texto. Parâmetros numéricos (ex.: "1 HP") ficam em `params` quando a keyword os tiver (`{"id":"robusto", ..., "params":{"cura":1}}`).

### 1.2 Raça — `data/breeds.json`

```json
{
  "schema_version": 1,
  "breeds": [
    {"id": "vira-lata", "nome": "Vira-lata", "papel": "Equilibrado, base do breed",
     "custo": 2, "atk_base": 2, "hp_base": 4, "keywords": []},
    {"id": "siames", "nome": "Siamês", "papel": "Atacante",
     "custo": 3, "atk_base": 4, "hp_base": 3, "keywords": ["investida"]}
  ]
}
```

Campos: `custo` (energia, fixo por raça), `atk_base`, `hp_base` (inteiros ≥ 1), `keywords` (lista de ids). Valores das 5 raças = tabela do GDD. Campos de breed por raça (`breed_runs`, raridade, receitas híbridas) **não entram** neste contrato até o Renatho definir (ver dúvidas).

### 1.3 Natureza — `data/natures.json`

```json
{"schema_version": 1, "natures": [
  {"id": "calmo",   "nome": "Calmo",   "atk": -1, "hp": 1},
  {"id": "bravo",   "nome": "Bravo",   "atk": 1,  "hp": -1},
  {"id": "agitado", "nome": "Agitado", "atk": 2,  "hp": -2}
]}
```

Valores = proposta inicial do GDD (ainda listados como em aberto, então podem mudar só por esta tabela).

### 1.4 Parâmetros de regra — `data/rules.json`

Todos os números de combate e de sorteio ficam aqui, nunca no código.

```json
{
  "schema_version": 1,
  "duel": {"leader_hp": 20, "slots": 5, "initial_hand": 4, "draw_per_turn": 1,
           "hand_max": 7, "energy_start": 2, "first_player_energy_start": 1,
           "energy_per_turn": 1, "energy_cap": 7, "deck_size": 12, "first_player_no_attack_first_turn": true,
           "draw_on_first_turn": true},
  "stats": {"iv_min": 1, "iv_max": 5, "min_stat": 1,
            "atk_iv_divisor": 2},
  "iv_weights": {"1": 30, "2": 25, "3": 25, "4": 15, "5": 5},
  "deadlock": {"variation": [-1, 0, 1], "min_damage": 1},
  "breed": {"mutation_chance": null, "base_runs": 2, "growth_runs": 2}
}
```

`first_player_energy_start` (opcional, inteiro ≥ 1; ausente = vale `energy_start`): energia do jogador que começa, **só no primeiro turno dele** (curva do 1º jogador: 1, 3, 4, 5…; do 2º: 2, 3, 4…; depois igual, teto `energy_cap`); o outro jogador usa `energy_start`. Decidido pelo Renatho em 2026-10-27 (pacote B de balanceamento, com custo 2 do Persa e 3 do Maine Coon; ver `docs/propostas/2026-10-27-balanceamento-inicial.md`). O GDD foi atualizado em 2026-10-27 (autorização do Renatho).

`null` = PENDENTE. Pesos de IV decididos pelo Renatho em 2026-10-27 (1:30, 2:25, 3:25, 4:15, 5:5, ajustáveis por simulação); a mutação do breed segue `null` (GDD: 5% a 10%, a definir). Os pesos valem para o sorteio de IV de ATK e de HP, cada um independente. Pesos de raça: não existem; `roll_cat` sem `breed_id` sorteia uniformemente entre as raças.

### 1.5 Gato (instância) — usado no save e na API

```json
{
  "id": "c-000123",
  "breed": "siames",
  "name": "Mingau",
  "sex": "F",
  "nature": "bravo",
  "iv_atk": 4,
  "iv_hp": 2,
  "stage": "adult",
  "rest_runs_left": 0,
  "runs_as_kitten": 0
}
```

- `sex`: `"M"` | `"F"`. `nature`: id de natureza. `iv_atk`, `iv_hp`: 1 a 5. `stage`: `"kitten"` | `"adult"`.
- `name` opcional (renomear). `rest_runs_left` > 0 = em breed/descanso, indisponível para o deck.
- Status final **não é guardado**: é derivado (1.5.1).
- Imutáveis depois de criado: `breed`, `sex`, `nature`, `iv_atk`, `iv_hp`.

**1.5.1 Fórmula (GDD):**
`ATK = max(1, atk_base + floor((iv_atk - 1) / 2) + nature.atk)` e `HP = max(1, hp_base + (iv_hp - 1) + nature.hp)`.

### 1.6 Gato Especial — `data/specials.json`

Só existem na run, sem IV, status fixos.

```json
{"schema_version": 1, "specials": [
  {"id": "espirito-exemplo", "nome": "…", "custo": 3, "atk": 3, "hp": 3,
   "keywords": ["provocar"], "efeito_ao_entrar": null, "texto": "…"}
]}
```

`efeito_ao_entrar` é opcional e usa o mesmo formato de ação de 1.7 (no schema real é uma lista de ações; o core aceita também um objeto). Os 8 Espíritos reais estão em `data/specials.json` (Fase 3, aprovados pelo Renatho em 2026-10-27).

### 1.7 Carta de efeito — `data/effects.json`

```json
{"schema_version": 1, "effects": [
  {"id": "exemplo-dano", "nome": "…", "custo": 2, "texto": "…",
   "acoes": [{"tipo": "dano", "alvo": "inimigo_escolhido", "valor": 3}]}
]}
```

- `tipo` (enum fechado, do GDD): `dano`, `cura`, `buff_atk`, `comprar`, `energia`.
- `alvo` (enum): `inimigo_escolhido`, `aliado_escolhido`, `lider_inimigo`, `lider_proprio`, `nenhum` (para `comprar`/`energia`).
- `custo`: inteiro ≥ 1 (decidido 2026-10-27; todo efeito gasta energia).
- `valor`: inteiro > 0. `buff_atk` guarda a duração em `duracao`: `"permanente"` ou `"turno"` (decidido pelo Renatho em 2026-10-27: os efeitos do MVP usam `"turno"`, até o fim do turno do dono).
- Carta de efeito é consumida ao uso e só existe durante a run.

### 1.8 Inimigo / rival — `data/enemies.json`

```json
{"schema_version": 1, "enemies": [
  {"id": "…", "nome": "…", "tipo": "batalha", "liga": 1,
   "lider_hp": 20, "deck": [{"carta": "vira-lata", "iv_atk": 3, "iv_hp": 3, "nature": "calmo", "qtd": 2}],
   "ia": "simples", "regra_propria": null,
   "falas": {"vitoria": [], "derrota": []}}
]}
```

- `tipo`: `batalha` | `elite` | `chefe`. `liga`: 1 a 3.
- `deck` aceita raça (com IVs/natureza fixos escolhidos pelo autor do dado) ou id de Gato Especial/efeito.
- `ia`: enum fechado, por ora só `"simples"` (decidido 2026-10-27; novos ids entram quando o Renatho definir rivais com outro comportamento).
- `lider_hp`: opcional, padrão = `rules.duel.leader_hp`.
- `regra_propria`: só para chefe (batalha e elite exigem `null`). Formato fechado em 2026-10-27 (Fase 3): `{"id": "banho-de-espuma", "nome": "Banho de Espuma", "texto": "No início do turno dela, o Líder se cura em 1 HP.", "gatilho": "inicio_turno_proprio", "acao": {"tipo": "cura", "alvo": "lider_proprio", "valor": 1}}` (`nome` e `texto` obrigatórios). `gatilho` é enum fechado (só `inicio_turno_proprio` por ora); `acao` usa o mesmo formato das ações de efeitos (§1.7); sem campos extras.
- Inimigos são **pessoas** (criadores), não gatos. `lider_hp` do chefe 25 e da elite 22 são valores provisórios (2026-10-27); batalhas comuns usam o padrão 20.
- `falas`: textos dos diálogos entre runs.

### 1.9 Save — `saves/save.json` (arquivo local, gerado pelo core)

```json
{
  "schema_version": 1,
  "cats": [ /* instâncias de 1.5 */ ],
  "deck": ["c-000123", "…12 ids de adultos…"],
  "coins": 0,
  "next_cat_id": 124,
  "breeding": [{"male": "c-1", "female": "c-2", "runs_left": 2}],
  "pity": {"runs_without_high_iv": 0},
  "progress": {"leagues_cleared": 0, "best_distance": 0, "records": {}},
  "dex": {"breeds_seen": [], "perfect_cats": []},
  "items": {"nature_item": false},
  "settings": {}
}
```

Gatos de run e cartas de efeito **nunca** entram no save (só existem durante a run). Estado de uma run em andamento fica fora do save na Fase 1 (decisão de retomada de run = dúvida).

---

## 2. API pública do `core`

Puro: sem pygame, sem `print`, sem `random` global. Todo sorteio recebe `rng: random.Random`. Estado serializável. Tipos em `core/types.py` (dataclasses). A UI e a CLI só usam o que está listado aqui.

### 2.1 Carregamento
```python
load_content(data_dir: Path) -> Content          # valida com data/schemas; erro claro se inválido
```

### 2.2 Gatos
```python
roll_cat(content: Content, rng: Random, breed_id: str | None = None,
         stage: Stage = "adult") -> Cat
cat_stats(content: Content, cat: Cat) -> Stats   # Stats(cost, atk, hp), fórmula 1.5.1
```

### 2.3 Duelo
```python
new_duel(content: Content, rng: Random, player: DeckSpec, enemy: DeckSpec,
         player_first: bool | None = None) -> Duel
legal_actions(duel: Duel) -> list[Action]
apply_action(duel: Duel, action: Action) -> list[Event]   # única forma de mudar o estado
view(duel: Duel, side: Side) -> DuelView                  # estado visível (mão do outro oculta)
is_over(duel: Duel) -> Winner | None
```

`Action` (união fechada): `PlayCat(hand_index, slot)`, `PlayEffect(hand_index, target)`, `Attack(attacker_slot, target)`, `EndTurn()`. `target` = `("slot", n)` ou `("leader",)`.
`Event` (lista ordenada, para a UI animar sem reprocessar regras): `DiceRolled`, `DrawSkipped`, `Deadlock`, `TurnStarted`, `Drew`, `CatPlayed`, `EffectPlayed`, `Attacked`, `DamageDealt`, `Healed`, `CatDied`, `LeaderDamaged`, `EnergyChanged`, `DuelEnded`.
**Regras de duelo decididas pelo Renatho (2026-10-27):**
- **Quem começa:** `new_duel` sorteia com o `rng` (o "dado") se `player_first` for `None`, e emite `DiceRolled`. Quem começa **não pode atacar no seu primeiro turno** (`legal_actions` não oferece `Attack` nesse turno). Ainda compra no turno 1.
- **Compra:** todo jogador compra 1 carta no início de cada turno, inclusive o primeiro. Deck vazio: não compra e **não há fadiga**; o jogador segue com mão e campo. Mão com 7 cartas: a compra é pulada (emite `DrawSkipped`, a carta fica no deck, nada é descartado). A UI mostra aviso de mão cheia.
- **Sem limite de turnos** (Renatho, 2026-10-27). O contra-golpe de quem tem Primeira Patada nunca é dobrado.
- **Primeira Patada:** dobra o dano só no **primeiro ataque da vida do gato** (não repete em turnos seguintes). Flag `used_first_strike` no gato em campo.
- **Robusto:** cura 1 no fim do turno do dono, limitada ao HP máximo do gato.
- **Líder:** não contra-ataca; atacar o Líder não causa dano de volta.
- **Provocar:** vale só para ataques de gatos (não para cartas de efeito). Com um ou mais gatos com Provocar em campo, o atacante só pode escolher entre eles, e precisa destruir todos antes de atacar outros gatos ou o Líder.
- **Slots:** o jogador escolhe o slot ao jogar; a posição não tem efeito nas regras.

**Dados de exibição para a UI (T2.0):** `Card` expõe `breed_name`, `cat_name`, `sex`, `nature`, `iv_atk`, `iv_hp` (None para Gatos Especiais). `FieldCat` expõe `atk`, `hp`, `hp_max`, `keywords`, `ready`, `attacked`, `used_first_strike` e `first_strike_available`. `SideView` expõe `leader_hp`, `leader_hp_max`, `energy`, `deck_count`, `hand_count`, `field`, `turns_taken` e `hand` (completa só em `me`). Funções: `attack_targets(duel, attacker_slot)` (alvos legais de um slot) e `keyword_info(content, id)` (nome e texto).

`apply_action` com ação ilegal levanta `IllegalAction` (nunca altera o estado). `apply_action` é **determinístico** dado o estado, incluindo o estado do `rng` guardado no `Duel`. Os sorteios são: embaralhar e dado em `new_duel`, e as variações e o desempate de HP da resolução do impasse (dentro de `apply_action`).

#### 2.3.1 Efeitos, Espíritos e inimigos (Fase 3, 2026-10-27)
```python
new_duel_vs_enemy(content, player: DeckSpec, enemy_id, rng, player_first=None) -> Duel
enemy_deck_spec(content, enemy_id, rng) -> DeckSpec   # Líder HP e regra do chefe já dentro
card_from_effect(content, id) -> Card ; card_from_special(content, id) -> Card
card_targets(duel, hand_index) -> list[Target]        # alvos escolhíveis da carta
DeckSpec(cats=[], cards=[], leader_hp=None, rule=None)
PlayEffect(hand_index, target)      # target = ("slot", n) quando a carta pede gato, senão ("leader",)
PlayCat(hand_index, slot, target=None)   # target só para Espírito com "ao entrar" escolhido
```
- Efeitos: custo cobrado, carta consumida; dano (gato ou Líder; ignora Provocar), cura limitada ao HP máximo, buff de ATK só até o fim do turno do dono (`FieldCat.atk_bonus_turn`), comprar (regras da compra normal) e energia (limitada a `energy_cap`).
- Espírito: sem IV; "ao entrar" dispara após `CatPlayed`; sem alvo válido o efeito se perde e o gato entra; `aliado_escolhido` não inclui o próprio Espírito.
- Eventos novos: `LeaderHealed`, `AtkBuffed`, `AtkBuffExpired`; `EffectPlayed(side, card, target)` reaproveitado. Ordem: `EffectPlayed`, `EnergyChanged` (custo), eventos das ações (Espírito: `CatPlayed`, `EnergyChanged`, `EffectPlayed`, ...).
- `Card` ganhou `text`, `actions`, `kind` (`cat`/`special`/`effect`); `SideView.rule` traz a regra do chefe. Regra do chefe roda no início do turno do dono.
- **Impasse (decidido pelo Renatho em 2026-10-27):** no gatilho só contam gatos e Espíritos; efeitos na mão não seguram. Além disso, **impasse por estagnação**: `rules.deadlock.stall_rounds` (5) rodadas completas seguidas sem gato/Espírito jogado, sem gato morto e sem Líder com HP líquido menor que o da base da janela resolvem o impasse como o atual (evento `Deadlock`). Sem a chave, a estagnação fica desligada. Continua sem limite de turnos.
- `specials.efeito_ao_entrar` aceita lista de ações (o schema real) ou objeto; `regra_propria` usa `acao` (o core aceita também `acoes`).

#### 2.3.2 Mini-run (Fase 4, 2026-10-27)
```python
new_run(content, rng) -> Run          # 12 gatos adultos sorteados (rules.duel.deck_size); ValueError sem data/run.json
Run.available_nodes() ; Run.choose_node(id) ; Run.start_duel(rng, player_first=None) -> Duel
Run.finish_duel(duel) ; Run.pick_draft(index) ; Run.abandon() ; Run.to_dict() ; Run.from_dict(content, d)
Run.status  # "map" | "duel" | "draft" | "finished" ; Run.result  # None | "vitoria" | "derrota"
```
- `data/run.json`: `draft_options`, `draft_options_elite`, `drafts_elite`, `draft_options_rest`, `rest_draft`, `pool`, `start_deck`, `map.layers[].nodes[]` (`id`, `tipo` batalha/elite/descanso/chefe, `inimigo`); todo nó de uma camada conecta a todos da seguinte.
- Regras (Renatho, 2026-10-27): cada duelo recomeça do zero; vitória em batalha/elite → draft de N opções distintas entre efeitos e Espíritos; elite → `drafts_elite` (2) drafts seguidos de `draft_options_elite` (3) opções; descanso → 1 draft de `draft_options_rest` (2) opções; batalha → 1 draft de `draft_options` (3); vitória no chefe → fim com vitória; derrota → fim. O deck da run cresce com o draft. `abandon()` conta como derrota (confirmado). A UI lê `Run.draft_step` (1-based, 0 fora de draft), `Run.draft_total` e `Run.drafts_left`. Erros de estado levantam `IllegalAction`.
- `to_dict` só vale entre duelos (o `Duel` não serializa). A run ainda não está em `save.schema.json`.

### 2.4 IA inimiga
```python
choose_action(duel: Duel, side: Side, rng: Random) -> Action   # sempre uma ação de legal_actions
```

### 2.5 Meta (Fase 5+, assinatura reservada)
**5a (feito, 2026-10-28):** `core/save.py` e `core/collection.py`.
```
new_game(content, rng) -> SaveData            # 12 adultos sorteados (rules.meta.start_cats), ids c-000001…, deck = os 12
save_to_dict(save) ; save_from_dict(d, content=None)   # ValueError em formato inválido
write_save(save, path) ; read_save(path, content=None) # JSON UTF-8, escrita atômica; caminho sempre por parâmetro
rename_cat(save, cat_id, name, content=None)   # até rules.meta.name_max_length (16); vazio/None remove `name`; IllegalAction se inválido
available_cats(save) ; get_cat(save, id) ; deck_cats(save) ; cat_stats(content, cat)
set_deck(content, save, cat_ids)               # exatamente 12 adultos distintos e disponíveis (rest_runs_left == 0)
autofill_deck(content, save, picked) -> ids    # completa com maior ATK+HP finais (desempate por id); não altera o save
new_run(content, rng, cats=None) ; new_run_from_save(content, save, rng)
```
`rules.meta`: `start_cats` (12) e `name_max_length` (16). O save **não guarda run em andamento** (run interrompida = abandonada = derrota); `name` ausente = nome padrão; o `deck` do save pode ter menos de 12 ids (só `set_deck` exige 12).
**5b/5c (pendente):** `breed(...)`, `age_cats_after_run(...)`, `adopt(...)`, `donate(...)`.

### 2.6 CLI
`python -m core.cli` é o único lugar que imprime e lê entrada.

---

## 3. Dúvidas para o Renatho (o GDD não responde; nenhuma foi decidida)

**Fase 1 (regras do duelo): respondidas em 2026-10-27**, ver "Regras de duelo decididas" na seção 2.3. Pequenos pontos que o texto não fecha (não bloqueiam, proponho o padrão entre parênteses):
- A energia do segundo jogador também começa em 2 no primeiro turno dele (padrão: sim, cada jogador tem o seu primeiro turno com 2).
- **Energia do 2º jogador:** confirmado, 2 no primeiro turno de cada um.
- **Impasse (decidido):** gatilho = os dois lados sem cartas jogáveis (mão e deck vazios) e sem gato em campo que cause dano. O `core` emite `Deadlock` e então resolve: poder do Líder = média de ATK final do deck inicial inteiro (arredondada) + variação sorteada por ataque (`rules.deadlock.variation`, valor inicial −1/0/+1, ajustável por simulação), dano direto no HP do Líder adversário. Os Líderes atacam alternadamente até um zerar; começa quem tem menos HP e, em HP igual, sorteia-se de novo com o `rng` do duelo (confirmado pelo Renatho em 2026-10-27, não reaproveita o dado do início). `min_damage` 1 evita ataque de 0 (**sugestão minha, não confirmada**, ver dúvida abaixo). Registrado em `docs/propostas/2026-10-27-desempate-impasse.md`.
- A regra do primeiro turno foi incluída no GDD por autorização do Renatho em 2026-10-27.

**Resolvido na Fase 3 (2026-10-27):** duração do buff (turno), os 8 Gatos Especiais e os 8 efeitos (`data/`), e o formato de `regra_propria` (§1.8, com `nome` e `texto`).

**Bloqueiam a Fase 4/5 (podem esperar):** pesos de sorteio de IV, chance de mutação, tempo de breed por raça, ninhada, receitas de raça híbrida, pity timer (valor de N), moedas, retomada de run salva.

Os pontos já listados em "Pontos em aberto" do GDD (naturezas, tempo de breed etc.) seguem como o GDD os descreve; este contrato só deixa o campo reservado.
