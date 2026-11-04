# Proposta: calibração da economia da 10a (precos e ganhos)

2026-11-03 · agente de testes (T13.2). **Proposta, não alterei `data/`.** Os números são do Renatho. Base: `reports/T13.2-economia-sim.md` (50 carreiras x 200 runs, seed 1, IA nos duelos, mapa e draft aleatórios) e what-ifs em memória com `python -m sim.economia --precos-areas ... --moedas-no ...` (30 carreiras x 80 runs, política `area`).

## Problema

A meta da especificação (§2) é "um desbloqueio relevante a cada 1 ou 2 runs no começo, espaçando até ~4 a 6 runs depois de ~15 runs". Com os números atuais:

| Janela de runs | Meta | Medido (área ou Prestígio) | Medido (+ decorações) |
| --- | --- | --- | --- |
| 1 a 5 | 1 a 2 runs por evento | 8,9 runs por evento (6% das runs têm evento) | 8,9 |
| 6 a 10 | 1 a 2 | 2,6 | 2,6 |
| 11 a 15 | 2 a 4 | 2,7 | 2,0 |
| 16 a 25 | 4 a 6 | 6,9 | 1,8 |
| 26 a 50 | 4 a 6 | 113 (quase nada) | 7,7 |
| depois de 50 | 4 a 6 | nada | nada |

Marcos (mediana de runs): área 1 na run 7, área 2 na 10,5, área 3 na 13,5, área 4 na 18,5. Última compra de área ou decoração na run 35,5. As áreas 5 e 6 (Prestígio 4 e 5, travados na 10a) ficam presas a partir da run ~18.

## O que a simulação mostra

1. **Começo lento.** Nas primeiras 5 runs entram ~1 a 3 moedas por run (nós) e a doação só rende quando o gatil enche (por volta da run 3). A área 1 (15) chega na run 7.
2. **Áreas 3 e 4 dependem do Prestígio 2, não do preço.** O Prestígio 2 (vencer a liga 1) sai na mediana da run 11,5 (p90: 23). Baixar preços praticamente não move as áreas 3 e 4 (tabela abaixo).
3. **Zona morta depois da área 4.** Tudo que é permanente na 10a custa 140 (áreas 1 a 4) + 182 (8 decorações liberadas) = 322 moedas, e a entrada média é ~17,6 por run. Por volta da run 35 não sobra desbloqueio permanente; só ração (consumo). Isso é esperado até a 10b liberar as áreas 5 e 6, mas o jogador de 15+ runs fica sem meta.
4. **A doação é a maior fonte de moedas** (10,8 de 17,6 por run, ~60%), porque o gatil enche em ~83% das runs e o jogador doa o mais fraco. Os nós pagam 6,8 por run em média (vitória estável ~10,5; derrota ~2,2). A estimativa da spec ("vitória 15 a 20") só aparece contando a doação (vitória: mediana de entrada total 26).
5. **O marco "5 raças" do Prestígio 3 é trivial.** O jogo tem 5 raças e a coleção inicial de 12 gatos já chega a 5 raças na run 1 (mediana). O Prestígio 3 sai junto do 2.
6. **A ração é barata em relação à entrada:** Fofa 12 = 0,7 run média (1,1 vitória estável); Veloz 15 = 0,9 (1,4); Escolha 30 = 1,7 (2,9). Com estoque vazio o jogador simulado compra 0,64 ração por run (sumidouro grande).

## What-ifs (política `area`, mediana de runs até a compra)

| Cenário (preços das áreas 1 a 4; ganho por nó batalha/elite/chefe) | Área 1 | Área 2 | Área 3 | Área 4 |
| --- | --- | --- | --- | --- |
| Atual: 15/25/40/60; 1/3/6 | 7 | 12 | 15 | 20 |
| 8/16/30/50; 1/3/6 | 5 | 9 | 14 | 20 |
| 6/12/24/40; 1/3/6 | 4 | 8 | 14,5 | 17,5 |
| 15/25/40/60; 2/4/8 (nós dobrados) | 5 | 9 | 14 | 19 |
| 10/20/35/55; 2/4/8 | 3 | 8 | 15 | 18,5 |

Nenhum cenário muda de forma relevante as áreas 3 e 4 (Prestígio 2 na mediana da run ~14) nem a janela das runs 1 a 5 (fica em 5 a 7 runs por evento).

## Opções

- **A. Acelerar o começo:** área 1 de 15 para ~8 a 10, ou moedas iniciais (por exemplo 10), ou bônus pequeno na primeira run. Meta: primeira compra na run 2 ou 3.
- **B. Soltar o gargalo do Prestígio 2:** baixar o requisito da área 3 para Prestígio 1, ou tornar o marco do Prestígio 2 mais cedo (por exemplo, derrotar o primeiro elite) e deixar "vencer a liga 1" para o 3. Hoje a área 3 espera uma vitória que a IA só consegue na run ~12 (um humano deve chegar antes; vale conferir em playtest).
- **C. Reduzir o marco "5 raças":** por exemplo 5 raças com pelo menos um gato IV 4+ de cada, ou 3 gatos de cada de 3 raças, para não coincidir com o Prestígio 2.
- **D. Preencher a zona morta (runs 20 a 50):** mais decorações (6 a 10 peças a 20 a 60 moedas), um item de natureza antecipado da 10c, ou antecipar o Prestígio 4 (Pressão) para a 10a.
- **E. Decidir o papel da doação:** se a ideia é a doação ser a fonte principal, está certo; se os nós deveriam pesar mais, dobrar para 2/4/8 leva a vitória estável a ~20 moedas de nós (e a janela 6 a 10 em ~2,5 runs por evento).

## Recomendação

A (área 1 por volta de 8 e nós 2/4/8 se quiser run mediana 5 a 8) + B (área 3 em Prestígio 1 ou marco do P2 mais fácil) + C. D e E ficam como decisão de design da 10b. Esses ajustes juntos deveriam levar a janela das runs 1 a 5 para ~2 a 3 runs por evento. Depois de aplicados, rodar de novo `python -m sim.economia --runs 200 --seed 1` e comparar.

## Limites da simulação

- O jogador é a IA de duelo com mapa e draft aleatórios (ou "elite" com `--mapa elite`, arquivo `reports/T13.2-economia-sim-elite.md`). Um humano deve vencer mais, o que adianta o Prestígio 2 e as moedas por run (limite superior de uma vitória: 12 moedas de nós).
- A taxa de vitória sai diferente entre políticas (54% com `area`, 38% com `barato`) porque comprar áreas mais cedo libera casais e breed antes; isso é efeito do jogador simulado, não calibração.
- O jogador usa só a Ração Fofa (a mais barata); Veloz e Escolha entram só como custo na tabela.
