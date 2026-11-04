# Especificação da Fase 10a: economia, gatil e quintal em expansão

2026-11-03 · orquestrador. Parte da proposta `2026-10-31-meta-progressao-e-economia.md`, com as **decisões do Renatho de 2026-11-03**: (1) limite do gatil aprovado; (2) cercado mostra no máximo **16 gatos com rotação**, e o jogador **desbloqueia mais mapa aos poucos**; (3) Prestígio aprovado; (4) as três rações aprovadas. Os números são ponto de partida, calibrados depois por simulação. Itens marcados **[decidir]** são do Renatho. Nada aqui altera o GDD até a permissão expressa dele.

## 1. Ideia central: o quintal cresce

As vagas e o mapa viram **um mecanismo só**. O quintal nasce parcial e cada **área** é comprada com moedas (e, em algumas, exige Prestígio). Comprar uma área:
- tira a camada de bloqueio (mato alto, tapume com placa de preço) com uma animação curta e um som;
- dá **+2 vagas** no gatil;
- abre algo novo (casal paralelo, cercadinho, decoração, lagoa).

Isso substitui a lista de "6 compras de vaga" da proposta anterior: **as 6 expansões de vaga passam a ser 6 áreas do mapa**. O progresso fica visível no hub, que é onde o jogador passa o tempo.

Cada área já existe na arte do quintal (`assets/pen/`). A camada de bloqueio é um overlay por script ou Pixellab, de custo baixo e sem redesenhar nada.

### Áreas (primeira versão, nomes e ordem para o Renatho ajustar)

| # | Área | Preço | Prestígio | Efeito |
| --- | --- | --- | --- | --- |
| início | Cercado dos adultos (parte baixa) + patinho do 1º casal + cesta dos filhotes | grátis | 0 | 18 vagas, 1 casal |
| 1 | Cercado dos adultos ampliado (cerca recua) | 15 | 1 | +2 vagas |
| 2 | Cercadinho de filhotes (cerca branca, bolinha, túnel) | 25 | 1 | +2 vagas, filhotes saem da cesta |
| 3 | Pátio de casais ampliado | 40 | 2 | +2 vagas, **casal nº 2** |
| 4 | Jardim e lagoa | 60 | 3 | +2 vagas, decoração do conjunto "Jardim" |
| 5 | Pátio de casais nobre | 85 | 4 | +2 vagas, **casal nº 3** |
| 6 | Pomar e árvore grande | 115 | 5 | +2 vagas, decoração rara |

Total: 18 → 30 vagas, e o quintal inteiro aberto no fim. **[decidir]** a ordem das áreas e se o primeiro casal já abre no início (recomendado, é o gancho do breed).

### Prestígio (aprovado)

Níveis 1 a 5, sem gastar. Marcos da proposta: início = 1; vencer a liga 1 = 2; 5 raças diferentes na coleção = 3; enquanto não existem ligas 2 e 3, os níveis 4 e 5 vêm de Pressão 3 e Pressão 6 (a Pressão é da 10b, então **na 10a os níveis 4 e 5 ficam travados** e as áreas 5 e 6 só abrem na 10b). Mostrar o nível na placa do portão e uma barra "próximo nível".

## 2. Economia (fontes e gastos na 10a)

**Fontes novas**, somando à doação existente: nó de batalha vencido +1, elite +3, chefe +6, primeira vitória da liga 1 +20 (uma vez). Estimativa: run mediana ~5 a 8 moedas, vitória ~15 a 20.

**Gastos da 10a:** áreas do quintal (§1), decoração, ração (§4). A tela de loja do hub mostra saldo, o que está à venda, o preço e o que falta.

**Barra de próxima meta** na tela de fim de run: "faltam X moedas para [próximo item acessível]". Mostra sempre o item mais barato ainda não comprado e liberado pelo Prestígio.

## 3. Limite do gatil (decidido)

- Vagas iniciais **18**; máximo **30** (por áreas).
- Filhotes, gatos em breed e o deck ocupam vaga.
- **Adoção com gatil cheio:** a tela pede doar um gato da coleção (escolhendo qual) para abrir espaço, ou doar o gato novo. Nunca há perda automática.
- **Nascimento com gatil cheio:** os filhotes nascem mesmo assim (o gatil pode passar do limite) e só ficam bloqueadas a adoção e a abertura de novo breed até voltar ao limite.
- Doar continua respeitando `min_adults_after_breed`/`deck_size` (12 adultos disponíveis) como hoje.
- **Mudança de regra:** substitui o registro de 2026-10-28 "sem limite de coleção por enquanto". A regra mínima 12 + 2 + 3 = 17 é verificada por teste.
- O **cercado visível continua em 16 gatos com rotação** (decisão do Renatho), independente do limite do gatil. A placa do portão mostra "ocupadas/vagas" (ex.: 14/18).

