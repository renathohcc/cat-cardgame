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
- `mut0`: Mutacao 0% (referencia)
- `mut3`: Mutacao 3%
- `mut10`: Mutacao 10%
- `ninhada1-2`: Ninhada 1-2
- `ninhada1-4`: Ninhada 1-4 (exemplo do GDD)
- `melhor-pai`: Cada IV do filhote = o maior dos pais (+mutacao 7%)
- `tempo3`: Tempo de breed 3 runs
- `tempo4`: Tempo de breed 4 runs
- `raras-lentas`: Tempo por raca (casal = maior dos dois): Vira-lata 2, Persa 2, Siames 3, Sphynx 3, Maine Coon 4 (raridade hipotetica, o GDD nao define)
- `mut3-melhor-pai`: Melhor pai + mutacao 3%

### 4.1 Estrategia nenhuma

Colunas: jogadores com o 1o 5/5 de qualquer origem ate a run 30 / 100 e mediana da run; idem so por adocao (inclui os gatos iniciais); 1o par de pais 5/5 (macho e femea adultos) ate 30 / 100 e mediana; 5/5 nascidos de breed ate 100; deck inteiro de 12 gatos 5/5 (ate 100 e mediana); media de gatos 5/5 e de gatos na colecao na run 100.

| Variante | 1o 5/5: ate 30 | ate 100 | mediana | so adocao: ate 30 | ate 100 | par 5/5: ate 30 | ate 100 | mediana | por breed (100) | deck 12x5/5: ate 100 | mediana | 5/5 medios (100) | gatos (100) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base | 86.7% | 100.0% | 12 | 86.7% | 100.0% | 40.0% | 100.0% | 33 | 0.0% | 0.0% | >- (so 0/60) | 8.8 | 334 |

### 4.2 Dificuldade ao longo da progressao (nenhuma)

Vitoria da run da IA e soma media (IV ATK + IV HP) do deck, por janela de runs.

| Variante | Runs 1-10 | 11-30 | 31-60 | 61-100 | Soma de IV do deck em 1-10 / 31-60 / 61-100 |
|---|---|---|---|---|---|
| base | 23.2% | 45.8% | 61.1% | 62.2% | 5.6 / 8.6 / 9.1 |

### 4.3 Estrategia simples

Colunas: jogadores com o 1o 5/5 de qualquer origem ate a run 30 / 100 e mediana da run; idem so por adocao (inclui os gatos iniciais); 1o par de pais 5/5 (macho e femea adultos) ate 30 / 100 e mediana; 5/5 nascidos de breed ate 100; deck inteiro de 12 gatos 5/5 (ate 100 e mediana); media de gatos 5/5 e de gatos na colecao na run 100.

| Variante | 1o 5/5: ate 30 | ate 100 | mediana | so adocao: ate 30 | ate 100 | par 5/5: ate 30 | ate 100 | mediana | por breed (100) | deck 12x5/5: ate 100 | mediana | 5/5 medios (100) | gatos (100) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base | 100.0% | 100.0% | 10 | 90.0% | 100.0% | 93.3% | 100.0% | 17 | 100.0% | 3.3% | >83 (so 2/60) | 93.5 | 459 |
| mut0 | 88.3% | 100.0% | 10 | 86.7% | 100.0% | 85.0% | 100.0% | 18 | 100.0% | 5.0% | >89 (so 3/60) | 89.4 | 453 |
| mut3 | 90.0% | 100.0% | 10 | 83.3% | 100.0% | 86.7% | 100.0% | 17 | 100.0% | 5.0% | >89 (so 3/60) | 90.8 | 457 |
| mut10 | 100.0% | 100.0% | 10 | 88.3% | 100.0% | 96.7% | 100.0% | 17 | 100.0% | 6.7% | >83 (so 4/60) | 94.8 | 460 |
| ninhada1-2 | 98.3% | 100.0% | 11 | 95.0% | 100.0% | 93.3% | 100.0% | 20 | 100.0% | 8.3% | >100 (so 5/60) | 72.1 | 434 |
| ninhada1-4 | 98.3% | 100.0% | 10 | 83.3% | 100.0% | 96.7% | 100.0% | 17 | 100.0% | 8.3% | >96 (so 5/60) | 115.0 | 477 |
| melhor-pai | 100.0% | 100.0% | 9 | 95.0% | 100.0% | 100.0% | 100.0% | 13 | 100.0% | 6.7% | >97 (so 4/60) | 97.6 | 453 |
| tempo3 | 98.3% | 100.0% | 14 | 90.0% | 100.0% | 81.7% | 100.0% | 22 | 100.0% | 8.3% | >84 (so 5/60) | 61.9 | 420 |
| tempo4 | 93.3% | 100.0% | 13 | 83.3% | 100.0% | 78.3% | 100.0% | 24 | 100.0% | 3.3% | >70 (so 2/60) | 47.1 | 398 |
| raras-lentas | 95.0% | 100.0% | 14 | 90.0% | 100.0% | 76.7% | 100.0% | 23 | 100.0% | 3.3% | >59 (so 2/60) | 65.4 | 432 |
| mut3-melhor-pai | 98.3% | 100.0% | 9 | 91.7% | 100.0% | 95.0% | 100.0% | 14 | 100.0% | 8.3% | >97 (so 5/60) | 96.4 | 452 |

