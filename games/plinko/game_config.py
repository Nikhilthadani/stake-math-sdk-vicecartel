"""Plinko game configuration for Stake Engine.

Ports the base-game multiplier tables from engine-plinko.
Each (rows, risk) combination becomes a separate BetMode, plus one
"wheel" buy mode per row count (20 modes total).
"""

from math import comb, sqrt
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


# ─── Wheel buy feature ────────────────────────────────────────────────────────
# Landing in a wheel slot spins the wheel; payout = slot multiplier × wheel value.
# Wheel: 20 equal segments, value -> segment count (E = 2.05).

WHEEL = {1: 13, 2: 4, 5: 2, 10: 1}
WHEEL_SEGMENTS = [1, 2, 1, 5, 1, 1, 2, 1, 1, 10, 1, 2, 1, 1, 5, 1, 2, 1, 1, 1]
WHEEL_COST = 1.3
WHEEL_RISK = "medium"

# Medium tables re-tuned so each mode returns exactly 96.10% of WHEEL_COST.
WHEEL_TABLES = {
    8: {
        "multipliers": [12.78, 2.93, 1.25, 0.69, 0.38, 0.69, 1.25, 2.93, 12.78],
        "wheel_slots": (2, 6),
    },
    10: {
        "multipliers": [22.07, 4.84, 1.94, 1.5, 0.59, 0.38, 0.59, 1.5, 1.94, 4.84, 22.07],
        "wheel_slots": (4, 6),
    },
    12: {
        "multipliers": [32.02, 10.67, 4.42, 1.95, 1.07, 0.59, 0.27, 0.59, 1.07, 1.95, 4.42, 10.67, 32.02],
        "wheel_slots": (4, 8),
    },
    14: {
        "multipliers": [56.66, 14.56, 6.58, 3.88, 1.84, 0.97, 0.49, 0.19, 0.49, 0.97, 1.84, 3.88, 6.58, 14.56, 56.66],
        "wheel_slots": (5, 7, 9),
    },
    16: {
        "multipliers": [109.56, 39.79, 9.69, 7.18, 2.9, 1.45, 0.97, 0.49, 0.29, 0.49, 0.97, 1.45, 2.9, 7.18, 9.69, 39.79, 109.56],
        "wheel_slots": (6, 10),
    },
}

assert sorted(WHEEL_SEGMENTS) == sorted(v for v, n in WHEEL.items() for _ in range(n))


# ─── Mode registry ────────────────────────────────────────────────────────────

def build_modes():
    """Return {mode_name: spec} for every base and wheel mode."""
    modes = {}
    for rows in ROWS:
        for risk in RISKS:
            modes[f"{rows}_{risk}"] = {
                "rows": rows,
                "risk": risk,
                "multipliers": BASE_MULTIPLIERS[rows][risk],
                "wheel_slots": (),
                "cost": 1.0,
            }
    for rows in ROWS:
        modes[f"{rows}_wheel"] = {
            "rows": rows,
            "risk": WHEEL_RISK,
            **WHEEL_TABLES[rows],
            "cost": WHEEL_COST,
        }
    return modes


MODES = build_modes()


# ─── Analytical math ──────────────────────────────────────────────────────────
# Slot k (k rightward bounces) has probability C(rows, k) / 2^rows.
# A wheel slot pays m * W, so its moments are m * E[W] and m^2 * E[W^2].

def _wheel_moment(power):
    return sum(v ** power * n for v, n in WHEEL.items()) / sum(WHEEL.values())


def _payout_moment(spec, power):
    rows, mults, wheel_slots = spec["rows"], spec["multipliers"], spec["wheel_slots"]
    wheel = _wheel_moment(power)
    total = sum(
        comb(rows, k) * mults[k] ** power * (wheel if k in wheel_slots else 1)
        for k in range(rows + 1)
    )
    return total / 2 ** rows


def analytical_rtp(mode):
    """Exact expected return per unit of mode cost."""
    spec = MODES[mode]
    return _payout_moment(spec, 1) / spec["cost"]


def analytical_sigma(mode):
    """Exact payout standard deviation per unit of mode cost."""
    spec = MODES[mode]
    variance = _payout_moment(spec, 2) - _payout_moment(spec, 1) ** 2
    return sqrt(max(variance, 0)) / spec["cost"]


def max_payout(mode):
    """Largest possible payout multiplier (wheel included)."""
    spec = MODES[mode]
    top_wheel = max(WHEEL)
    return max(
        m * (top_wheel if k in spec["wheel_slots"] else 1)
        for k, m in enumerate(spec["multipliers"])
    )


# ─── Game configuration ──────────────────────────────────────────────────────

class GameConfig(Config):
    """Plinko configuration.

    20 BetModes: 15 base modes (5 rows × 3 risks, cost 1) and
    5 wheel buy modes (one per row count, cost WHEEL_COST).
    No reels, no symbols, no free spins.
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
        self.wincap = max(max_payout(name) for name in MODES)
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
        self.plinko = MODES
        self.wheel_segments = WHEEL_SEGMENTS

        self.bet_modes = [
            BetMode(
                name=name,
                cost=spec["cost"],
                rtp=min(analytical_rtp(name), 0.9999),
                max_win=max_payout(name),
                auto_close_disabled=False,
                is_feature=not spec["wheel_slots"],
                is_buybonus=bool(spec["wheel_slots"]),
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
            for name, spec in MODES.items()
        ]
