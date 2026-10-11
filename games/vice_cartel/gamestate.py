"""Vice Cartel — main game state."""

from game_override import GameStateOverride
from game_config import MIN2WILD_EXTRA_PROB_200X, MIN2WILD_EXTRA_PROB_250X, MYSTERY_OUTCOME_WEIGHTS
from game_events import update_freespin_event, freespin_end_event, mystery_trigger_event
from src.calculations.statistics import get_random_outcome

_BONUS_TIER_WEIGHTS = {k: v for k, v in MYSTERY_OUTCOME_WEIGHTS.items() if k != "no_bonus"}

# Mode → extra-wild probability for Min 2 Wild
_MIN2WILD_EXTRA_PROB: dict[str, float] = {
    "min2wild_200x": MIN2WILD_EXTRA_PROB_200X,
    "min2wild_250x": MIN2WILD_EXTRA_PROB_250X,
}


class GameState(GameStateOverride):

    def run_spin(self, sim, simulation_seed=None):
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            self.reset_book()

            if self.in_mode("golden_case"):
                self.run_golden_case()
                self.evaluate_finalwin()
                self.repeat = False
                break

            if self.betmode in _MIN2WILD_EXTRA_PROB:
                self.draw_min2wild_board(_MIN2WILD_EXTRA_PROB[self.betmode])
                self.evaluate_lines_with_wilds()
                self.evaluate_scatter_pay()
                self.win_manager.update_gametype_wins(self.gametype)
                self.evaluate_finalwin()
                self.repeat = False
                break

            self.draw_wild_board()
            self.evaluate_lines_with_wilds()
            self.evaluate_scatter_pay()
            self.win_manager.update_gametype_wins(self.gametype)

            # Bonuses live only in the "freegame" criteria; its frequency is set by the optimizer
            if self.get_current_distribution_conditions().get("force_freegame"):
                self.triggered_freegame = True
                self.run_bonus(self._forced_mystery_outcome())

            self.evaluate_finalwin()
            self.check_repeat()
        self.imprint_wins()

    def run_bonus(self, tier: str) -> None:
        self.gametype = self.config.freegame_type
        sticky_wilds, turns_left = self.setup_bonus(tier)
        spin_count = 0
        max_spins = 200  # safety cap — PAR avg is 12-16 spins
        while turns_left > 0 and not self.get_wincap_triggered() and spin_count < max_spins:
            self.win_manager.reset_spin_win()
            self.win_data = {}
            spin_count += 1
            update_freespin_event(self)
            sticky_wilds, turns_left = self.resolve_wheel(sticky_wilds, turns_left)
            self.run_bonus_spin(sticky_wilds)
            self.win_manager.update_gametype_wins(self.gametype)
            turns_left -= 1
        freespin_end_event(self)
        self.gametype = self.config.basegame_type

    def run_freespin(self):
        pass

    def _forced_mystery_outcome(self) -> str:
        outcome = get_random_outcome(_BONUS_TIER_WEIGHTS)
        mystery_trigger_event(self, outcome)
        self.record({"kind": "mystery", "outcome": outcome, "gametype": self.gametype})
        return outcome
