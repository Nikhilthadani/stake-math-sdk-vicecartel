"""Vice Cartel — game configuration. All math values live here (MATH_SPEC v2.0, vc_math/)."""

import os
from src.config.config import Config
from src.config.distributions import Distribution
from src.config.betmode import BetMode


# ── Probability tables (MATH_SPEC §3, §5) ───────────────────────────────

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

WHEEL_RED_WEIGHT = 35
WHEEL_BLUE_WEIGHT = 40
WHEEL_YELLOW_WEIGHT = 25
RED_DOUBLE_WILD_PROB = 0.10
MAX_WILD_REELS_FROM_RED = 4  # a 5th Wild in a bonus only comes from the MAX WIN segment

PER_REEL_WILD_PROB = 0.053455

# Scatters are not on the strip: the count is drawn per base spin, then placed on free cells.
# 3 -> normal, 4 -> super, 5 -> hidden, 6 -> super hidden; 1 and 2 are cosmetic near-misses.
SCATTER_TRIGGER_TOTAL = 0.0017173
SCATTER_TIER_RATIO: dict[int, int] = {3: 40, 4: 20, 5: 5, 6: 1}
SCATTER_COUNT_PROBS: dict[int, float] = {
    1: 0.12,
    2: 0.03,
    **{n: SCATTER_TRIGGER_TOTAL * r / sum(SCATTER_TIER_RATIO.values()) for n, r in SCATTER_TIER_RATIO.items()},
}
EXTRA_CHANCE_UPLIFT = 5.0  # multiplies P(3..6 scatters); P(0) absorbs the difference

# wheel_prob: chance the wheel spins per bonus spin; maxwin_weight: MAX WIN segment vs RED 35 / BLUE 40 / YELLOW 25
BONUS_TIERS: dict[str, dict] = {
    "normal_bonus":       {"scatters": 3, "spins": 10, "start_wilds": 0, "start_mult": 1,
                           "wheel_prob": 0.303018, "maxwin_weight": 0.0029254},
    "super_bonus":        {"scatters": 4, "spins": 10, "start_wilds": 1, "start_mult": 2,
                           "wheel_prob": 0.245693, "maxwin_weight": 0.0092398},
    "hidden_bonus":       {"scatters": 5, "spins": 12, "start_wilds": 2, "start_mult": 3,
                           "wheel_prob": 0.350000, "maxwin_weight": 0.0414272},
    "super_hidden_bonus": {"scatters": 6, "spins": 12, "start_wilds": 3, "start_mult": 5,
                           "wheel_prob": 0.350000, "maxwin_weight": 0.1385452},
}
TIER_BY_SCATTERS: dict[int, str] = {cfg["scatters"]: tier for tier, cfg in BONUS_TIERS.items()}

BUY_BONUS_TIER: dict[str, str] = {"bonus_normal": "normal_bonus", "bonus_super": "super_bonus"}

MIN2WILD_EXTRA_PROB = 0.138188  # each non-forced reel; 5 Wilds = Max Win

GOLDEN_CASE_LETTER_PROB = 0.291759  # per-letter q (before "at least 1" guarantee), exact 96.30% RTP

# ── Book classes (natural stratified books, no optimizer) ───────────────
# Each class is generated with its outcome forced, then weighted to its exact natural probability
# (game_weights.py). Plain spins are split by Wild-reel count and multiplier-sum range so every
# class is narrow enough for the in-class mean correction to keep all weights close to 1.
MULT_SUM_RANGES: list[tuple[int, int]] = [
    (1, 6), (7, 15), (16, 40), (41, 100), (101, 250), (251, 600), (601, 4000),
]

BASE_CLASS_BOOKS: dict[str, int] = {
    "five_wilds": 100,
    "plain_k0": 400_000,
    **{f"plain_k{k}_m{j}": 40_000 for k in range(1, 5) for j in range(len(MULT_SUM_RANGES))},
    "bonus_sc3": 230_000,
    "bonus_sc4": 150_000,
    "bonus_sc5": 50_000,
    "bonus_sc6": 49_900,
}
MIN2WILD_CLASS_BOOKS: dict[str, int] = {
    "wilds5": 85,
    **{f"wilds{k}_m{j}": 47_615 for k in range(2, 5) for j in range(len(MULT_SUM_RANGES))},
}
BONUS_BUY_BOOKS = 500_000
GOLDEN_CASE_BOOKS = 500_000


