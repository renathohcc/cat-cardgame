# GDD v0.1 — Chaoscats (card game roguelike de gatos)

Oct 26, 2026 · @Renatho

## Visão geral e pilares

É um card game roguelike em que você cria gatos de raças e status únicos, monta um time com eles e enfrenta duelos por turnos em busca do título de campeão mundial. Cada run termina, mas seus gatos e sua coleção ficam.

- **Gênero:** card game de duelo (Hearthstone simplificado) com estrutura de run (estilo Hades e Slay the Spire) e coleção com breed.
- **Plataforma:** PC e navegador, sempre pronto para um lançamento na Steam.
- **Escopo:** dev solo, sem cenários nem mapas ilustrados, pixel art reaproveitada por camadas.
- **Sessão:** run de 15 a 30 minutos.

**Pilares**

1. **Meu gato é único.** Cada gato nasce com IVs próprios (1 a 5 em ATK e HP), então apego e coleção são o coração do jogo.
2. **Turnos curtos e legíveis.** Poucas regras, poucos status (só ATK e HP) e keywords claras.
3. **Só mais uma run.** Toda run, mesmo derrotada, rende gatos para adotar e progresso permanente.
4. **Gato perfeito ajuda, mas não é obrigatório.** Dá para zerar o jogo com gatos medianos. Os perfeitos servem para recordes de tempo, runs mais fáceis, coleção e conquistas.

## Tema e história

Você é um criador de gatos de batalha tentando chegar a campeão mundial. A história é leve, serve de contexto e não é o foco do jogo.

- **Estrutura:** três ligas (regional, nacional, mundial), cada uma com um ato da run e um criador rival como chefe.
- **Rivais:** cada chefe tem personalidade e estilo de deck próprios, e comenta suas vitórias e derrotas entre as runs, em pequenos diálogos no estilo do Hades.
- **Tom:** leve e bem-humorado, com carinho pelos gatos.
- **Desdobramentos futuros:** campeonatos especiais, rivais recorrentes, raças lendárias ligadas a eventos da história.

## Combate

O duelo é 1x1, por turnos, e vence quem zerar o HP do Líder adversário. Os números abaixo são o ponto de partida e serão ajustados com simulação.

| Regra | Valor inicial |
| --- | --- |
| Líder | 20 HP, sem ataque. Elite 22 HP e chefe 25 HP (provisório) |
| Campo | 5 slots por lado |
| Mão | 4 cartas iniciais, compra 1 por turno, máximo 7 |
| Energia | 2 no primeiro turno, +1 por turno, teto 7, reinicia a cada turno. Exceção: quem começa o duelo tem só 1 de energia no seu primeiro turno (depois segue 3, 4, 5...) |
| Ataque | cada gato ataca 1 vez por turno, um gato inimigo ou o Líder |
| Dano | quem ataca e quem é atacado trocam dano (ATK contra HP), como no Hearthstone |
| Entrada em campo | o gato não ataca no turno em que entra, exceto com Investida |
| Quem começa | um dado decide no início do duelo. Quem começa compra normalmente, mas não pode atacar no seu primeiro turno |

Não existe DEF. Os status são só **ATK** e **HP**.

**Tipos de carta**

- **Gato:** custo, ATK, HP, raça e habilidade. Vem da sua coleção ou da run (Gato Especial).
- **Efeito:** gasta energia e some depois de usada (dano, cura, buff, compra de cartas). Só aparece no draft da run, nunca na coleção.

**Keywords iniciais**

- **Provocar:** enquanto estiver em campo, o adversário precisa derrotar esse gato antes de atacar o Líder. É a forma de proteger o Líder.
- **Investida:** pode atacar no turno em que entra.
- **Primeira Patada:** causa dano dobrado no primeiro ataque.
- **Robusto:** recupera 1 HP no fim de cada turno seu.

## Gatos, raças e IVs

Cada gato tem uma raça, que define custo, status base e habilidade, e dois IVs de 1 a 5 (ATK e HP) sorteados no nascimento e fixos para sempre. As raças são diferenciadas por poder, não por classe.

