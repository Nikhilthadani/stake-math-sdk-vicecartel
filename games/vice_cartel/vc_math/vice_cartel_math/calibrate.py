"""Solve the CALIBRATED parameters. Run: python -m vice_cartel_math.calibrate"""
from __future__ import annotations
from . import config as C, exact as E

# Design targets (see docs/MATH_SPEC.md section 7)
TARGET = C.RTP_TARGET
TIER_TARGETS = {
    # tier: (wheel_prob or None=solve, EV target or None, P(max win) per round)
    "normal_bonus":       (None, TARGET * C.BET_MODES["bonus_normal"]["cost"], 1 / 10_000),
    "super_bonus":        (None, TARGET * C.BET_MODES["bonus_super"]["cost"], 1 / 4_000),
    "hidden_bonus":       (0.35, None, 1 / 500),
    "super_hidden_bonus": (0.35, None, 1 / 150),
}


def _bisect(f, lo, hi, target, it=60):
    for _ in range(it):
        mid = (lo + hi) / 2
        if f(mid) < target:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def solve_tier(tier, wp, ev_target, pmax, ev_scale=1.0):
    def mw_for(w):
        return _bisect(lambda m: E.bonus_ev(tier, w, m, detail=True)["p_maxwin"], 0, 50, pmax, 40)
    if wp is None:
        wp = _bisect(lambda w: ev_scale * E.bonus_ev(tier, w, mw_for(w)), 0.01, 0.95, ev_target, 30)
    mw = mw_for(wp)
    return wp, mw, E.bonus_ev(tier, wp, mw, detail=True)


if __name__ == "__main__":
    for tier, (wp, evt, pm) in TIER_TARGETS.items():
        wp, mw, d = solve_tier(tier, wp, evt, pm)
        print(f"{tier:20s} wheel_prob={wp:.6f} maxwin_weight={mw:.6f} EV={d['ev']:.3f} "
              f"P(max)=1/{1/d['p_maxwin']:.0f} spins={d['spins']:.3f}")
