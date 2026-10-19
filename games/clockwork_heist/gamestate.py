from game_override import GameStateOverride
from game_events import gold_meter_event, min_award_event, mwon_result_event, reveal_event, set_total_event
from src.calculations.lines import Lines


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
        """Max Win or Nothing (engine `playMaxWinOrNothing`).

        The book's criteria is the outcome (`wincap` = win, `0` = lose); the lookup-table
        weights carry the win probability. The screen is drawn to match: a win pays the flat
        prize on the first 5-of-a-kind line (x1, never the paytable); a loss pays nothing.
        """
        is_win = self.criteria == "wincap"
        line_wins = self.draw_mwon_presentation(is_win)
        reveal_event(self)

        prize = min(self.config.max_win_or_nothing["win_amount"], self.config.wincap) if is_win else 0.0
        mwon_result_event(self, is_win, prize)

        if is_win:
            five = next(w for w in line_wins if w["kind"] == 5)
            five["win"] = prize
            five["meta"].update({"multiplier": 1, "winWithoutMult": prize, "lineMultiplier": 1})
            self.win_data = {"totalWin": prize, "wins": [five]}
            Lines.record_lines_wins(self)
        else:
            self.win_data = {"totalWin": 0.0, "wins": []}
        self.win_manager.update_spinwin(prize)
        self.emit_linewin_events()
        self.win_manager.update_gametype_wins(self.gametype)
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
