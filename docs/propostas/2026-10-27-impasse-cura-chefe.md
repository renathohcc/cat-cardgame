# Proposta: impasse com cura do Líder do chefe (Banho de Espuma)

Autor: agente core (T3.2).

## Problema
Com a regra "Banho de Espuma" (Líder do chefe cura 1 no início do turno dele), um único atacante de ATK 1 do jogador (ex.: Vira-lata 1/7) causa 1 por turno e o chefe cura 1: HP do Líder nunca baixa. O gatilho de impasse atual (nenhuma carta de gato/Especial em mão/deck, nenhum gato em campo) não dispara, porque o jogador ainda tem gato em campo. Resultado: duelo infinito (IA vs IA; um humano simplesmente teria que descartar a vitória). Aconteceu em 1 de 150 duelos simulados contra a Madame Fifi. Não existia antes: sem cura, qualquer gato com ATK >= 1 acaba vencendo.

## Opções
1. Impasse por estagnação: se por N rodadas completas (N em `rules.deadlock.stall_rounds`) nenhum gato for jogado ou morrer e nenhum Líder terminar com HP menor que no início da janela, o `core` resolve o impasse como hoje. Mantém "sem limite de turnos" (só dispara em estagnação real).
2. Limitar a cura do chefe (ex.: não cura no turno seguinte a um turno em que foi atacado; ou só cura se não foi ferido na rodada).
3. Aceitar: o jogador sempre pode jogar mais cartas; o caso é raro.

## Recomendação
Opção 1 (precisa de um número novo em `data/rules.json`, que é do agente de dados). Até o Renatho decidir, o `core` não mudou o gatilho de impasse.

Decidido pelo Renatho (2026-10-27): opção 1.
