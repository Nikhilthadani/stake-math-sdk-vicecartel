"""Vice Cartel — state overrides."""

import os
import random
from game_executables import GameExecutables
from game_config import BONUS_TIERS


def raw_wins_dir(gamestate) -> str:
    return os.path.join(gamestate.output_files.library_path, "raw_wins")


class GameStateOverride(GameExecutables):

    def run_sims(self, betmode_copy_list, betmode, sim_to_criteria, total_threads, total_repeats, num_sims,
                 thread_index, repeat_count, compress=True, write_event_list=True, simulation_seeds=[]):
        """Also write each book's uncapped, unfloored round win; game_weights.py needs it for plain classes."""
        self.raw_wins: list[tuple[int, float]] = []
        super().run_sims(betmode_copy_list, betmode, sim_to_criteria, total_threads, total_repeats, num_sims,
                         thread_index, repeat_count, compress, write_event_list, simulation_seeds)
        os.makedirs(raw_wins_dir(self), exist_ok=True)
        path = os.path.join(raw_wins_dir(self), f"raw_{betmode}_{thread_index}_{repeat_count}.csv")
        with open(path, "w", encoding="UTF-8") as f:
            f.writelines(f"{book_id},{raw!r}\n" for book_id, raw in self.raw_wins)

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
        self.raw_round_win = wm.running_bet_win
        excess = (round(wm.running_bet_win * 100) % 10) / 100
        if excess > 0:
            from_free = min(excess, wm.freegame_wins)
            wm.freegame_wins = round(wm.freegame_wins - from_free, 2)
            wm.basegame_wins = round(wm.basegame_wins - (excess - from_free), 2)
            wm.running_bet_win = round(wm.running_bet_win - excess, 2)
        super().evaluate_finalwin()

    def setup_bonus(self, tier: str) -> tuple[dict[int, int], int]:
        """Initialise bonus state once from the tier table: fresh Wild positions, no carry-over."""
        cfg = BONUS_TIERS[tier]
        self.bonus_tier = tier
        sticky: dict[int, int] = {}
        for reel in random.sample(range(self.config.num_reels), cfg["start_wilds"]):
            sticky[reel] = cfg["start_mult"]
        return sticky, cfg["spins"]
