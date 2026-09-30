"""Vice Cartel — game configuration. All PAR-sheet values live here."""

import os
from src.config.config import Config
from src.config.distributions import Distribution
from src.config.betmode import BetMode


# ── Probability tables (PAR §1.5, §2.2, §2.3) ──────────────────────────

WILD_MULTIPLIER_WEIGHTS: dict[int, float] = {
    1: 3000, 2: 2200, 3: 1600, 5: 1000, 10: 500,
    15: 260, 20: 150, 25: 90, 50: 40, 75: 18,
    100: 9, 150: 4, 200: 2, 250: 1, 500: 0.3, 1000: 0.02,
}

BLUE_INCREMENT_WEIGHTS: dict[int, float] = {
    2: 2600, 3: 1800, 5: 1100, 10: 600, 15: 320,
    20: 190, 25: 110, 50: 45, 75: 20, 100: 10,
    150: 5, 200: 2, 250: 1, 500: 0.3, 1000: 0.02,
}

YELLOW_EXTRA_TURNS_WEIGHTS: dict[int, float] = {1: 60, 2: 30, 3: 10}

SURVIVAL_DEAD_SPIN_PROB: dict[int, float] = {
    0: 0.92, 1: 0.83, 2: 0.70, 3: 0.52, 4: 0.30, 5: 0.0,
}

WHEEL_TRIGGER_PROB = 0.35
WHEEL_RED_WEIGHT = 35
WHEEL_BLUE_WEIGHT = 40
WHEEL_YELLOW_WEIGHT = 25
RED_DOUBLE_WILD_PROB = 0.10

MYSTERY_TRIGGER_PROB = 0.00101631
MYSTERY_TRIGGER_PROB_EXTRA_3X = 0.004538    # PAR §7: 1-in-220, 4.47× uplift
MYSTERY_TRIGGER_PROB_EXTRA_5X = 0.008057    # PAR §7: 1-in-124, 7.93× uplift
MYSTERY_OUTCOME_WEIGHTS: dict[str, float] = {
    "normal_bonus": 40, "super_bonus": 20, "hidden_bonus": 5,
    "super_hidden_bonus": 1, "no_bonus": 34,
}

PER_REEL_WILD_PROB = 0.045

GOLDEN_CASE_REEL_HIT_PROB = 0.521

MIN2WILD_EXTRA_PROB_200X = 0.396    # PAR §8: extra-wild P for 200x price
MIN2WILD_EXTRA_PROB_250X = 0.438    # PAR §8: extra-wild P for 250x price


class GameConfig(Config):
    """Vice Cartel configuration — inherits from src/config/config.py."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        super().__init__()
        self.game_id = "vice_cartel"
        self.provider_name = "vicecartel"
        self.provider_number = 0
        self.game_name = "Vice Cartel"
        self.working_name = "Vice Cartel"
        self.wincap = 25000.0
        self.win_type = "lines"
        self.rtp = 0.9600
        self.construct_paths()

        # ── Grid ─────────────────────────────────────────────────
        self.num_reels = 5
        self.num_rows = [4] * self.num_reels

        # ── Paytable (PAR §1.3) — (kind, symbol): payout ────────
        self.paytable = {
            (5, "H1"): 6.0,   (4, "H1"): 2.0,   (3, "H1"): 0.5,
            (5, "H2"): 4.0,   (4, "H2"): 1.2,   (3, "H2"): 0.35,
            (5, "H3"): 2.5,   (4, "H3"): 0.8,   (3, "H3"): 0.25,
            (5, "H4"): 1.5,   (4, "H4"): 0.5,   (3, "H4"): 0.15,
            (5, "L1"): 1.0,   (4, "L1"): 0.3,   (3, "L1"): 0.1,
            (5, "L2"): 0.8,   (4, "L2"): 0.25,  (3, "L2"): 0.08,
            (5, "L3"): 0.5,   (4, "L3"): 0.15,  (3, "L3"): 0.05,
            (5, "L4"): 0.4,   (4, "L4"): 0.12,  (3, "L4"): 0.04,
        }

        # ── 14 Paylines (PAR §1.2, 0-indexed top-to-bottom) ─────
        self.paylines = {
            1:  [0, 0, 0, 0, 0],
            2:  [1, 1, 1, 1, 1],
            3:  [2, 2, 2, 2, 2],
            4:  [3, 3, 3, 3, 3],
            5:  [0, 1, 2, 1, 0],
            6:  [3, 2, 1, 2, 3],
            7:  [1, 0, 1, 0, 1],
            8:  [2, 3, 2, 3, 2],
            9:  [0, 1, 1, 1, 0],
            10: [3, 2, 2, 2, 3],
            11: [1, 2, 1, 2, 1],
            12: [2, 1, 2, 1, 2],
            13: [0, 1, 2, 3, 2],
            14: [3, 2, 1, 0, 1],
        }

        # ── Symbols ──────────────────────────────────────────────
        self.include_padding = False
        self.special_symbols = {"wild": ["W"], "scatter": ["SC"]}

        self.scatter_pay = {3: 0.5, 4: 2.0, 5: 5.0}

        self.freespin_triggers = {
            self.basegame_type: {},
            self.freegame_type: {},
        }
        self.anticipation_triggers = {
            self.basegame_type: 0,
            self.freegame_type: 0,
        }

        # ── Reels (PAR Reelsets — 200 stops, 5 columns) ─────────
        self.reels = {
            "BR0": self.read_reels_csv(os.path.join(self.reels_path, "BR0.csv")),
        }
        self.padding_reels[self.basegame_type] = self.reels["BR0"]
        self.padding_reels[self.freegame_type] = self.reels["BR0"]

        # ── Conditions (all need both basegame + freegame reel weights) ──
        _reel_weights_both = {
            self.basegame_type: {"BR0": 1},
            self.freegame_type: {"BR0": 1},
        }

        base_conditions = {
            "reel_weights": _reel_weights_both,
            "force_wincap": False,
            "force_freegame": False,
        }
        bonus_conditions = {
            "reel_weights": _reel_weights_both,
            "force_wincap": False,
            "force_freegame": True,
        }

        # ── Bet Modes ────────────────────────────────────────────
        self.bet_modes = [
            BetMode(
                name="base",
                cost=1.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=False,
                distributions=[
                    Distribution(criteria="basegame", quota=1.0, conditions=base_conditions),
                ],
            ),
            # Golden Case — skipped until max win logic is finalized
            # BetMode(
            #     name="golden_case",
            #     cost=1000.0,
            #     rtp=self.rtp,
            #     max_win=self.wincap,
            #     auto_close_disabled=False,
            #     is_feature=False,
            #     is_buybonus=True,
            #     distributions=[
            #         Distribution(criteria="golden_case", quota=1.0, conditions=base_conditions),
            #     ],
            # ),
            BetMode(
                name="extra_chance_3x",
                cost=3.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=[
                    Distribution(criteria="basegame", quota=1.0, conditions=base_conditions),
                ],
            ),
            BetMode(
                name="extra_chance_5x",
                cost=5.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=[
                    Distribution(criteria="basegame", quota=1.0, conditions=base_conditions),
                ],
            ),
            BetMode(
                name="min2wild_200x",
                cost=200.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=[
                    Distribution(criteria="basegame", quota=1.0, conditions=base_conditions),
                ],
            ),
            BetMode(
                name="min2wild_250x",
                cost=250.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=[
                    Distribution(criteria="basegame", quota=1.0, conditions=base_conditions),
                ],
            ),
        ]
