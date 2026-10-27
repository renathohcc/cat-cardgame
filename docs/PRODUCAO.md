# Plano de produção

## Modelo de trabalho

- **Você** decide o design e aprova os portões.
- **Orquestrador** (sessão principal) planeja, delega, confere critérios e mantém o `PLAN.md`. Não produz código, dados nem arte.
- **Agentes especialistas** (`.claude/agents/`) executam, cada um na sua pasta.
- **Revisor** confere cada fase contra o GDD, sem editar nada.

## Quem faz o quê

| Agente | Pasta | Faz | Não faz |
| --- | --- | --- | --- |
| core | `core/` | Regras, combate, IA, IVs, breed, save | UI, dados, testes, arte |
| testes | `tests/`, `sim/` | Testes a partir do GDD, simulação de balanceamento | Corrigir o core |
| dados | `data/` | JSON de conteúdo e schemas | Inventar números de design |
| interface | `ui/` | Telas pygame | Regras de jogo |
| arte | `assets/` | Guia de estilo, paletas, sprites por camadas, placeholders | Arte final sem aprovação |
| revisor | só lê | Divergências contra o GDD | Corrigir |
| build | `build/` | pygbag, PyInstaller, Steam | Alterar regras ou UI |

## Fluxo de uma tarefa

1. O orquestrador escreve o pedido: objetivo, arquivos a ler, pasta, critério de aceite.
2. O agente executa e roda `pytest`.
3. O agente escreve `reports/<ID>-<nome>.md`.
4. O orquestrador confere o critério, atualiza o `PLAN.md` e faz um commit.

## Portões

Cada fase termina em um portão de aprovação. Sem o seu OK, a próxima fase não começa. O portão exige algo que você consegue ver ou jogar, nunca só "os testes passaram".

## Princípios

- **Quem testa não escreve o código testado.** Os testes saem do GDD e dos contratos.
- **Contratos primeiro.** Formato dos dados e API do `core` ficam definidos antes de qualquer agente codar.
- **Dados fora do código.** Balancear é mexer em JSON e rodar a simulação.
- **Determinismo.** Todo sorteio usa RNG injetado, então todo bug é reproduzível por seed.
- **Mudança de regra passa por você.** GDD primeiro, agentes depois.
- **Estado em arquivos.** `PLAN.md`, `reports/` e o GDD guardam tudo; qualquer sessão nova retoma sozinha.
