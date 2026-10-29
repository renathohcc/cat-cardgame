# Pre-escuta dos candidatos de audio (T10.6)

Abra `reports/audio/pre_escuta_candidatos.html` no navegador: por cue, o arquivo **atual de producao** e depois os candidatos. **Ninguem ouviu** nada (so analise numerica e descricao das fontes); as notas descrevem a intencao e a recomendacao e podem estar erradas.

Comando para trocar: `python assets/tools/apply_audio_candidates.py meow_1=bsb_pequeno1 ...` ou `--recomendado` (ver T10.6).

## mapa_run

Atual: `music/mapa_run.ogg` (143.00 s, -20.0 LUFS). Fonte atual: The Arplands ([link](https://opengameart.org/content/the-arplands)) `the_arplands_0.ogg`.

| candidato | dur (s) | LUFS | fonte / autor | nota | recomendacao |
|---|---|---|---|---|---|
| `cozy_guitar` | 122.44 | -20.0 | Cozy Puzzle In-Game 3 (OpenGameArt) (MintoDog) | violao acustico + baixo, 'cozy/relax' pelas tags da fonte; loop de 122 s, ritmo ~108 bpm | RECOMENDADO (1a escolha) |
| `explor_guitar` | 81.49 | -20.0 | Exploration (OpenGameArt) (johnclark) | violao acustico em E maior, 'chill/aventura'; trecho original so tem 21 s, repetido 4x (81 s): repeticao audivel | reserva |
| `lofi_boredom` | 166.00 | -20.0 | Relaxing Instrumentals (Collection) (OpenGameArt) 'Boredom' (Holizna) | lo-fi instrumental da colecao Holizna ('Boredom'), 166 s, faixa nao feita para loop (costura de 4 s por crossfade); estilo exato nao confirmado | alternativa se quiser tom lo-fi; ouvir antes |

## meow_1

Atual: `sfx/meow_1.ogg` (0.51 s, -16.0 LUFS). Fonte atual: Meow ([link](https://opengameart.org/content/meow)) `Meow.ogg`.

| candidato | dur (s) | LUFS | fonte / autor | nota | recomendacao |
|---|---|---|---|---|---|
| `bsb_pequeno1` | 0.46 | -16.1 | BigSoundBank - Little Meow of a Cat #1 (s0494) (Joseph Sardin) | miadinho curto (0,46 s), gravacao limpa (piso de ruido ~-33 dB), timbre medio | RECOMENDADO |
| `bsb_mewing_a` | 0.62 | -16.0 | BigSoundBank - Small mewing of a cat (s0098) (Joseph Sardin) | 1o de 4 miados da mesma gravacao silenciosa (piso de ruido muito baixo), 0,6 s | boa alternativa |
| `lab_sintetico` | 1.08 | -17.1 | Meowing Cat Made in LabChirp (OpenGameArt) (Traceletz) | miado 'cartoon' de sintetizador (LabChirp), 1,1 s: limpo mas eletronico, mais 'jogo retro' que gato real | reserva (tom diferente) |

## meow_2

Atual: `sfx/meow_2.ogg` (1.10 s, -16.1 LUFS). Fonte atual: Cat Purr & Meow ([link](https://opengameart.org/content/cat-purr-meow)) `cat_mewfood.wav`.

| candidato | dur (s) | LUFS | fonte / autor | nota | recomendacao |
|---|---|---|---|---|---|
| `bsb_mewing_b` | 0.70 | -16.0 | BigSoundBank - Small mewing of a cat (s0098) (Joseph Sardin) | 2o miado da gravacao s0098, 0,7 s, claro | RECOMENDADO |
| `bsb_pequeno3` | 0.92 | -16.2 | BigSoundBank - Little meow of a cat #3 (s1473) (Joseph Sardin) | miadinho #3 do Sardin, 0,9 s, mais grave/suave | boa alternativa |
| `boca_1` | 1.10 | -16.0 | BigSoundBank - Cat Meow Made with Mouth (s0926) (Joseph Sardin) | 'miado feito com a boca' (imitacao humana), 1,1 s: tende a soar cartoon/divertido, nao gato real | reserva (gosto) |

## meow_3

Atual: `sfx/meow_3.ogg` (1.50 s, -16.2 LUFS). Fonte atual: Cat Purr & Meow ([link](https://opengameart.org/content/cat-purr-meow)) `cat_softmew.wav`.

| candidato | dur (s) | LUFS | fonte / autor | nota | recomendacao |
|---|---|---|---|---|---|
| `bsb_cat1_longo` | 1.48 | -16.0 | BigSoundBank - Meow cat #1 (s1889) (Joseph Sardin) | miado mais longo (1,5 s) do 'Meow cat #1', gravacao muito limpa (piso ~-81 dB) | RECOMENDADO |
| `bsb_mewing_c` | 0.53 | -16.1 | BigSoundBank - Small mewing of a cat (s0098) (Joseph Sardin) | 3o miado de s0098, 0,5 s, levemente mais grave | alternativa curta |
| `boca_4` | 1.10 | -16.0 | BigSoundBank - Cat Meow Made with Mouth (s0926) (Joseph Sardin) | imitacao com a boca, 1,1 s | reserva (gosto) |

## meow_4

Atual: `sfx/meow_4.ogg` (1.70 s, -16.1 LUFS). Fonte atual: Cat Purr & Meow ([link](https://opengameart.org/content/cat-purr-meow)) `cat_mewpurr2.wav`.

| candidato | dur (s) | LUFS | fonte / autor | nota | recomendacao |
|---|---|---|---|---|---|
| `bsb_mewing_d` | 0.54 | -15.9 | BigSoundBank - Small mewing of a cat (s0098) (Joseph Sardin) | 4o miado de s0098, 0,5 s, +8% de tom (mais fofo) | RECOMENDADO |
| `boca_7` | 0.95 | -16.0 | BigSoundBank - Cat Meow Made with Mouth (s0926) (Joseph Sardin) | imitacao com a boca, 0,95 s | reserva (gosto) |
| `baby_meow` | 0.93 | -16.1 | Baby Animals - Sounds Pack (OpenGameArt) `Meow.ogg` (Technopeasant (compilacao; origem de cada som e freesound CC0 nao identificada por arquivo)) | miado de filhote do Baby Animals Pack (0,9 s), agudo; proveniencia individual nao verificada | alternativa; usar tambem como pack B |

## kitten_mew

Atual: `sfx/kitten_mew.ogg` (0.92 s, -16.0 LUFS). Fonte atual: Kitten Mew ([link](https://opengameart.org/content/kitten-mew)) `kitten_mew-1_0.ogg`.

| candidato | dur (s) | LUFS | fonte / autor | nota | recomendacao |
|---|---|---|---|---|---|
| `bsb_pequeno1_agudo` | 0.32 | -16.3 | BigSoundBank - Little Meow of a Cat #1 (s0494) (Joseph Sardin) | meow #1 do Sardin a +45% de tom, 0,32 s: agudo e delicado, pode soar 'chipmunk' se exagerado | RECOMENDADO (testar) |
| `baby_agudo` | 0.77 | -16.2 | Baby Animals - Sounds Pack (OpenGameArt) `Meow.ogg` (Technopeasant (compilacao; origem de cada som e freesound CC0 nao identificada por arquivo)) | miado de filhote do pack Baby Animals a +20% de tom, 0,77 s | alternativa mais natural |
| `lab_agudo` | 0.67 | -16.1 | Meowing Cat Made in LabChirp (OpenGameArt) (Traceletz) | miado sintetico +60% de tom, 0,67 s, bem 'cartoon', baixo volume original | reserva |

## purr

Atual: `sfx/purr.ogg` (1.90 s, -19.0 LUFS). Fonte atual: Cat Purr & Meow ([link](https://opengameart.org/content/cat-purr-meow)) `cat_purrsleepy_loop.wav`.

| candidato | dur (s) | LUFS | fonte / autor | nota | recomendacao |
|---|---|---|---|---|---|
| `bsb_ronronar` | 1.90 | -19.2 | BigSoundBank - Cat Purr (s0436) (Joseph Sardin) | ronronar real (Sardin, 'Cat Purr'), trecho de 1,9 s, passa-baixa 3,5 kHz | boa |
| `bsb_ronronar_suave` | 1.90 | -19.4 | BigSoundBank - Cat Purr (s0436) (Joseph Sardin) | mesma gravacao, outro trecho, passa-baixa 1,8 kHz: mais abafado e suave | RECOMENDADO |
| `sintetizado` [SINTETIZADO] | 1.90 | -20.1 | Sintetizado por script (assets/tools/build_audio_candidates.py), sem amostras externas (projeto Chaoscats) | ruido passa-faixa modulado a 25 Hz + 110 Hz: limpo, sem ruido de fundo, mas artificial | fallback se o real incomodar |

## pet

Atual: `sfx/pet.ogg` (0.23 s, -20.6 LUFS). Fonte atual: Kenney - RPG Audio ([link](https://opengameart.org/content/50-rpg-sound-effects)) `handleSmallLeather.ogg`.

| candidato | dur (s) | LUFS | fonte / autor | nota | recomendacao |
|---|---|---|---|---|---|
| `sint_blip` [SINTETIZADO] | 0.35 | -18.9 | Sintetizado por script (assets/tools/build_audio_candidates.py), sem amostras externas (projeto Chaoscats) | dois toques tonais macios subindo (660->880 Hz), 0,35 s; sinteticos, 'carinho' de jogo | RECOMENDADO |
| `pop_fofo` | 0.42 | -25.0 | Pop sounds (OpenGameArt) (EZduzziteh) | 'pop' vocal de bolha do pack EZduzziteh, 0,4 s, passa-baixa | alternativa |
| `ronronar_curto` | 0.90 | -19.3 | BigSoundBank - Cat Purr (s0436) (Joseph Sardin) | 0,9 s de ronronar real, abafado | alternativa mais realista |

## pet_2

Atual: `sfx/pet_2.ogg` (0.90 s, -19.0 LUFS). Fonte atual: Cat Purr & Meow ([link](https://opengameart.org/content/cat-purr-meow)) `cat_purractive_loop.wav`.

| candidato | dur (s) | LUFS | fonte / autor | nota | recomendacao |
|---|---|---|---|---|---|
| `sint_blip2` [SINTETIZADO] | 0.30 | -18.9 | Sintetizado por script (assets/tools/build_audio_candidates.py), sem amostras externas (projeto Chaoscats) | bip redondo com vibrato leve, 0,3 s; sintetico | alternativa |
| `pop_fofo_2` | 0.14 | -19.4 | Pop sounds (OpenGameArt) (EZduzziteh) | pop curto (0,14 s) a -10% de tom | reserva |
| `ronronar_curto_2` | 0.90 | -19.4 | BigSoundBank - Cat Purr (s0436) (Joseph Sardin) | outro trecho de 0,9 s do ronronar real | RECOMENDADO (como variacao de pet) |

## cat_death

Atual: `sfx/cat_death.ogg` (1.20 s, -15.8 LUFS). Fonte atual: Cat Purr & Meow ([link](https://opengameart.org/content/cat-purr-meow)) `cat_softmew.wav`.

| candidato | dur (s) | LUFS | fonte / autor | nota | recomendacao |
|---|---|---|---|---|---|
| `sint_poof` [SINTETIZADO] | 0.42 | -17.4 | Sintetizado por script (assets/tools/build_audio_candidates.py), sem amostras externas (projeto Chaoscats) | 'puff' de ruido filtrado + bloop tonal descendente, 0,42 s; 100% sintetizado, sem miado | boa, a mais neutra |
| `poof_miadinho` [SINTETIZADO] | 0.55 | -16.2 | Sintetizado por script (assets/tools/build_audio_candidates.py), sem amostras externas; BigSoundBank - Little Meow of a Cat #1 (s0494) (projeto Chaoscats; Joseph Sardin) | puff sintetizado + miadinho do Sardin com pitch caindo (derrota fofa), 0,55 s | RECOMENDADO |
| `pop_queda` [SINTETIZADO] | 0.71 | -16.0 | Pop sounds (OpenGameArt); Sintetizado por script (assets/tools/build_audio_candidates.py), sem amostras externas (EZduzziteh; projeto Chaoscats) | pop vocal (EZduzziteh) + 3 notas macias descendo, 0,7 s: 'queda' suave | alternativa |

## cat_death_2

Atual: `sfx/cat_death_2.ogg` (0.73 s, -16.0 LUFS). Fonte atual: Meow ([link](https://opengameart.org/content/meow)) `Meow.ogg`.

| candidato | dur (s) | LUFS | fonte / autor | nota | recomendacao |
|---|---|---|---|---|---|
| `sint_poof_2` [SINTETIZADO] | 0.41 | -18.7 | Sintetizado por script (assets/tools/build_audio_candidates.py), sem amostras externas (projeto Chaoscats) | variacao do puff sintetizado, mais agudo, 0,41 s | boa |
| `poof_miadinho_2` [SINTETIZADO] | 0.65 | -16.2 | Sintetizado por script (assets/tools/build_audio_candidates.py), sem amostras externas; BigSoundBank - Little meow of a cat #3 (s1473) (projeto Chaoscats; Joseph Sardin) | puff + miadinho #3 do Sardin com pitch caindo, 0,65 s | RECOMENDADO |
| `pop_queda_2` [SINTETIZADO] | 0.70 | -16.1 | Pop sounds (OpenGameArt); Sintetizado por script (assets/tools/build_audio_candidates.py), sem amostras externas (EZduzziteh; projeto Chaoscats) | pop curto + notas descendo, 0,7 s | alternativa |

