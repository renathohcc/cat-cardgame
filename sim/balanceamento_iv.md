# Balanceamento, rodada 2 (T6.0): seeds [1, 2, 3], 1000 duelos por celula por seed

IA simples dos dois lados; sem cartas de efeito nos duelos de decks (as runs incluem drafts de efeitos e Espiritos escolhidos ao acaso). Valem para essa IA, nao para um humano. Dados atuais = pacote B ja aplicado.

## Tema 3: peso dos IVs (seeds [1, 2, 3], 1000 duelos e 300 runs por celula por seed)

### 3.1 Mesma raca nos dois lados, deck mono-raca: IV de A vs IV de B (vitoria de A, quem comeca alterna)

| Raca | 5/5 vs 1/1 | 5/1 vs 1/1 | 1/5 vs 1/1 | 3/3 vs 1/1 | 5/1 vs 1/5 |
|---|---|---|---|---|---|
| Vira-lata | 100.0% | 100.0% | 81.2% | 99.1% | 61.1% |
| Siamês | 86.5% | 59.2% | 73.5% | 72.0% | 50.0% |
| Persa | 100.0% | 100.0% | 100.0% | 100.0% | 56.5% |
| Sphynx | 96.1% | 92.6% | 75.3% | 87.8% | 50.9% |
| Maine Coon | 87.0% | 84.5% | 53.3% | 78.0% | 69.3% |

### 3.1b Um unico gato da raca no slot 0 (5/5 vs 1/1), resto do deck sorteado real; B misto real

| Raca | Com o gato 5/5 | Com o gato 1/1 | Diferenca (pontos) |
|---|---|---|---|
| Vira-lata | 54.9% | 43.6% | +11.2 |
| Siamês | 65.5% | 47.8% | +17.7 |
| Persa | 62.1% | 49.4% | +12.7 |
| Sphynx | 57.5% | 44.9% | +12.5 |
| Maine Coon | 58.9% | 47.0% | +11.9 |

### 3.2 Deck misto inteiro com IV fixo (vitoria de A)

| Confronto | base | pesos-topo+ | pesos-baixos | pesos-uniforme | pesos-medianos | div3 | div4 | div99 | hpdiv2 | hpdiv2-div3 |
|---|---|---|---|---|---|---|---|---|---|---|
| 5/5 vs 1/1 | 98.6% | 98.6% | 98.6% | 98.6% | 98.6% | 98.0% | 98.0% | 94.6% | 98.4% | 96.3% |
| 5/5 vs 3/3 | 90.7% | 90.7% | 90.7% | 90.7% | 90.7% | 91.7% | 91.7% | 78.6% | 89.9% | 93.1% |
| 3/3 vs 1/1 | 96.4% | 96.4% | 96.4% | 96.4% | 96.4% | 90.1% | 90.1% | 90.1% | 93.6% | 78.1% |
| real vs 5/5 | 4.8% | 5.4% | 3.2% | 8.5% | 5.8% | 7.0% | 5.9% | 16.9% | 4.3% | 6.0% |
| real vs 1/1 | 90.5% | 92.6% | 84.4% | 94.5% | 93.7% | 87.4% | 84.9% | 84.2% | 79.7% | 73.5% |
| 5/1 vs 1/5 | 30.5% | 30.5% | 30.5% | 30.5% | 30.5% | 12.8% | 12.8% | 5.7% | 69.4% | 33.4% |
| 5/1 vs 1/1 | 94.6% | 94.6% | 94.6% | 94.6% | 94.6% | 82.6% | 82.6% | 49.2% | 94.6% | 82.6% |
| 1/5 vs 1/1 | 92.6% | 92.6% | 92.6% | 92.6% | 92.6% | 92.6% | 92.6% | 92.6% | 90.0% | 90.0% |

### 3.3 Run completa da IA por perfil de colecao (vitoria da run / nos vencidos de 6 em media)

