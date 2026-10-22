from game_config import WILD
from src.calculations.statistics import get_random_outcome
from src.executables.executables import Executables


class GameCalculations(Executables):
    """Free-spins mechanics (sticky wilds, Gold Meter, minimum award) and the Max Win or Nothing vault grid."""

    def vault_doors(self) -> list:
        """Vault cells without a key, reel by reel, top to bottom (engine `emptyCells`)."""
        return [
            (reel, row)
            for reel in range(self.config.num_reels)
            for row in range(self.config.num_rows[reel])
            if (reel, row) not in self.vault
        ]

    def vault_land_key(self, cell: tuple) -> dict:
        """Puts a Vault Key with a drawn multiplier on `cell`; it stays for the rest of the round."""
        multiplier = get_random_outcome(self.config.max_win_or_nothing["mult_weights"])
        self.vault[cell] = multiplier
        return {"reel": cell[0], "row": cell[1], "multiplier": multiplier}

    def apply_sticky_wilds(self) -> None:
        """Locked cells show a wild with the multiplier it first landed with, whatever the reel stopped on."""
        for (reel, row), multiplier in self.locked_wilds.items():
            sym = self.symbol_storage.create_symbol(WILD)
            sym.assign_attribute({"multiplier": multiplier})
            self.board[reel][row] = sym
        self.get_special_symbols_on_board()

    def lock_new_wilds(self) -> list:
        """Locks every wild on an empty cell; each one is a Gold Meter key. Returns them reel by reel, top to bottom."""
        new_wilds = []
        for reel, column in enumerate(self.board):
            for row, sym in enumerate(column):
                if sym.name == WILD and (reel, row) not in self.locked_wilds:
                    self.locked_wilds[(reel, row)] = sym.multiplier
                    new_wilds.append({"reel": reel, "row": row, "multiplier": sym.multiplier})
        return new_wilds

    def update_gold_meter(self, keys_before: int) -> int:
        """Every `keys_per_award` keys add `spins_per_award` spins; extra keys carry over. Returns spins added."""
        per_award = self.config.free_spins["keys_per_award"]
        awards = len(self.locked_wilds) // per_award - keys_before // per_award
        spins_added = awards * self.config.free_spins["spins_per_award"]
        self.tot_fs += spins_added
        return spins_added

    def apply_min_award(self) -> tuple:
        """Tops session wins up to `min_award` unless the cap ended the session.

        The triggering spin's line win is paid on top and never counts toward the minimum.
        Returns (session win before top-up, top-up).
        """
        spins_win = round(self.win_manager.freegame_wins, 2)
        min_award = self.config.free_spins["min_award"]
        if self.wincap_triggered or spins_win >= min_award:
            return spins_win, 0.0
        top_up = round(min_award - spins_win, 2)
        self.win_manager.running_bet_win += top_up
        self.win_manager.freegame_wins += top_up
        return spins_win, top_up
