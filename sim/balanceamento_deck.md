# Balanceamento, rodada 2 (T6.0): seeds [1, 2, 3], 1000 duelos por celula por seed

IA simples dos dois lados; sem cartas de efeito nos duelos de decks (as runs incluem drafts de efeitos e Espiritos escolhidos ao acaso). Valem para essa IA, nao para um humano. Dados atuais = pacote B ja aplicado.

## Tema 5: como o deck de 12 e montado (seeds [1, 2, 3], 300 runs por celula por seed)

Coleção de 30 gatos do perfil (med23 = cada IV 2 ou 3; real = pesos atuais; 5/5), deck de 12 escolhido pela política, run completa da IA (mapa e draft ao acaso). Vitória da run (nós vencidos em média).

| Politica | med23 | real | 5/5 |
|---|---|---|---|
| autofill-core: `autofill_deck` do core (maior ATK+HP finais, sem limite por raca) | 10.7% (2.1) | 14.8% (2.4) | 40.9% (3.7) |
| aleatorio: 12 gatos da colecao ao acaso | 11.4% (2.5) | 10.8% (2.5) | 69.3% (4.9) |
| atk+hp-cap3: maior ATK+HP, no maximo 3 por raca | 21.6% (3.2) | 25.4% (3.3) | 71.2% (5.1) |
| 2atk+hp-livre: maior 2xATK+HP, sem limite por raca | 2.6% (1.0) | 5.8% (1.5) | 13.1% (1.8) |
| atk*hp-livre: maior ATK*HP, sem limite por raca | 13.3% (2.4) | 15.7% (2.6) | 19.9% (2.3) |
| atk*hp-cap4: maior ATK*HP, no maximo 4 por raca | 24.1% (3.4) | 28.0% (3.5) | 47.2% (3.9) |
| atk*hp-cap3: maior ATK*HP, no maximo 3 por raca (politica 'razoavel' do tema breed) | 32.4% (4.0) | 35.0% (3.9) | 76.3% (5.2) |
| atk*hp-cap2: maior ATK*HP, no maximo 2 por raca | 32.4% (4.0) | 35.0% (3.9) | 76.3% (5.2) |

