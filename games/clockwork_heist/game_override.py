from game_executables import GameExecutables
from game_config import WILD
from src.calculations.statistics import get_random_outcome
from src.state.books import Book

# Smallest payout increment Stake accepts, in payoutMultiplier units (bet x 100)
PAYOUT_STEP = 10


def copy_event(value):
    """Full copy of a JSON-like event (dicts, lists, tuples, scalars); `deepcopy` without its memo overhead."""
    if isinstance(value, dict):
        return {key: copy_event(item) for key, item in value.items()}
    if isinstance(value, list):
        return [copy_event(item) for item in value]
    if isinstance(value, tuple):
        return tuple(copy_event(item) for item in value)
    return value


class EventBook(Book):
    """`Book` whose events are copied with `copy_event`; `deepcopy` was over half of the simulation time."""

    def add_event(self, event: dict):
        self.events.append(copy_event(event))


class GameStateOverride(GameExecutables):
    """Overrides and extensions of the universal state.py functions."""

    def reset_book(self):
        super().reset_book()
        self.book = EventBook(self.book_id, self.criteria)
        self.locked_wilds = {}
        self.fs_summary = None

    def update_final_win(self) -> None:
        """Pays the round total rounded down to 0.1x: Stake accepts payout multipliers in steps of 10 (x100).

        The paytable has 0.05x steps (e.g. 0.15x, 1.25x), engine-clockwork pays them exactly.
        `exact_win` keeps the unrounded total; the cut comes off the free-spins share first.
        """
        super().update_final_win()
        self.exact_win = self.final_win
        cents = int(round(self.final_win * 100))
        cut = cents % PAYOUT_STEP
        if not cut:
            return
        free_cents = int(round(self.book.freegame_wins * 100))
        free_cut = min(cut, free_cents)
        self.final_win = (cents - cut) / 100
        self.book.payout_multiplier = self.final_win
        self.book.freegame_wins = (free_cents - free_cut) / 100
        self.book.basegame_wins = (int(round(self.book.basegame_wins * 100)) - (cut - free_cut)) / 100

    def assign_special_sym_function(self):
        self.special_symbol_functions = {WILD: [self.assign_mult_property]}

    def assign_mult_property(self, symbol) -> None:
        """Every wild that lands draws a 2x/3x/5x multiplier, in the base game and in free spins."""
        multiplier_value = get_random_outcome(self.get_current_distribution_conditions()["mult_values"][self.gametype])
        symbol.assign_attribute({"multiplier": multiplier_value})

    def check_repeat(self):
        super().check_repeat()
        if self.repeat is False:
            win_criteria = self.get_current_betmode_distributions().get_win_criteria()
            if win_criteria is None and self.final_win == 0:
                self.repeat = True
