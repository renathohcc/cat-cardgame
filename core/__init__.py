"""Core do jogo: regras puras, sem pygame."""
from core.adoption import (adopt, adoption_count, adoption_weights, create_adoption,
                           can_donate, donate_cat, donate_offer, donation_value,
                           has_pending_adoption)
from core.cats import cat_stats, roll_cat
from core.collection import (autofill_deck, available_cats, deck_cats, get_cat,
                             rename_cat, save_deck_draft, set_deck)
from core.content import load_content
from core.run import Run, new_run, new_run_from_save
from core.save import (SaveData, new_game, read_save, save_from_dict, save_to_dict,
                       write_save)
from core.types import Cat, Content, Stage, Stats

__all__ = ["load_content", "roll_cat", "cat_stats", "Cat", "Content", "Stage", "Stats",
           "Run", "new_run", "new_run_from_save", "SaveData", "new_game", "save_to_dict",
           "save_from_dict", "write_save", "read_save", "rename_cat", "available_cats",
           "set_deck", "autofill_deck", "deck_cats", "get_cat", "save_deck_draft",
           "adoption_weights", "adoption_count", "donation_value", "create_adoption",
           "adopt", "donate_offer", "donate_cat", "can_donate", "has_pending_adoption"]
