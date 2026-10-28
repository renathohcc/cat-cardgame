# Balanceamento, rodada 2 (T6.0): seeds [1, 2, 3], 1000 duelos por celula por seed

IA simples dos dois lados; sem cartas de efeito nos duelos de decks (as runs incluem drafts de efeitos e Espiritos escolhidos ao acaso). Valem para essa IA, nao para um humano. Dados atuais = pacote B ja aplicado.

## Tema 4: gato perfeito por breed (seeds [1, 2, 3], 20 jogadores por seed, 100 runs cada)

Modelo: jogador novo (12 gatos sorteados) joga runs completas da IA (mapa e draft ao acaso), adota todos os gatos oferecidos e monta o deck pelo `autofill_deck` do core (maior ATK+HP final, sem limite por raca). Estrategias: **nenhuma** = nunca faz breed (so adocao); **simples** = um casal por vez, o macho e a femea de maior soma de IV; **otima** = ate 3 casais ao mesmo tempo, escolhidos por P(filhote 5/5) e soma esperada. Nada e doado. Pais saem do deck durante o breed (como no jogo). Adocao com pity e deslocamento de pesos por nos vencidos (dados atuais):

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
- `ninhada1-2`: Ninhada 1-2
- `melhor-pai`: Cada IV do filhote = o maior dos pais (+mutacao 7%)
- `tempo3`: Tempo de breed 3 runs
- `raras-lentas`: Tempo por raca (casal = maior dos dois): Vira-lata 2, Persa 2, Siames 3, Sphynx 3, Maine Coon 4 (raridade hipotetica, o GDD nao define)

### 4.1 Estrategia nenhuma

Colunas: jogadores com o 1o 5/5 de qualquer origem ate a run 30 / 100 e mediana da run; idem so por adocao (inclui os gatos iniciais); 1o par de pais 5/5 (macho e femea adultos) ate 30 / 100 e mediana; 5/5 nascidos de breed ate 100; deck inteiro de 12 gatos 5/5 (ate 100 e mediana); media de gatos 5/5 e de gatos na colecao na run 100.

| Variante | 1o 5/5: ate 30 | ate 100 | mediana | so adocao: ate 30 | ate 100 | par 5/5: ate 30 | ate 100 | mediana | por breed (100) | deck 12x5/5: ate 100 | mediana | 5/5 medios (100) | gatos (100) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base | 60.0% | 85.0% | 26 | 60.0% | 85.0% | 13.3% | 43.3% | >94 (so 26/60) | 0.0% | 0.0% | >- (so 0/60) | 2.1 | 97 |

### 4.2 Dificuldade ao longo da progressao (nenhuma)

Vitoria da run da IA e soma media (IV ATK + IV HP) do deck, por janela de runs.

| Variante | Runs 1-10 | 11-30 | 31-60 | 61-100 | Soma de IV do deck em 1-10 / 31-60 / 61-100 |
|---|---|---|---|---|---|
| base | 15.0% | 14.2% | 6.9% | 3.3% | 5.6 / 6.9 / 7.1 |

### 4.3 Estrategia simples

Colunas: jogadores com o 1o 5/5 de qualquer origem ate a run 30 / 100 e mediana da run; idem so por adocao (inclui os gatos iniciais); 1o par de pais 5/5 (macho e femea adultos) ate 30 / 100 e mediana; 5/5 nascidos de breed ate 100; deck inteiro de 12 gatos 5/5 (ate 100 e mediana); media de gatos 5/5 e de gatos na colecao na run 100.

| Variante | 1o 5/5: ate 30 | ate 100 | mediana | so adocao: ate 30 | ate 100 | par 5/5: ate 30 | ate 100 | mediana | por breed (100) | deck 12x5/5: ate 100 | mediana | 5/5 medios (100) | gatos (100) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base | 80.0% | 96.7% | 14 | 61.7% | 81.7% | 61.7% | 91.7% | 26 | 95.0% | 15.0% | >81 (so 9/60) | 42.2 | 155 |
| mut0 | 65.0% | 78.3% | 18 | 61.7% | 78.3% | 45.0% | 76.7% | 36 | 76.7% | 13.3% | >81 (so 8/60) | 37.4 | 151 |
| mut3 | 75.0% | 91.7% | 13 | 61.7% | 85.0% | 50.0% | 86.7% | 32 | 90.0% | 16.7% | >81 (so 10/60) | 39.2 | 148 |
| ninhada1-2 | 80.0% | 98.3% | 13 | 65.0% | 80.0% | 63.3% | 93.3% | 27 | 96.7% | 6.7% | >87 (so 4/60) | 35.5 | 153 |
| melhor-pai | 83.3% | 100.0% | 10 | 61.7% | 78.3% | 76.7% | 98.3% | 16 | 100.0% | 21.7% | >78 (so 13/60) | 52.3 | 165 |
| tempo3 | 73.3% | 95.0% | 17 | 46.7% | 75.0% | 46.7% | 90.0% | 33 | 95.0% | 3.3% | >98 (so 2/60) | 27.4 | 135 |
| raras-lentas | 76.7% | 98.3% | 14 | 51.7% | 81.7% | 51.7% | 96.7% | 30 | 98.3% | 5.0% | >97 (so 3/60) | 31.2 | 137 |

