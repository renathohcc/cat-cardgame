# Proposta: plano de polimento

2026-10-31 · orquestrador, a pedido do Renatho: "um jogo não muito complexo, mas muito bem polido e divertido". As decisões marcadas com **[decidir]** são dele. Nada aqui altera regras do jogo: polimento vive quase todo em `ui/`, `assets/` e `data/` (textos, tempos), e o `core` só entra quando a UI precisar de uma informação nova (por exemplo, prévia de ataque).

## Princípios

1. **Orçamento de complexidade.** Antes de adicionar uma regra, polir as que existem. Cada sistema novo responde a duas perguntas: que decisão ele cria, e dá para explicar em uma frase?
2. **Clareza antes de brilho.** O jogador nunca deve ficar em dúvida sobre o que vai acontecer. Efeitos visuais vêm depois da leitura do jogo.
3. **Toda ação tem resposta.** Clique, ataque, morte, compra e revelação têm reação visual e sonora em menos de 100 ms.
4. **Respeitar o tempo do jogador.** Menos cliques, menos espera, nada de confirmação desnecessária, tudo pulável.
5. **Momentos de pico grandes.** Adoção, nascimento, vitória sobre o chefe e desbloqueio são os momentos que o jogador lembra: investir neles mais que no resto.
6. **Sempre ajustável.** Todo efeito forte (tremor de tela, flash) tem opção de desligar, e todo tempo de animação fica em `data/` para afinar sem mexer em código.

## Estado atual (levantamento rápido da UI)

- **Duelo:** já tem flash de dano e cura, números flutuantes, linha de ataque, fantasma de morte, borda de entrada, pílula de carta lançada, toasts e tooltip. Falta "peso": a carta não se move ao atacar, não há pausa no impacto, a mão não anima.
- **Telas:** não achei transição entre cenas, menu de pausa ou de opções no jogo (volume e mudo existem por tecla), nem tutorial.
- **Adoção:** já tem revelação por clique ("revelar" e "revelar todos"), sem cerimônia.

## P1. Sensação do duelo (o que o jogador mais vê)

| Item | Descrição | Custo |
| --- | --- | --- |
| Investida da carta | O atacante avança até o alvo, bate e volta (~250 ms, com easing), no lugar da linha | baixo |
| Pausa no impacto | Congelar 50 a 80 ms no golpe; mais longa em golpe letal e no Líder | baixo |
| Tremor de tela | Leve no dano ao Líder, mais forte em golpe letal; desligável | baixo |
| Números de dano | Surgem grandes, encolhem e sobem; dano alto fica maior e mais quente | baixo |
| Morte com "poof" | Partículas de pelo/fumaça + o som `poof_miadinho` que já existe | baixo |
| Mão animada | Compra desliza do deck para a mão; jogar uma carta faz um arco até o slot | médio |
| Carta em foco | Passar o mouse levanta e amplia a carta da mão; as outras se afastam | baixo |
| Respiração em campo | Gatos em campo oscilam 1 px devagar, cada um com fase própria | baixo |
| Energia viva | Cristais acendem um a um no início do turno e apagam ao gastar | baixo |
| Faixa de turno | "Seu turno" / "Turno de Fifi" entra e sai rápido, com som | baixo |
| Chefe com entrada | Retrato e nome do rival aparecem com fala curta antes do duelo | médio |

## P1. Clareza do duelo

| Item | Descrição | Custo |
| --- | --- | --- |
| Prévia de ataque | Ao mirar, mostrar o resultado antes de soltar: dano previsto nos dois lados e caveira em quem morre | médio (precisa de função de prévia no core) |
| Alvos válidos | Destacar só os alvos possíveis; com Provocar em campo, os outros ficam apagados com ícone de escudo | baixo |
| Botão Passar vivo | Pulsa quando não há mais jogadas; a confirmação só aparece se ainda houver jogada | baixo (parte já existe) |
| Velocidade do inimigo | Turno inimigo em 1x / 2x / instantâneo, nas opções; clique acelera a jogada atual | baixo |
| Histórico legível | Registro com ícones (espada, coração, caveira) em vez de só texto | médio |
| Intenção do chefe | A regra própria do chefe fica visível num ícone ao lado do retrato, com tooltip | baixo |

## P1. Fundamentos que todo jogo da Steam precisa

