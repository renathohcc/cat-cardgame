# Proposta: balanceamento, rodada 2 (Siamês, Calmo, peso dos IVs, gato perfeito por breed)

Autor: agente de testes (T6.0). Só medição e opções: **nenhuma decisão é minha** e nada em `data/`, `core/` ou `ui/` foi alterado.
Base: dados atuais (pacote B já aplicado: Persa 2, Maine Coon 3, energia 1 para quem começa; mutação 7%, ninhada 1-3, breed 2 runs).
Dados brutos e reprodução: `sim/balanceamento_siames.md`, `_natureza.md`, `_iv.md`, `_breed.md`, `_breed_autofill.md`, `_breed_adocao.md`, `_deck.md`
(comandos no fim). Seeds 1, 2 e 3 juntas; 1000 duelos por célula por seed (3000 por célula; IC 95% de cerca de ±1,8 ponto).
Runs completas da IA: 300 por célula por seed (900; IC de cerca de ±2 pontos). Progressão da coleção: 20 jogadores por seed (60 por célula).
IA simples dos dois lados. **Vale para essa IA, não para um humano**; na run, mapa e draft são escolhidos ao acaso (a IA não sabe draftar).

## Aviso sobre o método: o deck escolhido muda tudo

Um achado paralelo que muda a leitura dos temas 3 e 4. Com a coleção igual (30 gatos sorteados), a vitória da run da IA depende muito de **como o deck de 12 é montado**:

| Política de deck (300 runs x 3 seeds, coleção de 30 gatos do perfil) | Mediana (IV 2 ou 3) | Real (pesos atuais) | Perfeita (5/5) |
|---|---|---|---|
| `autofill_deck` do core (maior ATK+HP finais, sem limite por raça) | 10,7% | 14,8% | 40,9% |
| 12 gatos ao acaso | 11,4% | 10,8% | 69,3% |
| maior 2xATK+HP, sem limite por raça | 2,6% | 5,8% | 13,1% |
| maior ATK*HP, sem limite por raça | 13,3% | 15,7% | 19,9% |
| maior ATK+HP, no máximo 3 por raça | 21,6% | 25,4% | 71,2% |
| maior ATK*HP, no máximo 4 por raça | 24,1% | 28,0% | 47,2% |
| **maior ATK*HP, no máximo 3 por raça** | **32,4%** | **35,0%** | **76,3%** |

(Reprodução: `--tema deck`, arquivo `sim/balanceamento_deck.md`.)

O autofill atual não limita cópias por raça (provavelmente prefere Maine Coon e Persa, de soma ATK+HP alta e ATK baixo) e tende a decks de uma raça só, que perdem (mono-raça vs misto: 7 a 11%, tabela 1.3); o efeito é pior com a coleção perfeita (40,9% contra 76,3%).
**Fica como dúvida para o Renatho:** o autofill do core é a sugestão que a UI mostra; vale revisar a heurística (core). Nas tabelas, "razoável" = ATK*HP, máx. 3 por raça; "autofill" = o do core.

---

## 1. Siamês dominante (custo 3, ATK 4, HP 3, Investida)

### Problema
Em deck só de Siamês vence 82% no round-robin e 39,5% contra misto (as demais raças ficam em 7 a 11%); no deck realista (4 Siamês + 8 mistos vs misto) vence 58,1%, o maior de todas as raças.
Entre decks mistos sorteados, ter 4+ Siamês dá 56,6% de vitória contra 43,7% de quem tem 0 ou 1: a raça decide o duelo. Na **run completa** da IA o efeito é fraco/ruidoso (13,4% de vitória com 4+ Siamês contra 9,6% com 0 a 1, diferença dentro do ruído).
Uso: o Siamês é jogado em 0,83 das cópias (Vira-lata e Persa 0,75; Sphynx e Maine Coon 0,83): não está sendo evitado, é jogado e ganha.

### Números (vitória da raça, %)

| Variante (só em memória) | Round-robin mono-raça | Deck realista (4+8) vs misto | Mono vs misto | Realista: menor e maior entre as 5 raças |
|---|---|---|---|---|
| **base** (custo 3, 4/3, Investida) | 82,2 | 58,1 | 39,5 | 37,5 a 58,1 |
| custo 4 | 7,5 | 45,2 | 0,3 | 40,7 a 52,3 |
| ATK 4 -> 3 | 60,5 | 48,9 | 23,0 | 38,6 a 54,7 |
| sem Investida | 26,2 | 37,9 | 6,6 | 37,9 a 55,7 |
| ATK 3, HP 4 | 77,2 | 57,0 | 37,8 | 37,3 a 57,0 |
| ATK 3, HP 2 | 41,9 | 43,7 | 12,9 | 40,7 a 53,9 |
| custo 4, HP 4 | 13,0 | 51,4 | 1,1 | 38,1 a 51,4 |
| ATK 3 e sem Investida | 9,3 | 27,8 | 1,6 | 27,8 a 57,9 |
| HP 3 -> 4 (referência, buff) | 93,4 | 65,2 | 55,9 | 36,5 a 65,2 |

