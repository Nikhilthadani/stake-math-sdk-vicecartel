"""Plinko game configuration for Stake Engine.

Ports the base-game multiplier tables from engine-plinko.
Each (rows, risk) combination becomes a separate BetMode.
"""

from math import comb
from src.config.config import Config, BetMode
from src.config.distributions import Distribution


# ─── Row and risk options ─────────────────────────────────────────────────────

ROWS = [8, 9, 10, 11, 12, 13, 14, 15, 16]
RISKS = ["low", "medium", "high"]


# ─── Base-game multiplier tables (exact copy from engine-plinko) ──────────────
# Index = final slot (number of rightward bounces, 0 … rows).

BASE_MULTIPLIERS = {
    8: {
        "low":    [5.51, 2.05, 1.07, 0.98, 0.49, 0.98, 1.07, 2.05, 5.51],
        "medium": [12.73, 2.95, 1.26, 0.69, 0.39, 0.69, 1.26, 2.95, 12.73],
        "high":   [28.3, 3.9, 1.47, 0.29, 0.2, 0.29, 1.47, 3.9, 28.3],
    },
    9: {
        "low":    [5.47, 1.98, 1.57, 0.98, 0.68, 0.68, 0.98, 1.57, 1.98, 5.47],
        "medium": [17.56, 3.91, 1.65, 0.88, 0.49, 0.49, 0.88, 1.65, 3.91, 17.56],
        "high":   [42.04, 6.85, 1.95, 0.58, 0.2, 0.2, 0.58, 1.95, 6.85, 42.04],
    },
    10: {
        "low":    [8.72, 2.93, 1.37, 1.07, 0.98, 0.49, 0.98, 1.07, 1.37, 2.93, 8.72],
        "medium": [21.53, 4.89, 1.95, 1.37, 0.59, 0.39, 0.59, 1.37, 1.95, 4.89, 21.53],
        "high":   [74.26, 9.78, 2.93, 0.88, 0.29, 0.2, 0.29, 0.88, 2.93, 9.78, 74.26],
    },
    11: {
        "low":    [8.19, 2.91, 1.86, 1.28, 0.98, 0.68, 0.68, 0.98, 1.28, 1.86, 2.91, 8.19],
        "medium": [23.46, 5.9, 2.94, 1.76, 0.68, 0.49, 0.49, 0.68, 1.76, 2.94, 5.9, 23.46],
        "high":   [117.15, 13.66, 5.09, 1.37, 0.38, 0.2, 0.2, 0.38, 1.37, 5.09, 13.66, 117.15],
    },
    12: {
        "low":    [9.78, 2.93, 1.57, 1.37, 1.08, 0.98, 0.48, 0.98, 1.08, 1.37, 1.57, 2.93, 9.78],
        "medium": [32.27, 10.75, 3.92, 1.96, 1.08, 0.59, 0.28, 0.59, 1.08, 1.96, 3.92, 10.75, 32.27],
        "high":   [166.03, 23.46, 7.89, 1.94, 0.68, 0.2, 0.2, 0.2, 0.68, 1.94, 7.89, 23.46, 166.03],
    },
    13: {
        "low":    [7.92, 3.89, 2.93, 1.87, 1.18, 0.88, 0.68, 0.68, 0.88, 1.18, 1.87, 2.93, 3.89, 7.92],
        "medium": [42.05, 12.72, 5.86, 2.94, 1.28, 0.68, 0.39, 0.39, 0.68, 1.28, 2.94, 5.86, 12.72, 42.05],
        "high":   [254, 36.15, 10.75, 3.91, 0.98, 0.2, 0.19, 0.19, 0.2, 0.98, 3.91, 10.75, 36.15, 254],
    },
    14: {
        "low":    [6.94, 3.91, 1.86, 1.37, 1.27, 1.08, 0.98, 0.48, 0.98, 1.08, 1.27, 1.37, 1.86, 3.91, 6.94],
        "medium": [56.71, 14.67, 6.85, 3.91, 1.86, 0.98, 0.49, 0.19, 0.49, 0.98, 1.86, 3.91, 6.85, 14.67, 56.71],
        "high":   [410.76, 54.77, 17.62, 4.89, 1.86, 0.29, 0.2, 0.19, 0.2, 0.29, 1.86, 4.89, 17.62, 54.77, 410.76],
    },
    15: {
        "low":    [14.67, 7.82, 2.91, 1.96, 1.47, 1.08, 0.98, 0.68, 0.68, 0.98, 1.08, 1.47, 1.96, 2.91, 7.82, 14.67],
        "medium": [86.05, 17.6, 10.74, 4.88, 2.93, 1.28, 0.49, 0.29, 0.29, 0.49, 1.28, 2.93, 4.88, 10.74, 17.6, 86.05],
        "high":   [606.06, 81.13, 26.38, 7.82, 2.93, 0.49, 0.19, 0.2, 0.2, 0.19, 0.49, 2.93, 7.82, 26.38, 81.13, 606.06],
    },
    16: {
        "low":    [15.64, 8.8, 1.98, 1.38, 1.37, 1.17, 1.08, 0.98, 0.48, 0.98, 1.08, 1.17, 1.37, 1.38, 1.98, 8.8, 15.64],
        "medium": [107.57, 40.09, 9.77, 4.9, 2.92, 1.47, 0.98, 0.49, 0.29, 0.49, 0.98, 1.47, 2.92, 4.9, 9.77, 40.09, 107.57],
        "high":   [978.01, 127.14, 25.43, 8.81, 3.9, 1.96, 0.2, 0.19, 0.2, 0.19, 0.2, 1.96, 3.9, 8.81, 25.43, 127.14, 978.01],
    },
}