| Raça | Papel | Custo | ATK base | HP base | Habilidade |
| --- | --- | --- | --- | --- | --- |
| Vira-lata | Equilibrado, base do breed | 2 | 2 | 4 | Nenhuma |
| Siamês | Atacante | 3 | 3 | 3 | Investida |
| Persa | Defensor do Líder | 2 | 1 | 6 | Provocar |
| Sphynx | Canhão de vidro | 3 | 5 | 2 | Primeira Patada |
| Maine Coon | Tanque | 3 | 3 | 7 | Robusto |

**Como o IV entra na conta (proposta)**

```latex
ATK = ATK_{base} + \lfloor (IV_{ATK} - 1) / 2 \rfloor + N_{ATK} \qquad HP = HP_{base} + (IV_{HP} - 1) + N_{HP}
```

Com isso o ATK ganha de 0 a +2 e o HP de 0 a +4. Um gato 1/1 continua jogável, e um 5/5 é claramente melhor sem esconder a raça. O custo de energia é fixo por raça e não sofre variação.

- **Combinações:** 5 × 5 × 3 naturezas = 75 por raça. É pouco para se perder, mas o bastante para caçar o perfeito.
- **Exibição:** estrelas ou pontos no card, para o jogador ver o IV de relance.
- **Sorteio:** com pesos (IV 5 é raro, 2 e 3 são comuns), deslocados pela distância alcançada na run.

### Naturezas

Cada gato também nasce com uma natureza, sorteada junto com os IVs e fixa para sempre. Ela soma ou subtrai pontos de ATK e HP, e nenhum status fica abaixo de 1. Os valores são uma proposta inicial.

| Natureza | ATK | HP | Perfil |
| --- | --- | --- | --- |
| Calmo | 0 | +1 | Resistente, sem bônus de ataque |
| Bravo | +1 | −1 | Agressivo, mais frágil |
| Agitado | +2 | −2 | Extremo, alto risco e alto dano |

Com 25 combinações de IV e 3 naturezas, cada raça tem 75 variações possíveis.

### Sexo

Todo gato é macho ou fêmea, sorteado no nascimento com 50% de chance para cada. O sexo não altera os status e serve só para o breed, definindo quem pode cruzar com quem.

### Estágios de vida

Todo gato passa por dois estágios, o que reforça o apego. Só o breed gera filhotes, e os gatos encontrados nas runs sempre chegam adultos.

- **Filhote:** não pode entrar no deck. Vira adulto depois de algumas runs, no mesmo ritmo do tempo de breed (proposta: 2 runs como base).
- **Adulto:** único estágio que vai para o deck de 12 gatos e que pode cruzar.
- **Doação:** doar um filhote rende menos moedas que doar um adulto.
- **Status:** o filhote não precisa ter status de batalha, já que não luta. Os IVs, a natureza e o sexo já existem desde o nascimento e ficam visíveis no menu.

## Loop da run

Você entra na run com um deck pronto de gatos da sua coleção, e a run só adiciona ajuda temporária. Nada que você ganha na run substitui um gato criado por você.

1. **Montagem do deck:** deck fixo de 12 gatos adultos da coleção, cada um com seus IVs. Gatos em descanso de breed ficam indisponíveis.
2. **Mapa de nós:** uma árvore simples em UI, sem cenário, com batalha, elite, descanso, evento, loja, nó especial de gato e chefe. São 3 atos, um por liga.
3. **Draft após cada batalha:** escolha 1 entre 3 opções, que podem ser **Gato Especial** ou **carta de efeito**.
4. **Chefe do ato:** um criador rival, com deck e regra própria.
5. **Fim da run:** vitória ou derrota, e as recompensas são calculadas pela distância percorrida.

**Gatos Especiais (Espíritos Ancestrais)**

- Só existem durante a run e não podem ser obtidos na criação nem entram na coleção.
- Servem para dar variedade e ajudar a run, com habilidades mais fortes que as das raças comuns.
- Não têm IV: seus status são fixos.

**Cartas de efeito**