Notas: "HP 2->3" do pedido ficou ambíguo; testei HP 4 (buff, como referência), HP 2 (nerf) e as combinações acima.
Custo 4 e "sem Investida" empurram o Maine Coon para cima (47,6 e 55,7% no deck realista) e tiram o Siamês do deck puro.
Vira-lata (36 a 41%) e Sphynx (39 a 49%) ficam abaixo de 50% em qualquer variante: não é culpa do Siamês.

### Opções (efeito medido)
- **A. ATK 4 -> 3** (resto igual): Siamês 48,9% no deck realista, ainda o melhor em deck puro (60,5% no round-robin); faixa entre raças encolhe de 20,6 para 16,1 pontos. É a opção que mexe menos na identidade (barato, Investida, frágil).
- **B. Custo 4**: Siamês 45,2% realista e faixa mais estreita (40,7 a 52,3), mas em deck puro ele quase não ganha mais (7,5%); a 4 de energia ele demora a entrar, o que tira a função de "atacante rápido".
- **C. Custo 4 e HP 4**: 51,4% realista, mas também colapsa em deck puro (13%).
- **D. Sem Investida**: 37,9% realista (passa do ponto), 26,2% em deck puro, sem identidade.
- **E. ATK 3 e HP 2**: 43,7% realista, passa do ponto para baixo; 41,9% em deck puro.

### Recomendação (do agente de testes, sem decidir)
**Opção A (ATK 4 -> 3)**: leva o Siamês para perto de 50% no deck realista sem matá-lo em deck puro e sem mexer em custo nem keyword. Se o Renatho preferir tratar por energia, B é a segunda melhor, aceitando que ele vira carta de deck misto. Vale remedir depois de qualquer mudança nas outras raças (o equilíbrio é cíclico).

---

## 2. Natureza Calmo fraca (ATK -1, HP +1)

### Problema
Decks só de uma natureza contra deck misto (IV real): **Calmo 28,1%, Bravo 60,3%, Agitado 65,3%**. Par a par (IV 3/3): Calmo perde de Bravo (vence 16,9%) e de Agitado (14,9%); Bravo x Agitado 39,5% (Agitado um pouco à frente). O Calmo é estritamente pior: escolher natureza vira "sempre Bravo ou Agitado".
Escala para se orientar (decks mistos A vs B, 3000 duelos): +1 ATK = 83,6%; +1 HP = 72,1%; +2 HP = 87,6%; **+1 ATK e -1 HP = 62,4%**; **+2 ATK e -2 HP = 69,6%**. Um passo de IV nos dois status do deck inteiro (3/3 vs 2/2) dá 92,1% e (4/4 vs 3/3) 70,9%: **o IV pesa mais que a natureza**, mas a natureza Calmo perde sozinha porque o ATK vale cerca de 2 HP nesse meta.

### Números (vitória, %): deck 100% da natureza (IV real) vs misto

| Variante | Calmo | Bravo | Agitado | Calmo x Bravo (IV 3/3) | Calmo x Agitado | Bravo x Agitado |
|---|---|---|---|---|---|---|
| **base** (-1/+1, +1/-1, +2/-2) | 28,1 | 60,3 | 65,3 | 16,9 | 14,9 | 39,5 |
| Calmo 0/+1 | **53,6** | **44,8** | **53,0** | 57,1 | 52,8 | 39,5 |
| Calmo 0/+2 | 61,8 | 37,2 | 44,8 | 76,4 | 62,4 | 39,5 |
| Calmo 0/+3 | 64,0 | 32,9 | 38,2 | 79,1 | 72,9 | 39,5 |
| Calmo -1/+2 | 38,2 | 54,8 | 58,6 | 36,1 | 24,3 | 39,5 |
| Bravo +1/-2 | 35,1 | 43,1 | 73,1 | 35,6 | 14,9 | 17,3 |
| Agitado +2/-3 | 36,6 | 66,0 | 46,6 | 16,9 | 41,4 | 64,4 |
| Calmo 0/+1 e Agitado +2/-3 | 60,4 | 51,2 | 35,0 | 57,1 | 80,2 | 64,4 |
| Calmo 0/+2 e Bravo +1/-2 | 66,4 | 23,4 | 52,0 | 85,0 | 62,4 | 17,3 |