### 4.4 Dificuldade ao longo da progressao (simples)

Vitoria da run da IA e soma media (IV ATK + IV HP) do deck, por janela de runs.

| Variante | Runs 1-10 | 11-30 | 31-60 | 61-100 | Soma de IV do deck em 1-10 / 31-60 / 61-100 |
|---|---|---|---|---|---|
| base | 12.5% | 18.3% | 10.7% | 3.6% | 5.1 / 8.2 / 8.3 |
| mut0 | 12.2% | 18.4% | 9.7% | 2.5% | 5.1 / 8.1 / 8.2 |
| mut3 | 12.7% | 17.8% | 8.7% | 2.8% | 5.1 / 8.2 / 8.4 |
| ninhada1-2 | 12.0% | 18.7% | 12.7% | 4.1% | 5.1 / 8.1 / 8.2 |
| melhor-pai | 12.5% | 17.6% | 11.4% | 4.2% | 5.2 / 8.6 / 8.6 |
| tempo3 | 10.8% | 13.0% | 8.9% | 4.7% | 5.1 / 7.8 / 8.2 |
| raras-lentas | 11.3% | 15.3% | 10.2% | 4.0% | 5.1 / 8.0 / 8.3 |

### 4.5 Estrategia otima

Colunas: jogadores com o 1o 5/5 de qualquer origem ate a run 30 / 100 e mediana da run; idem so por adocao (inclui os gatos iniciais); 1o par de pais 5/5 (macho e femea adultos) ate 30 / 100 e mediana; 5/5 nascidos de breed ate 100; deck inteiro de 12 gatos 5/5 (ate 100 e mediana); media de gatos 5/5 e de gatos na colecao na run 100.

| Variante | 1o 5/5: ate 30 | ate 100 | mediana | so adocao: ate 30 | ate 100 | par 5/5: ate 30 | ate 100 | mediana | por breed (100) | deck 12x5/5: ate 100 | mediana | 5/5 medios (100) | gatos (100) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| base | 88.3% | 98.3% | 12 | 40.0% | 61.7% | 73.3% | 96.7% | 21 | 98.3% | 40.0% | >97 (so 24/60) | 98.7 | 207 |
| mut0 | 81.7% | 95.0% | 13 | 46.7% | 68.3% | 70.0% | 95.0% | 22 | 95.0% | 21.7% | >93 (so 13/60) | 99.0 | 218 |
| mut3 | 86.7% | 95.0% | 12 | 35.0% | 56.7% | 75.0% | 91.7% | 22 | 95.0% | 35.0% | >97 (so 21/60) | 92.3 | 202 |
| ninhada1-2 | 88.3% | 98.3% | 14 | 46.7% | 61.7% | 78.3% | 95.0% | 21 | 98.3% | 28.3% | >92 (so 17/60) | 72.7 | 174 |
| melhor-pai | 98.3% | 100.0% | 8 | 53.3% | 75.0% | 91.7% | 96.7% | 12 | 100.0% | 31.7% | >99 (so 19/60) | 137.6 | 246 |
| tempo3 | 91.7% | 100.0% | 13 | 48.3% | 63.3% | 73.3% | 96.7% | 21 | 100.0% | 18.3% | >98 (so 11/60) | 61.1 | 161 |
| raras-lentas | 91.7% | 100.0% | 14 | 46.7% | 66.7% | 75.0% | 100.0% | 21 | 100.0% | 13.3% | >99 (so 8/60) | 86.2 | 199 |

### 4.6 Dificuldade ao longo da progressao (otima)

Vitoria da run da IA e soma media (IV ATK + IV HP) do deck, por janela de runs.

| Variante | Runs 1-10 | 11-30 | 31-60 | 61-100 | Soma de IV do deck em 1-10 / 31-60 / 61-100 |
|---|---|---|---|---|---|
| base | 8.8% | 14.2% | 6.3% | 2.2% | 4.8 / 8.4 / 8.8 |
| mut0 | 9.8% | 15.0% | 8.6% | 2.3% | 4.8 / 8.1 / 8.4 |
| mut3 | 8.7% | 12.4% | 6.9% | 1.5% | 4.8 / 8.3 / 8.7 |
| ninhada1-2 | 7.0% | 12.8% | 7.8% | 2.0% | 4.8 / 8.1 / 8.6 |
| melhor-pai | 10.8% | 18.8% | 10.7% | 3.4% | 5.0 / 8.7 / 8.8 |
| tempo3 | 7.0% | 13.0% | 6.6% | 2.3% | 4.8 / 8.0 / 8.5 |
| raras-lentas | 7.8% | 15.2% | 8.8% | 3.0% | 4.8 / 8.0 / 8.4 |

### 4.9 Efeito do 5/5 na dificuldade (todas as variantes e estrategias juntas)

Vitoria da run por numero de gatos 5/5 no deck de 12 daquela run. Confunde: quem tem muitos 5/5 joga mais runs.

| Gatos 5/5 no deck | Runs | Vitoria da run |
|---|---|---|
| 0-2 | 48630 | 6.5% |
| 3-7 | 28430 | 11.2% |
| 8-11 | 7181 | 13.3% |
| 12 | 5759 | 0.3% |

