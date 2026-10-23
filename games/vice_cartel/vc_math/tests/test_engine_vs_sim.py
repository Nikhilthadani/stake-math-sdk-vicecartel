"""The scalar engine (to be ported) and the vectorized simulator must follow
the same math. Compare means and frequencies within 4 standard errors."""
import random, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from vice_cartel_math import config as C, engine as E, sim as S, exact as X


def _close(a, b, se, k=4.0):
    assert abs(a - b) <= k * se + 1e-12, (a, b, se)


def test_normal_bonus_engine_vs_exact():
    n = 20000
    w = np.array([E.play("bonus_normal", s).payout for s in range(n)])
    # trim cap outliers from SE by using sd of sample
    _close(w.mean(), X.bonus_ev("normal_bonus"), w.std() / np.sqrt(n))


def test_base_spin_engine_vs_sim():
    n = 60000
    e = [E.play("base", s) for s in range(n)]
    ep = np.array([r.payout for r in e if r.bonus is None and not r.max_win])
    sv, d = S.play_base(np.random.default_rng(3), 300000, detail=True)
    mask = (d["scatters"] < 3) & (~d["five"])
    sp = sv[mask]
    _close(ep.mean(), sp.mean(), np.hypot(ep.std() / np.sqrt(len(ep)), sp.std() / np.sqrt(len(sp))))
    _close((ep > 0).mean(), (sp > 0).mean(), 0.003)
    # trigger frequency matches design
    trig = np.mean([r.bonus is not None for r in e])
    _close(trig, C.SCATTER_TRIGGER_TOTAL, np.sqrt(C.SCATTER_TRIGGER_TOTAL / n))


def test_min2wild_wild_count_distribution():
    n = 40000
    ks = np.bincount([E.play("min2wild", s).wild_reels for s in range(n)], minlength=6) / n
    _, pk = X.min2wild_ev()
    for k in (2, 3, 4, 5):
        _close(ks[k], pk[k], np.sqrt(pk[k] * (1 - pk[k]) / n))


def test_extra_chance_uplift_is_exactly_5x():
    t1 = X.scatter_table(1.0); t5 = X.scatter_table(C.EXTRA_CHANCE_UPLIFT)
    for n in (3, 4, 5, 6):
        assert abs(t5[n] / t1[n] - 5.0) < 1e-12
    assert all(v >= 0 for v in t5.values())
