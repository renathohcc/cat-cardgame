# Licencas e origem dos assets

## Arte de gatos (`assets/cats/`)
- Gerada com **Pixellab** (IA generativa de pixel art, assinatura Tier 1) via MCP, em 2026-10-28 (racas Siames, Persa, Sphynx, Maine Coon, e Vira-lata em T7.0). Retoques locais por script (`assets/tools/`): reducao de cores, separacao em camadas e palette swap.
- Termos de uso do servico: https://pixellab.ai/termsofservice (consultar o texto vigente para uso comercial; nenhum termo e transcrito ou interpretado aqui).
- **Disclosure de IA na Steam:** o jogo contem arte gerada por IA em tempo de desenvolvimento (sprites dos gatos). Isso deve ser declarado no formulario de conteudo de IA da pagina da Steam, descrevendo a arte pre-gerada (nao ha geracao por IA durante o jogo). O Renatho aprovou o uso de arte por IA em T7.0.

## Scripts
- `assets/tools/*.py`: codigo proprio do projeto (Pillow).

## Espiritos, efeitos e tabuleiro (T7.5)
- `assets/specials/`, `assets/effects/` (48x48) e os fundos em `assets/board/_proposta/*_raw.png` (400x224): gerados com **Pixellab** (create_image_pixflux) em 2026-10-28; mesmos termos e mesmo aviso de disclosure de IA da secao de gatos. Os fundos sao apenas proposta (nao aprovados).
- `assets/icons/` (9x9 e 18x18): desenhados a mao por script (`assets/tools/build_t75.py`), sem IA e sem terceiros.
- Mockups `mock_*.png` e `*_480x270.png`: montagem por script (Pillow) sobre os fundos acima.

