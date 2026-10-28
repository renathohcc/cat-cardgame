# Proposta: conteúdo da Fase 3 (efeitos, Espíritos, inimigos e chefe)

Autor: agente de dados (T3.0). **Tudo aqui é sugestão inicial para o Renatho ajustar.** Nada foi criado em `data/` nem no GDD.
Régua usada: raças comuns (custo 2: Vira-lata 2/4, Persa 1/6; custo 3: Siamês 4/3, Sphynx 5/2, Maine Coon 3/7), energia com teto 7.
Convenção de ids: mantive `kebab-case` (como já está em `breeds.json` e no contrato). Se preferir `snake_case`, é só avisar.

## 1. Efeitos (8)

Todos têm custo >= 1 e somem depois de usados. Buff de ATK dura só até o fim do turno (`duracao: "turno"`).

| id | Nome | Custo | Ação | Alvo | Texto |
| --- | --- | --- | --- | --- | --- |
| arranhao-certeiro | Arranhão Certeiro | 2 | dano 3 | gato inimigo à escolha | "Um arranhão bem dado. Ai." |
| bote-no-lider | Bote no Líder | 3 | dano 4 | Líder inimigo | "Ignora Provocar: o bote vai direto ao dono." |
| lambida-curativa | Lambida Curativa | 1 | cura 3 | gato aliado à escolha | "Limpinho e reconfortado." |
| soneca-no-sol | Soneca no Sol | 2 | cura 4 | seu Líder | "Nada cura como um raio de sol." |
| rugido-de-guerra | Rugido de Guerra | 1 | buff ATK +2 (só neste turno) | gato aliado à escolha | "Miau com muita convicção." |
| petisco-surpresa | Petisco Surpresa | 1 | comprar 1 | nenhum | "Achou um petisco no bolso. E uma carta." |
| farejar-a-despensa | Farejar a Despensa | 2 | comprar 2 | nenhum | "Cheira daqui, cheira de lá, e olha o que apareceu." |
| cochilo-revigorante | Cochilo Revigorante | 1 | energia +2 | nenhum | "Um cochilo rápido rende mais que parece." (lucro líquido de 1 energia) |

Observação: "Bote no Líder" é a única forma de furar Provocar. Por isso custa 3 e causa só 4.

## 2. Espíritos Ancestrais (8)

Sem IV, status fixos, só as 4 keywords existentes. "Ao entrar" usa o mesmo formato de ação dos efeitos. Cada um sai um pouco acima da média de uma raça comum de mesmo custo (a média de um gato comum fica perto de +1 ATK e +1,6 HP sobre a base).

| id | Nome | Custo | ATK/HP | Keywords | Ao entrar | Papel |
| --- | --- | --- | --- | --- | --- | --- |
| sombra-miuda | Sombra Miúda | 1 | 2/2 | Investida | nada | Abertura barata e rápida |
| velha-dos-novelos | Velha dos Novelos | 2 | 2/4 | nenhuma | comprar 1 | Reposição de cartas |
| soneca-ancestral | Soneca Ancestral | 2 | 1/5 | Robusto | energia +1 (custo líquido 1) | Aguenta o jogo longo |
| trovao-amarelo | Trovão Amarelo | 3 | 3/3 | Investida | dano 2 em gato inimigo à escolha | Limpa o campo e ataca já |
| guardiao-bigodudo | Guardião Bigodudo | 3 | 3/7 | Provocar | cura 3 no seu Líder | Muralha que cura |
| mestre-das-garras | Mestre das Garras | 4 | 4/4 | Investida, Primeira Patada | nada | Entra e já bate 8 no primeiro ataque |
| pelo-de-aco | Pelo de Aço | 4 | 4/8 | Provocar, Robusto | nada | Tanque que se regenera |
| gata-das-brasas | Gata das Brasas | 5 | 5/5 | Primeira Patada | dano 3 no Líder inimigo | Fecha o jogo (carta cara) |

Ações em JSON (rascunho): `trovao-amarelo` = `{"tipo":"dano","alvo":"inimigo_escolhido","valor":2}`; `guardiao-bigodudo` = `{"tipo":"cura","alvo":"lider_proprio","valor":3}`; `gata-das-brasas` = `{"tipo":"dano","alvo":"lider_inimigo","valor":3}`; `velha-dos-novelos` = `{"tipo":"comprar","alvo":"nenhum","valor":1}`; `soneca-ancestral` = `{"tipo":"energia","alvo":"nenhum","valor":1}`.

Por que o deck do jogador não fica obsoleto: só 8 espíritos, um por escolha de draft, custos ou efeitos que exigem situação (alvo, energia), e nenhum passa de 5/8 de status. Um Maine Coon perfeito (3/11) ainda é tão grande quanto o Pelo de Aço.