### Opções
- **Calmo 0/+1** (tira o -1 de ATK): as três naturezas ficam em 45 a 54% contra misto; o Bravo vira o mais fraco (44,8%) e Agitado segue ligeiramente à frente do Bravo em par a par (39,5%).
- **Calmo 0/+2**: Calmo passa a dominar (61,8%; vence 76% do Bravo). Calmo 0/+3 piora.
- **Calmo -1/+2**: mantém o -1 de ATK e ainda perde (38,2%); insuficiente.
- **Mexer em Bravo ou Agitado** (+1/-2, +2/-3): sozinho não resolve o Calmo (35 a 37%) e desloca outra natureza para o fundo.

### Recomendação
**Calmo 0/+1** (uma linha em `data/natures.json`): é a única variante testada com as três entre 45 e 54%. Se o Renatho quiser manter "Calmo = ATK menor", a combinação precisaria de mais HP e passa para o outro lado (-1/+3 não foi testado).

---

## 3. Peso dos IVs (hoje 30/25/25/15/5) e o pilar "gato perfeito é opcional"

### Problema
A pergunta é se o jogo continua zerável com gatos medianos. Mediu-se de dois jeitos: IV fixo no deck inteiro e **run completa** da IA por perfil de coleção.

### Números

**Duelo, deck misto inteiro com IV fixo (vitória de A, 3000 duelos)**

| Confronto | Vitória de A |
|---|---|
| 5/5 vs 1/1 | 98,6% |
| 5/5 vs 3/3 | 90,7% |
| 3/3 vs 1/1 | 96,4% |
| IV sorteado real vs 5/5 | 4,8% (real vs 1/1: 90,5%) |
| ATK alto, HP baixo (5/1) vs 1/1 | 94,6% |
| HP alto, ATK baixo (1/5) vs 1/1 | 92,6% |
| 5/1 vs 1/5 | 30,5% (o IV de HP vale mais que o de ATK) |

**Mesma raça nos dois lados (deck mono-raça), vitória de A:**

| Raça | 5/5 vs 1/1 | 5/1 vs 1/1 | 1/5 vs 1/1 | 3/3 vs 1/1 | 5/1 vs 1/5 |
|---|---|---|---|---|---|
| Vira-lata | 100,0 | 100,0 | 81,2 | 99,1 | 61,1 |
| Siamês | 86,5 | 59,2 | 73,5 | 72,0 | 50,0 |
| Persa | 100,0 | 100,0 | 100,0 | 100,0 | 56,5 |
| Sphynx | 96,1 | 92,6 | 75,3 | 87,8 | 50,9 |
| Maine Coon | 87,0 | 84,5 | 53,3 | 78,0 | 69,3 |

**Um único gato no slot 0 do deck (resto real) contra deck real:** 5/5 vs 1/1 = +11,2 (Vira-lata), +17,7 (Siamês), +12,7 (Persa), +12,5 (Sphynx), +11,9 (Maine Coon) pontos de vitória.
(Os números do T7.0 eram +8; o pacote B aumentou o peso de um gato.)

**Run completa da IA (vitória da run; nós vencidos em média, de 6):**

| Coleção | 12 gatos sorteados no perfil | Coleção de 30 do perfil, deck de 12 escolhido (razoável) |
|---|---|---|
| todos 1/1 | 0,6% (1,1) | n/m |
| mediana (cada IV 2 ou 3) | 11,4% (2,6) | **34,6%** (4,1) |
| todos 3/3 | 30,1% (3,7) | n/m |
| sorteio real (30/25/25/15/5) | 10,7% (2,5) | 33,8% (3,9) |
| todos 4/4 | 39,2% (4,0) | 53,9% (4,6) |
| todos 5/5 | **71,0%** (5,1) | **72,1%** (5,0) |

Ou seja: com o deck bem montado a coleção mediana vence a run em um terço das vezes (contra a IA que draftar ao acaso), a perfeita em 72%; o 5/5 **não torna a run trivial** (teto de 72 a 75% nessa IA), mas dobra a taxa. Com o autofill do core a coleção mediana vence só 10,7% das runs (tema 5).

**Variantes de peso e divisor (vitória da run com coleção real de 30, deck razoável; P(5/5) por gato adotado sem bônus de nós):**

