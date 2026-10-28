# Proposta: desempate por impasse (duelo travado)

**Regra pedida pelo Renatho (2026-10-27):** se os dois jogadores ficarem sem cartas e sem ataque possível, rola-se um poder de ataque para cada Líder, baseado na média de ataque do deck de cada um, e os Líderes se atacam para encerrar a partida.

## O que ficou em aberto

1. **Gatilho exato.** Proposta: impasse quando, nos dois lados, a mão está vazia, o deck está vazio, e nenhum gato pode atacar (campos vazios ou nada atacável). Basta isso para travar o duelo por completo?
2. **"Rolar um poder baseado na média".** Qual o sorteio? Opções:
   - A) poder = média de ATK do deck arredondada, sem aleatoriedade (então "rolar" não existe);
   - B) poder = média ± variação sorteada (ex.: média + d3 − 2);
   - C) poder = sorteio entre 1 e a média de ATK.
3. **Média de quê.** ATK final dos 12 gatos do deck inicial, ou só dos gatos que ainda estão vivos? Gatos de efeito (sem ATK) ficam fora?
4. **Quantas rodadas.** Os Líderes se atacam uma vez (simultâneo) ou repetem até um chegar a 0 HP? Se os dois zerarem juntos, ou ficarem empatados em HP, quem vence?
5. **Dano entre Líderes.** O dano rolado é aplicado direto no HP do Líder adversário (20 HP), sem troca de dano?

## Recomendação

Gatilho do item 1 como proposto. Opção B no item 2, média do ATK final de todo o deck inicial (item 3), rodadas simultâneas repetidas até um Líder chegar a 0 HP (item 4) e, em empate total, vence quem tiver mais HP restante e, persistindo, um novo dado (item 4). Dano direto no item 5.

Sem a sua resposta, o `core` implementa só a detecção de impasse (evento `Deadlock`) e **não** resolve o desempate.

## Respostas do Renatho (2026-10-27)

1. **Gatilho:** os dois lados sem cartas jogáveis (mão e deck vazios) e sem nenhum gato em campo que possa causar dano de alguma forma. Decidido.
2. **Rolagem:** o Renatho não entendeu a pergunta. **Em aberto**, reexplicada no chat.
3. **Média:** ATK final do deck inicial inteiro. Decidido.
4. **Rodadas:** os Líderes se atacam um por vez, alternando, repetindo até um chegar a 0 HP. Quem tiver menos HP no momento do impasse ataca primeiro. Decidido. **Falta:** se os dois tiverem o mesmo HP, quem ataca primeiro (sugestão: o dado do duelo).
5. **Dano:** direto no HP do Líder adversário. Decidido.

## Fechamento (2026-10-27)

2. **Rolagem:** opção B. A cada ataque, o Líder causa a média de ATK do deck inicial (arredondada) mais uma variação sorteada (valor inicial: −1, 0 ou +1, ajustável por simulação). Decidido.
4. **Empate de HP:** o dado do duelo decide quem ataca primeiro. Decidido.

**Status: resolvida.** Implementação no `core`: ver `docs/CONTRATOS.md` §1.4 (`deadlock`) e §2.3.

**Confirmação final (2026-10-27):** em HP igual, o desempate sorteia de novo (não reaproveita o dado inicial).
