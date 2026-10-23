"""Calibrated values (solved by calibrate.py / docs/MATH_SPEC.md s7)."""
CALIBRATED = {
    "PER_REEL_WILD_PROB": 0.053455,
    "SCATTER_TRIGGER_TOTAL": 0.0017173,
    "MIN2WILD_EXTRA_PROB": 0.138188,
    # tier: (P(wheel spins) per bonus spin, MAX WIN segment weight vs RED35/BLUE40/YELLOW25)
    "WHEEL": {
        "normal_bonus": (0.303018, 0.0029254),
        "super_bonus": (0.245693, 0.0092398),
        "hidden_bonus": (0.350000, 0.0414272),
        "super_hidden_bonus": (0.350000, 0.1385452),
    },
}


def apply(g):
    c = CALIBRATED
    g["PER_REEL_WILD_PROB"] = c["PER_REEL_WILD_PROB"]
    g["MIN2WILD_EXTRA_PROB"] = c["MIN2WILD_EXTRA_PROB"]
    tot = c["SCATTER_TRIGGER_TOTAL"]
    g["SCATTER_TRIGGER_TOTAL"] = tot
    s = sum(g["TIER_RATIO"].values())
    g["SCATTER_P_TRIGGER"] = {n: tot * r / s for n, r in g["TIER_RATIO"].items()}
    for tier, (wp, mw) in c["WHEEL"].items():
        g["BONUS_TIERS"][tier]["wheel_prob"] = wp
        g["BONUS_TIERS"][tier]["maxwin_weight"] = mw
