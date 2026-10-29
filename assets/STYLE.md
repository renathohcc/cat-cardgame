# Guia de estilo (aprovado: sprite 48x48 variante A; racas aprovadas em T7.1c)

## Tela e cartas
- Resolucao interna 480x270, escala inteira. Carta de gato atual: 62x62 (passo 64) em `ui/layout.py`.
- Proposta de moldura: janela de arte creme 56x44 no topo (x3,y3), faixa escura 56x11 embaixo para custo/ATK/HP/estrelas. Moldura 1 px + sombra, uma cor por tipo (gato, Especial, efeito).
- **Sprite de batalha (carta): 48x48** (variante A) cabe na janela 56x44 com leve corte de espaco vazio; 32x32 (B) fica pequeno; 64x64 (C) estoura a carta de 62 (so serviria se a carta crescer).
- **Sprite de criatorio:** mesmo 48x48, em frames (idle/andar/dormir), mesma pelagem.

## Estilo
- Pixel art fofa "chibi": cabeca grande, olhos grandes amarelos com brilho branco, nariz rosa, corpo curto.
- Contorno de 1 px em cor escura quente (`#3b2a38`), nunca preto puro; sem anti-aliasing; sem dithering.
- Luz vinda de cima-esquerda: 3 tons de pelagem (sombra, base, luz) + padrao (listras) + peito/focinho claro.
- Vira-lata (A) usa ~10 cores; as outras racas podem usar ~13 a 30 cores para manter detalhe (aprovado pelo Renatho, T7.1c). Fundo transparente.
- **Cor de destaque por raca** (apetrecho, uma por gato, para leitura rapida): Vira-lata marrom (capa), Siames azul-petroleo (bandana), Persa azul real e dourado (capa e coroa), Sphynx roxo e magenta (capa e energia), Maine Coon vermelho (capa).

## Paleta base (Vira-lata laranja)
| Camada | Hex |
| --- | --- |
| contorno | #3b2a38 (pupila #2a1c2a) |
| pelagem sombra / base / luz | #b86a3a / #d98f4e / #f0b878 |
| padrao (listras) | #8f4a2c |
| peito e focinho | #f6e3c8 |
| nariz e orelha interna | #f09aa8 |
| olhos / brilho | #ffd84a / #ffffff |

## Camadas
Separadas por cor exata (o Pixellab respeita paleta forcada): `contorno`, `pelagem`, `padrao`, `peito_focinho`, `nariz_orelha`, `olhos`. Acessorio (capa, coleira) e expressao entram depois como camadas extras. Script: `assets/tools/split_layers.py`.

## Variacao
- **Raca:** corpo base proprio (silhueta): Vira-lata normal; Siames magro, mascara/patas escuras, olhos azuis; Persa redondo, pelo longo, focinho achatado; Sphynx sem pelo (so contorno e pele rosada, orelhas enormes); Maine Coon grande, tufos nas orelhas e cauda felpuda.
- **Pelagem:** palette swap das 5 cores de pelo (exemplos em `_proposta/A_48_capa_pelagem_*.png`: cinza, preto, creme). Pelagens raras = paletas raras.
- **IV:** brilho/estrelinha e olhos diferentes para IV alto (efeito em camada extra, sem mudar o corpo).
- **Natureza:** expressao (Calmo: olhos meio fechados; Bravo: sobrancelha; Agitado: olhos arregalados, pelo arrepiado) em camada de expressao.
- **Sexo:** sem diferenca no sprite (so icone na UI).