| Variante | P(5/5) por gato | Run real | Gap 5/5 vs mediana (run) | 5/5 vs 3/3 (duelo) | Real vs 5/5 (duelo) |
|---|---|---|---|---|---|
| base 30/25/25/15/5 | 0,3% | 33,8% | 72,1 vs 34,6 | 90,7 | 4,8 |
| 25/25/25/15/10 | 1,0% | 37,1% | igual | igual | 5,4 |
| 40/30/20/8/2 | 0,0% | 21,4% | igual | igual | 3,2 |
| 20/20/20/20/20 | 4,0% | 48,2% | igual | igual | 8,5 |
| 15/30/30/20/5 | 0,3% | 38,1% | igual | igual | 5,8 |
| divisor de ATK 3 | 0,3% | 31,6% | 63,7 vs 21,8 | 91,7 | 7,0 |
| divisor de ATK 4 | 0,3% | 37,7% | 73,7 vs 29,6 | 91,7 | 5,9 |
| IV de ATK sem efeito (divisor 99) | 0,3% | 40,8% | 60,0 vs 37,0 | 78,6 | 16,9 |
| IV de HP pela metade (emulado*) | 0,3% | 42,1% | 83,2 vs 43,2 | 89,9 | 4,3 |

(*) O core não tem divisor de IV de HP (`hp = base + IV - 1`); emulei no sim transformando os IVs de HP do jogador e dos inimigos. Só vira regra com mudança no core.
Mudar pesos desloca o nível médio de **todas** as coleções (e a dificuldade percebida), mas não o abismo entre decks de IV muito diferentes. Nenhuma variante reduziu o gap 5/5 vs mediana de forma relevante, exceto desligar o IV de ATK (gap de 23 pontos contra 37,5 na base), que também enfraquece o 5/5 vs 1/1 só um pouco (94,6 vs 98,6).

### Opções (efeito medido)
- **Manter** pesos e fórmula: 1 gato perfeito vale +11 a +18 pontos contra um 1/1; um deck inteiro de IV maior ganha 90% a 99%; mediana zera a run em 35% (deck bem montado).
- **Mais gatos "bons" (20/20/20/20/20 ou 15/30/30/20/5)**: a coleção real passa de 34% para 38 a 48% sem elevar P(5/5) (0,3%) no caso 15/30/30/20/5; no uniforme P(5/5) vai a 4%.
- **Pesos mais raros (40/30/20/8/2)**: a coleção real cai para 21%, ou seja, afasta do "zerável com mediano".
- **IV de ATK sem efeito (ou divisor maior)**: reduz o poder do 5/5 (60% vs 72%) e a distância do mediano; tira a graça do "ATK 5".

### Recomendação
Os pesos de IV **não são o gargalo** do pilar: o que separa o mediano do perfeito é o IV de HP (1 HP por ponto) e o deck montado. Sugiro **não mexer em pesos agora** e decidir primeiro (a) o autofill do core e (b) a meta de dificuldade (qual taxa de vitória da run o Renatho quer para uma coleção mediana), porque a dificuldade dos inimigos (T3.6b) é a alavanca direta. Se o Renatho quiser aproximar mediano e perfeito, a opção mais barata é elevar um pouco o meio (15/30/30/20/5).

---

## 4. Gato perfeito por breed (achado M2)

### Problema
M2: adoção dá 5/5 em 0,25% por gato; breed com pais 5/5 dá 100%. Medi a progressão de uma coleção por até 100 runs de um jogador novo que adota tudo, joga as runs completas contra os inimigos reais e faz breed. Três estratégias: **nenhuma** (nunca faz breed), **simples** (um casal por vez: macho e fêmea de maior soma de IV) e **ótima** (até 3 casais ao mesmo tempo, escolhidos por P(filhote 5/5) e soma esperada). Nada é doado.

Dois cenários de jogador: **razoável** (deck pelo maior ATK*HP, no máximo 3 por raça; vence 18% das runs 1-10 e ~72% das runs 61-100) e **fraco** (autofill do core; vence 12% das runs 1-10 e 3 a 4% das runs 61-100: a coleção melhora mas o deck não acompanha, provavelmente porque o autofill monta decks de uma ou duas raças).

A chance real de 5/5 na adoção **sobe com os nós vencidos** (cada nó desloca 2 de peso do IV 1 para o IV 5) e a oferta cresce com a distância:

| Nós vencidos | Gatos (derrota) | Gatos (vitória) | P(IV 5) por IV | P(gato 5/5) |
|---|---|---|---|---|
| 0 | 0 | 2 | 5% | 0,3% |
| 2 | 1 | 3 | 9% | 0,8% |
| 4 | 2 | 4 | 13% | 1,7% |
| 6 | 3 | 5 | 17% | 2,9% |

