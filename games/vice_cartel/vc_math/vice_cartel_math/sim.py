"""Vectorized simulator. Follows exactly the same rules as engine.py
(cross-checked in tests/test_engine_vs_sim.py)."""
from __future__ import annotations
import numpy as np
from . import config as C

LINES = np.array(C.PAYLINES, dtype=np.int64)          # [14,5] rows
PAY = np.zeros((10, 6))
for i, s in enumerate(C.SYMBOLS[:8]):
    PAY[i, 3:6] = C.PAYTABLE[s]
STRIP_P = np.array([C.STRIP_COUNTS[s] for s in C.SYMBOLS[:8]], float)
STRIP_P /= STRIP_P.sum()
STRIP_CDF = np.cumsum(STRIP_P)
WM_V = np.array(C.WILD_MULTIPLIERS, float); WM_C = np.cumsum(C.WILD_MULT_WEIGHTS) / sum(C.WILD_MULT_WEIGHTS)
BL_V = np.array(C.BLUE_INCREMENTS, float); BL_C = np.cumsum(C.BLUE_WEIGHTS) / sum(C.BLUE_WEIGHTS)
YE_V = np.array(C.YELLOW_SPINS); YE_C = np.cumsum(C.YELLOW_WEIGHTS) / sum(C.YELLOW_WEIGHTS)


def _pick(cdf, vals, u):
    return vals[np.minimum(np.searchsorted(cdf, u, side="left"), len(vals) - 1)]


def draw_symbols(rng, shape):
    return np.minimum(np.searchsorted(STRIP_CDF, rng.random(shape)), 7).astype(np.int8)


def eval_lines(board):
    """board [N,4,5] int8 -> raw line total [N] (x bet, before multiplier)."""
    n = board.shape[0]
    cells = board[:, LINES, np.arange(5)[None, :]]       # [N,14,5]
    c = cells.reshape(-1, 5)
    isw = c == C.W
    lead = np.cumprod(isw, axis=1).sum(axis=1)
    full = lead == 5
    s = c[np.arange(len(c)), np.minimum(lead, 4)]
    m = (c == s[:, None]) | isw
    run = np.cumprod(m, axis=1).sum(axis=1)
    pay = PAY[np.where(s == C.SC, 9, s), run]
    pay = np.where(s == C.SC, 0.0, pay)
    pay = np.where(full, C.WILD_LINE_PAY_5, pay)
    return pay.reshape(n, 14).sum(axis=1)


def floor_pay(x):
    cents = np.round(x * 100).astype(np.int64)
    return (cents - cents % 10) / 100.0


def spin_multiplier(mult):
    s = mult.sum(axis=1)
    return np.where((mult > 0).any(axis=1), s, 1.0)


# ------------------------------------------------------------------ bonus
def run_bonus(rng, tier, start_win, stats=None, paired=False):
    """Play bonus rounds for len(start_win) players. Returns round totals
    (start_win + bonus win, capped). No scatters, no base Wild roll."""
    t = C.BONUS_TIERS[tier]
    n = len(start_win)
    mult = np.zeros((n, 5))
    if t["start_wilds"]:
        keys = rng.random((n, 5))
        pos = np.argsort(keys, axis=1)[:, : t["start_wilds"]]
        np.put_along_axis(mult, pos, float(t["start_mult"]), axis=1)
    turns = np.full(n, t["spins"], dtype=np.int64)
    win = start_win.astype(float).copy()
    capped = win >= C.WINCAP
    if not paired:
        win[capped] = C.WINCAP
    active = ~capped if not paired else np.ones(n, bool)
    reached = capped.copy()
    spins = np.zeros(n, dtype=np.int64)
    maxwin_seg = np.zeros(n, bool)
    wsum = sum(C.WHEEL_SEGMENT_WEIGHTS.values()) + t["maxwin_weight"]
    segc = np.cumsum([C.WHEEL_SEGMENT_WEIGHTS["RED"], C.WHEEL_SEGMENT_WEIGHTS["BLUE"],
                      C.WHEEL_SEGMENT_WEIGHTS["YELLOW"], t["maxwin_weight"]]) / wsum
    while active.any():
        idx = np.nonzero(active)[0]
        k = len(idx)
        spins[idx] += 1
        m = mult[idx]
        trig = rng.random(k) < t["wheel_prob"]
        seg = np.searchsorted(segc, rng.random(k))           # 0R 1B 2Y 3MAX
        seg = np.where(trig, np.minimum(seg, 3), -1)
        nw = (m > 0).sum(axis=1)
        # RED: +1 (+2 w.p. 0.1), never beyond 4 Wild reels
        red = seg == 0
        add = np.where(rng.random(k) < C.RED_DOUBLE_PROB, 2, 1)
        add = np.where(red, np.minimum(add, C.MAX_WILD_REELS_FROM_RED - nw), 0)
        add = np.maximum(add, 0)
        keys = rng.random((k, 5)); keys[m > 0] = 2.0
        order = np.argsort(keys, axis=1)
        for j in range(2):
            sel = add > j
            if sel.any():
                r = np.nonzero(sel)[0]
                m[r, order[r, j]] = _pick(WM_C, WM_V, rng.random(len(r)))
        # BLUE: upgrade one random existing Wild
        blue = (seg == 1) & (nw > 0)
        if blue.any():
            r = np.nonzero(blue)[0]
            kk = rng.random((len(r), 5)); kk[m[r] <= 0] = 2.0
            m[r, np.argmin(kk, axis=1)] += _pick(BL_C, BL_V, rng.random(len(r)))
        # YELLOW
        yel = seg == 2
        turns[idx[yel]] += _pick(YE_C, YE_V, rng.random(yel.sum()))
        # MAX WIN segment: all reels Wild -> 5 Wilds -> Max Win, round ends
        mx = seg == 3
        mult[idx] = m
        if mx.any():
            g = idx[mx]
            win[g] = C.WINCAP; active[g] = False; maxwin_seg[g] = True
            reached[g] = True
        go = ~mx
        g = idx[go]
        if len(g):
            board = draw_symbols(rng, (len(g), 4, 5))
            wl = mult[g] > 0
            board[np.broadcast_to(wl[:, None, :], board.shape)] = C.W
            raw = eval_lines(board)
            win[g] += np.round(raw * spin_multiplier(mult[g]), 2)
            hit = win[g] >= C.WINCAP
            reached[g[hit]] = True
            if not paired:
                win[g[hit]] = C.WINCAP
                active[g[hit]] = False
            turns[g] -= 1
            done = (turns[g] <= 0) | (spins[g] >= C.BONUS_SPIN_SAFETY_LIMIT)
            active[g[done]] = False
    if stats is not None:
        stats["spins"] = spins
        stats["maxwin_segment"] = maxwin_seg
        stats["final_wilds"] = (mult > 0).sum(axis=1)
    if paired:
        # U: cap ignored (MAX WIN segment still sets 25,000) -> mean is exact.bonus_ev
        # Cg: the real game on the same random path
        return np.where(reached, C.WINCAP, win), win
    return win


