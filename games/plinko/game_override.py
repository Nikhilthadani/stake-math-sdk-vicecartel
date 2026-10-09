"""Plinko game-state overrides — minimal, no special symbols needed."""

from game_executables import GameExecutables


class GameStateOverride(GameExecutables):

    def reset_book(self):
        """Reset per-simulation state."""
        super().reset_book()

    def assign_special_sym_function(self):
        """Plinko has no special symbols."""
        pass

    def check_game_repeat(self):
        """No special repeat conditions for base-game Plinko."""
        pass
