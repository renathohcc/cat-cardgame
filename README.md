# Gatos — kit de partida

Este kit organiza o projeto para você produzir o jogo com agentes. Siga os passos na ordem.

## Passo 1 — Preparar o computador

1. Instale **Python 3.12 ou mais novo** e **Git**.
2. Tenha o **app desktop do Claude** com a área de código (para abrir uma pasta e rodar sessões com agentes).
3. (Opcional, recomendado) Crie um repositório **privado** no GitHub para guardar o projeto.

## Passo 2 — Colocar o projeto no lugar

1. Extraia este kit em uma pasta de trabalho, por exemplo `Documentos/jogos/gatos`.
2. Abra um terminal **dentro dessa pasta** e rode:

```
git init
git add .
git commit -m "Kit de partida"
python -m venv .venv
```

3. Ative o ambiente e instale as dependências:
   - Windows: `.venv\Scripts\activate`
   - Mac/Linux: `source .venv/bin/activate`

```
pip install -r requirements.txt
```

## Passo 3 — Colocar o GDD no repositório (tarefa T0.1)

1. Abra o documento do GDD no Claude e use a opção de **exportar em Markdown**.
2. Salve o arquivo como `docs/GDD.md` (dentro da pasta `docs` do projeto).
3. Rode `git add docs/GDD.md` e `git commit -m "GDD v0.1"`.

Sem esse arquivo, os agentes são instruídos a parar. O GDD no repositório passa a ser a cópia oficial: quando mudar uma regra, **edite `docs/GDD.md` primeiro** e só depois peça ajustes aos agentes.

## Passo 4 — Abrir a sessão do orquestrador

1. No app desktop, abra a pasta do projeto em uma **nova sessão de código**. Essa é a sessão principal (o orquestrador).
2. Cole este primeiro pedido:

> Você é o orquestrador deste projeto. Leia `CLAUDE.md`, `docs/GDD.md` e `PLAN.md`. Não escreva código, dados nem arte: planeje e delegue aos agentes de `.claude/agents/`. Comece pela Fase 0: me mostre um rascunho de `docs/CONTRATOS.md` (formatos JSON e API pública do core) para eu aprovar. Não passe para a Fase 1 sem o meu OK. Se o GDD for ambíguo, pergunte; nunca decida regra de design sozinho.

3. Leia o rascunho dos contratos com calma. Esse é o passo mais importante do projeto, porque todos os agentes vão herdar o que estiver ali. Corrija o que não bater com o que você quer.

## Passo 5 — Executar a Fase 1 (motor no terminal)

Depois de aprovar os contratos, peça ao orquestrador:

> Contratos aprovados. Execute a Fase 1 do `PLAN.md`. Rode em paralelo só o que não depende um do outro. Ao fim de cada tarefa, confira o critério de aceite e atualize o `PLAN.md`. Pare no portão da fase e me mostre o resultado.

No portão da Fase 1 você:
- joga um duelo na CLI (`python -m core.cli`);
- lê o relatório de simulação em `reports/`;
- lê a revisão em `reports/revisao-fase1.md`;
- diz "aprovado" ou lista o que quer mudar.

## Rotina de toda fase

1. O orquestrador detalha as tarefas da fase em `PLAN.md` e você revisa.
2. Os agentes executam, cada um na sua pasta, e deixam um relatório curto em `reports/`.
3. O orquestrador confere os critérios de aceite e chama o revisor.
4. **Portão:** você testa o resultado de verdade e aprova antes da próxima fase.
5. Faça um `git commit` a cada tarefa concluída.

## Regras para você

- **Você é o único dono do design.** Mudança de regra: edite `docs/GDD.md`, avise o orquestrador, e peça os ajustes. Não peça mudança de regra direto a um agente.
- **Comece com um agente por vez.** Paralelismo só depois que o fluxo estiver funcionando. Quando for paralelizar, use branches ou worktrees separados, para dois agentes nunca editarem a mesma pasta.
- **Sessão ficou lenta ou confusa?** Feche e abra uma nova. O `PLAN.md` e os relatórios guardam o estado, então nada se perde.
- **Dúvidas dos agentes** aparecem em `docs/propostas/`. Responda editando o GDD ou o contrato.
- **Arte:** os agentes geram placeholders e scripts. A arte final com personalidade (por exemplo, o gato guerreiro pacato) provavelmente vai precisar de você ou de uma ferramenta de imagem. Só vale investir nela depois de a diversão ser validada.
- **Dados pessoais e chaves:** nunca coloque senhas, tokens ou IDs de conta no repositório.

## O que tem no kit

| Caminho | Para quê |
| --- | --- |
| `CLAUDE.md` | Regras que todo agente lê, e o papel do orquestrador |
| `PLAN.md` | Backlog das Fases 0 e 1 e visão das seguintes |
| `.claude/agents/` | Agentes: core, testes, dados, interface, arte, revisor, build |
| `docs/PRODUCAO.md` | Visão geral do fluxo de produção |
| `docs/propostas/` | Dúvidas e propostas dos agentes |
| `reports/` | Relatório curto de cada tarefa |
| `core/`, `data/`, `tests/`, `sim/`, `ui/`, `assets/`, `build/` | Pastas de trabalho (vazias por enquanto) |