### Números: jogador razoável (60 jogadores por célula)

| Estratégia / variante | 1º 5/5 até run 30 | até 100 | mediana (run) | 1º par de pais 5/5: até 30 | até 100 | mediana | deck de 12x5/5 até a run 100 | gatos 5/5 na run 100 (de quantos) |
|---|---|---|---|---|---|---|---|---|
| nenhuma (só adoção) | 87% | 100% | 12 | 40% | 100% | 33 | 0% | 8,8 (de 334) |
| **simples, base** | 100% | 100% | 10 | 93% | 100% | **17** | 3% | 93,5 (de 459) |
| **ótima, base** | 100% | 100% | 9 | 98% | 100% | **14** | 38% | 258 (de 636) |

Comparação de variantes (estratégia **simples** / **ótima**):

| Variante | Mediana do 1º par 5/5 (simples / ótima) | Par até run 30 (simples / ótima) | 5/5 na run 100 (simples / ótima) | Deck 12x5/5 até 100 (ótima) |
|---|---|---|---|---|
| base (mut. 7%, ninhada 1-3, 2 runs) | 17 / 14 | 93% / 98% | 93,5 / 258 | 38% |
| mutação 0% | 18 / 14 | 85% / 92% | 89,4 / 255 | 8% |
| mutação 3% | 17 / 14 | 87% / 98% | 90,8 / 259 | 27% |
| mutação 10% | 17 / 14 | 97% / 100% | 94,8 / 260 | 30% |
| ninhada 1-2 | 20 / 16 | 93% / 97% | 72,1 / 191 | 8% |
| ninhada 1-4 | 17 / 13 | 97% / 100% | 115 / 326 | 27% |
| **filhote com o melhor IV dos pais** | **13 / 12** | 100% / 100% | 97,6 / 273 | 25% |
| melhor pai + mutação 3% | 14 / 12 | 95% / 100% | 96,4 / 272 | 25% |
| breed 3 runs | 22 / 17 | 82% / 97% | 61,9 / 169 | 23% |
| breed 4 runs | 24 / 20 | 78% / 93% | 47,1 / 124 | 30% |
| raças raras mais lentas (Vira-lata 2, Persa 2, Siamês 3, Sphynx 3, Maine Coon 4; hipotético) | 23 / 16 | 77% / 93% | 65,4 / 186 | 22% |

Cenário **fraco** (autofill do core): sem breed, o 1º 5/5 leva mediana de **26** runs e só 43% chegam a um par em 100 runs; com breed simples a mediana do 1º par é 26 (base), 36 (mutação 0%), 32 (3%), 16 (melhor pai), 33 (breed 3 runs), 30 (raras lentas); com breed ótimo, 21 em quase todas (12 com melhor pai). Gatos 5/5 na run 100: 42 (simples) e 99 (ótima) na base.
Adoção como alavanca (razoável; deslocamento por nó de 2 hoje; 1; 0): sem breed o 1º par vai de mediana 33 (hoje) a 70 (desloc. 1) e >100 (desloc. 0, só 18% chegam); **com breed simples a mediana do par fica em 17, 23 e 25**: o breed alcança o perfeito mesmo quando a adoção quase não dá 5/5.

### Leitura
1. **M2 confirmado:** o breed leva ao par de pais 5/5 em 13 a 24 runs (simples, razoável) e a dezenas de 5/5 em 100 runs. Não há "caçar" depois da run 20.
2. **A adoção também entrega o primeiro 5/5 cedo** (mediana 12 runs sem breed), porque a oferta cresce com a distância (2 a 5 gatos por run) e o 5/5 sobe de 0,3% para 2,9% por gato. O número de 0,25% do achado vale só para run curta.
3. **Efeito das alavancas no tempo até o 1º par:** melhor pai (-4 runs), tempo de breed 3 e 4 (+5 e +7 runs), raras lentas (+6), ninhada 1-2 (+3), mutação (3% vs 7%: 0 a 1 run; vale mais para completar o deck inteiro 5/5: ótima 27% com 3% e 38% com 7%, contra 8% sem mutação). Nenhuma variante de breed atrasa o 1º 5/5 (a adoção o dá); elas mudam a velocidade do par e a **quantidade** de 5/5.
4. **Dificuldade (razoável):** a vitória da run da IA sobe de 18% (runs 1-10) para 56% (11-30), 69% (31-60) e 73% (61-100) com a estratégia simples enquanto a soma de IV do deck vai de 5,2 para 9,5 (máx. 10). Com 12 gatos 5/5 no deck, 75,3%. Isso quer dizer **teto de ~75% para a IA (que draft ao acaso)**: a run não vira trivial, mas fica fácil para quem passa das 30 runs. O efeito de ter 5/5 no deck (vitória por gatos 5/5 no deck): 0-2 gatos 33,5%; 3-7: 67,0%; 8-11: 71,9%; 12: 75,3% (confunde com o tempo de jogo).
5. O deck inteiro 5/5 é mais difícil que o par (3% a 38% das coleções chegam em 100 runs): a mutação e a ninhada pesam nessa última milha.

