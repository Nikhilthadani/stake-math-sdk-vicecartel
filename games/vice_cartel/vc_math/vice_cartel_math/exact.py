"""Exact (no randomness) calculations. Ignores only the 25,000x cap on
accumulated line wins and the 0.1x floor; the simulator measures both."""
from __future__ import annotations
import itertools, math
from functools import lru_cache
import numpy as np
from . import config as C
from .sim import PAY, STRIP_P

WM = np.array(C.WILD_MULT_WEIGHTS) / sum(C.WILD_MULT_WEIGHTS)
MU_W = float((np.array(C.WILD_MULTIPLIERS) * WM).sum())
MU_B = float((np.array(C.BLUE_INCREMENTS) * np.array(C.BLUE_WEIGHTS)).sum() / sum(C.BLUE_WEIGHTS))
YEL = dict(zip(C.YELLOW_SPINS, np.array(C.YELLOW_WEIGHTS) / sum(C.YELLOW_WEIGHTS)))
SUBSETS = [S for k in range(6) for S in itertools.combinations(range(5), k)]
_COMBOS = np.array(list(itertools.product(range(9), repeat=5)), dtype=np.int8)


def _linepay(c):
    isw = c == C.W
    lead = np.cumprod(isw, axis=1).sum(axis=1)
    s = c[np.arange(len(c)), np.minimum(lead, 4)]
    run = np.cumprod((c == s[:, None]) | isw, axis=1).sum(axis=1)
    pay = np.where(s == C.SC, 0.0, PAY[np.where(s == C.SC, 9, s), run])
    return np.where(lead == 5, C.WILD_LINE_PAY_5, pay)


@lru_cache(None)
def ell(S, n_sc=0):
    """Exact EV of ONE payline given Wild reel set S and n_sc Scatters placed
    uniformly on the 4*(5-|S|) free cells (cells of the line on free reels
    receive Scatters hypergeometrically; others draw from the strip)."""
    S = tuple(S)
    free = [r for r in range(5) if r not in S]
    F = 4 * len(free); f = len(free)
    if f == 0:
        return C.WILD_LINE_PAY_5
    combos = _COMBOS[np.all(_COMBOS[:, list(S)] == 0, axis=1)] if S else _COMBOS
    c = combos.copy()
    for r in S:
        c[:, r] = C.W
    a = (c[:, free] == C.SC).sum(axis=1)                      # Scatters on line
    pr = np.ones(len(c))
    for r in free:
        sym = c[:, r]
        pr *= np.where(sym == C.SC, 1.0, STRIP_P[np.minimum(sym, 7)])
    hyp = np.array([math.comb(F - f, n_sc - j) / math.comb(F, n_sc) if 0 <= n_sc - j <= F - f else 0.0
                    for j in range(f + 1)])
    # P(specific set of j line cells are Scatter, rest not) = C(F-f, n-j)/C(F,n)
    return float((_linepay(c) * pr * hyp[a]).sum())


def _red_matrices():
    idx = {S: i for i, S in enumerate(SUBSETS)}
    n = len(SUBSETS)
    Rw = np.zeros((n, n)); Ra = np.zeros((n, n))
    for S in SUBSETS:
        i = idx[S]
        room = C.MAX_WILD_REELS_FROM_RED - len(S)
        if room <= 0:
            Rw[i, i] = 1.0
            continue
        empty = [r for r in range(5) if r not in S]
        for a, pa in ((1, 1 - C.RED_DOUBLE_PROB), (2, C.RED_DOUBLE_PROB)):
            a2 = min(a, room)
            news = list(itertools.combinations(empty, a2))
            for ns in news:
                j = idx[tuple(sorted(S + ns))]
                Rw[i, j] += pa / len(news)
                Ra[i, j] += pa / len(news) * a2
    return Rw, Ra


