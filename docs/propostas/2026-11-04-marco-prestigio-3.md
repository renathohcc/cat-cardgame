# Marco do Prestígio 3 ("5 raças") é trivial

## Problema
O marco atual `distinct_breeds` (count 5) só conta raças distintas no save, sem olhar qualidade. Os tipos de marco do core (`start`, `win_league`, `distinct_breeds`) não conseguem exigir IV alto.

## Opções
1. Novo tipo `distinct_breeds_min_iv`: `{"count": 5, "min_iv_sum": 8}`. Conta raças que têm ao menos 1 gato com soma de IV (ATK+HP) >= 8. Exige mudança em `core/prestige.py` (`_progress`) e no `rules.schema.json`.
2. Subir só o `count` do `distinct_breeds` (ex.: 7). Não precisa de código, mas só aumenta o grind e não pede qualidade.
3. Deixar como está.

## Recomendação
Opção 1, com os parâmetros sugeridos (count 5, min_iv_sum 8). O valor 8 é sugestão, o Renatho decide. Depois do core implementar, os dados trocam o marco e o schema ganha o novo tipo.