### Opções (sem decidir)
- **Manter** mutação 7%, ninhada 1-3, 2 runs: perfeito rápido (par em ~17 runs), muitos 5/5, deck todo 5/5 em 3 a 38% dos jogadores em 100 runs.
- **Tempo de breed 3 runs**: par +5 runs e 34% menos 5/5 na run 100; **4 runs**: par +7 e 50% menos; **raças raras mais lentas** (hipotético): par +6.
- **Mutação 3%**: quase não muda o par, mas reduz a chance do deck inteiro 5/5 em 100 runs (ótima: 38% -> 27%; sem mutação, 8%).
- **Ninhada 1-2**: par +3 runs, 5/5 acumulados -23%.
- **Filhote herda o melhor IV dos pais** (exige mudança no core): acelera o par (-4 runs), mais 5/5 e é a única opção que torna o deck 5/5 viável cedo. Vai no sentido contrário ao pilar.
- **Menos peso de adoção** (deslocamento por nó 1 ou 0): atrasa o 1º 5/5 e o par sem breed, mas **quase não atrasa quem faz breed** (par em 17, 23 e 25 runs).

### Recomendação
Se o Renatho quer que o perfeito exija esforço (caçar), as alavancas que **mexem de fato** são o tempo de breed (3 a 4 runs, ou por raridade) e, para a "última milha" (deck inteiro 5/5), a mutação (3%); ninhada 1-2 reduz a quantidade de 5/5 sem atrasar o par. Mexer no peso da adoção ou nos IVs não resolve (o breed compensa). Se preferir manter o perfeito acessível mas não trivial, os dados atuais já deixam a run em ~72% para a IA com o deck todo 5/5, ou seja, não trivial. Tempo de breed por raridade (item em aberto do GDD) pode usar a variante "raras lentas" como ponto de partida, com a ressalva de que a raridade por raça não existe no GDD.

---

## O que NÃO foi medido
- Cartas de efeito nos duelos de deck puro (as runs incluem drafts ao acaso).
- Humanos: draft, mapa e montagem do deck são decisões que a IA toma mal; todas as taxas de run são piso.
- Sensibilidade a mudanças simultâneas (Siamês + Calmo + pesos): o equilíbrio é cíclico; remedir após decidir.
- Raridade por raça e receitas híbridas; item de natureza; ração.

## Como reproduzir
```
python -m sim.balanceamento --lista
python -m sim.balanceamento --tema siames    --duelos 1000 --runs 300 --seeds 1 2 3 --jobs 10 --saida sim/balanceamento_siames.md
python -m sim.balanceamento --tema natureza  --duelos 1000 --seeds 1 2 3 --jobs 10 --saida sim/balanceamento_natureza.md
python -m sim.balanceamento --tema iv        --duelos 1000 --runs 300 --seeds 1 2 3 --jobs 10 --saida sim/balanceamento_iv.md
python -m sim.balanceamento --tema deck      --runs 300 --seeds 1 2 3 --jobs 10 --saida sim/balanceamento_deck.md
python -m sim.balanceamento --tema breed     --jogadores 20 --runs-breed 100 --seeds 1 2 3 --jobs 10 --saida sim/balanceamento_breed.md
python -m sim.balanceamento --tema breed --deck autofill --variante base mut0 mut3 ninhada1-2 melhor-pai tempo3 raras-lentas --jogadores 20 --runs-breed 100 --seeds 1 2 3 --jobs 10 --saida sim/balanceamento_breed_autofill.md
python -m sim.balanceamento --tema breed --variante base adocao-shift1 adocao-shift0 --jogadores 20 --runs-breed 100 --seeds 1 2 3 --jobs 10 --saida sim/balanceamento_breed_adocao.md
```
Tempo total com 10 processos: cerca de 40 minutos. Determinístico por seed (conferido: as linhas `base` e `atk3` do Siamês saíram idênticas numa segunda execução).

