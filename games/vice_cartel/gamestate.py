"""Vice Cartel — main game state."""

from game_override import GameStateOverride
from game_events import update_freespin_event, freespin_end_event, survival_life_event


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

            self.draw_wild_board()
            self.evaluate_lines_with_wilds()
            self.evaluate_scatter_pay()
            self.win_manager.update_gametype_wins(self.gametype)

            conds = self.get_current_distribution_conditions()
            if conds.get("force_freegame"):
                outcome = self._forced_mystery_outcome()
                self.triggered_freegame = True
                self.run_bonus(outcome)
            else:
                outcome = self.check_mystery_trigger()
                if outcome and outcome != "no_bonus":
                    self.triggered_freegame = True
                    self.run_bonus(outcome)

            self.evaluate_finalwin()
            self.check_repeat()
        self.imprint_wins()

    def run_bonus(self, tier: str) -> None:
        self.gametype = self.config.freegame_type
        sticky_wilds, turns_left = self.setup_bonus(tier)
        while turns_left > 0 and not self.get_wincap_triggered():
            self.win_manager.reset_spin_win()
            self.win_data = {}
            update_freespin_event(self)
            sticky_wilds, turns_left = self.resolve_wheel(sticky_wilds, turns_left)
            self.run_bonus_spin(sticky_wilds)
            self.win_manager.update_gametype_wins(self.gametype)
            if self.bonus_mode == "survival":
                if self.is_dead_spin(len(sticky_wilds)):
                    self.lives -= 1
                    survival_life_event(self, self.lives, lost=True)
                    if self.lives <= 0:
                        break
            else:
                turns_left -= 1
        freespin_end_event(self)
        self.gametype = self.config.basegame_type

    def run_freespin(self):
        pass

    def _forced_mystery_outcome(self) -> str:
        from src.calculations.statistics import get_random_outcome
        from game_config import MYSTERY_OUTCOME_WEIGHTS
        from game_events import mystery_trigger_event
        tier_weights = {k: v for k, v in MYSTERY_OUTCOME_WEIGHTS.items() if k != "no_bonus"}
        outcome = get_random_outcome(tier_weights)
        mystery_trigger_event(self, outcome)
        self.record({"kind": "mystery", "outcome": outcome, "gametype": self.gametype})
        return outcome
