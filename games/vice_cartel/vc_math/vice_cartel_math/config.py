"""Vice Cartel - single source of truth for every math parameter.

Every number used by the engine, the simulator, the exact calculator and the
docs is defined here once. Values marked CALIBRATED were solved by
calibrate.py; see docs/MATH_SPEC.md for the derivation.
"""
from __future__ import annotations

# ---------------------------------------------------------------- symbols
SYMBOLS = ["H1", "H2", "H3", "H4", "L1", "L2", "L3", "L4", "SC", "W"]
SC = 8
W = 9
NUM_REELS = 5
NUM_ROWS = 4
CELLS = NUM_REELS * NUM_ROWS

# Paytable, multiples of TOTAL bet per winning line (unchanged from code).
PAYTABLE = {
    "H1": (0.50, 2.00, 6.00),
    "H2": (0.35, 1.20, 4.00),
    "H3": (0.25, 0.80, 2.50),
    "H4": (0.15, 0.50, 1.50),
    "L1": (0.10, 0.30, 1.00),
    "L2": (0.08, 0.25, 0.80),
    "L3": (0.05, 0.15, 0.50),
    "L4": (0.04, 0.12, 0.40),
}
WILD_LINE_PAY_5 = 6.0  # (5, W); only reachable together with Max Win now

# Scatter pay, anywhere, NOT multiplied. Paid in addition to the bonus trigger.
SCATTER_PAY = {3: 0.5, 4: 2.0, 5: 5.0, 6: 5.0}

PAYLINES = [
    (0, 0, 0, 0, 0), (1, 1, 1, 1, 1), (2, 2, 2, 2, 2), (3, 3, 3, 3, 3),
    (0, 1, 2, 1, 0), (3, 2, 1, 2, 3), (1, 0, 1, 0, 1), (2, 3, 2, 3, 2),
    (0, 1, 1, 1, 0), (3, 2, 2, 2, 3), (1, 2, 1, 2, 1), (2, 1, 2, 1, 2),
    (0, 1, 2, 3, 2), (3, 2, 1, 0, 1),
]

# --------------------------------------------------------------- reel strip
# Symbol stop counts per reel (identical on all 5 reels). SC is no longer on the
# strip: it was 9/191 and produced 3+ Scatters on 1 in 17 spins, which cannot
# drive a 3/4/5/6 bonus ladder. Scatters are now placed by SCATTER_COUNT_TABLE.
STRIP_COUNTS = {"H1": 3, "H2": 6, "H3": 10, "H4": 16,
                "L1": 24, "L2": 32, "L3": 41, "L4": 50}  # 182 stops

# --------------------------------------------------------------- wilds
# CALIBRATED: was 0.045. Raised so base and bonus each carry ~48% RTP, which is
# the only split that lets Extra Chance (3x cost, 5x chance) land in range.
PER_REEL_WILD_PROB = 0.0510

WILD_MULTIPLIERS = (1, 2, 3, 5, 10, 15, 20, 25, 50, 75, 100, 150, 200, 250, 500, 1000)
WILD_MULT_WEIGHTS = (3000, 2200, 1600, 1000, 500, 260, 150, 90, 40, 18, 9, 4, 2, 1, 0.3, 0.02)

BLUE_INCREMENTS = (2, 3, 5, 10, 15, 20, 25, 50, 75, 100, 150, 200, 250, 500, 1000)
BLUE_WEIGHTS = (2600, 1800, 1100, 600, 320, 190, 110, 45, 20, 10, 5, 2, 1, 0.3, 0.02)

YELLOW_SPINS = (1, 2, 3)
YELLOW_WEIGHTS = (60, 30, 10)

# --------------------------------------------------------------- cap
WINCAP = 25_000.0
MIN_PAY_STEP = 0.1  # Stake payout granularity; round total is floored to this
BONUS_SPIN_SAFETY_LIMIT = 200
MAX_WILD_REELS_FROM_RED = 4  # the 5th Wild only comes from MAX WIN (=Max Win)

# --------------------------------------------------------------- scatters
# Scatter count drawn per base-game spin, then placed uniformly on non-Wild
# cells (clamped to free cells; only binds with 4 Wild reels).
# 3 -> Normal, 4 -> Super, 5 -> Hidden, 6 -> Super Hidden. 7+ cannot occur.
# CALIBRATED (P(n) for n = 3..6; P(1), P(2) are cosmetic near-miss frequencies).
SCATTER_P_1 = 0.12
SCATTER_P_2 = 0.03
SCATTER_P_TRIGGER = {3: None, 4: None, 5: None, 6: None}  # set below
TIER_RATIO = {3: 40, 4: 20, 5: 5, 6: 1}  # design intent: 40/20/5/1
SCATTER_TRIGGER_TOTAL = 0.0  # CALIBRATED below

# --------------------------------------------------------------- bonus tiers
# Wheel: P(spin wheel) per bonus spin, then segment weights. RED/BLUE/YELLOW keep
# the original 35/40/25 ratio. MAX_WIN weight is per tier (CALIBRATED).
WHEEL_SEGMENT_WEIGHTS = {"RED": 35.0, "BLUE": 40.0, "YELLOW": 25.0}
RED_DOUBLE_PROB = 0.10

BONUS_TIERS = {
    "normal_bonus": dict(scatters=3, spins=10, start_wilds=0, start_mult=0,
                         wheel_prob=None, maxwin_weight=None),
    "super_bonus": dict(scatters=4, spins=10, start_wilds=1, start_mult=2,
                        wheel_prob=None, maxwin_weight=None),
    "hidden_bonus": dict(scatters=5, spins=12, start_wilds=2, start_mult=3,
                         wheel_prob=None, maxwin_weight=None),
    "super_hidden_bonus": dict(scatters=6, spins=12, start_wilds=3, start_mult=5,
                               wheel_prob=None, maxwin_weight=None),
}
TIER_BY_SCATTERS = {v["scatters"]: k for k, v in BONUS_TIERS.items()}

# --------------------------------------------------------------- modes
RTP_TARGET = 0.964
RTP_RANGE = (0.961, 0.967)

EXTRA_CHANCE_UPLIFT = 5.0  # multiplies P(3..6 scatters); 3x is infeasible
MIN2WILD_EXTRA_PROB = None  # CALIBRATED
GOLDEN_CASE_LETTER_PROB = 0.291759  # unchanged, 96.30004% exact

BET_MODES = {
    "base":            dict(cost=1.0,    kind="base"),
    "extra_chance":    dict(cost=3.0,    kind="base", uplift=EXTRA_CHANCE_UPLIFT),
    "bonus_normal":    dict(cost=100.0,  kind="buy", tier="normal_bonus"),
    "bonus_super":     dict(cost=200.0,  kind="buy", tier="super_bonus"),
    "min2wild":        dict(cost=100.0,  kind="min2wild"),
    "golden_case":     dict(cost=1000.0, kind="golden"),
}

# Mode-level visibility, enforced in the math (not just UI).
MODE_RULES = {
    "base":         dict(scatters=True,  wheel=False),
    "extra_chance": dict(scatters=True,  wheel=False),
    "bonus_normal": dict(scatters=False, wheel=True),
    "bonus_super":  dict(scatters=False, wheel=True),
    "min2wild":     dict(scatters=False, wheel=False),
    "golden_case":  dict(scatters=False, wheel=False),
}

from .calibrated import apply as _apply  # noqa: E402
_apply(globals())
