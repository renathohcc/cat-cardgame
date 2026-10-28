# Balanceamento, rodada 2 (T6.0): seeds [1, 2, 3], 1000 duelos por celula por seed

IA simples dos dois lados; sem cartas de efeito nos duelos de decks (as runs incluem drafts de efeitos e Espiritos escolhidos ao acaso). Valem para essa IA, nao para um humano. Dados atuais = pacote B ja aplicado.

## Tema 4: gato perfeito por breed (seeds [1, 2, 3], 20 jogadores por seed, 100 runs cada)

Modelo: jogador novo (12 gatos sorteados) joga runs completas da IA (mapa e draft ao acaso), adota todos os gatos oferecidos e monta o deck pelo maior ATK*HP final com no maximo 3 gatos por raca (jogador razoavel). Estrategias: **nenhuma** = nunca faz breed (so adocao); **simples** = um casal por vez, o macho e a femea de maior soma de IV; **otima** = ate 3 casais ao mesmo tempo, escolhidos por P(filhote 5/5) e soma esperada. Nada e doado. Pais saem do deck durante o breed (como no jogo). Adocao com pity e deslocamento de pesos por nos vencidos (dados atuais):

| Nos vencidos | Gatos (derrota) | Gatos (vitoria) | P(IV 5) por IV | P(gato 5/5) |
|---|---|---|---|---|
| 0 | 0 | 2 | 5.0% | 0.3% |
| 1 | 0 | 2 | 7.0% | 0.5% |
| 2 | 1 | 3 | 9.0% | 0.8% |
| 3 | 1 | 3 | 11.0% | 1.2% |
| 4 | 2 | 4 | 13.0% | 1.7% |
| 5 | 2 | 4 | 15.0% | 2.2% |
| 6 | 3 | 5 | 17.0% | 2.9% |

Variantes:

- `base`: Mutacao 7%, ninhada 1-3, breed 2 runs (dados atuais)
- `adocao-shift1`: Adocao: cada no vencido desloca 1 peso de IV 1 para IV 5 (hoje 2)
- `adocao-shift0`: Adocao: sem deslocamento de pesos por no vencido (so os pesos base)

### 4.1 Estrategia nenhuma

Colunas: jogadores com o 1o 5/5 de qualquer origem ate a run 30 / 100 e mediana da run; idem so por adocao (inclui os gatos iniciais); 1o par de pais 5/5 (macho e femea adultos) ate 30 / 100 e mediana; 5/5 nascidos de breed ate 100; deck inteiro de 12 gatos 5/5 (ate 100 e mediana); media de gatos 5/5 e de gatos na colecao na run 100.

| Variante | 1o 5/5: ate 30 | ate 100 | mediana | so adocao: ate 30 | ate 100 | par 5/5: ate 30 | ate 100 | mediana | por breed (100) | deck 12x5/5: ate 100 | mediana | 5/5 medios (100) | gatos (100) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base | 86.7% | 100.0% | 12 | 86.7% | 100.0% | 40.0% | 100.0% | 33 | 0.0% | 0.0% | >- (so 0/60) | 8.8 | 334 |
| adocao-shift1 | 61.7% | 96.7% | 23 | 61.7% | 96.7% | 16.7% | 73.3% | 70 | 0.0% | 0.0% | >- (so 0/60) | 3.7 | 321 |
| adocao-shift0 | 28.3% | 68.3% | 68 | 28.3% | 68.3% | 1.7% | 18.3% | >100 (so 11/60) | 0.0% | 0.0% | >- (so 0/60) | 1.2 | 324 |

### 4.2 Dificuldade ao longo da progressao (nenhuma)

Vitoria da run da IA e soma media (IV ATK + IV HP) do deck, por janela de runs.

| Variante | Runs 1-10 | 11-30 | 31-60 | 61-100 | Soma de IV do deck em 1-10 / 31-60 / 61-100 |
|---|---|---|---|---|---|
| base | 23.2% | 45.8% | 61.1% | 62.2% | 5.6 / 8.6 / 9.1 |
| adocao-shift1 | 20.0% | 40.5% | 56.1% | 61.8% | 5.5 / 8.1 / 8.6 |
| adocao-shift0 | 19.3% | 42.1% | 56.1% | 61.5% | 5.3 / 7.5 / 8.1 |

### 4.3 Estrategia simples