- Só aparecem no draft da run e somem no fim dela.
- Exemplos para o MVP: dano direto, cura, buff de ATK, compra de cartas, ganhar energia.
- **Lista do MVP (8):** Arranhão Certeiro (dano 3 em gato inimigo), Bote no Líder (dano 4 no Líder, ignora Provocar), Lambida Curativa (cura 3 em gato aliado), Soneca no Sol (cura 4 no seu Líder), Rugido de Guerra (+2 ATK até o fim do turno), Petisco Surpresa (compra 1), Farejar a Despensa (compra 2), Cochilo Revigorante (+2 de energia, respeitando o teto de 7).
- **Gatos Especiais do MVP (8):** Sombra Miúda, Velha dos Novelos, Soneca Ancestral, Trovão Amarelo, Guardião Bigodudo, Mestre das Garras, Pelo de Aço e Gata das Brasas. Usam só as quatro keywords existentes, e alguns têm um efeito ao entrar (se não houver alvo válido, o efeito se perde e o gato entra mesmo assim).

**Inimigos**

- Os adversários são criadores (pessoas), nunca gatos. Todos podem jogar gatos, Espíritos e cartas de efeito.
- **Chefe do MVP:** Madame Fifi Pelúcia, com Siamês e Sphynx de IV 5/5 e a regra própria **Banho de Espuma**: no início do turno dela, o Líder dela cura 1 HP (até o máximo).
- **Impasse:** se ninguém tem gato jogável nem em campo, ou se por 5 rodadas completas seguidas ninguém joga gato, nenhum gato morre e nenhum Líder perde HP, o duelo é decidido por um golpe de Líder com poder igual à média de ATK do deck inicial (com variação de −1 a +1, mínimo 1). Continua sem limite de turnos.

**Mini-run do MVP (fase 6)**

Recorte da run completa, para validar a diversão antes da meta-progressão.

- **Mapa:** 6 camadas com bifurcações. Todo nó de uma camada conecta a todos os nós da seguinte. Há batalha, elite, descanso e chefe; evento, loja e nó especial de gato ficam para depois. É um ato só.
- **Deck:** 12 gatos adultos sorteados a cada run (a coleção entra na fase 7). Os Espíritos e efeitos do draft entram no deck além dos 12, sem teto de tamanho.
- **Duelos:** cada duelo recomeça do zero (Líder cheio, mão nova). Não há vida persistente entre nós.
- **Recompensas:** batalha rende 1 entre 3 opções; elite rende 2 drafts seguidos de 1 entre 3 cada; descanso rende 1 entre 2. Em todos o sorteio vem de efeitos e Espíritos juntos. A elite e a batalha têm de valer o risco frente ao descanso.
- **Fim:** vencer o chefe encerra a run com vitória; perder, ou abandonar a run, encerra com derrota.

## Meta-progressão: adoção e breed

O progresso permanente vem de duas fontes: a adoção de gatos ao fim de cada run e o breed, que é o diferencial do jogo.

**Gatos encontrados (recompensa pós-run)**

- Gatos são encontrados durante a run (em nós especiais do mapa) e adotados ao fim dela. Todos chegam adultos. Só há duas formas de obter gatos, os nós especiais das runs e o breed, e não existe compra de gatos. Quanto mais longe a run chegou, mais gatos há para adotar e maior a chance de IVs altos e raças melhores.
- A tela de adoção é um momento de revelação, mostrando raça, sexo, natureza e IVs de cada gato encontrado.
- **Duplicatas ruins** podem ser doadas para adoção em troca de moedas.
- **Pity timer:** após N runs sem encontrar um gato de IV alto, a próxima garante um.

**Breed**

- Escolha um macho e uma fêmea da coleção para cruzar, da mesma raça ou de raças diferentes. Eles ficam **fora do deck** durante o período de breed.
- **Tempo de breed:** contado em runs concluídas (2 runs como base, e raças mais raras demoram mais), e não em tempo real, para funcionar bem no PC e na Steam.
- **Herança:** cada IV do filhote vem de um dos pais (50/50), com pequena chance de mutação de +1.
- **Raças novas:** cruzar duas raças pode gerar uma raça híbrida, seguindo uma tabela de receitas que o jogador descobre, no estilo de uma Pokédex.
- **Sem punição:** os pais não são consumidos, só ficam indisponíveis por um tempo.

