# Proposta: balanceamento inicial (vantagem de quem começa e custos)

Autor: agente de testes (T7.0). Os números são do Renatho; aqui só há medições e opções.
Dados brutos: `sim/variantes_resultado_completo.md` e `sim/variantes_resultado_pacotes.md`
(seed 1, 1000 duelos por experimento, 2000 para "quem começa vence"; IA simples dos dois lados,
sem cartas de efeito; vale para essa IA, não para um humano).

## Problema

1. **Quem começa vence ~75%** (meta indicativa 50 a 56%). Ninguém ataca no 1º turno, mas o 1º jogador
   fica uma rodada à frente em energia e campo durante o duelo inteiro (~6 turnos por lado).
2. **Custos**: Maine Coon (custo 5) praticamente nunca joga; Persa (ATK 1) quase nunca fecha o duelo;
   Siamês (Investida + ATK 4) é a raça mais forte.
3. **Pilar "gato perfeito opcional"**: um deck todo 5/5 vence 94% de um deck 1/1 e 80% de um 3/3, mas
   **um** gato 5/5 no meio de 12 muda só ~4 pontos (54%). O conjunto dos IVs pesa muito; um gato isolado pouco.

## Descobertas principais

- **Os custos sozinhos não resolvem.** Testei 162 combinações de custo (Vira-lata 1 a 3, Siamês 3 a 4, Persa 1 a 3,
  Sphynx 2 a 4, Maine Coon 3 a 5): nenhuma deixa todas as raças entre 40 e 60% em decks de uma raça só contra
  decks de uma raça só. O equilíbrio é "pedra, papel, tesoura" (mexer em uma raça empurra outra para cima ou para baixo).
  Num deck realista (4 gatos da raça + 8 mistos), vários vetores ficam todos na faixa de ~40 a 58%.
- **Vantagem de quem começa**: cortes pequenos de energia funcionam, mas o efeito é grande e não linear:
  +1 de energia para o 2º jogador só no 1º turno derruba de 75% para 60%; durante 3 turnos, para 48% (passou do ponto).
  O ajuste ideal **depende dos custos** (custos baixos aumentam a vantagem de quem começa).
- **Carta extra para o 2º jogador (mão 5 vs 4) quase não faz diferença** (73%); Líder com HP extra para o 2º também pouco (71 a 73%).
  Energia é a alavanca.
- Mudanças simétricas (mão 5, energia inicial 3, sem compra no 1º turno) não ajudam (76 a 80%).

## Vantagem de quem começa ("precisa" = exige mudança no core)

| Variante | Regra | Core | 1º vence |
|---|---|---|---|
| base | dados atuais | - | 74,9% |
| a | 2º jogador +1 energia só no 1º turno (energia 3) | precisa | 60,0% |
| a-k2 | 2º jogador +1 energia nos 2 primeiros turnos | precisa | 58,4% |
| a-k3 | 2º jogador +1 energia nos 3 primeiros turnos | precisa | 48,2% |
| a2 | 2º jogador +1 energia em todo turno | precisa | 41,1% |
| b | 2º jogador com mão inicial 5 (1º com 4) | precisa | 73,2% |
| c | 1º jogador com energia 1 no 1º turno | precisa | 57,0% |
| a+b | | precisa | 59,4% |
| a+c / a+b+c | | precisa | 33,7% / 34,5% (exagera) |
| Líder do 2º +2 / +4 HP | | precisa | 72,9% / 70,7% |
| a + Líder +2 / c + Líder +2 | | precisa | 56,4% / 54,8% |
| mão 5 / energia inicial 3 / sem compra no 1º turno (ambos) | | dados | 75,9% / 79,5% / 76,0% |

## Custos (só dados). Vitória por raça em %: round-robin mono-raça / deck realista (4 + 8 mistos)

| Variante (custos Vira/Siamês/Persa/Sphynx/Maine) | Vira-lata | Siamês | Persa | Sphynx | Maine Coon |
|---|---|---|---|---|---|
| base (2/3/3/3/5) | 65 / 61 | 84 / 57 | 41 / 44 | 60 / 47 | 0 / 30 |
| Maine Coon 4 | 65 / 52 | 84 / 55 | 36 / 43 | 60 / 46 | 5 / 35 |
| Maine Coon 3 | 56 / 53 | 81 / 55 | 22 / 41 | 47 / 41 | 43 / 46 |
| Persa 2 | 58 / 50 | 76 / 60 | 70 / 56 | 47 / 47 | 0 / 30 |
| Siamês 4 | 80 / 60 | 32 / 51 | 59 / 46 | 79 / 50 | 0 / 29 |
| Sphynx 2 | 49 / 48 | 66 / 58 | 39 / 44 | 96 / 66 | 0 / 32 |
| Sphynx 4 | 72 / 60 | 90 / 58 | 61 / 46 | 26 / 41 | 2 / 32 |
| Vira-lata 1 | 89 / 73 | 71 / 52 | 36 / 39 | 54 / 44 | 0 / 26 |
| Persa 2 + Maine Coon 3 | 49 / 42 | 73 / 55 | 65 / 55 | 34 / 41 | 29 / 44 |

