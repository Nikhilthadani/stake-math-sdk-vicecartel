"""Plinko game configuration for Stake Engine.

Ports the base-game multiplier tables from engine-plinko.
Each (rows, risk) combination becomes a separate BetMode.
"""

from math import comb
from src.config.config import Config, BetMode
from src.config.distributions import Distribution


# ─── Row and risk options ─────────────────────────────────────────────────────

ROWS = [8, 10, 12, 14, 16]
RISKS = ["low", "medium", "high"]


# ─── Base-game multiplier tables (exact copy from engine-plinko) ──────────────
# Index = final slot (number of rightward bounces, 0 … rows).

# Base-game multipliers — 96.10% RTP target (exact binomial, 50/50 path)
BASE_MULTIPLIERS = {
    8: {
        "low": [5.49, 2.13, 1.13, 1.11, 0.19, 1.11, 1.13, 2.13, 5.49],
        "medium": [12.63, 2.93, 1.25, 0.69, 0.38, 0.69, 1.25, 2.93, 12.63],
        "high": [28.09, 3.85, 1.46, 0.29, 0.2, 0.29, 1.46, 3.85, 28.09],
    },
    10: {
        "low": [8.67, 3.11, 1.47, 1.17, 1.11, 0.1, 1.11, 1.17, 1.47, 3.11, 8.67],
        "medium": [21.35, 4.84, 1.94, 1.36, 0.59, 0.38, 0.59, 1.36, 1.94, 4.84, 21.35],
        "high": [73.68, 9.69, 2.91, 0.87, 0.29, 0.2, 0.29, 0.87, 2.91, 9.69, 73.68],
    },
    12: {
        "low": [9.74, 2.76, 1.62, 1.62, 1.66, 0.75, 0.1, 0.75, 1.66, 1.62, 1.62, 2.76, 9.74],
        "medium": [32.02, 10.67, 3.9, 1.95, 1.07, 0.59, 0.27, 0.59, 1.07, 1.95, 3.9, 10.67, 32.02],
        "high": [164.82, 23.29, 7.83, 1.93, 0.67, 0.2, 0.2, 0.2, 0.67, 1.93, 7.83, 23.29, 164.82],
    },
    14: {
        "low": [6.89, 3.77, 1.87, 1.44, 1.52, 1.75, 0.64, 0.1, 0.64, 1.75, 1.52, 1.44, 1.87, 3.77, 6.89],
        "medium": [56.3, 14.56, 6.8, 3.88, 1.84, 0.97, 0.49, 0.19, 0.49, 0.97, 1.84, 3.88, 6.8, 14.56, 56.3],
        "high": [407.77, 54.39, 17.5, 4.84, 1.84, 0.29, 0.2, 0.19, 0.2, 0.29, 1.84, 4.84, 17.5, 54.39, 407.77],
    },
    16: {
        "low": [15.53, 6.55, 1.95, 1.39, 1.46, 1.37, 1.76, 0.61, 0.1, 0.61, 1.76, 1.37, 1.46, 1.39, 1.95, 6.55, 15.53],
        "medium": [106.79, 39.79, 9.69, 4.88, 2.9, 1.45, 0.97, 0.49, 0.29, 0.49, 0.97, 1.45, 2.9, 4.88, 9.69, 39.79, 106.79],
        "high": [970.95, 126.2, 25.25, 8.77, 3.87, 1.95, 0.2, 0.19, 0.19, 0.19, 0.2, 1.95, 3.87, 8.77, 25.25, 126.2, 970.95],
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

    Creates one BetMode per (rows, risk) combination = 15 modes total.
    Rows: 8, 10, 12, 14, 16  ×  Risks: low, medium, high.
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
        self.rtp = 0.961
        self.wincap = 970.95
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