def bonus_ev(tier, wheel_prob=None, maxwin_weight=None, detail=False, tmax=200):
    """Exact Markov chain over (Wild set, turns left). Tracks probability mass
    P, multiplier-sum mass A and accumulated-win mass B per state; the MAX WIN
    segment replaces the accumulated win by exactly WINCAP."""
    t = C.BONUS_TIERS[tier]
    wp = t["wheel_prob"] if wheel_prob is None else wheel_prob
    mw = t["maxwin_weight"] if maxwin_weight is None else maxwin_weight
    sw = C.WHEEL_SEGMENT_WEIGHTS
    tot = sw["RED"] + sw["BLUE"] + sw["YELLOW"] + mw
    pR, pB, pY, pX = (wp * sw["RED"] / tot, wp * sw["BLUE"] / tot, wp * sw["YELLOW"] / tot, wp * mw / tot)
    pN = 1 - wp
    Rw, Ra = _red_matrices()
    L = np.array([14 * ell(S) for S in SUBSETS])
    nonempty = np.array([len(S) > 0 for S in SUBSETS])
    ksz = np.array([len(S) for S in SUBSETS])
    n = len(SUBSETS)
    P = np.zeros((n, tmax)); A = np.zeros((n, tmax)); B = np.zeros((n, tmax))
    starts = [i for i, S in enumerate(SUBSETS) if len(S) == t["start_wilds"]]
    for i in starts:
        P[i, t["spins"]] = 1 / len(starts)
        A[i, t["spins"]] = t["start_wilds"] * t["start_mult"] / len(starts)
    ev = 0.0; pmax = 0.0; spins = 0.0; endw = np.zeros(6)
    for _ in range(C.BONUS_SPIN_SAFETY_LIMIT):
        tp = P.sum()
        if tp < 1e-15:
            break
        spins += tp
        ev += pX * C.WINCAP * tp; pmax += pX * tp
        P2 = pN * P + pR * (Rw.T @ P) + pB * P
        A2 = pN * A + pR * (Rw.T @ A + MU_W * (Ra.T @ P)) + pB * (A + MU_B * P * nonempty[:, None])
        B2 = pN * B + pR * (Rw.T @ B) + pB * B
        for e, pe in YEL.items():
            P2[:, e:] += pY * pe * P[:, :-e]; A2[:, e:] += pY * pe * A[:, :-e]; B2[:, e:] += pY * pe * B[:, :-e]
        B2 = B2 + L[:, None] * np.where(nonempty[:, None], A2, P2)
        # consume one turn
        ev += B2[:, 1].sum()
        np.add.at(endw, ksz, P2[:, 1])
        P = np.zeros_like(P); A = np.zeros_like(A); B = np.zeros_like(B)
        P[:, :-1] = P2[:, 1:]; A[:, :-1] = A2[:, 1:]; B[:, :-1] = B2[:, 1:]
        P[:, 0] = A[:, 0] = B[:, 0] = 0
    if detail:
        return dict(ev=float(ev), p_maxwin=float(pmax), spins=float(spins), end_wilds=endw)
    return float(ev)


def min2wild_ev(q=None):
    q = C.MIN2WILD_EXTRA_PROB if q is None else q
    ev = 0.0; pk = np.zeros(6)
    for S in SUBSETS:
        k = len(S)
        if k < 2:
            continue
        p = math.comb(k, 2) / 10 * q ** (k - 2) * (1 - q) ** (5 - k)
        pk[k] += p
        ev += p * (C.WINCAP if k == 5 else 14 * ell(S) * k * MU_W)
    return ev, pk


def golden_rtp():
    q = C.GOLDEN_CASE_LETTER_PROB
    p3 = q ** 3 / (1 - (1 - q) ** 3)
    return p3 * C.WINCAP / C.BET_MODES["golden_case"]["cost"], p3


def scatter_table(uplift=1.0):
    p = {n: C.SCATTER_P_TRIGGER[n] * uplift for n in (3, 4, 5, 6)}
    p[1], p[2] = C.SCATTER_P_1, C.SCATTER_P_2
    p[0] = 1 - sum(p.values())
    return p


def base_components(uplift=1.0, bonus_ev=None, p_wild=None):
    """Exact pre-floor return per 1x bet unit of a base / Extra Chance round,
    split into lines, scatter pay, five-Wild Max Win and each bonus tier.
    bonus_ev: {tier: EV} (defaults to exact bonus_ev())."""
    pw = C.PER_REEL_WILD_PROB if p_wild is None else p_wild
    if bonus_ev is None:
        bonus_ev = {t: bonus_ev_(t) for t in C.BONUS_TIERS}
    T = scatter_table(uplift)
    out = dict(lines=0.0, scatter=0.0, five_wilds=pw ** 5 * C.WINCAP)
    trig = {t: 0.0 for t in C.BONUS_TIERS}
    for S in SUBSETS:
        k = len(S)
        if k == 5:
            continue
        PS = pw ** k * (1 - pw) ** (5 - k)
        M = 1.0 if k == 0 else k * MU_W
        F = 4 * (5 - k)
        for n, pn in T.items():
            n2 = min(n, F)
            out["lines"] += PS * pn * 14 * ell(S, n2) * M
            out["scatter"] += PS * pn * C.SCATTER_PAY.get(n2, 0.0)
            if n2 in C.TIER_BY_SCATTERS:
                trig[C.TIER_BY_SCATTERS[n2]] += PS * pn
    for t, p in trig.items():
        out[t] = p * bonus_ev[t]
    out["total"] = sum(out.values())
    return out, trig


bonus_ev_ = bonus_ev