### 4.4 Dificuldade ao longo da progressao (simples)

Vitoria da run da IA e soma media (IV ATK + IV HP) do deck, por janela de runs.

| Variante | Runs 1-10 | 11-30 | 31-60 | 61-100 | Soma de IV do deck em 1-10 / 31-60 / 61-100 |
|---|---|---|---|---|---|
| base | 18.2% | 55.6% | 69.2% | 72.8% | 5.2 / 9.2 / 9.5 |
| mut0 | 18.0% | 54.3% | 67.3% | 71.3% | 5.2 / 9.1 / 9.5 |
| mut3 | 18.2% | 55.2% | 68.4% | 72.2% | 5.2 / 9.1 / 9.5 |
| mut10 | 18.5% | 56.3% | 68.8% | 72.9% | 5.2 / 9.2 / 9.5 |
| ninhada1-2 | 15.5% | 53.8% | 71.1% | 73.1% | 5.2 / 9.1 / 9.5 |
| ninhada1-4 | 18.5% | 57.3% | 67.5% | 69.2% | 5.2 / 9.1 / 9.5 |
| melhor-pai | 18.3% | 58.4% | 68.9% | 68.9% | 5.3 / 9.2 / 9.5 |
| tempo3 | 18.8% | 52.2% | 69.3% | 70.0% | 5.2 / 9.1 / 9.5 |
| tempo4 | 18.7% | 51.2% | 65.1% | 70.5% | 5.2 / 9.0 / 9.5 |
| raras-lentas | 18.2% | 55.2% | 68.8% | 74.1% | 5.2 / 9.1 / 9.5 |
| mut3-melhor-pai | 18.0% | 56.5% | 68.8% | 69.0% | 5.2 / 9.2 / 9.5 |

### 4.5 Estrategia otima

Colunas: jogadores com o 1o 5/5 de qualquer origem ate a run 30 / 100 e mediana da run; idem so por adocao (inclui os gatos iniciais); 1o par de pais 5/5 (macho e femea adultos) ate 30 / 100 e mediana; 5/5 nascidos de breed ate 100; deck inteiro de 12 gatos 5/5 (ate 100 e mediana); media de gatos 5/5 e de gatos na colecao na run 100.