def base_class_conditions(name: str) -> dict:
    """Forced outcome for a base / Extra Chance book class."""
    if name == "five_wilds":
        return {"five_wilds": True}
    if name.startswith("bonus_sc"):
        return {"scatters": int(name[len("bonus_sc"):])}
    k, _, j = name[len("plain_k"):].partition("_m")
    cond = {"scatters": "plain", "wild_count": int(k)}
    if j:
        cond["mult_range"] = MULT_SUM_RANGES[int(j)]
    return cond


def min2wild_class_conditions(name: str) -> dict:
    k, _, j = name[len("wilds"):].partition("_m")
    cond = {"wild_count": int(k)}
    if j:
        cond["mult_range"] = MULT_SUM_RANGES[int(j)]
    return cond


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
        self.rtp = 0.9640
        self.construct_paths()

        # ── Grid ─────────────────────────────────────────────────
        self.num_reels = 5
        self.num_rows = [4] * self.num_reels

        # ── Paytable — (kind, symbol): payout ───────────────────
        self.paytable = {
            # Wild substitutes; only a 5-Wild line has no symbol to substitute for and pays as H1
            (5, "W"):  6.0,
            (5, "H1"): 6.0,   (4, "H1"): 2.0,   (3, "H1"): 0.5,
            (5, "H2"): 4.0,   (4, "H2"): 1.2,   (3, "H2"): 0.35,
            (5, "H3"): 2.5,   (4, "H3"): 0.8,   (3, "H3"): 0.25,
            (5, "H4"): 1.5,   (4, "H4"): 0.5,   (3, "H4"): 0.15,
            (5, "L1"): 1.0,   (4, "L1"): 0.3,   (3, "L1"): 0.1,
            (5, "L2"): 0.8,   (4, "L2"): 0.25,  (3, "L2"): 0.08,
            (5, "L3"): 0.5,   (4, "L3"): 0.15,  (3, "L3"): 0.05,
            (5, "L4"): 0.4,   (4, "L4"): 0.12,  (3, "L4"): 0.04,
        }

        # ── 14 Paylines (0-indexed top-to-bottom) ───────────────
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

        # Not multiplied by Wilds; paid in addition to the bonus trigger
        self.scatter_pay = {3: 0.5, 4: 2.0, 5: 5.0, 6: 5.0}

        self.freespin_triggers = {
            self.basegame_type: {},
            self.freegame_type: {},
        }
        self.anticipation_triggers = {
            self.basegame_type: 0,
            self.freegame_type: 0,
        }

        # ── Reels (182 stops per reel, no SC, no W) ─────────────
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

        def _classes(books: dict[str, int], conditions_for) -> list[Distribution]:
            return [
                Distribution(criteria=name, fixed_amt=n, conditions={**base_conditions, **conditions_for(name)})
                for name, n in books.items()
            ]

        def _single(criteria: str, n: int) -> list[Distribution]:
            return [Distribution(criteria=criteria, fixed_amt=n, conditions=dict(base_conditions))]

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
                distributions=_classes(BASE_CLASS_BOOKS, base_class_conditions),
            ),
            BetMode(
                name="extra_chance",
                cost=3.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=True,
                is_buybonus=False,
                distributions=_classes(BASE_CLASS_BOOKS, base_class_conditions),
            ),
            BetMode(
                name="bonus_normal",
                cost=100.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=_single("freegame", BONUS_BUY_BOOKS),
            ),
            BetMode(
                name="bonus_super",
                cost=200.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=_single("freegame", BONUS_BUY_BOOKS),
            ),
            BetMode(
                name="min2wild",
                cost=100.0,
                rtp=self.rtp,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=_classes(MIN2WILD_CLASS_BOOKS, min2wild_class_conditions),
            ),
            BetMode(
                name="golden_case",
                cost=1000.0,
                rtp=0.9630,
                max_win=self.wincap,
                auto_close_disabled=False,
                is_feature=False,
                is_buybonus=True,
                distributions=_single("golden_case", GOLDEN_CASE_BOOKS),
            ),
        ]
