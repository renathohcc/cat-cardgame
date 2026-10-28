# Dificuldade dos inimigos da Liga 1 (T3.6b)

Pedido do Renatho (2026-10-27): chefe com Siamês e Sphynx IV 5/5 (já aplicado), elite "um pouco mais fraca", e medir os 4 inimigos de novo. Os números de design são do Renatho; aqui só há medição e sugestão. Nada em `data/` foi alterado: as variantes rodam em memória.

Como ler: o jogador usa dois tipos de deck sorteado (sem escolha de carta, então é pior que um jogador real).
- **Deck A**: 12 gatos sorteados.
- **Deck B ("médio")**: 6 gatos + 3 Espíritos + 3 efeitos sorteados.
Os dois lados usam a IA simples. 1000 duelos por linha, seed 1, jogador começando em metade. Margem de erro: cerca de ±3 pontos.

## 1. Estado atual (chefe já com IV 5/5)

| Inimigo | Deck A | Deck B | Meta sugerida |
| --- | --- | --- | --- |
| Tonho Sem-Sorte (batalha 1) | 82% | 85% | 80%+ |
| Irmãos Pimenta (batalha 2) | 50% | 57% | 55-60% |
| Berenice (elite) | 40% | 27% | 45-50% |
| Madame Fifi (chefe) | 24% | 9% | 40-45% |

Antes do IV 5/5 (T3.5, 200 duelos): chefe 52% (A) e 19,5% (B). Com o IV 5/5 o chefe passou a ser **mais difícil que a elite** (24% contra 40% no deck A; 9% contra 27% no B). Ou seja, a ordem de dificuldade (elite abaixo do chefe) já está certa. O problema agora é que **o chefe ficou duro demais** frente à meta, e a elite também está acima dela no deck B.

## 2. Variantes para enfraquecer a elite

Taxa de vitória do jogador contra a Berenice (base: 40% / 27%).

| Variante | O que muda | Deck A | Deck B |
| --- | --- | --- | --- |
| Líder 20 | Líder de 22 para 20 HP | 42% | 30% |
| Gata das Brasas fraca | Gata das Brasas (custo 5) vira Velha dos Novelos (custo 2) | 39% | 22% |
| Sem Farejar | remove Farejar a Despensa | 38% | 26% |
| Sem Mestre das Garras | remove o Mestre das Garras | 48% | 32% |
| Mestre por Velha | Mestre das Garras (custo 4) vira Velha dos Novelos (custo 2) | 45% | 32% |
| Maine Coon IV 2/3 | Maine Coon de 3/3 para 2/3 | 51% | 35% |
| Maine Coon IV 2/2 | Maine Coon de 3/3 para 2/2 | 56% | 38% |
| Líder 20 + Maine Coon 2/2 | os dois acima | 58% | 41% |
| IVs -1 em todos os gatos | tudo um ponto menor | 78% | 58% |

Leitura: Líder menor, Farejar e Gata das Brasas quase não mexem (a IA joga mal ou nem chega nelas). Os efeitos grandes vêm do **Mestre das Garras** e dos **IVs dos Maine Coon**. "IVs -1 em todos" é forte demais (a elite viraria quase uma batalha comum).

## 3. Pacotes

- **Pacote 1, leve:** Maine Coon da elite IV 2/3. Resultado 51% / 35%.
- **Pacote 2, médio (recomendado):** trocar Mestre das Garras por Velha dos Novelos. Resultado 45% / 32%. Mantém todos os gatos e o Líder 22; só tira um Espírito caro e forte.
- **Pacote 3, forte:** Líder 20 + Maine Coon IV 2/2. Resultado 58% / 41%. A elite fica no nível da batalha 2, o que talvez seja fraco demais.

**Recomendação:** pacote 2 (45% no deck A, dentro da meta 45-50%). Se o Renatho quiser ainda mais suave, pacote 1. O deck B continua abaixo da meta em todos os pacotes, mas o deck B é uma amostra sem seleção de cartas; um jogador real escolhe melhor.

## 4. O chefe com IV 5/5

- Fica **acima** da elite (mais difícil), antes e depois de qualquer pacote acima.
- Mas está longe da meta: 24% / 9%. Referências medidas só para informar: Siamês e Sphynx de volta a IV 4/4 dão 38% / 13%; Líder 25 para 22 dá 25% / 10% (quase nada). O peso do chefe vem dos IVs e da parede de Provocar com cura (inclusive o Banho de Espuma), não do Líder.
- Se o Renatho quiser o chefe em 40-45% no deck A, o IV 5/5 foi demais; algo entre 4/4 e 5/5 (um deles em 5, o outro em 4) é o caminho a testar. Não testei porque não foi pedido.

## 5. Dúvidas para o Renatho

1. Qual pacote da elite (1, 2 ou 3)?
2. Aceita o chefe bem abaixo da meta (24%), ou prefere reduzir os IVs dele? Os dados do chefe são do Renatho.
3. A meta deve valer para o deck A, para o B ou para uma média? Hoje elas divergem muito.

Como reproduzir: `python -m sim.inimigos --duelos 1000 --seed 1` (base) e `python -m sim.inimigos --duelos 1000 --seed 1 --variante e-mestre-por-velha` (`--lista` mostra todas).

Decidido pelo Renatho (2026-10-27): elite = pacote médio; chefe aceito em 5/5
