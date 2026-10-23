"""Vice Cartel — executable game actions (calculation + event emission)."""

import random as _rng
from game_calculations import GameCalculations
from game_config import MAX_WILD_REELS_FROM_RED, MIN2WILD_EXTRA_PROB
from game_events import (
    reveal_event, wild_reel_event, spin_multiplier_event, scatter_pay_event,
    wheel_spin_event, sticky_wild_update_event, golden_case_reveal_event,
    five_wilds_event, win_info_event, set_win_event, set_total_event,
)
from src.calculations.lines import Lines


class GameExecutables(GameCalculations):

    def _draw_independent_board(self) -> None:
        """Draw 4 independent symbols per reel from the strip (each row draws independently)."""
        self.refresh_special_syms()
        self.reelstrip = self.config.reels["BR0"]
        self.reel_positions = [0] * self.config.num_reels
        self.anticipation = [0] * self.config.num_reels
        for reel in range(self.config.num_reels):
            strip = self.reelstrip[reel]
            for row in range(self.config.num_rows[reel]):
                sym_id = strip[_rng.randrange(len(strip))]
                self.board[reel][row] = self.symbol_storage.create_symbol(sym_id)

    def _apply_wild_reels(self) -> None:
        for reel, mult in self.wild_reels.items():
            for row in range(self.config.num_rows[reel]):
                self.board[reel][row] = self.symbol_storage.create_symbol("W")
            wild_reel_event(self, reel, mult)

    def _place_scatters(self, count: int) -> int:
        """Place `count` Scatters uniformly on cells of non-Wild reels; clamped to the free cells."""
        free = [
            (reel, row)
            for reel in range(self.config.num_reels) if reel not in self.wild_reels
            for row in range(self.config.num_rows[reel])
        ]
        count = min(count, len(free))
        for reel, row in _rng.sample(free, count):
            self.board[reel][row] = self.symbol_storage.create_symbol("SC")
        return count

    def is_five_wilds(self) -> bool:
        return len(self.wild_reels) == self.config.num_reels

    def _draw_forced_wild_reels(self, count: int, mult_range: tuple[int, int] | None) -> dict[int, int]:
        """`count` Wild reels on uniformly chosen reels; multipliers drawn given their sum range."""
        reels = sorted(_rng.sample(range(self.config.num_reels), count))
        if mult_range is None:
            mults = [self.draw_wild_multiplier() for _ in reels]
        else:
            mults = self.draw_wild_multipliers_in_range(count, *mult_range)
        return dict(zip(reels, mults))

    def _draw_natural_wild_reels(self) -> dict[int, int]:
        return {
            reel: self.draw_wild_multiplier()
            for reel in range(self.config.num_reels) if self.is_reel_wild()
        }

    def draw_base_board(self, scatter_uplift: float) -> int:
        """Base / Extra Chance board. Returns the Scatter count placed (0 on five Wilds).

        Book classes (distribution conditions) may force the outcome: five_wilds, wild_count with an
        optional mult_range, and scatters ("plain" or a trigger count). Without them the draw is natural.
        """
        force = self.get_current_distribution_conditions()
        if force.get("five_wilds"):
            self.wild_reels = self._draw_forced_wild_reels(self.config.num_reels, None)
        elif "wild_count" in force:
            self.wild_reels = self._draw_forced_wild_reels(force["wild_count"], force.get("mult_range"))
        else:
            self.wild_reels = self._draw_natural_wild_reels()
            while "scatters" in force and self.is_five_wilds():
                self.wild_reels = self._draw_natural_wild_reels()
        self._draw_independent_board()
        scatters = 0
        if not self.is_five_wilds():
            scatters = self._place_scatters(self.draw_scatter_count(scatter_uplift, force.get("scatters")))
        self._apply_wild_reels()
        reveal_event(self)
        return scatters

    def draw_min2wild_board(self) -> None:
        """Force 2 Wild reels + roll extra-wild on the remaining 3. No Scatters, no wheel, no bonus.

        A book class may force the Wild-reel count (wild_count) and the multiplier-sum range.
        """
        force = self.get_current_distribution_conditions()
        self._draw_independent_board()
        if "wild_count" in force:
            self.wild_reels = self._draw_forced_wild_reels(force["wild_count"], force.get("mult_range"))
        else:
            self.wild_reels = {}
            forced = _rng.sample(range(self.config.num_reels), 2)
            for reel in range(self.config.num_reels):
                if reel in forced or _rng.random() < MIN2WILD_EXTRA_PROB:
                    self.wild_reels[reel] = self.draw_wild_multiplier()
        self._apply_wild_reels()
        reveal_event(self)

    def award_five_wilds(self) -> None:
        """Five Wilds: the round total becomes exactly the max win and the round ends."""
        five_wilds_event(self)
        self.record({"kind": "fiveWilds", "gametype": self.gametype})
        self.win_manager.update_spinwin(self.config.wincap - self.win_manager.running_bet_win)
        self.evaluate_wincap()
        set_total_event(self)

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
            self.evaluate_wincap()

    def resolve_wheel(self, tier: str, sticky_wilds: dict[int, int], turns_left: int) -> tuple[dict[int, int], int, bool]:
        """Spin the bonus wheel (if it triggers). Returns (sticky_wilds, turns_left, max_win_hit)."""
        if not self.wheel_triggers(tier):
            return sticky_wilds, turns_left, False
        segment = self.wheel_segment(tier)
        if segment == "MAX_WIN":
            wheel_spin_event(self, "MAX_WIN", {})
            return sticky_wilds, turns_left, True
        if segment == "RED":
            empty = [r for r in range(self.config.num_reels) if r not in sticky_wilds]
            count = min(self.red_wild_count(), MAX_WILD_REELS_FROM_RED - len(sticky_wilds))
            chosen = _rng.sample(empty, count) if count > 0 else []
            for reel in chosen:
                sticky_wilds[reel] = self.draw_wild_multiplier()
            wheel_spin_event(self, "RED", {"newWilds": {str(r): sticky_wilds[r] for r in chosen}})
        elif segment == "BLUE":
            if sticky_wilds:
                target = _rng.choice(sorted(sticky_wilds))
                inc = self.blue_increment()
                sticky_wilds[target] += inc
                wheel_spin_event(self, "BLUE", {"reel": target, "increment": inc, "newMult": sticky_wilds[target]})
            else:
                wheel_spin_event(self, "BLUE", {})
        elif segment == "YELLOW":
            extra = self.yellow_extra_turns()
            turns_left += extra
            self.tot_fs += extra
            wheel_spin_event(self, "YELLOW", {"extraTurns": extra})
        sticky_wild_update_event(self, sticky_wilds)
        return sticky_wilds, turns_left, False

    def run_bonus_spin(self, sticky_wilds: dict[int, int]) -> None:
        self._draw_independent_board()
        for reel in sticky_wilds:
            for row in range(self.config.num_rows[reel]):
                self.board[reel][row] = self.symbol_storage.create_symbol("W")
        reveal_event(self)
        self.wild_reels = sticky_wilds
        self.evaluate_lines_with_wilds()

    def run_golden_case(self) -> None:
        letters, is_win = self.golden_case_spin()
        golden_case_reveal_event(self, letters, is_win)
        if is_win:
            self.win_manager.update_spinwin(self.config.wincap)
            set_win_event(self)
        self.win_manager.update_gametype_wins(self.gametype)
        set_total_event(self)
