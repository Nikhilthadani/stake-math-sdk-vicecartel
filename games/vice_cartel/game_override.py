"""Vice Cartel — state overrides."""

import random
from game_executables import GameExecutables
from game_events import bonus_choice_event, survival_life_event


class GameStateOverride(GameExecutables):

    def reset_book(self):
        super().reset_book()
        self.wild_reels: dict[int, int] = {}
        self.sticky_wilds: dict[int, int] = {}
        self.bonus_tier: str | None = None
        self.bonus_mode: str | None = None
        self.lives = 0

    def assign_special_sym_function(self):
        self.special_symbol_functions = {}

    def check_repeat(self):
        if self.repeat is False:
            win_criteria = self.get_current_betmode_distributions().get_win_criteria()
            if win_criteria is not None and self.final_win != win_criteria:
                self.repeat = True
                return
            conds = self.get_current_distribution_conditions()
            if conds.get("force_freegame") and not self.triggered_freegame:
                self.repeat = True
                return
        self.repeat_count += 1
        self.check_current_repeat_count()

    TIER_CONFIG: dict[str, dict] = {
        "normal_bonus":       {"spins": 10, "start_wilds": 0, "start_mult": 1, "has_choice": False},
        "super_bonus":        {"spins": 10, "start_wilds": 1, "start_mult": 2, "has_choice": False},
        "hidden_bonus":       {"spins": 12, "start_wilds": 2, "start_mult": 3, "has_choice": True, "lives": 5},
        "super_hidden_bonus": {"spins": 12, "start_wilds": 3, "start_mult": 5, "has_choice": True, "lives": 5},
    }

    def setup_bonus(self, tier: str) -> tuple[dict[int, int], int]:
        cfg = self.TIER_CONFIG[tier]
        self.bonus_tier = tier
        sticky: dict[int, int] = {}
        if cfg["start_wilds"] > 0:
            positions = random.sample(range(self.config.num_reels), cfg["start_wilds"])
            for reel in positions:
                sticky[reel] = cfg["start_mult"]
        if cfg["has_choice"]:
            self.bonus_mode = random.choice(["spins", "survival"])
            bonus_choice_event(self, self.bonus_mode)
            if self.bonus_mode == "survival":
                self.lives = cfg["lives"]
                return sticky, 999
        else:
            self.bonus_mode = "spins"
        return sticky, cfg["spins"]