* **Natureza:** a natureza do filhote é sorteada, e não herdada.
* **Item de natureza:** um item-chave, liberado por uma conquista específica, que não é consumido. Dado a um dos pais, faz toda a ninhada nascer com a natureza dele.
* **Sexo do filhote:** sorteado, 50% para cada.

- **Número de filhotes:** varia a cada cruzamento, como nos gatos reais.

**Gato perfeito é opcional**

O jogo deve ser concluído com gatos medianos. Os gatos de IV alto entram em:

- recordes de tempo por run e por liga;
- runs mais fáceis e seguras;
- coleção e conquistas (por exemplo, "Pokédex" de raças e gatos 5/5);
- dificuldades opcionais mais à frente, que escalam os inimigos para quem quer desafio.

## Criatório e economia

O hub é o Criatório: uma tela onde seus gatos vivem, animados, e de onde você gerencia a coleção. O gerenciamento é leve e serve ao apego, não a punir o jogador (proposta: sem fome nem penalidade por ficar ausente).

- **Quadro vivo:** um cercado com os gatos andando, dormindo e brincando, com sprites comuns e pacatos.
- **Sprite de batalha:** quando o gato vai para uma carta, ele aparece em uma pose de batalha, no estilo de um gato guerreiro, em contraste com o jeito pacato do criatório.
- **Menu de gatos:** lista com raça, sexo, natureza, IVs (estrelas) e status finais, com ordenação e filtro para achar os melhores e os piores.
- **Nomes:** você pode renomear qualquer gato para criar afinidade.
- **Moedas:** doar um gato para adoção rende moedas, e um filhote rende menos que um adulto.
- **Gastos:** ração, decoração do criatório.
- **Ração:** o efeito ainda precisa ser definido (por exemplo, melhorar a chance de IV alto ou acelerar o breed).

## Tecnologia

A base é Python puro com pygame, sem engine pronta, porque foi onde o desenvolvimento assistido por IA funcionou melhor.

- **Navegador:** pygbag (WebAssembly), para publicar no itch.io ou em hospedagem estática.
- **PC e Steam:** PyInstaller gera o executável, e o Steamworks entra depois, por uma biblioteca Python (a viabilidade e a manutenção dela precisam ser conferidas quando chegar a hora).
- **Arquitetura em camadas:** `core/` (regras, combate, IA, breed), `data/` (cartas, raças e inimigos em JSON) e `ui/` (pygame). O `core` não conhece a interface.
- **Conteúdo em dados:** raças, keywords, efeitos e inimigos ficam em JSON, para adicionar conteúdo sem mexer no código.
- **Testes e balanceamento:** como o combate roda sem interface, dá para simular milhares de duelos e checar se os IVs mantêm o jogo equilibrado.
- **Save:** arquivo JSON local com a coleção, os IVs, o estado do breed e o progresso das ligas.

## Direção de arte

O estilo é pixel art fofa, com poucos desenhos reaproveitados por camadas, para que cada gato pareça único sem exigir muita arte.

- **Resolução interna:** 960×540 (16:9), com arte nativa em 96×96 para gatos, Espíritos e efeitos, e ícones de 16×16. A tela escala de forma fracionária com letterbox e tem tela cheia (F11 ou Alt+Enter); funciona no Steam Deck.
- **Gato por camadas:** um corpo base por raça, com pelagem trocada por código (palette swap) e camadas de acessório e expressão.
- **Raridade visível:** pelagens raras, olhos diferentes e brilho para IVs altos, para o jogador perceber um bom gato de relance.
- **Cards (duelo):** carta limpa, só com nome, custo de energia, ATK e HP. As keywords viram badges pequenas com ícone, e natureza, sexo, IV e descrição aparecem em tooltip ao passar o mouse. Nas telas do hub (coleção, adoção, criatório) raça, sexo, natureza e IV (estrelas) ficam sempre visíveis.
- **Interface:** tabuleiro limpo, parecido em organização com um card game digital clássico, sem cenário complexo e sem quadrado ao redor de cada slot (tema noturno: pedra azul, prata e ouro pálido). Líder de cada lado com retrato próprio (o herói e os inimigos são pessoas) e HP em gema; o Líder não tem poder.
- **Fonte:** uma única fonte pixel em todo o jogo.
- **Ordem de produção:** retângulos e texto primeiro, para validar a diversão, e só depois a pixel art final.

