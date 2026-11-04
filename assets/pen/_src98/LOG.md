# T9.8 - log Pixellab (objetos e tiles do quintal)
Style ref: upload de ref_cat64.png / ref_cat64x40.png (recortes dos gatos de pen). Ferramenta: create_object_pro_flash (1 direcao, view high top-down, ~5 geracoes cada).
| nome | object_id |
|---|---|
| cama_rosa 64x40 | a164bc45-4f1a-44aa-9785-6cd5be21d6b7 |
| casinha_a 64x64 | 9f08e7ce-1bb7-46c5-8b0d-624e38d5126d |
| cama_teal 64x40 | 6861a9c9-5894-4cd4-8990-d91f0ff8737d |
| cama_cesto 64x40 | 4cd91603-ab5c-4759-8bad-235861299e5b |
| cama_cinza 64x40 | 2d218b87-a767-495f-9224-261c0e6b6493 |
| cama_casal 96x48 | 9d29d904-1f90-4782-9cb7-86b6574ae1d9 |
| viveiro_cesto 64x40 | 5c92c6e9-8b47-454e-b434-35ab9e396e4c |
| banco 80x48 | 3cd643b9-00f0-4a5c-ab4f-42ccdad9ca51 |
| casinha_filhote 64x64 | 72b6bff6-38ce-4839-9679-3a62ed7b08ad |
| arranhador 64x72 | 56ae18fd-fa2f-40a2-a095-4a07fbbe85ec |
| tunel 96x48 | c4e947df-c5f9-488d-b4fc-ca00772d7adf |
| arvore_a 64x80 | 50ef60a2-c84f-442e-b45c-7c0f075d375c |
| moita_flor 32x32 | dd51435b-ce50-4284-8a52-2acb40c490ea |
| tunel_b 96x48 (horizontal) | 169d9f30-a5eb-4ce3-85a7-48af6de2a5b8 |
| novelo 24x24 | 2349ed33-0583-4014-a493-7fc84a4c5eff |
| ratinho 24x24 | 9bf3ce7b-1fbb-4665-a157-edbb5f4ea041 |
| bola 24x24 | 06027f3e-c130-478f-ab4f-93592cca9158 |
| tigela_agua 24x24 | a1948bf7-f0bc-461d-9b41-dab5c32cbefc |
| tileset grass->dirt (standard, 16px) | 3170c5cb-5629-4c21-9840-dc1d89d4654c |
| tileset grass->path (standard, 16px) | a93ff4a9-6929-4a58-a6ee-9fb9609baf52 |
| arvore_b 64x80 | f1122948-1edb-4991-82bb-3d6860c94608 |
| banco_b 80x40 | c962eecb-3c44-4627-8a05-97354ca4c639 |
| tigela_racao 24x24 | 861180de-2487-4a23-a2df-ff08f7543193 |
| moita_b 32x32 | a32172b7-4149-412e-b550-20685dbbab49 |
| tileset grass->path chained (ts_path) | 662e3776-4a03-47f6-ad7f-87a44a8dae1c |
| tileset grass->floor filhotes (ts_floor) | 8cff2e47-5640-413b-811a-a2687b3c8f1f |
| tiles_pro cerca (16 tiles) | 4272b909-5821-4d79-8756-4b0469520d6c |
| cerca_h 48x32 | 4ac7b4ce-641c-4de0-bf0a-13723e2a79ff |
| cerca_v 24x48 | 16a0373b-20af-4503-a4a1-8693d806dfd3 |
| poste_portao 24x48 | 7b6569c4-5ff5-425d-bbde-d06a55ef0653 |
| pedra 24x24 | cff70971-6fed-40c4-8da5-0b4bc4c449ee |
| tileset grass->play mat (ts_floor2) | 57761a3e-3470-4038-82f8-72a370b9b633 |
Descartados: create_tiles_pro cerca (blur, fundo branco); ts_path/ts_floor encadeados (resultado com laranja).
| arvore_peq1 48x64 | 9612c361-fec1-45e5-8940-a3f541f5f55d |
| arvore_peq2 48x64 | 3c995e47-5f11-4356-b834-d38797a84b05 |
| moita_c 32x32 | edca4061-2c06-4343-90b3-b10858256e8f |
## Rodada L (canvas maiores; os 64x40 saiam com objeto de ~44x30, pequeno demais p/ gato de 50x40)
| cama_rosa_L 96x64 | 13006d7a-6056-4a60-b5e9-0a4d41910b2f |
| cama_cinza_L 96x64 | 1b31d284-140e-49bc-8c8d-14c00462c9a9 |
| cama_teal_L 96x64 | 06c47a7f-6601-4f3c-8752-508f66aca69a |
| cama_cesto_L 96x64 | 401fcbd5-cbad-4334-9f8f-25c6a49e680d |
| viveiro_L 96x64 | c857b628-44a7-4b98-b0d4-8d1f120f67e8 |
| cama_casal_L 128x72 | 08996d7f-12d3-4870-acbb-569a2cb01f0d |
| casinha_L 88x88 | f5c679e7-a5e4-4d0d-9473-b1f4b57dd86f |
| banco_L 104x64 | 014c7610-1b8a-40d9-b1a6-785d4d75a1c3 |
| casinha_filhote_L 80x80 | bb81c094-c7e0-4f6d-b696-a82e1147059a |
| arranhador_L 80x96 | e510b313-ecd4-4f86-bd04-45de7924f284 |
| tileset grass->clover piso filhotes (ts_floor3) | 66c8b5af-da91-45a5-9334-99fab4c643c2 |

## Prompts (resumo)
Prefixo comum: "chibi pixel art ..., fills most of the canvas", view high top-down, style_image = recorte do gato (ref_cat*.png, mesma pasta), uso: "1px dark warm outline, 3 tone shading light top-left, saturated soft colors, no anti-aliasing".
Camas: "cute round pet cat bed, <cor> cushion with thick rounded rim and cream inner pillow" (rosa/teal/lavanda); cesto: "oval woven wicker basket cat bed with soft cream blanket"; viveiro: "oval wicker basket for kittens with light blue blanket and tiny pink pillow"; casal: "large oval double cat bed ... two cream pillows and a red heart-shaped pillow".
Casinha: "cute wooden cat house, red clay tile roof, round window, arched door, tiny sign and flower pot"; filhote: "small cute kitten house, pastel pink roof, cream walls, heart".
Banco: "wooden park bench seen from above at an angle ... planks"; arranhador: "cat scratching post tower, rope pole, round teal cushion platform"; tunel: "striped teal and cream fabric cat play tunnel lying horizontally".
Brinquedos/tigelas 24x24; cerca_h 48x32 / cerca_v 24x48 / poste_portao 24x48; arvores 64x80 e 48x64; moitas 32x32.
Tilesets (standard, 16 px, square, lineless, basic shading, high top-down): lower "short soft green grass lawn ..." x upper "packed light brown dirt" / "cream sandy gravel footpath" / "light green clover meadow". NOTA: nesses sets o rotulo 'lower' veio como a terra/caminho e 'upper' como grama (build_t98_bg inverte).
Rodada 1 usou canvas 64x40 etc. (descartada: objeto saia com ~44x30); rodada L (canvas maiores) e a usada.