## 4. Ração (aprovada, uma por casal)

| Ração | Efeito | Preço |
| --- | --- | --- |
| Ração Fofa | mutação de 7% para 15% naquela ninhada | 12 |
| Ração Veloz | o breed termina 1 run antes (mínimo 1 run) | 15 |
| Ração Escolha | o jogador fixa 1 IV (ATK ou HP) de um dos pais, herdado por toda a ninhada | 30 |

- Compra no hub. O estoque fica no save. **Uma ração por casal**, escolhida ao iniciar o breed (na tela do breed, junto da **prévia de odds**).
- Ração Escolha exige Prestígio 3; a Veloz, 2; a Fofa, 1 (da tabela da proposta).
- Item de natureza (conquista) fica para a 10c.

## 5. Breed: prévia de odds e histórico

- **Prévia de odds** na tela do breed: chance da raça (60/40), de cada IV (50/50, mutação 7% ou 15% com a Fofa), faixa da ninhada (1 a 3) e o efeito da ração escolhida.
- **Linhagem e histórico** (só contadores no save e na ficha): geração (G1 para adotados, pai/mãe + 1), nome dos pais, runs jogadas, duelos vencidos, chefes derrotados. Títulos/coleiras ficam para depois.

## 6. Decoração (catálogo mínimo da 10a)

- Cosmética, em **âncoras fixas** do quintal (nada de editor livre).
- Catálogo inicial reaproveita objetos já desenhados: 6 a 10 peças, preços 10 a 60, ligadas às áreas (ex.: "Jardim" só depois da área 4).
- O gato interage com a peça (arranhador, cama, lagoa), usando as animações que já existem.
- Conjuntos completos viram conquista na 10b/10c.

## 7. O que muda nos contratos (para o Renatho aprovar)

`docs/CONTRATOS.md` e o save (versão sobe, com migração do save antigo):
- carteira (`coins` já existe), `prestige`, `areas_unlocked`, `rations` (estoque), `decorations_owned` e posicionadas;
- por gato: `generation`, `parents`, contadores de histórico;
- breed: `ration` aplicada no casal;
- regras novas em `data/rules.json`: capacidade, fontes de moeda, Prestígio; catálogo em `data/shop.json` (áreas, rações, decoração) com schema.

## 8. Tarefas

| ID | Tarefa | Agente | Depende de |
| --- | --- | --- | --- |
| T13.0 | Dados: `shop.json` (áreas, rações, decorações), regras de economia e Prestígio, schemas, validação | Dados | aprovação desta spec |
| T13.1 | Core: carteira, fontes de moeda, Prestígio, vagas por áreas, compra, adoção/nascimento com gatil cheio, ração no breed, prévia de odds, histórico/linhagem, save v+1 com migração | Core | T13.0 |
| T13.2 | Testes do core (limite 12+2+3, gatil cheio, ração, migração de save, odds = sorteio real por simulação) e **simulador de economia** (`sim/economia.py`: runs até cada área) | Testes | T13.1 |
| T13.3 | Arte: camada de bloqueio (mato, tapume, placa de preço), animação de desbloqueio, ícones de moeda/Prestígio/ração/decoração | Arte | T13.0 |
| T13.4 | UI: loja do hub, placa do portão (vagas e Prestígio), desbloqueio de área, adoção com gatil cheio, ração e prévia de odds no breed, ficha com histórico, barra de próxima meta no fim da run | Interface | T13.1, T13.3 |
| T13.5 | Testes de UI e fluxos reais | Testes | T13.4 |
| T13.6 | Revisão e portão (commit) | Revisor | todas |

T13.0 e T13.3 podem rodar em paralelo (pastas diferentes), depois T13.1, e a UI por último.

## Decisões para o Renatho

1. A tabela de **áreas** (ordem, preços, efeitos).
2. Primeiro casal aberto desde o início, e filhotes na **cesta** até a área 2.
3. Níveis 4 e 5 do Prestígio ficam **travados na 10a** (as áreas 5 e 6 só abrem na 10b).
4. Autoriza atualizar o **GDD** (limite do gatil, áreas, Prestígio, ração) e o **CONTRATOS** quando a 10a fechar.