Colunas: jogadores com o 1o 5/5 de qualquer origem ate a run 30 / 100 e mediana da run; idem so por adocao (inclui os gatos iniciais); 1o par de pais 5/5 (macho e femea adultos) ate 30 / 100 e mediana; 5/5 nascidos de breed ate 100; deck inteiro de 12 gatos 5/5 (ate 100 e mediana); media de gatos 5/5 e de gatos na colecao na run 100.

| Variante | 1o 5/5: ate 30 | ate 100 | mediana | so adocao: ate 30 | ate 100 | par 5/5: ate 30 | ate 100 | mediana | por breed (100) | deck 12x5/5: ate 100 | mediana | 5/5 medios (100) | gatos (100) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base | 100.0% | 100.0% | 10 | 90.0% | 100.0% | 93.3% | 100.0% | 17 | 100.0% | 3.3% | >83 (so 2/60) | 93.5 | 459 |
| adocao-shift1 | 88.3% | 100.0% | 16 | 63.3% | 96.7% | 78.3% | 100.0% | 23 | 100.0% | 0.0% | >- (so 0/60) | 79.4 | 442 |
| adocao-shift0 | 83.3% | 100.0% | 18 | 28.3% | 71.7% | 63.3% | 100.0% | 25 | 100.0% | 0.0% | >- (so 0/60) | 76.5 | 440 |

### 4.4 Dificuldade ao longo da progressao (simples)

Vitoria da run da IA e soma media (IV ATK + IV HP) do deck, por janela de runs.

| Variante | Runs 1-10 | 11-30 | 31-60 | 61-100 | Soma de IV do deck em 1-10 / 31-60 / 61-100 |
|---|---|---|---|---|---|
| base | 18.2% | 55.6% | 69.2% | 72.8% | 5.2 / 9.2 / 9.5 |
| adocao-shift1 | 17.2% | 52.4% | 64.0% | 67.6% | 5.1 / 8.8 / 9.1 |
| adocao-shift0 | 16.0% | 49.3% | 63.6% | 67.4% | 5.0 / 8.4 / 8.8 |

### 4.5 Estrategia otima

Colunas: jogadores com o 1o 5/5 de qualquer origem ate a run 30 / 100 e mediana da run; idem so por adocao (inclui os gatos iniciais); 1o par de pais 5/5 (macho e femea adultos) ate 30 / 100 e mediana; 5/5 nascidos de breed ate 100; deck inteiro de 12 gatos 5/5 (ate 100 e mediana); media de gatos 5/5 e de gatos na colecao na run 100.

| Variante | 1o 5/5: ate 30 | ate 100 | mediana | so adocao: ate 30 | ate 100 | par 5/5: ate 30 | ate 100 | mediana | por breed (100) | deck 12x5/5: ate 100 | mediana | 5/5 medios (100) | gatos (100) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base | 100.0% | 100.0% | 9 | 90.0% | 100.0% | 98.3% | 100.0% | 14 | 100.0% | 38.3% | >96 (so 23/60) | 258.1 | 636 |
| adocao-shift1 | 100.0% | 100.0% | 11 | 68.3% | 100.0% | 100.0% | 100.0% | 17 | 100.0% | 3.3% | >97 (so 2/60) | 246.5 | 628 |
| adocao-shift0 | 96.7% | 100.0% | 14 | 21.7% | 58.3% | 91.7% | 100.0% | 19 | 100.0% | 1.7% | >43 (so 1/60) | 236.2 | 619 |

### 4.6 Dificuldade ao longo da progressao (otima)

Vitoria da run da IA e soma media (IV ATK + IV HP) do deck, por janela de runs.

| Variante | Runs 1-10 | 11-30 | 31-60 | 61-100 | Soma de IV do deck em 1-10 / 31-60 / 61-100 |
|---|---|---|---|---|---|
| base | 14.7% | 56.6% | 69.4% | 72.5% | 4.9 / 9.5 / 9.7 |
| adocao-shift1 | 12.5% | 53.2% | 68.6% | 70.4% | 4.8 / 9.4 / 9.6 |
| adocao-shift0 | 11.5% | 49.5% | 66.9% | 68.7% | 4.7 / 9.0 / 9.2 |

### 4.9 Efeito do 5/5 na dificuldade (todas as variantes e estrategias juntas)

Vitoria da run por numero de gatos 5/5 no deck de 12 daquela run. Confunde: quem tem muitos 5/5 joga mais runs.

| Gatos 5/5 no deck | Runs | Vitoria da run |
|---|---|---|
| 0-2 | 21938 | 42.7% |
| 3-7 | 21772 | 65.9% |
| 8-11 | 9387 | 71.7% |
| 12 | 903 | 75.5% |