| Variante | 1o 5/5: ate 30 | ate 100 | mediana | so adocao: ate 30 | ate 100 | par 5/5: ate 30 | ate 100 | mediana | por breed (100) | deck 12x5/5: ate 100 | mediana | 5/5 medios (100) | gatos (100) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base | 100.0% | 100.0% | 9 | 90.0% | 100.0% | 98.3% | 100.0% | 14 | 100.0% | 38.3% | >96 (so 23/60) | 258.1 | 636 |
| mut0 | 98.3% | 100.0% | 9 | 88.3% | 100.0% | 91.7% | 100.0% | 14 | 100.0% | 8.3% | >93 (so 5/60) | 255.2 | 629 |
| mut3 | 100.0% | 100.0% | 9 | 91.7% | 100.0% | 98.3% | 100.0% | 14 | 100.0% | 26.7% | >89 (so 16/60) | 259.2 | 634 |
| mut10 | 100.0% | 100.0% | 9 | 86.7% | 100.0% | 100.0% | 100.0% | 14 | 100.0% | 30.0% | >96 (so 18/60) | 260.0 | 637 |
| ninhada1-2 | 98.3% | 100.0% | 9 | 81.7% | 100.0% | 96.7% | 100.0% | 16 | 100.0% | 8.3% | >96 (so 5/60) | 191.4 | 556 |
| ninhada1-4 | 100.0% | 100.0% | 8 | 95.0% | 100.0% | 100.0% | 100.0% | 13 | 100.0% | 26.7% | >98 (so 16/60) | 325.7 | 711 |
| melhor-pai | 100.0% | 100.0% | 7 | 85.0% | 100.0% | 100.0% | 100.0% | 12 | 100.0% | 25.0% | >99 (so 15/60) | 273.1 | 643 |
| tempo3 | 100.0% | 100.0% | 10 | 90.0% | 100.0% | 96.7% | 100.0% | 17 | 100.0% | 23.3% | >100 (so 14/60) | 168.8 | 535 |
| tempo4 | 96.7% | 100.0% | 10 | 81.7% | 100.0% | 93.3% | 100.0% | 20 | 100.0% | 30.0% | >100 (so 18/60) | 124.0 | 486 |
| raras-lentas | 100.0% | 100.0% | 10 | 83.3% | 100.0% | 93.3% | 100.0% | 16 | 100.0% | 21.7% | >100 (so 13/60) | 185.8 | 553 |
| mut3-melhor-pai | 100.0% | 100.0% | 8 | 86.7% | 100.0% | 100.0% | 100.0% | 12 | 100.0% | 25.0% | >100 (so 15/60) | 272.1 | 648 |

### 4.6 Dificuldade ao longo da progressao (otima)

Vitoria da run da IA e soma media (IV ATK + IV HP) do deck, por janela de runs.

| Variante | Runs 1-10 | 11-30 | 31-60 | 61-100 | Soma de IV do deck em 1-10 / 31-60 / 61-100 |
|---|---|---|---|---|---|
| base | 14.7% | 56.6% | 69.4% | 72.5% | 4.9 / 9.5 / 9.7 |
| mut0 | 15.2% | 53.8% | 67.6% | 71.0% | 4.9 / 9.4 / 9.6 |
| mut3 | 14.7% | 56.2% | 69.1% | 71.1% | 4.9 / 9.5 / 9.7 |
| mut10 | 15.7% | 55.5% | 70.7% | 72.3% | 4.9 / 9.5 / 9.7 |
| ninhada1-2 | 12.5% | 50.4% | 68.5% | 70.2% | 4.8 / 9.4 / 9.7 |
| ninhada1-4 | 14.2% | 58.1% | 72.0% | 72.5% | 4.9 / 9.5 / 9.7 |
| melhor-pai | 14.7% | 60.8% | 72.8% | 71.7% | 4.9 / 9.5 / 9.7 |
| tempo3 | 13.8% | 50.4% | 68.3% | 71.5% | 4.8 / 9.4 / 9.7 |
| tempo4 | 13.7% | 51.1% | 67.3% | 69.9% | 4.8 / 9.3 / 9.7 |
| raras-lentas | 13.2% | 50.2% | 68.3% | 72.5% | 4.8 / 9.4 / 9.7 |
| mut3-melhor-pai | 14.7% | 62.1% | 72.8% | 73.8% | 4.9 / 9.6 / 9.7 |

### 4.9 Efeito do 5/5 na dificuldade (todas as variantes e estrategias juntas)

Vitoria da run por numero de gatos 5/5 no deck de 12 daquela run. Confunde: quem tem muitos 5/5 joga mais runs.

| Gatos 5/5 no deck | Runs | Vitoria da run |
|---|---|---|
| 0-2 | 31542 | 33.5% |
| 3-7 | 46059 | 67.0% |
| 8-11 | 53122 | 71.9% |
| 12 | 7277 | 75.3% |

