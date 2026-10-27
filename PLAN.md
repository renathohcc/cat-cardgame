# PLAN.md — backlog e estado do projeto

Este arquivo é a memória do projeto. O orquestrador o atualiza a cada tarefa. Status: `pendente`, `em andamento`, `concluída`, `bloqueada`.

**Fase atual:** 0 — Fundação
**Última atualização:** (orquestrador preenche)

## Fase 0 — Fundação (feita por você com o orquestrador)

| ID | Tarefa | Agente | Aceite | Status |
| --- | --- | --- | --- | --- |
| T0.1 | Colocar o GDD exportado em `docs/GDD.md` | Renatho | Arquivo existe e abre | pendente |
| T0.2 | Inicializar git, primeiro commit, criar `.venv` e instalar dependências | Renatho | `pytest` roda (mesmo sem testes) | pendente |
| T0.3 | Escrever `docs/CONTRATOS.md`: formato JSON de raça, natureza, keyword, gato, carta de efeito, Gato Especial, inimigo; API pública do `core` (criar gato, montar duelo, executar ação, consultar estado); formato do save | Orquestrador, com revisão do Renatho | Renatho aprova o texto; nenhum campo contradiz o GDD | pendente |
| T0.4 | Criar `data/schemas/` com os JSON Schemas dos contratos | Dados | Schemas validam os exemplos do `CONTRATOS.md` | pendente |

**Portão da Fase 0:** Renatho aprova `docs/CONTRATOS.md`. Só depois a Fase 1 começa.

## Fase 1 — Motor de combate no terminal

Meta: duelo completo jogável no terminal, com testes e simulação.

| ID | Tarefa | Agente | Depende de | Aceite | Status |
| --- | --- | --- | --- | --- | --- |
| T1.1 | Dados das 5 raças, 3 naturezas e 4 keywords em JSON, validados pelo schema | Dados | T0.4 | JSON válido e igual à tabela do GDD | pendente |
| T1.2 | Modelos e geração de gato: raça, IV 1–5 em ATK/HP, natureza, sexo, estágio; cálculo de status final (fórmula do GDD, status mínimo 1); RNG injetado | Core | T0.3, T1.1 | Mesma seed gera o mesmo gato; status batem com a fórmula | pendente |
| T1.3 | Escrever testes de geração de gato a partir do GDD (sem olhar a implementação) | Testes | T0.3 | Testes cobrem limites de IV, naturezas, mínimo de status 1, distribuição de sexo | pendente |
| T1.4 | Estado de duelo: Líder (20 HP), 5 slots, mão, compra, energia crescente (2, +1/turno, teto 7), ataque com troca de dano, regra de não atacar ao entrar | Core | T1.2 | Duelo avança turno a turno por API, sem interface | pendente |
| T1.5 | Keywords: Provocar, Investida, Primeira Patada, Robusto | Core | T1.4 | Cada keyword com pelo menos um teste | pendente |
| T1.6 | Escrever testes de combate e keywords a partir do GDD | Testes | T0.3 | Cenários nomeados (ex.: "Provocar bloqueia ataque ao Líder") | pendente |
| T1.7 | IA inimiga simples (joga cartas disponíveis, ataca respeitando Provocar) | Core | T1.5 | IA joga um duelo inteiro sem travar nem violar regras | pendente |
| T1.8 | CLI jogável (`python -m core.cli`) para o Renatho jogar um duelo | Core | T1.7 | Renatho consegue jogar do início ao fim | pendente |
| T1.9 | Simulador IA vs IA (`sim/`), com relatório de taxa de vitória por raça e por IV | Testes | T1.7 | Relatório gerado em `reports/` com seed fixa | pendente |
| T1.10 | Revisão da fase contra o GDD | Revisor | todas | Lista de divergências (ou "nenhuma") em `reports/` | pendente |

**Portão da Fase 1:** Renatho joga um duelo na CLI, lê o relatório de simulação e aprova.

## Fases seguintes (detalhar só quando a anterior fechar)

- **Fase 2 — Conteúdo mínimo:** ~8 Gatos Especiais, ~8 efeitos, 3 inimigos e 1 chefe (o Renatho define o conteúdo; agentes só implementam).
- **Fase 3 — Interface com retângulos e texto:** mesa de duelo, mão, clicar/arrastar, feedback de dano.
- **Fase 4 — Mini-run:** mapa de 6 a 8 nós (incluindo nó especial de gato), draft 1 entre 3, chefe.
- **Fase 5 — Meta mínimo:** coleção, escolha do deck de 12, adoção pós-run, breed com filhotes e crescimento, doação por moedas, renomear gatos, criatório.
- **Fase 6 — Pixel art:** sprites por camadas (criatório e batalha), troca dos retângulos.
- **Fase 7 — Balanceamento e polimento.**
- **Fase 8 — Build:** navegador (pygbag) e PC/Steam.

## Decisões em aberto (do GDD)

Consulte a seção "Pontos em aberto" do GDD. O orquestrador **não** decide nenhuma delas.

## Registro de decisões e mudanças

(O orquestrador anota aqui, com data, qualquer mudança aprovada pelo Renatho.)