## 3. Inimigos da Liga 1

**Adotado em 2026-10-27 (T3.1, decisão do Renatho):** os inimigos são pessoas (criadores de gatos), não gatos. Nomes provisórios adotados em `data/enemies.json`: 3.1 vira **Tonho Sem-Sorte** (`tonho-sem-sorte`, criador de rua azarado), 3.2 vira **Irmãos Pimenta** (`irmaos-pimenta`, dupla de irmãos), 3.3 vira **Berenice da Matilha** (`berenice-da-matilha`, elite, Líder 22 HP) e o chefe segue **Madame Fifi Pelúcia** (`madame-fifi-pelucia`, Líder 25 HP). Batalhas comuns usam o Líder padrão (20). Regra "Banho de Espuma" aprovada com o formato fechado no schema. Ids em kebab-case; Espíritos podem repetir. Decks e falas de vitória/derrota (2 de cada) no JSON; os títulos antigos abaixo são só histórico.

### 3.1 Gatuno do Beco (batalha, o mais fácil)

Gato de rua oportunista. Deck: 4x Vira-lata (IV 1/2, Bravo = 3/4), 2x Persa (IV 2/2, Calmo = 1/8), 1x Siamês (IV 1/2, Calmo = 3/5), 1x Sphynx (IV 1/1, Calmo = 4/3), 1x Sombra Miúda, e efeitos: Arranhão Certeiro, Lambida Curativa, Petisco Surpresa.
Falas (sugestão): vitória "Miau! Essa rua é minha." / derrota "Tá, tá, pode passar. Mas deixa um petisco."

### 3.2 Dupla do Telhado (batalha, média, agressiva)

Muita Investida, pouca defesa. Deck: 3x Siamês (IV 2/2, Bravo = 5/3), 2x Vira-lata (IV 3/3, Calmo = 2/7), 1x Sphynx (IV 2/2, Calmo = 4/4), 1x Persa (IV 3/3, Calmo = 1/9), Sombra Miúda, Trovão Amarelo, e efeitos: Bote no Líder, Rugido de Guerra, Arranhão Certeiro.
Falas: vitória "Tchau, tchau, lá do alto do telhado!" / derrota "Escorreguei... foi o vento, tá?"

### 3.3 Matilha da Viela (ELITE, a mais difícil das três)

Tipo `elite`, deck variado com 3 Espíritos. Deck: 2x Vira-lata (IV 3/4, Bravo = 4/6), 2x Maine Coon (IV 3/3, Calmo = 3/10), 1x Persa (IV 3/3, Calmo = 1/9), 1x Sphynx (IV 3/3, Calmo = 5/5), 1x Siamês (IV 3/3, Calmo = 4/6), Guardião Bigodudo, Mestre das Garras, Gata das Brasas, e efeitos: Lambida Curativa, Farejar a Despensa.
Falas: vitória "A matilha vence, a matilha come." / derrota "Hmpf. A matilha vai se reorganizar."
Sugestão extra: recompensa de elite maior (decisão do Renatho, fora do escopo de dados).

Ajuste (Renatho, 2026-10-27): Mestre das Garras → Velha dos Novelos (no deck, 1x; continua somando 12).

### 3.4 Chefe: Madame Fifi Pelúcia (criadora rival, chefe da Liga 1)

Personalidade: criadora de Persas premiadas, esnobe, dramática, chama todo mundo de "querido" e jura que seus gatos nem precisam se despentear. No fundo, ama os gatos mais que os troféus.
Deck: 3x Persa (IV 4/4, Calmo = 1/10, Provocar), 2x Maine Coon (IV 4/4, Calmo = 3/11), 1x Siamês (IV 4/3, Bravo = 6/4), 1x Sphynx (IV 4/3, Calmo = 5/5), Guardião Bigodudo, Pelo de Aço, e efeitos: Soneca no Sol, Lambida Curativa, Bote no Líder.
Estilo: parede de Provocar e cura, poucas ameaças fortes. Quem tem Bote no Líder ou Primeira Patada vai bem.

Falas (sugestão, estilo Hades):
- Vitória (ela vence): "Ora, querido, até o seu pelo estava desalinhado. Volte quando estiver apresentável." / "Meus Persas nem despentearam. Pode tentar de novo, mas com mais classe."
- Derrota (você vence): "Impossível! Meus bigodes... estão tortos? Fique com a vitória, mas o troféu de beleza continua meu." / "Hmpf. Seus gatos têm... personalidade. Isso foi um elogio. Quase."

**Regra própria sugerida: "Banho de Espuma"**: no início de cada turno dela, o Líder da Fifi se cura em 1 HP (até o máximo de 20).
Formato proposto: `{"id":"banho-de-espuma","gatilho":"inicio_turno_proprio","acao":{"tipo":"cura","alvo":"lider_proprio","valor":1}}`. Reaproveita o formato de ação dos efeitos, então o core só precisa de um gancho novo.

