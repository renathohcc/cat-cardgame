# Proposta: meta-progressão, economia e breed (Fase 10)

2026-10-31 · orquestrador, a partir da conversa com o Renatho. **Ideias aprovadas em princípio pelo Renatho**; os números são ponto de partida e as decisões marcadas com **[decidir]** são dele. Nada aqui altera o GDD até a aprovação expressa.

## Problema

O núcleo (duelo e run) está sólido, mas o meta-loop está aberto: nada que o jogador ganha vira uma decisão interessante depois.

| Sistema | Hoje |
| --- | --- |
| Moedas | Só têm fonte (doação), sem nenhum gasto |
| Coleção | Sem limite: adotar tudo é sempre a melhor escolha, e doar quase nunca é decisão |
| Breed | Passivo: escolher o casal, esperar 2 runs, receber |
| Criatório | Bonito, mas só decorativo, sem feedback de progresso |
| Run | 1 ato só; depois de vencer, o único motivo para repetir é caçar IV |

## Princípios

1. **Todo recurso tem fonte, gasto e uma meta visível.** O jogador sempre sabe o que vem a seguir e quanto falta.
2. **Escassez cria decisão.** Limite de espaço faz adotar e doar virar escolha.
3. **Progressão horizontal, não vertical.** Desbloquear opções, variedade e cosmético, não poder bruto. Isso protege o pilar 4 (gato perfeito é opcional).
4. **Breed nunca é trancado; a quantidade é.** O breed é o diferencial e o gancho, então aparece cedo.
5. **Nunca punir.** Nenhum gato é perdido à força e não existe penalidade por ausência.

## 1. Economia de moedas

### Fontes (hoje só existe a doação)

| Fonte | Valor inicial |
| --- | --- |
| Doação (já existe) | 1 a 5 pela soma de IVs, filhote metade |
| Nó de batalha vencido | +1 |
| Elite vencida | +3 |
| Chefe vencido | +6 |
| Primeira vitória em cada liga | +20 (uma vez) |
| Meta da run cumprida (ver §4) | +5 |
| Conquista | 5 a 30, conforme a dificuldade |
| Pressão (ver §4) | +10% de moedas por nível |

Estimativa: uma run mediana (3 a 4 nós) rende ~5 a 8 moedas, uma vitória ~15 a 20, mais as doações. Alvo de ritmo: **um desbloqueio relevante a cada 1 ou 2 runs no começo, espaçando até a cada 4 ou 6 runs** depois de ~15 runs. A calibragem final sai de um simulador de economia (T10a.x, agente testes).

### Gastos

| Gasto | Preço inicial | Observação |
| --- | --- | --- |
| Vaga no gatil (+2 vagas) | 15, 25, 40, 60, 85, 115 | 6 compras, de 18 para 30 vagas |
| Casal paralelo nº 2 | 40 | exige Prestígio 2 |
| Casal paralelo nº 3 | 90 | exige Prestígio 3 |
| Decoração | 10 a 60 | cosmética, ver §2 |
| Ração (consumível) | 12 a 30 | ver §3 |
| Reroll do draft na run | não | fica para a moeda da run (§4) |

## 2. Criatório como progressão

### Capacidade do gatil

- O gatil passa a ter **limite de vagas**. Filhotes, gatos em breed e o deck ocupam vaga. **[decidir: isso substitui a decisão da 5b "sem limite de coleção por enquanto"]**
- **Vagas iniciais: 18.** Regra de segurança: as vagas iniciais têm de ser ≥ 12 (deck) + 2 (casal) + 3 (ninhada máxima) = 17, senão o breed trava.
- **Gatil cheio na adoção:** a tela pede doar um gato da coleção para abrir espaço ou recusar (doar) o gato novo. Nunca há perda automática.
- **Gatil cheio no nascimento:** os filhotes nascem mesmo assim (o gatil fica acima do limite) e o jogador só não adota nem inicia breed até voltar ao limite. Assim o breed nunca é punido.
- **Visual:** o cercado mostra as vagas ocupadas e as livres (por exemplo, "14/18" na placa do portão). Expandir o gatil **muda o quintal**: a cerca recua, aparece grama nova. O progresso fica visível. **[decidir: o cercado hoje desenha no máximo 16 gatos (`pen_max_cats`). Opção A: subir o limite visual com o gatil. Opção B: manter 16 visíveis e rotacionar o resto, como hoje. Recomendação: A até ~24, B acima disso]**

