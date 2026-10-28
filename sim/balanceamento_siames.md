# Balanceamento, rodada 2 (T6.0): seeds [1, 2, 3], 1000 duelos por celula por seed

IA simples dos dois lados; sem cartas de efeito nos duelos de decks (as runs incluem drafts de efeitos e Espiritos escolhidos ao acaso). Valem para essa IA, nao para um humano. Dados atuais = pacote B ja aplicado.

## Tema 1: Siames (seeds [1, 2, 3], 1000 duelos por experimento por seed, 300 runs por seed)

Variantes (so em memoria):

- `base`: Siames custo 3, ATK 4, HP 3, Investida (dados atuais)
- `custo4`: Custo 4
- `atk3`: ATK base 4 -> 3
- `hp4`: HP base 3 -> 4 (nao e um nerf; referencia)
- `sem-investida`: Remove Investida
- `atk3-hp4`: ATK 3, HP 4
- `custo4-hp4`: Custo 4, HP 4 (mantem ATK 4 e Investida)
- `atk3-sem-inv`: ATK 3 e sem Investida
- `atk3-hp2`: ATK 3, HP 3 -> 2 (mais fragil)

### 1.1 Vitoria por raca: round-robin mono-raca (quem comeca alterna)

| Variante | Vira-lata | Siamês | Persa | Sphynx | Maine Coon |
|---|---|---|---|---|---|
| base | 40.0% | 82.2% | 55.3% | 40.2% | 32.3% |
| custo4 | 60.1% | 7.5% | 75.7% | 58.5% | 48.2% |
| atk3 | 45.8% | 60.5% | 65.5% | 43.4% | 34.8% |
| hp4 | 36.8% | 93.4% | 52.4% | 36.2% | 31.2% |
| sem-investida | 53.1% | 26.2% | 69.7% | 51.6% | 49.3% |
| atk3-hp4 | 41.0% | 77.2% | 56.2% | 41.1% | 34.5% |
| custo4-hp4 | 58.4% | 13.0% | 74.7% | 57.8% | 46.2% |
| atk3-sem-inv | 58.0% | 9.3% | 74.2% | 56.7% | 51.9% |
| atk3-hp2 | 52.6% | 41.9% | 74.2% | 45.4% | 36.0% |

### 1.2 Vitoria por raca: deck realista (4 gatos da raca + 8 mistos) vs misto

| Variante | Vira-lata | Siamês | Persa | Sphynx | Maine Coon |
|---|---|---|---|---|---|
| base | 37.5% | 58.1% | 51.2% | 40.9% | 46.1% |
| custo4 | 40.7% | 45.2% | 52.3% | 44.8% | 47.6% |
| atk3 | 38.6% | 48.9% | 54.7% | 43.6% | 48.0% |
| hp4 | 36.5% | 65.2% | 48.5% | 38.8% | 42.6% |
| sem-investida | 38.3% | 37.9% | 51.9% | 47.2% | 55.7% |
| atk3-hp4 | 37.3% | 57.0% | 53.1% | 42.1% | 46.9% |
| custo4-hp4 | 38.1% | 51.4% | 48.9% | 42.3% | 48.3% |
| atk3-sem-inv | 39.6% | 27.8% | 53.0% | 49.2% | 57.9% |
| atk3-hp2 | 40.7% | 43.7% | 53.9% | 43.4% | 49.0% |

### 1.3 Vitoria por raca: deck mono-raca vs misto

| Variante | Vira-lata | Siamês | Persa | Sphynx | Maine Coon |
|---|---|---|---|---|---|
| base | 7.2% | 39.5% | 9.8% | 10.6% | 9.7% |
| custo4 | 12.4% | 0.3% | 13.8% | 16.6% | 13.2% |
| atk3 | 11.1% | 23.0% | 15.9% | 12.7% | 11.6% |
| hp4 | 5.6% | 55.9% | 6.6% | 8.6% | 8.3% |
| sem-investida | 13.8% | 6.6% | 17.1% | 22.8% | 22.2% |
| atk3-hp4 | 8.1% | 37.8% | 10.7% | 11.0% | 10.6% |
| custo4-hp4 | 8.9% | 1.1% | 10.7% | 13.6% | 11.0% |
| atk3-sem-inv | 17.6% | 1.6% | 19.9% | 25.1% | 25.1% |
| atk3-hp2 | 13.4% | 12.9% | 18.6% | 13.6% | 12.5% |

### 1.4 Uso: gatos da raca jogados por copia no deck (misto vs misto; 1,00 = joga toda copia que compra)
Menor que o dos outros = a raca fica na mao (custo alto) ou o duelo acaba antes.

| Variante | Vira-lata | Siamês | Persa | Sphynx | Maine Coon |
|---|---|---|---|---|---|
| base | 0.75 | 0.83 | 0.75 | 0.83 | 0.83 |
| custo4 | 0.71 | 0.87 | 0.70 | 0.80 | 0.81 |
| atk3 | 0.74 | 0.83 | 0.75 | 0.83 | 0.84 |
| hp4 | 0.74 | 0.83 | 0.74 | 0.82 | 0.82 |
| sem-investida | 0.83 | 0.90 | 0.84 | 0.90 | 0.90 |
| atk3-hp4 | 0.73 | 0.83 | 0.74 | 0.83 | 0.83 |
| custo4-hp4 | 0.70 | 0.87 | 0.71 | 0.81 | 0.80 |
| atk3-sem-inv | 0.82 | 0.90 | 0.82 | 0.90 | 0.90 |
| atk3-hp2 | 0.75 | 0.84 | 0.75 | 0.84 | 0.84 |

