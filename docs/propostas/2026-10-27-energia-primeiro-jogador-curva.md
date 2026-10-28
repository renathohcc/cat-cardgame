# Energia do 1o jogador: a curva toda ou so o turno 1?

## Problema
A decisao do pacote B diz: 1o jogador comeca com energia 1 e "depois +1 por turno" (turno 2 = 2).
O experimento que deu ~54,6% (sim/variantes, `first_turn1_energy_penalty`) penalizava SO o turno 1:
a curva do 1o jogador era 1, 3, 4, 5... (o 2o jogador: 2, 3, 4...).
Implementada literalmente (curva 1, 2, 3...), o 1o jogador fica 1 de energia atras PARA SEMPRE.

## Medido (core real, 1000 duelos misto vs misto, seed 1, Persa 2 / Maine Coon 3)
| Regra | 1o jogador vence |
|---|---|
| Sem a chave (antigo) | 83,1% |
| Literal: 1, 2, 3, ... | 19,8% (o 2o jogador domina) |
| So turno 1: 1, 3, 4, ... | 54,3% (bate com o experimento) |

## Opcoes
A. So o turno 1 usa `first_player_energy_start`; do turno 2 em diante vale a curva normal (energy_start + (n-1)). Recomendada.
B. Curva inteira deslocada (literal). Exigiria outro numero (ex.: 2 como start e 1 so no turno 1 nao se aplica); 19,8% inviavel sem novo balanceamento.

## Recomendacao
A. Mudanca de 1 linha em `core/duel.py::_turn_energy` (`and n == 1`). Aguardando OK do Renatho.


Decidido pelo Renatho (2026-10-27): só o turno 1.
