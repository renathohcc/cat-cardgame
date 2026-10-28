# Balanceamento, rodada 2 (T6.0): seeds [1, 2, 3], 1000 duelos por celula por seed

IA simples dos dois lados; sem cartas de efeito nos duelos de decks (as runs incluem drafts de efeitos e Espiritos escolhidos ao acaso). Valem para essa IA, nao para um humano. Dados atuais = pacote B ja aplicado.

## Tema 2: naturezas (seeds [1, 2, 3], 1000 duelos por celula por seed)

Variantes:

- `base`: Calmo -1/+1, Bravo +1/-1, Agitado +2/-2 (dados atuais)
- `calmo0+1`: Calmo 0/+1
- `calmo0+2`: Calmo 0/+2
- `calmo-1+2`: Calmo -1/+2
- `calmo0+3`: Calmo 0/+3
- `bravo+1-2`: Bravo +1/-2
- `agitado+2-3`: Agitado +2/-3
- `calmo0+2-bravo+1-2`: Calmo 0/+2 e Bravo +1/-2
- `calmo0+2-agit+2-3`: Calmo 0/+2 e Agitado +2/-3
- `calmo0+1-agit+2-3`: Calmo 0/+1 e Agitado +2/-3
- `calmo0+2-agit+1-2`: Calmo 0/+2 e Agitado +1/-2

### IV 3/3 fixo, decks mistos, natureza unica por deck (vitoria do primeiro)

| Variante | Calmo x Bravo | Calmo x Agitado | Bravo x Agitado |
|---|---|---|---|
| base | 16.9% | 14.9% | 39.5% |
| calmo0+1 | 57.1% | 52.8% | 39.5% |
| calmo0+2 | 76.4% | 62.4% | 39.5% |
| calmo-1+2 | 36.1% | 24.3% | 39.5% |
| calmo0+3 | 79.1% | 72.9% | 39.5% |
| bravo+1-2 | 35.6% | 14.9% | 17.3% |
| agitado+2-3 | 16.9% | 41.4% | 64.4% |
| calmo0+2-bravo+1-2 | 85.0% | 62.4% | 17.3% |
| calmo0+2-agit+2-3 | 76.4% | 81.8% | 64.4% |
| calmo0+1-agit+2-3 | 57.1% | 80.2% | 64.4% |
| calmo0+2-agit+1-2 | 76.4% | 85.7% | 80.3% |

### IV sorteado real, natureza unica por deck (vitoria do primeiro)

| Variante | Calmo x Bravo | Calmo x Agitado | Bravo x Agitado |
|---|---|---|---|
| base | 19.7% | 17.5% | 42.4% |
| calmo0+1 | 56.7% | 49.8% | 42.4% |
| calmo0+2 | 69.5% | 68.5% | 42.4% |
| calmo-1+2 | 33.1% | 32.5% | 42.4% |
| calmo0+3 | 74.4% | 74.1% | 42.4% |
| bravo+1-2 | 43.3% | 17.5% | 21.1% |
| agitado+2-3 | 19.7% | 42.3% | 62.8% |
| calmo0+2-bravo+1-2 | 85.1% | 68.5% | 21.1% |
| calmo0+2-agit+2-3 | 69.5% | 83.4% | 62.8% |
| calmo0+1-agit+2-3 | 56.7% | 73.0% | 62.8% |
| calmo0+2-agit+1-2 | 69.5% | 84.2% | 72.7% |

### Deck 100% de uma natureza (IV real) vs deck misto

| Variante | Calmo | Bravo | Agitado |
|---|---|---|---|
| base | 28.1% | 60.3% | 65.3% |
| calmo0+1 | 53.6% | 44.8% | 53.0% |
| calmo0+2 | 61.8% | 37.2% | 44.8% |
| calmo-1+2 | 38.2% | 54.8% | 58.6% |
| calmo0+3 | 64.0% | 32.9% | 38.2% |
| bravo+1-2 | 35.1% | 43.1% | 73.1% |
| agitado+2-3 | 36.6% | 66.0% | 46.6% |
| calmo0+2-bravo+1-2 | 66.4% | 23.4% | 52.0% |
| calmo0+2-agit+2-3 | 68.2% | 44.0% | 28.9% |
| calmo0+1-agit+2-3 | 60.4% | 51.2% | 35.0% |
| calmo0+2-agit+1-2 | 68.9% | 47.4% | 26.2% |

### Escala: quanto vale cada ajuste de status (deck misto A vs B; A tem o beneficio; variante 'base')

| Diferenca de status entre os decks | Vitoria de A |
|---|---|
| +1 ATK (IV ATK 3 vs 1) | 83.6% |
| +1 HP (IV HP 3 vs 2) | 72.1% |
| +2 HP (IV HP 3 vs 1) | 87.6% |
| +1 ATK -1 HP (3/2 vs 1/3) | 62.4% |
| +2 ATK -2 HP (5/1 vs 1/3) | 69.6% |
| IV 3/3 vs 2/2 | 92.1% |
| IV 4/4 vs 3/3 | 70.9% |

