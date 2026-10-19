from game_calculations import GameCalculations
from game_config import WILD
from src.calculations.lines import Lines
from src.events.events import fs_trigger_event, set_total_event, set_win_event, win_info_event


class GameExecutables(GameCalculations):

    def update_freespin_amount(self, scatter_key: str = "scatter") -> None:
        """Base trigger only (free spins never retrigger); the SDK version shifts scatter rows for padding."""
        self.tot_fs = self.config.freespin_triggers[self.gametype][self.count_special_symbols(scatter_key)]
        fs_trigger_event(
            self,
            include_padding_index=self.config.include_padding,
            basegame_trigger=True,
            freegame_trigger=False,
        )

    def evaluate_lines_board(self):
        """Line wins left to right; wild multipliers on a winning run add up (2x + 3x = 5x), no wild pays x1."""
        self.win_data = Lines.get_lines(
            self.board,
            self.config,
            wild_key="wild",
            wild_sym=WILD,
            multiplier_method="symbol",
            global_multiplier=self.global_multiplier,
        )
        Lines.record_lines_wins(self)
        self.win_manager.update_spinwin(self.win_data["totalWin"])
        self.emit_linewin_events()

    def emit_linewin_events(self):
        """`Lines.emit_linewin_events` always shifts rows by one for padding; this board has none."""
        if self.win_manager.spin_win > 0:
            win_info_event(self, include_padding_index=self.config.include_padding)
            self.evaluate_wincap()
            set_win_event(self)
        set_total_event(self)
