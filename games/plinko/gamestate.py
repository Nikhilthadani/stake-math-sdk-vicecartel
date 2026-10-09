"""Plinko game state — one ball drop per simulation.

For every simulation the engine:
  1. Seeds the RNG (deterministic per simulation number).
  2. Generates `rows` fair coin flips (0 = left, 1 = right).
  3. The final slot is simply the count of rightward bounces.
  4. Looks up the multiplier for that slot.
  5. Emits a single plinkoResult event with the full path.
  6. Records the payout.
"""

import random
from game_override import GameStateOverride
from game_events import plinko_result_event


class GameState(GameStateOverride):
    """Handle all game-logic for a single Plinko simulation."""

    def run_spin(self, sim, simulation_seed=None):
        self.reset_seed(sim)
        self.repeat = True

        while self.repeat:
            self.reset_book()

            # Current mode config (e.g. "12_medium")
            cfg = self.config.plinko[self.betmode]
            rows = cfg["rows"]
            multipliers = cfg["multipliers"]

            # Fair 50/50 path — identical distribution to engine-plinko
            path = [random.randint(0, 1) for _ in range(rows)]
            final_slot = sum(path)
            multiplier = multipliers[final_slot]

            # Update win manager
            self.win_manager.update_spinwin(multiplier)
            self.win_manager.update_gametype_wins(self.gametype)

            # Emit result event
            plinko_result_event(
                self, path, final_slot, rows, cfg["risk"], multiplier
            )

            # Set payout and emit finalWin event
            self.evaluate_finalwin()

        self.imprint_wins()

    def run_freespin(self):
        """Plinko base game has no free spins."""
        pass