Cada gato tem dois conjuntos de sprites: o do criatório (pacato, animado, de corpo inteiro) e o de batalha (pose de gato guerreiro, usado na carta). Os dois partilham a mesma pelagem e os mesmos acessórios por camadas.

## Plano de MVP

O MVP precisa responder uma pergunta: duelar com gatos de IVs diferentes e fazer uma run curta é divertido? Por isso a arte final fica por último.

| Fase | Entrega | Como validar |
| --- | --- | --- |
| 1. Motor de combate | Regras, 5 slots, energia, compra, keywords, tudo no terminal | Testes automáticos e duelos simulados |
| 2. IA inimiga | Inimigo que joga cartas e ataca com lógica simples | Joga um duelo inteiro sozinho |
| 3. Conteúdo mínimo | 5 raças, \~8 Gatos Especiais, \~8 efeitos, 3 inimigos, 1 chefe | Dá para ganhar e perder |
| 4. IVs | Sorteio de IV em ATK e HP, natureza, sexo e exibição | Simular 1.000 duelos e checar o impacto dos IVs |
| 5. Interface pygame | Mesa, mão, clicar ou arrastar, feedback de dano | Jogar de verdade |
| 6. Mini-run | Mapa de 6 a 8 nós, draft de 1 entre 3 e chefe | Uma run de cerca de 15 minutos |
| 7. Meta mínimo | Coleção, escolha do deck, adoção pós-run, breed simples, doação por moedas, renomear gatos e estágios de filhote e adulto | Dá vontade de fazer outra run? |
| 8. Pixel art | Sprites por camadas no lugar dos retângulos | Só depois de validar a diversão |

## Pontos em aberto

- [x] **Nome do jogo:** Chaoscats (definido pelo Renatho em 2026-10-28).
- [ ] **Provocar:** fica só no Persa ou outras raças também podem ter? Hoje só o Persa tem.
- [ ] **Sprites de batalha:** definir a referência visual do gato guerreiro pacato.
- [ ] **Naturezas:** valores exatos de Calmo, Bravo e Agitado.
- [ ] **Tempo de breed por raridade:** quantas runs cada raça exige.
- [ ] **Mutação no breed:** chance entre 5% e 10%, valor exato a testar.
- [ ] **Moedas e ração:** quantas moedas cada doação rende, preços de ração e decoração, e o efeito da ração.
- [x] **Lista de Gatos Especiais e efeitos:** primeiros 8 de cada definidos (ver Cartas de efeito).
- [ ] **Nomes e personalidades dos rivais:** um por liga. No MVP só existe a Madame Fifi Pelúcia (chefe) e três criadores comuns/elite.
- [ ] **Líder da elite e do chefe:** 22 e 25 HP são provisórios.
- [ ] **Dificuldades opcionais:** definir depois de validar o núcleo.

* [ ] **Item de natureza:** definir qual conquista o libera.
* [ ] **Ninhada do breed:** o número de filhotes varia a cada cruzamento, então falta definir a faixa (por exemplo, 1 a 4) e se depende da raça.
* [ ] **Sexo:** o sexo não altera status (decidido), falta definir só se há raças com proporção diferente de macho e fêmea.

- [ ] **Estágios de vida:** quantas runs até virar adulto, como é o sprite de filhote.

* [ ] **Nó especial de gato:** quantos aparecem por run, se o gato é mostrado antes de você decidir adotar e se há algum desafio para ganhá-lo.
