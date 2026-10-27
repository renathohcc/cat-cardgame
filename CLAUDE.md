# Gatos — card game roguelike (título provisório)

Card game roguelike em Python com pygame, sem engine pronta. PC e navegador, pensado para lançar na Steam. O dono do projeto é o Renatho, e só ele decide regras de design.

## Fonte da verdade

- `docs/GDD.md` é a fonte da verdade do design. **Nenhum agente edita o GDD.**
- Se uma regra estiver ambígua, faltando ou parecer errada, **não invente e não decida**: escreva a dúvida em `docs/propostas/AAAA-MM-DD-assunto.md` (problema, opções, sua recomendação) e pare essa tarefa.
- Se `docs/GDD.md` não existir, pare e avise.
- Em caso de divergência entre este arquivo e o GDD, o GDD vence.
- Contratos técnicos (formato dos JSON e API pública do `core`) ficam em `docs/CONTRATOS.md`.

## Stack e comandos

- Python 3.12+, pygame-ce, pytest, jsonschema.
- Ambiente: `python -m venv .venv`, depois `pip install -r requirements.txt`.
- Testes: `pytest`.
- Simulação de balanceamento: `python -m sim.run --duelos 1000 --seed 1` (criada na fase 1).

## Estrutura e donos das pastas

| Pasta | Dono | Conteúdo |
| --- | --- | --- |
| `core/` | agente core | Regras, combate, IA inimiga, IVs, naturezas, breed, save. **Nunca importa pygame nem `ui/`.** |
| `data/` | agente dados | JSON de raças, naturezas, keywords, Gatos Especiais, efeitos, rivais, textos, mais `data/schemas/` |
| `tests/`, `sim/` | agente testes | Testes automáticos e simulador de balanceamento |
| `ui/` | agente interface | Telas pygame |
| `assets/` | agente arte | Sprites, paletas, molduras, spritesheets |
| `build/` | agente build | pygbag, PyInstaller, Steam |
| `docs/` | Renatho | GDD, contratos, produção. Os agentes só escrevem em `docs/propostas/` |
| `reports/` | todos | Um relatório curto por tarefa concluída |

Um agente **só altera a própria pasta**. Se precisar de uma mudança em outra pasta, descreva em `reports/` e peça ao orquestrador.

## Regras de código

- O `core` é puro: sem pygame, sem I/O de tela, sem `print` de jogo (a CLI de teste fica em `core/cli.py` e só a CLI imprime).
- Todo sorteio usa um `random.Random` **injetado** (nunca o `random` global), para os testes serem determinísticos por seed.
- Conteúdo (raças, cartas, efeitos, inimigos) vive em `data/*.json`, nunca hardcoded no código. Todo JSON é validado por um schema em `data/schemas/`.
- Tipagem com type hints, funções pequenas, nomes em inglês no código e textos de jogo em português.
- Nada de dependências novas sem registrar o motivo em `reports/`.
- Antes de concluir qualquer tarefa, rode `pytest`. Não declare concluído com teste falhando.

## Regras fixas de design (resumo, o GDD vence em caso de dúvida)

- Status só **ATK** e **HP**. Não existe DEF.
- Duelo 1x1, Líder com HP, 5 slots por lado, energia crescente, mão com limite.
- IV de 1 a 5 em ATK e HP, natureza (Calmo, Bravo, Agitado) e sexo sorteados no nascimento e **fixos**.
- Deck de 12 gatos **adultos**. Filhote só nasce de breed e vira adulto depois de algumas runs.
- Gatos só se obtêm em nós especiais de run ou por breed. **Não existe compra de gatos.**
- Cartas de efeito e Gatos Especiais só existem durante a run.

## Relatório de tarefa (`reports/TX.Y-nome.md`)

Curto: o que mudou, como rodar/testar, o que ficou pendente, dúvidas para o Renatho. Nada de recapitular passo a passo.

## Papel do orquestrador (sessão principal)

A sessão principal planeja e delega, e **não escreve código, dados nem arte**.

1. Leia `docs/GDD.md`, este arquivo e `PLAN.md` ao iniciar qualquer sessão.
2. Pegue a próxima tarefa livre do `PLAN.md` e delegue ao agente certo, com um pedido completo (o agente não lembra de nada): objetivo, arquivos a ler, pasta onde trabalhar e critério de aceite.
3. Rode em paralelo só tarefas sem dependência entre si e em pastas diferentes.
4. Quando o agente terminar, confira o critério de aceite (rode `pytest`, leia o relatório) antes de marcar como concluída em `PLAN.md`.
5. No fim de cada fase, acione o agente revisor e **pare no portão de aprovação**: apresente o resultado ao Renatho e espere o OK.
6. Dúvida de design, conflito entre agentes ou mudança de regra: pare e pergunte ao Renatho. Nunca altere o GDD.
7. Mantenha o `PLAN.md` sempre atualizado: ele é a memória do projeto entre sessões.