---

## Resultado depois da decisão do Renatho (2026-10-28)

Decisões aplicadas nos dados: **Siamês ATK 4 -> 3**, **Calmo 0/+1**, **COMPLETAR (`autofill_deck`) por ATK*HP, no máximo 3 por raça**.
Mesmo método (seeds 1, 2, 3; 1000 duelos por célula por seed; 300 runs por célula por seed; 20 jogadores por seed no breed). Brutos em `sim/rodada2_pos/` (`siames_natureza.md`, `deck.md`, `breed_autofill.md`, `breed_razoavel.md`).
Nota: nessas tabelas as linhas `base`, `atk3` e `calmo0+1` agora são idênticas (os dados já têm a mudança); as demais variantes ainda aplicam o patch sobre os dados novos (ex.: `hp4` = Siamês 3/4). A linha `autofill-core` agora é igual a `atk*hp-cap3` (o core passou a fazer essa política); `cap2` = `cap3` porque 5 raças x 2 = 10 < 12 e o limite sobe.

### Siamês (dados novos)

| Cenário | Antes | Depois |
|---|---|---|
| Deck realista (4 Siamês + 8 mistos) vs misto | 58,1% (maior das 5) | **50,8%** (faixa entre raças 40 a 54%: Vira-lata 39,7, Siamês 50,8, Persa 53,5, Sphynx 41,2, Maine Coon 47,6) |
| Round-robin mono-raça | 82,2% | **58,4%** (Persa 67,8 e Vira-lata 56,2 acima; Maine Coon 31,0 e Sphynx 36,5 abaixo) |
| Mono-raça vs misto | 39,5% | **24,1%** (as demais: 9 a 12%) |
| Misto com 4+ cópias vs 0-1 | 56,6% vs 43,7% | **51,7% vs 48,4%** (efeito quase nulo) |
| Run da IA (deck de 12 sorteados) com 4+ vs 0-1 Siamês | 13,4% vs 9,6% | **2,0% vs 2,8%** (ruído; ver "run" abaixo) |

Leitura: o Siamês saiu de dominante para o meio (50,8% no realista). Nenhuma raça passa de 60% no deck realista. Em deck puro o Siamês ainda é a 2ª melhor raça (58,4%), atrás do Persa (67,8%); o Persa passa a ser o ponto alto do round-robin mono-raça, mas no deck realista fica em 53,5% (não é problema hoje). Sphynx e Vira-lata seguem abaixo de 45% no realista, como antes (não depende do Siamês).

### Natureza (dados novos: Calmo 0/+1)

Deck 100% da natureza (IV real) vs misto: **Calmo 49,2%, Bravo 44,5%, Agitado 55,0%** (antes 28,1 / 60,3 / 65,3). Todas entre 44 e 55%, mas o ordem inverteu na ponta: Agitado é o melhor e o Bravo o mais fraco.
Par a par, IV 3/3: Calmo x Bravo 53,4%, Calmo x Agitado 54,9%, Bravo x Agitado **41,5%** (Agitado 58,5% sobre Bravo). Com IV real: 53,6 / 45,2 / 40,0.
Observação: o Siamês 3 de ATK mudou também a base; as medições antigas do Calmo 0/+1 (53,6 / 44,8 / 53,0) concordam com estas (dentro de ±2 pontos), ou seja, a ordem Agitado > Calmo > Bravo se manteve e o Bravo ficou mais ou menos 5 a 10 pontos atrás do Agitado. Se o Renatho quiser fechar isso: `bravo+1-2` piora (27,5%); `agitado+2-3` leva o Agitado a 35,9% e deixa Calmo (57,5) e Bravo (52,6) na frente; medir `Bravo +1/-1` com Agitado +2/-3 ou intermediários fica como opção (sem decisão minha).

### Como o deck é montado (COMPLETAR novo)

Coleção de 30 gatos do perfil, deck de 12, run completa da IA (900 runs por célula):

| Política | Mediana (IV 2 ou 3) | Real | Perfeita (5/5) |
|---|---|---|---|
| **COMPLETAR do core hoje** (ATK*HP, máx. 3 por raça) | **11,0%** | **15,9%** | **56,8%** |
| 12 ao acaso | 3,7% | 3,6% | 60,1% |
| ATK+HP, máx. 3 por raça (política velha com limite) | 8,3% | 9,6% | 55,6% |
| ATK*HP, máx. 4 por raça | 11,2% | 11,8% | 43,9% |
| ATK*HP sem limite | 3,2% | 5,9% | 22,0% |
| 2ATK+HP sem limite | 0,7% | 1,8% | 5,0% |