# ─── Analytical RTP helper ────────────────────────────────────────────────────

def analytical_rtp(rows, multipliers):
    """Exact expected return for fair 50/50 Plinko.

    Each peg is an independent coin flip, so the probability of landing
    in slot k (= k rightward bounces out of `rows` total) is the
    binomial coefficient C(rows, k) / 2^rows.
    """
    ev = sum(comb(rows, k) * multipliers[k] for k in range(rows + 1))
    return ev / (2 ** rows)


# ─── Game configuration ──────────────────────────────────────────────────────

class GameConfig(Config):
    """Plinko base-game configuration.

    Creates one BetMode per (rows, risk) combination = 27 modes total.
    No reels, no symbols, no free spins — pure Plinko.
    """

    def __init__(self):
        super().__init__()

        # Game identity
        self.game_id = "plinko"
        self.provider_name = "stake"
        self.provider_number = 0
        self.game_name = "plinko"
        self.working_name = "plinko"
        self.win_type = "other"
        self.rtp = 0.97
        self.wincap = 978.01
        self.construct_paths()

        # Plinko has no reels, symbols, or paylines
        self.num_reels = 0
        self.num_rows = []
        self.paytable = {}
        self.include_padding = False
        self.special_symbols = {"wild": [], "scatter": [], "multiplier": []}
        self.freespin_triggers = {self.basegame_type: {}, self.freegame_type: {}}
        self.anticipation_triggers = {self.basegame_type: 0, self.freegame_type: 0}

        # Per-mode config lookup (used by gamestate.run_spin)
        self.plinko = {}
        self.bet_modes = []

        for rows in ROWS:
            for risk in RISKS:
                name = f"{rows}_{risk}"
                mults = BASE_MULTIPLIERS[rows][risk]
                max_mult = max(mults)
                rtp = analytical_rtp(rows, mults)

                self.plinko[name] = {
                    "rows": rows,
                    "risk": risk,
                    "multipliers": mults,
                }

                self.bet_modes.append(
                    BetMode(
                        name=name,
                        cost=1.0,
                        rtp=min(rtp, 0.9999),
                        max_win=max_mult,
                        auto_close_disabled=False,
                        is_feature=True,
                        is_buybonus=False,
                        distributions=[
                            Distribution(
                                criteria="basegame",
                                quota=1.0,
                                conditions={
                                    "reel_weights": {},
                                    "force_wincap": False,
                                    "force_freegame": False,
                                },
                            ),
                        ],
                    )
                )
