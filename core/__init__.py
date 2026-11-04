"""Core do jogo: regras puras, sem pygame."""
from core.adoption import (adopt, adoption_count, adoption_weights, create_adoption,
                           can_donate, donate_cat, donate_offer, donation_value,
                           has_pending_adoption, room_candidates)
from core.breeding import (RunAftermath, advance_after_run, breeding_status,
                           breed_cfg, cancel_breed, can_breed, can_start_breed,
                           initial_runs, start_breed)
from core.cats import cat_stats, roll_cat
from core.collection import (autofill_deck, available_cats, deck_cats, get_cat,
                             rename_cat, save_deck_draft, set_deck)
from core.content import load_content
from core.kennel import (AreaStatus, AreaUnlock, area_status, areas_blocked_by_coins,
                         areas_blocked_by_prestige, areas_status, available_areas,
                         can_adopt, couples_allowed, kennel_capacity, kennel_over_limit,
                         kennel_slots, kittens_in_basket, next_area, occupied, unlock_area)
from core.odds import BreedOdds, breed_odds, iv_distribution
from core.prestige import (PrestigeInfo, prestige_info, prestige_level, prestige_reached,
                           update_prestige)
from core.rations import IvChoice, choice_from_dict, choice_to_dict
from core.run import Run, new_run, new_run_from_save
from core.runend import RunSettlement, close_run, run_earnings
from core.save import (SaveData, migrate_save_dict, new_game, read_save, save_from_dict,
                       save_to_dict, write_save)
from core.shop import (available_decorations, buy_decoration, buy_ration,
                       decoration_catalog, next_goal, ration_stock, rations_catalog)
from core.types import Cat, Content, Stage, Stats

__all__ = ["load_content", "roll_cat", "cat_stats", "Cat", "Content", "Stage", "Stats",
           "Run", "new_run", "new_run_from_save", "SaveData", "new_game", "save_to_dict",
           "save_from_dict", "write_save", "read_save", "rename_cat", "available_cats",
           "set_deck", "autofill_deck", "deck_cats", "get_cat", "save_deck_draft",
           "adoption_weights", "adoption_count", "donation_value", "create_adoption",
           "adopt", "donate_offer", "donate_cat", "can_donate", "has_pending_adoption",
           "RunAftermath", "advance_after_run", "breeding_status", "cancel_breed",
           "can_breed", "start_breed", "breed_cfg",
           # Fase 10a (economia, gatil, racao, odds, historico)
           "migrate_save_dict", "room_candidates", "can_start_breed", "initial_runs",
           "AreaStatus", "AreaUnlock", "area_status", "areas_status", "available_areas",
           "areas_blocked_by_coins", "areas_blocked_by_prestige", "unlock_area",
           "next_area", "can_adopt", "couples_allowed", "kennel_over_limit",
           "kennel_slots", "kennel_capacity", "kittens_in_basket", "occupied",
           "BreedOdds", "breed_odds", "iv_distribution", "IvChoice", "choice_from_dict",
           "choice_to_dict", "PrestigeInfo", "prestige_info", "prestige_level",
           "prestige_reached", "update_prestige", "RunSettlement", "close_run",
           "run_earnings", "available_decorations", "buy_decoration", "buy_ration",
           "decoration_catalog", "next_goal", "ration_stock", "rations_catalog"]