| Item | Descrição | Custo |
| --- | --- | --- |
| Menu de pausa (Esc) | Continuar, Opções, Abandonar run (com confirmação), Sair | baixo |
| Tela de opções | Música, efeitos, mudo, tela cheia, velocidade do inimigo, tremor de tela on/off, idioma no futuro | médio |
| Transições | Fade curto (150 a 250 ms) entre todas as telas | baixo |
| Botões consistentes | Mesmo estilo, estado de hover/pressionado/desabilitado e som em todos | baixo |
| Teclado e controle | Navegação por teclado e controle (Steam Deck), atalhos (Espaço = passar turno, Esc = voltar) | alto |
| Registro de erros | Log em arquivo na pasta do usuário, para relatar bugs | baixo |

## P2. Momentos de pico

| Item | Descrição | Custo |
| --- | --- | --- |
| Adoção como "abrir pacote" | Cartas viradas para baixo; virar com animação; brilho e som graduados pela qualidade (comum, IV alto, shiny); a melhor fica por último | médio |
| Cerimônia de nascimento | Cesta que balança, filhotes revelados um a um, destaque de mutação ("+1 ATK herdado com mutação!") | médio |
| Fim de run com resumo | Nós vencidos, gato MVP (mais dano), moedas ganhas e barra "faltam X para o próximo desbloqueio" | médio |
| Vitória sobre o chefe | Câmera lenta no golpe final, confete de pelos, fala do rival derrotado | médio |
| Desbloqueio | Selo animado ao subir o Prestígio ou liberar algo novo, com som próprio | baixo |

## P2. Criatório vivo e com feedback

| Item | Descrição | Custo |
| --- | --- | --- |
| Avisos no quintal | Ícone sobre o casal quando o breed termina, sobre filhote que virou adulto, ponto de "novo" nos menus | baixo |
| Reação ao clique | Ampliar o que existe: coração, ronronar, e às vezes uma reação rara (rolar, espreguiçar) | baixo |
| Gatos olham o cursor | Os gatos próximos viram a cabeça ou andam até o cursor parado | médio |
| Placa de vagas | "14/18" na placa do portão (proposta de economia) | baixo |

## P2. Primeira hora (onboarding)

| Item | Descrição | Custo |
| --- | --- | --- |
| Primeiro duelo guiado | Dicas de contexto curtas: jogar gato, atacar, Provocar, passar turno. Uma vez só, puláveis | médio |
| Revelação gradual | Breed aparece depois da 1ª run, Prestígio depois da 1ª compra, Pressão depois da 1ª vitória. Ninguém vê tudo na primeira tela | baixo |
| Dicas na tela de carregamento | Frases curtas sobre regras e gatos | baixo |

## P3. Acessibilidade e conforto

- Números de ATK/HP sempre legíveis, sem depender só de cor (vermelho/verde com ícone ou forma).
- Opção de reduzir efeitos (sem tremor, sem flash).
- Tooltip com atraso ajustável e opção de tooltip ao clicar com o botão direito.
- Texto com escala maior nas telas do hub (opção).

## Como validar o polimento

- **Teste dos 30 segundos:** alguém que nunca jogou entende o que fazer no primeiro duelo sem ajuda?
- **Sessões gravadas:** o Renatho (ou um amigo) joga gravando a tela; anotamos onde hesitou, onde clicou errado e onde sorriu.
- **Lista de "sensação" por tela:** cada ação tem som, animação e resposta em < 100 ms? Vira um checklist em `reports/` a cada etapa.
- **Tempos em dados:** durações de animação, pausa de impacto e tremor ficam num bloco `ui_timing` (ou similar) em `data/`, para afinar jogando.

## Ordem sugerida

Polimento e meta-progressão podem andar intercalados. Recomendação:

1. **Polimento P1 (duelo + fundamentos)** primeiro: é o que o jogador mais vê, não depende de regra nova e deixa o jogo apresentável para teste.
2. **10a Economia e gatil** (proposta de meta), já com P2 do criatório e a barra de desbloqueio.
3. **P2 momentos de pico** junto com a 10b/10c (adoção, nascimento, chefe).
4. **P3** e teclado/controle antes da página da Steam.

## Decisões para o Renatho

1. Começar pelo polimento P1 antes da 10a, ou o contrário?
2. Velocidade do inimigo e tremor de tela entram como opções? (recomendação: sim)
3. Primeiro duelo guiado: dicas de contexto (recomendado) ou um duelo de tutorial separado?
4. Adoção em estilo "abrir pacote" com a melhor carta por último: ok?
5. Algum item que você viu jogando e que não está aqui?
