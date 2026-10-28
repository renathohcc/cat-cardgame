"""Paleta e constantes visuais (placeholders). Trocar aqui para re-colorir tudo."""
from __future__ import annotations

W, H = 480, 270            # resolucao interna

C = {
    "bg": (24, 28, 44),
    "panel": (34, 40, 62),
    "panel_edge": (70, 80, 112),
    "text": (236, 236, 244),
    "dim": (140, 148, 172),
    "dark": (14, 16, 26),
    "slot": (30, 36, 56),
    "slot_edge": (58, 66, 96),
    "card": (52, 58, 86),
    "card_enemy": (74, 52, 64),
    "card_edge": (110, 120, 156),
    "cost": (60, 120, 230),
    "atk": (214, 70, 64),
    "hp": (70, 180, 90),
    "star_on": (255, 214, 64),
    "star_off": (72, 76, 100),
    "ready": (96, 255, 120),
    "select": (255, 255, 255),
    "target": (255, 84, 84),
    "drop": (96, 220, 255),
    "taunt": (232, 184, 48),
    "player": (96, 200, 255),
    "enemy": (255, 120, 120),
    "good": (96, 230, 120),
    "bad": (255, 96, 96),
    "warn": (255, 200, 64),
    "button": (60, 170, 90),
    "button_hot": (110, 240, 130),
    "button_off": (60, 66, 90),
    "male": (110, 170, 255),
    "female": (255, 140, 200),
    "effect": (166, 110, 236),       # cartas de efeito
    "effect_bg": (52, 42, 88),
    "special": (236, 204, 96),       # Espiritos
    "special_bg": (68, 60, 40),
    "buff": (255, 214, 64),
    "energy": (140, 200, 255),
}

BREED_COLOR = {
    "vira-lata": (150, 120, 84),
    "siames": (196, 176, 140),
    "persa": (210, 210, 224),
    "sphynx": (230, 150, 150),
    "maine-coon": (176, 112, 64),
}
DEFAULT_BREED_COLOR = (150, 150, 170)

KEYWORD_COLOR = {
    "provocar": (232, 184, 48),
    "investida": (240, 110, 60),
    "primeira-patada": (170, 110, 240),
    "robusto": (70, 190, 100),
}
KEYWORD_LONG = {"provocar": "PROVOCAR", "investida": "INVESTIDA",
                "primeira-patada": "1A PATADA", "robusto": "ROBUSTO"}
KEYWORD_SHORT = {"provocar": "PROV", "investida": "INVE", "primeira-patada": "1PAT",
                 "robusto": "ROBU"}

NATURE_COLOR = {"calmo": (120, 190, 255), "bravo": (255, 150, 90), "agitado": (255, 100, 160)}

# Mini-run: cor, nome curto e nome longo de cada tipo de no
NODE_COLOR = {"batalha": (230, 96, 90), "elite": (190, 110, 255),
              "descanso": (96, 220, 140), "chefe": (255, 214, 64)}
NODE_NAME = {"batalha": "BATALHA", "elite": "ELITE", "descanso": "DESCANSO", "chefe": "CHEFE"}
NODE_LONG = {"batalha": "Batalha", "elite": "Elite", "descanso": "Descanso", "chefe": "Chefe"}