Comparação com a rodada anterior: a mesma política (ATK*HP, máx. 3) valia 32,4 / 35,0 / 76,3%; hoje 11,0 / 15,9 / 56,8%. A queda (mais de 20 pontos) vem de o Siamês ter perdido 1 ATK: os inimigos das runs (Madame Fifi com Siamês e Sphynx, e os rivais) também ficaram mais fracos, mas o jogador perdeu mais, pois seus decks de máx. 3 por raça usam 3 Siamês e 3 Sphynx no topo. Não isolei a causa (seria preciso rodar a run com o Siamês antigo só para o jogador ou só para os inimigos). **Dúvida para o Renatho:** a meta de dificuldade é rodada da IA com a coleção mediana a cerca de 11% e a real a cerca de 16%? Pelo método isso é piso (a IA drafta ao acaso).
O COMPLETAR do core agora é a melhor política testada sobre o conjunto mediana/real e a 2ª na perfeita (a de 12 ao acaso empata dentro do ruído de ±2 pontos com 60%, mas o ATK*HP máx. 3 é superior na mediana).

### Run mediana contra run perfeita, com o COMPLETAR novo (progressão com breed)

Jogador novo que adota tudo, monta o deck com o COMPLETAR do core e joga até 100 runs. Vitória da run da IA por janela:

| Estratégia | Runs 1-10 | 11-30 | 31-60 | 61-100 | 12 gatos 5/5 no deck |
|---|---|---|---|---|---|
| nenhuma (sem breed) | 10,3% | 26,5% | 40,2% | 46,0% | 66,4% (390 runs, todas as estratégias) |
| simples | 4,8% | 28,2% | 43,1% | 45,5% | idem |
| ótima | 3,0% | 30,8% | 51,1% | 50,1% | idem |

Resumo do efeito do 5/5 no deck (todas as estratégias): 0-2 gatos 5/5: 21,1%; 3-7: 42,0%; 8-11: 53,6%; **12: 66,4%**. Com o jogador "razoável" (mesma política): 22,2 / 44,3 / 53,2 / 56,9%.
Ou seja: coleção mediana (início) ~5-10% nas primeiras runs, perfeita ~57 a 66% (rodada anterior: 18% a 75%). O gato perfeito continua pesando muito (3x), mas o jogo não vira trivial: o teto da IA é de ~2/3.

### Cenário "fraco" refeito (jogador que usa o COMPLETAR do core)

Antes o COMPLETAR (ATK+HP, sem limite) rendia 12% nas runs 1-10 e 3 a 4% nas 61-100 e, sem breed, o 1º 5/5 vinha só na run 26. Agora:

| | Antes (autofill velho) | Depois (autofill novo) |
|---|---|---|
| Vitória nas runs 1-10 (simples) | 12% | 4,8% |
| Vitória nas runs 61-100 (simples) | 3 a 4% | **45,5%** |
| Vitória nas runs 61-100 (ótima) | n/m | 50,1% |
| 1º 5/5 (sem breed): mediana | 26 | **14** |
| 1º par de pais 5/5 (simples): mediana | 26 | **21** (razoável: 22) |
| 1º par de pais 5/5 (ótima): mediana | 21 | **18** (razoável: 15) |
| 5/5 por breed até a run 100 (simples) | n/m | 100% |
| Deck de 12 todos 5/5 até a run 100 (simples / ótima) | n/m | 8,3% / 10,0% (razoável: 5,0 / 18,3) |
| Gatos 5/5 na run 100 (simples / ótima) | 42 / 99 | **86 / 249** |

O cenário "fraco" deixou de existir: o COMPLETAR e o "razoável" agora são praticamente a mesma política (diferenças de 1 a 3 pontos são ruído; a ordem da raça e do id mudam o desempate), e a vitória da run cresce com a coleção (4,8% nas primeiras runs até ~45-50% depois das 60).
Efeito colateral da dificuldade: as primeiras runs ficam difíceis para a IA (5 a 10%) e só melhoram com a coleção; um humano que draft melhor deve ir bem acima disso.

### Pendências
- Nada foi mudado em `core/`, `data/` ou `ui/`; só testes, `sim/` e esta seção. Os arquivos antigos `sim/balanceamento_*.md` continuam como a medição "antes".
- Não foi medida a atribuição da queda de vitória (jogador vs inimigos) com o Siamês 3; se a meta de dificuldade for reajustada, remedir.
