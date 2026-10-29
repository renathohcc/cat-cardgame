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
