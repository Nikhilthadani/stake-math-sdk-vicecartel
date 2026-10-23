"""Reference per-round engine (scalar, seeded). This is the logic to port into
the Stake SDK game files; it mirrors sim.py rule-for-rule.

Every function takes a random.Random so a round is reproducible from a seed.
Returns a Round with the final payout and an event log (for book/UI mapping).
"""
from __future__ import annotations
import random
from dataclasses import dataclass, field
from . import config as C

_LINE_PAY = {s: C.PAYTABLE[s] for s in C.PAYTABLE}


def _weighted(rng: random.Random, values, weights):
    roll = rng.uniform(0, sum(weights))
    acc = 0.0
    for v, w in zip(values, weights):
        acc += w
        if roll <= acc:
            return v
    return values[-1]


def _strip_symbol(rng):
    syms = list(C.STRIP_COUNTS)
    return _weighted(rng, syms, [C.STRIP_COUNTS[s] for s in syms])


def floor_pay(x: float) -> float:
    cents = int(round(x * 100))
    return (cents - cents % 10) / 100.0


def line_pay(cells) -> float:
    """cells: 5 symbol names left->right. Same rules as SDK Lines.get_lines."""
    wm = 0
    while wm < 5 and cells[wm] == "W":
        wm += 1
    if wm == 5:
        return C.WILD_LINE_PAY_5
    sym = cells[wm]
    if sym == "SC":
        return 0.0
    n = wm
    while n < 5 and cells[n] in (sym, "W"):
        n += 1
    return _LINE_PAY[sym][n - 3] if n >= 3 else 0.0


def evaluate_lines(board) -> float:
    """board[row][reel] -> raw total of all 14 lines (before multiplier)."""
    return sum(line_pay([board[r][c] for c, r in enumerate(line)]) for line in C.PAYLINES)


def spin_multiplier(wilds: dict) -> float:
    return float(sum(wilds.values())) if wilds else 1.0


@dataclass
class Round:
    mode: str
    payout: float = 0.0
    events: list = field(default_factory=list)
    max_win: bool = False
    bonus: str | None = None
    scatters: int = 0
    wild_reels: int = 0


def _draw_board(rng, wild_reels):
    board = [[_strip_symbol(rng) for _ in range(5)] for _ in range(4)]
    for r in wild_reels:
        for row in range(4):
            board[row][r] = "W"
    return board


def _scatter_count(rng, uplift):
    p = {n: C.SCATTER_P_TRIGGER[n] * uplift for n in (3, 4, 5, 6)}
    p[1], p[2] = C.SCATTER_P_1, C.SCATTER_P_2
    p[0] = 1.0 - sum(p.values())
    u, acc = rng.random(), 0.0
    for n in range(7):
        acc += p[n]
        if u < acc:
            return n
    return 0


def _finish(rd: Round, total: float) -> Round:
    total = min(total, C.WINCAP)
    if total >= C.WINCAP:
        rd.max_win = True
    rd.payout = floor_pay(total)
    rd.events.append(("final", rd.payout))
    return rd


