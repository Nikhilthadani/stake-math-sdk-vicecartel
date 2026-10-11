"""Vice Cartel — state overrides."""

import random
from game_executables import GameExecutables


class GameStateOverride(GameExecutables):

    def reset_book(self):
        super().reset_book()
        self.wild_reels: dict[int, int] = {}
        self.sticky_wilds: dict[int, int] = {}
        self.bonus_tier: str | None = None

    def assign_special_sym_function(self):
        self.special_symbol_functions = {}

    def evaluate_finalwin(self) -> None:
        """RGS pays rounds in 0.1x steps: floor the round total, taking the excess from freegame first."""
        wm = self.win_manager
        excess = (round(wm.running_bet_win * 100) % 10) / 100
        if excess > 0:
            from_free = min(excess, wm.freegame_wins)
            wm.freegame_wins = round(wm.freegame_wins - from_free, 2)
            wm.basegame_wins = round(wm.basegame_wins - (excess - from_free), 2)
            wm.running_bet_win = round(wm.running_bet_win - excess, 2)
        super().evaluate_finalwin()

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
        "normal_bonus":       {"spins": 10, "start_wilds": 0, "start_mult": 1},
        "super_bonus":        {"spins": 10, "start_wilds": 1, "start_mult": 2},
        "hidden_bonus":       {"spins": 12, "start_wilds": 2, "start_mult": 3},
        "super_hidden_bonus": {"spins": 12, "start_wilds": 3, "start_mult": 5},
    }

    def setup_bonus(self, tier: str) -> tuple[dict[int, int], int]:
        cfg = self.TIER_CONFIG[tier]
        self.bonus_tier = tier
        sticky: dict[int, int] = {}
        if cfg["start_wilds"] > 0:
            positions = random.sample(range(self.config.num_reels), cfg["start_wilds"])
            for reel in positions:
                sticky[reel] = cfg["start_mult"]
        return sticky, cfg["spins"]
