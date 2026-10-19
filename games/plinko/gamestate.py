"""Plinko game state — one ball drop per simulation.

For every simulation the engine:
  1. Seeds the RNG (deterministic per simulation number).
  2. Generates `rows` fair coin flips (0 = left, 1 = right).
  3. The final slot is simply the count of rightward bounces.
  4. Looks up the multiplier for that slot.
  5. Emits a single plinkoResult event with the full path.
  6. In wheel modes, a wheel slot spins the wheel and multiplies the payout.
  7. Records the payout.
"""

import random
from game_override import GameStateOverride
from game_events import plinko_result_event, wheel_spin_event


class GameState(GameStateOverride):
    """Handle all game-logic for a single Plinko simulation."""

    def run_spin(self, sim, simulation_seed=None):
        self.reset_seed(sim)
        self.repeat = True

        while self.repeat:
            self.reset_book()

            # Current mode config (e.g. "12_medium" or "12_wheel")
            cfg = self.config.plinko[self.betmode]
            rows = cfg["rows"]

            # Fair 50/50 path — identical distribution to engine-plinko
            path = [random.randint(0, 1) for _ in range(rows)]
            final_slot = sum(path)
            multiplier = cfg["multipliers"][final_slot]

            plinko_result_event(
                self, path, final_slot, rows, cfg["risk"], multiplier
            )

            if final_slot in cfg["wheel_slots"]:
                multiplier = self.spin_wheel(final_slot, multiplier)

            # Update win manager
            self.win_manager.update_spinwin(multiplier)
            self.win_manager.update_gametype_wins(self.gametype)

            # Set payout and emit finalWin event
            self.evaluate_finalwin()

        self.imprint_wins()

    def spin_wheel(self, final_slot, base_multiplier):
        """Spin the wheel (equal segments) and return the boosted multiplier."""
        segments = self.config.wheel_segments
        segment = random.randrange(len(segments))
        wheel_value = segments[segment]
        multiplier = round(base_multiplier * wheel_value, 2)
        wheel_spin_event(self, final_slot, base_multiplier, segment, wheel_value, multiplier)
        return multiplier

    def run_freespin(self):
        """Plinko has no free spins."""
        pass
