# Escolha da Ração Escolha no save

2026-11-03 · agente core (T13.1)

## Problema
A Ração Escolha fixa 1 IV (ATK ou HP) de um dos pais, e a ninhada só nasce runs depois. A escolha do jogador precisa ficar guardada no casal. O schema do save v2 (`breeding[]`) é fechado (`additionalProperties: false`) e só tem `male`, `female`, `runs_left` e `ration` (id kebab-case), então não há campo para "qual IV e de qual pai".

## O que o core fez por enquanto (sem tocar em `data/`)
Codifica a escolha no próprio `ration`, que o schema aceita por ser kebab-case: `racao-escolha-atk-pai`, `racao-escolha-hp-mae` etc. As funções `encode_ration`/`parse_ration` (`core/rations.py`) isolam isso; a UI deve usar `breeding_status(save, content)`, que devolve `ration` (id real) e `choice` (`IvChoice`) já separados.

## Opções
1. **Manter a codificação** (zero mudança de dados). Contra: `ration` deixa de ser só um id de `shop.json`; um validador futuro que cheque o id contra a loja precisa conhecer o sufixo.
2. **Novo campo opcional `ration_choice`** no casal: `{"stat": "atk"|"hp", "parent": "father"|"mother"}` ou `null`. Schema e exemplos do save mudam (agente de dados) e o core passa a gravá-lo (troca pequena, só em `core/rations.py` e `core/breeding.py`).

## Recomendação
Opção 2 antes de fechar a 10a: é o formato limpo e a troca é barata agora, enquanto o save v2 ainda não saiu. Até lá a opção 1 funciona e é lida de volta sem perda.