Perfis: 1/1, med23 (cada IV 2 ou 3, o 'mediano'), 3/3, real (sorteio pelos pesos), 4/4, 5/5. Mapa e draft ao acaso, IA dos dois lados.

| Variante | P(5/5 por gato) | 1/1 | med23 | 3/3 | real | 4/4 | 5/5 |
|---|---|---|---|---|---|---|---|
| base | 0.3% | 0.6% (1.1) | 11.4% (2.6) | 30.1% (3.7) | 10.7% (2.5) | 39.2% (4.0) | 71.0% (5.1) |
| pesos-topo+ | 1.0% | 0.6% (1.1) | 11.4% (2.6) | 30.1% (3.7) | 14.6% (2.8) | 39.2% (4.0) | 71.0% (5.1) |
| pesos-baixos | 0.0% | 0.6% (1.1) | 11.4% (2.6) | 30.1% (3.7) | 6.0% (2.2) | 39.2% (4.0) | 71.0% (5.1) |
| pesos-uniforme | 4.0% | 0.6% (1.1) | 11.4% (2.6) | 30.1% (3.7) | 24.9% (3.4) | 39.2% (4.0) | 71.0% (5.1) |
| pesos-medianos | 0.3% | 0.6% (1.1) | 11.4% (2.6) | 30.1% (3.7) | 17.0% (2.9) | 39.2% (4.0) | 71.0% (5.1) |
| div3 | 0.3% | 0.6% (1.3) | 9.9% (2.6) | 11.3% (2.7) | 12.2% (2.7) | 53.2% (4.5) | 57.8% (4.6) |
| div4 | 0.3% | 1.6% (1.2) | 15.8% (2.6) | 22.6% (2.9) | 14.4% (2.4) | 33.6% (3.4) | 63.6% (4.6) |
| div99 | 0.3% | 2.6% (1.2) | 19.0% (2.7) | 23.7% (2.9) | 15.0% (2.5) | 37.0% (3.5) | 42.7% (3.7) |
| hpdiv2 | 0.3% | 2.1% (1.7) | 16.0% (2.7) | 40.3% (3.8) | 16.9% (2.7) | 37.9% (3.8) | 71.8% (4.9) |
| hpdiv2-div3 | 0.3% | 6.7% (2.1) | 13.7% (2.7) | 22.4% (3.2) | 17.7% (2.8) | 46.8% (4.2) | 61.0% (4.7) |

### 3.4 Colecao de 30 gatos do perfil, deck de 12 escolhido pelo jogador (ATK*HP, no maximo 3 por raca)

Mesmas runs da IA (mapa e draft ao acaso). Vitoria da run (nos vencidos em media).

| Variante | med23 | real | 4/4 | 5/5 |
|---|---|---|---|---|
| base | 34.6% (4.1) | 33.8% (3.9) | 53.9% (4.6) | 72.1% (5.0) |
| pesos-topo+ | 34.6% (4.1) | 37.1% (4.1) | 53.9% (4.6) | 72.1% (5.0) |
| pesos-baixos | 34.6% (4.1) | 21.4% (3.4) | 53.9% (4.6) | 72.1% (5.0) |
| pesos-uniforme | 34.6% (4.1) | 48.2% (4.4) | 53.9% (4.6) | 72.1% (5.0) |
| pesos-medianos | 34.6% (4.1) | 38.1% (4.1) | 53.9% (4.6) | 72.1% (5.0) |
| div3 | 21.8% (3.6) | 31.6% (3.9) | 64.1% (5.0) | 63.7% (4.9) |
| div4 | 29.6% (3.7) | 37.7% (3.9) | 54.2% (4.5) | 73.7% (5.1) |
| div99 | 37.0% (3.8) | 40.8% (3.9) | 55.4% (4.5) | 60.0% (4.6) |
| hpdiv2 | 43.2% (4.1) | 42.1% (3.9) | 66.4% (4.9) | 83.2% (5.4) |
| hpdiv2-div3 | 38.0% (4.2) | 44.2% (4.3) | 75.0% (5.2) | 75.4% (5.2) |