### 1.5 Vitoria do deck misto por numero de copias da raca (0-1 / 2-3 / 4+; duelo IA vs IA)

| Variante | Vira-lata | Siamês | Persa | Sphynx | Maine Coon |
|---|---|---|---|---|---|
| base | 54.3% / 50.7% / 42.3% | 43.7% / 50.9% / 56.6% | 44.0% / 52.5% / 51.3% | 56.0% / 49.4% / 43.8% | 45.1% / 52.4% / 50.3% |
| custo4 | 51.1% / 50.6% / 47.1% | 52.8% / 49.8% / 46.6% | 43.1% / 50.8% / 57.1% | 53.1% / 50.6% / 44.6% | 44.0% / 52.7% / 50.9% |
| atk3 | 55.3% / 49.6% / 43.9% | 50.4% / 50.3% / 48.6% | 42.7% / 52.3% / 54.5% | 52.9% / 50.3% / 45.4% | 45.7% / 51.1% / 52.7% |
| hp4 | 53.1% / 51.0% / 43.2% | 40.9% / 51.1% / 60.4% | 44.7% / 52.1% / 51.6% | 57.2% / 49.6% / 41.7% | 48.1% / 51.1% / 49.6% |
| sem-investida | 53.7% / 50.1% / 44.8% | 55.9% / 49.7% / 42.5% | 45.8% / 50.7% / 53.7% | 50.8% / 50.0% / 49.0% | 41.4% / 51.6% / 57.0% |
| atk3-hp4 | 55.5% / 50.2% / 42.2% | 45.0% / 50.9% / 54.9% | 42.9% / 52.3% / 53.6% | 52.3% / 51.1% / 44.4% | 47.3% / 51.6% / 49.4% |
| custo4-hp4 | 53.9% / 49.7% / 45.6% | 50.3% / 49.7% / 50.3% | 44.6% / 51.4% / 53.7% | 51.3% / 50.9% / 46.1% | 45.7% / 51.9% / 50.7% |
| atk3-sem-inv | 52.2% / 50.7% / 45.0% | 60.1% / 50.0% / 35.7% | 41.3% / 53.1% / 53.8% | 50.2% / 49.8% / 50.3% | 39.3% / 51.9% / 58.7% |
| atk3-hp2 | 54.3% / 50.2% / 43.5% | 54.2% / 50.1% / 43.8% | 42.5% / 52.0% / 55.4% | 50.2% / 50.6% / 48.1% | 43.1% / 51.8% / 54.4% |

### 1.6 Runs completas da IA (deck inicial de 12 sorteados; mapa e draft ao acaso)

Vitoria da run por numero de copias da raca no deck inicial (0-1 / 2-3 / 4+).

| Variante | Run vence (todas) | Nos vencidos (media) | Vira-lata | Siamês | Persa | Sphynx | Maine Coon |
|---|---|---|---|---|---|---|---|
| base | 11.0% | 2.61 | 11.2% / 11.3% / 9.9% | 9.6% / 10.7% / 13.4% | 1.8% / 12.3% / 18.3% | 16.3% / 9.9% / 6.6% | 15.3% / 10.1% / 7.4% |
| custo4 | 10.6% | 2.70 | 10.5% / 10.6% / 10.7% | 12.1% / 11.9% / 5.8% | 5.2% / 10.8% / 16.5% | 9.0% / 11.7% / 10.0% | 10.7% / 11.0% / 9.3% |
| atk3 | 10.0% | 2.66 | 12.2% / 9.7% / 7.9% | 10.0% / 10.2% / 9.4% | 3.0% / 9.5% / 19.1% | 11.1% / 10.7% / 6.9% | 13.8% / 9.7% / 5.5% |
| hp4 | 13.0% | 2.55 | 15.3% / 12.2% / 11.6% | 7.8% / 14.2% / 16.2% | 5.9% / 12.8% / 21.9% | 17.1% / 12.7% / 8.3% | 16.8% / 13.5% / 6.2% |
| sem-investida | 10.2% | 2.79 | 11.6% / 9.7% / 9.8% | 12.3% / 9.1% / 10.1% | 5.9% / 9.5% / 17.8% | 15.6% / 7.6% / 9.9% | 9.2% / 10.1% / 12.0% |
| atk3-hp4 | 9.3% | 2.55 | 11.5% / 9.8% / 5.3% | 5.5% / 11.1% / 10.3% | 3.0% / 10.5% / 14.2% | 13.5% / 8.1% / 7.3% | 10.7% / 10.2% / 5.1% |
| custo4-hp4 | 8.9% | 2.60 | 10.5% / 8.8% / 6.7% | 5.6% / 10.0% / 10.2% | 6.0% / 9.3% / 11.4% | 8.9% / 8.7% / 9.4% | 10.5% / 8.5% / 7.7% |
| atk3-sem-inv | 11.6% | 2.77 | 15.9% / 10.3% / 8.5% | 16.0% / 11.1% / 7.1% | 4.0% / 12.9% / 18.5% | 11.2% / 9.7% / 16.9% | 10.5% / 12.6% / 10.7% |
| atk3-hp2 | 8.2% | 2.67 | 8.9% / 8.6% / 6.4% | 8.4% / 9.6% / 4.0% | 3.4% / 9.4% / 11.2% | 7.4% / 9.0% / 7.6% | 9.4% / 9.5% / 3.6% |