Persa 2 e Maine Coon 3 ou 4 são as mudanças com mais retorno. Sphynx e Vira-lata são sensíveis a ±1.
Siamês de custo 4 o deixa fraco em mono-raça, mas razoável em deck misto.

## Pacotes recomendados

| Pacote | Mudanças | Core | 1º vence | Vira-lata | Siamês | Persa | Sphynx | Maine Coon |
|---|---|---|---|---|---|---|---|---|
| **A (mínimo)** | Persa 2, Maine Coon 4; 1º jogador com energia 1 no 1º turno | sim | 50,0% | 50 / 40 | 86 / 63 | 60 / 54 | 53 / 47 | 1 / 30 |
| **B (equilibrado)** | Persa 2, Maine Coon 3; 1º jogador com energia 1 no 1º turno | sim | 54,6% | 41 / 39 | 84 / 58 | 53 / 50 | 41 / 41 | 31 / 45 |
| **C (Siamês mais caro)** | Siamês 4, Persa 2, Maine Coon 3; 2º jogador +1 energia nos 3 primeiros turnos | sim | 52,9% | 59 / 41 | 9 / 40 | 81 / 52 | 52 / 43 | 49 / 52 |

Leitura: em A o Siamês segue forte (63% em deck realista) e o Maine Coon segue fraco; B melhora o
Maine Coon e deixa quase tudo entre 40 e 58% em deck realista; C é o mais parelho em deck misto (40 a 52%),
mas deixa o Siamês fraco em mono-raça e mexe em 3 raças.
**Recomendação: pacote B** (menos mudanças que C, boa faixa em deck realista), com nova medição depois de entrarem
as cartas de efeito. Todos os pacotes exigem mudança no core, porque a regra de início é assimétrica
(hoje `energy_start` vale igual para os dois lados).

## O que exige mudança no core (nada implementado)

- "Energia do 1º jogador no 1º turno = 1" ou "bônus de energia do 2º jogador por N turnos": hoje a energia é
  `energy_start + (n-1)*energy_per_turn` igual para os dois lados. Precisaria de chaves novas em `rules.duel`
  (e no schema), por exemplo `first_player_energy_penalty`, ou `second_player_energy_bonus` + `second_player_bonus_turns`.
- Mão inicial ou HP de Líder diferentes por lado: também exigiriam chaves novas, mas não são recomendados (efeito pequeno).
- Os custos de raça são só dados (`data/breeds.json`).
- O simulador emula as regras assimétricas dentro de `sim/` (`apply_handicap_*`), sem alterar o core.

## Observação sobre Calmo e naturezas (sem decidir)

Calmo (-1 ATK, +1 HP) perde de Bravo (25% de vitória; 11 a 18% nos pacotes) e de Agitado (28%; 14 a 18% nos pacotes);
Bravo x Agitado fica perto de 47% (39 a 44% nos pacotes). Em duelos curtos, ATK vale mais que HP, e
equilibrar a vantagem de início deixa o Calmo **pior**, não melhor. Ajustar naturezas significaria, por exemplo,
dar ao Calmo uma vantagem própria (mais HP, ou um bônus ao Líder) ou reduzir o ganho do Bravo; é decisão de design
e não proponho números. Se o Calmo continuar estritamente pior, a escolha de natureza deixa de ser decisão e vira "sempre Bravo".

## Peso do IV (resposta ao pilar)

IV 5/5 vs 1/1: 94% (base) e 97 a 99% nos pacotes; 5/5 vs 3/3: 80% e 87 a 93%; um único gato 5/5: 54% e 58 a 61%.
Reduzir a vantagem de quem começa **aumenta** o peso do IV (menos sorte de início, mais força de deck).
Para o gato perfeito ser opcional, o Renatho pode querer reduzir o efeito do IV no status (hoje o IV de ATK
é dividido por `atk_iv_divisor` = 2), mas isso é decisão de design e não foi medida aqui.
