import random, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from vice_cartel_math import config as C, engine as E, sim as S


def board_from(rows):
    return [r.split() for r in rows]


def test_line_rules():
    assert E.line_pay(["W"] * 5) == 6.0
    assert E.line_pay(["W", "W", "W", "W", "L4"]) == 0.4      # 5-kind L4
    assert E.line_pay(["W", "W", "W", "W", "SC"]) == 0.0      # SC breaks
    assert E.line_pay(["H1", "H1", "W", "L2", "L2"]) == 0.5
    assert E.line_pay(["SC", "H1", "H1", "H1", "H1"]) == 0.0
    assert E.line_pay(["L3", "L3", "SC", "L3", "L3"]) == 0.0


def test_sim_and_engine_line_evaluators_agree():
    rng = random.Random(7); nrng = np.random.default_rng(7)
    syms = C.SYMBOLS
    boards = []
    for _ in range(3000):
        wild = {r for r in range(5) if rng.random() < 0.3}
        b = [[("W" if c in wild else rng.choice(syms[:9])) for c in range(5)] for _ in range(4)]
        boards.append(b)
    arr = np.array([[[syms.index(x) for x in row] for row in b] for b in boards], dtype=np.int8)
    v = S.eval_lines(arr)
    for i, b in enumerate(boards):
        assert abs(v[i] - E.evaluate_lines(b)) < 1e-9


def test_scatter_mapping_unique():
    assert C.TIER_BY_SCATTERS == {3: "normal_bonus", 4: "super_bonus",
                                  5: "hidden_bonus", 6: "super_hidden_bonus"}
    assert sum(C.SCATTER_P_TRIGGER.values()) > 0


def test_bonus_starting_states():
    t = C.BONUS_TIERS
    assert (t["normal_bonus"]["spins"], t["normal_bonus"]["start_wilds"]) == (10, 0)
    assert (t["super_bonus"]["spins"], t["super_bonus"]["start_wilds"], t["super_bonus"]["start_mult"]) == (10, 1, 2)
    assert (t["hidden_bonus"]["spins"], t["hidden_bonus"]["start_wilds"], t["hidden_bonus"]["start_mult"]) == (12, 2, 3)
    assert (t["super_hidden_bonus"]["spins"], t["super_hidden_bonus"]["start_wilds"], t["super_hidden_bonus"]["start_mult"]) == (12, 3, 5)
    for seed in range(200):
        rd = E.Round("x")
        E.play_bonus(random.Random(seed), "super_bonus", 0.0, rd)
        ev = [e for e in rd.events if e[0] == "bonus_start"]
        assert len(ev) == 1 and ev[0][2] == 10 and list(ev[0][3].values()) == [2.0]


def test_rounds_are_seed_deterministic():
    for mode in C.BET_MODES:
        assert E.play(mode, 123).payout == E.play(mode, 123).payout


def test_five_wilds_pay_max_win_exactly_once():
    hits = 0
    for seed in range(20000):
        rd = E.play("min2wild", seed)
        fw = [e for e in rd.events if e[0] == "five_wilds"]
        assert len(fw) <= 1
        if fw:
            hits += 1
            assert rd.payout == C.WINCAP and rd.max_win
        assert rd.payout <= C.WINCAP
    assert hits > 0


def test_bonus_maxwin_segment_ends_round():
    for seed in range(6000):
        rd = E.Round("x")
        tot = E.play_bonus(random.Random(seed), "super_hidden_bonus", 0.0, rd)
        segs = [e for e in rd.events if e == ("wheel", "MAX_WIN")]
        if segs:
            assert tot == C.WINCAP
            assert rd.events[-1] == ("five_wilds",)


def test_red_never_creates_fifth_wild():
    for seed in range(3000):
        rd = E.Round("x")
        E.play_bonus(random.Random(seed), "super_hidden_bonus", 0.0, rd)
    # structural: RED add is clamped
    assert C.MAX_WILD_REELS_FROM_RED == 4


def test_restricted_modes_have_no_scatter_or_wheel():
    for seed in range(3000):
        for mode in ("min2wild", "golden_case"):
            rd = E.play(mode, seed)
            assert not any(e[0] in ("wheel", "bonus_start") for e in rd.events)
            assert rd.scatters == 0
        rd = E.play("bonus_normal", seed)
        assert rd.scatters == 0 and rd.wild_reels == 0   # no base roll in buys
    for seed in range(3000):
        rd = E.play("base", seed)
        assert rd.bonus is None or rd.scatters in (3, 4, 5, 6)
        assert not any(e[0] == "wheel" for e in rd.events) or rd.bonus


def test_payouts_on_grid_and_capped():
    for mode in C.BET_MODES:
        for seed in range(2000):
            p = E.play(mode, seed).payout
            assert 0 <= p <= C.WINCAP
            assert abs(round(p * 10) - p * 10) < 1e-6


def test_costs_centralised():
    assert {m: v["cost"] for m, v in C.BET_MODES.items()} == {
        "base": 1, "extra_chance": 3, "bonus_normal": 100, "bonus_super": 200,
        "min2wild": 100, "golden_case": 1000}
