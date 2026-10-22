import random

from game_override import GameStateOverride
from game_events import (
    gold_meter_event,
    min_award_event,
    reveal_event,
    set_total_event,
    vault_end_event,
    vault_respin_event,
    vault_start_event,
)


class GameState(GameStateOverride):
    """Game logic and events for a single simulation number/game round."""

    def run_spin(self, sim, simulation_seed=None):
        self.reset_seed(sim)
        self.repeat = True
        while self.repeat:
            self.reset_book()
            if self.betmode == "mwon":
                self.run_mwon()
                self.check_repeat()
                continue

            # base: BR0 board (forced 3-scatter board for the `freegame` criteria);
            # bonus: BUY board, which always shows the trigger and never pays
            self.draw_board()
            self.evaluate_lines_board()
            if self.betmode == "bonus" and self.win_manager.spin_win != 0:
                raise RuntimeError(f"Buy reels paid {self.win_manager.spin_win} at stops {self.reel_positions}")
            self.win_manager.update_gametype_wins(self.gametype)

            if self.check_fs_condition() and self.check_freespin_entry() and not self.wincap_triggered:
                self.run_freespin_from_base()

            self.evaluate_finalwin()
            self.check_repeat()
        self.imprint_wins()

    def run_mwon(self):
        """Max Win or Nothing (engine `playVault`): the Sticky Wild Vault hold & respin on the 5 x 4 grid.

        - `start_keys` Vault Keys land on random cells, each with a multiplier.
        - On each respin every empty cell lands a key with `land_probability`; keys stick.
        - Respins start at `respins`; a respin that lands a key resets them, one that lands none
          uses one up. The round ends at 0 respins or a full grid.
        - A full grid pays the flat `win_amount` (max win); otherwise the sum of all key
          multipliers, at least `min_award`.

        Rounds play naturally. The book's criteria is the outcome class (`wincap` = full grid,
        `basegame` = any other), so `check_repeat` plays a round of the other class again; the
        lookup weights carry the jackpot probability (run.py `set_mwon_weights`).
        """
        settings = self.config.max_win_or_nothing
        for _ in range(settings["start_keys"]):
            self.vault_land_key(random.choice(self.vault_doors()))
        respins_left = settings["respins"]
        vault_start_event(self, respins_left)

        respins = 0
        doors = self.vault_doors()
        while respins_left > 0 and doors:
            new_keys = [self.vault_land_key(cell) for cell in doors if random.random() < settings["land_probability"]]
            doors = self.vault_doors()
            respins += 1
            respins_left = 0 if not doors else settings["respins"] if new_keys else respins_left - 1
            vault_respin_event(self, respins, new_keys, respins_left)

        full = not doors
        multiplier_sum = sum(self.vault.values())
        min_award_applied = not full and multiplier_sum < settings["min_award"]
        win = min(settings["win_amount"], self.config.wincap) if full else max(multiplier_sum, settings["min_award"])
        self.vault_summary = {"full": full, "keys": len(self.vault), "respins": respins,
                              "multiplier_sum": multiplier_sum, "min_award_applied": min_award_applied}
        self.win_manager.update_spinwin(win)
        self.win_manager.update_gametype_wins(self.gametype)
        vault_end_event(self, respins, full, multiplier_sum, min_award_applied, win)
        self.evaluate_wincap()
        set_total_event(self)
        self.evaluate_finalwin()

    def run_freespin(self):
        """Free-spins session on FR0 with sticky wilds and the Gold Meter (engine `playFreeSpins`).

        - Every wild that lands stays locked, with its multiplier, for the rest of the session.
        - Each wild landing on an empty cell is a key; every 5 keys add 3 spins (extra keys carry over).
        - The round total is capped after every spin; reaching 25,000x ends the session.
        - Session wins below 10x are topped up to 10x at the end (not when capped).
        """
        self.reset_fs_spin()
        self.locked_wilds = {}
        spin_wins = []

        while self.fs < self.tot_fs and not self.wincap_triggered:
            self.update_freespin()
            self.draw_board(emit_event=False)
            self.apply_sticky_wilds()
            reveal_event(self)

            keys_before = len(self.locked_wilds)
            new_wilds = self.lock_new_wilds()
            spins_added = self.update_gold_meter(keys_before)
            gold_meter_event(self, new_wilds, spins_added)

            self.evaluate_lines_board()
            self.win_manager.update_gametype_wins(self.gametype)
            spin_wins.append(self.win_manager.spin_win)

        spins_win, top_up = self.apply_min_award()
        if top_up > 0:
            min_award_event(self, spins_win, top_up)
            set_total_event(self)
        self.end_freespin()

        self.fs_summary = {
            "spins": len(spin_wins),
            "keys": len(self.locked_wilds),
            "spin_wins": spin_wins,
            "raw_win": spins_win,
            "top_up": top_up,
            "capped": self.wincap_triggered,
        }