### Casais paralelos

- O **primeiro casal é liberado desde o início** (ou logo após a 1ª run, como tutorial, ver a proposta de polimento).
- O 2º e o 3º casal são comprados e usam os espaços que a zona de casais já tem (camas do quintal).

### Prestígio do gatil (segundo eixo, não gastável)

Evita o "juntei moedas e comprei tudo no primeiro dia" e dá ritmo. Níveis 1 a 5, subindo por marcos:

| Nível | Marco (sugestão) | Libera para compra |
| --- | --- | --- |
| 1 | início | vagas 1 e 2, decoração básica, Ração Fofa |
| 2 | vencer a liga 1 | casal nº 2, vagas 3 e 4, Ração Veloz |
| 3 | 5 raças diferentes na coleção | casal nº 3, Ração Escolha, decoração do conjunto 2 |
| 4 | vencer a liga 2 | vagas 5 e 6, decoração rara |
| 5 | vencer a liga 3 | decoração de campeão, Pressão máxima |

Enquanto as ligas 2 e 3 não existirem, os marcos 4 e 5 trocam por "Pressão 3" e "Pressão 6".

### Decoração

- **Cosmética, com uma função leve:** cada peça muda o comportamento dos gatos (o arranhador tem animação de arranhar, a cama tem gato dormindo, a lagoa tem gato olhando peixe). A peça dá vida ao quintal, não poder.
- **Conjuntos** (por exemplo, "Jardim Zen", "Festa Junina", "Castelo") dão conquista ao serem completados.
- **Posições fixas** (âncoras do quintal). Nada de editor livre: é mais barato e não quebra o layout em grade de 16 px.
- O catálogo inicial reaproveita a arte do quintal que já existe.

## 3. Breed com decisão

### Ração (resolve o ponto em aberto do GDD)

Consumível, um por casal, aplicado ao iniciar o breed. Preços altos de propósito, para não piorar o achado M2 da 5c (gato perfeito fácil demais por breed).

| Ração | Efeito | Preço |
| --- | --- | --- |
| Ração Fofa | mutação de 7% para 15% naquela ninhada | 12 |
| Ração Veloz | breed termina 1 run antes (mínimo 1 run) | 15 |
| Ração Escolha | o jogador fixa 1 IV (ATK ou HP) de um dos pais, herdado por toda a ninhada | 30 |

- **Item de natureza** (já no GDD): item-chave não consumido, liberado por conquista. Sugestão de conquista: "criar 3 gatos com a mesma natureza dos dois pais".
- **[decidir]** se mais de uma ração pode ser usada no mesmo casal. Recomendação: **uma só**, para manter a escolha.

### Prévia de odds

Ao escolher o casal, a tela mostra as chances: raça (60/40), cada IV (50/50 + mutação), faixa da ninhada (1 a 3) e o efeito da ração escolhida. Planejar é metade da diversão do breed.

### Cerimônia de nascimento

O nascimento vira um momento, igual ou maior que a adoção: cesta que balança, filhotes revelados um por um, brilho e som graduados pela qualidade (IV, mutação, shiny). Detalhe na proposta de polimento.

### Pelagem rara (shiny)

- Chance fixa de **1 em 50** por gato (adoção e breed), **independente de IV**, só cosmética: paleta alternativa por raça e um brilho leve.
- Breed de dois pais shiny: chance sobe para 1 em 10. **[decidir]**
- Dá uma caçada paralela barata que reforça o pilar 1 (meu gato é único). Custo de arte: 1 paleta extra por raça (palette swap já existe no pipeline).

### Raças híbridas e Pokédex