## T8.1 / T8.x: arte nativa 96x96 (2026-10-28)
- `assets/specials96/` (8 Espiritos) e `assets/effects96/` (8 efeitos): gerados com **Pixellab** (`create_image_pro_flash`, 96x96) em 2026-10-28; fontes originais em `_src/`. Binarizacao de alfa por script. Mesmos termos (https://pixellab.ai/termsofservice) e mesmo aviso de disclosure de IA da Steam das secoes anteriores.
- `assets/cats96/` e `assets/leaders/` (feitos por outro agente, tambem gerados com **Pixellab** em 2026-10-28): gatos 96x96 e retratos de Lideres. Mesmos termos; entram no disclosure de IA da Steam como arte pre-gerada em desenvolvimento (nao ha geracao durante o jogo). Detalhes de geracao no relatorio daquela tarefa.
- `assets/icons16/` (12 icones 16x16 + sheet x2): desenhados pixel a pixel por script (`assets/tools/build_t81_icons.py`), sem IA e sem terceiros.
- Scripts: `assets/tools/build_t81.py`, `assets/tools/build_t81_icons.py` (Pillow, codigo proprio).

## T8.4: tabuleiro final, pecas de UI e fonte (2026-10-28)
- `assets/board/final/board_taverna.png`, `board_noturno.png` e `assets/ui/*/*.png`: desenhados por script (Pillow, `assets/tools/build_t84_board.py`), sem IA e sem terceiros.
- Fonte `assets/fonts/chaoscats_16|32.png/json`: glifos base (A-Z, a-z, numeros, pontuacao) gerados com **Pixellab** `create_font` (Bold, 16 px) em 2026-10-28; mesmos termos (https://pixellab.ai/termsofservice) e mesmo aviso de disclosure de IA. Acentos pt-BR, cedilha, espaco e simbolos (`[ ] < > | x -> .`) desenhados por script (`assets/tools/build_t84_font.py`). Atlas original em `assets/fonts/_src/atlas.png`. Nenhuma fonte de terceiros.

## Cercado (Criatorio) — estado final (T9.0 a T9.11, 2026-10-29)

Consolida as antigas secoes T9.0, T9.2, T9.4, T9.6, T9.7, T9.8, T9.9 e T9.11. Os textos antigos que citavam `pen_bg.png` e "sem IA" estao superados: `pen_bg.png` nao existe mais e o fundo atual usa IA.

### Origem de cada arquivo em `assets/pen/`
| Arquivo | Origem |
| --- | --- |
| `pen_bg_dia.png`, `pen_bg_amanhecer.png`, `pen_bg_entardecer.png`, `pen_bg_noite.png` | **IA Pixellab (derivado)**: montagem por script a partir de tiles dos tilesets Wang (`create_topdown_tileset`: grama/terra, grama/caminho, grama/piso dos filhotes) e de sprites Pixellab (cerca, arvores, moitas). Postes/trilhos da cerca e postes de portao (T9.9) e sombras sao **por script**. Os 4 periodos saem por tabela de cores (script). |
| `objects.png/json` | **Misto**. Objetos Pixellab (`create_object_pro_flash`, T9.8): camas, casinhas, banco, arranhador, tunel, brinquedos, tigelas, arvores e moitas. Camas: versao Pixellab antiga **sem sombra de contato** (T9.11; sombra opcional por script via `T99_BED_SHADOW=1`). Animacoes, contorno forcado e pos-processo por script. |
| `cats_pen.png/json` | **IA Pixellab (T9.0)**: gatos pacato e filhotes 64x64; bases com `create_image_pro_flash`, animacoes com `animate_image`; frames brutos em `assets/pen/_src/`. Limpeza e montagem por script. |
| `fx.png/json` (coracao, z, nota, brilho, estrela 16x16) | **Script** (`build_t90_bg_fx.py`), sem IA. |
| `ambient.png/json`, `pen.json`, `palette_pen.json`, `PALETA_PEN.md/png` | **Script**, sem IA (paleta PEN de 48 cores). |
| Tapetes/almofadas T9.9 (`_src99/tapete_*.png`, `build_t99_beds.py`) | **Script**, sem IA; **nao usados em producao**. |

### Ids, prompts e logs
- T9.8: `assets/pen/_src98/LOG.md` (todos os ids e prompts Pixellab; originais crus; refs de estilo `ref_cat*.png` = recortes dos gatos de pen). `create_tiles_pro` foi testado para cerca e descartado.
- T9.9: `assets/pen/_src99/LOG.md` (0 geracoes Pixellab; so script).
- T9.6: blocos e objetos em `assets/pen/_src96/` (sem LOG.md proprio). T9.0: frames em `assets/pen/_src/`.
- Creditos Pixellab: T9.8 gastou ~213 geracoes (811.75 -> 598.75); T9.7 e T9.9 gastaram 0.

### Scripts
`assets/tools/build_t90*.py`, `build_t92_*.py`, `build_t94_*.py`, `build_t96_*.py`, `build_t97_*.py`, `build_t98_*.py`, `build_t99_*.py` (Pillow/numpy, codigo proprio). Pos-processo (T9.8): binarizacao de alpha, quantizacao na paleta PEN, contorno #3b2a38, corte ao bbox, montagem por tiles, sem resize.

### Historico resumido (versoes superadas, guardadas em `_v3`..`_v7`)
- T9.2 e T9.4: fundo e objetos 100% por script (sem IA). A imagem `_referencia_renatho.webp` foi so referencia de disposicao (nenhum pixel copiado).
- T9.6: quintal gerado com Pixellab (`create_image_pro`, `create_object_pro_flash`) a partir da referencia do Renatho; guardado em `_v4/`.
- T9.7: refeito 100% por script na paleta PEN (0 creditos); guardado em `_v5/`.
- T9.8: substituiu por sprites e tilesets Pixellab (estado atual); T9.9 trocou postes/cerca por script (backup T9.8 em `_v6/`); T9.11 removeu a sombra das camas.

### Termos e disclosure (PENDENTE para o Renatho)
- Termos: https://pixellab.ai/termsofservice (nenhum termo e transcrito ou interpretado aqui). Creditos: Pixellab, plano Tier 1.
- **PENDENTE:** o Renatho deve confirmar que o plano permite **uso comercial** da arte gerada (revisao da fase 7, item 12) e registrar o resultado aqui.
- **PENDENTE:** declarar no formulario de **disclosure de IA da Steam** que o cercado (fundos, objetos e gatos de pen) contem arte pre-gerada por IA em desenvolvimento (sem geracao durante o jogo).
