"""Vice Cartel — main game state (round order follows vc_math/vice_cartel_math/engine.py)."""

from game_override import GameStateOverride
from game_config import EXTRA_CHANCE_UPLIFT, TIER_BY_SCATTERS, BUY_BONUS_TIER, BONUS_TIERS
from game_events import update_freespin_event, freespin_end_event, bonus_trigger_event, bonus_start_event

_SCATTER_UPLIFT: dict[str, float] = {"base": 1.0, "extra_chance": EXTRA_CHANCE_UPLIFT}
_BONUS_SPIN_SAFETY_LIMIT = 200
# Distinct RNG streams per mode, so modes sharing book classes never get identical books
_MODE_SEED_OFFSET: dict[str, int] = {
    "base": 0, "extra_chance": 10**9, "bonus_normal": 2 * 10**9, "bonus_super": 3 * 10**9,
    "min2wild": 4 * 10**9, "golden_case": 5 * 10**9,
}


class GameState(GameStateOverride):

    def run_spin(self, sim, simulation_seed=None):
        self.reset_seed(sim, seed_override=_MODE_SEED_OFFSET[self.betmode] + sim)
        self.repeat = True
        while self.repeat:
            self.reset_book()

            if self.in_mode("golden_case"):
                self.run_golden_case()
            elif self.in_mode("min2wild"):
                self.run_min2wild()
            elif self.betmode in BUY_BONUS_TIER:
                self.triggered_freegame = True
                self.run_bonus(BUY_BONUS_TIER[self.betmode])
            else:
                self.run_base(_SCATTER_UPLIFT[self.betmode])

            self.evaluate_finalwin()
            self.check_repeat()
        if hasattr(self, "raw_wins"):
            self.raw_wins.append((self.book.id, self.raw_round_win))
        self.imprint_wins()

    def run_base(self, scatter_uplift: float) -> None:
        scatters = self.draw_base_board(scatter_uplift)
        if self.is_five_wilds():
            self.award_five_wilds()
            self.win_manager.update_gametype_wins(self.gametype)
            return
        self.evaluate_lines_with_wilds()
        self.evaluate_scatter_pay()
        self.win_manager.update_gametype_wins(self.gametype)

        tier = TIER_BY_SCATTERS.get(scatters)
        if tier is not None and not self.get_wincap_triggered():
            self.triggered_freegame = True
            bonus_trigger_event(self, tier, scatters)
            self.record({"kind": "bonus", "tier": tier, "gametype": self.gametype})
            self.run_bonus(tier)

    def run_min2wild(self) -> None:
        self.draw_min2wild_board()
        if self.is_five_wilds():
            self.award_five_wilds()
        else:
            self.evaluate_lines_with_wilds()
        self.win_manager.update_gametype_wins(self.gametype)

    def run_bonus(self, tier: str) -> None:
        self.gametype = self.config.freegame_type
        sticky_wilds, turns_left = self.setup_bonus(tier)
        self.tot_fs = BONUS_TIERS[tier]["spins"]
        bonus_start_event(self, tier, turns_left, sticky_wilds)
        spin_count = 0
        while turns_left > 0 and not self.get_wincap_triggered() and spin_count < _BONUS_SPIN_SAFETY_LIMIT:
            self.win_manager.reset_spin_win()
            self.win_data = {}
            spin_count += 1
            self.fs = spin_count
            update_freespin_event(self)
            sticky_wilds, turns_left, max_win = self.resolve_wheel(tier, sticky_wilds, turns_left)
            if max_win:
                self.award_five_wilds()
                self.win_manager.update_gametype_wins(self.gametype)
                break
            self.run_bonus_spin(sticky_wilds)
            self.win_manager.update_gametype_wins(self.gametype)
            turns_left -= 1
        freespin_end_event(self)
        self.gametype = self.config.basegame_type

    def run_freespin(self):
        pass