- Volta a tabela de receitas do GDD (cortada na 5c): certos cruzamentos de raças diferentes têm uma chance (sugestão 15%) de gerar uma raça híbrida.
- **Pokédex de raças** no menu: raças descobertas, silhuetas das que faltam e dicas vagas ("dizem que um gato de pelo longo com um gato sem pelo...").
- Cada híbrida é uma raça nova em `breeds.json` (custo, status, habilidade, só keywords existentes no começo).
- Custo real: arte (batalha 96 px + sprites de quintal + filhote por raça) e balanceamento. **Recomendação: começar com 3 híbridas** e medir.
- Exemplos de partida (nomes e números para o Renatho ajustar): Himalaio (Siamês × Persa), Bengal (Siamês × Maine Coon), Peterbald (Sphynx × Vira-lata).

### Linhagem e histórico do gato

- A ficha do gato ganha: geração (G1 para adotados, pai/mãe +1), nomes dos pais, runs jogadas, duelos vencidos, chefes derrotados.
- **Títulos e coleiras cosméticas** por marco ("Veterano" com 10 runs, coleira de campeão ao vencer uma liga no deck). Ligam a run à identidade do gato e dão motivo para jogar com os mesmos gatos.
- Custo baixo: só contadores no save e UI da ficha.

## 4. Repetição da run

- **Ligas 2 e 3** (já no GDD), cada uma com rival próprio e **diálogos curtos entre runs** no estilo do Hades: o rival comenta a última vitória ou derrota. É texto barato com retorno alto em personalidade.
- **Pressão** (dificuldade escalonável, estilo Heat do Hades e Ascensão do Slay the Spire): cada vitória libera o próximo nível, que acrescenta um modificador acumulativo (por exemplo, "inimigos +1 HP no Líder", "1 opção a menos no draft", "chefe com 2 regras próprias"). Recompensa: +10% de moedas e +1 ponto de deslocamento de IV na adoção por nível. **É aqui que o gato perfeito passa a ter função real**, sem ser obrigatório para zerar.
- **Nó de gato visível no mapa** (resolve o ponto em aberto do GDD): o nó mostra a raça e o sexo do gato, mas não os IVs. Vencer o duelo do nó garante esse gato na adoção. Sugestão: 1 por ato. Vira decisão de rota.
- **Meta da run:** um objetivo opcional sorteado a cada run ("vença sem perder nenhum gato em campo", "vença o chefe com 3 raças diferentes"). Cumprir rende moedas e +1 gato na adoção.
- **Loja e evento** (previstos no GDD): a loja usa uma **moeda da run (Petiscos)**, que se perde no fim, separada das moedas permanentes. Vende efeitos, Espíritos, remoção de carta e reroll do draft. Nunca vende gatos.
- **Conquistas com recompensa** (moedas, decoração, títulos), e base para as conquistas da Steam.

## 5. Ordem de produção recomendada

| Etapa | Conteúdo | Custo principal |
| --- | --- | --- |
| **10a Economia e gatil** | moedas por nó, vagas e expansão, casais paralelos, Prestígio, loja de decoração e ração, prévia de odds, histórico e linhagem, barra de próximo desbloqueio | core, UI e dados; pouca arte |
| **10b Repetição da run** | Pressão, nó de gato, meta da run, conquistas, liga 2 com rival e diálogos | conteúdo e balanceamento; retratos de rival |
| **10c Profundidade do breed** | shiny, 3 híbridas e Pokédex, item de natureza, loja da run e evento, liga 3 | arte das raças novas |

Cada etapa com portão e commit, como na Fase 5.

## Decisões para o Renatho

1. Confirmar o **limite do gatil** (vagas iniciais 18, máximo 30) no lugar de "sem limite".
2. Limite visual do cercado: opção A (subir com o gatil) ou B (16 visíveis com rotação).
3. **Prestígio** com os marcos da tabela, ou outros marcos.
4. Rações: os 3 tipos e preços; uma por casal.
5. Shiny: 1 em 50, e 1 em 10 com os dois pais shiny.
6. Híbridas: as 3 primeiras raças, nomes e status.
7. Nó de gato: 1 por ato, mostra raça e sexo.
8. Ordem 10a → 10b → 10c.
