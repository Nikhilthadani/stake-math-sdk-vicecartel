import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from vice_cartel_math import books as B, sim as S, config as C


def test_buy_mode_books_hit_validated_rtp_with_minimal_tilt():
    rng = np.random.default_rng(1)
    x = S.floor_pay(S.run_bonus(rng, "normal_bonus", np.zeros(500_000)))
    target = 96.3993  # validated Normal Bonus EV (VALIDATION_REPORT s4)
    w, rep = B.class_weights({"normal_bonus": x}, {"normal_bonus": 1.0}, {"normal_bonus": target})
    rtp = B.deployed_rtp(w, {"normal_bonus": x}, 100.0)
    assert abs(rtp - 0.963993) < 2e-5
    assert rep["normal_bonus"]["max_weight_ratio"] < 1.5   # natural shape kept


def test_class_totals_follow_exact_probabilities():
    a = np.array([0.0, 1.0, 2.0]); b = np.array([10.0, 30.0])
    w, _ = B.class_weights({"a": a, "b": b}, {"a": 0.9, "b": 0.1}, {"a": 1.0, "b": 20.0})
    tot = w["a"].sum() + w["b"].sum()
    assert abs(w["b"].sum() / tot - 0.1) < 1e-9