# --------------------------------------------------------------- bonus
def play_bonus(rng, tier: str, start_win: float, rd: Round) -> float:
    """Initialise state ONCE from tier config (no carry-over), play to the end,
    return round total (start_win + bonus wins), capped."""
    t = C.BONUS_TIERS[tier]
    rd.bonus = tier
    wilds: dict[int, float] = {}
    for r in rng.sample(range(5), t["start_wilds"]):
        wilds[r] = float(t["start_mult"])
    turns, spins, win = t["spins"], 0, start_win
    rd.events.append(("bonus_start", tier, t["spins"], dict(wilds)))
    sw = C.WHEEL_SEGMENT_WEIGHTS
    segs = ["RED", "BLUE", "YELLOW", "MAX_WIN"]
    wts = [sw["RED"], sw["BLUE"], sw["YELLOW"], t["maxwin_weight"]]
    while turns > 0 and win < C.WINCAP and spins < C.BONUS_SPIN_SAFETY_LIMIT:
        spins += 1
        if rng.random() < t["wheel_prob"]:
            seg = _weighted(rng, segs, wts)
            rd.events.append(("wheel", seg))
            if seg == "MAX_WIN":                    # 5-Wild icon
                for r in range(5):
                    wilds.setdefault(r, 0.0)
                rd.events.append(("five_wilds",))
                return C.WINCAP                      # round ends, exactly once
            if seg == "RED":
                add = 2 if rng.random() < C.RED_DOUBLE_PROB else 1
                add = min(add, C.MAX_WILD_REELS_FROM_RED - len(wilds))
                empty = [r for r in range(5) if r not in wilds]
                for r in rng.sample(empty, max(add, 0)) if add > 0 else []:
                    wilds[r] = float(_weighted(rng, C.WILD_MULTIPLIERS, C.WILD_MULT_WEIGHTS))
            elif seg == "BLUE" and wilds:
                r = rng.choice(sorted(wilds))
                wilds[r] += _weighted(rng, C.BLUE_INCREMENTS, C.BLUE_WEIGHTS)
            elif seg == "YELLOW":
                turns += _weighted(rng, C.YELLOW_SPINS, C.YELLOW_WEIGHTS)
        board = _draw_board(rng, wilds.keys())
        win += round(evaluate_lines(board) * spin_multiplier(wilds), 2)
        turns -= 1
    return min(win, C.WINCAP)


# --------------------------------------------------------------- modes
def play_base(rng, mode="base") -> Round:
    uplift = C.BET_MODES[mode].get("uplift", 1.0)
    rd = Round(mode)
    wilds = {r: float(_weighted(rng, C.WILD_MULTIPLIERS, C.WILD_MULT_WEIGHTS))
             for r in range(5) if rng.random() < C.PER_REEL_WILD_PROB}
    rd.wild_reels = len(wilds)
    if len(wilds) == 5:
        rd.events.append(("five_wilds",))
        return _finish(rd, C.WINCAP)
    board = _draw_board(rng, [])
    n = _scatter_count(rng, uplift)
    free = [(row, r) for r in range(5) if r not in wilds for row in range(4)]
    n = min(n, len(free))
    for row, r in rng.sample(free, n):
        board[row][r] = "SC"
    for r in wilds:
        for row in range(4):
            board[row][r] = "W"
    rd.scatters = n
    spin = round(evaluate_lines(board) * spin_multiplier(wilds), 2)
    spin += C.SCATTER_PAY.get(min(n, 6), 0.0)
    total = min(spin, C.WINCAP)
    if n in C.TIER_BY_SCATTERS:                     # exactly one tier per count
        total = play_bonus(rng, C.TIER_BY_SCATTERS[n], total, rd)
    return _finish(rd, total)


def play_bonus_buy(rng, mode) -> Round:
    """Purchased bonus: no base spin, no Scatter/trigger roll, no Wild roll."""
    rd = Round(mode)
    return _finish(rd, play_bonus(rng, C.BET_MODES[mode]["tier"], 0.0, rd))


def play_min2wild(rng, mode="min2wild") -> Round:
    rd = Round(mode)
    reels = set(rng.sample(range(5), 2))
    for r in range(5):
        if r not in reels and rng.random() < C.MIN2WILD_EXTRA_PROB:
            reels.add(r)
    wilds = {r: float(_weighted(rng, C.WILD_MULTIPLIERS, C.WILD_MULT_WEIGHTS)) for r in sorted(reels)}
    rd.wild_reels = len(wilds)
    if len(wilds) == 5:
        rd.events.append(("five_wilds",))
        return _finish(rd, C.WINCAP)
    board = _draw_board(rng, wilds.keys())
    return _finish(rd, round(evaluate_lines(board) * spin_multiplier(wilds), 2))


def play_golden(rng, mode="golden_case") -> Round:
    rd = Round(mode)
    q = C.GOLDEN_CASE_LETTER_PROB
    while True:
        n = sum(rng.random() < q for _ in range(3))
        if n:
            break
    rd.events.append(("letters", n))
    return _finish(rd, C.WINCAP if n == 3 else 0.0)


def play(mode: str, seed: int) -> Round:
    rng = random.Random(seed)
    kind = C.BET_MODES[mode]["kind"]
    return {"base": play_base, "buy": play_bonus_buy,
            "min2wild": play_min2wild, "golden": play_golden}[kind](rng, mode)
