"""Vice Cartel — executable game actions (calculation + event emission)."""

import random as _rng
from game_calculations import GameCalculations
from game_config import MYSTERY_TRIGGER_PROB, MIN2WILD_EXTRA_PROB_200X, MIN2WILD_EXTRA_PROB_250X
from game_events import (
    reveal_event, wild_reel_event, spin_multiplier_event, scatter_pay_event,
    mystery_trigger_event, wheel_spin_event, sticky_wild_update_event,
    golden_case_reveal_event, win_info_event, set_win_event, set_total_event,
    update_freespin_event, freespin_end_event, wincap_event,
)
from src.calculations.lines import Lines


class GameExecutables(GameCalculations):

    def draw_wild_board(self) -> None:
        """Draw board with per-reel Wild probability."""
        self.wild_reels: dict[int, int] = {}
        self.create_board_reelstrips()
        for reel in range(self.config.num_reels):
            if self.is_reel_wild():
                mult = self.draw_wild_multiplier()
                self.wild_reels[reel] = mult
                for row in range(self.config.num_rows[reel]):
                    self.board[reel][row] = self.symbol_storage.create_symbol("W")
                wild_reel_event(self, reel, mult)
        reveal_event(self)

    def draw_min2wild_board(self, extra_wild_prob: float) -> None:
        """Force 2 Wild reels + roll extra-wild on remaining 3. No mystery/bonus."""
        self.wild_reels: dict[int, int] = {}
        self.create_board_reelstrips()
        forced = _rng.sample(range(self.config.num_reels), 2)
        for reel in forced:
            self.wild_reels[reel] = self.draw_wild_multiplier()
        for reel in range(self.config.num_reels):
            if reel not in forced and _rng.random() < extra_wild_prob:
                self.wild_reels[reel] = self.draw_wild_multiplier()
        for reel, mult in self.wild_reels.items():
            for row in range(self.config.num_rows[reel]):
                self.board[reel][row] = self.symbol_storage.create_symbol("W")
            wild_reel_event(self, reel, mult)
        reveal_event(self)

    def evaluate_lines_with_wilds(self) -> None:
        """Evaluate all 14 paylines, apply combined Wild multiplier."""
        spin_mult = self.compute_spin_multiplier(self.wild_reels)
        if spin_mult > 1:
            spin_multiplier_event(self, spin_mult)
        self.win_data = self.evaluate_lines(self.board, self.config)
        raw_win = self.win_data["totalWin"]
        boosted_win = round(raw_win * spin_mult, 2)
        self.win_data["totalWin"] = boosted_win
        for w in self.win_data["wins"]:
            w["win"] = round(w["win"] * spin_mult, 2)
        Lines.record_lines_wins(self)
        self.win_manager.update_spinwin(boosted_win)
        if boosted_win > 0:
            win_info_event(self)
            self.evaluate_wincap()
            set_win_event(self)
        set_total_event(self)

    def evaluate_scatter_pay(self) -> None:
        count = self.count_scatter(self.board, self.config.num_reels, self.config.num_rows)
        payout = self.get_scatter_payout(count, self.config.scatter_pay)
        if payout > 0:
            self.win_manager.update_spinwin(payout)
            scatter_pay_event(self, count, payout)

    def check_mystery_trigger(self, trigger_prob: float | None = None) -> str | None:
        prob = trigger_prob if trigger_prob is not None else MYSTERY_TRIGGER_PROB
        outcome = self.mystery_check(prob)
        if outcome and outcome != "no_bonus":
            mystery_trigger_event(self, outcome)
            self.record({"kind": "mystery", "outcome": outcome, "gametype": self.gametype})
        return outcome

    def resolve_wheel(self, sticky_wilds: dict[int, int], turns_left: int) -> tuple[dict[int, int], int]:
        if not self.wheel_triggers():
            return sticky_wilds, turns_left
        segment = self.wheel_segment()
        if segment == "RED":
            empty = [r for r in range(self.config.num_reels) if r not in sticky_wilds]
            count = min(self.red_wild_count(), len(empty))
            chosen = _rng.sample(empty, count) if count > 0 else []
            for reel in chosen:
                sticky_wilds[reel] = self.draw_wild_multiplier()
            wheel_spin_event(self, "RED", {"newWilds": {str(r): sticky_wilds[r] for r in chosen}})
        elif segment == "BLUE":
            if sticky_wilds:
                target = _rng.choice(list(sticky_wilds.keys()))
                inc = self.blue_increment()
                sticky_wilds[target] += inc
                wheel_spin_event(self, "BLUE", {"reel": target, "increment": inc, "newMult": sticky_wilds[target]})
        elif segment == "YELLOW":
            extra = self.yellow_extra_turns()
            turns_left += extra
            wheel_spin_event(self, "YELLOW", {"extraTurns": extra})
        sticky_wild_update_event(self, sticky_wilds)
        return sticky_wilds, turns_left

    def run_bonus_spin(self, sticky_wilds: dict[int, int]) -> None:
        self.create_board_reelstrips()
        for reel, mult in sticky_wilds.items():
            for row in range(self.config.num_rows[reel]):
                self.board[reel][row] = self.symbol_storage.create_symbol("W")
        reveal_event(self)
        spin_mult = self.compute_spin_multiplier(sticky_wilds)
        if spin_mult > 1:
            spin_multiplier_event(self, spin_mult)
        self.win_data = self.evaluate_lines(self.board, self.config)
        raw_win = self.win_data["totalWin"]
        boosted_win = round(raw_win * spin_mult, 2)
        self.win_data["totalWin"] = boosted_win
        for w in self.win_data["wins"]:
            w["win"] = round(w["win"] * spin_mult, 2)
        Lines.record_lines_wins(self)
        self.win_manager.update_spinwin(boosted_win)
        if boosted_win > 0:
            win_info_event(self)
            self.evaluate_wincap()
            set_win_event(self)
        set_total_event(self)

    def run_golden_case(self) -> None:
        hits, is_win = self.golden_case_spin()
        golden_case_reveal_event(self, hits, is_win)
        if is_win:
            self.win_manager.update_spinwin(self.config.wincap)
            set_win_event(self)
        set_total_event(self)