Ajuste (Renatho, 2026-10-27): IVs do Siamês e do Sphynx do chefe = 5/5

## 3.5 Checagem rápida (simulador)

Rodei 600 duelos por inimigo em memória (nada editado em `data/`) contra um deck "médio" do jogador (12 gatos de raças e IVs sorteados, IA simples dos dois lados). **O core ainda não joga Espíritos nem efeitos**, então: Espíritos entraram como gatos comuns de status fixo (sem o "ao entrar"), as cartas de efeito foram **removidas** (decks de 9 a 10 cartas). Taxa de vitória do jogador:

| Inimigo | Jogador vence |
| --- | --- |
| Gatuno do Beco | ~83% |
| Dupla do Telhado | ~63% |
| Matilha da Viela (elite) | ~47% |
| Madame Fifi (chefe) | ~50% |

Leitura: a curva sobe como queremos (fácil, médio, difícil), mas o chefe está perto da elite e sem a cura da regra própria e dos efeitos. Isso é artefato do teste, que tira as cartas de efeito dos decks inimigos (deck menor, menos recurso). O deck "médio" também é uma média sem seleção do jogador, que na prática escolhe melhor. Remedir quando o core jogar efeitos. Se o chefe ainda ficar abaixo da elite, a alavanca mais simples é subir IVs do Siamês/Sphynx dele para 5.

## 4. O que o core precisa implementar

1. **Cartas de efeito**: carregar `effects.json`, `Card(kind="effect")`, `PlayEffect(hand_index, target)` em `legal_actions`/`apply_action`, custo de energia, carta consumida; eventos `EffectPlayed`, `DamageDealt`, `Healed`.
2. **Ações**: `dano` (gato ou Líder; se o gato morrer, `CatDied`), `cura` (limitada ao HP máximo do gato; no Líder, limitada ao HP máximo do Líder), `comprar` (respeita mão máxima 7 e deck vazio, igual à compra normal), `energia` (pode ultrapassar o teto 7? ver dúvida 5).
3. **Efeito ao entrar** dos Espíritos: disparado depois de `CatPlayed`. Alvo escolhido na hora de jogar a carta (por isso `PlayCat` precisa de `target` opcional). Sem alvo válido, o efeito é perdido (a carta entra do mesmo jeito).
4. **Buff de ATK até o fim do turno**: campo `atk_bonus_turn` no gato em campo, zerado no fim do turno do dono. Vale para o Líder? Não, só para gatos.
5. **Provocar** não afeta efeitos (já decidido no contrato); `Bote no Líder` ignora Provocar.
6. **Espíritos no deck**: `DeckSpec` precisa aceitar entradas além de `Cat` (Espírito, efeito) e `Card.kind` = `"special"`/`"effect"`; o schema de `enemies.json` já cobre isso.
7. **IA "simples" jogando efeitos**: regra mínima sugerida: (a) joga cura quando o alvo está abaixo de metade do HP, (b) joga dano no gato inimigo que ela consegue matar, ou no Líder se estiver a menos do dano de vencer, (c) compra/energia sempre que sobrar energia depois de jogar gatos, (d) buff só antes de atacar com o gato beneficiado. Sem isso a IA nunca usa as cartas e os decks acima ficam fracos.
8. **Regra do chefe**: gancho `inicio_turno_proprio` que executa uma ação do formato de efeito. Schema de `regra_propria` precisa fechar esse formato (`id`, `gatilho`, `acao`).
9. **Eventos novos para a UI**: nenhum além dos já listados, mais `EffectPlayed` com o alvo.

## 5. Dúvidas para o Renatho

1. Os custos e valores dos efeitos e Espíritos (seção 1 e 2) estão no caminho certo? Quer mais ou menos poder nas cartas de custo 1?
2. Ids em `kebab-case` (como hoje) ou `snake_case`?
3. Os nomes e personalidade da Madame Fifi (e dos três inimigos de batalha) servem como ponto de partida ou você quer escrever os seus?
4. O Líder do chefe e da elite deve ter mais HP que 20? (campo `lider_hp` já existe; não sugeri mudança.)
5. `Cochilo Revigorante` e `Soneca Ancestral` podem passar o teto de energia 7 no turno? (sugiro: não, ficam no teto.)
6. Efeito "ao entrar" com alvo à escolha, quando não existe alvo válido: perde o efeito (sugestão) ou impede de jogar o gato?
7. A regra do chefe "cura do Líder por turno" é boa, ou prefere algo mais marcante (ex.: o primeiro Persa dela entra com +2 HP)?
8. Os decks inimigos podem repetir Espíritos (hoje cada deck usa no máximo 1 de cada)?