def play_bonus_buy(rng, mode, n):
    tier = C.BET_MODES[mode]["tier"]
    st = {}
    w = floor_pay(run_bonus(rng, tier, np.zeros(n), st))
    return w, st


# ------------------------------------------------------------------ base
def scatter_table(uplift=1.0):
    p = {n: C.SCATTER_P_TRIGGER[n] * uplift for n in (3, 4, 5, 6)}
    p[1] = C.SCATTER_P_1; p[2] = C.SCATTER_P_2
    p[0] = 1.0 - sum(p.values())
    assert p[0] > 0
    return np.array([p[i] for i in range(7)])


def play_base(rng, n, uplift=1.0, detail=False, bonus_ev=None):
    """Base / Extra Chance round (cost handled by caller).
    bonus_ev={tier: E[bonus win]} replaces each triggered bonus by its expected
    value (conditional-expectation estimator used for low-variance RTP)."""
    wild = rng.random((n, 5)) < C.PER_REEL_WILD_PROB
    mult = np.where(wild, _pick(WM_C, WM_V, rng.random((n, 5))), 0.0)
    k = wild.sum(axis=1)
    total = np.zeros(n)
    five = k == 5
    total[five] = C.WINCAP
    tier_n = np.zeros(n, dtype=np.int64)
    rest = np.nonzero(~five)[0]
    board = draw_symbols(rng, (len(rest), 4, 5))
    wl = wild[rest]
    wmask = np.broadcast_to(wl[:, None, :], board.shape)
    # scatters: count from table, placed on free cells
    tab = np.cumsum(scatter_table(uplift))
    ns = np.minimum(np.searchsorted(tab, rng.random(len(rest))), 6)
    free = 4 * (5 - k[rest])
    ns = np.minimum(ns, free)
    keys = rng.random((len(rest), 20)); keys[wmask.reshape(len(rest), 20)] = 2.0
    rank = np.argsort(np.argsort(keys, axis=1), axis=1)
    scm = (rank < ns[:, None]).reshape(len(rest), 4, 5)
    board[scm] = C.SC
    board[wmask] = C.W
    raw = eval_lines(board)
    spin = np.round(raw * spin_multiplier(mult[rest]), 2)
    spin += np.select([ns == 3, ns == 4, ns >= 5], [C.SCATTER_PAY[3], C.SCATTER_PAY[4], C.SCATTER_PAY[5]], 0.0)
    total[rest] = np.minimum(spin, C.WINCAP)
    spin_raw = np.zeros(n); spin_raw[rest] = spin
    tier_n[rest] = ns
    for sc, tier in C.TIER_BY_SCATTERS.items():
        sel = rest[ns == sc]
        if len(sel):
            if bonus_ev is None:
                total[sel] = run_bonus(rng, tier, total[sel])
            else:
                total[sel] = total[sel] + bonus_ev[tier]
    if bonus_ev is not None:
        trig = tier_n >= 3
        out = np.where(trig, total, floor_pay(total))
        if detail:
            return out, dict(scatters=tier_n, wilds=k, five=five, spin_raw=spin_raw)
        return out
    out = floor_pay(total)
    if detail:
        return out, dict(scatters=tier_n, wilds=k, five=five, spin_raw=spin_raw)
    return out


# ------------------------------------------------------------------ min 2 wild
def play_min2wild(rng, n, q=None):
    q = C.MIN2WILD_EXTRA_PROB if q is None else q
    keys = rng.random((n, 5))
    order = np.argsort(keys, axis=1)
    wild = np.zeros((n, 5), bool)
    np.put_along_axis(wild, order[:, :2], True, axis=1)
    extra = rng.random((n, 5)) < q
    wild |= extra
    mult = np.where(wild, _pick(WM_C, WM_V, rng.random((n, 5))), 0.0)
    k = wild.sum(axis=1)
    total = np.full(n, C.WINCAP)
    rest = np.nonzero(k < 5)[0]
    board = draw_symbols(rng, (len(rest), 4, 5))
    board[np.broadcast_to(wild[rest][:, None, :], board.shape)] = C.W
    total[rest] = np.minimum(np.round(eval_lines(board) * spin_multiplier(mult[rest]), 2), C.WINCAP)
    return floor_pay(total), k


def play_golden(rng, n):
    q = C.GOLDEN_CASE_LETTER_PROB
    p3 = q ** 3 / (1 - (1 - q) ** 3)
    return np.where(rng.random(n) < p3, C.WINCAP, 0.0)
